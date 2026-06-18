#!/usr/bin/env python3
"""
decode_modes.py -- Shannon cofactor a FF's D-input cone to produce a mode table.

Uses Yosys to flatten the netlist to primitive cells, then Python-side
symbolic cofactoring: for each combo of ctrl signal values, substitute
constants into the expression tree and simplify.

Usage:
  python scripts/decode_modes.py \
      --netlist impl.v --lib SC_LIB_SCH.v --top COUNT_12BX2 \
      --ff MI1_QT[0] \
      --ctrl "X8710_Z,SET2,HOLD0[2],COUNT1N" \
      --out modes/a0.json
"""
import argparse, json, os, re, subprocess, sys, tempfile, itertools

YOSYS = "yosys"

# ---------------------------------------------------------------------------
# Yosys: flatten netlist to primitives
# ---------------------------------------------------------------------------
def run_yosys_flatten(netlist, lib_list, top, tmpdir):
    """Read netlist (WITH cell expansion, not -lib), flatten, write JSON."""
    ys = []
    for lf in lib_list:
        ys.append(f"read_verilog {lf}")   # expand cells so we get primitives
    ys.append(f"read_verilog {netlist}")
    ys.append(f"hierarchy -top {top} -check")
    ys.append("proc")
    ys.append("flatten")
    ys.append("opt_clean")
    json_out = os.path.join(tmpdir, "flat.json")
    ys.append(f"write_json {json_out}")
    ys_path = os.path.join(tmpdir, "flat.ys")
    log_path = os.path.join(tmpdir, "flat.log")
    with open(ys_path, "w") as f:
        f.write("\n".join(ys) + "\n")
    with open(log_path, "w") as lf:
        subprocess.run([YOSYS, "-q", ys_path], stdout=lf, stderr=subprocess.STDOUT)
    if not os.path.exists(json_out):
        with open(log_path) as lf:
            print(lf.read(), file=sys.stderr)
        sys.exit("ERROR: Yosys flatten failed; see log above")
    with open(json_out) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Build lookup maps from Yosys JSON module
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
    """bit_id (int) → (inst_name, output_pin) for the cell/port that drives it."""
    drivers = {}
    # Cells: output pins drive nets
    for inst, cell in module.get("cells", {}).items():
        pd = cell.get("port_directions", {})
        for pin, bits in cell.get("connections", {}).items():
            if pd.get(pin) == "output":
                for b in bits:
                    if isinstance(b, int):
                        drivers[b] = (inst, pin)
    # Input ports of the module are sources (not driven by any cell)
    for pname, pinfo in module.get("ports", {}).items():
        if pinfo["direction"] == "input":
            for i, b in enumerate(pinfo["bits"]):
                if isinstance(b, int):
                    nm = pname if len(pinfo["bits"]) == 1 else f"{pname}[{i}]"
                    drivers[b] = ("__PORT__", nm)
    return drivers


def get_net_bit(module, net_name):
    """Return the bit-id (int) for a named net or port."""
    base = net_name.split("[")[0]
    idx = None
    if "[" in net_name:
        idx = int(net_name.split("[")[1].rstrip("]"))

    for name, info in module.get("netnames", {}).items():
        if name == base:
            bits = info["bits"]
            if idx is None:
                return bits[0] if bits else None
            if idx < len(bits):
                return bits[idx]

    for pname, pinfo in module.get("ports", {}).items():
        if pname == base:
            bits = pinfo["bits"]
            if idx is None:
                return bits[0] if bits else None
            if idx < len(bits):
                return bits[idx]
    return None


