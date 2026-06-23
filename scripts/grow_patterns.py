#!/usr/bin/env python3
"""
grow_patterns.py -- iterate patterns.v coverage for decode_modes.

The loop this drives:

    decode_modes  ──>  op_hypotheses.json   (UNKNOWN branches + signatures)
         ^                     |
         |                     v
    re-run extract  <──  grow_patterns report   (cluster by shared carry nodes:
         ^                     |                  "5 branches share chain abc123")
         |                     v
    patterns.v   <──  [human/LLM writes a pattern  OR  a proposed_op]
                               |
                               v
                       grow_patterns verify  (ABC proves cone ≡ proposed_op;
                                              UNSAT = accept, SAT = CEX)

Three subcommands:

  report   Cluster the UNKNOWN entries in op_hypotheses.json by shared carry-chain
           nodes (union-find on overlapping w_X* structural node sets) and print a
           carry-chain sharing table.  Tells you which FF/branches share each chain.
           Optionally takes --ff-map to whitelist leaf-signal extraction.
           (Deterministic, no Yosys.)

  recheck  For each UNKNOWN branch, re-run the SINGLE cofactor through
           decode_modes' yosys pipeline with the CURRENT patterns.v.  If the
           cone is now fully operator-recognised (no opaque gates left), mark
           it RESOLVED_PATTERN.  Reports the coverage delta.  (Runs Yosys.)

  verify   For branches where the LLM filled "proposed_op" (e.g. "MI1_QT + 1"),
           build an ABC miter between the real cofactor cone and the proposed
           word-level op and prove equivalence.  UNSAT → RESOLVED_OP, SAT →
           print a counterexample hint.  ABC is the only ground-truth gate.

Design rule honoured: NO LLM calls here.  This is the deterministic tool layer.
The "propose a pattern / op" step is done by the agent BETWEEN invocations.

Usage:
  python3 scripts/grow_patterns.py report  --hypo op_hypotheses.json [--ff-map ff_map.json]
  python3 scripts/grow_patterns.py recheck --hypo op_hypotheses.json \\
         --netlist COUNT_12BX2/impl.v --lib COUNT_12BX2/SC_LIB_SCH.v --top COUNT_12BX2
  python3 scripts/grow_patterns.py verify  --hypo op_hypotheses.json \\
         --netlist COUNT_12BX2/impl.v --lib COUNT_12BX2/SC_LIB_SCH.v --top COUNT_12BX2
"""
import argparse, hashlib, json, os, re, subprocess, sys, tempfile
from collections import defaultdict, Counter

# Reuse the single source of truth.  decode_modes.py must sit next to this file.
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)
import decode_modes as dm   # noqa: E402

YOSYS = "yosys"

# Cell types that count as "recognised" — anything else left in a cone after
# extract means the motif is NOT yet covered by patterns.v / extract_fa.
RECOGNISED_TYPES = {
    "$fa", "full_adder", "half_adder", "incr_bit", "carry_cell",
    "carry_cmp_seed", "carry_cmp_prop", "xor3_cell", "xnor3_cell", "mux2",
}
# Pure interconnect / boundary cells that are fine to see in a cone.
BENIGN_PREFIXES = dm._FF_PREFIXES + ("$_BUF_", "$buf")

# Clustering thresholds for carry-chain union-find.
# Two branches are merged if they share at least MIN_SHARED_NODES structural
# nodes OR their Jaccard similarity meets JACCARD_THRESHOLD.
# MIN_SHARED_NODES catches the common case where two operands in the same carry
# chain share ~10–50 w_X* nodes; JACCARD_THRESHOLD catches shorter chains where
# the absolute count is small but the overlap fraction is high.
MIN_SHARED_NODES  = 3
JACCARD_THRESHOLD = 0.3


# ---------------------------------------------------------------------------
# Structural-node / leaf extraction helpers
# ---------------------------------------------------------------------------

