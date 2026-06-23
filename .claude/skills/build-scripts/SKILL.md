---
name: build-scripts
description: |
  Phase A. Load when building or self-testing the deterministic EDA scripts in
  scripts/ (run_inventory, check_equiv, grow_patterns, decode_modes,
  check_readability, parse_cex, patterns.v). These scripts only READ facts and
  JUDGE machine-checkable claims — they never guess word-level structure.
  Iron laws live in CLAUDE.md; this file is only Phase A's own steps. Keywords:
  yosys, abc, equivalence gate, cofactor, grow_patterns, self-test, Phase A.
---

# Phase A — 建并自检确定性脚本

铁律见 CLAUDE.md（读/猜/判、等价唯一判决、大文件不进上下文）。本文件只列 Phase A 独有步骤。

目标：把「机械可算 / 可机器判决」的事固化成脚本，并**自检证明闸门可信**。闸门不可信，后续全无意义。
所有 yosys/abc 咒语藏在脚本内部；脚本契约 = 吃大文件、吐严格 JSON。

## 脚本契约（scripts/）

| 脚本 | 动词 | 输入 → 输出 / exit |
|---|---|---|
| `run_inventory.py` | 读 | `--netlist --lib --top --out inventory.json` → FF 清单 + 每 FF clk/rst/rst_pol/D 锥支持集 + **candidate_words**（位切片枚举的**候选**向量，非既成事实） |
| `check_equiv.py` | **判** | `--spec --top-spec --netlist --lib --top-gate --ff-map --mode {comb\|seq} --out-dir` → 严格 JSON + exit `0/1/2`。**全工程唯一的等价判决来源。** |
| `grow_patterns.py` | **判** | 子命令 `report/recheck/verify`，验证**外部喂入**的字级算子假设（见下），绝不发明算子 |
| `decode_modes.py` | 读/算 | `--netlist --lib --top --ff <q> --ctrl <c,...> --out modes.json` → Shannon cofactor 模式表 |
| `check_readability.py` | **判（下限）** | `--spec --top --max-line-ratio K` → `{readable,violations}` + exit `0/1`；另 `--score` 梯度模式 |
| `parse_cex.py` | 读 | `--vcd cex.vcd --out cex.json` → `{failing:[{signal,bit,cycle}], input_trace}` |
| `patterns.v` | 读 | extract 模式库：加/减/比较(进位)/增量/MUX/移位 |

## check_equiv.py 内部要点（最重要，务必正确）
方法学：**寄存器对应 → 组合等价 (CEC)**，不走序列归纳（van Eijk TCAD'00：1:1 对应+状态编码不变时序列等价约简为组合等价）。
- 两侧 flatten；按 `ff_map.json` rename FF 输出为 spec 规范名——**对应来自 ff_map，绝不靠名字猜**。
- 证明目标 = 对应 FF 的 D 全等 **＋ 所有输出端口全等**。⚠️ `MI1_SUM[11:1]` 是组合输出且回灌次态，必须列为目标，不能只证 FF 的 D。
- 复位对齐：两侧异步清 0、rst_pol 一致即可，无需 async2sync。
- 切除供电网 `X19_GS/X19_VS`（don't-care），否则报无意义 mismatch。
- `seq` 兜底：仅当寄存器无法 1:1 对应，`abc -c dprove`。
- stdout：`{"status":"PASS|FAIL|UNKNOWN","cex_vcd":"...|null","failing_ff":"...|null","log_path":"..."}`

## grow_patterns.py —— 算子假设的验证闸门（只判不猜）
接收**上层喂入**的算子假设，用 ABC 证「这组 FF 的 D（或算术支 cofactor）= 该字级算子对应 bit」的 UNSAT/SAT。**绝不自己发明算子/挑操作数。**
`verify` 契约（即 Phase C 消费的 verify 产物来源）：
```
verify --netlist --lib --top --group <ff,...> --op {add|sub|cmp|inc} \
       --busA <leaf,...> --busB <leaf,...> --bit-order <cw_id> --carry-in <sig|0|1> \
       --out verify_<g>.json
→ {"status":"UNSAT|SAT|UNKNOWN","op","busA","busB","bit_order","carry_in","unsat_handle","cex_vcd"}
```
UNSAT → 算子被钉死，成 Phase C 既成事实。SAT → cex 回传大模型改假设，**grow_patterns 自己不改**。
`report`：列进位链成员 + 共享 w_X86xx 节点 + 候选叶子。`recheck`：复核既有 verify 是否仍成立。

## decode_modes.py
给定控制集对 D 锥做 Shannon cofactor（确定）。控制集 = SC_MFC 的 `S` 引脚（脚本读）+ 大模型识别的 COUNT/SET/HOLD/LOAD（猜，由 `--ctrl` 传入，本脚本不做语义识别）。

## check_readability.py
`--top`（下限闸门）：①always 块内零 `X####_` 残留 ②无长度>2 裸 `&|^` 链 ③每个 D 赋值是字级算术或 if/else/?: 分支，非 OAI/AOI/NAND 直译 ④总行数 ≤ K×FF 数（K=16）。任一不满足 → exit 1。
`--score`（梯度，供 refine）：返回语法卫生归一化分 + 各维度，按 FF 数/位宽归一使 6B 与 12BX2 可比。**它是语法卫生梯度，不是真好读分**（见 CLAUDE.md 防 Goodhart）。

## Phase A 自检（5 项全过才 `Phase A: PASS`，任一不过 → 停，报「闸门不可信」）
1. 等价·不冤：`gold.v` vs 逐字相同 `copy.v` → comb **PASS**（恒等自比，永远必须过）。
2. 等价·不纵：`copy.v` 改坏 1 bit → **FAIL** 且 parse_cex 解出发散 FF 与单拍。
3. cofactor：decode_modes 在已知 2:1-mux-FF 小样例产出正确两行模式表。
4. 可读性辨垃圾：故意留 `X123_ZN` 样例 → `false`；干净样例 → `true`。
5. 算子闸门·不冤不纵：grow_patterns verify 对正确加法器假设 → **UNSAT**；对改坏一位/错算子 → **SAT+cex**。
