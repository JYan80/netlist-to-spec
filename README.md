# RE-Agent harness（task.md 的 harness 化重构）

把原来「一份 3 阶段巨型过程脚本」拆成 **薄常驻 prompt + 按需 skill + 编排器 + 验证钩子**。
核心改变：**推进信号从「模型自评」改成「闸门 exit code」**，模型没有「自己宣布 PASS」的入口。

## 文件 → 老 task.md 的对应

| 新文件 | 取代老 task.md 的 | harness 机制 |
|---|---|---|
| `SYSTEM.md` | 角色/铁律/全局护栏/完成定义（精简后常驻） | 薄 system prompt（s07 渐进披露） |
| `skills/build-scripts/SKILL.md` | Phase A 全文 | 按需加载，建完即忘 |
| `skills/anchor/SKILL.md` | Phase B 全文 | 按需加载 |
| `skills/abstract-group/SKILL.md` | Phase C 单组循环 | 每组一次，配子 agent |
| `driver.py` | 「执行方式」+ 阶段推进 + 护栏 | 编排器：按 exit code 推进（s01/s12） |
| `hooks.py` | 散落各处的「此处该跑 check_equiv」 | PostToolUse 钩子：写 spec 即自动验证（s04/s20） |
| `refs/` | patterns 库说明 / van Eijk 依据 / 库单元语义 | 用时再 fetch，不常驻 |
| `scripts/` | 原样保留你的确定性脚本 | 工具层：yosys 咒语藏在这里 |

## 这套结构怎么堵住「159 行漂亮但不等价、还自报成功」

1. **钩子（hooks.py）**：每写一版 `spec*.v` 当场验证，过不了就把反例塞回去、阻止推进。
   「先验证」不再是会被遗忘的指令。
2. **子 agent 隔离（driver 的 run_subagent）**：每组干净上下文，只喂这组机器事实，
   不让门级噪声把注意力挤掉、退回手写 De Morgan（159 行那版的病根）。
3. **唯一判决（driver + 铁律）**：推进只认 `check_equiv` 的 exit code。
4. **升级阶梯（retry_ladder）**：失败有上限、能升级、不许伪造。
5. **任务图（.tasks/）**：已证明的组成为不可回退的锚，跨 session 可恢复。

## Quickstart

```bash
# 0) 放好你的确定性脚本与设计文件
#    scripts/{check_equiv,decode_modes,check_readability,run_inventory,parse_cex}.py
#    scripts/patterns.v  impl.v  SC_LIB_SCH.v

# 1) 接钩子（Claude Code settings.json）
#    PostToolUse matcher "Write|Edit" → command: python3 /path/re-agent/hooks.py

# 2) 跑编排器
python driver.py --design COUNT_12BX2 --impl impl.v --lib SC_LIB_SCH.v
```

## 你需要补的两处 `# ADAPT`（已在代码里标注）
- `driver.run_subagent()`：换成你的 Claude Code CLI headless 调用（`claude -p ...`）。
- 各 `run_gate(...)` 的命令行实参：对齐你 `scripts/` 里脚本的真实参数；
  Phase A 的自检入口 `selftest_gates.py` 也按你的实现接上。
- `hooks.py` 顶部注释：按你当前 Claude Code 版本的 hooks 文档核对 stdin 字段名与阻止约定。

> 注：`SYSTEM.md` 与各 `SKILL.md` 是给模型读的；`driver.py`/`hooks.py` 是 harness。
> 别把 yosys/abc 命令、cofactor 实现、De Morgan 规则写回给模型的正文——那些只该住在 `scripts/` 里。
