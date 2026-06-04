import bpy
import trimesh
import json
import os
import bmesh
import math
import uuid
import sys

try:
    from sdf_generator import generate_sdf_mesh
except Exception as e:
    # sdf_generator requires heavy dependencies (torch). Provide a fallback.
    print(f"[WARN] sdf_generator could not be imported: {e}. Using dummy placeholder.")
    def generate_sdf_mesh(*args, **kwargs):
        """Fallback no‑op stub for generate_sdf_mesh when torch is unavailable.
        Returns ``None``; callers should handle a ``None`` result gracefully.
        """
        return None

# ==========================================
# 0. NUKE THE SCENE
# ==========================================

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

# ==========================================
# 1. GENERATE THE MINIMAL CONE BASE (X = 0)
# ==========================================
def create_base(params):
    # Helper to clamp dimensions to the Creality K2 Plus build volume (≈220 mm)
    def clamp(val, max_val=200):
        return min(val, max_val)

    # Base defaults – smaller for a tabletop lamp
    base_radius = clamp(params.get("baseRadius", 60.0))
    base_height = clamp(params.get("baseHeight", 100.0))
    peg_radius = clamp(params.get("pegDiameter", 40.0) / 2.0)
    socket_radius = clamp(params.get("socketDiameter", 30.0) / 2.0)
    socket_clearance = 1.0

    # Create the cone base centered at the origin (X=0)
    bpy.ops.mesh.primitive_cone_add(
        vertices=64,
        radius1=base_radius,
        radius2=peg_radius,
        depth=base_height,
        location=(0, 0, base_height / 2),
    )
    base = bpy.context.active_object
    base.name = "AESTHETEQ_Orbital_Base"
    bpy.ops.object.shade_smooth()

    # Integrated socket housing (cylindrical)
    socket_housing_radius = socket_radius + socket_clearance
    socket_housing_height = 10.0
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32,
        radius=socket_housing_radius,
        depth=socket_housing_height,
        location=(0, 0, base_height + socket_housing_height / 2),
    )
    socket_housing = bpy.context.active_object
    socket_housing.name = "E26_Socket_Housing"
    socket_housing.display_type = 'SOLID'
    # Lip for the socket
    lip_thickness = 0.4
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32,
        radius=socket_housing_radius + lip_thickness,
        depth=1.5,
        location=(0, 0, base_height + socket_housing_height + 0.75),
    )
    lip = bpy.context.active_object
    lip.name = "E26_Socket_Lip"
    lip.hide_render = True

    # Male peg for dovetail interlock
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32,
        radius=peg_radius,
        depth=12,
        location=(0, 0, base_height + 6),
    )
    base_peg = bpy.context.active_object
    base_peg.hide_render = True

    # Dovetail male – positioned directly above the peg
    dovetail_width = peg_radius * 2.5
    dovetail_depth = 6.0
    dovetail_height = 4.0
    bpy.ops.mesh.primitive_cube_add(
        size=1,
        location=(0, 0, base_height + 12 + dovetail_height / 2),
    )
    dovetail = bpy.context.active_object
    dovetail.scale = (dovetail_width / 2, dovetail_depth / 2, dovetail_height / 2)
    dovetail.name = "Dovetail_Male"
    bpy.ops.object.modifier_add(type='BEVEL')
    dovetail.modifiers[-1].width = 0.3
    dovetail.modifiers[-1].segments = 2
    dovetail.modifiers[-1].profile = 0.7
    dovetail.modifiers[-1].limit_method = 'NONE'
    bpy.context.view_layer.objects.active = dovetail
    bpy.ops.object.modifier_apply(modifier=dovetail.modifiers[-1].name)

    # Internal wireframe core
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32,
        radius=socket_radius,
        depth=180,
        location=(0, 0, 90),
    )
    thread_tunnel = bpy.context.active_object
    thread_tunnel.display_type = 'WIRE'
    thread_tunnel.hide_render = True

    return base

