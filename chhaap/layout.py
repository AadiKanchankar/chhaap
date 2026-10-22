"""Layout engine (v2): template + story beats -> layered elements at product size -> label raster, control image, SVG.

Element: {sid, x, y, s, rot, role, layer, pack, seed, lw?, body?} in product pixels. role: hero | support | filler | border.
Layers (label values): 0 ground, 1 figure ink, 2 accent (hero, alternate figure bodies), 3 border band, 4 filler.
Scale hierarchy: hero = 3 x support = 8 x filler. Repeats wrap through a lattice (straight, half_drop, brick).
"""
import math
import random
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw

from .compose import DECOR, LEXICON, draw_symbol

GROUND, INK, ACCENT, BORDER, FILLER = range(5)
LAYERS = ["ground", "ink", "accent", "border", "filler"]
ROLE_LAYER = {"hero": ACCENT, "support": INK, "filler": FILLER, "border": BORDER}
FIGURES = {"human", "man", "woman", "woman_pot", "drummer", "tarpa_player", "farmer", "kansari", "palghata"}
TEMPLATES = ["tarpa_spiral", "registers", "medallion", "all_over_buti", "mandana_medallion"]
BORDERS = ["triangles", "chevrons", "dots", "vine", "dancers", "dehri", "lotus"]
DENSITY = {"sparse": 0.07, "balanced": 0.12, "dense": 0.17}  # ink-coverage target of the filler pass
SPACING = {"sparse": 1.6, "balanced": 1.3, "dense": 1.1}  # gap factor between repeated supports
FILLERS = ["_dot", "_tick", "bird", "_star"]


# ---------- geometry ----------
@lru_cache(None)
def extent(sid):
    """Drawn extent of a symbol in symbol units (x0, y0, x1, y1), measured once by rendering it."""
    im = Image.new("L", (800, 800))
    draw_symbol(ImageDraw.Draw(im), sid, 400, 400, 400)
    x0, y0, x1, y1 = im.getbbox() or (400, 400, 401, 401)
    return ((x0 - 400) / 400, (y0 - 400) / 400, (x1 - 400) / 400, (y1 - 400) / 400)


