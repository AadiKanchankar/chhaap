"""Builds eval/summary.md from eval/results/*.json and app.db (E3, E4). Never edit summary.md by hand."""
import collections
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent.parent
RES = ROOT / "eval/results"
DESC = {"a": "base, text only", "b": "base + circular", "c": "LoRA", "d": "LoRA + circular",
        "e": "composer + ControlNet + LoRA + circular"}
f3 = lambda x: f"{x:.3f}"
pm = lambda s: f"{s['mean']:.3f} ± {s['std']:.3f}"


def load(name):
    p = RES / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else {"status": "not run"}


def e3_e4():
    db = ROOT / "app.db"
    out = {"e3": {"status": "not run: no annotations"}, "e4": {"status": "not run: no responses"}}
    if not db.exists():
        return out
    con = sqlite3.connect(db)
    # an answer counts only if given after its image was last generated (E1 was rerun once the LoRA arrived)
    made = lambda run: (ROOT / "runs" / run / "tile.png").stat().st_mtime if (ROOT / "runs" / run / "tile.png").exists() else float("inf")
    latest = {}  # last answer per (run, symbol): early UI builds could save one form several times
    for run, cond, sym, present, ts in con.execute("SELECT run_id, cond, symbol, present, ts FROM annotations ORDER BY ts"):
        if ts > made(run):
            latest[run, sym] = (cond, present)
    ann = collections.defaultdict(lambda: {"runs": set(), "n": 0, "p": 0})
    for (run, _), (cond, present) in latest.items():
        ann[cond]["runs"].add(run); ann[cond]["n"] += 1; ann[cond]["p"] += present
    if ann:
        out["e3"] = {c: {"images": len(a["runs"]), "judgements": a["n"], "present": a["p"], "fraction_present": a["p"] / a["n"]} for c, a in sorted(ann.items())}
    v = [(c, a) for c, a, ar, er, ts in con.execute("SELECT choice, choice_after_card, a_run, e_run, ts FROM votes") if ts > max(made(ar), made(er))]
    if v:
        n = len(v)
        e_before = sum(c == "e" for c, _ in v)
        e_after = sum(a == "e" for _, a in v if a)
        n_after = sum(1 for _, a in v if a)
        out["e4"] = {"n": n, "pilot": n < 10, "e_wins_before_card": e_before, "win_rate_e_vs_a": e_before / n,
                     "n_after_card": n_after, "e_wins_after_card": e_after,
                     "win_rate_e_after_card": e_after / n_after if n_after else None,
                     "changed_answer": sum(1 for c, a in v if a and a != c)}
    (RES / "e3.json").write_text(json.dumps(out["e3"], indent=1))
    (RES / "e4.json").write_text(json.dumps(out["e4"], indent=1))
    return out


def v2_prefs():
    """E8/E9 blind preferences from the v2 study tab (table prefs2), as pilot counts."""
    db = ROOT / "app.db"
    out = {}
    if db.exists():
        con = sqlite3.connect(db)
        if con.execute("SELECT name FROM sqlite_master WHERE name='prefs2'").fetchone():
            for kind, n, wins in con.execute("SELECT kind, COUNT(*), SUM(choice = treat) FROM prefs2 GROUP BY kind"):
                out[kind] = {"n": n, "treatment_wins": int(wins), "win_rate": wins / n, "pilot": n < 10}
    (RES / "prefs_v2.json").write_text(json.dumps(out or {"status": "not run: no responses"}, indent=1))
    return out


