import os
from pathlib import Path

# Base directory for all outputs, logs, and design artifacts.
# Users can set the environment variable NEW_ART_DIR to choose a custom location.
# Default mirrors previous behaviour: Desktop/New art.
NEW_ART_DIR = Path(os.getenv("NEW_ART_DIR", Path("/content/drive/MyDrive/AESTHETEQ3D_Cloud/New art/outputs/")))

# Ensure the directory exists when imported.
NEW_ART_DIR.mkdir(parents=True, exist_ok=True)

# Subfolders
OUTPUTS_DIR = NEW_ART_DIR / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR = NEW_ART_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
CATALOG_PATH = LOGS_DIR / "catalog.json"

# Environment variable to control forced random mode.
FORCE_RANDOM = os.getenv("FORCE_RANDOM", "0") == "1"
