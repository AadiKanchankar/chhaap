"""Chhaap local app. Run: python -m app  ->  http://localhost:7860  (hidden study pages at /study)"""
import io
import json
import random
import sqlite3
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from chhaap.compose import LEXICON
from chhaap.meaning import card
from chhaap.metrics import sdr, wrap_error

ROOT = Path(__file__).parent
RUNS = ROOT / "runs"
RUNS.mkdir(exist_ok=True)
DB = sqlite3.connect(ROOT / "app.db", check_same_thread=False)
DB.executescript("""
CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, params TEXT, sdr REAL, wrap REAL, created REAL);
CREATE TABLE IF NOT EXISTS votes(id INTEGER PRIMARY KEY, seed INTEGER, a_run TEXT, e_run TEXT, left_cond TEXT,
  choice TEXT, choice_after_card TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS annotations(run_id TEXT, cond TEXT, symbol TEXT, present INTEGER, ts REAL);
CREATE TABLE IF NOT EXISTS prefs2(id INTEGER PRIMARY KEY, kind TEXT, item TEXT, left_cond TEXT, choice TEXT, treat TEXT, ts REAL);
""")
LOCK, JOBS = threading.Lock(), {}  # one generation at a time: CPU-bound
app = FastAPI(title="Chhaap")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
app.mount("/runs", StaticFiles(directory=RUNS), name="runs")


@app.get("/")
@app.get("/study")
def index():
    return FileResponse(ROOT / "static/index.html")


@app.get("/api/machine")
def machine():
    from chhaap.generate import DEFAULTS, DEVICE, FAST, WARLI_LORA
    return {"device": DEVICE, "fast": FAST, "steps": DEFAULTS["steps"], "cfg": DEFAULTS["cfg"], "cn": DEFAULTS["cn_scale"], "lora": WARLI_LORA.exists()}


@app.get("/api/lexicon")
def lexicon():
    return list(LEXICON.values())


@app.get("/api/symbol/{sid}.png")
def symbol_png(sid: str):
    """White-on-transparent glyph; the UI uses it as a CSS mask so the palette colours it."""
    from PIL import Image, ImageDraw
    from chhaap.compose import draw_symbol
    m = Image.new("L", (96, 96))
    draw_symbol(ImageDraw.Draw(m), sid, 48, 48, 88)
    buf = io.BytesIO()
    Image.merge("LA", (m, m)).save(buf, "PNG")
    return Response(buf.getvalue(), media_type="image/png", headers={"Cache-Control": "max-age=86400"})


def run_info(rid):
    run = RUNS / rid
    if rid in JOBS and JOBS[rid] != "done":
        previews = sorted(p.name for p in (run / "steps").glob("*.png")) if (run / "steps").exists() else []
        return {"id": rid, "status": JOBS[rid], "previews": previews}
    if not (run / "params.json").exists():
        raise HTTPException(404, "No such run")
    p = json.loads((run / "params.json").read_text())
    row = DB.execute("SELECT sdr, wrap FROM runs WHERE id=?", (rid,)).fetchone()
    if not row:  # runs made by the eval scripts
        row = (sdr(run / "tile.png"), wrap_error(run / "tile.png"))
        DB.execute("INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?)", (rid, json.dumps(p), *row, time.time()))
        DB.commit()
    previews = sorted(x.name for x in (run / "steps").glob("*.png")) if (run / "steps").exists() else []
    return {**p, "status": "done", "sdr": row[0], "wrap_error": row[1], "previews": previews,
            "has_svg": (run / "tile.svg").exists()}


@app.get("/api/runs/{rid}")
def get_run(rid: str):
    return run_info(rid)


@app.get("/api/runs/{rid}/meaning")
def meaning(rid: str):
    return card([q["id"] for q in run_info(rid)["placed"]])


# ---- study (E3 annotation, E4 preference). Pairs come from E1 runs: e1_a_<seed> (text only) vs e1_e_<seed> (full).
def eval_pairs():
    return sorted(int(p.name.split("_")[-1]) for p in RUNS.glob("e1_e_*")
                  if (p / "tile.png").exists() and (RUNS / f"e1_a_{p.name.split('_')[-1]}" / "tile.png").exists())


def made(run):  # answers older than the image they describe are stale (E1 was rerun once the LoRA arrived)
    return (RUNS / run / "tile.png").stat().st_mtime


@app.get("/api/study/pair")
def study_pair():
    seeds = eval_pairs()
    if not seeds:
        raise HTTPException(404, "No evaluation runs yet")
    voted = {r[0] for r in DB.execute("SELECT seed, ts FROM votes") if r[1] > made(f"e1_e_{r[0]:03d}")}
    seed = random.choice([s for s in seeds if s not in voted] or seeds)
    a, e = f"e1_a_{seed:03d}", f"e1_e_{seed:03d}"
    left = random.choice(["a", "e"])
    return {"seed": seed, "a_run": a, "e_run": e, "left": left, "meaning": meaning(e)}


