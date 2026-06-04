import bpy
import bmesh
import math
import os

# ==============================================================================
# PARAMETERS - TWEAKABLE VARIABLES
# ==============================================================================
# General Dimensions
LAMP_HEIGHT = 200.0         # Total height of the diffuser (mm)
BASE_RADIUS = 30.0          # Base radius of the diffuser (60mm diameter)
MAX_RADIUS = 50.0           # Maximum swelling radius of the diffuser
LED_PUCK_DIAMETER = 60.0    # Standard LED puck diameter
LED_PUCK_HEIGHT = 25.0      # Height of the LED puck cavity

# Snap-fit & Tolerances
SNAP_RING_HEIGHT = 4.0      # Vertical height of the snap ring ridge
SNAP_RING_DEPTH = 1.2       # How far the snap ring protrudes outward
TOLERANCE = 0.2             # Clearance gap between base and diffuser

# Biomorphic Exoskeleton (Ribs)
RIB_COUNT = 6               # Number of organic ribs
RIB_THICKNESS = 6.0         # Base thickness of ribs
TWIST_ANGLE = 90.0          # Total twist of ribs in degrees over the height
OVERHANG_LIMIT = 45.0       # Max overhang angle (degrees). 45 means dr/dz <= 1

# Branding
BRAND_TEXT = "WCA"
BRAND_DEPTH = 0.6           # Depth of the debossed text

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================
def clear_scene():
    """Removes all objects from the current scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def apply_modifiers(obj):
    """Applies all modifiers on a given object."""
    bpy.context.view_layer.objects.active = obj
    for mod in obj.modifiers:
        bpy.ops.object.modifier_apply(modifier=mod.name)

# ==============================================================================
# 1. CORE DIFFUSER (Vase Mode Optimized)
# ==============================================================================
def create_diffuser():
    """
    Creates an undulating, vase-mode safe cylindrical diffuser.
    Includes the male snap-fit ring at the bottom.
    """
    segments = 128
    height_steps = 100
    
    verts = []
    faces = []
    
    # Generate vertices using a sine wave profile
    for i in range(height_steps + 1):
        z = (i / height_steps) * LAMP_HEIGHT
        
        # Base radius
        r = BASE_RADIUS
        
        # Male Snap Ring at the bottom
        if z < SNAP_RING_HEIGHT:
            # Create a smooth outward bump. Using sine for smooth transition
            bump = math.sin((z / SNAP_RING_HEIGHT) * math.pi) * SNAP_RING_DEPTH
            r += bump
            
        # Undulating swelling (biomorphic shape)
        # Avoid swelling at the very base to allow it to fit in the base
        if z > SNAP_RING_HEIGHT:
            z_norm = (z - SNAP_RING_HEIGHT) / (LAMP_HEIGHT - SNAP_RING_HEIGHT)
            swell = math.sin(z_norm * math.pi) * (MAX_RADIUS - BASE_RADIUS)
            r += swell
            
        for s in range(segments):
            angle = (s / segments) * 2 * math.pi
            x = r * math.cos(angle)
            y = r * math.sin(angle)
            verts.append((x, y, z))
            
    # Generate faces (quads)
    for i in range(height_steps):
        for s in range(segments):
            next_s = (s + 1) % segments
            v1 = i * segments + s
            v2 = i * segments + next_s
            v3 = (i + 1) * segments + next_s
            v4 = (i + 1) * segments + s
            faces.append((v1, v2, v3, v4))
            
    # Cap the bottom (required for boolean or slicing solid)
    # We add a center vertex for the bottom
    bottom_center_idx = len(verts)
    verts.append((0, 0, 0))
    for s in range(segments):
        next_s = (s + 1) % segments
        faces.append((bottom_center_idx, next_s, s))
        
    # Cap the top
    top_center_idx = len(verts)
    verts.append((0, 0, LAMP_HEIGHT))
    top_start = height_steps * segments
    for s in range(segments):
        next_s = (s + 1) % segments
        faces.append((top_center_idx, top_start + s, top_start + next_s))

    mesh = bpy.data.meshes.new("Diffuser_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    
    diffuser = bpy.data.objects.new("Diffuser", mesh)
    bpy.context.collection.objects.link(diffuser)
    
    # Make it smooth
    for p in mesh.polygons:
        p.use_smooth = True
        
    return diffuser

# ==============================================================================
# 2. BIOMORPHIC EXOSKELETON (Base & Ribs)
# ==============================================================================
def create_base():
    """
    Creates the base unit that houses the LED puck and the female snap ring.
    """
    # Outer base cylinder
    base_outer_r = BASE_RADIUS + RIB_THICKNESS + 2.0
    base_h = LED_PUCK_HEIGHT + 10.0
    
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=128, 
        radius=base_outer_r, 
        depth=base_h, 
        location=(0, 0, base_h / 2)
    )
    base_obj = bpy.context.active_object
    base_obj.name = "Exoskeleton_Base"
    
    # LED Puck Cavity Cutter
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=64, 
        radius=LED_PUCK_DIAMETER / 2 + TOLERANCE, 
        depth=LED_PUCK_HEIGHT + 5.0,  # Extend slightly out the bottom
        location=(0, 0, LED_PUCK_HEIGHT / 2 - 1.0)
    )
    puck_cutter = bpy.context.active_object
    
    # Wire Hole Cutter
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32,
        radius=4.0,
        depth=base_outer_r * 2,
        location=(0, 0, 5.0)
    )
    wire_cutter = bpy.context.active_object
    wire_cutter.rotation_euler[1] = math.pi / 2 # Rotate to lie flat on X axis
    
    # Diffuser Socket Cavity Cutter (with female snap ring)
    # We generate a slightly larger version of the diffuser bottom
    segments = 64
    verts = [(0, 0, base_h)]
    faces = []
    
    socket_depth = SNAP_RING_HEIGHT + 5.0
    steps = 20
    for i in range(steps + 1):
        z = base_h - socket_depth + (i / steps) * socket_depth
        z_relative = z - (base_h - socket_depth)
        
        r = BASE_RADIUS + TOLERANCE
        if z_relative < SNAP_RING_HEIGHT:
            bump = math.sin((z_relative / SNAP_RING_HEIGHT) * math.pi) * SNAP_RING_DEPTH
            r += bump
            
        for s in range(segments):
            angle = (s / segments) * 2 * math.pi
            verts.append((r * math.cos(angle), r * math.sin(angle), z))
            
    # Faces for socket cutter (standard cylinder wrap)
    for i in range(steps):
        for s in range(segments):
            next_s = (s + 1) % segments
            v1 = 1 + i * segments + s
            v2 = 1 + i * segments + next_s
            v3 = 1 + (i + 1) * segments + next_s
            v4 = 1 + (i + 1) * segments + s
            faces.append((v1, v2, v3, v4))
            
    # Cap bottom of socket
    bottom_center = len(verts)
    verts.append((0, 0, base_h - socket_depth))
    for s in range(segments):
        next_s = (s + 1) % segments
        faces.append((bottom_center, 1 + next_s, 1 + s))
        
    # Cap top of socket
    top_center = len(verts)
    verts.append((0, 0, base_h + 1.0)) # slightly above to ensure clean cut
    top_start = 1 + steps * segments
    for s in range(segments):
        next_s = (s + 1) % segments
        faces.append((top_center, top_start + s, top_start + next_s))

    socket_mesh = bpy.data.meshes.new("Socket_Cutter_Mesh")
    socket_mesh.from_pydata(verts, [], faces)
    socket_cutter = bpy.data.objects.new("Socket_Cutter", socket_mesh)
    bpy.context.collection.objects.link(socket_cutter)
    
    # Perform Booleans on Base
    def add_boolean(target, cutter, operation='DIFFERENCE'):
        mod = target.modifiers.new(name="Bool", type='BOOLEAN')
        mod.operation = operation
        mod.object = cutter
        mod.solver = 'EXACT'
        
    add_boolean(base_obj, puck_cutter)
    add_boolean(base_obj, wire_cutter)
    add_boolean(base_obj, socket_cutter)
    
    apply_modifiers(base_obj)
    
    # Cleanup Cutters
    bpy.data.objects.remove(puck_cutter, do_unlink=True)
    bpy.data.objects.remove(wire_cutter, do_unlink=True)
    bpy.data.objects.remove(socket_cutter, do_unlink=True)
    
    return base_obj, base_h

def create_ribs(base_h):
    """
    Generates the organic ribs obeying the 45-degree overhang rule.
    """
    ribs = []
    
    # Curve math for 45-degree overhangs:
    # To maintain dr/dz <= 1, the radius can grow at most 1 unit per 1 unit of Z.
    # We will use a linear/sub-linear growth outward, bounded by the z-height.
    
    for i in range(RIB_COUNT):
        base_angle = (i / RIB_COUNT) * 2 * math.pi
        
        curve_data = bpy.data.curves.new(name=f"RibCurve_{i}", type='CURVE')
        curve_data.dimensions = '3D'
        curve_data.fill_mode = 'FULL'
        curve_data.bevel_depth = RIB_THICKNESS / 2.0
        curve_data.bevel_resolution = 4
        
        spline = curve_data.splines.new(type='BEZIER')
        
        # Rib profile control points
        num_points = 5
        spline.bezier_points.add(num_points - 1)
        
        for p in range(num_points):
            t = p / (num_points - 1)
            
            # Z position maps from base to near top
            z = base_h - 5.0 + t * (LAMP_HEIGHT - base_h - 10.0)
            
            # Radius calculation.
            # Start at base radius + thickness.
            # Bow outward slightly, but ensure dr/dz is safe.
            r_diffuser = BASE_RADIUS + (MAX_RADIUS - BASE_RADIUS) * math.sin(t * math.pi)
            
            # Max safe outward growth from base is exactly (z - base_z)
            max_safe_r = (BASE_RADIUS + RIB_THICKNESS + 2.0) + (z - base_h) * math.tan(math.radians(OVERHANG_LIMIT))
            
            # We want it to cradle the diffuser (be slightly larger than it)
            desired_r = r_diffuser + RIB_THICKNESS
            
            # Clamp to safe overhang
            r = min(desired_r, max_safe_r)
            
            # Apply twist
            current_angle = base_angle + t * math.radians(TWIST_ANGLE)
            
            x = r * math.cos(current_angle)
            y = r * math.sin(current_angle)
            
            pt = spline.bezier_points[p]
            pt.co = (x, y, z)
            pt.handle_left_type = 'AUTO'
            pt.handle_right_type = 'AUTO'
            
        rib_obj = bpy.data.objects.new(f"Rib_{i}", curve_data)
        bpy.context.collection.objects.link(rib_obj)
        
        # Convert to mesh
        bpy.context.view_layer.objects.active = rib_obj
        rib_obj.select_set(True)
        bpy.ops.object.convert(target='MESH')
        
        ribs.append(bpy.context.active_object)
        bpy.ops.object.select_all(action='DESELECT')
        
    return ribs

# ==============================================================================
# 3. TEXT DEBOSSING
# ==============================================================================
def apply_branding(base_obj):
    """
    Creates "WCA" text and debosses it into the base.
    Attempts to load a Windows font (e.g., Arial Italic as fallback) 
    and shears it to look handwritten if needed.
    """
    bpy.ops.object.text_add(location=(0, -BASE_RADIUS - RIB_THICKNESS, 8.0))
    text_obj = bpy.context.active_object
    text_obj.data.body = BRAND_TEXT
    
    # Try loading a handwriting/cursive font if on Windows
    font_paths = [
        "C:\\Windows\\Fonts\\segoesc.ttf",  # Segoe Script
        "C:\\Windows\\Fonts\\lucon.ttf",    # Lucida
        "C:\\Windows\\Fonts\\ariali.ttf"    # Arial Italic
    ]
    
    font_loaded = False
    for path in font_paths:
        if os.path.exists(path):
            try:
                font = bpy.data.fonts.load(path)
                text_obj.data.font = font
                font_loaded = True
                break
            except:
                pass
                
    if not font_loaded:
        # Fallback: shear the text to simulate italic/handwriting
        text_obj.data.shear = 0.3
        
    # Text settings
    text_obj.data.extrude = BRAND_DEPTH / 2.0
    text_obj.data.size = 6.0
    text_obj.data.align_x = 'CENTER'
    text_obj.data.align_y = 'CENTER'
    
    # Rotate to face outward on Y axis
    text_obj.rotation_euler[0] = math.pi / 2
    
    # Convert to mesh
    bpy.context.view_layer.objects.active = text_obj
    bpy.ops.object.convert(target='MESH')
    text_mesh = bpy.context.active_object
    
    # Boolean subtract from base
    mod = base_obj.modifiers.new(name="BrandBool", type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object = text_mesh
    mod.solver = 'EXACT'
    
    apply_modifiers(base_obj)
    
    # Cleanup text
    bpy.data.objects.remove(text_mesh, do_unlink=True)

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================
if __name__ == "__main__":
    clear_scene()
    
    print("Generating Core Diffuser...")
    diffuser = create_diffuser()
    
    print("Generating Exoskeleton Base...")
    base_obj, base_h = create_base()
    
    print("Generating Biomorphic Ribs...")
    ribs = create_ribs(base_h)
    
    print("Applying Branding...")
    apply_branding(base_obj)
    
    print("Fusing Base and Ribs...")
    # Join ribs to base
    bpy.ops.object.select_all(action='DESELECT')
    base_obj.select_set(True)
    for rib in ribs:
        rib.select_set(True)
    bpy.context.view_layer.objects.active = base_obj
    bpy.ops.object.join()
    
    # Ensure smooth shading on final base
    for p in base_obj.data.polygons:
        p.use_smooth = True
        
    print("Exporting STLs to Desktop...")
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", "New art")
    os.makedirs(desktop_path, exist_ok=True)
    
    # Export Diffuser
    diffuser_path = os.path.join(desktop_path, "Biomorphic_Diffuser.stl")
    bpy.ops.object.select_all(action='DESELECT')
    diffuser.select_set(True)
    bpy.context.view_layer.objects.active = diffuser
    try:
        bpy.ops.wm.stl_export(filepath=diffuser_path, export_selected_objects=True)
    except:
        bpy.ops.export_mesh.stl(filepath=diffuser_path, use_selection=True)
        
    # Export Base
    base_path = os.path.join(desktop_path, "Biomorphic_Base.stl")
    bpy.ops.object.select_all(action='DESELECT')
    base_obj.select_set(True)
    bpy.context.view_layer.objects.active = base_obj
    try:
        bpy.ops.wm.stl_export(filepath=base_path, export_selected_objects=True)
    except:
        bpy.ops.export_mesh.stl(filepath=base_path, use_selection=True)
        
    print("Done! Check 'Biomorphic_Diffuser.stl' and 'Biomorphic_Base.stl' in your Desktop/New art folder.")
