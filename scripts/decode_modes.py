#!/usr/bin/env python3
"""
decode_modes.py -- Shannon cofactor a FF's D-input cone → compact mode table.

Algorithm:
  1. Flatten the entire netlist ONCE with Yosys (cell expansion → primitives).
  2. For each combination of ctrl signal values:
       a. Inject constants into the flat JSON (replace ctrl bit IDs with "0"/"1"
          in every cell's input connections — Yosys-format constant strings).
       b. Write per-combo JSON, run light opt -> abc -g (normalise basis) ->
          extract_fa -> extract -map patterns.v for a minimised, operator-
          recognised netlist.
       c. Walk the D-input expression tree in the minimised netlist → short expr.
       d. Record the expr + any unrecognised terms in op_hypotheses.json.
  3. Emit {"ff":..., "ctrl":[...], "modes":[{"cond":..., "expr":...}]}.

Usage:
  python3 scripts/decode_modes.py \
      --netlist COUNT_12BX2/impl.v \
      --lib     COUNT_12BX2/SC_LIB_SCH.v \
      --top     COUNT_12BX2 \
      --ff      X63_1886_Q \
      --ctrl    "X412_46_Z" \
      --out     COUNT_12BX2/modes/X63_1886_Q.json
"""
import argparse, copy, json, os, re, subprocess, sys, tempfile, itertools

YOSYS       = "yosys"
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PATTERNS_V  = os.path.join(SCRIPTS_DIR, "patterns.v")


# ---------------------------------------------------------------------------
# Phase 1: flatten netlist once
# ---------------------------------------------------------------------------

def flatten_netlist(netlist, lib_list, top, tmpdir):
    """Read netlist with cell expansion (not -lib), proc, flatten, write JSON.

    We run 'techmap; opt_expr; opt_clean' after flatten so that abstract
    cells ($adff, $procdff, techmap-internal) are converted to stable Yosys
    primitives ($_ADFF_PN0_, $_DFF_P_, etc.).  The resulting JSON survives a
    read_json→opt_expr→write_json round-trip without validation errors.
    """
    ys = []
    for lf in lib_list:
        ys.append(f"read_verilog {lf}")
    ys.append(f"read_verilog {netlist}")
    ys.append(f"hierarchy -top {top} -check")
    ys.append("proc")
    ys.append("flatten")
    ys.append("techmap")      # abstract cells → $_ADFF_*, $_DFF_*, etc.
    ys.append("opt_expr")     # constant folding in the combinational cone
    ys.append("opt_clean")    # remove dead wires/cells
    json_out = os.path.join(tmpdir, "flat.json")
    ys_path  = os.path.join(tmpdir, "flat.ys")
    log_path = os.path.join(tmpdir, "flat.log")
    with open(ys_path, "w") as fh:
        fh.write("\n".join(ys) + "\n")
        fh.write(f"write_json {json_out}\n")
    with open(log_path, "w") as lh:
        subprocess.run([YOSYS, "-q", ys_path], stdout=lh, stderr=subprocess.STDOUT)
    if not os.path.exists(json_out):
        with open(log_path) as lh:
            sys.stderr.write(lh.read())
        sys.exit("ERROR: Yosys flatten failed — see log above")
    with open(json_out) as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Phase 2a: inject constants into flat JSON
# ---------------------------------------------------------------------------

def inject_constants(mod, const_map):
    """
    const_map: {bit_id (int) -> 0 or 1}
    Deep-copy mod and replace those bit IDs with Yosys constant strings
    ("0" / "1") in every cell's INPUT connections.
    OUTPUT connections are left intact so netnames / drivers remain valid.
    """
    mod = copy.deepcopy(mod)
    for cell in mod.get("cells", {}).values():
        pd = cell.get("port_directions", {})
        for pin, bits in cell.get("connections", {}).items():
            if pd.get(pin) != "input":
                continue
            cell["connections"][pin] = [
                ("1" if const_map[b] else "0")
                if (isinstance(b, int) and b in const_map) else b
                for b in bits
            ]
    return mod