@app.post("/api/study/vote")
def study_vote(body: dict):
    DB.execute("INSERT INTO votes(seed,a_run,e_run,left_cond,choice,choice_after_card,ts) VALUES (?,?,?,?,?,?,?)",
               (body["seed"], body["a_run"], body["e_run"], body["left"], body["choice"], body.get("choice_after_card"), time.time()))
    DB.commit()
    return {"ok": True, "n": DB.execute("SELECT COUNT(*) FROM votes").fetchone()[0]}


@app.get("/api/study/annotate")
def study_annotate():
    done = {r[0] for r in DB.execute("SELECT run_id, MAX(ts) FROM annotations GROUP BY run_id") if r[1] > made(r[0])}
    todo = [f"e1_{c}_{s:03d}" for s in eval_pairs() for c in "ae" if f"e1_{c}_{s:03d}" not in done]
    if not todo:
        return {"done": True, "n": len(done)}
    rid = random.choice(todo)
    ids = list(dict.fromkeys(q["id"] for q in run_info(rid)["placed"]))
    return {"run": rid, "symbols": [{"id": i, "name": LEXICON[i]["name"]} for i in ids], "remaining": len(todo)}


@app.post("/api/study/annotate")
def study_annotation(body: dict):
    cond = body["run"].split("_")[1]
    DB.execute("DELETE FROM annotations WHERE run_id=?", (body["run"],))  # last answer wins on resubmit
    DB.executemany("INSERT INTO annotations VALUES (?,?,?,?,?)",
                   [(body["run"], cond, s, int(v), time.time()) for s, v in body["present"].items()])
    DB.commit()
    return {"ok": True}


# ---- v2 study: blind pairs for E8 (scatter vs structured layout) and E9 (vector only vs diffusion + repair)
def study_image(kind, item, cond):
    """Render (and cache) one side of a pair: white on geru, textured, 640 px long side."""
    out = RUNS / "study_v2" / f"{kind}_{item}_{cond}.png"
    if not out.exists():
        import numpy as np
        from PIL import Image
        from chhaap.palette import colourize, texture
        from chhaap.studio import canvas, curves_to_labels, layered_curves
        from scripts.run_eval_v2 import make_layout, spec
        out.parent.mkdir(exist_ok=True)
        t, i = item.rsplit("_", 1)
        s = spec(t if kind == "e9" or cond != "scatter" else "scatter", int(i))
        if kind == "e8" and cond == "scatter":
            s.update(W=2480, H=3508, repeat=None, border="triangles")
        L = make_layout(s, seed=int(i))
        sc = 640 / max(canvas(L))
        if kind == "e9" and cond == "stylized":
            rep = json.loads((RUNS / f"e7_{int(i):02d}" / "survival.json").read_text())
            ink = np.asarray(Image.open(RUNS / f"e7_{int(i):02d}" / "ink.png")) > 0
            lab = curves_to_labels(layered_curves(L, ink, rep["k"]), rep["k"], sc, canvas(L))
        else:
            from chhaap.layout import render_labels
            lab = render_labels(L, sc, canvas(L))
        texture(colourize(lab, "white_on_geru"), lab, 0).save(out)
    return f"/runs/study_v2/{out.name}"


@app.get("/api/study/pair2")
def study_pair2():
    from chhaap.layout import TEMPLATES
    kinds = ["e8"] + (["e9"] if (RUNS / "e7_15" / "ink.png").exists() else [])
    kind = random.choice(kinds)
    if kind == "e8":
        item, a, b = f"{random.choice(TEMPLATES[:4])}_{random.randrange(16)}", "scatter", "structured"
    else:
        i = random.randrange(16)
        item, a, b = f"{TEMPLATES[i % 4]}_{i}", "vector", "stylized"
    left = random.choice([a, b])
    right = b if left == a else a
    return {"kind": kind, "item": item, "left": left, "right": right, "treat": b,
            "left_src": study_image(kind, item, left), "right_src": study_image(kind, item, right)}


@app.post("/api/study/pref2")
def study_pref2(body: dict):
    DB.execute("INSERT INTO prefs2(kind,item,left_cond,choice,treat,ts) VALUES (?,?,?,?,?,?)",
               (body["kind"], body["item"], body["left"], body["choice"], body["treat"], time.time()))
    DB.commit()
    return {"ok": True, "n": DB.execute("SELECT COUNT(*) FROM prefs2").fetchone()[0]}


