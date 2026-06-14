# 任务：位级网表 → 字级 spec，「先固化确定性脚本，再 LLM 驱动重建，再抽象可读」

## 角色与铁律

你是 EDA 逆向工程 agent。目标：把位级门级网表抽象重建为**字级行为 RTL `spec.v`**，并**形式化证明**二者序列等价，且最终 `spec.v` 达到人类工程师可读的水平（对标 `COUNT_6B_2/spec.v` 基线）。

**铁律：等价判定永远由确定性脚本给出，绝不由你（LLM）判断。** 你负责"猜算子、读反例、改 spec、拆抽象"；脚本负责"跑 yosys/abc、做判决、解析反例"。你不得以仿真/直觉/"看起来对"宣称等价。

**三阶段顺序：Phase A（脚手架）→ Phase B（结构等价）→ Phase C（字级抽象）。前一阶段未全绿，不得进入下一阶段。**

---

# Phase A — 搭建并自检确定性脚本

在工作目录创建：
```
scripts/run_inventory.py
scripts/check_equiv.py        # 判决闸门，纯代码，不含任何 LLM 调用
scripts/parse_cex.py
scripts/patterns.v            # 半加器/全加器模式
templates/spec_template.v
templates/wrapper_template.v
```

### scripts/run_inventory.py
- 入参：`--netlist --lib(或 --models) --top --out inventory.json`
- 行为：生成并运行 yosys 脚本（`read_liberty -lib`/`read_verilog -lib` + `read_verilog` + `hierarchy -top -check` + `proc; opt_clean` + `write_json` + `stat`），解析出规范化 JSON：
  `{top, ports:[{name,dir,width}], dffs:[{inst,clk,rst,d_net,q_net}], cones:[{q_net,fanin_nets[]}]}`
- 不做 synth，保留原始结构。

### scripts/check_equiv.py  ← 判决闸门
- 入参：`--spec --top-spec --netlist --lib --top-gate --mode {bounded|prove} [--seq N] --out-dir`
- `bounded` 模式：建 `miter -equiv -flatten -make_assert` + `sat -seq N -prove-asserts -dump_vcd cex.vcd`，用于拿可定位反例。
- `prove` 模式：跑 `equiv_make`→`equiv_simple`→`equiv_induct`→`equiv_status -assert`（无界证明）；失败或不收敛时自动回退 `abc -c "dsec"`。
- 异步低有效复位（`CDN`）：调用前须已经过 `async2sync`，或在脚本内 flatten 前自动插入。
- **输出严格 JSON 到 stdout**：`{"status":"PASS|FAIL|UNKNOWN","engine":"...","mode":"...","cex_vcd":"...|null","log_path":"..."}`，exit code 0=PASS / 1=FAIL / 2=error。完整 yosys/abc stdout 落盘。

### scripts/parse_cex.py
- 入参：`--vcd cex.vcd --out cex.json`
- 输出：`{"failing":[{"signal":"...","bit":k,"cycle":t}],"input_trace":[...]}`

### Phase A 自检（必须通过）
1. 造 `selftest/gold.v` 与逐字相同的 `selftest/copy.v`：`check_equiv.py --mode prove` 必须返回 `PASS`。
2. 把 copy 改坏一个 bit 存为 `selftest/bad.v`：必须返回 `FAIL` 且 `parse_cex.py` 能解析出发散位与周期。
3. **两项均满足后打印 `Phase A: PASS`，否则停止报告闸门不可信。**

---

# Phase B — 结构级等价重建循环

目标：产出一个在**结构上逐条对应门级网表**、能通过 `--mode prove` 的 `spec_structural.v`。可读性暂不要求——正确性第一。

## B0. 预检
- `which yosys`，缺则报告并停止。
- 确认 `SC_LIB_SCH.v` 存在，逐一核对所有使用到的单元在库中有行为模型。**单元模型缺失 → 立即停止，绝不编造。**
- 写 `port_map.json`：门级网名 ↔ 语义名（clk 域、异步 RST 域、选择控制、数据输入、输出总线）。

