"""Brief -> structured plan. The planner picks layout, story beats, symbols (lexicon ids only), palette and density.
It never draws and never writes meanings. Backends, in order: rules (always), Ollama (if installed), Claude Code headless
(only with CHHAAP_PLANNER=claude; uses the user's quota, tokens logged). A plan naming an unknown symbol is rejected;
an LLM backend retries once, then the rules plan is used."""
import json
import os
import re
import shutil
import subprocess
import time
from typing import Literal, Optional

from pydantic import BaseModel, field_validator, model_validator

from .compose import LEXICON
from .layout import BORDERS, TEMPLATES

PALETTE_IDS = ["white_on_geru", "white_on_maroon", "white_on_indigo", "white_on_charcoal",
               "mustard_rust_cream", "teal_ochre_white", "indigo_coral_cream", "forest_saffron_ivory"]
PRODUCT_IDS = ["frame_a4", "frame_a3", "saree", "diary", "wallpaper", "phone", "tee"]
OLLAMA_MODEL = "qwen2.5:3b-instruct"


class Beat(BaseModel):
    beat: str
    symbol_ids: list[str]

    @field_validator("symbol_ids")
    @classmethod
    def known(cls, v):
        bad = [i for i in v if i not in LEXICON]
        if bad or not v:
            raise ValueError(f"symbols not in lexicon: {bad}")
        return v


class Plan(BaseModel):
    product: Literal[tuple(PRODUCT_IDS)]
    template: Literal[tuple(TEMPLATES)]
    density: Literal["sparse", "balanced", "dense"]
    repeat: Optional[Literal["straight", "half_drop", "brick"]] = None
    palette_id: Literal[tuple(PALETTE_IDS)]
    border_style: Optional[Literal[tuple(BORDERS)]] = None
    story_beats: list[Beat]
    hero_symbol_id: str
    notes: str = ""

    @field_validator("hero_symbol_id")
    @classmethod
    def hero_known(cls, v):
        if v not in LEXICON:
            raise ValueError(f"hero not in lexicon: {v}")
        return v

    @model_validator(mode="after")
    def beats_range(self):
        if not 1 <= len(self.story_beats) <= 4:
            raise ValueError("1 to 4 story beats")
        return self


# ---------- rules backend ----------
STORIES = {  # beats in narrative order; hero first. Every id is a lexicon row.
    "harvest": ("kansari", [("sowing", ["farmer", "bird", "sun"]), ("reaping", ["kansari", "tree", "ladder"]), ("dance at night", ["tarpa_player", "woman", "moon"])]),
    "wedding": ("lagna_chauk", [("procession", ["drummer", "tarpa_player", "horse"]), ("the marriage square", ["lagna_chauk", "pachsera_deva"]),
                                ("celebration", ["woman", "man", "tree", "bird"])]),
    "tarpa": ("tarpa_player", [("evening", ["sun", "hut", "tree"]), ("the dance", ["tarpa_player", "drummer", "woman", "human"]), ("night", ["moon", "bird"])]),
    "village_day": ("hut", [("morning", ["sun", "woman_pot", "tree"]), ("work", ["farmer", "animal", "man"]), ("home", ["hut", "bird"])]),
    "forest": ("peacock", [("hills", ["mountain", "tree"]), ("animals", ["peacock", "animal", "bird"]), ("river", ["fish", "tree", "sun"])]),
    # Mandana pack (data/lexicon_mandana.csv)
    "mandana": ("m_lotus8", [("the lotus", ["m_lotus8", "m_shahphulya", "m_lotus4"]), ("arrival", ["m_paglya", "m_surya", "m_chandra"]),
                             ("the household", ["m_bijni", "m_chaupad", "m_mor"])]),
    "diwali": ("m_lakshmi_chowk", [("Lakshmi's square", ["m_lakshmi_chowk", "m_lakshmi_rath"]), ("the lotus", ["m_lotus8", "m_shahphulya"]),
                                   ("welcome", ["m_paglya", "m_bijni"])]),
}
MANDANA_STORIES = {"mandana", "diwali"}
STORY_WORDS = {
    "harvest": ["harvest", "crop", "field", "farm", "sowing", "reaping", "grain", "kansari", "paddy", "rice"],
    "wedding": ["wedding", "marriage", "anniversary", "bride", "groom", "lagna", "married", "shaadi"],
    "tarpa": ["tarpa", "dance", "music", "festival", "celebrat", "dancers"],
    "village_day": ["village", "daily", "home", "everyday", "household", "life"],
    "forest": ["forest", "nature", "jungle", "peacock", "river", "animals", "wild", "fish"],
    "mandana": ["mandana", "mandna", "rajasthan", "meena", "floor art"],
    "diwali": ["diwali", "deepavali", "lakshmi", "lamps"],
}
PRODUCT_WORDS = [("frame_a3", ["a3"]), ("frame_a4", ["a4", "frame", "poster", "wall art", "print"]), ("saree", ["saree", "sari", "dupatta"]),
                 ("diary", ["diary", "notebook", "journal"]), ("wallpaper", ["wallpaper", "wall paper", "room"]),
                 ("phone", ["phone", "mobile", "lock screen", "lockscreen"]), ("tee", ["tee", "t-shirt", "tshirt", "shirt"])]
