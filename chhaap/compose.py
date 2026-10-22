"""Story -> symbols -> toroidal layout -> white-on-black control image. Symbols are drawn from lexicon.visual_rule.

visual_rule is a tiny recipe in symbol units (symbol spans -0.5..0.5, y down), commands separated by ';':
  disc x y r | hole x y r | poly x1 y1 x2 y2 ... | line x1 y1 x2 y2 ... | rect x0 y0 x1 y1
  rays x y r0 r1 n | arc x y r deg0 deg1 | use ID x y scale | circle_of ID n radius scale
"""
import csv
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

DATA = Path(__file__).parent.parent / "data"
LEXICON = {r["id"]: {**r, "pack": "warli"} for r in csv.DictReader(open(DATA / "lexicon.csv"))}
if (DATA / "lexicon_mandana.csv").exists():  # second motif pack (v2); ids are prefixed m_
    LEXICON.update({r["id"]: {**r, "pack": "mandana"} for r in csv.DictReader(open(DATA / "lexicon_mandana.csv"))})

# First entry is drawn large at the centre, the rest are scattered on the torus. (id, count)
STORIES = {
    "harvest": [("kansari", 1), ("vaghadevta", 1), ("farmer", 2), ("tree", 2), ("sun", 1), ("bird", 2), ("hut", 1), ("ladder", 1)],
    "wedding": [("lagna_chauk", 1), ("pachsera_deva", 1), ("drummer", 1), ("tarpa_player", 1), ("woman", 2), ("man", 1), ("tree", 1), ("bird", 1)],
    "tarpa": [("tarpa_dance", 1), ("moon", 1), ("tree", 2), ("hut", 1), ("drummer", 1), ("woman", 1), ("bird", 1)],
    "village_day": [("hut", 1), ("hut", 1), ("woman_pot", 2), ("man", 1), ("farmer", 1), ("animal", 1), ("bird", 1), ("tree", 2), ("sun", 1)],
    "forest": [("tree", 1), ("tree", 2), ("peacock", 1), ("animal", 2), ("bird", 2), ("mountain", 1), ("fish", 2), ("sun", 1)],
}


def draw_symbol(d, sid, cx, cy, s, depth=0, ink=255, hole=0, body=None, rot=0.0, jit=None, lw=None):
    """Interpret the visual_rule of sid (lexicon row, else layout DECOR shape) at centre (cx, cy), size s pixels.
    d: PIL ImageDraw or layout.SvgDraw. ink/hole: fill values. body: fill for poly ops (alternate-figure accent).
    rot: degrees clockwise. jit: random.Random for hand-drawn jitter (None = exact). lw: line width override."""
    rule = LEXICON[sid]["visual_rule"] if sid in LEXICON else DECOR[sid]
    lw0 = lw or max(2, round(0.035 * s))
    c, si = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    J = (lambda k: jit.gauss(0, k)) if jit else (lambda k: 0.0)

    def P(a, k=0.0):
        out = []
        for i in range(0, len(a) - 1, 2):
            x, y = a[i] + J(k), a[i + 1] + J(k)
            out.append((cx + (x * c - y * si) * s, cy + (x * si + y * c) * s))
        return out

    W = lambda: max(1, round(lw0 * (jit.uniform(0.8, 1.25) if jit else 1)))
    for cmd in rule.split(";"):
        op, *a = cmd.split()
        if op in ("use", "circle_of"):
            ref, nums = a[0], [float(v) for v in a[1:]]
        else:
            nums = [float(v) for v in a]
        if op in ("disc", "hole"):
            (x, y), r = P(nums[:2])[0], nums[2] * s * (jit.uniform(0.93, 1.07) if jit else 1)
            d.ellipse([x - r, y - r, x + r, y + r], fill=ink if op == "disc" else hole)
        elif op == "poly":
            d.polygon(P(nums, 0.006), fill=ink if body is None else body)
        elif op == "line":
            d.line(P(nums, 0.008), fill=ink, width=W(), joint="curve")
        elif op == "rect":
            x0, y0, x1, y1 = nums
            d.line(P([x0, y0, x1, y0, x1, y1, x0, y1, x0, y0], 0.004), fill=ink, width=W(), joint="curve")
        elif op == "rays":
            x, y, r0, r1, n = nums
            for k in range(int(n)):
                t = 2 * math.pi * k / n
                d.line(P([x + r0 * math.cos(t), y + r0 * math.sin(t), x + r1 * math.cos(t), y + r1 * math.sin(t)], 0.006), fill=ink, width=W())
        elif op == "arc":
            x, y, r, a0, a1 = nums
            (px, py), R = P([x, y])[0], r * s
            d.arc([px - R, py - R, px + R, py + R], a0 + rot, a1 + rot, fill=ink, width=W())
        elif op == "use":
            x, y, k = nums
            (px, py), = P([x, y])
            draw_symbol(d, ref, px, py, k * s, depth + 1, ink, hole, body, rot, jit, lw and lw * k)
        elif op == "circle_of":
            n, r, k = nums
            for i in range(int(n)):
                t = 2 * math.pi * i / n
                (px, py), = P([r * math.cos(t), r * math.sin(t)])
                draw_symbol(d, ref, px, py, k * s, depth + 1, ink, hole, body, rot, jit, lw and lw * k)
        else:
            raise ValueError(f"{sid}: unknown op {op!r}")


