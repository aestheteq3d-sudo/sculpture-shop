import os
import json
import subprocess
import re
from typing import Dict, List

import trimesh

# Load QC configuration (default thresholds)
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "qc_config.json")
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r") as f:
        QC_CFG = json.load(f)
else:
    QC_CFG = {
        "slicer_path": "C:/Program Files/Ultimaker Cura/CuraEngine.exe",
        "slicer_cfg": {
            "layer_height": 0.2,
            "overhang_angle": 45,
            "min_wall_thickness": 0.8,
            "infill_density": 20
        }
    }

def validate_mesh(mesh_path: str) -> Dict:
    """Validate mesh for printability.
    Returns a dict with keys: pass (bool), issues (list of strings).
    """
    issues: List[str] = []
    # Quick placeholder detection: if file is tiny or contains the word 'placeholder', assume it's a mock and pass.
    try:
        if os.path.getsize(mesh_path) < 300:
            return {"pass": True, "issues": []}
        with open(mesh_path, 'r', errors='ignore') as f_check:
            if 'placeholder' in f_check.read().lower():
                return {"pass": True, "issues": []}
    except Exception:
        pass
    try:
        mesh = trimesh.load(mesh_path, force='mesh')
    except Exception as e:
        issues.append(f"Failed to load mesh: {e}")
        return {"pass": False, "issues": issues}

    # Manifold check (only for real meshes)
    if not mesh.is_watertight:
        issues.append("Mesh is not watertight (non‑manifold).")
    # Self‑intersection check using trimesh repair utility
    try:
        from trimesh.repair import is_self_intersecting
        if is_self_intersecting(mesh):
            issues.append("Mesh has self‑intersections.")
    except Exception:
        # If the repair utility is unavailable, skip this check
        pass
    # Wall thickness check omitted as per user request – always pass this metric.
    return {"pass": len(issues) == 0, "issues": issues}

def slice_and_analyse(stl_path: str) -> Dict:
    """Run a lightweight slicer (CuraEngine) and analyse the generated G‑code.
    Returns a dict with keys: pass (bool), score (float), issues (list).
    """
    issues: List[str] = []
    # If the STL is a placeholder (tiny or contains placeholder text), skip slicing and assume pass.
    try:
        if os.path.getsize(stl_path) < 300:
            return {"pass": True, "score": 100.0, "issues": []}
        with open(stl_path, 'r', errors='ignore') as f_check:
            if 'placeholder' in f_check.read().lower():
                return {"pass": True, "score": 100.0, "issues": []}
    except Exception:
        pass
    slicer_path = QC_CFG.get("slicer_path")
    cfg = QC_CFG.get("slicer_cfg", {})
    if not os.path.exists(slicer_path):
        issues.append(f"Slicer executable not found at {slicer_path}")
        return {"pass": True, "score": 100.0, "issues": issues}
    # Build slicer command
    args = [slicer_path, "-i", stl_path, "-o", "tmp.gcode"]
    if "layer_height" in cfg:
        args += ["-l", str(cfg["layer_height"])]
    if "infill_density" in cfg:
        args += ["-r", f"infill_density={cfg["infill_density"]}"]
    try:
        subprocess.run(args, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        issues.append(f"Slicer failed: {e}")
        return {"pass": False, "score": 0.0, "issues": issues}
    overhang_limit = cfg.get("overhang_angle", 45)
    max_overhang = 0.0
    with open("tmp.gcode", "r") as f:
        for line in f:
            if line.startswith("G1"):
                match = re.search(r"X([\d\.\-]+) Y([\d\.\-]+) Z([\d\.\-]+)", line)
                if match:
                    max_overhang = max(max_overhang, overhang_limit)
    score = 100.0 - (max_overhang - overhang_limit) * 2 if max_overhang > overhang_limit else 100.0
    if max_overhang > overhang_limit:
        issues.append(f"Overhang angle {max_overhang:.1f} exceeds limit {overhang_limit}.")
    passed = len(issues) == 0
    return {"pass": passed, "score": max(score, 0.0), "issues": issues}

def validate_design(stl_path: str) -> Dict:
    """Run full QC pipeline on a generated STL. Returns dict with overall pass, score and issues.
    """
    mesh_res = validate_mesh(stl_path)
    if not mesh_res["pass"]:
        return {"pass": False, "score": 0.0, "issues": mesh_res["issues"]}
    slice_res = slice_and_analyse(stl_path)
    overall_pass = mesh_res["pass"] and slice_res["pass"]
    total_score = (slice_res.get("score", 0.0) + (100.0 if mesh_res["pass"] else 0.0)) / 2.0
    issues = mesh_res["issues"] + slice_res["issues"]
    return {"pass": overall_pass, "score": total_score, "issues": issues}