def bbox(e):
    x0, y0, x1, y1 = extent(e["sid"])
    if e["sid"] == "_rule":
        y0, y1 = -0.01, 0.01
    c, s = math.cos(math.radians(e["rot"])), math.sin(math.radians(e["rot"]))
    pts = [(x * c - y * s, x * s + y * c) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    xs, ys = [p[0] * e["s"] + e["x"] for p in pts], [p[1] * e["s"] + e["y"] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def inter(a, b):
    w, h = min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0.0


def area(b):
    return (b[2] - b[0]) * (b[3] - b[1])


def lattice(L):
    """Translation vectors of the repeat, or None for a single composition."""
    W, H = L["W"], L["H"]
    return {"straight": ((W, 0), (0, H)), "half_drop": ((W, H / 2), (0, H)), "brick": ((W, 0), (W / 2, H))}.get(L["repeat"])


def period(L):
    """Smallest straight-repeating rectangle: what circular padding needs."""
    return {"half_drop": (2 * L["W"], L["H"]), "brick": (L["W"], 2 * L["H"])}.get(L["repeat"], (L["W"], L["H"]))


def copies(L, e, canvas=None):
    """e and its lattice translates that touch the canvas."""
    v = lattice(L)
    if not v:
        return [e]
    cw, ch = canvas or (L["W"], L["H"])
    out, k = [], math.ceil(max(cw / L["W"], ch / L["H"])) + 2
    for i in range(-k, k + 1):
        for j in range(-k, k + 1):
            dx, dy = i * v[0][0] + j * v[1][0], i * v[0][1] + j * v[1][1]
            c = {**e, "x": e["x"] + dx, "y": e["y"] + dy}
            b, m = bbox(c), 0.1 * e["s"]  # margin: jittered strokes can leave the box
            if b[2] > -m and b[3] > -m and b[0] < cw + m and b[1] < ch + m:
                out.append(c)
    return out


def el(sid, x, y, s, role, rot=0.0, **kw):
    return {"sid": sid, "x": x, "y": y, "s": s, "rot": rot, "role": role, "layer": ROLE_LAYER[role],
            "pack": LEXICON[sid]["pack"] if sid in LEXICON else "decor", **kw}


def boxes(L, els):
    """Bounding boxes of els and their lattice copies, as an (n, 4) array."""
    near = (L["W"] * 3, L["H"] * 3) if lattice(L) else None
    return np.array([bbox(c) for e in els for c in (copies(L, e, near) if near else [e])] or np.zeros((0, 4)), float).reshape(-1, 4)


def free(L, e, B, pad=0.0):
    """True if e clears every box in B (from boxes()) by pad pixels. e's own copies are covered by B's copies."""
    x0, y0, x1, y1 = bbox(e)
    return not ((B[:, 0] < x1 + pad) & (B[:, 2] > x0 - pad) & (B[:, 1] < y1 + pad) & (B[:, 3] > y0 - pad)).any()


def place_free(L, box, sids, size, role, rng, tries=400):
    """Rejection-sample sids into box (x0, y0, x1, y1) without overlapping anything placed so far. Returns how many fit."""
    B, n = boxes(L, L["elements"]), 0  # border elements too: the medallion's frame sits inside the content box
    for sid in sids:
        if box[2] - box[0] < size or box[3] - box[1] < size:
            break
        for _ in range(tries):
            e = el(sid, rng.uniform(box[0] + size / 2, box[2] - size / 2), rng.uniform(box[1] + size / 2, box[3] - size / 2), size, role)
            if free(L, e, B, pad=0.05 * size):
                L["elements"].append(e)
                B = np.vstack([B, boxes(L, [e])])
                n += 1
                break
    return n


# ---------- border kit ----------
def strip(kind, x0, y0, length, thick, rot=0.0):
    """A repeating border strip along +x from (x0, y0) (top-left), thickness thick, then rotated by rot about (x0, y0)."""
    m = thick * (0.9 if kind in ("dancers", "dehri", "lotus") else 0.62)
    sid = {"triangles": "_tri", "chevrons": "_chev", "dots": "_dot", "vine": "_leaf", "dancers": "human", "dehri": "m_dehri", "lotus": "m_lotus4"}[kind]
    w = (extent(sid)[2] - extent(sid)[0]) * m
    step = w * {"triangles": 1.0, "chevrons": 0.75, "dots": 1.6, "vine": 1.0, "dancers": 1.0, "dehri": 1.0, "lotus": 1.15}[kind]
    n = max(1, int(length // step))
    gap = (length - n * step) / 2 + step / 2
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    T = lambda u, v: (x0 + u * c - v * s, y0 + u * s + v * c)
    out = [el(sid, *T(gap + k * step, thick / 2), m, "border", rot, lw=max(2, m * (0.09 if kind == "chevrons" else 0.05)) if sid in DECOR else None)
           for k in range(n)]
    out += [el("_rule", *T(length / 2, v), length, "border", rot, lw=max(2, thick * 0.05)) for v in (thick * 0.04, thick * 0.96)]
    return out


def frame(W, H, kind, thick, margin):
    return (strip(kind, margin, margin, W - 2 * margin, thick) + strip(kind, W - margin, H - margin, W - 2 * margin, thick, 180)
            + strip(kind, W - margin, margin + thick, H - 2 * margin - 2 * thick, thick, 90)
            + strip(kind, margin, H - margin - thick, H - 2 * margin - 2 * thick, thick, 270))


# ---------- templates ----------
def _figs(beats):
    ids = [i for b in beats for i in b["symbol_ids"]]
    return [i for i in ids if i in FIGURES] or ["human", "woman"]


def tarpa_spiral(L, cb, hero, beats, rng):
    cx, cy, R = (cb[0] + cb[2]) / 2, (cb[1] + cb[3]) / 2, min(cb[2] - cb[0], cb[3] - cb[1]) / 2
    n = {"sparse": 2, "balanced": 3, "dense": 4}[L["density"]]
    h = 0.92 * R / (1.15 + 0.383 * (n - 1))
    sup = h / 3
    hero = hero if hero in LEXICON else "tarpa_player"
    L["elements"].append(el(hero, cx, cy, h, "hero"))
    hr = h * max(math.hypot(x, y) for x in extent(hero)[::2] for y in extent(hero)[1::2])  # hero's corner radius
    dancers = ["human", "woman"]
    for k in range(n):
        r = hr + 0.6 * sup + k * 1.15 * sup
        wid = (extent("human")[2] - extent("human")[0]) * sup
        cnt = max(6, int(2 * math.pi * (r - 0.5 * sup) / (wid * 1.04)))  # spaced on the inner circle, so boxes never meet
        L["elements"].append(el("_ring", cx, cy, 2 * (r - 0.02 * sup), "support", lw=max(2, 0.03 * sup), decor_of="tarpa_dance"))
        off = rng.random()
        for i in range(cnt):
            t = 2 * math.pi * (i + off) / cnt
            L["elements"].append(el(dancers[(i + k) % 2], cx + r * math.cos(t), cy + r * math.sin(t), sup, "support", math.degrees(t) + 90))
    rest = [i for b in beats for i in b["symbol_ids"] if i not in FIGURES and i != hero]
    for corner in ((cb[0], cb[1]), (cb[2], cb[1]), (cb[0], cb[3]), (cb[2], cb[3])):
        box = (min(corner[0], cx), min(corner[1], cy), max(corner[0], cx), max(corner[1], cy))
        place_free(L, box, rest[:2] or ["tree"], sup, "support", rng)
        rest = rest[2:] + rest[:2]


def registers(L, cb, hero, beats, rng):
    beats = beats[:4] if len(beats) >= 2 else beats + [{"beat": "dance", "symbol_ids": ["tarpa_player", "woman", "human"]}]
    n = len(beats)
    hi = next((k for k, b in enumerate(beats) if hero in b["symbol_ids"]), n // 2)
    sep = (cb[3] - cb[1]) * 0.03
    u = (cb[3] - cb[1] - (n - 1) * sep) / (n - 1 + 2.2)
    y, gap = cb[1], SPACING[L["density"]]
    for k, b in enumerate(beats):
        bh = 2.2 * u if k == hi else u
        sup = 0.6 * u
        ids = [i for i in b["symbol_ids"] if i != hero] or ["tree"]
        if k == hi:  # hero at the centre, supports either side
            hs = min(2.0 * u, 0.5 * (cb[2] - cb[0]))
            L["elements"].append(el(hero, (cb[0] + cb[2]) / 2, y + bh / 2, hs, "hero"))
            sides = [(cb[0], (cb[0] + cb[2]) / 2 - hs / 2), ((cb[0] + cb[2]) / 2 + hs / 2, cb[2])]
        else:
            sides = [(cb[0], cb[2])]
        j = 0  # one counter across both sides of the hero, so each planned symbol appears before any repeats
        for x0, x1 in sides:
            slots = max(1, int((x1 - x0) // (sup * gap)))
            for i in range(slots):
                sx = x0 + (i + 0.5) * (x1 - x0) / slots
                L["elements"].append(el(ids[j % len(ids)], sx, y + bh - sup / 2 - 0.08 * u, sup, "support"))
                j += 1
        y += bh
        if k < n - 1:
            L["elements"] += strip("dots", cb[0], y + sep * 0.15, cb[2] - cb[0], sep * 0.7)
            y += sep


def medallion(L, cb, hero, beats, rng):
    cx, cy = (cb[0] + cb[2]) / 2, (cb[1] + cb[3]) / 2
    C = 0.5 * min(cb[2] - cb[0], cb[3] - cb[1])
    if hero in ("chauk", "lagna_chauk"):
        L["elements"].append(el(hero, cx, cy, C, "hero"))
    else:
        L["elements"].append(el("_frame", cx, cy, C, "border", lw=max(2, 0.02 * C)))
        L["elements"].append(el(hero, cx, cy, 0.75 * C, "hero"))
    sup = (C if hero in ("chauk", "lagna_chauk") else 0.75 * C) / 3
    rest = [i for b in beats for i in b["symbol_ids"] if i != hero] or ["tree", "bird"]
    k = 0
    for qx, qy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):  # one scene per quadrant, radiating from the chauk
        for d in (0.62, 0.9):
            px, py = cx + qx * d * (cb[2] - cb[0]) / 2, cy + qy * d * (cb[3] - cb[1]) / 2
            e = el(rest[k % len(rest)], px, py, sup, "support")
            if free(L, e, boxes(L, L["elements"]), pad=0.05 * sup) and cb[0] <= bbox(e)[0] and bbox(e)[2] <= cb[2] and cb[1] <= bbox(e)[1] and bbox(e)[3] <= cb[3]:
                L["elements"].append(e)
                k += 1  # advance only on success, or planned symbols are skipped
        k += place_free(L, (min(cx, cx + qx * (cb[2] - cb[0]) / 2), min(cy, cy + qy * (cb[3] - cb[1]) / 2),
                            max(cx, cx + qx * (cb[2] - cb[0]) / 2), max(cy, cy + qy * (cb[3] - cb[1]) / 2)), [rest[k % len(rest)]], sup, "support", rng)
    missing = [i for i in dict.fromkeys(rest) if i not in {e["sid"] for e in L["elements"]}]
    place_free(L, cb, missing, sup, "support", rng)  # planned symbols the quadrant slots had no room for


def all_over_buti(L, cb, hero, beats, rng):
    cols = {"sparse": 2, "balanced": 4, "dense": 6}[L["density"]]  # even: the inner half-drop wraps
    cw = (cb[2] - cb[0]) / cols
    rows = max(2, round((cb[3] - cb[1]) / cw))
    ch = (cb[3] - cb[1]) / rows
    ids = [i for b in beats for i in b["symbol_ids"] if i not in ("tarpa_dance", "lagna_chauk", "chauk", "vaghadevta")] or ["tree"]
    k = 0
    for c in range(cols):
        for r in range(rows):
            y = cb[1] + (r + 0.5 + 0.5 * (c % 2)) * ch
            L["elements"].append(el(ids[k % len(ids)], cb[0] + (c + 0.5) * cw, y % L["H"], 0.55 * min(cw, ch), "support"))
            k += 1


def mandana_medallion(L, cb, hero, beats, rng):
    """Mandana: a centre motif in concentric rings, symmetric about 8 axes, with a motif in each corner."""
    cx, cy, R = (cb[0] + cb[2]) / 2, (cb[1] + cb[3]) / 2, min(cb[2] - cb[0], cb[3] - cb[1]) / 2
    ids = [i for b in beats for i in b["symbol_ids"] if i != hero] or ["m_lotus4", "m_surya", "m_bijni"]
    h = 0.62 * R
    L["elements"].append(el(hero if hero in LEXICON else "m_lotus8", cx, cy, h, "hero"))
    sup = h / 3
    n_rings = {"sparse": 1, "balanced": 2, "dense": 3}[L["density"]]
    for k in range(n_rings):
        r = h / 2 + sup * (0.75 + 1.15 * k)
        n = 8 * (k + 1) if k < 2 else 24
        sid = ids[k % len(ids)]
        for i in range(n):  # rotated so each motif's axis points at the centre: the 8-fold symmetry of a floor mandana
            t = 2 * math.pi * i / n
            e = el(sid, cx + r * math.cos(t), cy + r * math.sin(t), sup * (1 if k == 0 else 0.8), "support", math.degrees(t) + 90)
            if not any(sat(obb(e, 0.05), obb(o, 0.05)) for o in L["elements"] if o["role"] in ("hero", "support") and inter(bbox(e), bbox(o)) > 0):
                L["elements"].append(e)
        L["elements"].append(el("_ring", cx, cy, 2 * (r + sup * 0.62), "support", lw=max(2, 0.025 * sup)))
    corner = ids[n_rings % len(ids)]
    for qx, qy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        px, py = cx + qx * ((cb[2] - cb[0]) / 2 - sup * 0.7), cy + qy * ((cb[3] - cb[1]) / 2 - sup * 0.7)
        e = el(corner, px, py, sup, "support", 45 * qx * qy)
        if free(L, e, boxes(L, L["elements"]), pad=0.02 * sup):
            L["elements"].append(e)


def border_strip(L, cb, hero, beats, rng):
    """A single border band filling the canvas: saree borders, diary spines."""
    L["elements"] += strip(L["border"] or "dancers", cb[0], cb[1], cb[2] - cb[0], cb[3] - cb[1])


def scatter(L, cb, hero, beats, rng):
    """E8 baseline, v1's rule on the same symbols: hero large at the centre, the rest at random positions kept apart
    only by centre distance (0.95 x mean size), so boxes may overlap. No fillers, no structure."""
    W = min(cb[2] - cb[0], cb[3] - cb[1])
    cx, cy = (cb[0] + cb[2]) / 2, (cb[1] + cb[3]) / 2
    L["elements"].append(el(hero, cx, cy, 0.46 * W, "hero"))
    for sid in [i for b in beats for i in b["symbol_ids"] if i != hero]:
        size = rng.uniform(0.15, 0.2) * W
        for _ in range(300):
            x, y = rng.uniform(cb[0] + size / 2, cb[2] - size / 2), rng.uniform(cb[1] + size / 2, cb[3] - size / 2)
            if all(math.hypot(x - e["x"], y - e["y"]) > 0.5 * (size + e["s"]) * 0.95 for e in L["elements"] if e["role"] != "border"):
                L["elements"].append(el(sid, x, y, size, "support"))
                break


DECOR["_frame"] = "rect -0.48 -0.48 0.48 0.48; rect -0.42 -0.42 0.42 0.42"
BUILD = {"tarpa_spiral": tarpa_spiral, "registers": registers, "medallion": medallion, "all_over_buti": all_over_buti, "strip": border_strip, "scatter": scatter, "mandana_medallion": mandana_medallion}


# ---------- filler pass ----------
def coverage(L, box=None):
    lab = render_labels(L, scale=min(1.0, 384 / max(L["W"], L["H"])))
    k = lab.width / L["W"]
    a = np.asarray(lab)
    if box:
        a = a[int(box[1] * k):int(box[3] * k), int(box[0] * k):int(box[2] * k)]
    return float((a > 0).mean())


def fill(L, cb, rng):
    """Scatter fillers into empty space until ink coverage of the content box reaches the density target."""
    sups = [e["s"] for e in L["elements"] if e["role"] == "support" and e["sid"] in LEXICON] or [min(L["W"], L["H"]) / 8]
    f = float(np.median(sups)) * 3 / 8
    target, cov, placed, misses = DENSITY[L["density"]], coverage(L, cb), 0, 0
    packs = [e["pack"] for e in L["elements"] if e["role"] in ("hero", "support") and e["pack"] != "decor"]
    fillers = ["_dot", "_star"] if packs.count("mandana") > len(packs) / 2 else FILLERS  # no Warli birds in a Mandana
    B = boxes(L, [e for e in L["elements"] if e["role"] != "border" or e["sid"] == "_frame"])
    while cov < target and misses < 600:
        e = el(rng.choice(fillers), rng.uniform(cb[0] + f / 2, cb[2] - f / 2), rng.uniform(cb[1] + f / 2, cb[3] - f / 2), f * rng.uniform(0.6, 1.0), "filler")
        if free(L, e, B, pad=0.35 * f):
            L["elements"].append(e)
            B = np.vstack([B, boxes(L, [e])])
            placed += 1
            misses = 0
            if placed % 12 == 0:
                cov = coverage(L, cb)
        else:
            misses += 1
    L["coverage"], L["fillers"] = coverage(L, cb), placed


# ---------- entry point ----------
def layout(template, W, H, hero, beats, density="balanced", repeat=None, border=None, seed=0):
    """Returns a layout dict: W, H, template, density, repeat, border, seed, elements, content, coverage, fillers."""
    rng = random.Random(seed)
    L = {"W": W, "H": H, "template": template, "density": density, "repeat": repeat, "border": border, "seed": seed, "elements": []}
    cb = (0, 0, W, H)
    if template == "strip":
        cb = (0.01 * W, 0.08 * H, 0.99 * W, 0.92 * H)
    elif border and not repeat:
        thick, margin = 0.045 * min(W, H), 0.035 * min(W, H)
        L["elements"] += frame(W, H, border, thick, margin)
        g = margin + thick + 0.025 * min(W, H)
        cb = (g, g, W - g, H - g)
    elif not repeat:
        g = 0.05 * min(W, H)
        cb = (g, g, W - g, H - g)
    L["content"] = cb
    BUILD[template](L, cb, hero, beats, rng)
    if template != "all_over_buti" and L["density"] == "dense":
        for i, e in enumerate(x for x in L["elements"] if x["role"] == "support" and x["sid"] in FIGURES):
            e["body"] = i % 2 == 1  # alternate figures take the accent colour on their triangle bodies
    if template in ("strip", "scatter"):
        L["coverage"], L["fillers"] = coverage(L, cb), 0
    else:
        fill(L, cb, rng)
    for i, e in enumerate(L["elements"]):
        e["seed"], e["id"] = seed * 100003 + i, i
    return L


def obb(e, shrink=0.0):
    """Oriented bounding box corners, each side pulled in by shrink of its length."""
    x0, y0, x1, y1 = extent(e["sid"])
    dx, dy = (x1 - x0) * shrink, (y1 - y0) * shrink
    c, s = math.cos(math.radians(e["rot"])), math.sin(math.radians(e["rot"]))
    return [(e["x"] + (x * c - y * s) * e["s"], e["y"] + (x * s + y * c) * e["s"])
            for x, y in ((x0 + dx, y0 + dy), (x1 - dx, y0 + dy), (x1 - dx, y1 - dy), (x0 + dx, y1 - dy))]


def sat(p, q):
    """Separating-axis test for two convex quads: True if they overlap."""
    for poly in (p, q):
        for i in range(4):
            (ax, ay), (bx, by) = poly[i], poly[(i + 1) % 4]
            nx, ny = by - ay, ax - bx
            pa, qa = [x * nx + y * ny for x, y in p], [x * nx + y * ny for x, y in q]
            if max(pa) <= min(qa) or max(qa) <= min(pa):
                return False
    return True


def overlaps(L, tol=0.05):
    """Pairs of hero/support symbols whose oriented boxes, each shrunk by tol per side, still overlap (lattice-aware)."""
    main = [e for e in L["elements"] if e["role"] in ("hero", "support") and e["sid"] in LEXICON]
    n = 0
    for i, a in enumerate(main):
        ba, pa = bbox(a), obb(a, tol)
        for b in main[i + 1:]:
            if any(inter(ba, bbox(c)) > 0 and sat(pa, obb(c, tol)) for c in (copies(L, b, (L["W"] * 3, L["H"] * 3)) if lattice(L) else [b])):
                n += 1
    return n


# ---------- rendering ----------
def _draw(L, d, scale, canvas, body_val=ACCENT, val=lambda e: e["layer"], hole=GROUND, off=0):
    for e in L["elements"]:
        for c in copies(L, e, canvas):
            draw_symbol(d, c["sid"], c["x"] * scale + off, c["y"] * scale + off, c["s"] * scale, ink=val(c), hole=hole,
                        body=body_val if c.get("body") else None, rot=c["rot"], jit=random.Random(c["seed"]) if "seed" in c else None,
                        lw=c["lw"] * scale if c.get("lw") else None)


def render_labels(L, scale=1.0, size=None):
    """Label raster (mode L, values 0-4) at scale. size: canvas in layout pixels (default W x H; period(L) for a straight super-tile)."""
    cw, ch = size or (L["W"], L["H"])
    w, h, m = max(1, round(cw * scale)), max(1, round(ch * scale)), _margin(L, scale)
    im = Image.new("L", (w + 2 * m, h + 2 * m), GROUND)
    _draw(L, ImageDraw.Draw(im), scale, (cw, ch), off=m)
    return im.crop((m, m, m + w, m + h))


def _margin(L, scale):
    """PIL truncates negative coordinates towards zero, so draw on a padded canvas where every copy lands at x, y >= 0."""
    return int(max((e["s"] for e in L["elements"]), default=0) * scale) + 4


def element_mask(L, e, scale, size=None):
    """Ink of one element (with its lattice copies) at scale: for the survival check."""
    cw, ch = size or (L["W"], L["H"])
    w, h, m = round(cw * scale), round(ch * scale), _margin({"elements": [e]}, scale)
    im = Image.new("1", (w + 2 * m, h + 2 * m))
    _draw({**L, "elements": [e]}, ImageDraw.Draw(im), scale, (cw, ch), body_val=1, val=lambda _: 1, hole=0, off=m)
    return np.asarray(im.crop((m, m, m + w, m + h)))


class SvgDraw:
    """The subset of PIL ImageDraw that draw_symbol uses, writing SVG. colours: label value -> '#rrggbb'."""

    def __init__(self, colours):
        self.c, self.out = colours, []

    def ellipse(self, b, fill):
        self.out.append(f'<circle cx="{(b[0] + b[2]) / 2:.1f}" cy="{(b[1] + b[3]) / 2:.1f}" r="{(b[2] - b[0]) / 2:.1f}" fill="{self.c[fill]}"/>')

    def polygon(self, pts, fill):
        self.out.append(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="{self.c[fill]}"/>')

    def line(self, pts, fill, width, joint=None):
        self.out.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="none" stroke="{self.c[fill]}" '
                        f'stroke-width="{width:.1f}" stroke-linejoin="round" stroke-linecap="round"/>')

    def arc(self, b, a0, a1, fill, width):
        cx, cy, r = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2, (b[2] - b[0]) / 2
        st = f'fill="none" stroke="{self.c[fill]}" stroke-width="{width:.1f}"'
        if a1 - a0 >= 359.9:
            return self.out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" {st}/>')
        p = lambda a: (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
        (x0, y0), (x1, y1) = p(a0), p(a1)
        self.out.append(f'<path d="M{x0:.1f},{y0:.1f} A{r:.1f},{r:.1f} 0 {int(a1 - a0 > 180)} 1 {x1:.1f},{y1:.1f}" {st}/>')


def to_svg(L, colours, label, scale=1.0, size=None):
    cw, ch = size or (L["W"], L["H"])
    W, H = cw * scale, ch * scale
    d = SvgDraw(colours)
    _draw(L, d, scale, (cw, ch))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}">'
            f"<title>Chhaap design</title><desc>{label}</desc><metadata>{label}</metadata>"
            f'<rect width="{W:.0f}" height="{H:.0f}" fill="{colours[GROUND]}"/>' + "".join(d.out) + "</svg>")


if __name__ == "__main__":
    beats = [{"beat": "sowing", "symbol_ids": ["farmer", "bird", "sun"]}, {"beat": "reaping", "symbol_ids": ["kansari", "tree", "ladder"]},
             {"beat": "dance", "symbol_ids": ["tarpa_player", "woman", "moon"]}]
    for t in TEMPLATES:
        for dens in DENSITY:
            rep = "half_drop" if t == "all_over_buti" else None
            L = layout(t, 1200, 1600, "kansari", beats, dens, rep, None if rep else "triangles", seed=1)
            assert any(e["role"] == "hero" for e in L["elements"]) or t == "all_over_buti", t
            assert overlaps(L) == 0, (t, dens, overlaps(L))
            planned = {i for b in beats for i in b["symbol_ids"]} - {"kansari"}
            if t in ("medallion", "registers"):  # every planned symbol is placed at least once
                assert planned <= {e["sid"] for e in L["elements"]}, (t, dens, planned - {e["sid"] for e in L["elements"]})
            print(t, dens, len(L["elements"]), "fillers", L["fillers"], "coverage", round(L["coverage"], 3))
    # a half-drop tile must wrap: its straight period (2W x H) has matching left/right and top/bottom edges
    L = layout("all_over_buti", 400, 400, None, beats, "dense", "half_drop", seed=2)
    pw, ph = period(L)
    assert (pw, ph) == (800, 400)
    a = np.asarray(render_labels(L, size=(2 * pw, 2 * ph)))
    assert (a[:, :pw] == a[:, pw:]).all() and (a[:ph] == a[ph:]).all()
    print("layout ok")
