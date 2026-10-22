"""Clean the Mandana class with the Warli pipeline (dedupe, size, CLIP filter, manual review, 80/20 split).
Writes data/clean/mandana/{train,heldout}, data/manifest_mandana.csv and mandana_train.zip (for the Colab notebook).
data/manifest.csv is left alone: the E2 probe split depends on it."""
import csv
import random
import shutil
import sys
import zipfile
from collections import Counter
from pathlib import Path

import imagehash
from PIL import Image, ImageOps

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from scripts.prepare_data import EXTS, LICENSE, RAW, URL, class_of  # noqa: E402

CLEAN = ROOT / "data/clean/mandana"
PROMPTS = ["a Mandana floor or wall painting, white geometric lines on a red ground",
           "a product photo of a t-shirt, mug, bag, cushion or phone case",
           "an image covered by a large watermark", "an image that is mostly printed text"]


def main(sheet_only=False):
    rows = []
    for p in sorted(x for x in RAW.rglob("*") if x.suffix.lower() in EXTS and class_of(x) == "mandana"):
        with Image.open(p) as im:
            w, h = im.size
        rows.append(dict(file=str(p.relative_to(ROOT)), **{"class": "mandana"}, w=w, h=h, kept="yes", drop_reason="", split=""))
    hashes = []
    for r in rows:
        hsh = imagehash.phash(Image.open(ROOT / r["file"]).convert("RGB"))
        if any(hsh - k <= 6 for k in hashes):
            r.update(kept="no", drop_reason="duplicate (phash<=6)")
            continue
        hashes.append(hsh)
        if min(r["w"], r["h"]) < 512:
            r.update(kept="no", drop_reason="short side < 512")
    from chhaap.metrics import _clip, clip_embed
    import torch
    cand = [r for r in rows if r["kept"] == "yes"]
    img = clip_embed([ROOT / r["file"] for r in cand])
    with torch.no_grad():
        t = _clip["model"].get_text_features(**_clip["proc"](text=PROMPTS, return_tensors="pt", padding=True)).pooler_output
    best = (torch.from_numpy(img) @ torch.nn.functional.normalize(t, dim=-1).T).argmax(1).tolist()
    for r, b in zip(cand, best):
        if b:
            r.update(kept="no", drop_reason=f"CLIP filter: {PROMPTS[b].split(',')[0]}")
    review = ROOT / "data/manual_review_mandana.csv"
    manual = {r["file"]: r["drop_reason"] for r in csv.DictReader(open(review))} if review.exists() else {}
    for r in rows:
        if r["kept"] == "yes" and r["file"] in manual:
            r.update(kept="no", drop_reason=manual[r["file"]])
    kept = [r for r in rows if r["kept"] == "yes"]
    if sheet_only:  # contact sheets for the manual review, numbered in file order
        from scripts.contact_sheet import contact_sheet
        for i in range(0, len(kept), 24):
            contact_sheet([ROOT / r["file"] for r in kept[i:i + 24]], ROOT / f"data/review_mandana_{i // 24}.png", cols=6, labels=True)
        print("review sheets:", (len(kept) + 23) // 24, "kept so far:", len(kept))
        for i, r in enumerate(kept):  # sheet, row, column -> file, for writing data/manual_review_mandana.csv
            print(i // 24, (i % 24) // 6, i % 6, r["file"])
        return
    random.Random(0).shuffle(kept)
    n_train = round(0.8 * len(kept))
    shutil.rmtree(CLEAN, ignore_errors=True)
    for i, r in enumerate(kept):
        r["split"] = "train" if i < n_train else "heldout"
        out = CLEAN / r["split"] / (Path(r["file"]).stem + ".png")
        out.parent.mkdir(parents=True, exist_ok=True)
        ImageOps.fit(Image.open(ROOT / r["file"]).convert("RGB"), (512, 512), Image.LANCZOS).save(out)
    with open(ROOT / "data/manifest_mandana.csv", "w", newline="") as f:
        w = csv.DictWriter(f, ["file", "class", "source_url", "license", "w", "h", "kept", "drop_reason", "split"])
        w.writeheader()
        w.writerows({**r, "source_url": URL, "license": LICENSE} for r in rows)
    with zipfile.ZipFile(ROOT / "mandana_train.zip", "w") as z:
        for p in sorted((CLEAN / "train").glob("*.png")):
            z.write(p, f"train/{p.name}")  # the notebook expects data/train/
    print("mandana:", len(rows), "kept:", len(kept), "train:", n_train, "heldout:", len(kept) - n_train,
          "drops:", dict(Counter(r["drop_reason"].split(":")[0] for r in rows if r["kept"] == "no")))


if __name__ == "__main__":
    main(sheet_only="--sheets" in sys.argv)
