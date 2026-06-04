import bpy
import bmesh
import math

# ==========================================
# 0. NUKE THE SCENE
# ==========================================
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# ==========================================
# 1. GENERATE THE MINIMAL CONE BASE (X = -120)
# ==========================================
# Steep architectural cone matching the blueprint
bpy.ops.mesh.primitive_cone_add(vertices=128, radius1=95, radius2=37, depth=140, location=(-120, 0, 70))
base = bpy.context.active_object
base.name = "AESTHETEQ_Orbital_Base"
bpy.ops.object.shade_smooth()

# The Universal 74mm Male Peg
bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=37.0, depth=15, location=(-120, 0, 147.5))
base_peg = bpy.context.active_object
base_peg.hide_render = True

# Internal E26 Hardware Core
bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=20.5, depth=200, location=(-120, 0, 70))
thread_tunnel = bpy.context.active_object
thread_tunnel.display_type = 'WIRE'
thread_tunnel.hide_render = True

bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=30, depth=85, location=(-120, 0, 42.5))
wiring_cavity = bpy.context.active_object
wiring_cavity.display_type = 'WIRE'
wiring_cavity.hide_render = True

# Diamond Cord Channel (Slicer-safe)
bpy.ops.mesh.primitive_cube_add(size=1, location=(-120, -60, 5))
cord_channel = bpy.context.active_object
cord_channel.scale = (10, 150, 10)
cord_channel.rotation_euler = (0, math.radians(45), 0)
bpy.ops.object.transform_apply(scale=True, rotation=True)
cord_channel.display_type = 'WIRE'
cord_channel.hide_render = True

# Apply Base Booleans
base.modifiers.new("Peg", 'BOOLEAN').object = base_peg
base.modifiers["Peg"].operation = 'UNION'
base.modifiers["Peg"].solver = 'EXACT'

base.modifiers.new("CutTunnel", 'BOOLEAN').object = thread_tunnel
base.modifiers["CutTunnel"].operation = 'DIFFERENCE'
base.modifiers["CutTunnel"].solver = 'EXACT'

base.modifiers.new("CutCavity", 'BOOLEAN').object = wiring_cavity
base.modifiers["CutCavity"].operation = 'DIFFERENCE'
base.modifiers["CutCavity"].solver = 'EXACT'

base.modifiers.new("CutCord", 'BOOLEAN').object = cord_channel
base.modifiers["CutCord"].operation = 'DIFFERENCE'
base.modifiers["CutCord"].solver = 'EXACT'

# ==========================================
# 2. GENERATE THE MCM SAUCER SHADE (X = 120)
# ==========================================
bpy.ops.mesh.primitive_uv_sphere_add(segments=256, ring_count=128, radius=150, location=(120, 0, 80))
shade = bpy.context.active_object
shade.name = "AESTHETEQ_Orbital_Saucer"

bm = bmesh.new()
bm.from_mesh(shade.data)

for v in bm.verts:
    # Squash the sphere into the classic MCM Saucer profile
    v.co.z *= 0.5 
    
    xy_dist = math.sqrt(v.co.x**2 + v.co.y**2)
    if xy_dist < 0.1: continue

    angle = math.atan2(v.co.y, v.co.x)

    # Parametric Helix Math (Creates the sweeping ribs)
    z_norm = (v.co.z + 75) / 150.0 
    twist = z_norm * math.pi * 1.5 # 270-degree sweeping rotation

    # 18 deep, continuous ribs
    rib_depth = 14.0
    r_mult = 1.0 + (math.sin((angle * 18) + twist) * (rib_depth / 150.0))

    v.co.x *= r_mult
    v.co.y *= r_mult

bm.to_mesh(shade.data)
bm.free()
bpy.ops.object.shade_smooth()

# DFM Engineering: Volumetric Shell
# Using Solidify ensures the complex twisting ribs maintain exactly 2.6mm thickness
shade.modifiers.new(name="Thicken", type='SOLIDIFY').thickness = 2.6
shade.modifiers["Thicken"].offset = 0

# Base Chopper (Ensures Z=0 is flat)
bpy.ops.mesh.primitive_cube_add(size=1, location=(120, 0, -100))
shade_chopper = bpy.context.active_object
shade_chopper.scale = (400, 400, 200)
bpy.ops.object.transform_apply(scale=True)
shade_chopper.display_type = 'WIRE'
shade_chopper.hide_render = True

# 75mm Wide-Mouth Female Cavity
bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=37.5, depth=16, location=(120, 0, 8))
shade_recess = bpy.context.active_object
shade_recess.display_type = 'WIRE'
shade_recess.hide_render = True

# 50mm Thermal Exhaust
bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=25, depth=100, location=(120, 0, 150))
top_vent = bpy.context.active_object
top_vent.display_type = 'WIRE'
top_vent.hide_render = True

# Apply Shade Booleans
shade.modifiers.new("Chop", 'BOOLEAN').object = shade_chopper
shade.modifiers["Chop"].operation = 'DIFFERENCE'
shade.modifiers["Chop"].solver = 'EXACT'

shade.modifiers.new("Recess", 'BOOLEAN').object = shade_recess
shade.modifiers["Recess"].operation = 'DIFFERENCE'
shade.modifiers["Recess"].solver = 'EXACT'

shade.modifiers.new("Vent", 'BOOLEAN').object = top_vent
shade.modifiers["Vent"].operation = 'DIFFERENCE'
shade.modifiers["Vent"].solver = 'EXACT'

bpy.ops.object.select_all(action='DESELECT')
