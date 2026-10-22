"""SD1.5 (+ Warli LoRA if present) + ControlNet scribble, optional LCM-LoRA, circular padding, TAESD step previews.
Every call writes runs/<id>/ with control.png, tile.png, steps/*.png and params.json."""
import json
import time
import uuid
from pathlib import Path

import torch
from PIL import Image
from diffusers import (AutoencoderTiny, ControlNetModel, DPMSolverMultistepScheduler, LCMScheduler,
                       StableDiffusionControlNetPipeline, StableDiffusionPipeline)

from .compose import LEXICON, compose

ROOT = Path(__file__).parent.parent
RUNS, WARLI_LORA, MANDANA_LORA = ROOT / "runs", ROOT / "models/warli_lora.safetensors", ROOT / "models/mandana_lora.safetensors"
BASE = "stable-diffusion-v1-5/stable-diffusion-v1-5"
CONTROLNET = "lllyasviel/control_v11p_sd15_scribble"  # ponytail: lineart variant not wired; add when scribble falls short
DEVICE = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
DTYPE = torch.float16 if DEVICE == "cuda" else torch.float32
FAST = DEVICE != "cuda"  # CPU/MPS: LCM-LoRA, 6 steps. GPU: 25 steps.
DEFAULTS = dict(steps=6 if FAST else 25, cfg=1.0 if FAST else 7.0, lora_scale=0.8, cn_scale=0.7, circular=True, lcm=FAST)
NEGATIVE = "photo, 3d render, shading, gradient, text, watermark, signature, frame, border, blurry"

_P = {}


def pipes():
    """Lazily load once: ControlNet pipeline, a text-only pipeline sharing its weights, and TAESD."""
    if not _P:
        cn = ControlNetModel.from_pretrained(CONTROLNET, torch_dtype=DTYPE, variant="fp16")
        cp = StableDiffusionControlNetPipeline.from_pretrained(BASE, controlnet=cn, torch_dtype=DTYPE, variant="fp16",
                                                               safety_checker=None, requires_safety_checker=False)
        cp.load_lora_weights("latent-consistency/lcm-lora-sdv1-5", adapter_name="lcm")
        if WARLI_LORA.exists():
            cp.load_lora_weights(str(WARLI_LORA), adapter_name="warli")
        if MANDANA_LORA.exists():  # trained with the same notebook, trigger mandana_style
            cp.load_lora_weights(str(MANDANA_LORA), adapter_name="mandana")
        cp.to(DEVICE).set_progress_bar_config(disable=True)
        tp = StableDiffusionPipeline(**{k: v for k, v in cp.components.items() if k != "controlnet"})
        tp.set_progress_bar_config(disable=True)
        _P.update(cn=cp, text=tp, taesd=AutoencoderTiny.from_pretrained("madebyollin/taesd", torch_dtype=DTYPE).to(DEVICE),
                  sched={"lcm": LCMScheduler.from_config(cp.scheduler.config),
                         "full": DPMSolverMultistepScheduler.from_config(cp.scheduler.config)})
    return _P


def has_lora():
    return "warli" in pipes()["cn"].get_list_adapters().get("unet", [])


def set_circular(flag):
    """padding_mode='circular' on every Conv2d in UNet, VAE, ControlNet (LoRA convs included): the latent wraps."""
    p = pipes()
    for model in (p["cn"].unet, p["cn"].vae, p["cn"].controlnet, p["taesd"]):
        for m in model.modules():
            if isinstance(m, torch.nn.Conv2d):
                m.padding_mode = "circular" if flag else "zeros"


def style_of(ids):
    """The art form most of the symbols belong to."""
    packs = [LEXICON[i]["pack"] for i in ids if i in LEXICON]
    return "mandana" if packs.count("mandana") > len(packs) / 2 else "warli"


def prompt_for(ids):
    names = ", ".join(dict.fromkeys(LEXICON[i]["name"] for i in ids))
    if style_of(ids) == "mandana":
        return f"mandana_style, Mandana floor painting, white lime lines on a red ochre floor, {names}, symmetric geometric folk art, flat"
    return f"warli_style, Warli painting, white chalk line figures painted on a dark red-brown mud wall, {names}, white on red ochre, flat folk art"


