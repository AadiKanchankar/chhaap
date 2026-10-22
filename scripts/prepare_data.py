"""Phase A data: download the Kaggle Indian paintings dataset, clean the Warli class, split, write data/manifest.csv.
Usage: python scripts/prepare_data.py   (needs ~/.kaggle/kaggle.json, or tries kagglehub anonymously)"""
import csv
import random
import shutil
import sys
from pathlib import Path

import imagehash
from PIL import Image, ImageOps

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
RAW, CLEAN = ROOT / "data/raw", ROOT / "data/clean/warli"
DATASET = "ajg117/indian-paintings-dataset"
URL = f"https://www.kaggle.com/datasets/{DATASET}"
LICENSE = "unclear, scraped; research use only"
CLASSES = ["gond", "kalighat", "kangra", "kerala mural", "madhubani", "mandana", "pichwai", "warli"]
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
# CLIP zero-shot filter: keep only images whose best prompt is the first one
PROMPTS = ["a Warli painting, white figures on a plain background", "a product photo of a t-shirt, mug, bag, cushion or phone case",
           "an image covered by a large watermark", "an image that is mostly printed text"]


def download():
    if any(RAW.rglob("*.jp*g")) or any(RAW.rglob("*.png")):
        return
    import kagglehub  # uses ~/.kaggle/kaggle.json when present
    src = Path(kagglehub.dataset_download(DATASET))
    shutil.copytree(src, RAW, dirs_exist_ok=True)


def class_of(p):
    for part in reversed(p.relative_to(RAW).parts[:-1]):
        name = part.lower().replace("_", " ").replace("-", " ")
        for c in CLASSES:
            if c in name or c.replace(" ", "") in name.replace(" ", ""):
                return c
    return None


def main():
    download()
    rows, warli = [], []
    for p in sorted(x for x in RAW.rglob("*") if x.suffix.lower() in EXTS):
        c = class_of(p)
        try:
            with Image.open(p) as im:
                w, h = im.size
        except Exception:
            rows.append(dict(file=str(p.relative_to(ROOT)), **{"class": c}, w=0, h=0, kept="no", drop_reason="unreadable", split=""))
            continue
        r = dict(file=str(p.relative_to(ROOT)), **{"class": c}, w=w, h=h, kept="yes", drop_reason="", split="probe")
        rows.append(r)
        if c == "warli":
            warli.append(r)

    hashes = []
    for r in warli:  # dedupe (phash <= 6) then size
        hsh = imagehash.phash(Image.open(ROOT / r["file"]).convert("RGB"))
        if any(hsh - k <= 6 for k in hashes):
            r.update(kept="no", drop_reason="duplicate (phash<=6)", split="")
            continue
        hashes.append(hsh)
        if min(r["w"], r["h"]) < 512:
            r.update(kept="no", drop_reason="short side < 512", split="")

    from chhaap.metrics import clip_embed, _clip
    cand = [r for r in warli if r["kept"] == "yes"]
    if cand:
        import torch
        img = clip_embed([ROOT / r["file"] for r in cand])
        with torch.no_grad():
            t = _clip["model"].get_text_features(**_clip["proc"](text=PROMPTS, return_tensors="pt", padding=True)).pooler_output
        best = (torch.from_numpy(img) @ torch.nn.functional.normalize(t, dim=-1).T).argmax(1).tolist()
        for r, b in zip(cand, best):
            if b:
                r.update(kept="no", drop_reason=f"CLIP filter: {PROMPTS[b].split(',')[0]}", split="")

    manual = {r["file"]: r["drop_reason"] for r in csv.DictReader(open(ROOT / "data/manual_review.csv"))}
    for r in warli:  # contact-sheet review: product shots the CLIP filter missed
        if r["kept"] == "yes" and r["file"] in manual:
            r.update(kept="no", drop_reason=manual[r["file"]], split="")
    kept = [r for r in warli if r["kept"] == "yes"]
    random.Random(0).shuffle(kept)
    n_train = round(0.8 * len(kept))
    shutil.rmtree(CLEAN, ignore_errors=True)
    for i, r in enumerate(kept):
        r["split"] = "train" if i < n_train else "heldout"
        out = CLEAN / r["split"] / (Path(r["file"]).stem + ".png")
        out.parent.mkdir(parents=True, exist_ok=True)
        ImageOps.fit(Image.open(ROOT / r["file"]).convert("RGB"), (512, 512), Image.LANCZOS).save(out)

    with open(ROOT / "data/manifest.csv", "w", newline="") as f:
        w = csv.DictWriter(f, ["file", "class", "source_url", "license", "w", "h", "kept", "drop_reason", "split"])
        w.writeheader()
        w.writerows({**r, "source_url": URL, "license": LICENSE} for r in rows)

    from collections import Counter
    print("classes:", dict(Counter(r["class"] for r in rows)))
    print("warli:", len(warli), "kept:", len(kept), "train:", n_train, "heldout:", len(kept) - n_train,
          "drops:", dict(Counter(r["drop_reason"] for r in warli if r["kept"] == "no")))


if __name__ == "__main__":
    main()
