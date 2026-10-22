# Chhaap

A story-to-product design studio for Warli-inspired prints, running on your own machine with open models. Write a brief, pick a product (wall frame, saree set, diary cover, wallpaper, phone wallpaper, tee), and Chhaap lays the story out, colours it from a designed palette, paints the line work with diffusion, checks that every placed symbol survived, and shows the result on a mockup with a meaning card. Every symbol is known because the layout engine placed it, and every meaning links to a published source.

## Install (one command)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

(`uv venv && uv pip install -r requirements.txt --index-strategy unsafe-best-match` is faster.)

### On a laptop with an NVIDIA GPU

Install the CUDA build of PyTorch first, then the rest (the CPU index in requirements.txt is then skipped for torch):

```bash
python3 -m venv .venv
.venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
.venv/bin/pip install -r requirements.txt
.venv/bin/python -c "import torch; print(torch.cuda.is_available())"   # should print True
```

Nothing else changes. On a GPU the pipeline switches itself to fp16 and 25 full sampling steps, so a hand-painted design takes seconds instead of minutes. The Warli LoRA ships in `models/`. On Windows use `.venv\Scripts\python` in place of `.venv/bin/python`.

## Run (one command)

```bash
.venv/bin/python -m app
```

Open http://localhost:7860: write a brief or click an example, check the plan, press Print design. "Vector only" in Press settings skips diffusion and takes seconds. The first hand-painted design downloads about 3.5 GB of open weights from Hugging Face (SD 1.5, ControlNet scribble, LCM-LoRA, TAESD) and caches them. The study pages live at http://localhost:7860/study (Preference and Annotation for v1 tiles, Designs for the v2 blind comparisons).

## Hardware notes

- NVIDIA GPU (6 GB or more): fp16, 25 steps, about a few seconds per tile.
- CPU or Apple Silicon: LCM-LoRA, 6 steps at 512 px. Measured cost on this project's laptop (Intel Core Ultra 7 155H, 15 GB RAM, no GPU) is in `eval/summary.md` (E5).
- LoRA training needs a GPU. On CPU, run `train/train_lora_colab.ipynb` on a free Colab T4 and unzip its output into `models/`. The app loads `models/warli_lora.safetensors` automatically.
- Memory: the pipeline holds about 7.5 GB once loaded. On a 16 GB machine, restart the app (`fuser -k 7860/tcp`, then start it again) before running the experiment scripts, or the two copies run out of memory.
- Vectorization uses the pip package `potracer` (pure Python), so no system potrace is needed.
- Planner: keyword rules by default. If `ollama` is installed (`ollama pull qwen2.5:3b-instruct`), a local model plans instead. `CHHAAP_PLANNER=claude` uses Claude Code in headless mode; that spends your Claude quota and is off by default.

## Data and experiments

```bash
.venv/bin/python scripts/prepare_data.py   # needs ~/.kaggle/kaggle.json
.venv/bin/python scripts/run_eval.py        # E1, E2, E5, E6 -> eval/results/*.json
.venv/bin/python scripts/run_eval_v2.py     # E7-E10 (v2: survival, layout, vector vs diffusion, planner)
.venv/bin/python scripts/summarize.py       # eval/summary.md (also reads study answers from app.db)
.venv/bin/python tests/test_sdr.py          # seam metric self-test
for m in compose layout palette studio planner meaning vectorize; do .venv/bin/python -m chhaap.$m; done   # module self-checks
```

Training images: Kaggle Indian paintings dataset (ajg117). Licence unclear, scraped; research use only.

Every export is labelled "AI-generated, Warli-inspired. Not a GI-certified Warli painting."
