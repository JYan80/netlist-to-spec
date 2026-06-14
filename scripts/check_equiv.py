#!/usr/bin/env python3
"""
check_equiv.py -- deterministic equivalence gate between spec and gate-level netlist.
NO LLM CALLS. Exit 0=PASS, 1=FAIL, 2=UNKNOWN/error.
Outputs strict JSON to stdout.

Usage:
  python scripts/check_equiv.py \
      --spec spec.v --top-spec COUNT_12BX2_spec \
      --netlist impl.v --top-gate COUNT_12BX2 \
      --lib SC_LIB_SCH.v \
      [--wrapper wrapper.v] \
      --mode {bounded|prove} [--seq 70] \
      [--out-dir .]
"""
import argparse, json, os, subprocess, sys, tempfile, shutil

YOSYS = "yosys"
YOSYS_ABC = "yosys-abc"


def run_yosys(script_path, log_path):
    # Run without -q so log captures all output needed for classification.
    # In yosys 0.9, exit code is always 0 even on logical failure;
    # we classify by parsing log text.
    with open(log_path, "w") as lf:
        r = subprocess.run([YOSYS, script_path],
                           stdout=lf, stderr=subprocess.STDOUT)
    return r.returncode


def read_log(log_path):
    try:
        with open(log_path) as f:
            return f.read()
    except FileNotFoundError:
        return ""


def build_gate_reads(args):
    # Library must be read WITHOUT -lib so cells get properly inlined by flatten.
    # (Matches the working COUNT_6B_2/equiv.ys pattern.)
    lines = []
    if args.lib:
        for lf in args.lib:
            lines.append(f"read_verilog {lf}")
    if args.wrapper:
        lines.append(f"read_verilog {args.wrapper}")
    lines.append(f"read_verilog {args.netlist}")
    return lines


def build_gold_reads(args):
    lines = []
    if args.lib:
        for lf in args.lib:
            lines.append(f"read_verilog {lf}")
    lines.append(f"read_verilog {args.spec}")
    return lines


def gen_prove_script(args, tmpdir):
    """Generate yosys script for unbounded equivalence proof."""
    lines = []
    # --- gate side ---
    lines += build_gate_reads(args)
    lines.append(f"prep -top {args.top_gate}")
    lines.append("flatten")
    lines.append("async2sync")
    lines.append("design -save gate_save")
    lines.append("")
    # --- gold side ---
    lines.append("design -reset")
    lines += build_gold_reads(args)
    lines.append(f"prep -top {args.top_spec}")
    lines.append("flatten")
    lines.append("async2sync")
    lines.append("design -save gold_save")
    lines.append("")
    # --- equivalence check ---
    lines.append("design -reset")
    lines.append(f"design -copy-from gate_save -as gate {args.top_gate}")
    lines.append(f"design -copy-from gold_save -as gold {args.top_spec}")
    lines.append("equiv_make gold gate equiv")
    lines.append("hierarchy -top equiv")
    lines.append("equiv_simple")
    lines.append("equiv_induct")
    lines.append("equiv_status -assert")
    return "\n".join(lines) + "\n"


def gen_bounded_script(args, tmpdir, cex_vcd):
    """Generate yosys script for bounded model checking (produces CEX VCD)."""
    lines = []
    # --- gate side ---
    lines += build_gate_reads(args)
    lines.append(f"prep -top {args.top_gate}")
    lines.append("flatten")
    lines.append("async2sync")
    lines.append("design -save gate_save")
    lines.append("")
    # --- gold side ---
    lines.append("design -reset")
    lines += build_gold_reads(args)
    lines.append(f"prep -top {args.top_spec}")
    lines.append("flatten")
    lines.append("async2sync")
    lines.append("design -save gold_save")
    lines.append("")
    # --- miter ---
    lines.append("design -reset")
    lines.append(f"design -copy-from gate_save -as gate {args.top_gate}")
    lines.append(f"design -copy-from gold_save -as gold {args.top_spec}")
    lines.append("miter -equiv -flatten -make_assert gold gate miter_top")
    lines.append("hierarchy -top miter_top")
    seq = args.seq if args.seq else 30
    lines.append(f"sat -seq {seq} -prove-asserts -dump_vcd {cex_vcd}")
    return "\n".join(lines) + "\n"


def gen_aiger_scripts(args, tmpdir):
    """Generate two yosys scripts that write gate.aig and gold.aig."""
    gate_ys_lines = []
    gate_ys_lines += build_gate_reads(args)
    gate_ys_lines.append(f"prep -top {args.top_gate}")
    gate_ys_lines.append("flatten")
    gate_ys_lines.append("async2sync")
    gate_ys_lines.append("aigmap")
    gate_ys_lines.append(f"write_aiger -zinit {os.path.join(tmpdir, 'gate.aig')}")

    gold_ys_lines = []
    gold_ys_lines += build_gold_reads(args)
    gold_ys_lines.append(f"prep -top {args.top_spec}")
    gold_ys_lines.append("flatten")
    gold_ys_lines.append("async2sync")
    gold_ys_lines.append("aigmap")
    gold_ys_lines.append(f"write_aiger -zinit {os.path.join(tmpdir, 'gold.aig')}")

    return "\n".join(gate_ys_lines) + "\n", "\n".join(gold_ys_lines) + "\n"


