# NSFW-API / **Wan-VACE**

Smooth, motion-driven text-to-video generation with **Wan 2.1‑VACE** — wrapped in a single Python/Cog predictor that supports **First → Last frame guidance** out‑of‑the‑box.

---

## ✨ Features

| What                                  | Details                                                                                                                                           |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **14 B & 1.3 B checkpoints**          | Auto‑downloads from 🤗 *Wan‑AI/Wan2.1‑VACE‑14B* (≈ 66 GB) or *‑1.3B* when you pick the lower‑res option.                                          |
| **First‑Last Frame‑to‑Video (FLF2V)** | Supply a start & end still (or two clips) plus a motion driver (depth / pose). Wan‑VACE morphs the visuals while following the driver’s movement. |
| **Cog predictor / REST API**          | Drop into any Cog‑based infra (Replicate, Banana, custom docker) or import the `Predictor` class directly.                                        |
| **Fully offline weights cache**       | `MODEL_CACHE=/src/weights` keeps T5 / VAE / diffusion shards and avoids re‑pulling.                                                               |
| **Single‑config run**                 | One YAML (`cog.yaml`) pins all system deps. No hand hacking of the original VACE repo.                                                            |

---

## 🖥️ Quick Start

> **Hardware:** A single A100 80 GB runs 1280×720 at 25 steps. Two 40 GB cards or the 1.3 B model (480 p) for smaller GPUs.

```bash
git clone https://github.com/NSFW-API/Wan-VACE.git
cd Wan-VACE

# 1. Build once
docker build -t wan-vace .

# 2. Run (Cog)
cog predict \
  -i prompt="A woman grips her top with her hands and lifts it up, revealing her breasts" \
  -i start_image=@start.png \
  -i end_image=@end.png \
  -i driver_video=@motion.mp4 \
  -i fps=15 -i steps=25 -i guidance=5.0 -i size="1280*720" \
  -o result.mp4
```

The **first frame** of the output will match **`start.png`**, the **last frame** will match **`end.png`**, and every frame in between follows the motion in **`motion.mp4`** (depth controlled).

---

## 📂 Repo Layout

```
Wan-VACE/
├─ cog.yaml               # image spec (Ubuntu 22.04 + CUDA 12.2 + PyTorch 2.2)
├─ predict.py             # this repo’s star — the Cog Predictor
├─ /src
│   ├─ VACE-code/         # clean clone of Alibaba's VACE (added as git submodule)
│   └─ weights/           # auto-populated HF cache
└─ docs/
    └─ teaser.gif         # example output
```

---

## 🔧 How it Works Internally

| Step                      | Script call                                              | Output                             |
| ------------------------- | -------------------------------------------------------- | ---------------------------------- |
| **Depth preprocess**      | `vace_preproccess --task depth`                          | `src_video-depth.mp4`              |
| **First/Last ref expand** | `vace_preproccess --task frameref --mode firstlastframe` | `src_ref_images-frameref.txt`      |
| **Inference**             | `vace_wan_inference.py`                                  | `results/vace-14B/…/out_video.mp4` |

`predict.py` wires these together, sets all Hugging Face env vars to `/src/weights`, chooses model size based on the `size=` flag, and moves the final video to `/tmp/run_…/result.mp4` for Cog to return.

---

## ⚙️ Parameters

| CLI / Cog flag             | Range                   | Meaning                                                      |
| -------------------------- | ----------------------- | ------------------------------------------------------------ |
| `prompt`                   | text                    | Scene description (Chinese phrases boost fidelity).          |
| `start_image`, `end_image` | PNG/JPG                 | First & last reference frames (same resolution recommended). |
| `driver_video`             | MP4                     | Motion clip *or* depth/pose video already.                   |
| `fps`                      | 1 – 30                  | Output frame rate.                                           |
| `steps`                    | 10 – 40                 | Diffusion steps (quality ↑ but time ↑).                      |
| `guidance`                 | 0 – 20                  | Classifier‑free guidance scale.                              |
| `size`                     | `1280*720` \| `832*480` | Selects 14 B (HD) or 1.3 B (SD) checkpoint automatically.    |

---

## 🩹 Troubleshooting

| Symptom                                                 | Fix                                                                                                                                   |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `Warning: failed to importing 'ltx'`                    | Optional; silence with `pip install "ltx-video@git+https://github.com/Lightricks/LTX-Video@ltx-video-0.9.1" sentencepiece --no-deps`. |
| CUDA OOM at 720 p                                       | Use `size="832*480"` or split across 2×40 GB with FSDP (`ulysses_size = 8`).                                                          |

---

## 📜 Licenses & Credits

* **Wan 2.1 VACE** © 2024 Alibaba DAMO / Wan‑AI – Apache 2.0 license on Hugging Face.
* This wrapper (predictor, Docker spec, docs) © 2025 **The NSFW Company, LLC** – MIT license.
* The project is **research / adult‑only**. Check local regulations before deploying any NSFW model.

---

## 🌱 Roadmap

* DreamBooth‑style LoRA finetune slot
* ComfyUI node pack
* API v2 with async job queue & webhook callbacks

---

> Have fun generating buttery‑smooth FLF videos!
> Questions / PRs welcome in the **Issues** tab or on our Discord.
