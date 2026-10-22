"""Prose linter for docs/WRITING_RULES.md. Usage: python scripts/lint_prose.py FILE [FILE...]  (exit 1 on any hit)"""
import re
import sys

BANNED = ("delve tapestry landscape realm intricate nuanced multifaceted pivotal crucial vital underscore underscores "
          "underscored highlight highlights highlighted highlighting showcase showcases garner foster fosters enhance "
          "enhances enhanced leverage leverages navigate navigating robust comprehensive testament enduring vibrant "
          "meticulous commendable resonate resonates embark unlock elevate ever-evolving stunning breathtaking "
          "world-class game-changing utilize utilizes facilitate facilitates notably interestingly").split()
PATTERNS = [
    (r"\b(" + "|".join(map(re.escape, BANNED)) + r")\b", "banned word"),
    (r"\balign(s|ed)? with\b|\bin today's world\b|\brich heritage\b", "banned phrase"),
    (r"\b(moreover|furthermore|additionally|in conclusion|overall|ultimately)\b", "transition word"),
    (r"\bnot only\b|\bit'?s not just\b|\bnot (?:just |merely |simply )?\w+(?: \w+){0,3}, but\b", "not-X-but-Y"),
    (r"[‘’“”]", "curly quote"),
    (r"(?<![\w}\\!])\[(?!@)(?![\d, -]+\])[^\]\n]*\](?!\()|\bXX+\b|\bTBD\b|\bTODO\b", "placeholder"),
    (r", (highlighting|reflecting|ensuring|underscoring)\b", "tacked-on participle"),
    (r"\b(it is important to note|it is worth mentioning|stands as|serves as|boasts)\b", "editorializing"),
]


def lint(path):
    text = open(path, encoding="utf-8").read()
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        line = re.sub(r"\$[^$]*\$|https?://\S+|\\url\{[^}]*\}", "", line)  # inline maths, URLs
        for pat, why in PATTERNS:
            for m in re.finditer(pat, line, re.I):
                hits.append(f"{path}:{n}: {why}: {m.group(0)!r}")
    words = len(text.split())
    dashes = text.count("—") + text.count("---") - text.count("----")
    if dashes > max(1, words // 500):
        hits.append(f"{path}: em dashes: {dashes} in {words} words (limit {max(1, words // 500)})")
    return hits


if __name__ == "__main__":
    out = [h for p in sys.argv[1:] for h in lint(p)]
    print("\n".join(out) or "clean")
    sys.exit(bool(out))