# Yosys structural intermediate nodes always start with w_X (e.g. w_X773_346_Z).
_STRUCTURAL_RE = re.compile(r'\bw_X\w+\b')

# Any C-identifier-like token in an expression.
_IDENT_RE = re.compile(r'\b[A-Za-z_][A-Za-z0-9_$]*\b')

# Tokens that are definitely NOT leaf signals: Verilog/Yosys keywords, Yosys
# internal wire names, and abc-generated node names.
_EXCLUDE_RE = re.compile(
    r'^('
    r'wire|reg|input|output|assign|module|endmodule|always|begin|end|'
    r'if|else|case|casez|casex|default|posedge|negedge|'
    r'abc|new_n\d+|w_X\w+'
    r')$'
)


def extract_structural_nodes(expr: str) -> frozenset:
    """Return frozenset of w_X* structural node references appearing in expr."""
    return frozenset(_STRUCTURAL_RE.findall(expr))


def chain_signature(nodes) -> str:
    """Stable 12-hex-char hash of a sorted set of structural node names."""
    blob = ",".join(sorted(nodes))
    return hashlib.sha1(blob.encode()).hexdigest()[:12]


def extract_leaf_inputs(expr: str, valid_leaves=None) -> list:
    """
    Return sorted list of true leaf signal names from expr.

    First pass: collect all identifier-like tokens.
    Second pass: drop keywords and Yosys internal/intermediate names.
    Third pass: if valid_leaves whitelist is provided, intersect with it.
    """
    candidates = {t for t in _IDENT_RE.findall(expr) if not _EXCLUDE_RE.match(t)}
    if valid_leaves is not None:
        candidates &= valid_leaves
    return sorted(candidates)


def load_valid_leaves(ff_map_path) -> set | None:
    """
    Build a whitelist of valid leaf signal names from ff_map.json.
    Returns None if the file is absent or empty (caller falls back to
    keyword-exclusion-only filtering).
    """
    if not ff_map_path or not os.path.exists(ff_map_path):
        return None
    with open(ff_map_path) as fh:
        ff_map = json.load(fh)
    leaves = set()
    for entry in ff_map.values():
        if not isinstance(entry, dict):
            continue
        for field in ("q_net", "name", "d_net"):
            if field in entry:
                leaves.add(entry[field])
        # Collect any extra signal fields stored under arbitrary keys.
        for v in entry.values():
            if isinstance(v, str) and v and not _EXCLUDE_RE.match(v):
                leaves.add(v)
    return leaves or None


# ---------------------------------------------------------------------------
# Union-Find for carry-chain clustering
# ---------------------------------------------------------------------------

class _UF:
    def __init__(self):
        self._p = {}

    def find(self, x):
        self._p.setdefault(x, x)
        if self._p[x] != x:
            self._p[x] = self.find(self._p[x])
        return self._p[x]

    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx != ry:
            self._p[ry] = rx


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def load_hypo(path):
    if not os.path.exists(path):
        sys.exit(f"ERROR: {path} not found — run decode_modes with --hypo first")
    with open(path) as fh:
        return json.load(fh)


def save_hypo(path, hyps):
    with open(path, "w") as fh:
        json.dump(hyps, fh, indent=2)


def parse_cond(cond):
    """'CTRL0=1,CTRL1=0' -> {'CTRL0':1,'CTRL1':0}."""
    out = {}
    for tok in cond.split(","):
        tok = tok.strip()
        if not tok or "=" not in tok:
            continue
        name, val = tok.split("=", 1)
        out[name.strip()] = int(val)
    return out


def flatten_for(netlist, libs, top, tmpdir):
    """Flatten once; return mod dict."""
    design = dm.flatten_netlist(netlist, libs, top, tmpdir)
    mod = design["modules"].get(top)
    if mod is None:
        sys.exit(f"ERROR: module '{top}' not found after flatten")
    return mod


# ---------------------------------------------------------------------------
# Subcommand: report  (carry-chain sharing table)
# ---------------------------------------------------------------------------

