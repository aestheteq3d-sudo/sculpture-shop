import bpy
import bmesh
import math
import os

# ==============================================================================
# PARAMETERS - TWEAKABLE VARIABLES
# ==============================================================================
LAMP_HEIGHT = 200.0         # Total height of the lamp (mm)
BASE_RADIUS = 30.0          # Base radius where ribs start
MAX_RADIUS = 70.0           # Maximum outward curve of the ribs
BASE_HEIGHT = 30.0          # Height of the solid base

# LED Channel & Ribs
RIB_COUNT = 6               # Number of organic ribs
TWIST_ANGLE = 45.0          # Total twist of ribs (keep <= 60 for COB health)
OVERHANG_LIMIT = 45.0       # Max overhang angle (degrees).
COB_WIDTH = 6.0             # Width of the LED groove
COB_DEPTH = 3.0             # Depth of the LED groove
RIB_THICKNESS = 14.0        # Total thickness/depth of the rib
RIB_WIDTH = 10.0            # Total width of the rib

# Base Chamber
CHAMBER_RADIUS = 20.0       # Internal hollow chamber radius
CHAMBER_HEIGHT = 20.0       # Internal hollow chamber height
WIRE_TUNNEL_RADIUS = 2.5    # Radius of wire tunnels connecting ribs to chamber

# Branding
BRAND_TEXT = "WCA"
BRAND_DEPTH = 0.6           # Depth of the debossed text

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================
def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def apply_modifiers(obj):
    bpy.context.view_layer.objects.active = obj
    for mod in obj.modifiers:
        bpy.ops.object.modifier_apply(modifier=mod.name)

# ==============================================================================
# 1. CUSTOM BEVEL PROFILE (The Rib Cross-Section)
# ==============================================================================
def create_rib_profile():
    """
    Creates a 2D curve representing the rib cross-section.
    It's a rounded rectangle with a 6x3mm notch on the negative X side.
    The curve origin is offset so the rib sweeps along its outer edge,
    with the notch facing inward (-X).
    """
    curve_data = bpy.data.curves.new(name="RibProfileCurve", type='CURVE')
    curve_data.dimensions = '2D'
    spline = curve_data.splines.new(type='POLY')
    
    # Define points for the profile.
    # We build it centered on Y, from x=0 to x=RIB_THICKNESS.
    # The notch is at x=0, extending to x=COB_DEPTH, centered on Y=0.
    
    hw = RIB_WIDTH / 2.0
    notch_hw = COB_WIDTH / 2.0
    
    # Path of the outer boundary
    pts = [
        (0, -notch_hw),                      # Notch bottom inner
        (COB_DEPTH, -notch_hw),              # Notch bottom outer
        (COB_DEPTH, -hw),                    # Bottom inner corner
        (RIB_THICKNESS, -hw),                # Bottom outer corner
        (RIB_THICKNESS, hw),                 # Top outer corner
        (COB_DEPTH, hw),                     # Top inner corner
        (COB_DEPTH, notch_hw),               # Notch top outer
        (0, notch_hw),                       # Notch top inner
        (0, -notch_hw)                       # Close loop
    ]
    
    spline.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        spline.points[i].co = (p[0], p[1], 0, 1)
        
    spline.use_cyclic_u = True
    
    profile_obj = bpy.data.objects.new("RibProfile", curve_data)
    bpy.context.collection.objects.link(profile_obj)
    
    return profile_obj

# ==============================================================================
# 2. GENERATING THE RIBS
# ==============================================================================
def create_ribs(profile_obj):
    """
    Generates the swept ribs with Z-Up twisting so the LED channel faces inward.
    """
    ribs = []
    
    for i in range(RIB_COUNT):
        base_angle = (i / RIB_COUNT) * 2 * math.pi
        
        curve_data = bpy.data.curves.new(name=f"RibCurve_{i}", type='CURVE')
        curve_data.dimensions = '3D'
        curve_data.fill_mode = 'FULL'
        curve_data.twist_mode = 'Z_UP'  # CRITICAL: Keeps local Y aligned to global Z
        curve_data.use_fill_caps = True
        
        # Assign the custom profile
        curve_data.bevel_object = profile_obj
        
        spline = curve_data.splines.new(type='BEZIER')
        
        num_points = 5
        spline.bezier_points.add(num_points - 1)
        
        for p in range(num_points):
            t = p / (num_points - 1)
            
            z = BASE_HEIGHT + t * (LAMP_HEIGHT - BASE_HEIGHT)
            
            # Sweeping math for 45-deg overhang
            desired_r = BASE_RADIUS + (MAX_RADIUS - BASE_RADIUS) * math.sin(t * math.pi)
            max_safe_r = BASE_RADIUS + (z - BASE_HEIGHT) * math.tan(math.radians(OVERHANG_LIMIT))
            r = min(desired_r, max_safe_r)
            
            current_angle = base_angle + t * math.radians(TWIST_ANGLE)
            
            x = r * math.cos(current_angle)
            y = r * math.sin(current_angle)
            
            pt = spline.bezier_points[p]
            pt.co = (x, y, z)
            pt.handle_left_type = 'AUTO'
            pt.handle_right_type = 'AUTO'
            
            # Z-Up twist mode ensures the local X-axis (where our notch is) 
            # points precisely along the normal. We can adjust tilt to face the origin.
            pt.tilt = current_angle + math.pi # Face inward
            
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
# 3. BASE & WIRE ROUTING
# ==============================================================================
def create_base_and_routing():
    """
    Creates the base cylinder, central hollow chamber, and wire routing tunnels.
    """
    # 1. Solid Base
    base_r = BASE_RADIUS + RIB_THICKNESS
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=128, 
        radius=base_r, 
        depth=BASE_HEIGHT, 
        location=(0, 0, BASE_HEIGHT / 2)
    )
    base_obj = bpy.context.active_object
    base_obj.name = "Lamp_Base"
    
    # 2. Central Chamber Cutter
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=64, 
        radius=CHAMBER_RADIUS, 
        depth=CHAMBER_HEIGHT + 5.0,  # Extend out the bottom
        location=(0, 0, CHAMBER_HEIGHT / 2 - 1.0)
    )
    chamber_cutter = bpy.context.active_object
    
    # 3. Wire Tunnels
    tunnel_cutters = []
    for i in range(RIB_COUNT):
        base_angle = (i / RIB_COUNT) * 2 * math.pi
        
        # Tunnel from chamber center to the start of the rib notch
        start_r = CHAMBER_RADIUS
        end_r = BASE_RADIUS
        tunnel_len = end_r - start_r + 5.0
        
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=16,
            radius=WIRE_TUNNEL_RADIUS,
            depth=tunnel_len,
            location=(0, 0, 0)
        )
        tunnel = bpy.context.active_object
        
        # Rotate and position
        tunnel.rotation_euler[1] = math.pi / 2
        tunnel.rotation_euler[2] = base_angle
        
        # Move outward and up to the top of the base (where ribs start)
        cx = (start_r + end_r) / 2 * math.cos(base_angle)
        cy = (start_r + end_r) / 2 * math.sin(base_angle)
        tunnel.location = (cx, cy, BASE_HEIGHT - WIRE_TUNNEL_RADIUS)
        
        tunnel_cutters.append(tunnel)
        
    return base_obj, chamber_cutter, tunnel_cutters

