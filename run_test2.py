import os
os.environ["FORCE_RANDOM"] = "1"
from agents import execute_cad

params = {"uid": "testuid"}
execute_cad(params)
print("Done")
