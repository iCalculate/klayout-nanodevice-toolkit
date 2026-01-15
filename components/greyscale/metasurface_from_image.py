
import gdsfactory as gf
import numpy as np
from PIL import Image
import os
from typing import Callable, Tuple, Optional, Union

# =============================================================================
# UNIT CELL GENERATORS
# =============================================================================

def cell_rectangle(
    length: float = 1.5,
    width: float = 0.5,
    rotation: float = 0.0,
    layer: tuple = (1, 0)
) -> gf.Component:
    """Generates a rectangular bar unit cell."""
    c = gf.Component()
    rect = c << gf.components.rectangle(size=(length, width), layer=layer, centered=True)
    rect.rotate(rotation)
    return c

def cell_clock(
    arm_length: float = 0.8,
    arm_width: float = 0.5,
    angle: float = 90.0,
    rotation: float = 0.0,
    layer: tuple = (1, 0)
) -> gf.Component:
    """Generates a 'clock' structure (two arms with an included angle)."""
    c = gf.Component()
    
    # Add circular joint at pivot for smooth connection
    # Pivot is at (0,0)
    pivot = c << gf.components.circle(radius=arm_width/2, layer=layer)
    
    # Arm 1: Along X axis (fixed relative to structure)
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
    length_top: float = 1.5,
    width_top: float = 0.5,
    length_stem: float = 1.2,
    width_stem: float = 0.5,
    rotation: float = 0.0,
    layer: tuple = (1, 0)
) -> gf.Component:
    """Generates a T-shape structure."""
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
    major_axis: float = 1.5,
    minor_axis: float = 0.6,
    rotation: float = 0.0,
    layer: tuple = (1, 0)
) -> gf.Component:
    """Generates an elliptical structure."""
    c = gf.Component()
    ellipse = c << gf.components.ellipse(radii=(major_axis/2, minor_axis/2), layer=layer)
    ellipse.rotate(rotation)
    return c

