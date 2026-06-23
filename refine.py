#!/usr/bin/env python3
"""
refine.py — 可读性优化循环（Phase D：在 C 产出「等价且过底线」之后，爬向「像 COUNT_6B_2 一样易读」）

把"一次 A→B→C 达不到工程师易读"这个现实，变成一个有方向、会收敛、永不退化的循环。

三个不变量（缺一不可）：
  1. equiv 是硬约束。任何改写让 comb-equiv 不过 → 直接丢弃，不参与评分。（防"漂亮但不等价"）
  2. readability 分数（check_readability.py --score）是确定性**梯度**，LLM 只当"改写提议者"，
     永不当"裁判"。⚠️ 但要清醒：这个分数测的是**语法卫生**，不是"真好读"——
     爬到标杆只代表语法卫生追平 COUNT_6B_2，不等于可读性追平。（天花板自知）
  3. 棘轮：best 永远保留"既等价、分数又最高、且无 violations"的那版；
     只接受 equiv 仍过 且 violations 为空 且 分数严格提高 的改写。

防 Goodhart（本版新增）：score 可被退化手法刷高（硬抬 wordop_density 等）。
  对策：**任何 violations 非空的候选一律拒收**，即使 score 微涨——把语法底线从软目标钉回硬门。

所有确定性闸门统一来自 harness.py（单一判决来源；不再本地重写 check_equiv，杜绝与 driver 漂移）。

挂载：driver.py 的 C-final（spec.v 整合并首次 comb+readable PASS）之后调用
    refine_loop(spec="COUNT_12BX2/spec.v", ctx=ctx)
独立跑：python3 refine.py COUNT_12BX2/spec.v
"""

import json
import os
import sys
import time
from pathlib import Path

import harness
from harness import ROOT, SKILLS, PERM_FLAGS, equiv_ok, readability_score

BUDGET = 8        # 每个 spec 的最大改写轮数（防无限爬）
PATIENCE = 2      # 连续多少轮无严格提升就停（收敛判据）
REF_DESIGN = "COUNT_6B_2"          # 可读性标杆


# ── 标杆：数据驱动的目标分（非魔法常数） ─────────────────────────────
def reference_bar(ctx) -> float:
    """给 COUNT_6B_2/spec.v 打分作为目标。没有标杆 → inf，靠 patience/budget 收敛（不是错误）。"""
    ref_spec = ROOT / REF_DESIGN / "spec.v"
    if not ref_spec.exists():
        return float("inf")
    r = readability_score(str(ref_spec), ctx, top=f"{REF_DESIGN}_spec")
    return r.get("score", float("inf"))


# ── 提议者：干净子上下文，只负责"提一个更易读的改写"，不判等价/可读 ──
def propose_rewrite(best_spec: str, report: dict, ctx) -> str:
    """
    喂子 agent：当前 best spec + 分数明细/violations + 标杆参照，产出候选 candidate.v。
    它不判等价、不判可读——那是 harness 闸门的事。
    系统提示用 harness.run_subagent 统一加载（CLAUDE.md + skill），不再本地拼 SYSTEM.md。

    注：这里给的是一段**轻量全局 polish 指令**，而非复用 Phase C 的「单组铁律」语境——
    Phase D 面对的是整合后的 spec.v，目标是全局可读化，与 abstract-group 的「只看本组」不同。
    """
    ref = ROOT / REF_DESIGN / "spec.v"
    cand = str(Path(best_spec).with_name("candidate.v"))
    prompt = (
        f"任务：对已『等价且过可读底线』的 {Path(best_spec).name} 做**保语义**的可读性改写，"
        f"风格向 {REF_DESIGN}/spec.v 靠拢。\n"
        f"当前可读性维度：{json.dumps(report.get('dims', {}), ensure_ascii=False)}；"
        f"必须清零的 violations：{report.get('violations')}。\n"
        f"参照风格：{ref}。\n"
        f"只做下列小幅改写之一，绝不改变任何信号的逻辑函数：\n"
        f"(a) 残留网表名 → 语义名；(b) 裸布尔树 → 字级算子/模式分支；"
        f"(c) 合并同 clk/rst 域 always 块；(d) 内联只用一次的具名 wire；"
        f"(e) 深嵌套 ?: → if/else if 模式阶梯。\n"
        f"⚠️ 不得用退化手法硬刷指标（如把简单赋值改写成无意义的字级算子凑 density）——"
        f"那会被 equiv 或 violations 拦下，纯属浪费轮次。\n"
        f"把结果写到 {cand}。"
    )
    # abstract-group skill 含「保语义/零网表名残留/不手写布尔树」等正合用的铁律，复用其约束部分。
    return harness.run_subagent("abstract-group", prompt, [cand], allowed_tools="Read,Write")