def cmd_report(args):
    hyps = load_hypo(args.hypo)
    unknown = {k: v for k, v in hyps.items() if v.get("status", "UNKNOWN") == "UNKNOWN"}
    if not unknown:
        print("No UNKNOWN branches — patterns.v already covers everything. ✓")
        return

    valid_leaves = load_valid_leaves(getattr(args, "ff_map", None))
    if valid_leaves is None:
        print("(no --ff-map supplied; leaf filtering uses keyword exclusion only)\n")

    # Per-branch: extract structural nodes and fix up leaf inputs.
    branch_nodes  = {}   # key -> frozenset[str]
    branch_leaves = {}   # key -> list[str]
    for key, rec in unknown.items():
        expr = rec.get("raw_expr", "")
        nodes = extract_structural_nodes(expr)
        branch_nodes[key]  = nodes
        branch_leaves[key] = extract_leaf_inputs(expr, valid_leaves)
        # Update stored signature to chain-node hash (replaces old op histogram).
        # The old op histogram is retained in a separate field for reference.
        if "signature" in rec:
            rec["signature_op_histogram"] = rec["signature"]
        rec["signature"] = chain_signature(nodes) if nodes else "trivial"
        rec["inputs"] = branch_leaves[key]   # write back the corrected inputs

    # Cluster branches that share carry-chain nodes (union-find).
    uf   = _UF()
    keys = list(unknown.keys())
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            ka, kb = keys[i], keys[j]
            na, nb = branch_nodes[ka], branch_nodes[kb]
            if not na or not nb:
                continue
            shared      = len(na & nb)
            union_size  = len(na | nb)
            jaccard     = shared / union_size if union_size else 0.0
            if shared >= MIN_SHARED_NODES or jaccard >= JACCARD_THRESHOLD:
                uf.union(ka, kb)

    # Collect groups; compute per-group chain node union and candidate leaves.
    groups       = defaultdict(list)
    for key in keys:
        groups[uf.find(key)].append(key)

    group_chain_nodes = {}
    group_leaves      = {}
    for rep, members in groups.items():
        chain = set()
        leaves = set()
        for k in members:
            chain  |= branch_nodes[k]
            leaves |= set(branch_leaves[k])
        group_chain_nodes[rep] = chain
        group_leaves[rep]      = sorted(leaves)

    # ---- Print carry-chain sharing table ----
    print(f"\n{len(unknown)} UNKNOWN branches → {len(groups)} carry-chain groups")
    print(f"(merge criteria: shared structural nodes ≥ {MIN_SHARED_NODES}"
          f" OR Jaccard ≥ {JACCARD_THRESHOLD})\n")
    print("Carry-chain sharing table:")
    print(f"  {'chain_sig':>12}  {'branches':>8}  {'chain_nodes':>11}  members")
    print("  " + "-" * 90)

    for rep, members in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        chain     = group_chain_nodes[rep]
        chain_sig = chain_signature(chain) if chain else "trivial"
        member_strs = [f"{unknown[k]['ff']}:{unknown[k]['cond']}" for k in members]
        first_line  = ", ".join(member_strs[:3])
        if len(members) > 3:
            first_line += f"  ...+{len(members) - 3} more"
        print(f"  {chain_sig:>12}  {len(members):>8}  {len(chain):>11}  {first_line}")

        # Show representative structural nodes (first 5).
        sample_nodes = sorted(chain)[:5]
        node_str = ", ".join(sample_nodes)
        if len(chain) > 5:
            node_str += f", ...+{len(chain) - 5}"
        print(f"  {'':>12}  {'':>8}  {'':>11}  chain nodes: [{node_str}]")

        # Show candidate operand leaves.
        leaves = group_leaves[rep]
        if leaves:
            leaf_str = ", ".join(leaves[:8])
            if len(leaves) > 8:
                leaf_str += f", ...+{len(leaves) - 8}"
            print(f"  {'':>12}  {'':>8}  {'':>11}  candidate leaves: [{leaf_str}]")
        print()

    save_hypo(args.hypo, hyps)   # persist corrected signatures and inputs
    print("(op_hypotheses.json updated with chain-based signatures and corrected inputs)\n")
    print("Next: for each group, either")
    print("  (a) add a (* extract_pattern *) module to patterns.v, then: grow_patterns recheck")
    print("  (b) fill 'proposed_op' in op_hypotheses.json, then:        grow_patterns verify")