# ---------------------------------------------------------------------------
# Phase 2b: Yosys opt + extract on the modified module
# ---------------------------------------------------------------------------

# Normalisation basis for operator recognition.
# extract is subgraph-isomorphism: the design and patterns.v must live in the
# SAME gate basis or nothing matches.  SC-library cones are full of AOI/OAI/
# NAND/NOR; patterns.v is written in &|^~ and ?:.  'abc -g AND,OR,XOR,MUX'
# rewrites the cone into exactly that basis so the patterns have a chance to
# match.  XOR is kept in the basis so adder sum-bits survive.
NORM_BASIS     = "AND,OR,XOR,MUX"
# extract_fa is a dedicated, basis-independent full/half-adder pass; it is far
# more robust than structural extract for arithmetic, so we run it first to
# peel off the adder skeleton, then extract -map for the remaining motifs.
USE_EXTRACT_FA = False


def yosys_optimise(mod, mod_name, tmpdir, combo_id, run_extract):
    """
    Write single-module JSON, run (per the cofactor branch):
      opt_expr; opt_clean                     -- fold injected constants, kill ~(~x)
      [ abc -g {NORM_BASIS}; opt_clean        -- normalise to a uniform gate basis
        extract_fa                            -- robust adder/half-adder recognition
        extract -map patterns.v; opt_clean ]  -- structural motif recognition
    Return the simplified module dict.
    """
    design = {"creator": "decode_modes", "modules": {mod_name: mod}}
    in_json  = os.path.join(tmpdir, f"c{combo_id}_in.json")
    out_json = os.path.join(tmpdir, f"c{combo_id}_out.json")
    ys_path  = os.path.join(tmpdir, f"c{combo_id}.ys")
    log_path = os.path.join(tmpdir, f"c{combo_id}.log")

    with open(in_json, "w") as fh:
        json.dump(design, fh)

    # (1) 轻量 opt: 只折叠注入的常量、消掉双重否定，不做激进 AOI 重构
    #     （重构会把全加器塌成 AOI，反而让 extract 永远 miss）
    cmds = [
        f"read_json {in_json}",
        "opt_expr",
        "opt_clean",
    ]
    if run_extract:
        cmds += [
            # (2) techmap 归一基: 把 SC 库 AOI/OAI/NAND/NOR 拆成统一门基，
            #     让 design 与 patterns.v 处于同一基，extract 才可能命中
            f"abc -g {NORM_BASIS}",
            "opt_clean",
        ]
        if USE_EXTRACT_FA:
            # (3a) 专用全/半加器抽取: 基-无关，先吃掉算术骨架 → $fa 单元
            cmds.append("extract_fa")
        cmds += [
            # (3b) 结构模式库: mux / 进位 / 比较链等母题
            f"extract -map {PATTERNS_V}",
            "opt_clean",
        ]
    cmds.append(f"write_json {out_json}")

    with open(ys_path, "w") as fh:
        fh.write("\n".join(cmds) + "\n")
    with open(log_path, "w") as lh:
        r = subprocess.run([YOSYS, "-q", ys_path], stdout=lh, stderr=subprocess.STDOUT)

    if not os.path.exists(out_json):
        with open(log_path) as lh:
            sys.stderr.write(lh.read())
        sys.exit(f"ERROR: Yosys opt failed for combo {combo_id}")

    with open(out_json) as fh:
        d = json.load(fh)
    # prefer the named module; fall back to the first module in the file
    return d["modules"].get(mod_name) or next(iter(d["modules"].values()))


# ---------------------------------------------------------------------------
# Net / driver helpers
# ---------------------------------------------------------------------------

