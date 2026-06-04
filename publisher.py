# publisher.py
"""Publisher utilities for AESTHETEQ3D.

Generates a single aggregated JSON catalog (catalog.json) that records every
lamp design produced during a batch run. Each entry contains:
- uid
- timestamp
- vibe (design brief)
- all numeric parameters returned by the agents
- QC pass flag and any issues
"""

import os
import json
import datetime
from pathlib import Path

from config import CATALOG_PATH

def _load_catalog() -> list:
    if CATALOG_PATH.is_file():
        try:
            with open(CATALOG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            # Corrupt file – start fresh
            return []
    return []

def _save_catalog(entries: list) -> None:
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

def publish(uid: str, vibe: str, params: dict, passed: bool, issues: list | None = None) -> None:
    """Append a design record to the aggregated JSON catalog.

    Parameters
    ----------
    uid: str
        Unique identifier for the design (derived from Blender export).
    vibe: str
        The design brief used for generation.
    params: dict
        All numeric parameters returned by the LLM agents.
    passed: bool
        Result of the QC check.
    issues: list | None
        Optional list of QC failure reasons.
    """
    entry = {
        "uid": uid,
        "timestamp": datetime.datetime.now().isoformat(),
        "vibe": vibe,
        "parameters": params,
        "qc_pass": passed,
        "issues": issues or [],
    }
    catalog = _load_catalog()
    # Remove any existing entry with same uid to avoid duplicates
    catalog = [e for e in catalog if e.get("uid") != uid]
    catalog.append(entry)
    _save_catalog(catalog)

# Convenience wrapper used by main after a successful QC pass
def record_success(uid: str, vibe: str, params: dict) -> None:
    publish(uid, vibe, params, passed=True)

def record_failure(uid: str, vibe: str, params: dict, issues: list) -> None:
    publish(uid, vibe, params, passed=False, issues=issues)
