"""v2 experiments. E7 symbol survival, E9 vector vs stylized vs repaired (same runs as E7), E8 layout vs scatter, E10 planner.
Writes eval/results/e7.json, e8.json, e9.json, e10.json and figures. Usage: python scripts/run_eval_v2.py [e7] [e8] [e10]"""
import json
import statistics as st
import sys
import time
from functools import lru_cache
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent.parent))
from chhaap.compose import LEXICON, draw_symbol  # noqa: E402
from chhaap.layout import TEMPLATES, layout, overlaps, render_labels  # noqa: E402
TEMPLATES = TEMPLATES[:4]  # the Warli templates; Mandana rings take Mandana symbols, not these stories
from chhaap.planner import STORIES, available, plan  # noqa: E402

ROOT = Path(__file__).parent.parent
RES, FIG, RUNS = ROOT / "eval/results", ROOT / "eval/figures", ROOT / "runs"
N = 16  # CPU rule from TASK.md
STORY = lambda i: list(STORIES)[i % 5]
A4 = (2480, 3508)


def stats(xs):
    xs = [float(x) for x in xs]
    return {"mean": st.mean(xs), "std": st.stdev(xs) if len(xs) > 1 else 0.0, "n": len(xs)}


def spec(template, i, density="balanced"):
    story = STORY(i)
    hero, beats = STORIES[story]
    beats = [{"beat": b, "symbol_ids": ids} for b, ids in beats]
    if template == "all_over_buti":
        return dict(template=template, W=1024, H=1024, hero=hero, beats=beats, density=density, repeat="half_drop", border=None, story=story)
    return dict(template=template, W=A4[0], H=A4[1], hero=hero, beats=beats, density=density, repeat=None, border="triangles", story=story)


def make_layout(s, seed):
    return layout(s["template"], s["W"], s["H"], s["hero"], s["beats"], s["density"], s["repeat"], s["border"], seed=seed)


@lru_cache(None)
def complexity(sid):
    """Drawing primitives in a symbol's recipe, composites expanded; and its ink share when drawn at 200 px."""
    n = 0
    for cmd in LEXICON[sid]["visual_rule"].split(";"):
        op, *a = cmd.split()
        n += complexity(a[0])[0] if op == "use" else int(float(a[1])) * complexity(a[0])[0] if op == "circle_of" else int(float(a[-1])) if op == "rays" else 1
    im = Image.new("L", (240, 240))
    draw_symbol(ImageDraw.Draw(im), sid, 120, 120, 200)
    return n, float((np.asarray(im) > 0).mean())