# ---------------------------------------------------------------------------
# Subcommand: recheck  (did the new pattern actually fire?)
# ---------------------------------------------------------------------------

def cone_cell_types(mod_opt, d_bit):
    """BFS the fan-in cone of d_bit; return Counter of cell types reached
       (stopping at FF / port boundaries)."""
    drivers = dm.build_driver_map(mod_opt)
    seen, stack, types = set(), [d_bit], Counter()
    while stack:
        b = stack.pop()
        if not isinstance(b, int) or b in seen:
            continue
        seen.add(b)
        entry = drivers.get(b)
        if entry is None or entry[0] == "__PORT__":
            continue
        inst, _ = entry
        cell  = mod_opt["cells"][inst]
        ctype = cell["type"]
        types[ctype] += 1
        if any(ctype.startswith(p) for p in dm._FF_PREFIXES):
            continue  # FF boundary — don't cross
        pd = cell.get("port_directions", {})
        for pin, bits in cell["connections"].items():
            if pd.get(pin) == "input":
                for bb in bits:
                    if isinstance(bb, int):
                        stack.append(bb)
    return types


def is_recognised(types):
    """A cone is 'recognised' if every non-benign cell is a known operator."""
    for ctype in types:
        if ctype in RECOGNISED_TYPES:
            continue
        if any(ctype.startswith(p) for p in BENIGN_PREFIXES):
            continue
        return False
    return True


def rebuild_branch(mod, netlist_top, ctrl_assignment, ff, tmpdir, combo_id):
    """Inject one ctrl assignment, run the decode_modes yosys pipeline (WITH
       extract), return (expr, mod_opt, d_bit)."""
    const_map = {}
    for name, val in ctrl_assignment.items():
        b = dm.get_net_bit(mod, name)
        if b is None:
            print(f"    WARNING: ctrl '{name}' not found; skipping", file=sys.stderr)
            continue
        const_map[b] = val
    mod_c   = dm.inject_constants(mod, const_map)
    mod_opt = dm.yosys_optimise(mod_c, netlist_top, tmpdir, combo_id, run_extract=True)
    nm  = dm.build_net_map(mod_opt)
    drv = dm.build_driver_map(mod_opt)
    d_bit, _ = dm.find_ff_d_bit(mod_opt, ff, drv, nm)
    expr = dm.build_expr(d_bit, mod_opt, nm, drv) if d_bit is not None else "1'bx"
    return expr, mod_opt, d_bit


def cmd_recheck(args):
    hyps    = load_hypo(args.hypo)
    unknown = [(k, v) for k, v in hyps.items() if v.get("status", "UNKNOWN") == "UNKNOWN"]
    if not unknown:
        print("No UNKNOWN branches to re-check. ✓")
        return

    resolved = 0
    with tempfile.TemporaryDirectory() as tmpdir:
        mod = flatten_for(args.netlist, args.lib, args.top, tmpdir)
        for i, (key, rec) in enumerate(unknown):
            ff   = rec["ff"]
            assn = parse_cond(rec["cond"])
            expr, mod_opt, d_bit = rebuild_branch(mod, args.top, assn, ff, tmpdir, i)
            if d_bit is None:
                print(f"  [{ff}:{rec['cond']}] D folded to constant: {expr}")
                rec["status"], rec["raw_expr"] = "RESOLVED_PATTERN", expr
                resolved += 1
                continue
            types = cone_cell_types(mod_opt, d_bit)
            if is_recognised(types):
                print(f"  [{ff}:{rec['cond']}] ✓ now recognised -> {expr}")
                rec["status"], rec["raw_expr"] = "RESOLVED_PATTERN", expr
                resolved += 1
            else:
                leftover = {t: c for t, c in types.items()
                            if t not in RECOGNISED_TYPES
                            and not any(t.startswith(p) for p in BENIGN_PREFIXES)}
                print(f"  [{ff}:{rec['cond']}] still opaque; leftover cells = {leftover}")
                rec["raw_expr"] = expr

    save_hypo(args.hypo, hyps)
    print(f"\nrecheck: {resolved}/{len(unknown)} branches resolved by current patterns.v")
    print(f"         {len(unknown) - resolved} still UNKNOWN — run 'report' for the chain table")