def generate(story="harvest", enabled=None, seed=0, mode="full", lora_scale=None, preview=True, run_id=None, **kw):
    """mode='full': composer + ControlNet. mode='text': text prompt naming the same symbols, no control image.
    lora_scale 0 disables the Warli LoRA. Returns params dict (also saved as runs/<id>/params.json)."""
    run = RUNS / (run_id or uuid.uuid4().hex[:10])
    (run / "steps").mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    control, placed = compose(story, set(enabled) if enabled else None, seed)
    control.save(run / "control.png")
    t_compose = time.perf_counter() - t0
    img, info = paint(control if mode == "full" else None, [q["id"] for q in placed], seed, run / "steps" if preview else None,
                      lora_scale=lora_scale, **kw)
    img.save(run / "tile.png")
    info["timing"] = {"compose": t_compose, **info["timing"]}
    params = dict(id=run.name, story=story, mode=mode, **info, placed=placed)
    (run / "params.json").write_text(json.dumps(params, indent=1))
    return params


def paint(control, ids, seed=0, steps_dir=None, lora_scale=None, size=(512, 512), **kw):
    """Diffusion over a control image (white ink on black, sides divisible by 64), or text only when control is None.
    Returns (RGB image, info: prompt, tokens, settings, timing). steps_dir: write TAESD previews there."""
    p, o = pipes(), {**DEFAULTS, **kw}
    o["lora_scale"] = (DEFAULTS["lora_scale"] if lora_scale is None else lora_scale) if has_lora() else 0.0
    pipe, t = p["cn"] if control is not None else p["text"], {}
    names, weights = (["lcm"], [1.0]) if o["lcm"] else ([], [])
    style = style_of(ids)  # the Warli LoRA never paints a Mandana design; a Mandana LoRA does if one is trained
    adapter = style if style in pipe.get_list_adapters().get("unet", []) else None
    if adapter:
        names, weights = names + [adapter], weights + [o["lora_scale"]]
    if names:
        pipe.enable_lora()
        pipe.set_adapters(names, weights)
    else:
        pipe.disable_lora()
    pipe.scheduler = p["sched"]["lcm" if o["lcm"] else "full"]
    set_circular(o["circular"])
    prompt = prompt_for(ids)

    t0 = time.perf_counter()
    with torch.no_grad():
        pe, ne = pipe.encode_prompt(prompt, DEVICE, 1, o["cfg"] > 1, NEGATIVE)
    t["text_encode"] = time.perf_counter() - t0

    step_times, last = [], [time.perf_counter()]

    def on_step(_pipe, i, _t, cb):
        now = time.perf_counter()
        step_times.append(now - last[0])
        if steps_dir:
            with torch.no_grad():
                x = p["taesd"].decode(cb["latents"][-1:]).sample[0].clamp(-1, 1)
            to_pil(x).save(Path(steps_dir) / f"{i:02d}.png")
        last[0] = time.perf_counter()
        return cb

    w, h = control.size if control is not None else size
    args = dict(prompt_embeds=pe, negative_prompt_embeds=ne, num_inference_steps=o["steps"], guidance_scale=o["cfg"], width=w, height=h,
                generator=torch.Generator("cpu").manual_seed(seed), output_type="latent", callback_on_step_end=on_step)
    if control is not None:
        args.update(image=control.convert("RGB"), controlnet_conditioning_scale=o["cn_scale"])
    t0 = time.perf_counter()
    with torch.no_grad():
        latents = pipe(**args).images
    t["denoise"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    with torch.no_grad():
        img = to_pil(pipe.vae.decode(latents / pipe.vae.config.scaling_factor).sample[0].clamp(-1, 1))
    t["vae_decode"] = time.perf_counter() - t0
    info = dict(prompt=prompt, negative_prompt=NEGATIVE if o["cfg"] > 1 else "", tokens=pipe.tokenizer.tokenize(prompt), seed=seed,
                steps=o["steps"], cfg=o["cfg"], lcm=o["lcm"], lora=bool(adapter) and o["lora_scale"] > 0, lora_scale=o["lora_scale"] if adapter else 0.0, style=style, adapter=adapter,
                controlnet=CONTROLNET if control is not None else None, cn_scale=o["cn_scale"] if control is not None else None,
                circular=o["circular"], device=DEVICE, timing={**t, "steps": step_times})
    return img, info


def to_pil(x):
    return Image.fromarray(((x.permute(1, 2, 0).float().cpu().numpy() + 1) * 127.5).round().astype("uint8"))
