"""Layered colour (exact, from the layout's label raster) and a procedural texture pass for raster exports."""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from .layout import LAYERS

PALETTES = {p["id"]: p for p in json.loads((Path(__file__).parent.parent / "data/palettes.json").read_text())}


def rgb(hexc):
    return tuple(int(hexc[i:i + 2], 16) for i in (1, 3, 5))


def hexes(pid):
    """Label value -> hex, for SVG."""
    return {i: PALETTES[pid][name] for i, name in enumerate(LAYERS)}


def colourize(labels, pid):
    """Label raster (values 0-4) -> RGB image in palette pid."""
    lut = np.array([rgb(PALETTES[pid][name]) for name in LAYERS], np.uint8)
    return Image.fromarray(lut[np.asarray(labels)])


def texture(img, labels, seed=0, strength=1.0):
    """Mud-wall grain multiplied over the ground, and slightly uneven ink opacity so the wall shows through the paint."""
    rs = np.random.default_rng(seed)
    w, h = img.size
    lab = np.asarray(labels)
    low = lambda k: np.asarray(Image.fromarray((rs.random((max(2, h // k), max(2, w // k))) * 255).astype(np.uint8))
                               .resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(k / 4)), np.float32) / 255 - 0.5
    grain = 1 + strength * (0.10 * low(max(8, w // 60)) + 0.05 * low(max(2, w // 400)) + 0.03 * (rs.random((h, w), np.float32) - 0.5))
    a = np.asarray(img, np.float32)
    wall = a[lab == 0].mean(0) if (lab == 0).any() else a.reshape(-1, 3).mean(0)
    paint = np.clip(0.88 + strength * 0.25 * low(max(4, w // 150)), 0.72, 1.0)[..., None]  # rice paste coverage per spot
    ink = lab[..., None] > 0
    out = np.where(ink, a * paint + wall * (1 - paint), a) * grain[..., None]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


if __name__ == "__main__":
    from .layout import layout, render_labels
    assert len(PALETTES) == 8 and all(len(hexes(p)) == 5 for p in PALETTES)
    L = layout("medallion", 600, 600, "kansari", [{"beat": "b", "symbol_ids": ["farmer", "tree"]}], "balanced", None, "dots", seed=3)
    lab = render_labels(L)
    for pid in PALETTES:
        im = colourize(lab, pid)
        a, l = np.asarray(im), np.asarray(lab)
        for i, name in enumerate(LAYERS):  # every layer pixel carries exactly its palette colour
            if (l == i).any():
                assert (a[l == i] == rgb(PALETTES[pid][name])).all(), (pid, name)
        t = np.asarray(texture(im, lab, 1), np.float32)
        assert 2 < np.abs(t - a).mean() < 40, np.abs(t - a).mean()
    print("palette ok")