# ---------------------------------------------------------------------------
# Subcommand: verify  (ABC proves cone ≡ proposed word-level op)
# ---------------------------------------------------------------------------

def write_cone_verilog(mod, netlist_top, ctrl_assignment, ff, tmpdir, combo_id):
    """
    Re-run the branch, then write the D-cone out as a standalone verilog module
    'impl' whose single output is the FF's D value and whose inputs are the
    cone's leaf nets.  Returns (impl_v_path, input_names) or (None, None).
    """
    const_map = {}
    for name, val in ctrl_assignment.items():
        b = dm.get_net_bit(mod, name)
        if b is not None:
            const_map[b] = val
    mod_c = dm.inject_constants(mod, const_map)

    design   = {"creator": "grow_patterns", "modules": {netlist_top: mod_c}}
    in_json  = os.path.join(tmpdir, f"v{combo_id}_in.json")
    impl_v   = os.path.join(tmpdir, f"v{combo_id}_impl.v")
    ys_path  = os.path.join(tmpdir, f"v{combo_id}_cone.ys")
    log_path = os.path.join(tmpdir, f"v{combo_id}_cone.log")
    with open(in_json, "w") as fh:
        json.dump(design, fh)

    nm  = dm.build_net_map(mod_c)
    drv = dm.build_driver_map(mod_c)
    d_bit, _ = dm.find_ff_d_bit(mod_c, ff, drv, nm)
    if d_bit is None:
        return None, None
    d_net = nm.get(d_bit)
    if d_net is None:
        return None, None

    cmds = [
        f"read_json {in_json}",
        "opt_expr", "opt_clean",
        f"abc -g {dm.NORM_BASIS}", "opt_clean",
        f"select -set cone {d_net} %ci*",
        f"rename {netlist_top} impl",
        f"submod -name impl_cone @cone",
        f"write_verilog -noattr {impl_v}",
    ]
    with open(ys_path, "w") as fh:
        fh.write("\n".join(cmds) + "\n")
    with open(log_path, "w") as lh:
        subprocess.run([YOSYS, "-q", ys_path], stdout=lh, stderr=subprocess.STDOUT)

    if not os.path.exists(impl_v):
        return None, None
    return impl_v, None


def write_spec_verilog(proposed_op, bit, inputs, tmpdir, combo_id):
    """
    Render the LLM's proposed word-level op as a 1-bit spec module.

    proposed_op is a human string like 'MI1_QT + 1' or 'MI1_SUM + MI1_QT'.
    For a real implementation you parse this into a small expression over the
    same leaf nets the cone exposes, pick bit `bit`, and emit:

        module spec(<inputs>, output Y); assign Y = <expr_bit>; endmodule

    This is left as a focused TODO because the safe way to evaluate '+' on the
    right bit-slice is to let Yosys elaborate the arithmetic rather than
    hand-expanding it: build a tiny wrapper that declares the operands as
    vectors, writes `assign result = opA + opB;`, and taps result[bit].
    """
    raise NotImplementedError(
        "write_spec_verilog: parse proposed_op into a bit-sliced assign.\n"
        "Recommended: declare operands as [W-1:0] vectors, 'assign r = opA + opB;',\n"
        "tap r[bit], and let Yosys synthesise the adder so the miter is exact.")


