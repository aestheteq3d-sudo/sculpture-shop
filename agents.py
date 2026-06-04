# agents.py

"""Agents for the AESTHETEQ3D lamp design pipeline.

This module replaces the previous Google Gemini calls with a lightweight,
open‑source LLM loaded via :pymod:`llm_wrapper`. The functions respect the
environment variable ``FORCE_RANDOM`` to fall back to deterministic random
behaviour for overnight batch runs.
"""

import json
import uuid
import pathlib
# Attempt to import Blender Python API; if unavailable, provide a stub.
try:
    import bpy
except ImportError:  # pragma: no cover
    bpy = None
# If bpy imported but lacks full functionality, disable it
if bpy is not None:
    try:
        _ = bpy.context
    except Exception:
        bpy = None
import os
from config import OUTPUTS_DIR
# lamp_cad will be imported lazily inside execute_cad when bpy is available.
import random
import hashlib
import sys
from llm_wrapper import generate as llm_generate

# ---------------------------------------------------------------------------
# Helper – deterministic random design based on a seed string
# ---------------------------------------------------------------------------
def generate_random_design(seed_str: str) -> dict:
    """Generate deterministic parametric design parameters from a seed.

    The seed string is hashed with SHA‑256 and used to seed Python's ``random``
    module, ensuring reproducibility across runs.
    """
    seed_hash = hashlib.sha256(seed_str.encode("utf-8")).hexdigest()
    seed_int = int(seed_hash[:16], 16)
    random.seed(seed_int)
    params = {
        "saucerRadius": random.uniform(100.0, 250.0),
        "saucerSquash": random.uniform(0.3, 0.8),
        "ribCount": random.randint(12, 36),
        "ribDepth": random.uniform(5.0, 30.0),
        "ribTwist": random.uniform(0.0, 2.0),
        "baseRadius": random.uniform(70.0, 120.0),
        "baseHeight": random.uniform(100.0, 200.0),
        "socketDiameter": random.uniform(35.0, 45.0),
        "pegDiameter": random.uniform(65.0, 85.0),
    }
    return params

# ---------------------------------------------------------------------------
# Conceptualizer – generate a design brief from a vibe string
# ---------------------------------------------------------------------------
def conceptualize_lamp(vibe: str) -> str:
    """Return a vivid textual description of the lamp.

    If ``USE_LLM`` is disabled, the original vibe string is returned unchanged.
    Otherwise the LLM is prompted to elaborate the vibe into a full design
    description.
    """
    if os.getenv("USE_LLM", "1") != "1":
        print("[INFO] USE_LLM disabled – skipping LLM call for Conceptualizer.")
        return vibe
    prompt = (
        f"You are a Master Industrial Designer specializing in 3D‑printed, "
        f"support‑free architectural lighting. Given the following aesthetic "
        f"direction, craft a concise yet vivid design description that includes "
        f"form factor, anchor (base) details, canopy (shade) details, and the "
        f"transition between them. Keep the output under 300 words.\n\n"
        f"Aesthetic direction: {vibe}\n"
    )
    try:
        description = llm_generate(prompt)
        # Ensure safe Unicode output
        safe_desc = description.encode('utf-8', errors='replace').decode('utf-8')
        print("\n=== CONCEPTUAL DESIGN ===\n", safe_desc, "\n==========================\n")
        return safe_desc.strip()
    except Exception as e:
        print("Conceptualizer Agent Error:", e)
        return vibe  # fallback

# ---------------------------------------------------------------------------
# Designer – turn a textual description into numeric CAD parameters
# ---------------------------------------------------------------------------
def design_lamp(prompt: str) -> dict:
    """Return a dictionary of numeric CAD parameters.

    The function asks the LLM to output ONLY a JSON object matching the schema
    required by the CAD script. If the LLM call fails or ``USE_LLM`` is disabled,
    a deterministic random design is returned.
    """
    if os.getenv("USE_LLM", "1") != "1":
        print("[INFO] USE_LLM disabled – skipping LLM call for Designer.")
        return generate_random_design(prompt)
    schema = {
        "saucerRadius": "float (100 to 250)",
        "saucerSquash": "float (0.3 to 0.8)",
        "ribCount": "int (12 to 36)",
        "ribDepth": "float (5.0 to 30.0)",
        "ribTwist": "float (0.0 to 2.0)",
        "baseRadius": "float (70 to 120)",
        "baseHeight": "float (100 to 200)",
        "socketDiameter": "float (35.0 to 45.0)",
        "pegDiameter": "float (65.0 to 85.0)"
    }
    prompt_llm = (
        "You are an Avant‑Garde Lighting Designer translating a textual design "
        "description into concrete CAD parameters. Output ONLY a JSON object that "
        "matches the following schema (keys and descriptions are provided for "
        "reference only). Use values that best fit the description.\n\n"
        f"Description: {prompt}\n"
        f"Schema: {json.dumps(schema, indent=2)}"
    )
    try:
        raw = llm_generate(prompt_llm)
        # Attempt to parse JSON; if fails, fallback
        try:
            params = json.loads(raw)
            print("Designer Agent Output:", params)
            return params
        except Exception as json_err:
            print("Designer JSON parse error:", json_err)
            print("Raw LLM output:", raw)
            return generate_random_design(prompt)
    except Exception as e:
        print("Designer Agent Error:", e)
        return generate_random_design(prompt)

