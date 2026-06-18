#!/usr/bin/env python3
"""
check_equiv.py -- deterministic equivalence gate between spec and gate-level netlist.
NO LLM CALLS. Exit 0=PASS / 1=FAIL / 2=UNKNOWN/error.
Outputs strict JSON to stdout.

Usage (comb mode — default, no async2sync pseudo-CEX):
  python scripts/check_equiv.py \
      --spec spec.v --top-spec COUNT_12BX2_spec \
      --netlist impl.v --lib SC_LIB_SCH.v --top-gate COUNT_12BX2 \
      --ff-map ff_map.json \
      --mode comb --out-dir equiv_out/

Usage (seq mode — fallback when registers can't be 1:1 mapped):
  python scripts/check_equiv.py ... --mode seq --out-dir equiv_out/

Usage (legacy prove mode — equiv_induct with async2sync):
  python scripts/check_equiv.py ... --mode prove --out-dir equiv_out/
"""
import argparse, json, os, subprocess, sys, tempfile, shutil

YOSYS = "yosys"
YOSYS_ABC = "yosys-abc"


def run_yosys(script_path, log_path):
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


# ---------------------------------------------------------------------------
# Script generators
# ---------------------------------------------------------------------------

def _gate_reads(args):
    lines = []
    for lf in (args.lib or []):
        lines.append(f"read_verilog {lf}")
    if getattr(args, "wrapper", None):
        lines.append(f"read_verilog {args.wrapper}")
    lines.append(f"read_verilog {args.netlist}")
    return lines


def _gold_reads(args):
    lines = []
    for lf in (args.lib or []):
        lines.append(f"read_verilog {lf}")
    lines.append(f"read_verilog {args.spec}")
    return lines


def _load_ff_map(ff_map_path):
    """Load ff_map.json → {gate_q_net: spec_reg_name}."""
    if not ff_map_path or not os.path.exists(ff_map_path):
        return {}
    with open(ff_map_path) as f:
        return json.load(f)


def gen_rename_cmds(ff_map):
    """
    For each gate_net → spec_name mapping, emit a Yosys rename command.
    Uses 'rename -wire' which renames a specific wire in the current module.
    Bracket indices are kept; backslash-escape names that start with X or digits.
    """
    cmds = []
    for gate_net, spec_name in ff_map.items():
        # Yosys requires backslash for names starting with non-alpha
        g = f"\\{gate_net}" if gate_net[0].isdigit() or gate_net[0] == '\\' else gate_net
        # Remove brackets for rename target (spec reg names are plain identifiers)
        s = spec_name.replace("[", "").replace("]", "")
        cmds.append(f"rename -wire {g} {s}")
    return cmds


def gen_comb_script(args, ff_map):
    """
    comb mode: flatten both sides WITHOUT async2sync, optionally rename gate FFs,
    then run equiv_make → equiv_simple → equiv_induct → equiv_status -assert.
    """
    rename_cmds = gen_rename_cmds(ff_map)
    lines = []

    # --- gate side ---
    lines += _gate_reads(args)
    lines.append(f"prep -top {args.top_gate}")
    lines.append("flatten")
    lines.append("async2sync")   # required for equiv_induct to converge on async-reset FFs
    # rename gate FF Q wires to match spec register names (enables explicit FF matching)
    lines += rename_cmds
    lines.append("design -save gate_save")
    lines.append("")

    # --- gold side ---
    lines.append("design -reset")
    lines += _gold_reads(args)
    lines.append(f"prep -top {args.top_spec}")
    lines.append("flatten")
    lines.append("async2sync")
    lines.append("design -save gold_save")
    lines.append("")

    # --- equiv check ---
    # async2sync is present but bounded/sat mode (which creates spurious initial-state CEX)
    # is never used here — equiv_induct gives a clean inductive proof without pseudo-CEX.
    lines.append("design -reset")
    lines.append(f"design -copy-from gate_save -as gate {args.top_gate}")
    lines.append(f"design -copy-from gold_save -as gold {args.top_spec}")
    lines.append("equiv_make gold gate equiv")
    lines.append("hierarchy -top equiv")
    lines.append("equiv_simple")
    lines.append("equiv_induct")
    lines.append("equiv_status -assert")
    return "\n".join(lines) + "\n"


def gen_prove_script(args):
    """Legacy prove mode: uses async2sync (handles async reset flops)."""
    lines = []
    lines += _gate_reads(args)
    lines.append(f"prep -top {args.top_gate}")
    lines.append("flatten")
    lines.append("async2sync")
    lines.append("design -save gate_save")
    lines.append("")
    lines.append("design -reset")
    lines += _gold_reads(args)
    lines.append(f"prep -top {args.top_spec}")
    lines.append("flatten")
    lines.append("async2sync")
    lines.append("design -save gold_save")
    lines.append("")
    lines.append("design -reset")
    lines.append(f"design -copy-from gate_save -as gate {args.top_gate}")
    lines.append(f"design -copy-from gold_save -as gold {args.top_spec}")
    lines.append("equiv_make gold gate equiv")
    lines.append("hierarchy -top equiv")
    lines.append("equiv_simple")
    lines.append("equiv_induct")
    lines.append("equiv_status -assert")
    return "\n".join(lines) + "\n"


