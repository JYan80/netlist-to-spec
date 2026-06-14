# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A **hardware reverse engineering and formal equivalence verification** workspace. Gate-level netlists from a proprietary ASIC library (`HCQ_2404150`) are reverse-engineered into behavioral RTL specifications, then formally proven equivalent using Yosys.

## Running equivalence checks

```bash
# Run a completed equivalence check (COUNT_6B_2 is the worked example)
cd COUNT_6B_2
yosys equiv.ys

# Or from the repo root using the system yosys
yosys COUNT_6B_2/equiv.ys

# Or using the bundled yosys submodule (if built)
yosys/yosys COUNT_6B_2/equiv.ys
```

The script passes if `equiv_status -assert` emits no error. Any "unproven" or "not equivalent" output indicates a mismatch between `impl.v` and `spec.v`.

## Yosys equivalence check script structure

`equiv.ys` (see `COUNT_6B_2/equiv.ys`) always follows this pattern:

1. Read `SC_LIB_SCH.v` + `impl.v` + `spec.v`
2. `prep -top <impl_module>` → `flatten` → `async2sync` → `design -save impl`
3. Reset, re-read, `prep -top <spec_module>` → `flatten` → `async2sync` → `design -save spec`
4. `design -copy-from impl -as gate <impl_module>` and `-copy-from spec -as gold <spec_module>`
5. `equiv_make gold gate equiv` → `hierarchy -top equiv` → `equiv_simple` → `equiv_induct` → `equiv_status -assert`

`async2sync` is required because the flip-flops use asynchronous active-low clear (`CDN`).

## Directory layout

| Directory | Contents |
|---|---|
| `COUNT_6B_2/` | Complete example: impl netlist + behavioral spec + `equiv.ys` |
| `COUNT_12BX2/` | Complex 12-bit counter; impl + library only, spec not yet written |
| `Netlist/` | Hierarchical netlist (`SC_HIER.v`) using a subset of the SC library |
| `yosys/` | Yosys source tree (submodule) |

Each working directory contains its own `SC_LIB_SCH.v` — a Verilog behavioral model of the standard cell library required by that netlist. `Netlist/SC_HIER.v` re-defines only the specific cells it uses rather than pulling in the full library.

## Standard cell library conventions

All cells in `SC_LIB_SCH.v` follow `SC_<FUNCTION>_<WIDTH>_<HEIGHT>[variant]`. The `GS` (ground) and `VS` (supply) pins are present on every cell but carry no logic; they can be ignored when reading or writing Verilog.

Key sequential cells:
- `SC_MFC_*` — Mux-D flip-flop with async clear (`CDN`). `S=0` → `D0`, `S=1` → `D1`. This is the dominant register type.
- `SC_DFC_*` — Standard D flip-flop with async clear.
- `SC_DFB_*` / `SC_MFB_*` — Variants with both async clear (`CDN`) and async set (`SDN`).
- `SC_MFC_140_80S1` / `SC_MFS_140_80` — **Inverted-data variants**: these store `~(S ? D1 : D0)`, not the raw mux output. Don't miss this when reading the netlist.

Key arithmetic cells:
- `SC_CARRY_140_80` — Full carry: `CO = (A&B)|(A&CI)|(B&CI)`. No sum output.
- `SC_HADD_140_80` — Half adder: `SUM = A^B`, `CO = A&B`.
- `SC_XOR3_E140_90` / `SC_XNOR3_140_E90` — 3-input XOR/XNOR. Used for sum bits in multi-bit adder trees.

Active-low signals use the `N` suffix (e.g., `CDN` = clear-active-low, `ZN` = inverted output).

## Writing a behavioral spec

The spec module must have a **different top-level name** from the impl module (e.g., `COUNT_6B_2_spec` vs `COUNT_6B_2`) so both can coexist in the same Yosys design. Port names and directions must match the impl exactly. Use `always @(posedge CLK or negedge RST)` with `async2sync` handling the reset polarity.

See `COUNT_6B_2/spec.v` for a complete example of a reverse-engineered behavioral spec.

## COUNT_12BX2 complexity notes

COUNT_12BX2 is significantly harder than COUNT_6B_2. Key differences to account for when writing its spec:

- **Two clocks**: `X1026_138_ZN` (used by the `MI1_QT` output registers and `X1805`/`X1806`) and `X1027_138_ZN` (used by most internal state registers).
- **Two reset domains**: most FFs use `X3_323_Z` as `CDN`; `X1795`, `X1798`, and `X1800` use `X1676_Z` instead.
- **Two mux-select inputs**: `X8710_Z` (selects `D1` for the `MI1_QT`-domain FFs) and `X412_46_Z` (for the `X1027` clock domain).
- **Arithmetic carry chain**: the `MI1_SUM[1:11]` outputs are formed from a tree of `SC_CARRY_140_80`, `SC_HADD_140_80`, `SC_XOR3`, and `SC_XNOR3` cells that add multiple internal register values together.
- **Output muxing via CTRL0/CTRL1/CTRL2**: the final `MI1_SUM` values are selected between two computed results using `SC_AO22` (for `CTRL0`) and `SC_OAI22`/`SC_OAI211` (for the carry inputs to the D-inputs of state FFs via `CTRL1`/`CTRL2`).