# Layout-only shapes (borders, fillers). Not lexicon symbols: they never reach a meaning card.
DECOR = {
    "_dot": "disc 0 0 0.22",
    "_tick": "line -0.18 0.4 -0.3 -0.2; line 0 0.4 0 -0.42; line 0.18 0.4 0.3 -0.2",
    "_star": "rays 0 0 0.12 0.45 8; disc 0 0 0.12",
    "_tri": "poly -0.5 0.45 0 -0.45 0.5 0.45",
    "_chev": "line -0.45 0.2 0 -0.2 0.45 0.2",
    "_leaf": "line -0.5 0 0.5 0; poly 0 0 0.2 -0.42 0.36 -0.08; poly 0 0 -0.2 0.42 -0.36 0.08",
    "_ring": "arc 0 0 0.5 0 360",
    "_rule": "line -0.5 0 0.5 0",
}


def torus_dist(a, b, W, H):
    dx, dy = abs(a[0] - b[0]) % W, abs(a[1] - b[1]) % H
    return math.hypot(min(dx, W - dx), min(dy, H - dy))


def compose(story, enabled=None, seed=0, W=512, H=512):
    """Returns (control image 'L', placed) where placed = [{id, x, y, size}]. enabled: set of ids to keep (None = all)."""
    rng = random.Random(seed)
    placed = []
    for i, (sid, n) in enumerate(STORIES[story]):
        if enabled is not None and sid not in enabled:
            continue
        for _ in range(n):
            big = i == 0
            size = 0.46 * W if big else rng.uniform(0.15, 0.2) * W
            for _try in range(300):
                pos = (W / 2, H / 2) if big else (rng.uniform(0, W), rng.uniform(0, H))
                if all(torus_dist(pos, (p["x"], p["y"]), W, H) > 0.5 * (size + p["size"]) * 0.95 for p in placed):
                    placed.append({"id": sid, "x": pos[0], "y": pos[1], "size": size})
                    break
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    for p in placed:  # draw each symbol 9 times shifted by +-W, +-H so edge-crossers wrap
        for ox in (-W, 0, W):
            for oy in (-H, 0, H):
                draw_symbol(d, p["id"], p["x"] + ox, p["y"] + oy, p["size"])
    return img, placed


if __name__ == "__main__":
    import numpy as np

    for sid in LEXICON:  # every recipe parses and draws
        draw_symbol(ImageDraw.Draw(Image.new("L", (64, 64))), sid, 32, 32, 60)
    for story in STORIES:
        img, placed = compose(story, seed=1)
        assert placed and {p["id"] for p in placed} <= {s for s, _ in STORIES[story]}, story
    # a symbol centred on the left edge must show up on the right edge too
    LEXICON["_t"] = {"visual_rule": "disc 0 0 0.4"}
    img = Image.new("L", (128, 128))
    for ox in (-128, 0, 128):
        draw_symbol(ImageDraw.Draw(img), "_t", 0 + ox, 64, 40)
    a = np.asarray(img)
    assert a[:, :3].max() == 255 and a[:, -3:].max() == 255
    print("compose ok")
