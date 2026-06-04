import os
os.environ["FORCE_RANDOM"] = "1"
from agents import run_workflow

# Run a single workflow with a simple vibe string
params = run_workflow("minimalist table lamp")
print("Workflow completed, params uid:", params.get('uid'))
