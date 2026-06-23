# CLAUDE.md — RE-Agent 宪法（共有铁律，全程只读这一次）

> 本文件是项目级稳定约定。三份 skill 不再重复这些铁律，只写各阶段独有步骤。
> Claude Code 开会话时自动加载本文件一次，全程复用。

## 一句话目标
把门级网表 `impl.v` 逆向成**可读的**字级行为 RTL `spec.v`，并由**确定性形式等价**证明正确。
当前目标设计 COUNT_12BX2（22 FF）；可读性标杆 COUNT_6B_2/spec.v。

## 唯一判准：读 / 猜 / 判
一个论断若**对错可被机器验证** → 交确定性闸门**判**；
若本质是**「猜设计者把什么字级结构综合成了这堆门」** → 交大模型**猜**。
**大模型只猜，闸门只判，永不互换。**

- **读**（确定性脚本）：网表上能直接读出的事实——FF 清单、clk/rst、D 锥支持集、进位链邻接、总线下标、cofactor。
- **猜**（大模型外展）：算子身份、哪些位拼成一个字、位序、寄存器对应、语义命名、控制流写法。
- **判**（确定性闸门）：等价（神圣）、grow_patterns 算子验证、可读性语法下限。

**铁律：每个「猜」必须被一个「判」钉死；没有任何「猜」能仅凭自身被信任。**

## 不可动摇的红线
1. **等价是唯一判决来源**：推进信号永远是 `check_equiv.py` 的 exit code，不是「我觉得行了」。
2. **绝不伪造 PASS**：连续重试+升级仍 FAIL → 回传 `blocked` + cex，停下请人介入。绝不谎报通过、绝不编造数据掩盖失败。
3. **大文件永不进上下文**：netlist、535 行锚点、布尔 dump、VCD 只进脚本，脚本吐一行小 JSON 摘要；模型只看摘要。
4. **缺模型/缺数据立即停**：单元缺行为模型、机器事实缺失 → 停止报告，绝不编造补齐。
5. **绝不手写 De Morgan / NAND 树**：需要某组合信号 → 它要么在 candidate_words/字级算术里，要么去 decode_modes 拿。

## 防 Goodhart（可读性）
`check_readability --score` 测的是**语法卫生（下限梯度）**，**不是「真好读」**。
真可读性是大模型软信号，**永不当确定性目标、永不否决正确性、永不可被刷分**。
任何 `violations` 非空的候选一律拒收，即使分数更高。

## 关键环境事实（缺一即坑）
- Yosys 0.9（2019）。`extract_fa` 会崩（extract_fa.cc:218）——**保持禁用**。
- `abc -g` 可用集 = `AND,OR,XOR,MUX`（别名 simple）。`extract` 可用。
- FF 单元 `SC_MFC_140_80`：`Q <= S ? D1 : D0`，异步清 `CDN`（低有效 negedge），时钟 `CP`。
- `X19_GS`/`X19_VS` 是供电网，**剥离**、作 don't-care 切除。
- WSL2 + 代理（Clash）联网。

## 目录地图
```
.claude/skills/{build-scripts,anchor,abstract-group}/SKILL.md   # 各阶段独有步骤（按需加载）
scripts/        # 确定性脚本：吃大文件、吐小 JSON。会话用 Bash 直跑，零大模型 token
COUNT_12BX2/    # 当前设计：impl.v / spec_*.v / ff_map.json / modes/ / verify/ / equiv_out/
COUNT_6B_2/     # 可读性标杆
.tasks/         # 每组一行小 JSON，跨会话可恢复（恢复读台账，不重放历史）
```

## 流程总览（A→B→C→D，靠会话推进，非冷启动 driver）
- **A** build-scripts：建脚本 + 跑 5 项自检（闸门可信才往下）。
- **B** anchor：外展 ff_map/算子，grow_patterns 证 UNSAT，合成锚点并 comb-PASS，产机器事实，写 .tasks/。
- **C** abstract-group：逐组把机器事实写成干净 always 块，组级 comb-equiv + 可读下限。
- **D** refine：等价硬约束下按可读分数爬向标杆（棘轮，永不退化）。

## 调试期工作方式
单个 design 调试**不跑 driver.py 冷启动**。在一个温交互会话里逐步走：
脚本用 Bash 直跑；大文件不读进来；每步只把脚本吐的小 JSON 贴回。
（批量跑几十个 design 时才用 Tier-2 启动器：per-design 一次 headless 会话，不是 per-phase。）
