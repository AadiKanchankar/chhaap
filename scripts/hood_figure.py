"""Builds eval/figures/under_the_hood.png: one proof stage by stage (control, step previews, tile, two-tone)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from chhaap.generate import generate  # noqa: E402
from chhaap.vectorize import vectorize  # noqa: E402
from scripts.contact_sheet import contact_sheet  # noqa: E402

ROOT = Path(__file__).parent.parent
p = generate("wedding", seed=21, run_id="fig_hood")
run = ROOT / "runs" / p["id"]
vectorize(run / "tile.png")
paths = [run / "control.png", *sorted((run / "steps").glob("*.png")), run / "tile.png", run / "two_tone.png"]
contact_sheet(paths, ROOT / "eval/figures/under_the_hood.png", cols=len(paths), width=2048)
print(p["id"], p["lora"], len(paths))
