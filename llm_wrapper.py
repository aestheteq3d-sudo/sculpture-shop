# llm_wrapper.py
"""Utility to lazily load a lightweight open‑source LLM.

The default model is **Phi‑3‑mini‑4k‑instruct** (≈4 B parameters) which runs on
CPU but benefits from a GPU if available. The wrapper exposes a single function:

    generate(prompt: str) -> str

which returns the model's raw textual output. Configuration (model name,
device, temperature, max tokens) lives in ``config.yaml``.
"""

import os
import json
import time
from pathlib import Path

# Load configuration ----------------------------------------------------------
CONFIG_PATH = Path(__file__).with_name("config.yaml")
if CONFIG_PATH.is_file():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        _config = json.load(f)  # simple JSON for ease; YAML could also be used
else:
    # sensible defaults if config missing
    _config = {
        "model_name": "microsoft/Phi-3-mini-4k-instruct",
        "device": "auto",  # "cuda" if torch.cuda.is_available() else "cpu"
        "temperature": 0.8,
        "max_new_tokens": 512,
    }

_model = None

def _load_model():
    global _model
    from transformers import AutoModelForCausalLM, AutoTokenizer
    model_name = _config.get("model_name", "microsoft/Phi-3-mini-4k-instruct")
    device = _config.get("device", "auto")
    # Resolve "auto" to actual device string
    if device == "auto":
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[LLM] Loading model {model_name} onto {device} …")
    start = time.time()
    _model = {
        "tokenizer": AutoTokenizer.from_pretrained(model_name),
        "model": AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype="auto",
            device_map=device,
        ),
        "device": device,
    }
    elapsed = time.time() - start
    print(f"[LLM] Model loaded in {elapsed:.2f}s")

def generate(prompt: str) -> str:
    """Generate text from the configured model.

    Parameters
    ----------
    prompt:
        The user‑visible instruction sent to the LLM.
    Returns
    -------
    str
        Raw model output (string). The caller is responsible for parsing JSON
        or extracting the needed information.
    """
    if _model is None:
        _load_model()
    tokenizer = _model["tokenizer"]
    model = _model["model"]
    inputs = tokenizer(prompt, return_tensors="pt")
    # Move tensors to the correct device
    inputs = {k: v.to(_model["device"]) for k, v in inputs.items()}
    output = model.generate(
        **inputs,
        max_new_tokens=_config.get("max_new_tokens", 512),
        temperature=_config.get("temperature", 0.8),
        do_sample=True,
        top_p=0.95,
        pad_token_id=tokenizer.eos_token_id,
    )
    text = tokenizer.decode(output[0], skip_special_tokens=True)
    return text.strip()