def build_net_map(module):
    """bit_id (int) → human-readable net name."""
    m = {}
    for name, info in module.get("netnames", {}).items():
        bits = info["bits"]
        if len(bits) == 1:
            m[bits[0]] = name
        else:
            for i, b in enumerate(bits):
                if isinstance(b, int):
                    m[b] = f"{name}[{i}]"
    return m


def build_driver_map(module):
    """bit_id (int) → (inst_name, output_pin)."""
    drv = {}
    for inst, cell in module.get("cells", {}).items():
        pd = cell.get("port_directions", {})
        for pin, bits in cell.get("connections", {}).items():
            if pd.get(pin) == "output":
                for b in bits:
                    if isinstance(b, int):
                        drv[b] = (inst, pin)
    for pname, pinfo in module.get("ports", {}).items():
        if pinfo["direction"] == "input":
            nm_bits = pinfo["bits"]
            for i, b in enumerate(nm_bits):
                if isinstance(b, int):
                    nm = pname if len(nm_bits) == 1 else f"{pname}[{i}]"
                    drv[b] = ("__PORT__", nm)
    return drv


def get_net_bit(module, net_name):
    """Return the bit-id (int) for a named net or port, or None."""
    base = net_name.split("[")[0]
    idx  = int(net_name.split("[")[1].rstrip("]")) if "[" in net_name else None
    for name, info in module.get("netnames", {}).items():
        if name == base:
            bits = info["bits"]
            k = idx if idx is not None else 0
            return bits[k] if k < len(bits) else None
    for pname, pinfo in module.get("ports", {}).items():
        if pname == base:
            bits = pinfo["bits"]
            k = idx if idx is not None else 0
            return bits[k] if k < len(bits) else None
    return None


def find_ff_d_bit(module, q_net_name, drivers, net_map):
    """Return (d_bit_id, ff_cell_type) for the FF whose Q drives q_net_name."""
    q_bit = get_net_bit(module, q_net_name)
    if q_bit is None:
        return None, None

    for inst, cell in module.get("cells", {}).items():
        ctype = cell["type"]
        if not any(ctype.startswith(p) for p in _FF_PREFIXES):
            continue
        pd    = cell.get("port_directions", {})
        conns = cell["connections"]
        # Yosys primitive FFs use "Q"; abstract $dff/$adff also use "Q"
        for qpin in ("Q", "q"):
            if qpin in conns and pd.get(qpin) == "output" and q_bit in conns[qpin]:
                for dpin in ("D", "d"):
                    if dpin in conns:
                        return conns[dpin][0], ctype

    # fallback: q_bit might be driven via a direct wire alias
    entry = drivers.get(q_bit)
    if entry and entry[0] != "__PORT__":
        inst, _ = entry
        cell  = module["cells"][inst]
        ctype = cell["type"]
        if any(ctype.startswith(p) for p in _FF_PREFIXES):
            for dpin in ("D", "d"):
                if dpin in cell["connections"]:
                    return cell["connections"][dpin][0], ctype

    return None, None


# ---------------------------------------------------------------------------
# Phase 2c: expression builder on the minimised netlist
# ---------------------------------------------------------------------------

_FF_PREFIXES = ("$_DFF", "$_ADFF", "$_ALDFF", "$_SDFF", "$adff", "$dff", "$sdff")