def cell_split_ring(
    radius: float = 0.8,
    width: float = 0.5,
    gap_angle: float = 45.0,
    rotation: float = 0.0,
    layer: tuple = (1, 0)
) -> gf.Component:
    """Generates a split ring resonator (C-shape)."""
    c = gf.Component()
    
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
    split_ring.move((0, -center_radius))
    
    # Rotate so the gap is centered (at 0 degrees, right side)
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
    """Generates a square or circle of variable size."""
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
    output_gds: Optional[str],
    pitch_x: float = 1.0,
    pitch_y: float = 1.0,
    cell_function: Callable = cell_rectangle,
    value_map_func: Callable = None,
    pixel_to_nm_scale: float = None,
    invert_image: bool = False,
    layer: tuple = (1, 0),
    top_cell_name: str = "Metasurface_Array",
    flatten: bool = False
) -> gf.Component:
    """
    Generates a metasurface array based on a grayscale image.
    
    Args:
        image_path: Path to the input image.
        output_gds: Path to save the output GDS file. If None, does not save.
        pitch_x: Periodicity in X direction (um).
        pitch_y: Periodicity in Y direction (um).
        cell_function: Function to generate unit cell (e.g., cell_rectangle).
        value_map_func: Function to map pixel value to cell parameters.
        pixel_to_nm_scale: Deprecated/Optional.
        invert_image: If True, 0 becomes 255 and vice versa.
        layer: GDS layer to place structures on.
        top_cell_name: Name of the top-level GDS cell.
        flatten: If True, flattens the hierarchy so the top cell contains only polygons.
        
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
    
    print(f"[{top_cell_name}] Loading image: {width}x{height} pixels, Pitch: {pitch_x}x{pitch_y} um")
    
    # 2. Create Top Component
    # Use strict naming to avoid caching collisions if function is called multiple times
    top = gf.Component(top_cell_name)
    
    # 3. Iterate pixels and place cells
    # We can cache identical cells to reduce GDS size/memory usage temporarily before flattening
    cell_cache = {}
    
    for y in range(height):
        for x in range(width):
            val = img_array[y, x]
            
            # Determine cell parameters from pixel value
            if value_map_func:
                kwargs = value_map_func(val)
            else:
                # Default mapping
                kwargs = {"rotation": val * 180.0 / 255.0}
            
            # Ensure layer is passed if not in kwargs
            if "layer" not in kwargs:
                kwargs["layer"] = layer
            
            # Create unique key for caching based on kwargs
            cache_key = tuple(sorted(kwargs.items()))
            
            if cache_key in cell_cache:
                cell = cell_cache[cache_key]
            else:
                cell = cell_function(**kwargs)
                cell_cache[cache_key] = cell
            
            # Calculate position
            pos_x = x * pitch_x
            pos_y = (height - 1 - y) * pitch_y 
            
            ref = top << cell
            ref.move((pos_x, pos_y))
            
    if flatten:
        print(f"[{top_cell_name}] Flattening hierarchy...")
        top.flatten()
        
    # 4. Save GDS if output_gds is provided
    if output_gds:
        top.write_gds(output_gds)
        print(f"[{top_cell_name}] GDS saved to: {output_gds}")
    
    return top


# =============================================================================
# EXAMPLES AND DEMO
# =============================================================================

if __name__ == "__main__":
    # Settings
    # Each type occupies 300x300 um
    # Total array 900x900 um (3x3 grid)
    BLOCK_SIZE_UM = 300
    PITCH_UM = 2.0 # 2 um pitch (allows for larger features ~500nm) -> 50x50 pixels per block
    PIXELS = int(BLOCK_SIZE_UM / PITCH_UM)
    
    # Use the Great Wave image
    input_image_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "MyLayoutTemplate", "The_Great_Wave.jpg")
    processed_image_path = "great_wave_resized.png"
    
    output_gds_name = "metasurface_3x3_great_wave.gds"
    flatten_cells = True # Each 100x100 block will be flattened
    
    # Load and resize the image
    if os.path.exists(input_image_path):
        print(f"Loading image from: {input_image_path}")
        img = Image.open(input_image_path).convert('L')
        img = img.resize((PIXELS, PIXELS), Image.Resampling.LANCZOS)
        img.save(processed_image_path)
        demo_image_path = processed_image_path
        print(f"Resized image saved to: {demo_image_path} ({PIXELS}x{PIXELS})")
    else:
        print(f"Warning: {input_image_path} not found. Falling back to gradient.")
        demo_image_path = "gradient_resized.png"
        gradient = np.zeros((PIXELS, PIXELS), dtype=np.uint8)
        for i in range(PIXELS):
            gradient[:, i] = int(i * 255 / (PIXELS - 1))
        Image.fromarray(gradient).save(demo_image_path)
        print(f"Created test image: {demo_image_path} ({PIXELS}x{PIXELS})")
    
    # Create master container (300x300 um)
    main_container = gf.Component("Metasurface_3x3_Master")
    
    # Define the 9 modes for the 3x3 grid
    # Grid Layout:
    # 6 7 8
    # 3 4 5
    # 0 1 2
    
    modes = []
    
    # --- Mode 0: Rotating Rectangles (PB) ---
    modes.append({
        "name": "M0_Rect_PB",
        "func": cell_rectangle,
        "map": lambda val: {"length": 1.5, "width": 0.5, "rotation": val * 180.0 / 255.0}
    })
    
    # --- Mode 1: Variable Circles (Prop) ---
    modes.append({
        "name": "M1_Circle_Var",
        "func": cell_variable_size,
        "map": lambda val: {"shape": "circle", "size": 0.5 + (val/255.0)*(1.8-0.5)}
    })
    
    # --- Mode 2: Rotating Split Ring ---
    modes.append({
        "name": "M2_SRR_Rot",
        "func": cell_split_ring,
        "map": lambda val: {"radius": 0.8, "width": 0.5, "gap_angle": 45, "rotation": val * 360.0 / 255.0}
    })
    
    # --- Mode 3: Rotating Ellipse ---
    modes.append({
        "name": "M3_Ellipse_PB",
        "func": cell_ellipse,
        "map": lambda val: {"major_axis": 1.5, "minor_axis": 0.6, "rotation": val * 180.0 / 255.0}
    })
    
    # --- Mode 4: Clock Structure (Varying Angle) ---
    modes.append({
        "name": "M4_Clock_Angle",
        "func": cell_clock,
        "map": lambda val: {"arm_length": 0.8, "arm_width": 0.5, "angle": 10 + (val/255.0)*(170), "rotation": 0}
    })
    
    # --- Mode 5: T-Shape (Rotating) ---
    modes.append({
        "name": "M5_TShape_PB",
        "func": cell_t_shape,
        "map": lambda val: {"length_top": 1.5, "width_top": 0.5, "length_stem": 1.2, "width_stem": 0.5, "rotation": val * 180.0 / 255.0}
    })
    
    # --- Mode 6: Variable Square ---
    modes.append({
        "name": "M6_Square_Var",
        "func": cell_variable_size,
        "map": lambda val: {"shape": "square", "size": 0.5 + (val/255.0)*(1.8-0.5), "rotation": 0}
    })
    
    # --- Mode 7: Split Ring (Varying Gap Angle) ---
    modes.append({
        "name": "M7_SRR_Gap",
        "func": cell_split_ring,
        "map": lambda val: {"radius": 0.8, "width": 0.5, "gap_angle": 10 + (val/255.0)*340, "rotation": 0}
    })
    
    # --- Mode 8: Cross/Rect Orthogonal (Simulated with Rect for now, different params) ---
    # Just another rectangle variant, thicker
    modes.append({
        "name": "M8_Rect_Thick",
        "func": cell_rectangle,
        "map": lambda val: {"length": 1.5, "width": 0.8, "rotation": val * 180.0 / 255.0}
    })
    
    # Generate and Place
    for i, mode in enumerate(modes):
        print(f"\n--- Generating {mode['name']} ({i+1}/9) ---")
        
        # Grid position (3x3)
        # col = i % 3
        # row = i // 3
        
        col = i % 3
        row = i // 3
        
        x_offset = col * BLOCK_SIZE_UM
        y_offset = row * BLOCK_SIZE_UM
        
        # Generate Component
        c = generate_metasurface_from_image(
            image_path=demo_image_path,
            output_gds=None,
            pitch_x=PITCH_UM,
            pitch_y=PITCH_UM,
            cell_function=mode["func"],
            value_map_func=mode["map"],
            top_cell_name=mode["name"],
            flatten=flatten_cells
        )
        
        # Add to master
        ref = main_container << c
        ref.move((x_offset, y_offset))
        print(f"Placed at ({x_offset}, {y_offset})")

    # Save Master
    print(f"\nWriting master GDS: {output_gds_name}")
    main_container.write_gds(output_gds_name)
    print("Done!")