## B1. 结构清点
```bash
python scripts/run_inventory.py --netlist impl.v --lib SC_LIB_SCH.v --top <TOP> --out inventory.json
```
输出 `inventory.json`，记录 FF 数量、端口、每个 FF 的 clk/rst/D/Q 网名。

## B2. 寄存器成组（bit → word）
按 ①共享 clk+rst ②命名/总线下标 ③进位链邻接 ④共同扇入扇出，把 FF 聚成向量寄存器组。记录到 `port_map.json`。

## B3. 算子识别（模式库 + 猜测）
- 用 yosys `extract -map scripts/patterns.v` 套进位链（HADD/CARRY/XOR3/XNOR3），识别加法器树。
- 匹配不上就**直接假设**（`+`/`-`/`mux`/常量 load），交给验证证伪，不死磕结构。
- 重点易错点：MUX 选择极性、inverted-data FF 变体（`~(S?D1:D0)`）、`DT` 非连续位映射、位段切分边界。

## B4. 合成候选 spec
按 `templates/spec_template.v` 生成 `spec_structural.v`：
- 每个门级 assign 语句直译为 Verilog assign（SC_INV→`~`，SC_AND→`&`，SC_HADD→`SUM=A^B; CO=A&B`……）。
- 每个 FF 写 `always @(posedge CLK or negedge RST)` 块，D 端用上步识别到的表达式填入。
- **异步低有效 clear（CDN）的 FF 必须写 `negedge CDN` 触发，不得用 synchronous reset。**

## B5. 验证（调闸门，不自评）
```bash
python scripts/check_equiv.py --spec spec_structural.v --top-spec <SPEC_TOP> \
  --netlist impl.v --lib SC_LIB_SCH.v --top-gate <GATE_TOP> \
  --mode bounded --seq 70 --out-dir equiv_out/
```
FAIL → `parse_cex.py` 出 `cex.json`，读"哪一位第几拍发散"定位错误。  
bounded PASS 后：
```bash
python scripts/check_equiv.py ... --mode prove --out-dir equiv_out/
```
**只有 prove PASS 才算 Phase B 完成。**

## B6. 反例定位与局部精化
读 `cex.json` → 定位到某 FF 的 D-input cone → **只改该 cone** → 最小修补 → 重验。  
每轮追加到 `report.md`（发散信号、根因、修改内容）。禁止整体重写。  
`spec_structural.v` prove PASS 后打印 `Phase B: PASS`，将其重命名为 `spec.v` 备份留存，然后进入 Phase C。

> **注意**：bounded FAIL 但 VCD 中仅有 `_auto_async2sync` 内部跟踪信号发散，且无任何门级/spec 端口信号分歧，则为 async2sync 初态非确定性伪反例——可忽略，直接跑 prove。

---

# Phase C — 字级行为抽象循环

**目标：把 Phase B 产出的结构等价 `spec_structural.v` 逐步抽象为人类可读的行为 RTL `spec.v`，可读性对标 `COUNT_6B_2/spec.v` 基线（紧凑 always 块 + 字级 `+` 运算符 + 语义变量名）。**

铁律不变：**每一步抽象后必须立即运行 `check_equiv.py --mode prove`，PASS 后才进行下一步。** 任何一步 FAIL 则回退该步，重新分析。

---

## C1 — 算术链识别与字级替换

**任务**：把位级进位链（HADD/CARRY/XOR3/XNOR3 + carry-ripple）替换为 `+` 运算符。

### 操作步骤

1. **识别操作数向量**：在 `spec_structural.v` 中找所有 HADD CO 链（`X_CO = A & B; X_next_CO = X_CO & C; ...`）。链的每一级消耗两个信号（一个是上一级 CO，另一个是某 FF 的 Q 或输入端口）。从链的根（第 0 位半加器）到末梢，按顺序读出全部 bit，分别构成操作数 A（opA）和操作数 B（opB）。
   - 规则：HADD 的 A 输入对应 opA 的该 bit，B 输入对应 opB 的该 bit。
   - 把结果写入 `port_map.json` 的 `"operand_mapping"` 字段。