def build_expr(b, module, net_map, drivers, visited=None, depth=0):
    """
    Walk the combinational cone of bit b and return a compact expression string.
    After Yosys opt the cone is small, so depth rarely exceeds ~20.
    """
    if visited is None:
        visited = set()
    if depth > 300:
        return net_map.get(b, f"net_{b}") if isinstance(b, int) else str(b)

    # Yosys constant literals
    if b == "0":      return "1'b0"
    if b == "1":      return "1'b1"
    if b in ("x", "z"): return "1'bx"
    if not isinstance(b, int):
        return str(b)

    if b in visited:
        return net_map.get(b, f"net_{b}")
    visited = visited | {b}

    entry = drivers.get(b)
    if entry is None:
        return net_map.get(b, f"net_{b}")

    inst, drv_pin = entry
    if inst == "__PORT__":
        return drv_pin

    cell  = module["cells"][inst]
    ctype = cell["type"]
    conns = cell["connections"]

    def inp(pin, idx=0):
        bits_ = conns.get(pin, ["x"])
        bval  = bits_[idx] if idx < len(bits_) else "x"
        return build_expr(bval, module, net_map, drivers, visited, depth + 1)

    # ── Yosys primitive gates ──────────────────────────────────────────────
    if ctype in ("$not",    "$_NOT_"):    return f"~{inp('A')}"
    if ctype in ("$buf",    "$_BUF_"):    return inp("A")
    if ctype in ("$and",    "$_AND_"):    return f"({inp('A')} & {inp('B')})"
    if ctype in ("$or",     "$_OR_"):     return f"({inp('A')} | {inp('B')})"
    if ctype in ("$xor",    "$_XOR_"):    return f"({inp('A')} ^ {inp('B')})"
    if ctype in ("$xnor",   "$_XNOR_"):   return f"~({inp('A')} ^ {inp('B')})"
    if ctype in ("$nand",   "$_NAND_"):   return f"~({inp('A')} & {inp('B')})"
    if ctype in ("$nor",    "$_NOR_"):    return f"~({inp('A')} | {inp('B')})"
    if ctype in ("$mux",    "$_MUX_"):    return f"({inp('S')} ? {inp('B')} : {inp('A')})"
    if ctype in ("$nmux",   "$_NMUX_"):   return f"~({inp('S')} ? {inp('B')} : {inp('A')})"
    if ctype == "$_ANDNOT_":             return f"({inp('A')} & ~{inp('B')})"
    if ctype == "$_ORNOT_":              return f"({inp('A')} | ~{inp('B')})"
    if ctype == "$_AOI3_":               return f"~(({inp('A')} & {inp('B')}) | {inp('C')})"
    if ctype == "$_OAI3_":               return f"~(({inp('A')} | {inp('B')}) & {inp('C')})"
    if ctype == "$_AOI4_":               return f"~(({inp('A')} & {inp('B')}) | ({inp('C')} & {inp('D')}))"
    if ctype == "$_OAI4_":               return f"~(({inp('A')} | {inp('B')}) & ({inp('C')} | {inp('D')}))"
    if ctype in ("$reduce_and", "$reduce_or", "$reduce_xor", "$reduce_bool"):
        return inp("A")
    if ctype == "$logic_not":            return f"~{inp('A')}"

    # ── extract_fa output: $fa full-adder cell (Y=sum, X=carry) ───────────
    if ctype == "$fa":
        # Yosys $fa: Y = A ^ B ^ C ; X = maj(A,B,C)
        if drv_pin == "Y": return f"({inp('A')} ^ {inp('B')} ^ {inp('C')})"
        if drv_pin == "X": return f"(({inp('A')}&{inp('B')})|({inp('A')}&{inp('C')})|({inp('B')}&{inp('C')}))"

    # ── Recognised operator patterns (from extract -map patterns.v) ────────
    if ctype == "full_adder":
        if drv_pin == "SUM": return f"({inp('A')} ^ {inp('B')} ^ {inp('CI')})"
        if drv_pin == "CO":  return f"(({inp('A')}&{inp('B')})|({inp('A')}&{inp('CI')})|({inp('B')}&{inp('CI')}))"
    if ctype == "half_adder":
        if drv_pin == "SUM": return f"({inp('A')} ^ {inp('B')})"
        if drv_pin == "CO":  return f"({inp('A')} & {inp('B')})"
    if ctype == "incr_bit":
        if drv_pin == "SUM": return f"({inp('A')} ^ {inp('CI')})"
        if drv_pin == "CO":  return f"({inp('A')} & {inp('CI')})"
    if ctype == "carry_cell":
        return f"(({inp('A')}&{inp('B')})|({inp('A')}&{inp('CI')})|({inp('B')}&{inp('CI')}))"
    if ctype == "carry_cmp_seed":  return f"({inp('S')} & {inp('Q')})"
    if ctype == "carry_cmp_prop":
        return f"(({inp('S')}&{inp('Q')})|({inp('S')}&{inp('CI')})|({inp('Q')}&{inp('CI')}))"
    if ctype == "xor3_cell":   return f"({inp('A')} ^ {inp('B')} ^ {inp('C')})"
    if ctype == "xnor3_cell":  return f"~({inp('A')} ^ {inp('B')} ^ {inp('C')})"
    if ctype == "mux2":        return f"({inp('S')} ? {inp('D1')} : {inp('D0')})"

    # ── Flip-flops: Q is a sequential state atom ───────────────────────────
    if any(ctype.startswith(p) for p in _FF_PREFIXES):
        return net_map.get(b, f"net_{b}")

    # ── Unknown cell: return opaque net name ───────────────────────────────
    return net_map.get(b, f"{ctype}_{inst}_{drv_pin}")