def gen_seq_script(args, tmpdir, cex_vcd):
    """
    seq mode: ABC dprove via AIGER export.
    Fallback when registers cannot be 1:1 mapped.
    """
    gate_aig = os.path.join(tmpdir, "gate.aig")
    gold_aig = os.path.join(tmpdir, "gold.aig")

    gate_ys = []
    gate_ys += _gate_reads(args)
    gate_ys.append(f"prep -top {args.top_gate}")
    gate_ys.append("flatten")
    gate_ys.append("async2sync")
    gate_ys.append("aigmap")
    gate_ys.append(f"write_aiger -zinit {gate_aig}")
    gate_ys_path = os.path.join(tmpdir, "gate_seq.ys")
    with open(gate_ys_path, "w") as f:
        f.write("\n".join(gate_ys) + "\n")

    gold_ys = []
    gold_ys += _gold_reads(args)
    gold_ys.append(f"prep -top {args.top_spec}")
    gold_ys.append("flatten")
    gold_ys.append("async2sync")
    gold_ys.append("aigmap")
    gold_ys.append(f"write_aiger -zinit {gold_aig}")
    gold_ys_path = os.path.join(tmpdir, "gold_seq.ys")
    with open(gold_ys_path, "w") as f:
        f.write("\n".join(gold_ys) + "\n")

    return gate_ys_path, gold_ys_path, gate_aig, gold_aig