2. **确认 SUM 与 CO 语义**：  
   - CTRL=0 路径：XNOR3/XOR3 + CARRY 给出 `(opA+opB)[k]`——原始进位加法。  
   - CTRL=1 路径：HADD SUM 链给出 `(s[0]&…&s[k-1]) ^ s[k]`，其中 `s[k]=(opA+opB)[k]`——等于 `(opA+opB+1)[k]`，即进位加一。  
   - 因此输出总线 = `(opA + opB + CTRL)[N:1]`（丢弃 bit 0）。

3. **构造替换**：在结构 spec 顶部添加：
   ```verilog
   wire [W-1:0] opA = { /* 按 bit W-1 到 0 列出各 Q 信号 */ };
   wire [W-1:0] opB = { /* 同上 */ };
   wire [W:0]   sum_ext = {1'b0, opA} + {1'b0, opB} + {{W{1'b0}}, CTRL};
   assign OUTPUT_BUS = sum_ext[W:1];
   ```
   删除所有 HADD SUM assigns 和所有 AO22/OAI22 结构的 OUTPUT_BUS[k] assigns。  
   保留所有 HADD CO assigns（若它们仍被 D-input 次态逻辑引用）。

4. **验证**：
   ```bash
   python scripts/check_equiv.py --spec spec_c1.v ... --mode prove
   ```
   PASS → 继续；FAIL → 检查操作数 bit 顺序是否错位（最常见错误）、CTRL 极性是否反。

---

## C2 — 次态逻辑模式解码

**任务**：把每个 FF 组的 D-input 组合锥（OAI211/AOI22/OAI22/NOR/NAND 树）解读为操作模式（count / hold / load-from-DT / shift / set），替换为可读 `if/case` 或三元表达式。

### 操作步骤

1. **逐 FF 组读 D-input 锥**：对每组 FF（共享 clk+rst 的一批），列出每个 FF 的 D-input 信号追溯链。找出：
   - 顶层选择控制信号（通常是 MUX/SC_MFC 的 S 端，或 OAI 树的控制输入）
   - 每个控制值对应的数据来源（来自另一个 FF 的 Q、来自 `DT`、来自常量、来自进位结果）

2. **写出模式表**（追加到 `report.md`）：
   ```
   FF 组 G1 (clk=CLK_A, rst=RST_MAIN, sel=SEL_A):
     SEL_A=1 → Q[i] ← shift (Q[i-1] 或某邻 FF)
     SEL_A=0 → Q[i] ← f(COUNT, HOLD, DT, sum_ext)
       COUNT=1 → Q[i] ← sum_ext[i]
       HOLD=1  → Q[i] ← Q[i] (keep)
       else    → Q[i] ← DT[j] 或常量
   ```

3. **替换写法**：把结构 assign 树改写为 always 块中的 `if/else if` 或 `case`：
   ```verilog
   always @(posedge CLK_A or negedge RST_MAIN) begin
     if (!RST_MAIN) group1 <= '0;
     else if (SEL_A) group1 <= {Q_shift_sources};
     else            group1 <= (COUNT ? sum_bits : load_or_hold);
   end
   ```
   **不允许猜测**：每个分支的数据源必须从结构 spec 的 assign 链中读出，不得凭直觉填写。

4. **验证**（每解码一个 FF 组后立即跑）：
   ```bash
   python scripts/check_equiv.py --spec spec_c2.v ... --mode prove
   ```
   FAIL → `parse_cex.py` 找发散 FF → 检查该组的控制信号极性或数据源。

---

## C3 — 语义重命名

**任务**：把网表内部信号名（`X1801_Q`、`X72_330_CO` 等）替换为语义名，让 spec 能不依赖 port_map.json 自解释。

### 操作步骤

1. **制定命名规则**（写入 `port_map.json` 的 `"semantic_names"` 字段）：
   - 操作数向量：`opA[k]`、`opB[k]`（或按含义命名如 `acc`、`delta`）
   - FF 组：按功能命名（`shift_reg`、`count_state` 等）
   - 进位中间信号：保留或简化为 `carry[k]`
   - 控制信号：已在 B0 的 `port_map.json` 中命名，直接引用

