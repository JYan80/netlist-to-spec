#!/usr/bin/env python3
"""
gen_structural.py — translate gate-level netlist to behavioral spec_structural.v
Usage: python3 scripts/gen_structural.py COUNT_12BX2/impl.v COUNT_12BX2/spec_structural.v
"""
import re, sys

CELL_BOOLEAN = {
    "SC_INV_140_60":      lambda p: [("ZN", f"~{p['A']}")],
    "SC_AND2_50_30":      lambda p: [("Z",  f"({p['A1']} & {p['A2']})")],
    "SC_AO22_140_80":     lambda p: [("Z",  f"(({p['B1']} & {p['B2']}) | ({p['A1']} & {p['A2']}))")],
    "SC_AOI22_E100_60":   lambda p: [("ZN", f"~(({p['A1']} & {p['A2']}) | ({p['B1']} & {p['B2']}))")],
    "SC_NAND2_70_40":     lambda p: [("ZN", f"~({p['A1']} & {p['A2']})")],
    "SC_OAI211_90_E60":   lambda p: [("ZN", f"~({p['B']} & {p['C']} & ({p['A1']} | {p['A2']}))")],
    "SC_OAI22_100_E80":   lambda p: [("ZN", f"~(({p['A1']} | {p['A2']}) & ({p['B1']} | {p['B2']}))")],
    "SC_XNOR3_140_E90":   lambda p: [("ZN", f"~(({p['A1']} ^ {p['A2']}) ^ {p['A3']})")],
    "SC_XOR2_E120_70":    lambda p: [("Z",  f"({p['A1']} ^ {p['A2']})")],
    "SC_XOR3_E140_90":    lambda p: [("Z",  f"(({p['A1']} ^ {p['A2']}) ^ {p['A3']})")],
    "SC_CARRY_140_80":    lambda p: [("CO", f"(({p['A']} & {p['B']}) | ({p['A']} & {p['CI']}) | ({p['B']} & {p['CI']}))")],
    "SC_HADD_140_80":     lambda p: [("SUM", f"({p['A']} ^ {p['B']})"), ("CO", f"({p['A']} & {p['B']})")],
}

SKIP_PINS = {"GS", "VS"}


def parse_portmap(portmap_str):
    d = {}
    for m in re.finditer(r'\.(\w+)\(([^)]*)\)', portmap_str):
        pin, net = m.group(1), m.group(2).strip()
        if pin not in SKIP_PINS:
            d[pin] = net
    return d


def parse_instances(verilog):
    pattern = re.compile(r'\b(SC_\w+)\s+(\w+)\s*\(([^;]+?)\)\s*;', re.DOTALL)
    for m in pattern.finditer(verilog):
        yield m.group(1), m.group(2), parse_portmap(m.group(3))


def extract_header(verilog):
    m = re.search(r'\b(SC_\w+)\s+\w+\s*\(', verilog)
    return verilog[:m.start()].rstrip() if m else verilog


def port_net_to_reg_name(net):
    """Convert a port bit like MI1_QT[0] to a safe reg name r_MI1_QT_0."""
    return "r_" + net.replace("[", "_").replace("]", "")


def main():
    src, dst = sys.argv[1], sys.argv[2]
    with open(src) as f:
        verilog = f.read()

    header = extract_header(verilog)

    # Collect output port nets to detect FF Q → output port connections
    # Scalar outputs: "output foo" → {'foo'}
    # Bus outputs: "output [H:L] foo" → {'foo[L]', 'foo[L+1]', ...}
    output_nets = set()
    for m in re.finditer(r'\boutput\s+(\w+)\s*[;,]', header):
        output_nets.add(m.group(1))
    for m in re.finditer(r'\boutput\s+\[(\d+):(\d+)\]\s+(\w+)', header):
        hi, lo, name = int(m.group(1)), int(m.group(2)), m.group(3)
        for i in range(lo, hi+1):
            output_nets.add(f"{name}[{i}]")

    # Collect FF data: net -> (cp, cdn, sel, d0, d1, inst)
    ff_data = {}   # q_net -> tuple
    comb_assigns = []

    for ctype, inst, pins in parse_instances(verilog):
        if ctype == "SC_MFC_140_80":
            q = pins["Q"]
            ff_data[q] = (pins["CP"], pins["CDN"], pins["S"], pins["D0"], pins["D1"], inst)
        elif ctype in CELL_BOOLEAN:
            for out_pin, expr in CELL_BOOLEAN[ctype](pins):
                net = pins[out_pin]
                comb_assigns.append((net, expr))
        else:
            print(f"WARNING: unhandled cell {ctype} inst {inst}", file=sys.stderr)

    # For FF Q nets that are output ports, map to internal reg names
    q_reg = {}  # q_net -> reg_name_in_spec
    output_port_assigns = []  # (output_net, reg_name) for FF→output connections
    for q in ff_data:
        if q in output_nets:
            rname = port_net_to_reg_name(q)
            q_reg[q] = rname
            output_port_assigns.append((q, rname))
        else:
            q_reg[q] = q

    # Build spec
    lines = []

    # Header — strip the conflicting internal wire declarations for output buses
    # (MI1_QT and MI1_SUM are outputs; we don't need the "wire" re-declarations)
    filtered_header_lines = []
    for line in header.split('\n'):
        # Drop internal wire decls for output buses; keep port decls
        if re.match(r'\s+wire\s+\[\d+:\d+\]\s+(MI1_QT|MI1_SUM)\s*;', line):
            continue
        filtered_header_lines.append(line)
    lines.extend(filtered_header_lines)
    lines.append("")

    lines.append("    // FF state registers")
    for q, (cp, cdn, s, d0, d1, inst) in ff_data.items():
        rname = q_reg[q]
        lines.append(f"    reg {rname};")
    lines.append("")

    lines.append("    // FF output → module output port")
    for out_net, rname in output_port_assigns:
        lines.append(f"    assign {out_net} = {rname};")
    lines.append("")

    lines.append("    // Combinational logic")
    for net, expr in comb_assigns:
        lines.append(f"    assign {net} = {expr};")
    lines.append("")

    lines.append("    // Sequential logic (SC_MFC: Q <= S?D1:D0, async low reset)")
    for q, (cp, cdn, s, d0, d1, inst) in ff_data.items():
        rname = q_reg[q]
        # Replace any reference to q inside d0/d1/s that uses the original q net name
        # (No self-references expected, but substitute for safety)
        lines.append(f"    always @(posedge {cp} or negedge {cdn}) begin")
        lines.append(f"        if (!{cdn}) {rname} <= 1'b0;")
        lines.append(f"        else       {rname} <= {s} ? {d1} : {d0};")
        lines.append(f"    end")
    lines.append("")
    lines.append("endmodule  // COUNT_12BX2")

    with open(dst, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    print(f"Written {dst}: {len(ff_data)} FFs, {len(comb_assigns)} assigns, "
          f"{len(output_port_assigns)} FF→port connections")


if __name__ == "__main__":
    main()
