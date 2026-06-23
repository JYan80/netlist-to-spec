---
name: abstract-group
description: |
  Phase C, once per FF group in a clean context. Load to turn ONE group's machine
  facts into a clean, IDIOMATIC always-block and prove it combinationally. Operator
  + operands + bit-order are ALREADY fixed upstream (proven UNSAT by grow_patterns)
  and must NOT be re-guessed; but semantic naming + idiomatic control-flow are real
  LLM design, not transcription. Use only this group's facts. Iron laws live in
  CLAUDE.md. Keywords: word-level abstraction, idiomatic RTL, semantic naming, Phase C.
---

# Phase C（单组）— 机器事实 → 干净 idiomatic always 块 → 组级组合证明

铁律见 CLAUDE.md。本文件只列 Phase C 独有步骤。
你在干净子上下文里**只处理一个 FF 组**（上游已按共享进位链聚好、并对算术支证过 UNSAT）。

## 两半性质（认清才不空转）
- **既成事实（不准重猜）**：算子身份、操作数 busA/busB、位序——grow_patterns verify 已 ABC 证 UNSAT。重猜加/减就是错。
- **真·大模型设计（无确定性来源可替代，必须你来）**：语义命名（opA→counter_q）、控制流 idiom 化（cofactor 表 → 自然 if/else / ?:）。
> ⚠️ **不是「转写」。** 那个词会让你当抄写员、产出丑命名、卡可读性空转。你在**设计给人读的 RTL**：既成事实约束语义，命名与结构是你的设计自由，也是本阶段的全部意义。

## 输入（只这一组，齐全不悬空；缺失/blocked → 别臆造，回 grow_patterns）
- `modes/<ff>.json`：每成员 FF 的 cofactor 模式表（每支化简表达式 + cond 顺序，权威数据源）。
- `ff_map.json`：命名权威（已 B5 证）。`candidate_words.json`：位序权威。
- `verify/verify_<g>.json`：已 UNSAT 的字级算子 + 操作数叶子映射 + bit_order + carry_in + unsat_handle。

**不读别组门级细节、不读锚点全文**（那是上下文撑爆、退回逐门心算的根因）。
输出：`spec_c<N>.v`，只含本组 always 块 + 本组字级 wire。回传：路径 + 命名映射摘要。

## C1 实例化已证字级算子（不是重新构造）
算子/操作数来自 verify 产物，位序来自 candidate_words。**一条进位链 = 一个总线运算，被成员 FF 当作各 bit slice 共享**——写一次字级表达式覆盖整组，别逐 FF 写门级锥。
```verilog
wire [10:0] opA = { ... };   // = verify 产物 busA
wire [10:0] opB = { ... };   // = verify 产物 busB
wire [11:0] sum_ext = {1'b0,opA} + {1'b0,opB} + CTRL0;   // op 由 verify 证过
```
进位比较链字级化：`carry_a[k]/carry_b[k]/carry_cmp[k]`（名字你设计，语义忠于 verify）。
⚠️ 若 `MI1_SUM` 在本组：门级是 `CTRL0 ? 加法和 : 比较路径`，**非无条件 opA+opB**——modes 给两个 cofactor，verify 分支各证，**按两支分别转写**，漏 CTRL0=0 必挂。

## C2 模式表 → idiomatic 控制流（按 cond 优先级照抄 modes，不重排）
```verilog
always @(posedge CLK_x or negedge RST_y) begin
  if (!RST_y)    grp <= '0;
  else if (load) grp <= {shift_sources};
  else if (set)  grp <= set_data;
  else if (hold) grp <= grp;
  else           grp <= count_sources;   // = C1 字级运算对应 bit
end
```
`load/set/hold` 是**语义名**（你设计的），不是网表网名。

## C3 语义命名（覆盖全部组合中间网）
命名依据 = ff_map + candidate_words；在此之上，所有 always 块/字级 wire 里的中间网（carry_*、sum_ext、opA/opB…）都要有**达意语义名**。无脚本能替你起名——起得好不好决定像不像人写的。替换后 always 块内零 `X####_`。
（可读性两道关：语法下限是确定性闸门 check_readability；真可读性是软信号、refine 的方向，见 CLAUDE.md 防 Goodhart。）

## C4 组级组合证明
写出 `spec_c<N>.v` 后跑 `check_equiv --mode comb`（+ readability 下限）。读 `failing_ff`/`bit` 定位发散支：
- **算术支** → 算子已证，几乎一定是**转写错**（位序/bit slice/命名）。对照 verify + candidate_words 改这条，**别改算子**。
- **控制赋值（load/set/hold…）** → 该分支数据源/位序/优先级错，改这条。
- **cycle 0** → 复位值错。
仅改本组，不碰别组。

> 连续 3 次仍 FAIL：不硬磕、不伪造，回传 `blocked + 最后 cex`，走升级阶梯：
> - cex 指向**算术恒等本身**（非转写细节）→ 上游分组/操作数选错，回 grow_patterns 复核分组/verify，别在 C 硬凑。
> - 否则：扩 ctrl 集重跑 decode_modes → 退 seq 模式 → 请人介入。