# ---------- E7 + E9 ----------
def e7_e9():
    from scipy.stats import spearmanr
    from chhaap.palette import colourize
    from chhaap.studio import canvas, curves_to_labels, layered_curves, stylize
    runs = []
    for i in range(N):
        t = TEMPLATES[i % 4]
        s = spec(t, i)
        L = make_layout(s, seed=i)
        t0 = time.perf_counter()  # vector only: the layout at print size, recoloured
        colourize(render_labels(L, 1.0, canvas(L)), "white_on_geru")
        t_vec = time.perf_counter() - t0
        done = RUNS / f"e7_{i:02d}" / "survival.json"  # resume: a finished page keeps its stored passes and timings
        rep = json.loads(done.read_text()) if done.exists() else stylize(L, 1000 + i, RUNS / f"e7_{i:02d}", preview=i < 4)
        t0 = time.perf_counter()
        ink = np.asarray(Image.open(RUNS / f"e7_{i:02d}" / "ink.png")) > 0
        curves_to_labels(layered_curves(L, ink, rep["k"]), rep["k"], 1.0, canvas(L))
        t_trace = time.perf_counter() - t0
        runs.append({"i": i, "template": t, "story": s["story"], "seed": 1000 + i, "elements": rep["elements"], "attempts": rep["attempts"],
                     "seconds_vector": t_vec, "seconds_first_pass": rep["attempts"][0]["seconds"] + t_trace,
                     "seconds_repaired": sum(a["seconds"] for a in rep["attempts"]) + t_trace, "trace_render_seconds": t_trace})
        print("e7", i, t, s["story"], Counter(e["path"] for e in rep["elements"]), flush=True)
    els = [e for r in runs for e in r["elements"]]
    by_sid = defaultdict(list)
    for e in els:
        by_sid[e["sid"]].append(e)
    per = {sid: {"n": len(v), "survival_first_pass": sum(e["survived0"] for e in v) / len(v),
                 "survival_final": sum(e["survived"] or e["path"] == "vector" for e in v) / len(v),
                 "mean_iou_first_pass": st.mean(e["iou0"] for e in v), "primitives": complexity(sid)[0], "ink_share": complexity(sid)[1],
                 "roles": dict(Counter(e["role"] for e in v))} for sid, v in sorted(by_sid.items())}
    sids = [k for k, v in per.items() if v["n"] >= 3]
    rho_p = spearmanr([per[k]["primitives"] for k in sids], [per[k]["survival_first_pass"] for k in sids])
    rho_a = spearmanr([per[k]["ink_share"] for k in sids], [per[k]["survival_first_pass"] for k in sids])
    roles = {r: {"n": len(v), "survival_first_pass": sum(e["survived0"] for e in v) / len(v)} for r in ("hero", "support", "filler")
             for v in [[e for e in els if e["role"] == r]] if v}
    per_t = {t: {"survival_first_pass": sum(e["survived0"] for r in runs if r["template"] == t for e in r["elements"]) /
                 max(1, sum(len(r["elements"]) for r in runs if r["template"] == t))} for t in TEMPLATES}
    reruns = Counter(len(r["attempts"]) - 1 for r in runs)
    e7 = {"n_runs": len(runs), "n_elements": len(els), "page": "A4 2480x3508 (all_over_buti: 1024 half-drop tile)", "density": "balanced",
          "keep_rule": "IoU >= 0.5 after 1 px dilation, inside the element box, at stylize scale", "per_symbol": per, "per_role": roles,
          "per_template": per_t, "spearman_primitives_vs_survival": {"rho": float(rho_p[0]), "p_value": float(rho_p[1]), "n_symbols": len(sids)},
          "spearman_ink_share_vs_survival": {"rho": float(rho_a[0]), "p_value": float(rho_a[1]), "n_symbols": len(sids)},
          "runs_by_reruns": {str(k): v for k, v in sorted(reruns.items())},
          "paths": dict(Counter(e["path"] for e in els)), "runs": runs}
    (RES / "e7.json").write_text(json.dumps(e7, indent=1))
    main = [e for e in els if e["role"] in ("hero", "support")]
    e9 = {"note": "same 16 runs as E7; vector-only survival is 1 by construction (the layout is the output)",
          "survival_main": {"vector_only": 1.0, "stylized": sum(e["survived0"] for e in main) / len(main),
                            "stylized_repaired": sum(e["survived"] or e["path"] == "vector" for e in main) / len(main), "n": len(main)},
          "survival_all": {"vector_only": 1.0, "stylized": sum(e["survived0"] for e in els) / len(els),
                           "stylized_repaired": sum(e["survived"] or e["path"] == "vector" for e in els) / len(els), "n": len(els)},
          "seconds": {"vector_only": stats(r["seconds_vector"] for r in runs), "stylized": stats(r["seconds_first_pass"] for r in runs),
                      "stylized_repaired": stats(r["seconds_repaired"] for r in runs)},
          "repair_paths_main": dict(Counter(e["path"] for e in main)), "preference": "see e9_preference in summarize (study pages)"}
    (RES / "e9.json").write_text(json.dumps(e9, indent=1))
    figures_e7(per, runs)


