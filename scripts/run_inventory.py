#!/usr/bin/env python3
"""
run_inventory.py -- run yosys on a gate-level netlist and emit normalized inventory.json
Usage: python scripts/run_inventory.py --netlist impl.v --lib SC_LIB_SCH.v --top COUNT_12BX2 --out inventory.json
"""
import argparse, json, subprocess, sys, tempfile, os, re

# Cell types recognized as flip-flops and their pin semantics
FF_CELLS = {
    # name_pattern: (cp_pin, cdn_pin, sdn_pin, q_pin, d0_pin, d1_pin, s_pin, inverted)
    "SC_MFC": ("CP", "CDN", None,  "Q",  "D0", "D1", "S",  False),
    "SC_MFC_140_80S1": ("CP", "CDN", None, "Q", "D0", "D1", "S", True),
    "SC_MFS_140_80":   ("CP", "CDN", None, "Q", "D0", "D1", "S", True),
    "SC_DFC": ("CP", "CDN", None,  "Q",  "D",  None, None, False),
    "SC_DFB": ("CP", "CDN", "SDN", "Q",  "D",  None, None, False),
    "SC_MFB": ("CP", "CDN", "SDN", "Q",  "D0", "D1", "S",  False),
}

def cell_is_ff(cell_type):
    for pat in FF_CELLS:
        if cell_type.startswith(pat):
            return pat
    return None


def bits_to_net(bits, netnames_map):
    """Resolve a yosys bits list to a net name string."""
    if len(bits) == 1:
        b = bits[0]
        if isinstance(b, int):
            return netnames_map.get(b, f"bit{b}")
        return str(b)
    parts = []
    for b in bits:
        if isinstance(b, int):
            parts.append(netnames_map.get(b, f"bit{b}"))
        else:
            parts.append(str(b))
    return ",".join(parts)


def build_bit_to_name(module_data):
    """Build bit-id → net-name (with index) mapping from yosys JSON module."""
    mapping = {}
    netnames = module_data.get("netnames", {})
    for name, info in netnames.items():
        bits = info["bits"]
        if len(bits) == 1:
            mapping[bits[0]] = name
        else:
            for i, b in enumerate(bits):
                mapping[b] = f"{name}[{i}]"
    return mapping


def run_yosys(netlist, lib, top, tmpdir):
    ys = []
    if lib:
        for lf in (lib if isinstance(lib, list) else [lib]):
            ys.append(f"read_verilog -lib {lf}")
    ys.append(f"read_verilog {netlist}")
    ys.append(f"hierarchy -top {top} -check")
    ys.append("proc")
    ys.append("opt_clean")
    json_out = os.path.join(tmpdir, "design.json")
    ys.append(f"write_json {json_out}")
    ys.append("stat")
    ys_path = os.path.join(tmpdir, "inventory.ys")
    with open(ys_path, "w") as f:
        f.write("\n".join(ys) + "\n")
    log_path = os.path.join(tmpdir, "inventory_yosys.log")
    with open(log_path, "w") as lf:
        result = subprocess.run(
            ["yosys", "-q", ys_path],
            stdout=lf, stderr=subprocess.STDOUT
        )
    if result.returncode != 0:
        with open(log_path) as lf:
            print(lf.read(), file=sys.stderr)
        sys.exit(f"ERROR: yosys failed (exit {result.returncode})")
    with open(json_out) as f:
        return json.load(f), log_path


def parse_ports(module_data):
    ports = []
    for name, info in module_data.get("ports", {}).items():
        bits = info["bits"]
        ports.append({"name": name, "dir": info["direction"], "width": len(bits)})
    return ports


def parse_dffs(module_data, bit_map):
    dffs = []
    cells = module_data.get("cells", {})
    for inst, cell in cells.items():
        ctype = cell["type"]
        pat = cell_is_ff(ctype)
        if pat is None:
            continue
        cp_pin, cdn_pin, sdn_pin, q_pin, d0_pin, d1_pin, s_pin, inverted = FF_CELLS[pat]
        conns = cell.get("connections", {})

        def resolve(pin):
            if pin and pin in conns:
                return bits_to_net(conns[pin], bit_map)
            return None

        entry = {
            "inst": inst,
            "cell_type": ctype,
            "clk": resolve(cp_pin),
            "rst": resolve(cdn_pin),
            "q_net": resolve(q_pin),
            "d_net": resolve(d0_pin) if d0_pin else resolve("D"),
            "inverted": inverted,
        }
        if d1_pin and d1_pin in conns:
            entry["d1_net"] = resolve(d1_pin)
        if s_pin and s_pin in conns:
            entry["s_net"] = resolve(s_pin)
        if sdn_pin and sdn_pin in conns:
            entry["sdn_net"] = resolve(sdn_pin)
        dffs.append(entry)
    return dffs


def compute_cones(module_data, bit_map, dffs):
    """For each FF q_net, collect immediate fanin net names (combinational drivers)."""
    cells = module_data.get("cells", {})
    # Build bit → driving cell map
    bit_driven_by = {}  # bit_id → (cell_inst, pin)
    for inst, cell in cells.items():
        for pin, bits in cell.get("connections", {}).items():
            # Output pins drive nets
            port_dirs = cell.get("port_directions", {})
            if port_dirs.get(pin) == "output":
                for b in bits:
                    if isinstance(b, int):
                        bit_driven_by[b] = inst

    cones = []
    for dff in dffs:
        q = dff["q_net"]
        # Find bits of q
        netnames = module_data.get("netnames", {})
        q_base = q.split("[")[0]
        fanin = set()
        if q_base in netnames:
            q_bits = netnames[q_base]["bits"]
        else:
            q_bits = []
        for b in q_bits:
            drv = bit_driven_by.get(b)
            if drv:
                # Collect all input nets of the driving cell
                drv_cell = cells[drv]
                for pin, pbits in drv_cell.get("connections", {}).items():
                    pd = drv_cell.get("port_directions", {}).get(pin)
                    if pd == "input":
                        for pb in pbits:
                            nm = bit_map.get(pb)
                            if nm:
                                fanin.add(nm)
        cones.append({"q_net": q, "fanin_nets": sorted(fanin)})
    return cones


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--netlist", required=True)
    ap.add_argument("--lib", "--models", dest="lib", action="append")
    ap.add_argument("--top", required=True)
    ap.add_argument("--out", default="inventory.json")
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmpdir:
        design, log_path = run_yosys(args.netlist, args.lib, args.top, tmpdir)

    if args.top not in design.get("modules", {}):
        sys.exit(f"ERROR: module '{args.top}' not found in design")

    mod = design["modules"][args.top]
    bit_map = build_bit_to_name(mod)
    ports = parse_ports(mod)
    dffs = parse_dffs(mod, bit_map)
    cones = compute_cones(mod, bit_map, dffs)

    result = {
        "top": args.top,
        "ports": ports,
        "dffs": dffs,
        "cones": cones,
    }
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Inventory written to {args.out}: {len(ports)} ports, {len(dffs)} DFFs, {len(cones)} cones")


if __name__ == "__main__":
    main()
