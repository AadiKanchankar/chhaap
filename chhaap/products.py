"""Products (v2): plan -> parts (one layout each) -> stylize or vector -> assembled design -> print files and mockups.

Sizes are pixels at 300 DPI. Diffusion runs on each main part at <= 768 px (chhaap/studio.py); print files are drawn from
vectors (the layout itself, or the traced and layered stylized ink), never upscaled. Mockups are flat PIL drawings.
"""
import json
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, PngImagePlugin

from .compose import LEXICON
from .layout import layout, render_labels, to_svg
from .palette import PALETTES, colourize, hexes, rgb, texture
from .studio import canvas, curves_svg, curves_to_labels, layered_curves, stylize
from .vectorize import LABEL, label_for

PRODUCTS = {
    "frame_a4": {"name": "Wall frame A4", "size": (2480, 3508), "note": "Framed print, no repeat"},
    "frame_a3": {"name": "Wall frame A3", "size": (3508, 4961), "note": "Framed print, no repeat"},
    "saree": {"name": "Saree set", "size": (3600, 2400), "note": "Body repeat, border strip, pallu panel"},
    "diary": {"name": "Diary cover", "size": (3626, 2480), "note": "A5 wrap: back, spine, front"},
    "wallpaper": {"name": "Wallpaper", "size": (2048, 1024), "note": "Half-drop repeat tile"},
    "phone": {"name": "Phone wallpaper", "size": (1290, 2796), "note": "1290x2796 and 1080x2400"},
    "tee": {"name": "Tee", "size": (4500, 5400), "note": "Placement print, 15 x 18 in"},
}
SPINE = 130


def parts(plan, seed=0):
    """Part specs for a plan: name, W, H, template, repeat, border, stylize."""
    p, t, b = plan["product"], plan["template"], plan["border_style"]
    main = t if t != "all_over_buti" else "medallion"
    S = lambda name, W, H, template, repeat=None, border=None, stylize=True: dict(name=name, W=W, H=H, template=template, repeat=repeat, border=border, stylize=stylize)
    if p in ("frame_a4", "frame_a3"):
        W, H = PRODUCTS[p]["size"]
        out = [S("main", W, H, t, plan["repeat"] if t == "all_over_buti" else None, b)]
    elif p == "saree":
        out = [S("body", 1024, 1024, "all_over_buti", plan["repeat"] or "half_drop"), S("border", 3600, 400, "strip", None, b or "dancers", False),
               S("pallu", 3600, 2400, t if t in ("registers", "tarpa_spiral") else "registers")]
    elif p == "diary":
        out = [S("front", 1748, 2480, main, None, b or "triangles"), S("back", 1024, 1024, "all_over_buti", "straight"),
               S("spine", 2480, SPINE, "strip", None, b or "triangles", False)]
    elif p == "wallpaper":
        out = [S("tile", 1024, 1024, "all_over_buti", plan["repeat"] or "half_drop")]
    elif p == "phone":
        out = [S("1290x2796", 1290, 2796, main if main != "medallion" else "tarpa_spiral", None, b), S("1080x2400", 1080, 2400, main if main != "medallion" else "tarpa_spiral", None, b)]
    else:  # tee
        out = [S("print", 4500, 5400, t, plan["repeat"] if t == "all_over_buti" else None, None)] if t != "all_over_buti" else \
              [S("print", 1024, 1024, "all_over_buti", plan["repeat"] or "half_drop")]
    for i, x in enumerate(out):
        x["seed"] = seed * 10 + i
    return out


def build_layout(plan, spec):
    return layout(spec["template"], spec["W"], spec["H"], plan["hero_symbol_id"], plan["story_beats"], plan["density"],
                  spec["repeat"], spec["border"], seed=spec["seed"])


# ---------- labels at a scale ----------
class Part:
    """One built part: its layout, and (if stylized) the traced layered ink."""

    def __init__(self, spec, L, rep=None, ink=None):
        self.spec, self.L, self.rep, self.curves = spec, L, rep, None
        if ink is not None:
            self.curves = layered_curves(L, ink, rep["k"])

    def labels(self, scale):
        if self.curves is None:
            return render_labels(self.L, scale, canvas(self.L))
        return curves_to_labels(self.curves, self.rep["k"], scale, canvas(self.L))

    def svg(self, pid, label=LABEL):
        if self.curves is None:
            return to_svg(self.L, hexes(pid), label, 1.0, canvas(self.L))
        return curves_svg(self.curves, self.rep["k"], canvas(self.L), hexes(pid), label)