# ---------------------------------------------------------------------------
# Lightweight operator recognition
# ---------------------------------------------------------------------------

def compute_fanout(module):
    """bit_id -> number of cell INPUT pins that reference it."""
    from collections import Counter
    f = Counter()
    for cell in module.get("cells", {}).values():
        pd = cell.get("port_directions", {})
        for pin, bits in cell.get("connections", {}).items():
            if pd.get(pin) == "input":
                for b in bits:
                    if isinstance(b, int):
                        f[b] += 1
    return f


def build_d_expr(d_bit, module, net_map, drivers, share_threshold=2):
    """
    Like build_expr, but emits any reconvergent (fanout>=threshold) internal
    node as a named wire instead of re-inlining it.  This turns the
    tree-exponential blowup (the 600KB blob) into a linear DAG of wire defs.

    Returns (defs, top_expr) where defs is a list of (wire_name, rhs_expr).
    """
    fanout = compute_fanout(module)
    defs, named = [], {}

    def rec(b, depth=0):
        if b == "0":      return "1'b0"
        if b == "1":      return "1'b1"
        if b in ("x", "z"): return "1'bx"
        if not isinstance(b, int):
            return str(b)
        if b in named:                       # already shared -> reference it
            return named[b]
        entry = drivers.get(b)
        if entry is None:
            return net_map.get(b, f"net_{b}")
        inst, drv_pin = entry
        if inst == "__PORT__":
            return drv_pin
        ctype = module["cells"][inst]["type"]
        if any(ctype.startswith(p) for p in _FF_PREFIXES):
            return net_map.get(b, f"net_{b}")    # FF Q is a state boundary
        # reuse build_expr's full cell-type dispatch for the RHS by calling it
        # one level deep with a recursion that routes back through rec()
        e = _cell_rhs(b, inst, drv_pin, module, net_map, drivers,
                      lambda x: rec(x, depth + 1))
        if e is None:
            return net_map.get(b, f"net_{b}")
        if fanout.get(b, 0) >= share_threshold:
            nm = net_map.get(b, f"net_{b}")
            wname = "w_" + re.sub(r"[\[\].]", "_", nm) if not nm.startswith("net_") else f"w{b}"
            named[b] = wname
            defs.append((wname, e))
            return wname
        return e

    top = rec(d_bit)
    return defs, top