# ==========================================
# 2. ORGANIC SCULPTURE VIA SDF (X = 0)
# ==========================================
def create_sculpture(params):
    """Generate an organic sculpture using the SDF network and import it into Blender."""
    # Derive a deterministic latent vector from numeric params
    seed_vals = [
        params.get("saucerRadius", 150.0),
        params.get("ribCount", 18),
        params.get("ribDepth", 14.0),
        params.get("ribTwist", 1.5),
        params.get("shellThickness", 2.6)
    ]
    seed = int(sum(seed_vals) * 1000) % (2**32 - 1)
    import numpy as np
    np.random.seed(seed)
    latent = np.random.randn(128).astype(np.float32)
    
    # Attempt to generate organic sculpture via SDF; fallback to sphere if unavailable
    try:
        mesh = generate_sdf_mesh(latent, bounds=1.0, resolution=256)
    except Exception as e:
        mesh = None
        print(f"[WARN] generate_sdf_mesh failed: {e}")
    if mesh is None:
        # Simple fallback – create a UV sphere as placeholder sculpture
        bpy.ops.mesh.primitive_uv_sphere_add(radius=params.get("saucerRadius", 80), location=(0, 0, params.get("baseHeight", 100) + 50))
        return bpy.context.active_object

    def mesh_to_object(mesh, obj_name):
        bm = bmesh.new()
        for v in mesh.vertices:
            bm.verts.new(v.tolist())
        bm.verts.ensure_lookup_table()
        for face in mesh.faces:
            try:
                bm.faces.new([bm.verts[i] for i in face])
            except ValueError:
                pass
        new_mesh = bpy.data.meshes.new(obj_name)
        bm.to_mesh(new_mesh)
        bm.free()
        obj = bpy.data.objects.new(obj_name, new_mesh)
        bpy.context.collection.objects.link(obj)
        return obj

    sculpture = mesh_to_object(mesh, "AESTHETEQ_Organic_Sculpture")
    sculpture.location = (0, 0, params.get("baseHeight", 100.0) + 50)
    return sculpture

# ==========================================
# 3. GENERATE THE MCM SAUCER SHADE (X = 0)
# ==========================================
def create_saucer(params):
    def clamp(v, max_val=200):
        return min(v, max_val)

    saucer_radius = clamp(params.get("saucerRadius", 80.0))
    saucer_squash = params.get("saucerSquash", 0.4)
    rib_count = params.get("ribCount", 12)
    rib_depth = params.get("ribDepth", 6.0)
    rib_twist = params.get("ribTwist", 1.0)
    shell_thickness = params.get("shellThickness", 1.2)
    vent_radius = clamp(params.get("ventDiameter", 30.0) / 2.0)
    peg_radius = clamp(params.get("pegDiameter", 40.0) / 2.0)
    dovetail_clearance = 0.2

    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=128,
        ring_count=64,
        radius=saucer_radius,
        location=(0, 0, params.get("baseHeight", 100.0) + 10),
    )
    shade = bpy.context.active_object
    shade.name = "AESTHETEQ_Orbital_Saucer"

    bm = bmesh.new()
    bm.from_mesh(shade.data)
    for v in bm.verts:
        v.co.z *= saucer_squash
        xy_dist = math.sqrt(v.co.x ** 2 + v.co.y ** 2)
        if xy_dist < 0.1: continue
        angle = math.atan2(v.co.y, v.co.x)
        z_norm = (v.co.z + saucer_radius * saucer_squash) / (saucer_radius * 2 * saucer_squash)
        twist = z_norm * math.pi * rib_twist
        r_mult = 1.0 + (math.sin((angle * rib_count) + twist) * (rib_depth / saucer_radius))
        v.co.x *= r_mult
        v.co.y *= r_mult
    bm.to_mesh(shade.data)
    bm.free()
    bpy.ops.object.shade_smooth()

    solid_mod = shade.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid_mod.thickness = params.get("solidifyThickness", 1.0)
    solid_mod.offset = 0
    bpy.context.view_layer.objects.active = shade
    bpy.ops.object.modifier_apply(modifier=solid_mod.name)

    dovetail_width = peg_radius * 2.5
    dovetail_depth = 6.0 + dovetail_clearance
    dovetail_height = 4.0 + dovetail_clearance
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, params.get("baseHeight", 100.0) + 15 + dovetail_height / 2))
    dovetail_female = bpy.context.active_object
    dovetail_female.scale = (dovetail_width / 2, dovetail_depth / 2, dovetail_height / 2)
    dovetail_female.name = "Dovetail_Female"
    shade.modifiers.new("Dovetail_Cut", 'BOOLEAN').object = dovetail_female
    shade.modifiers["Dovetail_Cut"].operation = 'DIFFERENCE'
    shade.modifiers["Dovetail_Cut"].solver = 'EXACT'

    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32,
        radius=vent_radius,
        depth=30,
        location=(0, 0, params.get("baseHeight", 100.0) + 30),
    )
    top_vent = bpy.context.active_object
    top_vent.display_type = 'WIRE'
    top_vent.hide_render = True

    bpy.context.view_layer.objects.active = shade
    for mod in shade.modifiers: bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(dovetail_female, do_unlink=True)
    bpy.data.objects.remove(top_vent, do_unlink=True)
    return shade

# ==========================================
# 4. MAIN ENTRY
# ==========================================
if __name__ == "__main__":
    params = {}
    for arg in sys.argv:
        if arg.startswith("{"):
            try: params = json.loads(arg)
            except: pass
    if params.get("tableLamp"):
        params.setdefault("baseRadius", 60.0)
        params.setdefault("baseHeight", 100.0)
        params.setdefault("saucerRadius", 80.0)
    clear_scene()
    base = create_base(params)
    saucer = create_saucer(params)
    sculpture = create_sculpture(params)
    print("Export complete.")