def find_ff_d_bit(module, q_net_name, net_map, drivers):
    """
    Find the D-input bit of the DFF whose Q output corresponds to q_net_name.
    Returns (d_bit_id, ff_cell_type).
    """
    # Resolve q_net_name to a bit ID
    q_bit = get_net_bit(module, q_net_name)
    if q_bit is None:
        # Maybe the Q net is an output port driven by the FF Q
        for pname, pinfo in module.get("ports", {}).items():
            if pname == q_net_name.split("[")[0]:
                idx = int(q_net_name.split("[")[1].rstrip("]")) if "[" in q_net_name else 0
                bits = pinfo["bits"]
                if idx < len(bits):
                    q_bit = bits[idx]
                    break

    if q_bit is None:
        sys.exit(f"ERROR: Q net '{q_net_name}' not found in design")

    # Scan cells for a DFF whose Q pin drives q_bit
    for inst, cell in module.get("cells", {}).items():
        ctype = cell["type"]
        if not (ctype.startswith("$_DFF") or ctype.startswith("$adff")
                or ctype.startswith("$dff")):
            continue
        pd = cell.get("port_directions", {})
        conns = cell["connections"]
        for pin, bits in conns.items():
            if pd.get(pin) == "output" and isinstance(bits[0] if bits else None, int) and q_bit in bits:
                # Found the FF; return its D input
                for dpin in ["D", "d"]:
                    if dpin in conns and pd.get(dpin) == "input":
                        return conns[dpin][0], ctype
        # Also check: Q pin might be named differently
        for qpin in ["Q", "q"]:
            if qpin in conns and pd.get(qpin) == "output":
                if q_bit in conns[qpin]:
                    for dpin in ["D", "d"]:
                        if dpin in conns and pd.get(dpin) == "input":
                            return conns[dpin][0], ctype

    # Fallback: q_bit might be driven by a wire alias, check the driver
    drv = drivers.get(q_bit)
    if drv and drv[0] != "__PORT__":
        inst, pin = drv
        cell = module["cells"][inst]
        ctype = cell["type"]
        if ctype.startswith("$_DFF") or ctype.startswith("$adff"):
            for dpin in ["D", "d"]:
                if dpin in cell["connections"]:
                    return cell["connections"][dpin][0], ctype

    sys.exit(f"ERROR: No DFF found with Q='{q_net_name}' (bit_id={q_bit})")


# ---------------------------------------------------------------------------
# Symbolic expression builder with constant substitution
# ---------------------------------------------------------------------------
CONST_0 = "1'b0"
CONST_1 = "1'b1"

def build_expr(b, module, net_map, drivers, constants, visited=None, depth=0):
    """
    Recursively build an expression string for bit b,
    substituting constants for bits in `constants` dict.
    """
    if visited is None:
        visited = set()
    if depth > 120:
        return net_map.get(b, f"net_{b}") if isinstance(b, int) else str(b)

    # Literal constants in the JSON
    if b == "0":   return CONST_0
    if b == "1":   return CONST_1
    if b in ("x", "z"):  return "1'bx"
    if not isinstance(b, int):
        return str(b)

    # Control signal constant override
    if b in constants:
        return CONST_1 if constants[b] else CONST_0

    # Cycle guard
    if b in visited:
        return net_map.get(b, f"net_{b}")
    visited = visited | {b}

    drv = drivers.get(b)
    if drv is None:
        return net_map.get(b, f"net_{b}")

    inst, drv_pin = drv

    # Module input port: just use its name
    if inst == "__PORT__":
        return drv_pin

    cell = module["cells"][inst]
    ctype = cell["type"]
    conns = cell["connections"]

    def inp(pin):
        bits_ = conns.get(pin, ["x"])
        return build_expr(bits_[0], module, net_map, drivers, constants, visited, depth+1)

    # ---- Yosys internal cells (from proc, before techmap) ----
    if ctype in ("$not", "$_NOT_"):    return f"~({inp('A')})"
    if ctype in ("$and", "$_AND_"):    return f"({inp('A')} & {inp('B')})"
    if ctype in ("$or",  "$_OR_"):     return f"({inp('A')} | {inp('B')})"
    if ctype in ("$xor", "$_XOR_"):    return f"({inp('A')} ^ {inp('B')})"
    if ctype in ("$xnor","$_XNOR_"):   return f"~({inp('A')} ^ {inp('B')})"
    if ctype in ("$mux", "$_MUX_"):    return f"({inp('S')} ? {inp('B')} : {inp('A')})"
    if ctype in ("$nmux","$_NMUX_"):   return f"~({inp('S')} ? {inp('B')} : {inp('A')})"
    if ctype in ("$nand","$_NAND_"):   return f"~({inp('A')} & {inp('B')})"
    if ctype in ("$nor", "$_NOR_"):    return f"~({inp('A')} | {inp('B')})"
    if ctype == "$_ANDNOT_":           return f"({inp('A')} & ~({inp('B')}))"
    if ctype == "$_ORNOT_":            return f"({inp('A')} | ~({inp('B')}))"
    if ctype == "$_AOI3_":             return f"~(({inp('A')} & {inp('B')}) | {inp('C')})"
    if ctype == "$_OAI3_":             return f"~(({inp('A')} | {inp('B')}) & {inp('C')})"
    if ctype == "$_AOI4_":             return f"~(({inp('A')} & {inp('B')}) | ({inp('C')} & {inp('D')}))"
    if ctype == "$_OAI4_":             return f"~(({inp('A')} | {inp('B')}) & ({inp('C')} | {inp('D')}))"
    if ctype in ("$buf", "$_BUF_"):    return inp("A")
    # Reduce/logic ops (single-bit output after opt)
    if ctype == "$reduce_and":         return inp("A")
    if ctype == "$reduce_or":          return inp("A")
    if ctype == "$reduce_xor":         return inp("A")
    if ctype == "$reduce_bool":        return inp("A")
    if ctype == "$logic_not":          return f"~({inp('A')})"

    # ---- Register cells: Q is a state boundary; return the net name ----
    if (ctype.startswith("$_DFF") or ctype.startswith("$adff")
            or ctype.startswith("$dff") or ctype.startswith("$sdff")):
        return net_map.get(b, f"net_{b}")

    # ---- Unknown: return net name as opaque atom ----
    return net_map.get(b, f"{ctype}_{b}")


