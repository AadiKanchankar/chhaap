"""Phase D experiments. Usage: python scripts/run_eval.py [e1] [e2] [e5] [e6]   (default: all that can run)
Writes eval/results/<exp>.json and eval/figures/*.png. Same seeds and prompts in every condition."""
import json
import sys
import threading
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from chhaap import generate as G  # noqa: E402
from chhaap.compose import STORIES  # noqa: E402
from chhaap.metrics import kid, sdr, train_probe, warli_prob, wrap_error  # noqa: E402
from scripts.contact_sheet import contact_sheet  # noqa: E402

RES, FIG = ROOT / "eval/results", ROOT / "eval/figures"
RES.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
N = 50 if G.DEVICE == "cuda" else 16
SEEDS = list(range(N))
STORY = lambda s: list(STORIES)[s % len(STORIES)]
# E1 conditions: (mode, LoRA on, circular)
CONDS = {"a": ("text", False, False), "b": ("text", False, True), "c": ("text", True, False),
         "d": ("text", True, True), "e": ("full", True, True)}
HELDOUT = ROOT / "data/clean/warli/heldout"


class PeakRSS:
    """Samples VmRSS of this process every 50 ms; .peak in MB."""
    def __enter__(self):
        self.peak, self.on = 0, True
        def loop():
            while self.on:
                kb = int(next(l for l in open("/proc/self/status") if l.startswith("VmRSS")).split()[1])
                self.peak = max(self.peak, kb / 1024)
                time.sleep(0.05)
        self.t = threading.Thread(target=loop, daemon=True)
        self.t.start()
        return self

    def __exit__(self, *a):
        self.on = False
        self.t.join()


def tiles(cond):
    return [ROOT / f"runs/e1_{cond}_{s:03d}/tile.png" for s in SEEDS]


def run_cond(cond):
    mode, lora, circ = CONDS[cond]
    out = []
    with PeakRSS() as mem:
        for s in SEEDS:
            p = G.generate(STORY(s), seed=s, mode=mode, lora_scale=None if lora else 0.0, circular=circ,
                           preview=False, run_id=f"e1_{cond}_{s:03d}")
            out.append(p)
    return out, mem.peak


def stats(xs):
    return {"mean": float(np.mean(xs)), "std": float(np.std(xs, ddof=1)), "n": len(xs)}


def e1_e5():
    G.pipes()
    lora = G.has_lora()
    for m in ("text", "full"):  # untimed warm-up: the first LoRA call pays a one-off adapter setup (153 s in a smoke test)
        G.generate(STORY(0), seed=100, mode=m, preview=False, run_id=f"warmup_{m}")
    res, cost = {"lora_available": lora, "device": G.DEVICE, "seeds": SEEDS, "conditions": {}}, {"device": G.DEVICE, "conditions": {}}
    for cond, (mode, use_lora, circ) in CONDS.items():
        if use_lora and not lora and cond != "e":
            res["conditions"][cond] = {"status": "not run: no trained LoRA (models/warli_lora.safetensors missing)"}
            continue
        runs, peak = run_cond(cond)
        sd, we = [sdr(t) for t in tiles(cond)], [wrap_error(t) for t in tiles(cond)]
        secs = [sum(v for k, v in p["timing"].items() if k != "steps") for p in runs]
        res["conditions"][cond] = {"mode": mode, "lora": runs[0]["lora"], "circular": circ, "steps": runs[0]["steps"],
                                   "cfg": runs[0]["cfg"], "sdr": stats(sd), "wrap_error": stats(we), "sdr_values": sd, "wrap_values": we}
        cost["conditions"][cond] = {"seconds_per_image": stats(secs), "peak_rss_mb": peak,
                                    "denoise_seconds": stats([p["timing"]["denoise"] for p in runs])}
        print(cond, res["conditions"][cond]["sdr"], cost["conditions"][cond]["seconds_per_image"], flush=True)
    from scipy.stats import wilcoxon
    a, e = res["conditions"]["a"], res["conditions"]["e"]
    res["wilcoxon_e_vs_a"] = {m: dict(zip(("statistic", "p_value"), map(float, wilcoxon(e[f"{m}_values"], a[f"{m}_values"]))))
                              for m in ("sdr", "wrap")}
    res["note_e"] = "condition e used the Warli LoRA" if e["lora"] else "condition e ran without a LoRA (none trained yet): composer + ControlNet + circular"
    (RES / "e1.json").write_text(json.dumps(res, indent=1))
    (RES / "e5.json").write_text(json.dumps(cost, indent=1))
    # figure: 2x2 mosaics (seams visible at the centre cross), rows = conditions, 4 seeds
    from PIL import Image
    paths = []
    for cond in CONDS:
        if "sdr" not in res["conditions"][cond]:
            continue
        for s in SEEDS[:4]:
            t = Image.open(tiles(cond)[s])
            m = Image.new("RGB", (1024, 1024))
            for x in (0, 512):
                for y in (0, 512):
                    m.paste(t, (x, y))
            q = ROOT / f"runs/e1_{cond}_{s:03d}/mosaic.png"
            m.save(q)
            paths.append(q)
    contact_sheet(paths, FIG / "e1_mosaics.png", cols=4)


