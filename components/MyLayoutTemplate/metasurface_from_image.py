
import gdsfactory as gf
import numpy as np
from PIL import Image
import os
from typing import Callable, Tuple, Optional, Union

# =============================================================================
# UNIT CELL GENERATORS
# =============================================================================

def cell_rectangle(
    length: float = 1.0,
    width: float = 0.3,
    rotation: float = 0.0,
    layer: tuple = (1, 0)
) -> gf.Component:
    """
    Generates a rectangular bar unit cell.
    
    Args:
        length: Length of the rectangle.
        width: Width of the rectangle.
        rotation: Rotation angle in degrees.
        layer: GDS layer.
    """
    c = gf.Component()
    rect = c << gf.components.rectangle(size=(length, width), layer=layer, centered=True)
    rect.rotate(rotation)
    return c

def cell_clock(
    arm_length: float = 1.0,
    arm_width: float = 0.2,
    angle: float = 90.0,
    rotation: float = 0.0,
    layer: tuple = (1, 0)
) -> gf.Component:
    """
    Generates a 'clock' structure (two arms with an included angle).
    
    Args:
        arm_length: Length of each arm.
        arm_width: Width of each arm.
        angle: Included angle between the two arms in degrees.
        rotation: Overall rotation of the structure.
        layer: GDS layer.
    """
    c = gf.Component()
    
    # Arm 1: Along X axis
    a1 = gf.components.rectangle(size=(arm_length, arm_width), layer=layer, centered=False)
    ref1 = c << a1
    ref1.movey(-arm_width/2) # Center vertically
    
    # Arm 2: Rotated by 'angle'
    a2 = gf.components.rectangle(size=(arm_length, arm_width), layer=layer, centered=False)
    ref2 = c << a2
    ref2.movey(-arm_width/2)
    ref2.rotate(angle)
    
    # Rotate entire structure
    c.rotate(rotation)
    return c

def cell_t_shape(
    length_top: float = 1.0,
    width_top: float = 0.3,
    length_stem: float = 1.0,
    width_stem: float = 0.3,
    rotation: float = 0.0,
    layer: tuple = (1, 0)
) -> gf.Component:
    """
    Generates a T-shape structure.
    
    Args:
        length_top: Length of the top horizontal bar.
        width_top: Width of the top horizontal bar.
        length_stem: Length of the vertical stem.
        width_stem: Width of the vertical stem.
        rotation: Rotation angle in degrees.
        layer: GDS layer.
    """
    c = gf.Component()
    
    # Top bar
    top = c << gf.components.rectangle(size=(length_top, width_top), layer=layer, centered=True)
    top.movey(length_stem / 2 + width_top / 2)
    
    # Stem
    stem = c << gf.components.rectangle(size=(width_stem, length_stem), layer=layer, centered=True)
    
    # Rotate
    c.rotate(rotation)
    return c

def cell_ellipse(
    major_axis: float = 1.0,
    minor_axis: float = 0.5,
    rotation: float = 0.0,
    layer: tuple = (1, 0)
) -> gf.Component:
    """
    Generates an elliptical structure.
    
    Args:
        major_axis: Length of the major axis.
        minor_axis: Length of the minor axis.
        rotation: Rotation angle in degrees.
        layer: GDS layer.
    """
    c = gf.Component()
    ellipse = c << gf.components.ellipse(radii=(major_axis/2, minor_axis/2), layer=layer)
    ellipse.rotate(rotation)
    return c

