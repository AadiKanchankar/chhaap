"""v2 pipeline for one layout ("part"): stylize (optional) -> survival check + repair -> traced, layered label raster.

Stylize runs diffusion on the monochrome ink layer at <= 768 px; a page is cropped to its drawn area first, because a blank
margin comes back as paper and would trace as ink. Survival compares composition ink with output ink inside each element's
box (IoU after a 1 px dilation at stylize scale; IoU >= 0.5 survives). It cannot see a swap inside a composite symbol. A lost hero or support element
triggers a re-run with ControlNet strength + 0.15 (at most twice), then the clean vector symbol is composited in its box.
The repaired ink is traced and each path takes the layer of the element box it overlaps most, so recolouring is exact.
"""
import json
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .compose import LEXICON
from .layout import ACCENT, BORDER, FILLER, INK, bbox, copies, period, render_labels
from .vectorize import trace, two_tone

STYLIZE_MAX, KEEP, DILATE, CN_STEP, RERUNS = 768, 0.5, 1, 0.15, 2


def canvas(L):
    """Layout pixels the part covers: the straight period for repeats, else the page."""
    return period(L) if L["repeat"] else (L["W"], L["H"])


def stylize_geometry(L):
    """(k, (w, h), (sw, sh)): layout->stylize scale, the unstretched size, and the diffusion size (multiples of 64)."""
    P = canvas(L)
    k = STYLIZE_MAX / max(P)
    w, h = round(P[0] * k), round(P[1] * k)
    return k, (w, h), (max(256, round(w / 64) * 64), max(256, round(h / 64) * 64))


def _iou(a, b):
    return (a & b).sum() / max(1, (a | b).sum())


def _dil(m, r=DILATE):
    return np.asarray(Image.fromarray(m.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(2 * r + 1))) > 0


def regions(L, k, size):
    """Element id -> bool mask of its boxes (all lattice copies) at scale k on a size canvas."""
    w, h = round(size[0] * k), round(size[1] * k)
    out = {}
    for e in L["elements"]:
        if e["sid"] not in LEXICON:
            continue
        m = np.zeros((h, w), bool)
        for c in copies(L, e, size):
            x0, y0, x1, y1 = (int(round(v * k)) for v in bbox(c))
            m[max(0, y0):max(0, y1), max(0, x0):max(0, x1)] = True
        if m.any():
            out[e["id"]] = m
    return out


def survival(L, comp, ink, R):
    """Per lexicon element: IoU of composition ink and output ink inside its box (both dilated)."""
    dc, do = _dil(comp), _dil(ink)
    by_id = {e["id"]: e for e in L["elements"]}
    res = []
    for i, m in R.items():
        v = float(_iou(dc[m], do[m]))
        res.append({"id": i, "sid": by_id[i]["sid"], "role": by_id[i]["role"], "iou": v, "survived": v >= KEEP,
                    "ink_px": int(comp[m].sum())})
    return res


def stylize(L, seed, out_dir, cn_scale=0.7, preview=True, **kw):
    """Diffusion + survival + repair for one layout. Writes control.png, stylized.png, ink.png, survival.json in out_dir."""
    from .generate import paint
    out_dir = Path(out_dir)
    (out_dir / "steps").mkdir(parents=True, exist_ok=True)
    size = canvas(L)
    k, (w, h), (sw, sh) = stylize_geometry(L)
    comp = np.asarray(render_labels(L, k, size)) > 0
    x0, y0, x1, y1 = 0, 0, w, h
    if not L["repeat"]:  # crop to the drawn area
        ys, xs = np.nonzero(comp)
        x0, y0, x1, y1 = int(max(0, xs.min() - 2)), int(max(0, ys.min() - 2)), int(min(w, xs.max() + 3)), int(min(h, ys.max() + 3))
        sw, sh = max(256, round((x1 - x0) / 64) * 64), max(256, round((y1 - y0) / 64) * 64)
    crop = (slice(y0, y1), slice(x0, x1))
    control = Image.fromarray(comp[crop].astype(np.uint8) * 255).resize((sw, sh), Image.NEAREST)
    control.save(out_dir / "control.png")
    ids = list(dict.fromkeys(e["sid"] for e in L["elements"] if e["sid"] in LEXICON and e["role"] in ("hero", "support")))
    R = regions(L, k, size)
    attempts, first, best, cn = [], None, None, cn_scale
    for a in range(RERUNS + 1):
        t0 = time.perf_counter()
        img, info = paint(control, ids, seed, out_dir / "steps" if preview and a == 0 else None, cn_scale=cn, circular=bool(L["repeat"]), **kw)
        out = img.resize((x1 - x0, y1 - y0), Image.LANCZOS)
        part, *_ = two_tone(out)
        if _iou(part, comp[crop]) < _iou(~part, comp[crop]):  # polarity: ink is whichever tone matches the composition
            part = ~part
        ink = np.zeros_like(comp)
        ink[crop] = part
        surv = survival(L, comp, ink, R)
        lost = [s for s in surv if not s["survived"] and s["role"] in ("hero", "support")]
        attempts.append({"cn_scale": round(cn, 3), "seconds": time.perf_counter() - t0, "lost_main": len(lost),
                         "survival_rate": sum(s["survived"] for s in surv) / max(1, len(surv)), "timing": info["timing"]})
        first = first or {s["id"]: s for s in surv}
        score = (len(lost), -attempts[-1]["survival_rate"])
        if best is None or score < best[0]:  # keep the best pass, not the last: a stronger ControlNet can collapse
            best = (score, a, out, ink, surv)
        if not lost or a == RERUNS:
            break
        cn += CN_STEP
    _, kept, out, ink, surv = best
    for i, at in enumerate(attempts):
        at["kept"] = i == kept
    out.save(out_dir / "stylized.png")
    final = ink.copy()
    for s in surv:  # every element records how it reached the final design
        s["iou0"], s["survived0"] = first[s["id"]]["iou"], first[s["id"]]["survived"]
        s["path"] = "as_generated" if s["survived0"] else "rerun" if s["survived"] else "lost"
        if not s["survived"] and s["role"] in ("hero", "support"):
            m = R[s["id"]]
            final[m] = comp[m]  # vector fallback: the clean symbol replaces the output inside its box
            s["path"] = "vector"
    Image.fromarray(final.astype(np.uint8) * 255).save(out_dir / "ink.png")
    rep = {"k": k, "size": [w, h], "crop": [x0, y0, x1, y1], "diffusion_size": [sw, sh], "attempts": attempts, "elements": surv,
           "prompt": info["prompt"], "tokens": info["tokens"], "settings": {x: info[x] for x in ("seed", "steps", "cfg", "lora", "lora_scale", "cn_scale", "circular", "device")}}
    (out_dir / "survival.json").write_text(json.dumps(rep, indent=1))
    return rep


