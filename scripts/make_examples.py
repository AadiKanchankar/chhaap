"""Pre-render demo designs into runs/d_ex_* (they show in the app's Gallery) and copy each mockup to examples/."""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from chhaap.planner import plan  # noqa: E402
from chhaap.products import make  # noqa: E402

ROOT = Path(__file__).parent.parent
EXAMPLES = [  # (brief, product, mode)
    ("A3 frame for my parents' anniversary. Wedding and harvest, maroon and mustard, busy, traditional border.", "frame_a3", "vector"),
    ("Saree with forest animals and peacocks, forest green and saffron, a chain of dancers on the border.", "saree", "vector"),
    ("Diary cover about village life, mustard and rust, calm and minimal.", "diary", "vector"),
    ("Phone wallpaper of the tarpa dance in rings, white on charcoal.", "phone", "vector"),
    ("Wallpaper for a nursery with forest animals, teal and ochre.", "wallpaper", "vector"),
    ("Tee with a wedding chauk on the chest, indigo and coral.", "tee", "vector"),
    ("Diwali floor design, mandana lotus, white on maroon, dense.", "frame_a4", "vector"),
    ("A4 frame, Warli harvest with a Mandana border, white on geru.", "frame_a4", "vector"),
    ("Wall art of the tarpa dance, white on indigo, busy.", "frame_a4", "stylized"),
    ("A4 print of village life in bands, white on geru, traditional border.", "frame_a4", "stylized"),
]

if __name__ == "__main__":
    out = ROOT / "examples"
    out.mkdir(exist_ok=True)
    for i, (brief, product, mode) in enumerate(EXAMPLES):
        run = ROOT / "runs" / f"d_ex_{i:02d}"
        if (run / "meta.json").exists():
            continue
        r = plan(brief, product, "rules")
        run.mkdir(parents=True, exist_ok=True)
        (run / "brief.json").write_text(json.dumps({"brief": brief, "planner": r}, indent=1))
        m = make(r["plan"], run, mode, seed=40 + i, log=lambda *_: None)
        shutil.copy(run / "mockup.png", out / f"{i:02d}_{product}_{mode}.png")
        print(i, product, mode, round(m["timing"]["total"], 1), flush=True)