def _cell_rhs(b, inst, drv_pin, module, net_map, drivers, recf):
    """Compute the RHS expression string for one cell output, using recf for inputs.
    Mirrors build_expr's cell-type table but with a single return path."""
    cell  = module["cells"][inst]
    ctype = cell["type"]
    conns = cell["connections"]
    def inp(pin, idx=0):
        bits_ = conns.get(pin, ["x"])
        return recf(bits_[idx] if idx < len(bits_) else "x")
    table_unary  = {"$not": "~{A}", "$_NOT_": "~{A}", "$logic_not": "~{A}"}
    if ctype in ("$buf", "$_BUF_", "$reduce_and", "$reduce_or", "$reduce_xor", "$reduce_bool"):
        return inp("A")
    if ctype in table_unary:               return f"~{inp('A')}"
    if ctype in ("$and", "$_AND_"):        return f"({inp('A')} & {inp('B')})"
    if ctype in ("$or",  "$_OR_"):         return f"({inp('A')} | {inp('B')})"
    if ctype in ("$xor", "$_XOR_"):        return f"({inp('A')} ^ {inp('B')})"
    if ctype in ("$xnor","$_XNOR_"):       return f"~({inp('A')} ^ {inp('B')})"
    if ctype in ("$nand","$_NAND_"):       return f"~({inp('A')} & {inp('B')})"
    if ctype in ("$nor", "$_NOR_"):        return f"~({inp('A')} | {inp('B')})"
    if ctype in ("$mux", "$_MUX_"):        return f"({inp('S')} ? {inp('B')} : {inp('A')})"
    if ctype in ("$nmux","$_NMUX_"):       return f"~({inp('S')} ? {inp('B')} : {inp('A')})"
    if ctype == "$_ANDNOT_":               return f"({inp('A')} & ~{inp('B')})"
    if ctype == "$_ORNOT_":                return f"({inp('A')} | ~{inp('B')})"
    if ctype == "$_AOI3_":                 return f"~(({inp('A')} & {inp('B')}) | {inp('C')})"
    if ctype == "$_OAI3_":                 return f"~(({inp('A')} | {inp('B')}) & {inp('C')})"
    if ctype == "$_AOI4_":                 return f"~(({inp('A')} & {inp('B')}) | ({inp('C')} & {inp('D')}))"
    if ctype == "$_OAI4_":                 return f"~(({inp('A')} | {inp('B')}) & ({inp('C')} | {inp('D')}))"
    if ctype == "$fa":
        if drv_pin == "Y": return f"({inp('A')} ^ {inp('B')} ^ {inp('C')})"
        if drv_pin == "X": return f"(({inp('A')}&{inp('B')})|({inp('A')}&{inp('C')})|({inp('B')}&{inp('C')}))"
    if ctype == "full_adder":
        if drv_pin == "SUM": return f"({inp('A')} ^ {inp('B')} ^ {inp('CI')})"
        if drv_pin == "CO":  return f"(({inp('A')}&{inp('B')})|({inp('A')}&{inp('CI')})|({inp('B')}&{inp('CI')}))"
    if ctype == "half_adder":
        if drv_pin == "SUM": return f"({inp('A')} ^ {inp('B')})"
        if drv_pin == "CO":  return f"({inp('A')} & {inp('B')})"
    if ctype == "incr_bit":
        if drv_pin == "SUM": return f"({inp('A')} ^ {inp('CI')})"
        if drv_pin == "CO":  return f"({inp('A')} & {inp('CI')})"
    if ctype == "carry_cell":
        return f"(({inp('A')}&{inp('B')})|({inp('A')}&{inp('CI')})|({inp('B')}&{inp('CI')}))"
    if ctype == "mux2":      return f"({inp('S')} ? {inp('D1')} : {inp('D0')})"
    return None


def format_modes_expr(defs, top):
    """Render (defs, top) into a compact, readable string for the mode table."""
    if not defs:
        return top
    lines = [f"wire {w} = {e};" for w, e in defs]
    lines.append(f"=> {top}")
    return "\n".join(lines)


def classify_expr(expr, q_name):
    """
    Return a human-readable label or the original expr unchanged.
    Keeps the expr short; word-level grouping is done in Phase C.
    """
    e = expr.strip()
    if e == q_name:
        return f"{q_name}  # HOLD"
    if e in ("1'b0", "1'b1"):
        return e
    return expr