TEMPLATE_WORDS = [("tarpa_spiral", ["spiral", "ring", "circle", "round"]), ("registers", ["band", "rows", "register", "in order", "sequence"]),
                  ("medallion", ["medallion", "centre", "center", "chauk"]), ("all_over_buti", ["all over", "all-over", "buti", "scattered"])]
DENSE, SPARSE = ["busy", "dense", "rich", "full", "packed", "intricate", "detailed"], ["minimal", "sparse", "airy", "calm", "simple", "clean", "quiet"]
BORDER_WORDS = [("dancers", ["dancer", "chain"]), ("chevrons", ["chevron", "zigzag", "zig-zag"]), ("dots", ["dot"]),
                ("vine", ["vine", "leaf", "leaves", "floral"]), ("triangles", ["triangle", "mountain", "traditional border", "border"])]


def _first(text, table):
    hits = [(min(text.find(w) for w in ws if w in text), k) for k, ws in table if any(w in text for w in ws)]
    return min(hits)[1] if hits else None


def rules(brief, product=None):
    from .palette import PALETTES
    t = " " + brief.lower() + " "
    product = product or _first(t, PRODUCT_WORDS) or "frame_a4"
    stories = sorted((min(t.find(w) for w in ws if w in t), s) for s, ws in STORY_WORDS.items() if any(w in t for w in ws))
    stories = [s for _, s in stories] or ["harvest"]
    hero, beats = STORIES[stories[0]][0], []
    for s in stories:
        beats += [b for b in STORIES[s][1] if b not in beats]
    if len(stories) > 1:  # keep each story's central beat first so a mixed brief keeps both stories
        beats = [STORIES[s][1][1] for s in stories][:4] + [b for b in beats if b not in [STORIES[s][1][1] for s in stories]]
    beats = beats[:4]
    density = "dense" if any(w in t for w in DENSE) else "sparse" if any(w in t for w in SPARSE) else "balanced"
    words = [w for w in re.findall(r"[a-z]+", t)]
    tags = {p: set(PALETTES[p]["tags"]) for p in PALETTE_IDS}
    colours = [w for w in words if any(w in tg for tg in tags.values()) and w not in ("traditional", "contemporary")]
    if colours:
        score = {p: (sum(c in tags[p] for c in set(colours)), -min([colours.index(c) for c in colours if c in tags[p]] or [99])) for p in PALETTE_IDS}
        palette = max(PALETTE_IDS, key=lambda p: score[p])
    else:
        palette = "mustard_rust_cream" if any(w in t for w in ("modern", "contemporary", "bright")) else "white_on_geru"
    template = _first(t, TEMPLATE_WORDS)
    if product in ("wallpaper",):
        template = "all_over_buti"
    mandana = [s for s in stories if s in MANDANA_STORIES]
    fusion = bool(mandana) and len(mandana) < len(stories)
    if fusion:  # fusion: a Warli centre framed by a Mandana border, as the brief mixes the two
        warli = [s for s in stories if s not in MANDANA_STORIES]
        hero, beats = STORIES[warli[0]][0], [b for s in warli for b in STORIES[s][1]][:4]
    elif mandana and template is None and product != "wallpaper":
        template = "mandana_medallion"
    template = template or ("medallion" if hero in ("lagna_chauk", "chauk") else "tarpa_spiral" if hero == "tarpa_player"
                            else "all_over_buti" if product == "saree" else "registers")
    repeat = ("brick" if "brick" in t else "straight" if "straight" in t or "grid" in t else "half_drop") if template == "all_over_buti" else None
    border = None if "no border" in t or "borderless" in t else _first(t, BORDER_WORDS)
    if border is None and "no border" not in t and product in ("frame_a4", "frame_a3", "diary", "saree"):
        border = "dehri" if mandana else "triangles"
    if fusion and "no border" not in t:
        border = "dehri" if border in (None, "triangles") else border
    return Plan(product=product, template=template, density=density, repeat=repeat, palette_id=palette, border_style=border,
                story_beats=[Beat(beat=b, symbol_ids=ids) for b, ids in beats], hero_symbol_id=hero,
                notes=f"rules: stories {', '.join(stories)}" + ("; fusion: Mandana border around a Warli centre" if fusion else ""))


