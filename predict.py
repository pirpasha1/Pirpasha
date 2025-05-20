import glob, os, random, shutil, subprocess
from datetime import datetime
from pathlib import Path as _P

import cv2, numpy as np, torch
from cog import BasePredictor, Input, Path
from huggingface_hub import snapshot_download

MODEL_CACHE = "/src/weights"
REPO_ID     = "Wan-AI/Wan2.1-VACE-14B"
LOCAL_DIR   = f"{MODEL_CACHE}/Wan2.1-VACE-14B"
VACE_CODE   = "/src/VACE-code"                 # cloned in cog.yaml


class Predictor(BasePredictor):
    # --------------------------- set-up ---------------------------
    def setup(self):
        os.makedirs(MODEL_CACHE, exist_ok=True)
        for v in ("HF_HOME","HF_DATASETS_CACHE","HUGGINGFACE_HUB_CACHE","TORCH_HOME"):
            os.environ[v] = MODEL_CACHE
        if not (os.path.isdir(LOCAL_DIR) and os.listdir(LOCAL_DIR)):
            print("▶ Downloading Wan VACE-14B (~66 GB)…")
            snapshot_download(REPO_ID, local_dir=LOCAL_DIR, resume_download=True)
        self.num_gpus = torch.cuda.device_count()

    # -------------------------- predict --------------------------
    def predict(
        self,
        prompt: str       = Input(default=""),
        start_image: Path = Input(),
        end_image:   Path = Input(),
        driver_video: Path = Input(),
        fps:      int  = Input(default=15,  ge=1, le=30),
        steps:    int  = Input(default=25,  ge=10, le=40),
        guidance: float = Input(default=5.0, ge=0,  le=20),
        seed:     int  = Input(default=None),
        size:     str  = Input(default="1280*720", choices=["1280*720","832*480"]),
    ) -> Path:

        work = _P("/tmp") / f"run_{datetime.now():%Y%m%d_%H%M%S}"
        work.mkdir(parents=True, exist_ok=True)

        # ---------- copy user inputs ----------
        s_img, e_img = work/"start.png", work/"end.png"
        d_rgb        = work/"driver.mp4"
        shutil.copyfile(start_image, s_img)
        shutil.copyfile(end_image,   e_img)
        shutil.copyfile(driver_video, d_rgb)

        env = os.environ.copy()
        env["PYTHONPATH"] = f"/src/VACE-code/vace:/src/VACE-code:{env.get('PYTHONPATH','')}"
        pre_dir = work / "pre"; pre_dir.mkdir()

        # ---------- 1. depth pre-process ----------
        subprocess.check_call(
            ["python","-m","vace.vace_preproccess",
             "--task","depth",
             "--video",str(d_rgb),
             "--pre_save_dir",str(pre_dir)],
            env=env, cwd=VACE_CODE)

        depth_vid = pre_dir / "src_video-depth.mp4"   # written above

        # ---------- 3. run Wan-14 B MV2V ----------
        cmd = [
            "python", "-m", "vace.vace_wan_inference",
            "--ckpt_dir", LOCAL_DIR,
            "--model_name", "vace-14B",
            "--size", size,
            "--src_video", str(depth_vid),
            "--src_ref_images", f"{s_img},{e_img}",  # <- new
            "--prompt", prompt,
            "--sample_steps", str(steps),
            "--sample_guide_scale", str(guidance),
            "--base_seed", str(seed or random.randint(0, 2 ** 31 - 1)),
            "--offload_model", "False"  # keep if you really have room
        ]
        subprocess.check_call(cmd, env=env, cwd=VACE_CODE)

        # ---------- 4. fetch result ----------
        runs = sorted(Path(f"{VACE_CODE}/results/vace-14B").glob("*"), key=os.path.getmtime)
        out = runs[-1] / "out_video.mp4"
        final = work / "result.mp4"
        shutil.copyfile(out, final)
        return Path(final)