def cell_split_ring(
    radius: float = 1.0,
    width: float = 0.2,
    gap_angle: float = 30.0,
    rotation: float = 0.0,
    layer: tuple = (1, 0)
) -> gf.Component:
    """
    Generates a split ring resonator (C-shape).
    
    Args:
        radius: Outer radius of the ring.
        width: Width of the ring trace.
        gap_angle: Angular size of the gap in degrees.
        rotation: Rotation angle in degrees.
        layer: GDS layer.
    """
    c = gf.Component()
    
    # Use bend_circular to create a partial ring
    # radius in bend_circular is usually centerline radius
    center_radius = radius - width / 2.0
    bend_angle = 360.0 - gap_angle
    
    # bend_circular creates a bend starting from (0,0)
    split_ring = c << gf.components.bend_circular(
        radius=center_radius,
        angle=bend_angle,
        width=width,
        layer=layer,
        allow_min_radius_violation=True
    )
    
    # Center the split ring
    # bend_circular starts at (0,0) tangent to x-axis. Center of curvature is at (0, center_radius).
    # We move it so the center of curvature is at (0,0).
    split_ring.move((0, -center_radius))
    
    # Rotate so the gap is centered (e.g., at 0 degrees)
    # The arc starts at -90 degrees (relative to center) and goes counter-clockwise for bend_angle.
    # Start angle is 270 (-90). End angle is 270 + bend_angle.
    # Midpoint of arc is 270 + bend_angle/2.
    # We want midpoint to be at 180 (so gap is at 0).
    # rotation needed = 180 - (270 + bend_angle/2) = -90 - bend_angle/2
    
    # Let's adjust rotation to place gap at 0 degrees (right side)
    # Gap center is at 0. Arc center is at 180.
    # Current arc center (relative to center of curvature) is at -90 + bend_angle/2.
    # We want it at 180.
    # Rotate by: 180 - (-90 + bend_angle/2) = 270 - bend_angle/2
    
    rotation_offset = 270.0 - bend_angle / 2.0
    split_ring.rotate(rotation_offset)
    
    # Apply user rotation
    c.rotate(rotation)
    
    return c

def cell_variable_size(
    shape: str = "square",
    size: float = 1.0,
    rotation: float = 0.0,
    layer: tuple = (1, 0)
) -> gf.Component:
    """
    Generates a square or circle of variable size.
    
    Args:
        shape: "square" or "circle".
        size: Side length (square) or Diameter (circle).
        rotation: Rotation angle (relevant for square).
        layer: GDS layer.
    """
    c = gf.Component()
    if shape == "circle":
        comp = c << gf.components.circle(radius=size/2, layer=layer)
    else:
        comp = c << gf.components.rectangle(size=(size, size), layer=layer, centered=True)
        comp.rotate(rotation)
    return c


# =============================================================================
# MAIN GENERATOR FUNCTION
# =============================================================================

