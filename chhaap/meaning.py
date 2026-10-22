"""Placed symbol ids -> meaning card from lexicon rows. A template, no LLM: every line comes from data/lexicon.csv.
v2: the card splits symbols that survived generation from those placed but lost, and a story caption is built from the
plan and lexicon names only; caption_ok() rejects any caption that names a lost symbol or adds a meaning sentence."""
from collections import Counter

from .compose import LEXICON

FOOTER = "Meanings not yet verified by a Warli artist."
FOOTERS = {"mandana": "Meanings not yet verified by a Mandana artist.", "both": "Meanings not yet verified by a Warli or Mandana artist."}
FUSION_NOTE = ("This design mixes Warli and Mandana motifs. Fusion is a contemporary design practice, not a traditional form; "
               "the two arts come from different communities and regions.")
LINE = "{name}{local}: {meaning} Context: {context} Source: {source_url}"
LOST_NOTE = ("These symbols were planned, but the design may not show them: either the layout had no room for them, "
             "or the model did not draw them clearly enough to pass the survival check. Fillers are never repaired.")
NONE_LOST = "None. Every planned symbol is in the design; the survival check repaired any the model lost."
TEMPLATE_PHRASE = {"tarpa_spiral": "Dancers ring the {hero}.", "registers": "The story runs in bands from top to bottom.",
                   "medallion": "The {hero} sits at the centre, with scenes in the four corners.",
                   "all_over_buti": "Small motifs repeat across the cloth.", "strip": "A border band.",
                   "mandana_medallion": "Rings of motifs turn around the {hero}, symmetric on eight axes."}


def _rows(counts):
    return [{**LEXICON[i], "count": n} for i, n in counts.items()]


def _text(rows):
    return "\n".join(LINE.format(**r, local=f" ({r['local_name']})" if r["local_name"] else "") for r in rows)


def card(placed_ids, present_ids=None):
    """placed_ids: ids in placement order (repeats = count). present_ids: ids that survived (None = all of them).
    Returns {symbols (present rows), lost (rows), text, footer, lost_note}."""
    placed = Counter(i for i in placed_ids if i in LEXICON)
    present = placed if present_ids is None else Counter(i for i in present_ids if i in LEXICON)
    rows, lost = _rows(present), _rows({i: n for i, n in placed.items() if i not in present})
    packs = {LEXICON[i]["pack"] for i in placed}
    foot = FOOTERS["both"] if len(packs) > 1 else FOOTERS.get(next(iter(packs), "warli"), FOOTER)
    rows.sort(key=lambda r: r["pack"] != "warli")  # grouped by art form, Warli first
    text = _text(rows) + (f"\nPlaced but lost in generation:\n{_text(lost)}" if lost else "")
    return {"symbols": rows, "lost": lost, "text": f"{text}\n{foot}", "footer": foot, "lost_note": LOST_NOTE if lost else NONE_LOST,
            "packs": sorted(packs), "fusion_note": FUSION_NOTE if len(packs) > 1 else ""}


def caption(plan, present_ids):
    """One or two sentences from the plan, naming only symbols that survived."""
    ok = set(present_ids)
    hero = LEXICON[plan["hero_symbol_id"]]["name"]
    out = [TEMPLATE_PHRASE[plan["template"]].format(hero=hero if plan["hero_symbol_id"] in ok else "central figure")]
    beats = []
    for b in plan["story_beats"]:
        names = list(dict.fromkeys(LEXICON[i]["name"] for i in b["symbol_ids"] if i in ok))
        if names:
            beats.append(f"{b['beat']} ({', '.join(names)})")
    if beats:
        out.append("The beats: " + "; then ".join(beats) + ".")
    return " ".join(out)


def caption_ok(text, present_ids):
    """True if the caption names no symbol outside present_ids and repeats no lexicon meaning."""
    ok = {LEXICON[i]["name"] for i in present_ids if i in LEXICON}
    low = text.lower()
    named = {r["name"] for r in LEXICON.values() if r["name"].lower() in low}
    named -= {n for n in named if any(n != m and n.lower() in m.lower() and m in ok for m in named)}  # "woman" inside "woman carrying a pot"
    return named <= ok and not any(r["meaning"].lower()[:40] in low for r in LEXICON.values())


if __name__ == "__main__":
    c = card(["tree", "tree", "sun", "ladder"], ["tree", "sun"])
    assert [r["id"] for r in c["symbols"]] == ["tree", "sun"] and [r["id"] for r in c["lost"]] == ["ladder"] and c["lost_note"] != NONE_LOST
    assert card(["tree"])["lost"] == [] and card(["tree"])["text"].endswith(FOOTER)
    plan = {"template": "registers", "hero_symbol_id": "kansari", "story_beats": [{"beat": "sowing", "symbol_ids": ["farmer", "ladder"]}]}
    t = caption(plan, ["kansari", "farmer"])
    assert "ladder" not in t and caption_ok(t, ["kansari", "farmer"]) and not caption_ok(t + " A ladder.", ["kansari", "farmer"])
    print("meaning ok:", t)