# ---------- traced, layered rendering of stylized ink ----------
def layered_curves(L, ink, k):
    """Trace the ink mask; each closed path takes the layer of the element box it overlaps most (none: figure ink)."""
    size = canvas(L)
    B, lay = [], []
    for e in L["elements"]:
        for c in copies(L, e, size):
            B.append([v * k for v in bbox(c)])
            lay.append(INK if e.get("body") else e["layer"])
    B, lay = np.array(B), np.array(lay)
    out = []
    for c in trace(ink):
        a = np.array(c)
        x0, y0, x1, y1 = a[:, 0].min(), a[:, 1].min(), a[:, 0].max(), a[:, 1].max()
        ov = np.clip(np.minimum(B[:, 2], x1) - np.maximum(B[:, 0], x0), 0, None) * np.clip(np.minimum(B[:, 3], y1) - np.maximum(B[:, 1], y0), 0, None)
        if not len(ov) or ov.max() <= 0:
            out.append((c, INK))
            continue
        cov = np.round(ov / max(1e-9, (x1 - x0) * (y1 - y0)), 2)  # share of the path's box covered; ties -> innermost element
        best = np.lexsort(((B[:, 2] - B[:, 0]) * (B[:, 3] - B[:, 1]), -cov))[0]
        out.append((c, int(lay[best])))
    return out


def curves_to_labels(curves, k, scale, size):
    """Rasterise layered curves at scale (layout px -> output px) with even-odd fill per layer."""
    W, H = round(size[0] * scale), round(size[1] * scale)
    f = scale / k
    lab = np.zeros((H, W), np.uint8)
    for layer in (INK, FILLER, BORDER, ACCENT):
        acc = np.zeros((H, W), bool)
        for c, l in curves:
            if l != layer:
                continue
            pts = [(x * f, y * f) for x, y in c]
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            x0, y0 = max(0, int(min(xs))), max(0, int(min(ys)))
            x1, y1 = min(W, int(max(xs)) + 2), min(H, int(max(ys)) + 2)
            if x1 <= x0 or y1 <= y0:
                continue
            m = Image.new("1", (x1 - x0, y1 - y0))
            ImageDraw.Draw(m).polygon([(x - x0, y - y0) for x, y in pts], fill=1)
            acc[y0:y1, x0:x1] ^= np.asarray(m)
        lab[acc] = layer
    return Image.fromarray(lab)


def curves_svg(curves, k, size, colours, label):
    W, H = size
    paths = []
    for layer in (INK, FILLER, BORDER, ACCENT):
        d = " ".join("M" + " L".join(f"{x / k:.1f},{y / k:.1f}" for x, y in c) + "Z" for c, l in curves if l == layer)
        if d:
            paths.append(f'<path d="{d}" fill="{colours[layer]}" fill-rule="evenodd"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}">'
            f"<title>Chhaap design</title><desc>{label}</desc><metadata>{label}</metadata>"
            f'<rect width="{W:.0f}" height="{H:.0f}" fill="{colours[0]}"/>' + "".join(paths) + "</svg>")


if __name__ == "__main__":  # survival logic on synthetic output, no diffusion: an erased element must be found lost
    from .layout import layout
    L = layout("medallion", 768, 768, "kansari", [{"beat": "b", "symbol_ids": ["farmer", "tree", "sun"]}], "balanced", None, "dots", seed=5)
    k = 1.0
    comp = np.asarray(render_labels(L, k)) > 0
    R = regions(L, k, (768, 768))
    hero = next(e for e in L["elements"] if e["role"] == "hero")
    damaged = comp.copy()
    damaged[R[hero["id"]]] = False
    s = {x["id"]: x for x in survival(L, comp, damaged, R)}
    assert s[hero["id"]]["survived"] is False and s[hero["id"]]["iou"] < 0.2
    assert all(x["survived"] for x in survival(L, comp, comp, R))
    curves = layered_curves(L, comp, k)
    back = np.asarray(curves_to_labels(curves, k, 1.0, (768, 768)))
    lab = np.asarray(render_labels(L, k))
    agree = ((back > 0) == (lab > 0)).mean()
    layer_ok = (back[(back > 0) & (lab > 0)] == lab[(back > 0) & (lab > 0)]).mean()
    assert agree > 0.97 and layer_ok > 0.9, (agree, layer_ok)
    print("studio ok", round(float(agree), 4), "layer agreement", round(float(layer_ok), 3))
