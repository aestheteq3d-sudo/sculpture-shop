import os, sys, importlib
sys.path.append('c:/Users/asamenwe/Downloads/parametric-lamp-designer')
agents = importlib.import_module('agents')
print('bpy is', agents.bpy)
