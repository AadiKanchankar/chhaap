"""Two-tone threshold (Otsu) -> potrace (potracer) -> SVG. render() redraws the curves at any size for print."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

LABEL = "AI-generated, Warli-inspired. Not a GI-certified Warli painting."
LABELS = {frozenset({"warli"}): LABEL, frozenset({"mandana"}): "AI-generated, Mandana-inspired. Not a hand-painted Mandana.",
          frozenset({"warli", "mandana"}): "AI-generated, inspired by Warli and Mandana."}


def label_for(packs):
    """Export label for the art forms a design draws on (decor shapes do not count)."""
    return LABELS.get(frozenset(set(packs) & {"warli", "mandana"}) or frozenset({"warli"}), LABEL)


def otsu(a):
    hist = np.bincount(a.ravel(), minlength=256).astype(float)
    w = hist.cumsum()
    m = (hist * np.arange(256)).cumsum()
    between = (m[-1] * w - m * w[-1]) ** 2 / np.maximum(w * (w[-1] - w), 1)
    return int(between.argmax())


def two_tone(tile):
    """Returns (ink mask bool, ink rgb, ground rgb). Ink = the lighter tone (rice paste on geru)."""
    rgb = np.asarray(tile.convert("RGB"))
    g = np.asarray(tile.convert("L"))
    ink = g > otsu(g)
    if ink.mean() > 0.5:  # ground is the majority tone
        ink = ~ink
    col = lambda m: tuple(int(v) for v in rgb[m].mean(0)) if m.any() else (0, 0, 0)
    return ink, col(ink), col(~ink)


def trace(mask):
    """Closed curves as lists of (x, y) points (Bezier segments flattened to 8 points each), in tile pixels."""
    import potrace  # pip "potracer"; the potrace CLI needs root to install here
    curves = []
    xy = lambda p: (p.x, p.y)
    for c in potrace.Bitmap(~mask).trace(turdsize=4, alphamax=1.0):  # potracer fills the falsy pixels
        pts, p0 = [xy(c.start_point)], xy(c.start_point)
        for s in c.segments:
            if s.is_corner:
                pts += [xy(s.c), xy(s.end_point)]
            else:
                pts += [_bez(p0, xy(s.c1), xy(s.c2), xy(s.end_point), k / 8) for k in range(1, 9)]
            p0 = xy(s.end_point)
        curves.append(pts)
    return curves


def _bez(p0, p1, p2, p3, t):
    u = 1 - t
    return tuple(u ** 3 * a + 3 * u * u * t * b + 3 * u * t * t * c + t ** 3 * d for a, b, c, d in zip(p0, p1, p2, p3))


def to_svg(curves, size, ink, ground):
    W, H = size
    hexc = lambda c: "#%02x%02x%02x" % c
    d = " ".join("M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in c) + "Z" for c in curves)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            f"<title>Chhaap tile</title><desc>{LABEL}</desc><metadata>{LABEL}</metadata>"
            f'<rect width="{W}" height="{H}" fill="{hexc(ground)}"/><path d="{d}" fill="{hexc(ink)}" fill-rule="evenodd"/></svg>')


def render(curves, src_size, out_px, ink, ground):
    """Rasterise curves at out_px square with even-odd fill (XOR per curve), 2x supersampled."""
    ss, k = 2, 2 * out_px / src_size
    acc = np.zeros((out_px * ss, out_px * ss), bool)
    for c in curves:
        m = Image.new("1", acc.shape[::-1])
        ImageDraw.Draw(m).polygon([(x * k, y * k) for x, y in c], fill=1)
        acc ^= np.asarray(m)
    big = Image.fromarray(np.where(acc[..., None], ink, ground).astype("uint8"))
    return big.resize((out_px, out_px), Image.LANCZOS)


def vectorize(tile_path):
    """Writes two_tone.png and tile.svg next to the tile. Returns (curves, ink, ground)."""
    tile_path = Path(tile_path)
    tile = Image.open(tile_path)
    mask, ink, ground = two_tone(tile)
    Image.fromarray(np.where(mask[..., None], ink, ground).astype("uint8")).save(tile_path.parent / "two_tone.png")
    curves = trace(mask)
    (tile_path.parent / "tile.svg").write_text(to_svg(curves, tile.size, ink, ground))
    return curves, ink, ground


if __name__ == "__main__":  # traced curves, re-rasterised, must match the two-tone mask
    from .compose import compose
    tile = Image.merge("RGB", [compose("tarpa", seed=2)[0].point(lambda v, k=k: 60 + v * k) for k in (0.7, 0.6, 0.5)])
    mask, *_ = two_tone(tile)
    back = np.asarray(render(trace(mask), 512, 512, (255, 255, 255), (0, 0, 0)).convert("L")) > 127
    assert (back == mask).mean() > 0.98, (back == mask).mean()
    print("vectorize ok", round(float((back == mask).mean()), 4))