def generate_metasurface_from_image(
    image_path: str,
    output_gds: str,
    pitch_x: float = 1.0,
    pitch_y: float = 1.0,
    cell_function: Callable = cell_rectangle,
    value_map_func: Callable = None,
    pixel_to_nm_scale: float = None,
    invert_image: bool = False,
    layer: tuple = (1, 0),
    top_cell_name: str = "Metasurface_Array"
) -> gf.Component:
    """
    Generates a metasurface array based on a grayscale image.
    
    Args:
        image_path: Path to the input image.
        output_gds: Path to save the output GDS file.
        pitch_x: Periodicity in X direction (um).
        pitch_y: Periodicity in Y direction (um).
        cell_function: Function to generate unit cell (e.g., cell_rectangle).
                       Must accept parameters determined by value_map_func.
        value_map_func: Function that takes a pixel value (0-255) and returns 
                        a dictionary of kwargs for the cell_function.
                        Example: lambda val: {"rotation": val * 180 / 255, "length": 0.8}
        pixel_to_nm_scale: Deprecated/Optional. If set, ignores pitch and uses pixel mapping directly? 
                           Here we assume 1 pixel = 1 unit cell.
        invert_image: If True, 0 becomes 255 and vice versa.
        layer: GDS layer to place structures on.
        top_cell_name: Name of the top-level GDS cell.
        
    Returns:
        gf.Component: The generated top-level component.
    """
    
    # 1. Load Image
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    img = Image.open(image_path).convert('L') # Convert to grayscale
    img_array = np.array(img)
    
    if invert_image:
        img_array = 255 - img_array
        
    height, width = img_array.shape
    
    print(f"Image loaded: {width}x{height} pixels")
    print(f"Generating array with pitch {pitch_x}x{pitch_y} um")
    
    # 2. Create Top Component
    top = gf.Component(top_cell_name)
    
    # 3. Iterate pixels and place cells
    # We can cache identical cells to reduce GDS size/memory usage
    cell_cache = {}
    
    for y in range(height):
        for x in range(width):
            val = img_array[y, x]
            
            # Determine cell parameters from pixel value
            if value_map_func:
                kwargs = value_map_func(val)
            else:
                kwargs = {"rotation": val * 180.0 / 255.0, "length": pitch_x * 0.8, "width": pitch_x * 0.2}
            
            if "layer" not in kwargs:
                kwargs["layer"] = layer
            
            cache_key = tuple(sorted(kwargs.items()))
            
            if cache_key in cell_cache:
                cell = cell_cache[cache_key]
            else:
                cell = cell_function(**kwargs)
                cell_cache[cache_key] = cell
            
            pos_x = x * pitch_x
            pos_y = (height - 1 - y) * pitch_y 
            
            ref = top << cell
            ref.move((pos_x, pos_y))
            
    # 4. Save GDS
    top.write_gds(output_gds)
    print(f"GDS saved to: {output_gds}")
    
    return top


# =============================================================================
# EXAMPLES AND DEMO
# =============================================================================

if __name__ == "__main__":
    # Create a dummy gradient image for demonstration if one doesn't exist
    demo_image_path = "gradient_test.png"
    width, height = 50, 50
    gradient = np.zeros((height, width), dtype=np.uint8)
    for i in range(width):
        gradient[:, i] = int(i * 255 / (width - 1))
    
    Image.fromarray(gradient).save(demo_image_path)
    print(f"Created test image: {demo_image_path}")
    
    # Example 1: Rotating Rectangles (Pancharatnam-Berry phase)
    # Map 0-255 to 0-180 degrees
    def map_pb_phase(val):
        return {
            "length": 0.8,
            "width": 0.2,
            "rotation": val * 180.0 / 255.0
        }
    
    generate_metasurface_from_image(
        image_path=demo_image_path,
        output_gds="metasurface_pb_rect.gds",
        pitch_x=1.0,
        pitch_y=1.0,
        cell_function=cell_rectangle,
        value_map_func=map_pb_phase,
        top_cell_name="Metasurface_PB_Rect"
    )
    
    # Example 2: Variable Diameter Circles (Propagation phase)
    # Map 0-255 to diameter 0.2 - 0.9 um
    def map_prop_phase(val):
        min_d = 0.2
        max_d = 0.9
        d = min_d + (val / 255.0) * (max_d - min_d)
        return {
            "shape": "circle",
            "size": d
        }
        
    generate_metasurface_from_image(
        image_path=demo_image_path,
        output_gds="metasurface_variable_circle.gds",
        pitch_x=1.0,
        pitch_y=1.0,
        cell_function=cell_variable_size,
        value_map_func=map_prop_phase,
        top_cell_name="Metasurface_Var_Circle"
    )
    
    # Example 3: Rotating Split Ring
    def map_split_ring(val):
        return {
            "radius": 0.4,
            "width": 0.1,
            "gap_angle": 45,
            "rotation": val * 360.0 / 255.0 # Full 360 rotation
        }

    generate_metasurface_from_image(
        image_path=demo_image_path,
        output_gds="metasurface_split_ring.gds",
        pitch_x=1.0,
        pitch_y=1.0,
        cell_function=cell_split_ring,
        value_map_func=map_split_ring,
        top_cell_name="Metasurface_Split_Ring"
    )