def v2_sections():
    L = []
    e7, e8, e9, e10, pr = load("e7"), load("e8"), load("e9"), load("e10"), v2_prefs()
    L += ["## E7 symbol survival", ""]
    if "per_symbol" in e7:
        L += [f"{e7['n_runs']} stylized runs ({e7['page']}, {e7['density']} density), {e7['n_elements']} placed symbols. Keep rule: {e7['keep_rule']}.", "",
              "| Symbol | n | Primitives | Ink share | Survival, first pass | Survival, final |", "|---|---|---|---|---|---|"]
        rows = sorted(e7["per_symbol"].items(), key=lambda kv: kv[1]["survival_first_pass"])
        L += [f"| {k} | {v['n']} | {v['primitives']} | {f3(v['ink_share'])} | {f3(v['survival_first_pass'])} | {f3(v['survival_final'])} |" for k, v in rows]
        sp, sa = e7["spearman_primitives_vs_survival"], e7["spearman_ink_share_vs_survival"]
        L += ["", "By role, first pass: " + "; ".join(f"{r} {f3(v['survival_first_pass'])} (n = {v['n']})" for r, v in e7["per_role"].items()) + ".",
              "By template, first pass: " + "; ".join(f"{t} {f3(v['survival_first_pass'])}" for t, v in e7["per_template"].items()) + ".",
              f"Spearman, primitives against first-pass survival over {sp['n_symbols']} symbols with n >= 3: rho = {f3(sp['rho'])}, p = {sp['p_value']:.4f}. "
              f"Ink share against survival: rho = {f3(sa['rho'])}, p = {sa['p_value']:.4f}.",
              "Final paths: " + "; ".join(f"{k} {v}" for k, v in e7["paths"].items()) + ". Runs by number of reruns: " +
              "; ".join(f"{k} reruns: {v}" for k, v in e7["runs_by_reruns"].items()) + ".", "Figure: eval/figures/e7_survival.png", ""]
        ph = load("e7_posthoc")
        if "rotated" in ph:
            L += ["### E7 post-hoc (defined after inspecting E7)", "",
                  f"Hero and support symbols, n = {ph['n']}. Size is composition ink pixels in the element box at stylize scale (quartile edges "
                  + ", ".join(f"{v:.0f}" for v in ph["quartile_edges_ink_px"]) + "). First-pass survival by size quartile: "
                  + "; ".join(f"Q{q['quartile']} {f3(q['survival_first_pass'])} (n = {q['n']})" for q in ph["survival_by_size_quartile"])
                  + f". Spearman, size against survival: rho = {f3(ph['spearman_ink_px_vs_survival']['rho'])}, p = {ph['spearman_ink_px_vs_survival']['p_value']:.4f}. "
                  f"Median size: survived {ph['median_ink_px']['survived']:.0f}, lost {ph['median_ink_px']['lost']:.0f} (Mann-Whitney p = {ph['mann_whitney']['p_value']:.4f}).",
                  f"Rotated symbols (ring dancers): first-pass survival {f3(ph['rotated']['survival_first_pass'])} (n = {ph['rotated']['n']}); upright: "
                  f"{f3(ph['upright']['survival_first_pass'])} (n = {ph['upright']['n']}). Fisher exact: odds ratio = {f3(ph['fisher_rotated_vs_upright']['odds_ratio'])}, "
                  f"p = {ph['fisher_rotated_vs_upright']['p_value']:.2e} ({'{:.2e}'.format(ph['fisher_rotated_vs_upright']['p_value']).replace('e-', ' x 10^-')}). Rotation is confounded with crowding: the rotated symbols are the touching dancers of the tarpa rings.", ""]
    else:
        L += [e7["status"], ""]
    L += ["## E8 structured layout against random scatter", ""]
    if "conditions" in e8:
        L += [f"{e8['n_seeds']} seeds per condition, same story symbols. Evenness: coefficient of variation of ink coverage over a {e8['grid']} (lower is more even).", "",
              "| Layout | CV (mean ± std) | CV without fillers | Overlapping symbol pairs (mean ± std) | Ink coverage (mean) | Wilcoxon CV against scatter | Same, without fillers |", "|---|---|---|---|---|---|---|"]
        for t, v in e8["conditions"].items():
            w, wn = v.get("wilcoxon_cv_vs_scatter"), v.get("wilcoxon_cv_no_fillers_vs_scatter")
            W = lambda x: f"W = {x['statistic']:.1f}, p = {x['p_value']:.4f}" if x else ""
            L.append(f"| {t} | {pm(v['cv'])} | {pm(v['cv_no_fillers'])} | {pm(v['overlaps'])} | {f3(v['coverage']['mean'])} | {W(w)} | {W(wn)} |")
        p8 = pr.get("e8")
        L += ["", f"Blind preference (study pages): {'pilot, ' if p8 and p8['pilot'] else ''}" + (f"n = {p8['n']}, structured layout preferred in {p8['treatment_wins']}." if p8 else "not run: no responses."), ""]
    else:
        L += [e8["status"], ""]
    L += ["## E9 vector only against diffusion", ""]
    if "survival_main" in e9:
        sm, sa, sec = e9["survival_main"], e9["survival_all"], e9["seconds"]
        L += [f"{e9['note']}.", "", "| Condition | Survival, hero and support | Survival, all symbols | Seconds per design (mean ± std) |", "|---|---|---|---|",
              f"| vector only | {f3(sm['vector_only'])} | {f3(sa['vector_only'])} | {pm(sec['vector_only'])} |",
              f"| stylized | {f3(sm['stylized'])} | {f3(sa['stylized'])} | {pm(sec['stylized'])} |",
              f"| stylized + repair | {f3(sm['stylized_repaired'])} | {f3(sa['stylized_repaired'])} | {pm(sec['stylized_repaired'])} |", "",
              f"Hero and support symbols: n = {sm['n']}; all symbols: n = {sa['n']}. Lost on the first pass: hero and support {f3(1 - sm['stylized'])}, "
              f"all symbols {f3(1 - sa['stylized'])}. Repair paths for hero and support: " + "; ".join(f"{k} {v}" for k, v in e9["repair_paths_main"].items()) + "."]
        p9 = pr.get("e9")
        L += [f"Blind preference (study pages): {'pilot, ' if p9 and p9['pilot'] else ''}" + (f"n = {p9['n']}, stylized + repair preferred in {p9['treatment_wins']}." if p9 else "not run: no responses."), ""]
    else:
        L += [e9["status"], ""]
    L += ["## E10 planner faithfulness", ""]
    if "backends" in e10:
        L += [f"{e10['n_briefs']} fixed briefs. {e10['note']}.", "", "| Backend | Schema valid | Constraints | Satisfied | By type | Seconds (mean) |", "|---|---|---|---|---|---|"]
        for b, v in e10["backends"].items():
            L.append(f"| {b} | {f3(v['schema_valid'])} | {v['constraints']} | {f3(v['satisfied'])} | " + "; ".join(f"{k} {f3(x['satisfied'])} of {x['n']}" for k, x in v["by_type"].items())
                     + f" | {v['seconds']['mean']:.4f} |" if "satisfied" in v else f"| {b} | {v['status']} | | | | |")
        L.append("")
    else:
        L += [e10["status"], ""]
    return L


