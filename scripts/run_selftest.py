#!/usr/bin/env python3
"""
run_selftest.py -- Phase A self-test suite.
Runs four deterministic checks; prints "Phase A: PASS" only if all pass.
Usage: python3 scripts/run_selftest.py --lib <SC_LIB_SCH.v> --netlist <impl.v>
         --spec <spec.v> --top-gate <TOP> --top-spec <TOP_spec>
Default: uses COUNT_6B_2 reference design.
"""
import argparse, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PYTHON = sys.executable


def run(cmd, *, capture=True, timeout=120):
    r = subprocess.run(cmd, capture_output=capture, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def check(label, ok, detail=""):
    sym = "PASS" if ok else "FAIL"
    msg = f"  [{sym}] {label}"
    if detail:
        msg += f"  — {detail}"
    print(msg)
    return ok


def selftest_1_equiv(lib, netlist, spec, top_gate, top_spec, outdir):
    """check_equiv spec vs impl → PASS."""
    d = os.path.join(outdir, "t1_equiv")
    rc, out, _ = run([PYTHON, os.path.join(HERE, "check_equiv.py"),
                      "--spec", spec, "--top-spec", top_spec,
                      "--netlist", netlist, "--top-gate", top_gate,
                      "--lib", lib, "--mode", "comb", "--out-dir", d])
    try:
        j = json.loads(out.strip())
        status = j.get("status", "UNKNOWN")
    except Exception:
        status = "UNKNOWN"
    return check("equiv COUNT_6B_2 spec vs impl → PASS",
                 rc == 0 and status == "PASS",
                 f"status={status} exit={rc}")


def selftest_2_fail(lib, netlist, spec, top_gate, top_spec, outdir):
    """check_equiv broken spec → FAIL; parse_cex decodes synthetic VCD."""
    all_pass = True

    # 2a: equivalence on broken spec returns FAIL
    broken = os.path.join(outdir, "spec_broken.v")
    with open(spec) as f:
        txt = f.read()
    # Introduce a bug: swap two slice endpoints in the count path
    broken_txt = txt.replace("count_next[5:3]", "count_next[2:0]", 1)
    if broken_txt == txt:
        # Fallback: flip one character in an assignment RHS
        broken_txt = txt.replace("count_next[1:0]", "count_next[3:2]", 1)
    if broken_txt == txt:
        print("    WARNING: could not produce a broken spec; skipping 2a")
    else:
        with open(broken, "w") as f:
            f.write(broken_txt)
        d2 = os.path.join(outdir, "t2_fail")
        rc, out, _ = run([PYTHON, os.path.join(HERE, "check_equiv.py"),
                          "--spec", broken, "--top-spec", top_spec,
                          "--netlist", netlist, "--top-gate", top_gate,
                          "--lib", lib, "--mode", "comb", "--out-dir", d2])
        try:
            j = json.loads(out.strip())
            status = j.get("status", "UNKNOWN")
        except Exception:
            status = "UNKNOWN"
        ok2a = (rc == 1 and status == "FAIL")
        all_pass &= check("equiv broken spec → FAIL", ok2a,
                          f"status={status} exit={rc}")

    # 2b: parse_cex decodes a synthetic gate/gold VCD (1 divergence, 2 timesteps)
    vcd = os.path.join(outdir, "t2_synth.vcd")
    cex_out = os.path.join(outdir, "t2_cex.json")
    with open(vcd, "w") as f:
        f.write("$timescale 1ns $end\n"
                "$scope module miter $end\n"
                "$var wire 1 a gate_MI2_Q_0 $end\n"
                "$var wire 1 b gold_MI2_Q_0 $end\n"
                "$var wire 1 c gate_CI $end\n"
                "$upscope $end\n"
                "$enddefinitions $end\n"
                "$dumpvars\n0a\n0b\n0c\n$end\n"
                "#1\n1a\n0b\n1c\n")
    rc2, out2, _ = run([PYTHON, os.path.join(HERE, "parse_cex.py"),
                        "--vcd", vcd, "--out", cex_out])
    try:
        j2 = json.load(open(cex_out))
        n_fail = len(j2.get("failing", []))
        first_sig = j2["failing"][0]["signal"] if j2.get("failing") else ""
        first_cyc = j2["failing"][0]["cycle"] if j2.get("failing") else -1
    except Exception:
        n_fail, first_sig, first_cyc = 0, "", -1
    ok2b = (rc2 == 0 and n_fail >= 1 and "MI2_Q" in first_sig and first_cyc == 1)
    all_pass &= check("parse_cex decodes synthetic CEX VCD (1 divergence at cycle 1)",
                      ok2b, f"n_fail={n_fail} first={first_sig}@{first_cyc}")
    return all_pass


def selftest_3_decode(lib, netlist_top, outdir):
    """decode_modes on 2:1-MUX-FF netlist → exactly 2 cofactors, SEL=0→A, SEL=1→B."""
    mfc_v = os.path.join(outdir, "test_mfc.v")
    with open(mfc_v, "w") as f:
        f.write("module test_mfc(input CP, CDN, SEL, A, B, output Q, input GS, VS);\n"
                "    SC_MFC_140_80 ff(.CP(CP),.CDN(CDN),.S(SEL),"
                ".D0(A),.D1(B),.Q(Q),.GS(GS),.VS(VS));\n"
                "endmodule\n")
    modes_out = os.path.join(outdir, "t3_modes.json")
    rc, out, err = run([PYTHON, os.path.join(HERE, "decode_modes.py"),
                        "--netlist", mfc_v, "--lib", lib,
                        "--top", "test_mfc",
                        "--ff", "Q", "--ctrl", "SEL",
                        "--out", modes_out])
    try:
        j = json.load(open(modes_out))
        modes = j.get("modes", [])
        m0 = next((m for m in modes if "SEL=0" in m["cond"]), None)
        m1 = next((m for m in modes if "SEL=1" in m["cond"]), None)
        ok = (len(modes) == 2
              and m0 is not None and m0["expr"] == "A"
              and m1 is not None and m1["expr"] == "B")
    except Exception:
        ok = False
        modes = []
    return check("decode_modes 2:1-MUX-FF → 2 rows (SEL=0→A, SEL=1→B)", ok,
                 f"rows={len(modes)}")


def selftest_4_readability(spec, outdir):
    """check_readability: dirty spec fails, COUNT_6B_2 spec passes."""
    dirty = os.path.join(outdir, "dirty.v")
    with open(dirty, "w") as f:
        f.write("module dirty(input clk, rstn, input [3:0] a, output reg [3:0] q);\n"
                "    always @(posedge clk or negedge rstn) begin\n"
                "        if (!rstn) q <= 0;\n"
                "        else q <= ~(X38_6_ZN & X845_5_ZN);\n"
                "    end\nendmodule\n")
    rc_dirty, _, _ = run([PYTHON, os.path.join(HERE, "check_readability.py"),
                          "--spec", dirty, "--top", "dirty"])
    rc_clean, out_clean, _ = run([PYTHON, os.path.join(HERE, "check_readability.py"),
                                  "--spec", spec, "--top", ""])
    try:
        j_clean = json.loads(out_clean)
        clean_readable = j_clean.get("readable", False)
    except Exception:
        clean_readable = False

    ok_dirty = check("check_readability dirty (X-names) → exit 1",
                     rc_dirty == 1, f"exit={rc_dirty}")
    ok_clean = check("check_readability COUNT_6B_2/spec.v → PASS",
                     rc_clean == 0 and clean_readable,
                     f"exit={rc_clean} readable={clean_readable}")
    return ok_dirty and ok_clean


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lib",      default=None)
    ap.add_argument("--netlist",  default=None)
    ap.add_argument("--spec",     default=None)
    ap.add_argument("--top-gate", default=None)
    ap.add_argument("--top-spec", default=None)
    args = ap.parse_args()

    # Defaults: use COUNT_6B_2 reference design
    ref = os.path.join(REPO, "COUNT_6B_2")
    lib      = args.lib      or os.path.join(ref, "SC_LIB_SCH.v")
    netlist  = args.netlist  or os.path.join(ref, "impl.v")
    spec     = args.spec     or os.path.join(ref, "spec.v")
    top_gate = args.top_gate or "COUNT_6B_2"
    top_spec = args.top_spec or "COUNT_6B_2_spec"

    print("Phase A self-test — 4 checks")
    print(f"  lib:     {lib}")
    print(f"  netlist: {netlist}")
    print(f"  spec:    {spec}")
    print()

    results = []
    with tempfile.TemporaryDirectory() as tmp:
        results.append(selftest_1_equiv(lib, netlist, spec, top_gate, top_spec, tmp))
        results.append(selftest_2_fail(lib, netlist, spec, top_gate, top_spec, tmp))
        results.append(selftest_3_decode(lib, netlist, tmp))
        results.append(selftest_4_readability(spec, tmp))

    print()
    if all(results):
        print("Phase A: PASS")
        sys.exit(0)
    else:
        n_fail = sum(1 for r in results if not r)
        print(f"Phase A: FAIL ({n_fail}/{len(results)} checks failed)")
        sys.exit(1)


if __name__ == "__main__":
    main()