# ---- v2 studio: brief -> plan -> product design
@app.get("/api/v2/options")
def v2_options():
    from chhaap.layout import BORDERS, TEMPLATES
    from chhaap.palette import PALETTES
    from chhaap.planner import available
    from chhaap.products import PRODUCTS
    return {"products": [{"id": k, **v} for k, v in PRODUCTS.items()], "palettes": list(PALETTES.values()),
            "templates": TEMPLATES, "borders": BORDERS, "densities": ["sparse", "balanced", "dense"],
            "backends": available(), "symbols": [{"id": i, "name": r["name"], "pack": r["pack"]} for i, r in LEXICON.items()]}


@app.post("/api/v2/plan")
def v2_plan(body: dict):
    from chhaap.planner import plan
    return {"brief": body.get("brief", ""), **plan(body.get("brief", ""), body.get("product"), body.get("backend"))}


@app.post("/api/v2/design")
def v2_design(body: dict):
    """body: {plan, brief, planner (the /plan response), mode: stylized|vector, seed}. Runs in a thread; poll /api/v2/designs/<id>."""
    from chhaap.planner import Plan
    from chhaap.products import make
    try:
        plan = Plan(**body["plan"]).model_dump()
    except Exception as e:
        raise HTTPException(422, f"Invalid plan: {e}")
    rid = f"d_{int(time.time() * 1000):x}"
    run = RUNS / rid
    run.mkdir()
    (run / "brief.json").write_text(json.dumps({"brief": body.get("brief", ""), "planner": body.get("planner")}, indent=1))
    JOBS[rid] = "queued"

    def work():
        with LOCK:
            try:
                st = {k: body[k] for k in ("steps", "cfg", "lora_scale", "cn_scale") if body.get(k) is not None}
                make(plan, run, body.get("mode", "stylized"), int(body.get("seed", 0)), textured=body.get("texture", True),
                     log=lambda m: JOBS.__setitem__(rid, m), settings=st)
                JOBS[rid] = "done"
            except Exception as e:  # surfaced through /api/v2/designs/<id>
                JOBS[rid] = f"error: {e}"

    threading.Thread(target=work, daemon=True).start()
    return {"id": rid}


def design_info(rid):
    from chhaap.meaning import caption, caption_ok, card
    run = RUNS / rid
    if not run.exists():
        raise HTTPException(404, "No such design")
    steps = sorted(str(x.relative_to(RUNS)) for x in run.glob("*/steps/*.png"))
    brief = json.loads((run / "brief.json").read_text()) if (run / "brief.json").exists() else {}
    if not (run / "meta.json").exists():
        return {"id": rid, "status": JOBS.get(rid, "error: interrupted"), "steps": steps, **brief}
    meta = json.loads((run / "meta.json").read_text())
    els = meta["elements"]
    present = [e["sid"] for e in els if e["survived"] or e["path"] == "vector"]
    cap = caption(meta["plan"], present)
    surv = [e for e in els if "iou" in e and e["role"] != "filler"]  # fillers are checked but never repaired
    plan = meta["plan"]
    planned = [plan["hero_symbol_id"]] + [i for b in plan["story_beats"] for i in b["symbol_ids"]]
    placed = [e["sid"] for e in els]
    placed += [i for i in dict.fromkeys(planned) if i not in placed]  # planned but never placed: the card lists it as lost
    return {**meta, **brief, "status": "done", "steps": steps, "card": card(placed, present),
            "caption": cap if caption_ok(cap, present) else "", "export": (run / "export").exists(),
            "survival": {"checked": len(surv), "survived_first": sum(e["survived0"] for e in surv),
                         "repaired_rerun": sum(e["path"] == "rerun" for e in surv), "repaired_vector": sum(e["path"] == "vector" for e in surv),
                         "lost": sum(e["path"] == "lost" for e in surv)},
            "attempts": {p.parent.name: json.loads(p.read_text())["attempts"] for p in run.glob("*/survival.json")}}


@app.get("/api/v2/designs/{rid}")
def v2_get(rid: str):
    return design_info(rid)


@app.post("/api/v2/designs/{rid}/export")
def v2_export(rid: str):
    from chhaap.products import export
    with LOCK:
        files = export(RUNS / rid)
    return {k: "/runs/" + str(Path(v).relative_to(RUNS)) for k, v in files.items()}


@app.get("/api/v2/gallery")
def v2_gallery():
    out = []
    for run in sorted(RUNS.glob("d_*"), reverse=True):
        if (run / "meta.json").exists():
            m = json.loads((run / "meta.json").read_text())
            b = json.loads((run / "brief.json").read_text()) if (run / "brief.json").exists() else {}
            out.append({"id": run.name, "brief": b.get("brief", ""), "product": m["plan"]["product"], "mode": m["mode"],
                        "palette": m["plan"]["palette_id"], "mockup": f"/runs/{run.name}/mockup.png"})
    return out


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=7860)