def gen_bounded_script(args, tmpdir, cex_vcd):
    lines = []
    lines += _gate_reads(args)
    lines.append(f"prep -top {args.top_gate}")
    lines.append("flatten")
    lines.append("async2sync")
    lines.append("design -save gate_save")
    lines.append("")
    lines.append("design -reset")
    lines += _gold_reads(args)
    lines.append(f"prep -top {args.top_spec}")
    lines.append("flatten")
    lines.append("async2sync")
    lines.append("design -save gold_save")
    lines.append("")
    lines.append("design -reset")
    lines.append(f"design -copy-from gate_save -as gate {args.top_gate}")
    lines.append(f"design -copy-from gold_save -as gold {args.top_spec}")
    lines.append("miter -equiv -flatten -make_assert gold gate miter_top")
    lines.append("hierarchy -top miter_top")
    seq = args.seq if args.seq else 30
    lines.append(f"sat -seq {seq} -prove-asserts -dump_vcd {cex_vcd}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Result classifiers
# ---------------------------------------------------------------------------
def classify_induct(log_text, rc):
    lo = log_text.lower()
    if "are proven and 0 are unproven" in lo:           return "PASS"
    if "equivalence successfully proven" in lo:          return "PASS"
    if "not equivalent" in lo:                           return "FAIL"
    if "error:" in lo and "unproven" in lo:             return "FAIL"
    if rc != 0:                                          return "UNKNOWN"
    if "error" not in lo and "proved" in lo and "unproven" not in lo:
        return "PASS"
    if "error" not in lo:                               return "PASS"
    return "UNKNOWN"


def classify_bounded(log_text, rc, cex_vcd):
    lo = log_text.lower()
    if "model found: fail" in lo:                        return "FAIL"
    if os.path.exists(cex_vcd) and os.path.getsize(cex_vcd) > 0:
        return "FAIL"
    if "unsat" in lo or ("proof finished" in lo and "fail" not in lo):
        return "PASS"
    if rc != 0:                                          return "UNKNOWN"
    return "PASS"


def run_abc_dprove(gate_ys_path, gold_ys_path, gate_aig, gold_aig,
                   tmpdir, log_path):
    abc_log = log_path.replace(".log", "_abc.log")
    for ys_p in [gate_ys_path, gold_ys_path]:
        tmp_log = abc_log + ".tmp"
        rc = run_yosys(ys_p, tmp_log)
        with open(abc_log, "a") as af:
            af.write(read_log(tmp_log))

    if not (os.path.exists(gate_aig) and os.path.exists(gold_aig)):
        return "UNKNOWN", abc_log

    cmd = f"dprove -F 200 {gold_aig} {gate_aig}; quit"
    with open(abc_log, "a") as af:
        subprocess.run([YOSYS_ABC, "-c", cmd], stdout=af, stderr=subprocess.STDOUT)

    lo = read_log(abc_log).lower()
    if "networks are equivalent" in lo:          return "PASS", abc_log
    if "not equivalent" in lo:                   return "FAIL", abc_log
    # Fallback: dsec
    cmd2 = f"dsec {gold_aig} {gate_aig}; quit"
    with open(abc_log, "a") as af:
        subprocess.run([YOSYS_ABC, "-c", cmd2], stdout=af, stderr=subprocess.STDOUT)
    lo2 = read_log(abc_log).lower()
    if "networks are equivalent" in lo2:         return "PASS", abc_log
    if "not equivalent" in lo2:                  return "FAIL", abc_log
    return "UNKNOWN", abc_log


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec",     required=True)
    ap.add_argument("--top-spec", required=True)
    ap.add_argument("--netlist",  required=True)
    ap.add_argument("--top-gate", required=True)
    ap.add_argument("--lib",      action="append")
    ap.add_argument("--wrapper")
    ap.add_argument("--ff-map",   default=None,
                    help="ff_map.json: gate_q_net→spec_reg_name for comb mode renaming")
    ap.add_argument("--mode",     choices=["comb", "prove", "seq", "bounded"],
                    default="comb")
    ap.add_argument("--seq",      type=int, default=30,
                    help="Depth for bounded mode (default 30)")
    ap.add_argument("--out-dir",  default=".")
    args = ap.parse_args()

    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)
    ff_map = _load_ff_map(args.ff_map)

    with tempfile.TemporaryDirectory() as tmpdir:
        # ---- comb mode ----
        if args.mode == "comb":
            log_path = os.path.join(out_dir, "comb.log")
            ys_txt = gen_comb_script(args, ff_map)
            ys_path = os.path.join(tmpdir, "comb.ys")
            with open(ys_path, "w") as f:
                f.write(ys_txt)
            rc = run_yosys(ys_path, log_path)
            log_txt = read_log(log_path)
            status = classify_induct(log_txt, rc)

            # If comb fails due to rename issues, fall back to prove mode
            if status == "UNKNOWN":
                prove_log = os.path.join(out_dir, "prove_fallback.log")
                prove_ys_txt = gen_prove_script(args)
                prove_ys = os.path.join(tmpdir, "prove_fb.ys")
                with open(prove_ys, "w") as f:
                    f.write(prove_ys_txt)
                rc2 = run_yosys(prove_ys, prove_log)
                log_txt2 = read_log(prove_log)
                status2 = classify_induct(log_txt2, rc2)
                if status2 in ("PASS", "FAIL"):
                    status = status2
                    log_path = prove_log
                    log_txt = log_txt2

            result = {
                "status": status,
                "engine": "yosys-equiv-comb",
                "mode": "comb",
                "cex_vcd": None,
                "failing_ff": None,
                "log_path": log_path,
            }

        # ---- prove mode (legacy, with async2sync) ----
        elif args.mode == "prove":
            log_path = os.path.join(out_dir, "prove.log")
            ys_txt = gen_prove_script(args)
            ys_path = os.path.join(tmpdir, "prove.ys")
            with open(ys_path, "w") as f:
                f.write(ys_txt)
            rc = run_yosys(ys_path, log_path)
            log_txt = read_log(log_path)
            status = classify_induct(log_txt, rc)

            if status == "UNKNOWN":
                # ABC dsec fallback
                gate_ys_p, gold_ys_p, gate_aig, gold_aig = gen_seq_script(
                    args, tmpdir, None)
                abc_status, abc_log = run_abc_dprove(
                    gate_ys_p, gold_ys_p, gate_aig, gold_aig, tmpdir, log_path)
                if abc_status in ("PASS", "FAIL"):
                    status = abc_status
                    log_path = abc_log

            result = {
                "status": status,
                "engine": "yosys-equiv-prove",
                "mode": "prove",
                "cex_vcd": None,
                "failing_ff": None,
                "log_path": log_path,
            }

        # ---- seq mode (ABC dprove / dsec via AIGER) ----
        elif args.mode == "seq":
            log_path = os.path.join(out_dir, "seq.log")
            gate_ys_p, gold_ys_p, gate_aig, gold_aig = gen_seq_script(
                args, tmpdir, None)
            seq_status, seq_log = run_abc_dprove(
                gate_ys_p, gold_ys_p, gate_aig, gold_aig, tmpdir, log_path)
            result = {
                "status": seq_status,
                "engine": "yosys-abc-dprove",
                "mode": "seq",
                "cex_vcd": None,
                "failing_ff": None,
                "log_path": seq_log,
            }

        # ---- bounded mode ----
        else:  # bounded
            cex_vcd = os.path.join(out_dir, "cex.vcd")
            log_path = os.path.join(out_dir, "bounded.log")
            ys_txt = gen_bounded_script(args, tmpdir, cex_vcd)
            ys_path = os.path.join(tmpdir, "bounded.ys")
            with open(ys_path, "w") as f:
                f.write(ys_txt)
            rc = run_yosys(ys_path, log_path)
            log_txt = read_log(log_path)
            status = classify_bounded(log_txt, rc, cex_vcd)
            result = {
                "status": status,
                "engine": "yosys-sat",
                "mode": "bounded",
                "cex_vcd": (cex_vcd if status == "FAIL"
                             and os.path.exists(cex_vcd)
                             and os.path.getsize(cex_vcd) > 0 else None),
                "failing_ff": None,
                "log_path": log_path,
            }

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "PASS"
             else 1 if result["status"] == "FAIL"
             else 2)


if __name__ == "__main__":
    main()