# ---------- LLM backends ----------
def _prompt(brief, product):
    syms = ", ".join(f"{i} ({r['name']})" for i, r in LEXICON.items())
    return (f"Turn this design brief into a JSON plan. Brief: {brief!r}. {'Product is fixed: ' + product + '. ' if product else ''}"
            f"Reply with JSON only, keys: product (one of {PRODUCT_IDS}), template (one of {TEMPLATES}), density (sparse|balanced|dense), "
            f"repeat (null, or straight|half_drop|brick; only for all_over_buti), palette_id (one of {PALETTE_IDS}), "
            f"border_style (null or one of {BORDERS}), story_beats (1-4 items of {{beat, symbol_ids}}), hero_symbol_id, notes. "
            f"symbol_ids and hero_symbol_id must come from this list: {syms}. Do not explain symbols.")


def _parse(text):
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else None


def ollama(brief, product=None):
    import urllib.request
    body = json.dumps({"model": OLLAMA_MODEL, "prompt": _prompt(brief, product), "format": "json", "stream": False,
                       "options": {"num_predict": 400, "temperature": 0}}).encode()
    r = json.loads(urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/generate", body), timeout=120).read())
    return _parse(r["response"]), {"tokens_in": r.get("prompt_eval_count"), "tokens_out": r.get("eval_count")}


def claude(brief, product=None):
    out = subprocess.run(["claude", "-p", _prompt(brief, product), "--model", "haiku", "--output-format", "json"],
                         capture_output=True, text=True, timeout=180, env={**os.environ, "CLAUDE_CODE_MAX_OUTPUT_TOKENS": "400"})
    r = json.loads(out.stdout)
    u = r.get("usage", {})
    return _parse(r.get("result", "")), {"tokens_in": u.get("input_tokens"), "tokens_out": u.get("output_tokens"), "cost_usd": r.get("total_cost_usd")}


def available():
    b = ["rules"]
    if shutil.which("ollama"):
        b.append("ollama")
    if os.environ.get("CHHAAP_PLANNER") == "claude" and shutil.which("claude"):
        b.append("claude")
    return b


def plan(brief, product=None, backend=None):
    """Returns {plan, backend, seconds, attempts, usage, fallback}. backend None: the most capable available."""
    backend = backend or available()[-1]
    t0, usage, attempts = time.perf_counter(), {}, 0
    if backend != "rules":
        for attempts in (1, 2):
            try:
                raw, usage = {"ollama": ollama, "claude": claude}[backend](brief, product)
                p = Plan(**{**raw, **({"product": product} if product else {})})
                return {"plan": p.model_dump(), "backend": backend, "seconds": time.perf_counter() - t0, "attempts": attempts, "usage": usage, "fallback": False}
            except Exception as e:  # invalid JSON, unknown symbol, backend down: retry once, then rules
                usage = {**usage, "error": str(e)[:200]}
    p = rules(brief, product)
    return {"plan": p.model_dump(), "backend": "rules", "requested": backend, "seconds": time.perf_counter() - t0,
            "attempts": attempts, "usage": usage, "fallback": backend != "rules"}


if __name__ == "__main__":
    r = plan("A3 frame for my parents' anniversary. Wedding and harvest, maroon and mustard, busy, traditional border.", backend="rules")
    p = r["plan"]
    assert p["product"] == "frame_a3" and p["density"] == "dense" and p["border_style"] == "triangles", p
    assert p["hero_symbol_id"] == "lagna_chauk" and any("kansari" in b["symbol_ids"] for b in p["story_beats"]), p
    assert p["palette_id"] in ("white_on_maroon", "mustard_rust_cream"), p
    try:
        Plan(**{**p, "hero_symbol_id": "dragon"})
        raise AssertionError("unknown symbol accepted")
    except ValueError:
        pass
    assert rules("Saree with peacocks, teal and ochre, minimal").model_dump()["palette_id"] == "teal_ochre_white"
    assert rules("phone wallpaper, tarpa dance spiral").template == "tarpa_spiral"
    m = rules("Diwali floor design, mandana lotus, white on maroon").model_dump()
    assert m["template"] == "mandana_medallion" and m["hero_symbol_id"].startswith("m_") and m["border_style"] == "dehri", m
    f = rules("A4 frame, Warli harvest with a Mandana border").model_dump()
    assert f["hero_symbol_id"] == "kansari" and f["border_style"] == "dehri" and "fusion" in f["notes"], f
    print("planner ok", p["template"], p["palette_id"], [b["beat"] for b in p["story_beats"]])