def tile_to(lab, size):
    out = Image.new(lab.mode, size)
    for x in range(0, size[0], lab.width):
        for y in range(0, size[1], lab.height):
            out.paste(lab, (x, y))
    return out


def assemble(product, P, scale):
    """Named label rasters (the deliverables) for a product at scale."""
    if product in ("frame_a4", "frame_a3"):
        return {"design": P["main"].labels(scale)}
    if product == "saree":
        return {"body_tile": P["body"].labels(scale), "border": P["border"].labels(scale), "pallu": P["pallu"].labels(scale)}
    if product == "diary":
        front, back = P["front"].labels(scale), P["back"].labels(scale)
        spine = P["spine"].labels(scale).transpose(Image.Transpose.ROTATE_90)
        wrap = Image.new("L", (front.width * 2 + spine.width, front.height))
        wrap.paste(tile_to(back, front.size), (0, 0))
        wrap.paste(spine, (front.width, 0))
        wrap.paste(front, (front.width + spine.width, 0))
        return {"wrap": wrap}
    if product == "wallpaper":
        return {"tile": P["tile"].labels(scale)}
    if product == "phone":
        return {k: P[k].labels(scale) for k in ("1290x2796", "1080x2400")}
    lab = P["print"].labels(scale)
    if P["print"].L["repeat"]:
        lab = tile_to(lab, (round(4500 * scale), round(5400 * scale)))
    return {"print": lab}


def paint(lab, pid, seed, textured=True):
    im = colourize(lab, pid)
    return texture(im, lab, seed) if textured else im


# ---------- mockups (flat PIL drawings) ----------
def _font(px):
    try:
        return ImageFont.load_default(size=px)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