# ---------------------------------------------------------------------------
# Engineer – add mechanical/structural parameters and perform validation cues
# ---------------------------------------------------------------------------
def engineer_validate(prompt: str, designer_params: dict) -> dict:
    """Enhance the designer parameters with engineering values.

    The LLM is asked to supply shell thickness, socket diameter, vent diameter,
    and peg diameter. If the LLM call fails or ``USE_LLM`` is disabled, sensible
    defaults are used.
    """
    if os.getenv("USE_LLM", "1") != "1":
        print("[INFO] USE_LLM disabled – skipping LLM call for Engineer.")
        designer_params.update({
            "shellThickness": 2.6,
            "socketDiameter": 41.0,
            "ventDiameter": 50.0,
            "pegDiameter": 74.0,
        })
        return designer_params
    schema = {
        "shellThickness": "float (1.5 to 4.0)",
        "socketDiameter": "float (35.0 to 45.0)",
        "ventDiameter": "float (40.0 to 70.0)",
        "pegDiameter": "float (65.0 to 85.0)"
    }
    prompt_llm = (
        "You are a Mechanical Engineer for 3D‑printed lighting. Using the user "
        "prompt and the existing designer parameters, propose the best mechanical "
        "values (shell thickness, socket, vent, peg) that satisfy structural "
        "integrity and manufacturability. Output ONLY a JSON object matching the "
        f"following schema: {json.dumps(schema, indent=2)}.\n\n"
        f"User prompt: {prompt}\n"
        f"Designer parameters: {json.dumps(designer_params, indent=2)}"
    )
    try:
        raw = llm_generate(prompt_llm)
        # Attempt JSON parse; fallback on error
        try:
            mech_params = json.loads(raw)
            print("Engineer Agent Output:", mech_params)
            designer_params.update(mech_params)
            return designer_params
        except Exception as json_err:
            print("Engineer JSON parse error:", json_err)
            print("Raw LLM output:", raw)
            # Use deterministic defaults
            designer_params.update({
                "shellThickness": 2.6,
                "socketDiameter": 41.0,
                "ventDiameter": 50.0,
                "pegDiameter": 74.0,
            })
            return designer_params
    except Exception as e:
        print("Engineer Agent Error:", e)
        designer_params.update({
            "shellThickness": 2.6,
            "socketDiameter": 41.0,
            "ventDiameter": 50.0,
            "pegDiameter": 74.0,
        })
        return designer_params