def figures_e7(per, runs):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ink, muted, rule = "#231e1a", "#594a3d", "#d9c9aa"
    items = sorted(((v["survival_first_pass"], k) for k, v in per.items() if v["n"] >= 3))
    fig, ax = plt.subplots(figsize=(6.4, 0.24 * len(items) + 0.9), dpi=200)
    ax.barh([LEXICON[k]["name"] for _, k in items], [v for v, _ in items], color=ink, height=0.62)
    for y, (v, k) in enumerate(items):
        ax.text(v + 0.01, y, f"{v:.2f}  (n={per[k]['n']})", va="center", fontsize=7, color=muted)
    ax.set_xlim(0, 1.18)
    ax.set_xlabel("Share surviving the first diffusion pass", fontsize=8, color=muted)
    ax.tick_params(labelsize=7, colors=muted, length=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(rule)
    ax.xaxis.grid(True, color=rule, linewidth=0.5)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(FIG / "e7_survival.png")
    from scripts.contact_sheet import contact_sheet
    paths = [RUNS / f"e7_{i:02d}" / f for i in range(4) for f in ("control.png", "stylized.png", "ink.png")]
    contact_sheet(paths, FIG / "e7_examples.png", cols=6, width=2400)


def e7_posthoc():
    """Defined after reading E7 (complexity did not predict survival): is drawn size the factor?
    Size = composition ink pixels inside the element box at stylize scale. Hero and support symbols only."""
    from scipy.stats import mannwhitneyu, spearmanr
    e7 = json.loads((RES / "e7.json").read_text())
    els = [e for r in e7["runs"] for e in r["elements"] if e["role"] in ("hero", "support")]
    px = np.array([e["ink_px"] for e in els], float)
    ok = np.array([e["survived0"] for e in els], bool)
    q = np.quantile(px, [0.25, 0.5, 0.75])
    bins = np.digitize(px, q)
    rho = spearmanr(px, ok)
    mw = mannwhitneyu(px[ok], px[~ok])
    out = {"note": "post hoc, defined after inspecting E7", "n": len(els),
           "quartile_edges_ink_px": q.tolist(),
           "survival_by_size_quartile": [{"quartile": i + 1, "n": int((bins == i).sum()), "survival_first_pass": float(ok[bins == i].mean())} for i in range(4)],
           "spearman_ink_px_vs_survival": {"rho": float(rho[0]), "p_value": float(rho[1])},
           "median_ink_px": {"survived": float(np.median(px[ok])), "lost": float(np.median(px[~ok]))},
           "mann_whitney": {"U": float(mw[0]), "p_value": float(mw[1])}}
    rot = {}  # layouts are deterministic: rebuild them to recover each element's rotation
    for r in e7["runs"]:
        L = make_layout(spec(r["template"], r["i"]), seed=r["i"])
        rot.update({(r["i"], e["id"]): abs(((e["rot"] + 180) % 360) - 180) > 1 for e in L["elements"]})
    tilt = np.array([rot[(r["i"], e["id"])] for r in e7["runs"] for e in r["elements"] if e["role"] in ("hero", "support")])
    from scipy.stats import fisher_exact
    tab = [[int((ok & tilt).sum()), int((~ok & tilt).sum())], [int((ok & ~tilt).sum()), int((~ok & ~tilt).sum())]]
    out["rotated"] = {"n": int(tilt.sum()), "survival_first_pass": float(ok[tilt].mean())}
    out["upright"] = {"n": int((~tilt).sum()), "survival_first_pass": float(ok[~tilt].mean())}
    out["fisher_rotated_vs_upright"] = {"odds_ratio": float(fisher_exact(tab)[0]), "p_value": float(fisher_exact(tab)[1])}
    (RES / "e7_posthoc.json").write_text(json.dumps(out, indent=1))
    print("rotation", out["rotated"], out["upright"], out["fisher_rotated_vs_upright"])
    print("e7 posthoc", out["survival_by_size_quartile"], out["spearman_ink_px_vs_survival"], out["median_ink_px"])


# ---------- E8 ----------
def cv_grid(L, k=4):
    """Coefficient of variation of ink coverage over a k x k grid of the content box."""
    sc = 384 / max(L["W"], L["H"])
    a = np.asarray(render_labels(L, sc)) > 0
    x0, y0, x1, y1 = (int(v * sc) for v in L["content"])
    a = a[y0:y1, x0:x1]
    cells = [c.mean() for row in np.array_split(a, k, 0) for c in np.array_split(row, k, 1)]
    return float(np.std(cells) / max(1e-9, np.mean(cells)))


def e8():
    from scipy.stats import wilcoxon
    out = {"n_seeds": N, "grid": "4x4 over the content box", "conditions": {}}
    vals = {}
    for t in ["scatter"] + TEMPLATES:
        cv, ov, cov, cvn = [], [], [], []
        for sd in range(N):
            s = spec(t, sd)
            if t == "scatter":
                s.update(W=A4[0], H=A4[1], repeat=None, border="triangles")
            L = make_layout(s, seed=sd)
            cv.append(cv_grid(L)), ov.append(overlaps(L)), cov.append(L["coverage"])
            cvn.append(cv_grid({**L, "elements": [e for e in L["elements"] if e["role"] != "filler"]}))  # structure alone
        vals[t] = cv
        out["conditions"][t] = {"cv": stats(cv), "cv_no_fillers": stats(cvn), "overlaps": stats(ov), "coverage": stats(cov),
                                "cv_values": cv, "cv_no_fillers_values": cvn, "overlap_values": ov}
    for t in TEMPLATES:
        w = wilcoxon(vals[t], vals["scatter"])
        out["conditions"][t]["wilcoxon_cv_vs_scatter"] = {"statistic": float(w[0]), "p_value": float(w[1])}
        w = wilcoxon(out["conditions"][t]["cv_no_fillers_values"], vals["scatter"])
        out["conditions"][t]["wilcoxon_cv_no_fillers_vs_scatter"] = {"statistic": float(w[0]), "p_value": float(w[1])}
    (RES / "e8.json").write_text(json.dumps(out, indent=1))
    print("e8", {t: round(v["cv"]["mean"], 3) for t, v in out["conditions"].items()})


# ---------- E10 ----------
def satisfied(p, b):
    from chhaap.palette import PALETTES
    tags = set(PALETTES[p["palette_id"]]["tags"])
    ids = {p["hero_symbol_id"]} | {i for x in p["story_beats"] for i in x["symbol_ids"]}
    checks = {"product": p["product"] == b["product"], "palette": all(c in tags for c in b["colours"])}
    if b["density"]:
        checks["density"] = p["density"] == b["density"]
    for s in b["stories"]:
        checks[f"story_{s}"] = STORIES[s][0] in ids
    return checks


def e10():
    briefs = json.loads((ROOT / "eval/briefs.json").read_text())
    out = {"n_briefs": len(briefs), "backends": {}, "note": "briefs and the rules backend were written by the same author; briefs fixed before any planner ran on them"}
    for be in ("rules", "ollama", "claude"):
        if be not in available():
            out["backends"][be] = {"status": "not run: " + ("ollama not installed" if be == "ollama" else "CHHAAP_PLANNER=claude not set (uses the user's paid quota)")}
            continue
        rows = []
        for b in briefs:
            r = plan(b["brief"], None, be)
            c = satisfied(r["plan"], b)
            rows.append({"brief": b["brief"], "checks": c, "seconds": r["seconds"], "fallback": r["fallback"], "usage": r["usage"]})
        allc = [v for r in rows for v in r["checks"].values()]
        by = defaultdict(list)
        for r in rows:
            for k, v in r["checks"].items():
                by[k.split("_")[0]].append(v)
        out["backends"][be] = {"schema_valid": sum(not r["fallback"] for r in rows) / len(rows), "constraints": len(allc),
                               "satisfied": sum(allc) / len(allc), "by_type": {k: {"n": len(v), "satisfied": sum(v) / len(v)} for k, v in by.items()},
                               "seconds": stats(r["seconds"] for r in rows), "rows": rows}
        print("e10", be, round(out["backends"][be]["satisfied"], 3), {k: round(v["satisfied"], 2) for k, v in out["backends"][be]["by_type"].items()})
    (RES / "e10.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    todo = sys.argv[1:] or ["e8", "e10", "e7"]
    for k in todo:
        {"e7": e7_e9, "e8": e8, "e10": e10, "e7post": e7_posthoc}[k]()
