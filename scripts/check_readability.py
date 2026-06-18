#!/usr/bin/env python3
"""
check_readability.py -- objective readability gate for spec.v
Exit 0=PASS (readable), 1=FAIL, 2=error.
Outputs strict JSON to stdout.

Rules:
  1. always blocks: zero X####_ netlist-name residues
  2. always blocks: no long bare boolean chains (>=3 consecutive &/| without parens)
  3. always blocks: D-assignments must be if/else / ?: / word-level, not raw NAND trees
  4. total line count <= max_line_ratio * ff_count
"""
import argparse, json, re, sys


# ---------------------------------------------------------------------------
# Always-block extraction (tracks begin/end nesting)
# ---------------------------------------------------------------------------
def extract_always_blocks(text):
    blocks = []
    i = 0
    n = len(text)
    while i < n:
        m = re.search(r'\balways\b', text[i:])
        if not m:
            break
        start = i + m.start()
        # Find 'begin'
        bi = text.find('begin', start)
        if bi == -1:
            i = start + 1
            continue
        depth = 0
        pos = bi
        while pos < n:
            if text[pos:pos+5] == 'begin':
                depth += 1
                pos += 5
            elif text[pos:pos+9] == 'endmodule':
                pos += 9
            elif text[pos:pos+7] == 'endcase':
                pos += 7
            elif text[pos:pos+3] == 'end':
                depth -= 1
                if depth == 0:
                    blocks.append(text[start: pos + 3])
                    pos += 3
                    break
                pos += 3
            else:
                pos += 1
        i = pos
    return blocks


def strip_comments(text):
    # Remove // … to end-of-line
    return re.sub(r'//[^\n]*', '', text)


# ---------------------------------------------------------------------------
# Rule 1: no X####_ patterns inside always blocks
# ---------------------------------------------------------------------------
NETNAME_RE = re.compile(r'\bX\d+_')

def check_no_netnames(blocks):
    violations = []
    for i, blk in enumerate(blocks):
        clean = strip_comments(blk)
        hits = NETNAME_RE.findall(clean)
        if hits:
            violations.append({
                "rule": "no_netlist_names_in_always",
                "always_index": i,
                "examples": list(dict.fromkeys(hits))[:5],
            })
    return violations


# ---------------------------------------------------------------------------
# Rule 2: no long bare boolean chains (≥3 chained & or |)
# ---------------------------------------------------------------------------
# Matches sequences like  A & B & C  or  A | B | C  with no intervening ()
LONG_BOOL_RE = re.compile(r'\b\w[\w\[\]]*\s*(?:[&|^]\s*\b\w[\w\[\]]*\s*){2,}')

def check_no_long_bool_chains(blocks):
    violations = []
    for i, blk in enumerate(blocks):
        clean = strip_comments(blk)
        # Remove content inside balanced parens at depth≥1 so sub-expressions don't count
        flat = re.sub(r'\([^()]*\)', '', clean)
        hits = LONG_BOOL_RE.findall(flat)
        if hits:
            violations.append({
                "rule": "no_long_boolean_chains",
                "always_index": i,
                "examples": hits[:3],
            })
    return violations


# ---------------------------------------------------------------------------
# Rule 3: D-assignments must not be raw NAND/NOR expressions
#   Heuristic: a single `<=` that is followed by ~(...&...&...) or ~(...|...|...)
#   without an enclosing if/else or ?:
# ---------------------------------------------------------------------------
RAW_NAND_RE = re.compile(
    r'<=\s*~\s*\((?:[^()]*&[^()]*){2,}\)'   # <= ~(A & B & C)
    r'|'
    r'<=\s*~\s*\((?:[^()]*\|[^()]*){2,}\)'  # <= ~(A | B | C)
)

def check_control_flow(blocks):
    violations = []
    for i, blk in enumerate(blocks):
        clean = strip_comments(blk)
        hits = RAW_NAND_RE.findall(clean)
        if hits:
            violations.append({
                "rule": "no_gate_level_d_input",
                "always_index": i,
                "count": len(hits),
                "example": hits[0][:80],
            })
    return violations


# ---------------------------------------------------------------------------
# Rule 4: total line count
# ---------------------------------------------------------------------------
def check_line_count(text, max_ratio, n_ffs):
    lines = text.count('\n')
    limit = int(max_ratio * max(n_ffs, 1))
    if lines > limit:
        return [{"rule": "line_count", "lines": lines,
                 "limit": limit, "ff_count": n_ffs}]
    return []


def count_ffs(text):
    # Count scalar 'reg' and vector 'reg [...]' declarations
    return max(len(re.findall(r'\breg\b', text)), 1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--top")
    ap.add_argument("--max-line-ratio", type=float, default=16.0,
                    help="Max lines / FF count (default 16)")
    ap.add_argument("--ff-count", type=int, default=0,
                    help="Override FF count (auto-detected if 0)")
    args = ap.parse_args()

    try:
        with open(args.spec) as f:
            text = f.read()
    except FileNotFoundError:
        print(json.dumps({"readable": False,
                          "violations": [{"rule": "file_not_found",
                                          "path": args.spec}]}))
        sys.exit(2)

    blocks = extract_always_blocks(text)
    n_ffs = args.ff_count if args.ff_count > 0 else count_ffs(text)

    violations = []
    violations += check_no_netnames(blocks)
    violations += check_no_long_bool_chains(blocks)
    violations += check_control_flow(blocks)
    violations += check_line_count(text, args.max_line_ratio, n_ffs)

    readable = len(violations) == 0
    result = {
        "readable": readable,
        "always_block_count": len(blocks),
        "ff_count": n_ffs,
        "violations": violations,
    }
    print(json.dumps(result, indent=2))
    sys.exit(0 if readable else 1)


if __name__ == "__main__":
    main()
