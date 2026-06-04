import argparse
import csv
import datetime
import glob
import os
try:
    import bpy
except ImportError:  # pragma: no cover
    bpy = None
# In a non‑Blender environment the bpy module may import but lack full functionality.
# Detect this and disable it so the fallback trimesh path is used.
if bpy is not None:
import random
    try:
        _ = bpy.context
    except Exception:
        bpy = None
# Ensure console output uses UTF-8 to avoid encoding errors on Windows
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
import time
from dotenv import load_dotenv
from publisher import record_success, record_failure
from data_preprocess import process_stl
from quality_control import validate_design
from agents import run_workflow
from config import NEW_ART_DIR, LOGS_DIR, OUTPUTS_DIR


# By default the pipeline uses open‑source LLMs for all agents.
# The "FORCE_RANDOM" flag is removed; LLM usage is controlled via the CLI flag --use-llm.


def generate_random_concept():
    philosophies = ["Mid-Century Modern", "Bauhaus", "Biomorphic", "Cyberpunk", "Art Deco", "Brutalist", "Parametric Fluidity", "Deconstructivism"]
    shapes = ["a wide, flat saucer", "a tall, twisting spire", "an asymmetrical flowing blob", "a geometric, sharp-angled cage", "a deeply ribbed, organic shell"]
    details = ["with heavy twisting ribs", "featuring smooth, continuous surfaces", "incorporating aggressive structural voids", "with delicate, sweeping fins"]
    concept1 = random.choice(philosophies)
    concept2 = random.choice(philosophies)
    while concept2 == concept1:
        concept2 = random.choice(philosophies)
    shape = random.choice(shapes)
    detail = random.choice(details)
    return f"A hybrid design blending {concept1} and {concept2} philosophies. The core shape should be {shape}, {detail}."

def log_design(uid: str, vibe: str, params: dict):
    """Append a row to a CSV log in the output folder.
    Columns: uid, timestamp, vibe, all param keys.
    """

    timestamp = datetime.datetime.now().isoformat()
    # Ensure the directory exists (NEW_ART_DIR already created on import)
    csv_path = NEW_ART_DIR / "design_log.csv"
    fieldnames = ["uid", "timestamp", "vibe"] + list(params.keys())
    write_header = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        row = {"uid": uid, "timestamp": timestamp, "vibe": vibe}
        row.update(params)
        writer.writerow(row)

def get_latest_uid():
    """Return the uid of the most recent Assembly STL file.
    The filename pattern is AESTHETEQ_Orbital_Assembly_<uid>.stl
    """
    # Use the configured directory for design outputs
    pattern = os.path.join(str(NEW_ART_DIR), "AESTHETEQ_Orbital_Assembly_*.stl")
    files = glob.glob(pattern)
    if not files:
        return None
    latest_file = max(files, key=os.path.getmtime)
    uid = os.path.basename(latest_file).split("_")[-1].replace('.stl', '')
    return uid

def main():
    load_dotenv()
    print("Welcome to the Multi-Agent Parametric Lamp Designer")
    parser = argparse.ArgumentParser(description="Generate a large batch of random lamp designs.")
    parser.add_argument("--batch-size", type=int, default=10, help="Number of designs to generate (default 10)")
    parser.add_argument("--pause-seconds", type=float, default=10.0, help="Seconds to pause between designs (default 10)")
    parser.add_argument("--no-cleanup", action="store_true", help="Do not delete old STL files before starting")
    parser.add_argument("--count", type=int, help="Alias for --batch-size (deprecated)")
    parser.add_argument("--no-llm", action="store_true", help="Force random mode, disable LLMs")
    
    args = parser.parse_args()
    if args.batch_size > 500:
        print("[WARNING] Batch size > 500 may take a very long time and consume large storage.")

    # Set environment flag controlling LLM usage (default enabled)
    os.environ["USE_LLM"] = "0" if args.no_llm else "1"

    # Create a unique sub‑folder for this run
    run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_output_dir = OUTPUTS_DIR / f"run_{run_id}"
    run_output_dir.mkdir(parents=True, exist_ok=True)

    # Logging uses run‑specific file
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"batch_{run_id}.txt"
    with open(log_path, "a") as log_file:
        log_file.write(f"Batch started at {datetime.datetime.now().isoformat()}, size={args.batch_size}, run_id={run_id}\n")

    try:
        if args.count:
            args.batch_size = args.count
        for i in range(args.batch_size):
            vibe = generate_random_concept()
            print(f"\n--- Generating design {i+1}/{args.batch_size} ---")
            print(f"Vibe: {vibe}\n")
            validated_params = run_workflow(vibe)
            uid = validated_params.get('uid')
            if uid:
                assembly_path = run_output_dir / f"AESTHETEQ_Orbital_Assembly_{uid}.stl"
                # Agent writes to OUTPUTS_DIR; move file to run-specific folder if present
                default_path = OUTPUTS_DIR / f"AESTHETEQ_Orbital_Assembly_{uid}.stl"
                if default_path.exists():
                    default_path.rename(assembly_path)
                
                if assembly_path.exists():
                    qc_res = validate_design(assembly_path)
                    if qc_res["pass"]:
                        # Log design using global NEW_ART_DIR (unchanged) – keep original signature
                        log_design(uid, vibe, validated_params)
                        record_success(uid, vibe, validated_params)
                        with open(log_path, "a") as log_file:
                            log_file.write(f"[PASS] UID {uid}\n")
                    else:
                        safe_issues = ', '.join(qc_res['issues']).replace('\u2011', '-')
                        print(f"[QC FAIL] UID {uid}: {safe_issues}")
                        record_failure(uid, vibe, validated_params, qc_res['issues'])
                        with open(log_path, "a") as log_file:
                            log_file.write(f"[FAIL] UID {uid}: {safe_issues}\n")
                else:
                    print(f"[WARNING] STL file not found for UID {uid}.")
                    with open(log_path, "a") as log_file:
                        log_file.write(f"[WARN] STL file missing for UID {uid}.\n")
            else:
                print("[WARNING] UID not captured for logging.")
                with open(log_path, "a") as log_file:
                    log_file.write("[WARN] UID not captured for logging.\n")
            time.sleep(args.pause_seconds)
    except KeyboardInterrupt:
        print("\nBatch interrupted by user.")
    finally:
        with open(log_path, "a") as log_file:
            log_file.write(f"Batch ended at {datetime.datetime.now().isoformat()}\n\n")
    print(f"All {args.batch_size} designs completed. Files are in {run_output_dir}.")

if __name__ == "__main__":
    main()