# ---------------------------------------------------------------------------
# op_hypotheses.json accumulation
# ---------------------------------------------------------------------------

def expr_signature(expr):
    """
    Cheap motif fingerprint for an unrecognised boolean expr, so grow_patterns
    can cluster branches: '7 branches share this signature → write 1 pattern'.
    Returns dict with operator counts, leaf inputs, and a canonical key.
    """
    ops = {
        "and":   expr.count("&"),
        "or":    expr.count("|"),
        "xor":   expr.count("^"),
        "not":   expr.count("~"),
        "mux":   expr.count("?"),
    }
    # leaf identifiers: net/port names (strip operators, constants, parens)
    leaves = sorted(set(re.findall(r"[A-Za-z_]\w*(?:\[\d+\])?", expr)) -
                    {"1'b0", "1'b1", "1'bx"})
    # canonical signature key: operator histogram + leaf arity (not leaf names,
    # so structurally-identical motifs on different nets cluster together)
    key = f"and{ops['and']}_or{ops['or']}_xor{ops['xor']}_not{ops['not']}_mux{ops['mux']}_in{len(leaves)}"
    return {"ops": ops, "inputs": leaves, "sig": key}


def update_hypotheses(hypo_path, ff_name, cond, expr):
    """Append an unrecognised expression to op_hypotheses.json (rich schema)."""
    hyps = {}
    if os.path.exists(hypo_path):
        try:
            with open(hypo_path) as fh:
                hyps = json.load(fh)
        except Exception:
            pass
    key = f"{ff_name}:{cond}"
    sig = expr_signature(expr)
    hyps[key] = {
        "ff":         ff_name,
        "cond":       cond,
        "raw_expr":   expr,
        "signature":  sig["sig"],     # motif cluster key (grow_patterns groups on this)
        "inputs":     sig["inputs"],  # leaf nets feeding this branch
        "ops":        sig["ops"],     # operator histogram
        "status":     "UNKNOWN",      # UNKNOWN -> RESOLVED_PATTERN | RESOLVED_OP
        "proposed_op": "",            # LLM fills e.g. "MI1_QT + 1"  (then grow_patterns --verify)
        "bit":        None,           # which bit of proposed_op this branch is
    }
    with open(hypo_path, "w") as fh:
        json.dump(hyps, fh, indent=2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Filter out whitespace-only tokens that bash injects when "\ " (backslash-space)
    # is used instead of "\"<newline>" for multi-line commands.  No legitimate
    # argument to this script is pure whitespace, so filtering is always safe.
    cleaned = [a for a in sys.argv[1:] if a.strip()]
    if len(cleaned) != len(sys.argv) - 1:
        dropped = [repr(a) for a in sys.argv[1:] if not a.strip()]
        print(f"[warn] stripped {len(dropped)} whitespace-only argv token(s): "
              f"{dropped}  (caused by trailing spaces after '\\' in shell)", file=sys.stderr)

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--netlist",      required=True,  metavar="NETLIST")
    ap.add_argument("--lib",          action="append", default=[], metavar="LIB")
    ap.add_argument("--top",          required=True,  metavar="TOP")
    ap.add_argument("--ff",           required=True,  metavar="FF",
                    help="Q-net name of target FF")
    ap.add_argument("--ctrl",         required=True,  metavar="CTRL",
                    help="Comma-separated control net names")
    ap.add_argument("--out",          required=True,  metavar="OUT")
    ap.add_argument("--hypo",         default=None,   metavar="HYPO",
                    help="Path to op_hypotheses.json for unrecognised operators")
    ap.add_argument("--no-extract",   action="store_true",
                    help="Skip 'extract -map patterns.v' step")
    args = ap.parse_args(cleaned)

    ctrl_names  = [c.strip() for c in args.ctrl.split(",") if c.strip()]
    run_extract = (not args.no_extract) and os.path.exists(PATTERNS_V)

    with tempfile.TemporaryDirectory() as tmpdir:

        # ── Phase 1: flatten once ──────────────────────────────────────────
        print(f"[flatten] {args.top} ...", flush=True)
        design = flatten_netlist(args.netlist, args.lib, args.top, tmpdir)
        mod = design["modules"].get(args.top)
        if mod is None:
            sys.exit(f"ERROR: module '{args.top}' not found after flatten")

        flat_net_map = build_net_map(mod)
        flat_drivers = build_driver_map(mod)

        # Verify the FF exists before doing any cofactoring
        d_bit_check, ff_type = find_ff_d_bit(mod, args.ff, flat_drivers, flat_net_map)
        if d_bit_check is None:
            sys.exit(f"ERROR: FF '{args.ff}' not found in flattened design")
        print(f"[ff] {args.ff}  type={ff_type}", flush=True)

        # Resolve ctrl signals → bit IDs in the flat netlist
        ctrl_bits = {}
        for c in ctrl_names:
            b = get_net_bit(mod, c)
            if b is None:
                print(f"  WARNING: ctrl '{c}' not found — skipping", file=sys.stderr)
            else:
                ctrl_bits[c] = b
        valid_ctrl = list(ctrl_bits.keys())
        valid_bits = [ctrl_bits[c] for c in valid_ctrl]
        n          = len(valid_ctrl)

        # ── Phase 2: per-combo cofactor → Yosys opt → expression ──────────
        modes   = []
        total   = 2 ** n
        for i, combo in enumerate(itertools.product([0, 1], repeat=n)):
            const_map = {bit: val for bit, val in zip(valid_bits, combo)}
            cond      = ",".join(f"{c}={v}" for c, v in zip(valid_ctrl, combo))
            print(f"[cofactor {i+1}/{total}] {cond}", flush=True)

            # a) inject constants
            mod_c = inject_constants(mod, const_map)

            # b) Yosys: opt -full -purge; opt_clean; [extract; opt_clean]
            mod_opt = yosys_optimise(mod_c, args.top, tmpdir, i, run_extract)

            # c) rebuild maps for the optimised netlist (bit IDs may change)
            nm  = build_net_map(mod_opt)
            drv = build_driver_map(mod_opt)

            # d) find FF's D input in the optimised netlist
            d_bit, _ = find_ff_d_bit(mod_opt, args.ff, drv, nm)

            if d_bit is None:
                # FF was optimised away (Q became unused after constant folding)
                q_bit = get_net_bit(mod_opt, args.ff)
                if q_bit:
                    defs, top = build_d_expr(q_bit, mod_opt, nm, drv)
                else:
                    defs, top = [], "1'bx"
            else:
                # e) walk the cone with node-sharing (no exponential blowup)
                defs, top = build_d_expr(d_bit, mod_opt, nm, drv)

            top  = classify_expr(top, args.ff)
            expr = format_modes_expr(defs, top)

            # record unrecognised complex expressions for Phase C hypothesis work
            if args.hypo and not re.match(r"^(1'b[01]|[A-Za-z_]\w*(\[\d+\])?(  # \w+)?)$", top):
                update_hypotheses(args.hypo, args.ff, cond, expr)

            modes.append({"cond": cond, "expr": expr})

    # ── Phase 3: emit mode table ───────────────────────────────────────────
    result = {
        "ff":      args.ff,
        "ff_type": ff_type,
        "ctrl":    valid_ctrl,
        "modes":   modes,
    }

    os.makedirs(os.path.dirname(args.out) if os.path.dirname(args.out) else ".", exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(result, fh, indent=2)

    print(f"\n[done] {len(modes)} modes → {args.out}")
    for m in modes:
        print(f"  {m['cond']:45s}  {m['expr']}")


if __name__ == "__main__":
    main()
