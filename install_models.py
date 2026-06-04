# install_models.py
"""Utility script to download the selected open‑source LLM model.

The workflow uses the `huggingface_hub` library (already installed) to
fetch the model files into a local `models/` directory. The default
model is **microsoft/Phi-3-mini-4k-instruct**, which works on CPU and can
use a GPU if available.

Run the script with:
    python install_models.py
"""

import os
from pathlib import Path
from huggingface_hub import snapshot_download

# Directory where models are stored (sibling to this script)
MODEL_ROOT = Path(__file__).parent / "models"
MODEL_ROOT.mkdir(parents=True, exist_ok=True)

# Model identifier – can be changed by editing this file
MODEL_NAME = os.getenv("PHI_MODEL", "microsoft/Phi-3-mini-4k-instruct")

def download_model():
    print(f"[install_models] Downloading {MODEL_NAME} …")
    # `snapshot_download` pulls the entire repo (including tokenizer config)
    snapshot_download(repo_id=MODEL_NAME, local_dir=MODEL_ROOT / MODEL_NAME.split('/')[-1],
                      ignore_patterns=["*.bin"],  # keep only necessary files
                      max_workers=4)
    print("[install_models] Download complete.")

if __name__ == "__main__":
    download_model()
