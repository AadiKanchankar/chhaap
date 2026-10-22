# Models

- `warli_lora.safetensors`: the Warli style LoRA for Stable Diffusion 1.5 (rank 16, 1500 steps, 45 images, trained on free Colab with train/train_lora_colab.ipynb). The app loads it automatically.
- `train_log.txt`, `train_loss.csv`, `captions.jsonl`: its training record, read by scripts/summarize.py.

Research use only. The training images come from a scraped Kaggle dataset (ajg117/indian-paintings-dataset) with no stated licence, and Warli painting holds a Geographical Indication. This adapter is not a licence to sell work in the Warli style. The training images are not in this repository; rebuild them with scripts/prepare_data.py.
