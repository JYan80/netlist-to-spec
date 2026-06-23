#!/usr/bin/env python3
"""
check_readability.py — 可读性闸门（默认：过/不过） + 打分器（--score：可读性梯度）

向后兼容：保留 --spec/--top/--max-line-ratio/--ff-count 与原闸门行为；
新增 --score：返回归一化综合分 + 六维明细，供 refine.py 优化循环用。

闸门模式（默认）输出：{"readable": bool, "violations": [...]}  exit 0/1
打分模式（--score）输出：{"score": 0..1, "violations": [...], "dims": {...}, "ff_count": N}  exit 0

设计目标：让 COUNT_6B_2/spec.v 这类干净 RTL 自然拿高分；
机器直译（残留网表名、裸布尔树、行数臃肿）自然拿低分。
"""

import argparse
import json
import re
import sys

# ── 维度权重（和越大越重要；总和=1）。残留名 & 布尔树是可读性头号杀手，权重最高。──
WEIGHTS = {
    "name_residue": 0.05,   # always 块内 X####_ 残留（↓好）
    "bool_chain":   0.00,   # 长度>2 的裸 &|^ 链（↓好）
    "wordop":       0.05,   # 字级算子密度 + - << >> {}（↑好）
    "mode_branch":  0.85,   # if/else | ?: 模式分支占比（↑好）
    "lines":        0.05,   # 行数/FF（↓好，对标 ~5×）
    "named_wires":  0.00,   # 具名中间 wire/FF（↓好）
}
TARGET_LINES_PER_FF = 5.0   # COUNT_6B_2 基线量级

NETLIST_NAME = re.compile(r'\bX\d+_\w*')          # 网表中间网名，如 X421_73_ZN
ALWAYS_HDR   = re.compile(r'\balways\b')
BOOLCHAIN    = re.compile(r'(?:[~()\w\[\].]+\s*[&|^]\s*){2,}[~()\w\[\].]+')  # >2 操作数的裸布尔链
WORDOP       = re.compile(r'(\+|\-|<<|>>|\{)')    # 字级算子（{ 表示拼接）
COND         = re.compile(r'(\bif\b|\?)')


def strip_comments(text: str) -> str:
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    text = re.sub(r'//[^\n]*', '', text)
    return text


def code_lines(text: str):
    return [ln for ln in text.splitlines() if ln.strip()]


def always_blocks(lines):
    """返回 always 块覆盖的行索引集合（按 begin/end 配平，无 begin 则取单行）。"""
    covered, i, n = [], 0, len(lines)
    while i < n:
        if ALWAYS_HDR.search(lines[i]):
            # 找到块体
            j = i
            depth = 0
            started = False
            while j < n:
                depth += lines[j].count("begin") - lines[j].count("end")
                covered.append(j)
                if "begin" in lines[j]:
                    started = True
                if started and depth <= 0:
                    break
                if not started and (";" in lines[j]) and j > i:
                    break
                j += 1
            i = j + 1
        else:
            i += 1
    return set(covered)


def resolve_ff_count(text: str, arg) -> int:
    if arg:
        return max(1, int(arg))
    # 估计：累加 reg 声明位宽
    total = 0
    for m in re.finditer(r'\breg\b\s*(\[(\d+)\s*:\s*(\d+)\])?\s*([\w,\s]+);', text):
        names = [x.strip() for x in m.group(4).split(",") if x.strip()]
        if m.group(2) is not None:
            width = abs(int(m.group(2)) - int(m.group(3))) + 1
        else:
            width = 1
        total += width * len(names)
    if total:
        return total
    # 兜底：数非阻塞赋值条数
    return max(1, text.count("<="))


def analyze(spec_path: str, ff_count_arg, max_line_ratio: float):
    raw = open(spec_path, encoding="utf-8").read()
    text = strip_comments(raw)
    lines = code_lines(text)
    ff = resolve_ff_count(text, ff_count_arg)
    cov = always_blocks(lines)
    always_text = "\n".join(lines[k] for k in sorted(cov))

    # 原始计数
    residue = len(NETLIST_NAME.findall(always_text))
    bool_chains = sum(1 for ln in (lines[k] for k in cov) if BOOLCHAIN.search(ln))
    n_lines = len(lines)
    named_wires = len(re.findall(r'\b(?:wire|assign)\b', text))
    # 赋值统计（用于密度）
    assigns = re.findall(r'<=.*?;|assign[^=]*=.*?;', text, flags=re.S)
    n_assign = max(1, len(assigns))
    wordop_hits = sum(1 for a in assigns if WORDOP.search(a))
    nb_assigns = re.findall(r'<=.*?;', always_text, flags=re.S) or re.findall(r'<=.*?;', text, flags=re.S)
    n_nb = max(1, len(nb_assigns))
    mode_hits = sum(1 for ln in (lines[k] for k in cov) if COND.search(ln))

    dims = {
        "name_residue_per_ff": round(residue / ff, 4),
        "bool_chain_count": bool_chains,
        "lines_per_ff": round(n_lines / ff, 3),
        "named_wires_per_ff": round(named_wires / ff, 3),
        "wordop_density": round(wordop_hits / n_assign, 3),
        "mode_branch_ratio": round(min(1.0, mode_hits / n_nb), 3),
    }

    # 违规（闸门用）
    violations = []
    if residue > 0:
        violations.append(f"always 块内残留网表名 {residue} 处 (X####_)")
    if bool_chains > 0:
        violations.append(f"裸布尔树 {bool_chains} 处 (长度>2 的 &|^ 链)")
    if n_lines > max_line_ratio * ff:
        violations.append(f"行数 {n_lines} > {max_line_ratio}×FF({ff})={max_line_ratio*ff:.0f}")

    # 子分（各映射到 0..1，越大越易读）
    s = {
        "name_residue": 1.0 / (1.0 + dims["name_residue_per_ff"]),
        "bool_chain":   1.0 / (1.0 + dims["bool_chain_count"]),
        "wordop":       dims["wordop_density"],
        "mode_branch":  dims["mode_branch_ratio"],
        "lines":        min(1.0, TARGET_LINES_PER_FF / max(dims["lines_per_ff"], 1e-6)),
        "named_wires":  1.0 / (1.0 + dims["named_wires_per_ff"]),
    }
    score = round(sum(WEIGHTS[k] * s[k] for k in WEIGHTS), 4)
    return ff, dims, violations, score


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--top")                          # 兼容保留
    ap.add_argument("--max-line-ratio", type=float, default=16.0)
    ap.add_argument("--ff-count", type=int, default=None)
    ap.add_argument("--score", action="store_true", help="输出可读性梯度分而非过/不过")
    a = ap.parse_args()

    ff, dims, violations, score = analyze(a.spec, a.ff_count, a.max_line_ratio)

    if a.score:
        print(json.dumps({"score": score, "violations": violations,
                          "dims": dims, "ff_count": ff}, ensure_ascii=False))
        sys.exit(0)

    readable = len(violations) == 0
    print(json.dumps({"readable": readable, "violations": violations},
                     ensure_ascii=False))
    sys.exit(0 if readable else 1)


if __name__ == "__main__":
    main()
