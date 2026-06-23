---
name: anchor
description: |
  Phase B. Load after Phase A is green, to build the structural equivalence anchor
  (spec_structural.v, gate-faithful, comb-PASS) and emit Phase C's machine facts:
  ff_map.json (LLM hypothesis the anchor proof certifies), candidate_words,
  verify_<g>.json (operators proven UNSAT by grow_patterns), modes/<ff>.json.
  Iron laws live in CLAUDE.md; this file is only Phase B's own steps. Keywords:
  structural anchor, register correspondence, ff_map, abduction, mode tables, Phase B.
---

# Phase B — 结构等价锚点 + 产出机器事实

铁律见 CLAUDE.md。本文件只列 Phase B 独有步骤。
`spec_structural.v` 是**已被闸门证明正确的参照锚点**，不是待手工模糊的底稿。本阶段**不要求可读性，只要求 comb-PASS**。
Phase B 是「猜」最密集的阶段——综合抹掉的字级结构在这里被外展，再被闸门钉死。**每类「猜」分别在哪一步被钉死，是本阶段的核心。**

## 本设计已知结构（先核对再动手）
- 两时钟 `X1026_138_ZN`/`X1027_138_ZN`；两复位 `X3_323_Z`/`X1676_Z`。22 FF。
- FF 组 = 按 `(CP, CDN, S)` 三元组聚类 = 后续 always 块的时钟/复位/选择域 = 逐组证明边界。
- 输出 `MI1_QT[1:0]` 为寄存器输出（X0_335.Q / X1800.Q）；`MI1_SUM[11:1]` 为组合输出且回灌次态。
- spec 把 clk/rst/sel 网作为**输入端口**暴露（与门级同名）。

## B0 预检（读）
`which yosys abc`；核对 impl.v / SC_LIB_SCH.v 存在；确认所用单元都有行为模型（缺 → 停，见 CLAUDE.md）。剥离 X19_GS/X19_VS。

## B1 清点 + 候选字枚举（读）
`run_inventory.py` → inventory.json。candidate_words 是**候选枚举**，非选定字；位序最终由 Phase C 等价证明钉死。

## B2 寄存器成组（读）+ 对应命名（猜，B5 钉死）
- 结构分组（读，可脚本化）：①共享 clk+rst+sel ②总线下标 ③进位链邻接 ④共同扇入扇出。
- 对应命名（猜）：门级 FF 输出网 ↔ 规范名（如 X0_335.Q→a0），**不能靠名字反推**，大模型结合分组/位序/扇入扇出提**假设**。
产出 `ff_map.json`。⚠️ 此刻是**假设**，**B5 锚点 comb-PASS 那一刻才成为权威**。它同时是 check_equiv 的对应输入 + Phase C 命名权威（同源）。

## B3 算子识别（大模型外展 + 确定性验证，不死磕 extract）
长进位链算子不可能靠确定性算法可靠求出 → 必须**外展（猜）+ 等价验证（判）**：
1. extract 首过（读，廉价）：`extract -map scripts/patterns.v`，匹配上就拿，匹配不上**不死磕**。
2. 大模型外展（猜）：写算子假设进 `op_hypotheses.json`，**按设计线索排序**（像减计数→先试 A−1；进位比较→先试 cmp）。每条含 `{op,busA,busB,bit_order,carry_in}`。覆盖加/减(XOR3/XNOR3+CARRY)、比较/进位比较(逐位 carry-out)、增量/条件增量、MUX、移位、SC_MFC 内置 S?D1:D0。
3. 确定性验证（判）：每条喂 `grow_patterns verify`。UNSAT → 写 `verify/verify_<g>.json`；SAT → cex 回传改假设。
**统一一套**：op_hypotheses（猜）→ grow_patterns verify（唯一验证闸门）→ verify_<g>.json（钉死）。

## B4 合成结构锚点（机械直译，建议脚本化）
门级直译 spec_structural.v：SC_INV→~、SC_AND→&、SC_MFC→带 S/D0/D1 的 always、FF→`always @(posedge CP or negedge CDN)` 异步低有效清 0。只求可证，不求精简。纯 transliteration 无「猜」，**建议做成 gate2v.py** 消除手译笔误、且锚点全文不进上下文。

## B5 验证锚点（判）—— 同时钉死 ff_map
`check_equiv.py --mode comb`。
- PASS → **此刻 ff_map 成为权威**。
- FAIL → parse_cex 定位发散 FF → 只改该 FF 的 D 直译（或修 ff_map 对应）→ 重验。comb 反例必单拍、直指一锥。
⚠️ 锚点 PASS 只证「直译对 + 寄存器对应对」；**位序/分词的对错要到 Phase C 套上算术语义、再被 check_equiv 证明时才钉死**（锚点是门级直译，对位序错位不敏感）。

## B6 产出 Phase C 机器事实（清单必须齐全，不准悬空）
锚点 PASS 后，每 FF 跑 `decode_modes.py`：`--ctrl` = SC_MFC 的 S 引脚（读）+ 大模型识别的 COUNT/SET/HOLD/LOAD（猜）→ `modes/<ff>.json`。
**交付清单**：ff_map.json（已证）、candidate_words.json、verify/verify_<g>.json（每组 UNSAT + unsat_handle）、modes/<ff>.json。
全部就绪 → `Phase B: PASS`，写 `.tasks/`（每组一条，初始 pending，组 N+1 blockedBy 组 N）。