def e1_posthoc():
    """Added after E1: SDR fails in both directions (a framed tile scores << 1, a broken seam >> 1), so the mean hides
    both. Summarise each tile by |log SDR|, and re-measure with 64 interior lines to test denominator noise."""
    from scipy.stats import wilcoxon
    res = json.loads((RES / "e1.json").read_text())
    out = {"note": "post-hoc, defined after inspecting E1", "conditions": {}}
    for cond, r in res["conditions"].items():
        if "sdr_values" not in r:
            continue
        s8 = np.array(r["sdr_values"])
        s64 = np.array([sdr(t, n_lines=64) for t in tiles(cond)])
        out["conditions"][cond] = {"abs_log_sdr": stats(np.abs(np.log(s8)).tolist()), "abs_log_sdr64": stats(np.abs(np.log(s64)).tolist()),
                                   "sdr64": stats(s64.tolist()), "within_0.8_1.25": int(((s8 > 0.8) & (s8 < 1.25)).sum()),
                                   "abs_log_values": np.abs(np.log(s8)).tolist(), "abs_log64_values": np.abs(np.log(s64)).tolist()}
    ctrl = [ROOT / f"runs/e1_e_{s:03d}/control.png" for s in SEEDS]  # seamless by construction, as sparse as e
    out["control_images"] = {"abs_log_sdr": stats([abs(np.log(sdr(t))) for t in ctrl]),
                             "abs_log_sdr64": stats([abs(np.log(sdr(t, n_lines=64))) for t in ctrl])}
    c = out["conditions"]
    for k in ("abs_log", "abs_log64"):
        for x, y in (("b", "a"), ("e", "a"), ("d", "c")):
            if x in c and y in c:
                st, pv = wilcoxon(c[x][f"{k}_values"], c[y][f"{k}_values"])
                out[f"wilcoxon_{k}_{x}_vs_{y}"] = {"statistic": float(st), "p_value": float(pv)}
    (RES / "e1_posthoc.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out["control_images"]))
    for k, v in c.items():
        print(k, {m: round(v[m]["mean"], 3) for m in ("abs_log_sdr", "abs_log_sdr64", "sdr64")}, v["within_0.8_1.25"])


def e2():
    import csv
    held = sorted(HELDOUT.glob("*.png"))
    if not held:
        (RES / "e2.json").write_text(json.dumps({"status": "not run: no held-out Warli images (Kaggle dataset not downloaded)"}, indent=1))
        return
    rows = [r for r in csv.DictReader(open(ROOT / "data/manifest.csv")) if r["split"] in ("probe", "train") and r["class"]]  # held-out Warli never trains the probe
    probe = train_probe([ROOT / r["file"] for r in rows], [r["class"] for r in rows])
    out = {"probe": probe, "heldout_n": len(held), "conditions": {}}
    for cond in "ace":
        ts = [t for t in tiles(cond) if t.exists()]
        if len(ts) < len(SEEDS):
            out["conditions"][cond] = {"status": "not run: E1 condition not generated (needs the trained LoRA)" if cond == "c" else "not run: E1 tiles missing"}
            continue
        k_mean, k_std = kid(ts, held, subset_size=min(N, len(held)))
        out["conditions"][cond] = {"kid_mean": k_mean, "kid_std": k_std, "warli_prob": stats(warli_prob(ts).tolist()), "n": len(ts)}
        print(cond, out["conditions"][cond], flush=True)
    out["reference_warli_prob_heldout"] = stats(warli_prob(held).tolist())
    (RES / "e2.json").write_text(json.dumps(out, indent=1))


def e6():
    ck = {s: ROOT / f"models/checkpoints/warli_lora_{s}.safetensors" for s in (500, 1000, 1500)}
    if not all(p.exists() for p in ck.values()):
        (RES / "e6.json").write_text(json.dumps({"status": "not run: LoRA checkpoints missing (run train/train_lora_colab.ipynb)"}, indent=1))
        return
    pipe = G.pipes()["cn"]
    grid, out = [], {"seed": 3, "story": STORY(3), "cells": []}
    for s, path in ck.items():
        pipe.delete_adapters("warli")
        pipe.load_lora_weights(str(path), adapter_name="warli")
        for w in (0.4, 0.8, 1.2):
            p = G.generate(STORY(3), seed=3, lora_scale=w, preview=False, run_id=f"e6_{s}_{w}")
            grid.append(ROOT / f"runs/{p['id']}/tile.png")
            out["cells"].append({"steps": s, "strength": w, "run": p["id"], "sdr": sdr(grid[-1])})
    pipe.delete_adapters("warli")
    pipe.load_lora_weights(str(G.WARLI_LORA), adapter_name="warli")
    contact_sheet(grid, FIG / "e6_lora_steps_strength.png", cols=3)
    (RES / "e6.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    todo = sys.argv[1:] or ["e1", "posthoc", "e2", "e6"]
    if "e1" in todo or "e5" in todo:
        e1_e5()
    if "posthoc" in todo:
        e1_posthoc()
    if "e2" in todo:
        e2()
    if "e6" in todo:
        e6()