def abc_miter(impl_v, spec_v, top_impl, top_spec, tmpdir, combo_id):
    """
    Prove impl ≡ spec with a SAT miter.  Returns (equiv: bool, cex_text: str).
    This is the GROUND-TRUTH gate — the same role ABC plays in check_equiv.py.
    """
    ys_path  = os.path.join(tmpdir, f"v{combo_id}_miter.ys")
    log_path = os.path.join(tmpdir, f"v{combo_id}_miter.log")
    cmds = [
        f"read_verilog {impl_v}",
        f"read_verilog {spec_v}",
        f"miter -equiv -flatten {top_impl} {top_spec} miter",
        "hierarchy -top miter",
        "flatten",
        "sat -verify -prove trigger 0 -show-inputs miter",
    ]
    with open(ys_path, "w") as fh:
        fh.write("\n".join(cmds) + "\n")
    with open(log_path, "w") as lh:
        subprocess.run([YOSYS, "-q", ys_path], stdout=lh, stderr=subprocess.STDOUT)
    text = open(log_path).read()
    equiv = ("Assumption is satisfied" in text) or ("SUCCESS" in text) \
            or ("UNSATISFIABLE" in text) or ("proved" in text.lower())
    return equiv, text[-1500:]


def cmd_verify(args):
    hyps = load_hypo(args.hypo)
    todo = [(k, v) for k, v in hyps.items()
            if v.get("status", "UNKNOWN") == "UNKNOWN" and v.get("proposed_op")]
    if not todo:
        print("No branches with a 'proposed_op' to verify.")
        print("Fill op_hypotheses.json[*].proposed_op (and .bit), then re-run.")
        return

    resolved = 0
    with tempfile.TemporaryDirectory() as tmpdir:
        mod = flatten_for(args.netlist, args.lib, args.top, tmpdir)
        for i, (key, rec) in enumerate(todo):
            ff, cond = rec["ff"], rec["cond"]
            print(f"\n[verify] {ff}:{cond}  proposed_op = {rec['proposed_op']} (bit {rec.get('bit')})")
            assn   = parse_cond(cond)
            impl_v, _ = write_cone_verilog(mod, args.top, assn, ff, tmpdir, i)
            if impl_v is None:
                print("  ! could not isolate cone (see TODO in write_cone_verilog)")
                continue
            try:
                spec_v = write_spec_verilog(rec["proposed_op"], rec.get("bit"),
                                            rec.get("inputs", []), tmpdir, i)
            except NotImplementedError as e:
                print(f"  ! spec emitter is a stub: {str(e).splitlines()[0]}")
                continue
            equiv, cex = abc_miter(impl_v, spec_v, "impl_cone", "spec", tmpdir, i)
            if equiv:
                print("  ✓ UNSAT — cone ≡ proposed_op.  Accepting word-level op.")
                rec["status"] = "RESOLVED_OP"
                resolved += 1
            else:
                print("  ✗ SAT — proposed_op is WRONG for this cone. CEX tail:")
                print("    " + "\n    ".join(cex.strip().splitlines()[-6:]))

    save_hypo(args.hypo, hyps)
    print(f"\nverify: {resolved}/{len(todo)} proposed ops proven equivalent")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("report", help="cluster UNKNOWN branches by shared carry-chain nodes")
    pr.add_argument("--hypo",   required=True)
    pr.add_argument("--ff-map", default=None, dest="ff_map",
                    help="ff_map.json — used to whitelist valid leaf signal names")
    pr.set_defaults(func=cmd_report)

    for name, fn in (("recheck", cmd_recheck), ("verify", cmd_verify)):
        p = sub.add_parser(name)
        p.add_argument("--hypo",    required=True)
        p.add_argument("--netlist", required=True)
        p.add_argument("--lib",     action="append", default=[])
        p.add_argument("--top",     required=True)
        p.set_defaults(func=fn)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