# ==============================================================================
# 4. BRANDING DEBOSS
# ==============================================================================
def apply_branding(base_obj):
    bpy.ops.object.text_add(location=(0, -(BASE_RADIUS + RIB_THICKNESS), 8.0))
    text_obj = bpy.context.active_object
    text_obj.data.body = BRAND_TEXT
    
    font_paths = [
        "C:\\Windows\\Fonts\\segoesc.ttf",  
        "C:\\Windows\\Fonts\\lucon.ttf",    
        "C:\\Windows\\Fonts\\ariali.ttf"    
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
        text_obj.data.shear = 0.3
        
    text_obj.data.extrude = BRAND_DEPTH / 2.0
    text_obj.data.size = 6.0
    text_obj.data.align_x = 'CENTER'
    text_obj.data.align_y = 'CENTER'
    
    text_obj.rotation_euler[0] = math.pi / 2
    
    bpy.context.view_layer.objects.active = text_obj
    bpy.ops.object.convert(target='MESH')
    text_mesh = bpy.context.active_object
    
    mod = base_obj.modifiers.new(name="BrandBool", type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object = text_mesh
    mod.solver = 'EXACT'
    
    apply_modifiers(base_obj)
    bpy.data.objects.remove(text_mesh, do_unlink=True)

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================
if __name__ == "__main__":
    clear_scene()
    
    print("Generating Rib Profile...")
    profile_obj = create_rib_profile()
    
    print("Generating Biomorphic Ribs...")
    ribs = create_ribs(profile_obj)
    
    print("Generating Base and Routing...")
    base_obj, chamber_cutter, tunnel_cutters = create_base_and_routing()
    
    print("Applying Branding...")
    apply_branding(base_obj)
    
    print("Fusing Geometry...")
    # Join ribs to base
    bpy.ops.object.select_all(action='DESELECT')
    base_obj.select_set(True)
    for rib in ribs:
        rib.select_set(True)
    bpy.context.view_layer.objects.active = base_obj
    bpy.ops.object.join()
    
    # Boolean subtract chamber and tunnels
    mod = base_obj.modifiers.new(name="BoolChamber", type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object = chamber_cutter
    mod.solver = 'EXACT'
    
    for i, tunnel in enumerate(tunnel_cutters):
        mod = base_obj.modifiers.new(name=f"BoolTunnel_{i}", type='BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.object = tunnel
        mod.solver = 'EXACT'
        
    apply_modifiers(base_obj)
    
    # Cleanup cutters
    bpy.data.objects.remove(chamber_cutter, do_unlink=True)
    for tunnel in tunnel_cutters:
        bpy.data.objects.remove(tunnel, do_unlink=True)
    bpy.data.objects.remove(profile_obj, do_unlink=True)
    
    for p in base_obj.data.polygons:
        p.use_smooth = True
        
    print("Exporting STL to Desktop...")
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", "New art")
    os.makedirs(desktop_path, exist_ok=True)
    
    stl_path = os.path.join(desktop_path, "LED_Rib_Lamp.stl")
    bpy.ops.object.select_all(action='DESELECT')
    base_obj.select_set(True)
    bpy.context.view_layer.objects.active = base_obj
    try:
        bpy.ops.wm.stl_export(filepath=stl_path, export_selected_objects=True)
    except:
        bpy.ops.export_mesh.stl(filepath=stl_path, use_selection=True)
        
    print(f"Done! Check '{stl_path}'")