# ---------------------------------------------------------------------------
# Execution – run the Blender CAD script (unchanged)
# ---------------------------------------------------------------------------
def execute_cad(params: dict):
    """Execution Agent: Runs the Blender CAD pipeline.

    This function builds the lamp geometry using ``lamp_cad`` (if Blender Python is
    available), applies a mesh‑fix step, and exports an STL file. When ``bpy`` is
    not present (e.g., during headless testing), the function logs a warning and
    skips the Blender steps.
    """
    OUTPUT_DIR = OUTPUTS_DIR
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if bpy is None:
        # Headless mode – generate a simple geometry using trimesh.
        print("[INFO] bpy not available; generating simple STL with trimesh as fallback.")
        import trimesh
        # Create a basic lamp shape: a cylinder (base) plus a sphere (saucer)
        base_radius = params.get('baseRadius', 80.0)
        base_height = params.get('baseHeight', 150.0)
        saucer_radius = params.get('saucerRadius', 150.0)
        # Cylinder for base
        base = trimesh.creation.cylinder(radius=base_radius, height=base_height)
        # Sphere for saucer positioned on top
        sphere = trimesh.creation.icosphere(subdivisions=2, radius=saucer_radius)
        sphere.apply_translation([0, 0, base_height])
        # Combine meshes
        combined = trimesh.util.concatenate([base, sphere])
        # Export STL
        output_path = OUTPUT_DIR / f"AESTHETEQ_Orbital_Assembly_{params.get('uid', 'unknown')}.stl"
        combined.export(output_path)
        print(f"[INFO] Exported fallback STL to {output_path}")
        return

    # Import lamp_cad lazily now that we know bpy exists.
    import lamp_cad

    # Build geometry using lamp_cad helpers
    lamp_cad.clear_scene()
    base = lamp_cad.create_base(params)
    saucer = lamp_cad.create_saucer(params)
    sculpture = lamp_cad.create_sculpture(params)

    # Join all parts into a single object for fixing
    bpy.ops.object.select_all(action='DESELECT')
    for obj in [base, saucer, sculpture]:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = base
    bpy.ops.object.join()
    combined = bpy.context.active_object

    # Apply mesh‑fix (remesh + solidify)
    fix_mesh(combined)

    # Export to STL (saved to project outputs folder)
    output_path = os.path.join(OUTPUT_DIR, f"AESTHETEQ_Orbital_Assembly_{params.get('uid', 'unknown')}.stl")
    # Ensure STL export addon is enabled
    try:
        bpy.ops.wm.addon_enable(module="io_mesh_stl")
    except Exception as e:
        print("[WARN] Could not enable STL export addon:", e)
    # Try exporting STL, fallback to OBJ if unavailable
    try:
        bpy.ops.export_mesh.stl(filepath=output_path)
        print("Export complete (STL).")
    except Exception as e:
        print("[WARN] STL export failed, falling back to OBJ:", e)
        obj_path = output_path.replace(".stl", ".obj")
        try:
            bpy.ops.export_scene.obj(filepath=obj_path)
            print("Export complete (OBJ).")
        except Exception as e2:
            print("[ERROR] Both STL and OBJ export failed:", e2)
    combined = bpy.context.active_object

    # Apply mesh‑fix (remesh + solidify)
    fix_mesh(combined)

    # Export to STL (saved to project outputs folder)
    output_path = os.path.join(OUTPUT_DIR, f"AESTHETEQ_Orbital_Assembly_{params.get('uid', 'unknown')}.stl")
    # Ensure STL export addon is enabled
    try:
        bpy.ops.wm.addon_enable(module="io_mesh_stl")
    except Exception as e:
        print("[WARN] Could not enable STL export addon:", e)
    # Try exporting STL, fallback to OBJ if unavailable
    try:
        bpy.ops.export_mesh.stl(filepath=output_path)
        print("Export complete (STL).")
    except Exception as e:
        print("[WARN] STL export failed, falling back to OBJ:", e)
        obj_path = output_path.replace(".stl", ".obj")
        try:
            bpy.ops.export_scene.obj(filepath=obj_path)
            print("Export complete (OBJ).")
        except Exception as e2:
            print("[ERROR] Both STL and OBJ export failed:", e2)

def fix_mesh(obj: bpy.types.Object):
    """Apply a remesh (voxel) and a low‑thickness solidify to seal holes.

    This simple pipeline helps close small gaps and makes the mesh watertight.
    """
    # Ensure object is active
    bpy.context.view_layer.objects.active = obj
    # Remesh modifier (voxel = 0.5 mm, block mode gives a clean solid)
    remesh = obj.modifiers.new(name="Remesh", type='REMESH')
    remesh.mode = 'BLOCKS'
    remesh.voxel_size = 0.5
    remesh.use_remove_disconnected = False
    # Apply the remesh
    bpy.ops.object.modifier_apply(modifier=remesh.name)
    # Solidify to add minimal thickness (helps seal remaining holes)
    solid = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid.thickness = 0.5  # increased thickness for better integrity
    solid.use_even_offset = True
    # solid.use_fill_holes = True  # removed: attribute not available in some Blender versions
    bpy.ops.object.modifier_apply(modifier=solid.name)


# ---------------------------------------------------------------------------
# Workflow – orchestrates the pipeline
# ---------------------------------------------------------------------------

def run_workflow(vibe: str) -> dict:
    """Execute the full design workflow for a given vibe string.

    Returns the final CAD parameters dictionary.
    """
    # 1. Conceptualize the lamp description
    description = conceptualize_lamp(vibe)
    # 2. Generate design parameters from description
    designer_params = design_lamp(description)
    # 3. Add engineering parameters and validation
    full_params = engineer_validate(vibe, designer_params)
    # 4. Generate a unique identifier for this design
    full_params['uid'] = uuid.uuid4().hex
    # 5. Run the Blender CAD pipeline and export the model
    execute_cad(full_params)
    return full_params