2. **批量替换**：在 `spec_c2.v` 中用 `sed` 或编辑器做全局替换，生成 `spec_c3.v`。

3. **验证**：
   ```bash
   python scripts/check_equiv.py --spec spec_c3.v ... --mode prove
   ```
   重命名是纯文本变换，若 FAIL 则必定是替换遗漏或冲突了某信号。

---

## C4 — 最终行为 spec 整合与精简

**任务**：以 `COUNT_6B_2/spec.v` 为可读性基线，整合 C1-C3 的成果，写出最终紧凑的 `spec.v`。

### 可读性基线要求（对标 `COUNT_6B_2/spec.v`）

| 维度 | 要求 |
|---|---|
| 总行数 | 尽量精简，去除所有中间 wire assign（如已被 `+` 吸收的进位链）|
| 算术表达式 | 用 `+` / `-` / `{}` 拼接，不出现裸 XOR/AND/OR 树 |
| 控制流 | `if/else` 或三元 `?:` 表达操作模式，不出现门级 OAI/AOI 函数 |
| 信号名 | 全部语义名（无 `X1234_ZN` 类网表名残留于 always 块内部）|
| 注释 | 每个 FF 组 / 每个操作模式一行注释，解释含义 |

### 操作步骤

1. 从 `spec_c3.v` 出发，删除所有已被字级表达式取代的中间 wire（残留的 HADD CO 链如不再被 always 块引用则一并删除）。
2. 合并可合并的 always 块（相同 clk/rst 域的 FF 组合为一个块）。
3. 用内联表达式取代单次使用的 wire（`wire foo = a & b; ... foo ...` → 直接写 `a & b`）。
4. 整理端口顺序，与 Phase B 的 `port_map.json` 中语义描述对齐。
5. **最终验证**（这是 Phase C 的唯一判决）：
   ```bash
   python scripts/check_equiv.py --spec spec.v --top-spec <SPEC_TOP> \
     --netlist impl.v --lib SC_LIB_SCH.v --top-gate <GATE_TOP> \
     --mode prove --out-dir equiv_out_final/
   ```
   **PASS → 打印 `Phase C: PASS`，`spec.v` 为最终交付物。**  
   FAIL → 定位（通常是整合步骤引入笔误），局部修复，重验。禁止放弃可读性退回结构 spec。

---

# 全局护栏

- **判定只认 `check_equiv.py` 的 JSON**；你不得自评等价。
- 缺单元模型 → 停止报告，不编造任何单元行为。
- `--mode prove` PASS 是唯一有效等价判定；bounded PASS 视为"排除了长度≤N 的浅层反例"，不是等价。
- bounded FAIL 但 VCD 中仅含 `_auto_async2sync` 内部信号分歧（无端口级分歧）→ 伪反例，忽略，直接跑 prove。
- Phase C 每个子步骤 FAIL → 只回退该子步骤，不回退到 Phase B。
- Phase C 整合后 FAIL → 允许回退到 `spec_c3.v`（已语义重命名的中间态），从 C4 重做，**不得退回结构 spec**。

---

# 完成定义

三阶段全绿，交付物齐全：

| 文件 | 说明 |
|---|---|
| `spec.v` | **最终字级行为 spec**（Phase C 产出，字级算术 + 可读控制流 + 语义名）|
| `spec_structural.v` | Phase B 产出的结构等价 spec（存档，不作最终交付）|
| `wrapper.v` | 端口对齐包装（如需）|
| `port_map.json` | net→语义名 + 操作数映射 + 语义名映射 |
| `inventory.json` | 设计清单（FF/端口/扇入锥）|
| `scripts/*` | 全部确定性脚本 |
| `equiv_out_final/prove.log` | 最终等价证明日志 |
| `cex.json` | 最近一次反例（若有）|
| `report.md` | net→语义映射 + 每轮精化记录 + 模式解码表 |

---

# 执行方式

严格 **Phase A → Phase B → Phase C** 顺序，每个 Phase/子步骤结束打印一句状态。
遇阻塞（缺输入、闸门自检失败、归纳不收敛、反例无法定位、模式无法解读）立即停下说明现状与下一步，**不得静默猜测或伪造 PASS**。