def _label(img, colour=(70, 60, 50), label=LABEL):
    d = ImageDraw.Draw(img)
    d.text((img.width * 0.02, img.height - img.height * 0.045), label, fill=colour, font=_font(max(12, img.width // 80)))
    return img


def _wall(size, colour=(233, 226, 214), seed=0):
    rs = np.random.default_rng(seed)
    n = np.asarray(Image.fromarray((rs.random((size[1] // 6, size[0] // 6)) * 255).astype(np.uint8)).resize(size, Image.BICUBIC), np.float32)
    a = np.array(colour, np.float32)[None, None] * (0.97 + 0.06 * n[..., None] / 255)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def _shadow(base, box, r=18, off=(10, 16), alpha=110):
    sh = Image.new("L", base.size)
    ImageDraw.Draw(sh).rectangle([box[0] + off[0], box[1] + off[1], box[2] + off[0], box[3] + off[1]], fill=alpha)
    sh = sh.filter(ImageFilter.GaussianBlur(r))
    base.paste((40, 32, 26), mask=sh)


def frame_mockup(design, W=1400):
    H = int(W * 0.8)
    out = _wall((W, H))
    h = int(H * 0.72)
    w = int(h * design.width / design.height)
    mat, wood = int(h * 0.07), int(h * 0.035)
    x0, y0 = (W - w) // 2 - mat - wood, int(H * 0.08)
    box = (x0, y0, x0 + w + 2 * (mat + wood), y0 + h + 2 * (mat + wood))
    _shadow(out, box)
    d = ImageDraw.Draw(out)
    d.rectangle(box, fill=(58, 40, 30))
    d.rectangle([box[0] + wood, box[1] + wood, box[2] - wood, box[3] - wood], fill=(246, 242, 234))
    out.paste(design.resize((w, h), Image.LANCZOS), (box[0] + wood + mat, box[1] + wood + mat))
    return out


def wall_mockup(tile, W=1600):
    H = int(W * 0.62)
    out = _wall((W, H))
    wall_h = int(H * 0.82)
    tw = W // 3
    pat = tile_to(tile.resize((tw, int(tw * tile.height / tile.width)), Image.LANCZOS), (W, wall_h))
    out.paste(pat, (0, 0))
    d = ImageDraw.Draw(out)
    d.rectangle([0, wall_h, W, wall_h + int(H * 0.025)], fill=(245, 241, 233))
    d.rectangle([0, wall_h + int(H * 0.025), W, H], fill=(150, 112, 80))
    return out


def phone_mockup(screens, W=1400):
    H = int(W * 0.75)
    out = _wall((W, H), (226, 221, 212))
    d = ImageDraw.Draw(out)
    ph = int(H * 0.82)
    for i, s in enumerate(screens):
        pw = int(ph * s.width / s.height)
        x0 = int(W * (0.3 + 0.4 * i)) - pw // 2 - 14
        box = (x0, int(H * 0.06), x0 + pw + 28, int(H * 0.06) + ph + 28)
        _shadow(out, box, 14, (6, 12))
        d.rounded_rectangle(box, radius=int(pw * 0.13), fill=(24, 22, 22))
        m = Image.new("L", (pw, ph))
        ImageDraw.Draw(m).rounded_rectangle([0, 0, pw - 1, ph - 1], radius=int(pw * 0.11), fill=255)
        out.paste(s.resize((pw, ph), Image.LANCZOS), (box[0] + 14, box[1] + 14), m)
        d.rounded_rectangle([box[0] + 14 + pw * 0.36, box[1] + 22, box[0] + 14 + pw * 0.64, box[1] + 22 + pw * 0.06], radius=10, fill=(24, 22, 22))
    return out


def saree_mockup(body, border, pallu, W=1800):
    """Flat saree laid out: body repeat with border strips along both edges and the pallu panel at one end."""
    H = int(W * 0.5)
    out = _wall((W, H), (236, 230, 220))
    sw, sh = int(W * 0.9), int(H * 0.62)
    bh = int(sh * 0.12)
    cloth = Image.new("RGB", (sw, sh))
    tw = int(sh / 1.6)
    cloth.paste(tile_to(body.resize((tw * body.width // body.height, tw), Image.LANCZOS), (sw, sh)), (0, 0))
    pw = int(sh * pallu.height / pallu.width)
    cloth.paste(pallu.transpose(Image.Transpose.ROTATE_90).resize((pw, sh), Image.LANCZOS), (sw - pw, 0))
    strip = tile_to(border.resize((int(bh * border.width / border.height), bh), Image.LANCZOS), (sw, bh))
    cloth.paste(strip, (0, 0))
    cloth.paste(strip.transpose(Image.Transpose.FLIP_TOP_BOTTOM), (0, sh - bh))
    a = np.asarray(cloth, np.float32)  # soft pleats across the body
    x = np.arange(sw)[None, :, None]
    folds = 1 - 0.07 * (0.5 + 0.5 * np.sin(x / (sw * 0.035))) * (x < sw * 0.45)
    cloth = Image.fromarray(np.clip(a * folds, 0, 255).astype(np.uint8))
    x0, y0 = (W - sw) // 2, int(H * 0.12)
    _shadow(out, (x0, y0, x0 + sw, y0 + sh), 16, (8, 12), 90)
    out.paste(cloth, (x0, y0))
    return out


def diary_mockup(wrap, W=1800):
    """Closed diary (front cover in perspective, spine edge) beside the open flat wrap."""
    H = int(W * 0.55)
    out = _wall((W, H), (230, 224, 214))
    fw = (wrap.width - SPINE * wrap.height // 2480) // 2
    front = wrap.crop((wrap.width - fw, 0, wrap.width, wrap.height))
    ch = int(H * 0.72)
    cw = int(ch * front.width / front.height)
    cover = front.resize((cw, ch), Image.LANCZOS)
    sq = 0.08  # perspective: the far edge is shorter
    coeffs = _persp([(0, 0), (cw, ch * sq / 2), (cw, ch * (1 - sq / 2)), (0, ch)], [(0, 0), (cw, 0), (cw, ch), (0, ch)])
    cover = cover.transform((cw, ch), Image.PERSPECTIVE, coeffs, Image.BICUBIC)
    mask = Image.new("L", (cw, ch))
    ImageDraw.Draw(mask).polygon([(0, 0), (cw, ch * sq / 2), (cw, ch * (1 - sq / 2)), (0, ch)], fill=255)
    x0, y0 = int(W * 0.06), int(H * 0.1)
    _shadow(out, (x0, y0, x0 + cw, y0 + ch), 16)
    d = ImageDraw.Draw(out)
    d.rectangle([x0 - 10, y0, x0, y0 + ch], fill=tuple(int(v * 0.7) for v in wrap.getpixel((wrap.width // 2, 10))))
    out.paste(cover, (x0, y0), mask)
    ow = int(W * 0.5)
    oh = int(ow * wrap.height / wrap.width)
    ox, oy = int(W * 0.46), (H - oh) // 2 - int(H * 0.03)
    _shadow(out, (ox, oy, ox + ow, oy + oh), 14)
    out.paste(wrap.resize((ow, oh), Image.LANCZOS), (ox, oy))
    return out


def _persp(src, dst):
    """Coefficients for Image.PERSPECTIVE mapping dst quad -> src quad."""
    A, b = [], []
    for (x, y), (u, v) in zip(dst, src):
        A += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]
        b += [u, v]
    return np.linalg.solve(np.array(A, float), np.array(b, float)).tolist()


def tee_mockup(design, repeat, ground, W=1200):
    s = W / 100
    body = [(30, 12), (40, 8), (44, 12), (56, 12), (60, 8), (70, 12), (88, 26), (78, 36), (72, 31), (72, 92), (28, 92), (28, 31), (22, 36), (12, 26)]
    mask = Image.new("L", (W, W))
    ImageDraw.Draw(mask).polygon([(x * s, y * s) for x, y in body], fill=255)
    out = _wall((W, W), (236, 230, 218))
    fill = tile_to(design.resize((W // 4, W // 4 * design.height // design.width), Image.LANCZOS), (W, W)) if repeat else Image.new("RGB", (W, W), ground)
    if not repeat:
        pw = int(30 * s)
        fill.paste(design.resize((pw, int(pw * design.height / design.width)), Image.LANCZOS), (int(35 * s), int(24 * s)))
    out.paste(fill, mask=mask)
    d = ImageDraw.Draw(out)
    d.line([(x * s, y * s) for x, y in body + body[:1]], fill=(60, 50, 40), width=3)
    d.ellipse([44 * s, 6 * s, 56 * s, 16 * s], fill=(236, 230, 218), outline=(60, 50, 40), width=3)
    return out


def mockup(product, rgbs, pid, label=LABEL):
    if product in ("frame_a4", "frame_a3"):
        out = frame_mockup(rgbs["design"])
    elif product == "saree":
        out = saree_mockup(rgbs["body_tile"], rgbs["border"], rgbs["pallu"])
    elif product == "diary":
        out = diary_mockup(rgbs["wrap"])
    elif product == "wallpaper":
        return _label(wall_mockup(rgbs["tile"]), (250, 245, 236), label)
    elif product == "phone":
        out = phone_mockup([rgbs["1290x2796"], rgbs["1080x2400"]])
    else:
        out = tee_mockup(rgbs["print"], False, rgb(PALETTES[pid]["ground"]))
    return _label(out, label=label)


def save_png(img, path, dpi=None, label=LABEL):
    info = PngImagePlugin.PngInfo()
    info.add_text("Description", label)
    info.add_text("Software", "Chhaap")
    img.save(path, pnginfo=info, **({"dpi": dpi} if dpi else {}))
    return str(path)


# ---------- orchestration ----------
def make(plan, run_dir, mode="stylized", seed=0, preview_px=1400, textured=True, log=print, settings=None):
    """Build every part, check survival, write previews and the mockup. Returns the run summary (also meta.json)."""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "plan.json").write_text(json.dumps(plan, indent=1))
    t0, P, timing, elements = time.perf_counter(), {}, {}, []
    for spec in parts(plan, seed):
        t1 = time.perf_counter()
        L = build_layout(plan, spec)
        (run_dir / f"layout_{spec['name']}.json").write_text(json.dumps({k: v for k, v in L.items()}, default=str))
        timing[f"layout_{spec['name']}"] = time.perf_counter() - t1
        rep, ink = None, None
        if mode == "stylized" and spec["stylize"]:
            log(f"stylizing {spec['name']}")
            t1 = time.perf_counter()
            rep = stylize(L, spec["seed"], run_dir / spec["name"], **(settings or {}))
            ink = np.asarray(Image.open(run_dir / spec["name"] / "ink.png")) > 0
            timing[f"stylize_{spec['name']}"] = time.perf_counter() - t1
            elements += [{**e, "part": spec["name"]} for e in rep["elements"]]
        else:
            elements += [{"id": e["id"], "sid": e["sid"], "role": e["role"], "survived": True, "path": "vector", "part": spec["name"]}
                         for e in L["elements"] if e["sid"] in LEXICON]
        P[spec["name"]] = Part(spec, L, rep, ink)
    packs = {e["pack"] for p in P.values() for e in p.L["elements"]}
    label = label_for(packs)
    t1 = time.perf_counter()
    scale = preview_px / max(PRODUCTS[plan["product"]]["size"])
    labs = assemble(plan["product"], P, scale)
    rgbs = {k: paint(v, plan["palette_id"], seed, textured) for k, v in labs.items()}
    for k, v in rgbs.items():
        save_png(v, run_dir / f"preview_{k}.png", label=label)
    save_png(mockup(plan["product"], rgbs, plan["palette_id"], label), run_dir / "mockup.png", label=label)
    timing["render_preview"] = time.perf_counter() - t1
    timing["total"] = time.perf_counter() - t0
    meta = {"id": run_dir.name, "mode": mode, "seed": seed, "textured": textured, "label": label, "packs": sorted(packs - {"decor"}), "settings": settings or {}, "plan": plan, "parts": [p.spec for p in P.values()],
            "previews": sorted(f"preview_{k}.png" for k in rgbs), "elements": elements, "timing": timing,
            "coverage": {k: p.L["coverage"] for k, p in P.items()}}
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=1, default=str))
    return meta


def load(run_dir):
    """Rebuild the Part objects of a finished run (layouts and traced ink) for export."""
    run_dir = Path(run_dir)
    meta = json.loads((run_dir / "meta.json").read_text())
    P = {}
    for spec in meta["parts"]:
        L = json.loads((run_dir / f"layout_{spec['name']}.json").read_text())
        L["content"] = tuple(L["content"])
        s = run_dir / spec["name"] / "survival.json"
        if s.exists():
            P[spec["name"]] = Part(spec, L, json.loads(s.read_text()), np.asarray(Image.open(run_dir / spec["name"] / "ink.png")) > 0)
        else:
            P[spec["name"]] = Part(spec, L)
    return meta, P


def export(run_dir, textured=None):
    """Print files at 300 DPI (texture on rasters only), one SVG per part, the mockup. Returns {name: path}."""
    run_dir = Path(run_dir)
    meta, P = load(run_dir)
    plan, pid = meta["plan"], meta["plan"]["palette_id"]
    textured = meta.get("textured", True) if textured is None else textured
    label = meta.get("label", LABEL)
    out = run_dir / "export"
    out.mkdir(exist_ok=True)
    files = {}
    rgbs = {}
    for k, lab in assemble(plan["product"], P, 1.0).items():
        rgbs[k] = paint(lab, pid, meta["seed"], textured)
        files[k] = save_png(rgbs[k], out / f"{plan['product']}_{k}.png", (300, 300), label)
    for name, part in P.items():
        (out / f"{plan['product']}_{name}.svg").write_text(part.svg(pid, label))
        files[f"{name}_svg"] = str(out / f"{plan['product']}_{name}.svg")
    small = {k: v.resize((max(1, v.width * 1400 // max(v.size)), max(1, v.height * 1400 // max(v.size))), Image.LANCZOS) for k, v in rgbs.items()}
    files["mockup"] = save_png(mockup(plan["product"], small, pid, label), out / f"{plan['product']}_mockup.png", label=label)
    return files