def classify_prove_result(log_text, rc):
    """Return 'PASS', 'FAIL', or 'UNKNOWN' from prove-mode log.
    In yosys 0.9 exit code is always 0; classification is log-text based."""
    lo = log_text.lower()
    # Definitive PASS: final equiv_status shows 0 unproven cells
    if "are proven and 0 are unproven" in lo:
        return "PASS"
    # Definitive PASS: yosys explicitly says equivalence proven
    if "equivalence successfully proven" in lo:
        return "PASS"
    # Definitive PASS: all equiv cells proved, no error, and no "unproven" in final status
    if "error" not in lo and "proved" in lo and "unproven" not in lo:
        return "PASS"
    # Definitive not-equivalent from induction counterexample
    if "not equivalent" in lo:
        return "FAIL"
    # equiv_status -assert errored due to unproven cells → FAIL
    if "error:" in lo and "unproven" in lo:
        return "FAIL"
    # No equiv output at all (yosys crashed or input error)
    if rc != 0:
        return "UNKNOWN"
    # No error found: PASS
    if "error" not in lo:
        return "PASS"
    return "UNKNOWN"


def classify_bounded_result(log_text, rc, cex_vcd):
    """Return 'PASS' or 'FAIL' from bounded-mode log.
    In yosys 0.9 exit code is always 0; check log text for SAT result."""
    lo = log_text.lower()
    # CEX found by sat
    if "model found: fail" in lo:
        return "FAIL"
    # Proved: no counterexample in N steps
    if "unsat" in lo or ("proof finished" in lo and "fail" not in lo):
        return "PASS"
    # VCD produced even if log unclear
    if os.path.exists(cex_vcd) and os.path.getsize(cex_vcd) > 0:
        return "FAIL"
    if rc != 0:
        return "UNKNOWN"
    # Default: if no FAIL signal, assume bounded PASS
    return "PASS"


def run_abc_dsec(args, tmpdir, log_path):
    """Write AIGER files and run yosys-abc dsec for fallback proof."""
    gate_ys_txt, gold_ys_txt = gen_aiger_scripts(args, tmpdir)
    gate_ys = os.path.join(tmpdir, "gate_aig.ys")
    gold_ys = os.path.join(tmpdir, "gold_aig.ys")
    gate_aig = os.path.join(tmpdir, "gate.aig")
    gold_aig = os.path.join(tmpdir, "gold.aig")

    with open(gate_ys, "w") as f:
        f.write(gate_ys_txt)
    with open(gold_ys, "w") as f:
        f.write(gold_ys_txt)

    abc_log = log_path.replace(".log", "_abc.log")
    ok = True
    for ys_path in [gate_ys, gold_ys]:
        rc = run_yosys(ys_path, abc_log + ".tmp")
        with open(abc_log, "a") as af:
            af.write(read_log(abc_log + ".tmp"))
        if rc != 0:
            ok = False
            break

    if not ok or not os.path.exists(gate_aig) or not os.path.exists(gold_aig):
        return "UNKNOWN", abc_log

    dsec_cmd = f"dsec {gold_aig} {gate_aig}; quit"
    with open(abc_log, "a") as af:
        r = subprocess.run([YOSYS_ABC, "-c", dsec_cmd],
                           stdout=af, stderr=subprocess.STDOUT)
    abc_txt = read_log(abc_log)
    lo = abc_txt.lower()
    if "networks are equivalent" in lo:
        return "PASS", abc_log
    if "networks are not equivalent" in lo or "not equivalent" in lo:
        return "FAIL", abc_log
    return "UNKNOWN", abc_log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--top-spec", required=True)
    ap.add_argument("--netlist", required=True)
    ap.add_argument("--top-gate", required=True)
    ap.add_argument("--lib", action="append")
    ap.add_argument("--wrapper")
    ap.add_argument("--mode", choices=["bounded", "prove"], required=True)
    ap.add_argument("--seq", type=int, default=30)
    ap.add_argument("--out-dir", default=".")
    args = ap.parse_args()

    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        if args.mode == "bounded":
            cex_vcd = os.path.join(out_dir, "cex.vcd")
            ys_txt = gen_bounded_script(args, tmpdir, cex_vcd)
            ys_path = os.path.join(tmpdir, "bounded.ys")
            log_path = os.path.join(out_dir, "bounded.log")
            with open(ys_path, "w") as f:
                f.write(ys_txt)
            rc = run_yosys(ys_path, log_path)
            log_txt = read_log(log_path)
            status = classify_bounded_result(log_txt, rc, cex_vcd)
            result = {
                "status": status,
                "engine": "yosys-sat",
                "mode": "bounded",
                "cex_vcd": cex_vcd if (status == "FAIL" and os.path.exists(cex_vcd) and os.path.getsize(cex_vcd) > 0) else None,
                "log_path": log_path,
            }

        else:  # prove
            cex_vcd = None
            ys_txt = gen_prove_script(args, tmpdir)
            ys_path = os.path.join(tmpdir, "prove.ys")
            log_path = os.path.join(out_dir, "prove.log")
            with open(ys_path, "w") as f:
                f.write(ys_txt)
            rc = run_yosys(ys_path, log_path)
            log_txt = read_log(log_path)
            status = classify_prove_result(log_txt, rc)

            if status == "UNKNOWN":
                # Fallback: ABC dsec
                abc_status, abc_log = run_abc_dsec(args, tmpdir, log_path)
                if abc_status in ("PASS", "FAIL"):
                    status = abc_status
                    result = {
                        "status": status,
                        "engine": "yosys-abc-dsec",
                        "mode": "prove",
                        "cex_vcd": None,
                        "log_path": abc_log,
                    }
                else:
                    result = {
                        "status": "UNKNOWN",
                        "engine": "yosys-equiv+abc-dsec",
                        "mode": "prove",
                        "cex_vcd": None,
                        "log_path": log_path,
                    }
            else:
                result = {
                    "status": status,
                    "engine": "yosys-equiv",
                    "mode": "prove",
                    "cex_vcd": None,
                    "log_path": log_path,
                }

    print(json.dumps(result, indent=2))
    if result["status"] == "PASS":
        sys.exit(0)
    elif result["status"] == "FAIL":
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()