# ── 棘轮主循环：约束式爬山 ───────────────────────────────────────────
def refine_loop(spec: str, ctx, budget: int = BUDGET, patience: int = PATIENCE) -> str:
    assert equiv_ok(spec, ctx), "进入 refine 前 spec 必须已 comb-PASS"
    best = spec
    best_report = readability_score(best, ctx)
    best_score = best_report.get("score", -1.0)
    bar = reference_bar(ctx)
    bar_str = "inf(无标杆)" if bar == float("inf") else f"{bar:.3f}"
    print(f"[refine] 起点分={best_score:.3f}  标杆({REF_DESIGN})={bar_str}")

    # 保护：只有「打分器坏了」才致命退出。
    # bar==inf 不致命——那只是没标杆，照样靠 patience/budget 纯爬坡收敛（修正旧版逻辑 bug）。
    if best_score < 0:
        print("[refine] ⚠️ 打分器未返回有效 score（--score 未实现或字段名不符），跳过优化循环。"
              "spec.v 已是『等价+过底线』版本。修通 check_readability.py --score 后再单独跑："
              f"python3 refine.py {ctx.design}/spec.v")
        return best

    stale = 0
    for it in range(1, budget + 1):
        if best_score >= bar:                       # 够到标杆 → 收敛（bar==inf 时永不触发）
            print(f"[refine] 第 {it} 轮前已达标杆，停。"); break

        cand = propose_rewrite(best, best_report, ctx)

        # 防御：子 agent 空转没写出候选文件 → 计 stale，别拿不存在的文件去跑闸门
        if not Path(cand).exists():
            print(f"[refine] 轮{it}: 子 agent 未产出候选文件，跳过。")
            stale += 1
        elif not equiv_ok(cand, ctx):               # 硬约束：等价不过 → 整版作废
            print(f"[refine] 轮{it}: 改写破坏等价，丢弃。")
            stale += 1
        else:
            rep = readability_score(cand, ctx)
            sc = rep.get("score", -1.0)
            viol = rep.get("violations") or []
            if viol:                                # 防 Goodhart：底线未过 → 拒收，无论分数高低
                print(f"[refine] 轮{it}: 等价但 violations 非空({len(viol)} 条)，拒收（防刷分）。")
                stale += 1
            elif sc > best_score + 1e-6:            # 严格提升才接受（棘轮）
                ts = time.strftime("%H%M%S")
                Path(best).replace(Path(best).with_suffix(f".v.{it:02d}_{ts}.prev"))  # 带轮次时间戳，不互相覆盖
                Path(cand).replace(Path(best))
                best_report, best_score, stale = rep, sc, 0
                print(f"[refine] 轮{it}: 接受，分数 → {best_score:.3f}")
            else:
                print(f"[refine] 轮{it}: 等价但无提升({sc:.3f}≤{best_score:.3f})，回退。")
                stale += 1

        if stale >= patience:                       # 连续无提升 → 收敛
            print(f"[refine] 连续{stale}轮无提升，停。"); break

    bar_final = "inf(无标杆)" if bar == float("inf") else f"{bar:.3f}"
    print(f"[refine] 完成：最终分={best_score:.3f}（标杆 {bar_final}），输出 {best}")
    print("[refine] 提醒：score 是语法卫生梯度，非『真好读』——达标杆≠可读性追平 COUNT_6B_2。")
    return best


if __name__ == "__main__":
    import types
    spec = sys.argv[1] if len(sys.argv) > 1 else "COUNT_12BX2/spec.v"
    design = os.environ.get("RE_DESIGN", "COUNT_12BX2")
    ddir = ROOT / design
    ctx = types.SimpleNamespace(
        design=design, impl=str(ddir / "impl.v"), lib=str(ddir / "SC_LIB_SCH.v"),
        ff_map=str(ddir / "ff_map.json"), out_dir=str(ddir / "equiv_out"))
    refine_loop(spec, ctx)