def main():
    hs = e3_e4()
    e1, e2, e5, e6 = load("e1"), load("e2"), load("e5"), load("e6")
    L = ["# Evaluation summary", "", "Generated by scripts/summarize.py from eval/results/*.json and app.db. Do not edit.", ""]

    import csv
    from collections import Counter
    rows = list(csv.DictReader(open(ROOT / "data/manifest.csv")))
    by_class = Counter(r["class"] for r in rows if r["kept"] == "yes")
    w = [r for r in rows if r["class"] == "warli"]
    drops = Counter(r["drop_reason"].split(":")[0] for r in w if r["kept"] == "no")
    split = Counter(r["split"] for r in w if r["kept"] == "yes")
    data = {"images_per_class": dict(by_class), "total_images": sum(by_class.values()), "warli_readable": len(w),
            "warli_kept": split["train"] + split["heldout"], "warli_train": split["train"], "warli_heldout": split["heldout"],
            "warli_drops": dict(drops), "lexicon_rows": sum(1 for _ in csv.DictReader(open(ROOT / "data/lexicon.csv")))}
    (RES / "data.json").write_text(json.dumps(data, indent=1))
    L += ["## Data", "", f"Kept images per class (Warli after cleaning; the CLIP probe trains on these minus the held-out Warli): " +
          ", ".join(f"{k} {v}" for k, v in sorted(by_class.items())) + f"; total {data['total_images']}.",
          f"Warli: {len(w)} readable, {data['warli_kept']} kept, {data['warli_train']} train, {data['warli_heldout']} held out. "
          "Drops: " + "; ".join(f"{k} {v}" for k, v in drops.items()) + f". Lexicon rows: {data['lexicon_rows']}.", ""]

    log, loss = ROOT / "models/train_log.txt", ROOT / "models/train_loss.csv"
    if log.exists() and loss.exists():  # LoRA trained on free Colab (train/train_lora_colab.ipynb); the zip carries these logs
        import re
        txt, ls = log.read_text(errors="ignore"), [float(r["loss"]) for r in csv.DictReader(open(loss))]
        grab = lambda k: int(re.search(rf"{k} = (\d+)", txt).group(1))
        mm, ss = re.findall(r"\d+/\d+ \[(\d+):(\d+)<", txt)[-1]
        lt = {"examples": grab("Num examples"), "epochs": grab("Num Epochs"), "batch_size": grab("Instantaneous batch size per device"),
              "steps": len(ls), "train_minutes": int(mm) + int(ss) / 60, "mixed_precision": "fp16" if "Mixed precision type: fp16" in txt else "no",
              "loss_mean_first_100": sum(ls[:100]) / 100, "loss_mean_last_100": sum(ls[-100:]) / 100}
        (RES / "lora_train.json").write_text(json.dumps(lt, indent=1))
        L += ["## LoRA training (free Colab GPU)", "",
              f"{lt['examples']} images, batch {lt['batch_size']}, {lt['steps']} steps ({lt['epochs']} epochs), {lt['mixed_precision']}, "
              f"{lt['train_minutes']:.1f} minutes. Mean step loss: first 100 steps {f3(lt['loss_mean_first_100'])}, last 100 steps {f3(lt['loss_mean_last_100'])} "
              "(per-step diffusion loss depends on the sampled timestep, so it is not a convergence measure).", ""]

    L += ["## E1 tiling ablation", ""]
    if "conditions" in e1:
        L += [f"Device: {e1['device']}. Seeds: {len(e1['seeds'])} per condition. {e1.get('note_e', '')}.", "",
              "| Condition | Description | n | SDR (mean ± std) | Wrap error (mean ± std) |", "|---|---|---|---|---|"]
        for c, r in e1["conditions"].items():
            desc = DESC[c] if r.get("lora", True) or c != "e" else "composer + ControlNet + circular (no LoRA)"
            L.append(f"| {c} | {desc} | {r['sdr']['n']} | {pm(r['sdr'])} | {pm(r['wrap_error'])} |" if "sdr" in r
                     else f"| {c} | {DESC[c]} | 0 | {r['status']} | |")
        w = e1.get("wilcoxon_e_vs_a", {})
        L += ["", "Wilcoxon signed-rank, e against a (paired by seed): " +
              "; ".join(f"{m}: W = {f3(x['statistic'])}, p = {x['p_value']:.2e}" for m, x in w.items()), ""]
    else:
        L += [e1["status"], ""]

    ph = load("e1_posthoc")
    if "conditions" in ph:
        L += ["### E1 post-hoc (defined after inspecting E1)", "",
              "SDR is two-sided: a framed tile puts a flat border on the seam and scores well below 1. Each tile is summarised by |log SDR| (0 = seamless), "
              "with the planned 8 interior lines and with 64 lines.", "",
              "| Condition | n | abs log SDR, 8 lines | abs log SDR, 64 lines | SDR, 64 lines | Tiles with 0.8 < SDR < 1.25 |", "|---|---|---|---|---|---|"]
        L += [f"| {c} | {r['abs_log_sdr']['n']} | {pm(r['abs_log_sdr'])} | {pm(r['abs_log_sdr64'])} | {pm(r['sdr64'])} | {r['within_0.8_1.25']} of {r['abs_log_sdr']['n']} |"
              for c, r in ph["conditions"].items()]
        ci = ph["control_images"]
        L += [f"| control images of e (seamless by construction) | {ci['abs_log_sdr']['n']} | {pm(ci['abs_log_sdr'])} | {pm(ci['abs_log_sdr64'])} | | |", "",
              "Wilcoxon signed-rank on abs log SDR, paired by seed: " + "; ".join(
                  f"{k.replace('wilcoxon_', '').replace('_vs_', ' vs ')}: W = {v['statistic']:.1f}, p = {v['p_value']:.4f}"
                  for k, v in ph.items() if k.startswith("wilcoxon")), ""]

    L += ["## E2 style fidelity", ""]
    if "conditions" in e2:
        p = e2["probe"]
        L += [f"CLIP linear probe (openai/clip-vit-base-patch32, logistic regression, {len(p['classes'])} classes): "
              f"test accuracy {f3(p['test_accuracy'])} on {p['n_test']} images ({p['n_train']} train). Held-out Warli images: {e2['heldout_n']}. "
              f"Probe Warli probability on held-out Warli: {pm(e2['reference_warli_prob_heldout'])}.", "",
              "| Condition | KID (mean ± std) | Warli probability (mean ± std) |", "|---|---|---|"]
        for c, r in e2["conditions"].items():
            L.append(f"| {c} | {f3(r['kid_mean'])} ± {f3(r['kid_std'])} | {pm(r['warli_prob'])} |" if "kid_mean" in r else f"| {c} | {r['status']} | |")
        L.append("")
    else:
        L += [e2["status"], ""]

    L += ["## E3 symbol grounding", ""]
    if "a" in hs["e3"] or "e" in hs["e3"]:
        L += ["| Condition | Images | Judgements | Present | Fraction present |", "|---|---|---|---|---|"]
        L += [f"| {c} | {r['images']} | {r['judgements']} | {r['present']} | {f3(r['fraction_present'])} |" for c, r in hs["e3"].items()]
        L.append("")
    else:
        L += [hs["e3"]["status"], ""]

    L += ["## E4 preference pilot", ""]
    r = hs["e4"]
    if "n" in r:
        L += [f"{'Pilot, ' if r['pilot'] else ''}n = {r['n']}. e preferred over a in {r['e_wins_before_card']} of {r['n']} "
              f"(win rate {f3(r['win_rate_e_vs_a'])}). After reading the meaning card: e preferred in {r['e_wins_after_card']} of "
              f"{r['n_after_card']}" + (f" (win rate {f3(r['win_rate_e_after_card'])})" if r["n_after_card"] else "") +
              f"; {r['changed_answer']} answers changed.", ""]
    else:
        L += [r["status"], ""]

    L += ["## E5 cost", ""]
    if "conditions" in e5:
        L += [f"Device: {e5['device']}.", "", "| Condition | Seconds per image (mean ± std) | Denoise seconds (mean ± std) | Peak RSS (MB) |", "|---|---|---|---|"]
        L += [f"| {c} | {pm(x['seconds_per_image'])} | {pm(x['denoise_seconds'])} | {x['peak_rss_mb']:.0f} |" for c, x in e5["conditions"].items()]
        L.append("")
    else:
        L += [e5["status"], ""]

    L += ["## E6 LoRA steps and strength", ""]
    if "cells" in e6:
        L += ["| Steps | Strength | SDR |", "|---|---|---|"] + [f"| {c['steps']} | {c['strength']} | {f3(c['sdr'])} |" for c in e6["cells"]] + ["", "Figure: eval/figures/e6_lora_steps_strength.png", ""]
    else:
        L += [e6["status"], ""]

    L += v2_sections()
    (ROOT / "eval/summary.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
