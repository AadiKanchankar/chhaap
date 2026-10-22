"""Seam score (SDR, wrap error), KID, CLIP style probe. Timing is recorded by generate.py in params.json."""
import pickle
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).parent.parent
PROBE = ROOT / "models/clip_probe.pkl"
CLIP = "openai/clip-vit-base-patch32"


def gray(tile):
    return np.asarray(Image.open(tile).convert("L") if isinstance(tile, (str, Path)) else tile.convert("L") if isinstance(tile, Image.Image) else tile, dtype=np.float64)


def grad_mag(a):
    return np.hypot(ndimage.sobel(a, 0), ndimage.sobel(a, 1))


def sdr(tile, band=4, n_lines=8, seed=0):
    """Seam Discontinuity Ratio: mean Sobel magnitude in band-px strips centred on the seams of a 2x2 mosaic,
    divided by the same at n_lines random interior lines (half vertical, half horizontal). ~1 = seamless."""
    t = gray(tile)
    H, W = t.shape
    g = grad_mag(np.tile(t, (2, 2)))
    h = band // 2
    seam = np.concatenate([g[:, W - h:W + h].ravel(), g[H - h:H + h, :].ravel()]).mean()
    rng = np.random.default_rng(seed)
    xs = rng.integers(band + 4, W - band - 4, n_lines // 2)
    ys = rng.integers(band + 4, H - band - 4, n_lines - n_lines // 2)
    interior = np.concatenate([g[:, x - h:x + h].ravel() for x in xs] + [g[y - h:y + h, :].ravel() for y in ys]).mean()
    return float(seam / max(interior, 1e-8))


def wrap_error(tile):
    """Mean |first - last| column and row difference over the mean adjacent interior column/row difference."""
    t = gray(tile)
    edge = (np.abs(t[:, 0] - t[:, -1]).mean() + np.abs(t[0, :] - t[-1, :]).mean()) / 2
    inner = (np.abs(np.diff(t, axis=1)).mean() + np.abs(np.diff(t, axis=0)).mean()) / 2
    return float(edge / max(inner, 1e-8))


def seam_heatmap(tile, reps=3):
    """Gradient magnitude of a reps x reps repeat, normalised to 0..255 (for the UI overlay)."""
    g = grad_mag(np.tile(gray(tile), (reps, reps)))
    return Image.fromarray((255 * g / max(np.percentile(g, 99.5), 1e-8)).clip(0, 255).astype("uint8"))


def _load(paths, size=None):
    ims = [Image.open(p).convert("RGB") for p in paths]
    return [im.resize((size, size)) for im in ims] if size else ims


def kid(gen_paths, ref_paths, subset_size=None):
    """Kernel Inception Distance (torchmetrics). Returns (mean, std)."""
    import torch
    from torchmetrics.image.kid import KernelInceptionDistance
    n = min(len(gen_paths), len(ref_paths))
    m = KernelInceptionDistance(subset_size=min(subset_size or n, n), normalize=True)
    to_t = lambda ps: torch.stack([torch.from_numpy(np.asarray(im)).permute(2, 0, 1).float() / 255 for im in _load(ps, 299)])
    m.update(to_t(ref_paths), real=True)
    m.update(to_t(gen_paths), real=False)
    mean, std = m.compute()
    return float(mean), float(std)


_clip = {}


def clip_embed(paths, batch=32):
    import torch
    from transformers import CLIPModel, CLIPProcessor
    if not _clip:
        _clip.update(model=CLIPModel.from_pretrained(CLIP).eval(), proc=CLIPProcessor.from_pretrained(CLIP))
    out = []
    for i in range(0, len(paths), batch):
        with torch.no_grad():
            x = _clip["proc"](images=_load(paths[i:i + batch]), return_tensors="pt")
            e = _clip["model"].get_image_features(**x).pooler_output  # transformers 5: projected embedding
        out.append(torch.nn.functional.normalize(e, dim=-1).numpy())
    return np.concatenate(out)


def train_probe(paths, labels, seed=0):
    """Logistic regression on CLIP embeddings of all classes; 80/20 stratified split. Saves model + test accuracy."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    X = clip_embed(paths)
    Xtr, Xte, ytr, yte = train_test_split(X, labels, test_size=0.2, stratify=labels, random_state=seed)
    clf = LogisticRegression(max_iter=2000).fit(Xtr, ytr)
    info = dict(test_accuracy=float(clf.score(Xte, yte)), n_train=len(ytr), n_test=len(yte), classes=list(clf.classes_))
    PROBE.parent.mkdir(exist_ok=True)
    PROBE.write_bytes(pickle.dumps((clf, info)))
    return info


def warli_prob(paths):
    clf, _ = pickle.loads(PROBE.read_bytes())
    return clf.predict_proba(clip_embed(paths))[:, list(clf.classes_).index("warli")]
