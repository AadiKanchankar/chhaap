# STATUS

Defaults: CPU only (Core Ultra 7 155H, 15 GB RAM). N=16 per condition. LCM 6 steps, CFG 1.0, ControlNet 0.7; v2 stylize <= 768 px. Warli LoRA trained on Colab (models/).
Run: `.venv/bin/python -m app` -> localhost:7860 (studio), /study (E3/E4 tabs for v1 tiles, Designs tab for E8/E9 preference).

## Done
- v1: data, lexicon (25 rows), E1-E6; pre-LoRA results in eval/results/pre_lora/
- v2 (TASK2.md): layout engine (4 templates + Mandana rings, border kit, fillers, repeats, jitter), 8 palettes + texture,
  survival check with best-pass rerun + vector repair, 7 products with mockups and 300 DPI export, rules planner (Ollama/Claude optional),
  meaning card present/lost grouped by art form, brief-first UI (impeccable rounds 1-3, finish review fixes, DESIGN.md updated), study Designs tab
- E7, E7 post hoc, E8 (+ no-filler ablation), E9, E10 in eval/summary.md
- Mandana P2: 14-motif sourced lexicon, fusion mode + labels, cleaned data (23 kept, 18 train), mandana_train.zip, notebook STYLE switch
- Paper + synopsis revised for v2; authors 3+2 grid with guide; synopsis on the college template; PDFs and Google Docs (.docx) rebuilt
- Ponytail pass: dead v1 endpoints and chhaap/export.py removed

## Demo
- Pre-rendered examples: Gallery tab in the app, and examples/ (scripts/make_examples.py: 8 vector + 2 hand-painted)

## User to do
- /study: Preference, Annotation (E3/E4) and Designs (E8/E9) tabs; then `.venv/bin/python scripts/summarize.py` and ask for a paper update
- synopsis/MISSING.md: course unit titles, flowchart
- Optional: train the Mandana LoRA on Colab (set STYLE = "mandana", upload mandana_train.zip, unzip output into models/)

## Not run (stated in the paper)
- E3, E4, E8/E9 preferences (no responses); E10 Ollama and Claude backends; Mandana LoRA