# ---------------------------------------------------------------------------
# String-level constant folding
# ---------------------------------------------------------------------------
def fold_once(expr):
    """Apply one pass of constant-folding substitutions."""
    rules = [
        # MUX constant select
        (r"\(1'b1 \? ([^?:()]+) : [^?:()]+\)",         r"\1"),
        (r"\(1'b0 \? [^?:()]+ : ([^?:()]+)\)",          r"\1"),
        # AND with constant
        (r"\(1'b1 & ([^&|()]+)\)",   r"\1"),
        (r"\(([^&|()]+) & 1'b1\)",   r"\1"),
        (r"\(1'b0 & [^&|()]+\)",     "1'b0"),
        (r"\([^&|()]+ & 1'b0\)",     "1'b0"),
        # OR with constant
        (r"\(1'b1 \| [^&|()]+\)",    "1'b1"),
        (r"\([^&|()]+ \| 1'b1\)",    "1'b1"),
        (r"\(1'b0 \| ([^&|()]+)\)",  r"\1"),
        (r"\(([^&|()]+) \| 1'b0\)",  r"\1"),
        # NOT of constant
        (r"~\(1'b1\)",               "1'b0"),
        (r"~\(1'b0\)",               "1'b1"),
        # Redundant parens around constant
        (r"\(1'b0\)",                "1'b0"),
        (r"\(1'b1\)",                "1'b1"),
    ]
    for pat, rep in rules:
        expr = re.sub(pat, rep, expr)
    return expr


def simplify(expr, passes=20):
    for _ in range(passes):
        prev = expr
        expr = fold_once(expr)
        if expr == prev:
            break
    return expr


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--netlist", required=True)
    ap.add_argument("--lib",    action="append", default=[])
    ap.add_argument("--top",    required=True)
    ap.add_argument("--ff",     required=True, help="Q-net name of the target FF")
    ap.add_argument("--ctrl",   required=True,
                    help="Comma-separated control net names (e.g. 'SEL,SET2,HOLD')")
    ap.add_argument("--out",    required=True)
    args = ap.parse_args()

    ctrl_names = [c.strip() for c in args.ctrl.split(",") if c.strip()]

    with tempfile.TemporaryDirectory() as tmpdir:
        design = run_yosys_flatten(args.netlist, args.lib, args.top, tmpdir)

    mod = design["modules"].get(args.top)
    if mod is None:
        sys.exit(f"ERROR: module '{args.top}' not found in design JSON")

    net_map = build_net_map(mod)
    drivers = build_driver_map(mod)

    # Resolve D-input bit of the target FF
    d_bit, ff_type = find_ff_d_bit(mod, args.ff, net_map, drivers)

    # Resolve control net → bit_id
    ctrl_bits = {}
    for c in ctrl_names:
        b = get_net_bit(mod, c)
        if b is None:
            print(f"WARNING: control '{c}' not found in '{args.top}'; skipping",
                  file=sys.stderr)
        else:
            ctrl_bits[c] = b

    valid_ctrl = list(ctrl_bits.keys())
    valid_bits = [ctrl_bits[c] for c in valid_ctrl]
    n = len(valid_ctrl)

    modes = []
    for combo in itertools.product([0, 1], repeat=n):
        constants = {bit_id: val
                     for bit_id, val in zip(valid_bits, combo)}
        raw = build_expr(d_bit, mod, net_map, drivers, constants)
        expr = simplify(raw)
        cond = ",".join(f"{c}={v}" for c, v in zip(valid_ctrl, combo))
        modes.append({"cond": cond, "expr": expr})

    result = {
        "ff":    args.ff,
        "ff_type": ff_type,
        "ctrl":  valid_ctrl,
        "modes": modes,
    }

    os.makedirs(os.path.dirname(args.out) if os.path.dirname(args.out) else ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)

    print(f"decode_modes: FF='{args.ff}' ctrl={valid_ctrl} → {len(modes)} cofactors → {args.out}")


if __name__ == "__main__":
    main()
