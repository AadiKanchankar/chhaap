"""Flags every number in the paper that is not in eval/summary.md or eval/results/*.json.
Usage: python scripts/check_numbers.py paper/paper.tex   (exit 1 on any unmatched number)
Skipped: citation/label/ref/figure-file arguments, years 1900-2039, and numbers listed in paper/allowed_numbers.txt
(setup constants such as 512 px; each line there must say where the number comes from)."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
NUM = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?:e-?\d+)?(?![\w])")


def known():
    text = (ROOT / "eval/summary.md").read_text()
    for p in (ROOT / "eval/results").glob("*.json"):
        text += " " + json.dumps(json.loads(p.read_text()))
    vals = set(NUM.findall(text))
    for v in list(vals):  # accept any rounding of a real value to 1-3 decimals
        try:
            f = float(v)
        except ValueError:
            continue
        vals |= {f"{f:.{d}f}" for d in range(4)} | {str(int(f)) if f == int(f) else v}
    allowed = ROOT / "paper/allowed_numbers.txt"
    if allowed.exists():
        vals |= {l.split()[0] for l in allowed.read_text().splitlines() if l.strip() and not l.startswith("#")}
    return vals


def main(path):
    tex = Path(path).read_text()
    tex = re.sub(r"%.*", "", tex)
    tex = re.sub(r"\\(cite|ref|label|includegraphics|url|href|bibliography|bibliographystyle|documentclass|usepackage)(\[[^\]]*\])?\{[^}]*\}", " ", tex)
    tex = re.sub(r"\\begin\{(table|figure)\*?\}\[[^\]]*\]", " ", tex)
    tex = re.sub(r"\\[a-zA-Z]+\*?", " ", tex)  # strip command names, keep their arguments
    ok, bad = known(), []
    for n, line in enumerate(tex.splitlines(), 1):
        for m in NUM.findall(line):
            if 1900 <= abs(float(m)) <= 2039 and "." not in m:
                continue
            if m not in ok and m.lstrip("-") not in ok:
                bad.append(f"{path}:{n}: {m}")
    print("\n".join(bad) or "all numbers found in eval/summary.md or eval/results")
    return bool(bad)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
