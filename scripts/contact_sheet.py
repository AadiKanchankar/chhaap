"""Grid of images, at most 1024px wide. Usage: python scripts/contact_sheet.py OUT.png IMG... [--cols N] [--labels]"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw


def contact_sheet(paths, out, cols=None, labels=False, width=1024):
    cols = cols or math.ceil(math.sqrt(len(paths)))
    cell = width // cols
    rows = math.ceil(len(paths) / cols)
    sheet = Image.new("RGB", (cols * cell, rows * cell), "white")
    d = ImageDraw.Draw(sheet)
    for i, p in enumerate(paths):
        im = Image.open(p).convert("RGB")
        im.thumbnail((cell - 4, cell - 4))
        x, y = (i % cols) * cell + 2, (i // cols) * cell + 2
        sheet.paste(im, (x, y))
        if labels:
            d.text((x + 3, y + 3), Path(p).stem[:28], fill="red")
    sheet.save(out)
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cols = int(sys.argv[sys.argv.index("--cols") + 1]) if "--cols" in sys.argv else None
    if cols:
        args.remove(str(cols))
    print(contact_sheet(args[1:], args[0], cols, "--labels" in sys.argv))
