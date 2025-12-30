
import gdsfactory as gf
import numpy as np
from PIL import Image

def image_to_parameter_matrix(
    image_path: str,
    target_resolution: tuple,
    value_range: tuple = (0.0, 1.0),
    mode: str = 'grayscale', # 'grayscale', 'hue', 'saturation', 'value'
    inverse: bool = False,
    save_debug_image: bool = False
) -> np.ndarray:
    """
    Converts an image to a parameter matrix (numpy array).
    
    Args:
        image_path: Path to the input image.
        target_resolution: (nx, ny) size of the output matrix.
        value_range: (min_val, max_val) to map pixel intensity to.
        mode: Extraction mode. 'grayscale' (luminance), 'hue' (color), 'saturation', 'value' (brightness).
        inverse: If True, high pixel intensity maps to min_val, low to max_val.
        save_debug_image: If True, saves the resized image for inspection.
    
    Returns:
        np.ndarray of shape (nx, ny) with mapped values.
    """
    try:
        img = Image.open(image_path)
    except Exception as e:
        print(f"Error loading image: {e}")
        return None
        
    # Resize to target resolution (nx, ny) BEFORE color conversion to save processing
    # or AFTER? Resizing RGB is better than resizing Hue channel due to cyclic nature of Hue?
    # Actually, interpolating Hue is tricky (359 -> 1 should not go through 180).
    # But for simple logos, maybe standard resize is fine. 
    # Let's resize first in RGB then convert, or convert then resize.
    # Standard resize on RGB handles edges better usually.
    img = img.resize(target_resolution, Image.Resampling.NEAREST)
    
    if save_debug_image:
        # Save debug image before flipping (so it looks upright in viewer)
        # We append mode and resolution to filename
        debug_filename = f"debug_resized_{mode}_{target_resolution[0]}x{target_resolution[1]}.png"
        img.save(debug_filename)
        print(f"Saved debug image to {debug_filename}")

    # Flip vertically to match layout coordinates (y up) vs Image (y down)
    img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    
    if mode == 'grayscale':
        # Convert to grayscale
        img = img.convert('L')
        # Get data
        data = np.array(img).astype(float)
        # Normalize 0-255 to 0-1
        norm_data = data / 255.0
        
    elif mode in ['hue', 'saturation', 'value']:
        # Convert to HSV
        img = img.convert('HSV')
        h, s, v = img.split()
        
        if mode == 'hue':
            data = np.array(h).astype(float)
            # Hue in Pillow is 0-255 (mapped from 0-360)
            norm_data = data / 255.0
        elif mode == 'saturation':
            data = np.array(s).astype(float)
            norm_data = data / 255.0
        elif mode == 'value':
            data = np.array(v).astype(float)
            norm_data = data / 255.0
    else:
        print(f"Unknown mode: {mode}")
        return None
    
    # img_array shape is (ny, nx) -> (rows, cols)
    # We need to transpose to match (nx, ny) for grid generation [col, row]
    norm_data = norm_data.T
    
    if inverse:
        norm_data = 1.0 - norm_data
        
    # Map to value_range
    min_val, max_val = value_range
    mapped_array = min_val + norm_data * (max_val - min_val)
    
    return mapped_array

def create_grating_cell(
    width: float,
    gap: float,
    angle: float,
    size: float,
    layer: tuple = (1, 0)
) -> gf.Component:
    """
    Creates a square cell filled with a grating (lines).
    
    Args:
        width: Line width (um).
        gap: Space between lines (um).
        angle: Angle of the lines (degrees).
        size: Size of the square cell (um).
        layer: Layer for the grating.
    """
    # Name the component uniquely based on parameters to avoid caching collisions if parameters are close
    # or use unnamed component if caching not needed/handled by caller loop
    c = gf.Component()
    
    period = width + gap
    
    # To ensure we cover the whole rotated square, we need a larger area of lines
    # Diagonal of the square
    diagonal = size * np.sqrt(2)
    
    # Number of lines needed to cover the diagonal
    # We center the grating lines
    num_lines = int(np.ceil(diagonal / period)) + 2
    
    # Generate lines centered at (0,0)
    # Length of lines should be at least diagonal
    line_length = diagonal
    
    # Create a temporary component for the raw grating lines
    # We draw them horizontal first, then rotate
    grating_raw = gf.Component()
    
    # Center position calculations
    total_height = (num_lines - 1) * period + width
    start_y = -total_height / 2 + width / 2
    
    rect = gf.components.rectangle(size=(line_length, width), layer=layer, centered=True)
    
    for i in range(num_lines):
        y = start_y + i * period
        ref = grating_raw << rect
        ref.movey(y)
        
    # Create the rotated grating component (Operand A)
    c_rotated = gf.Component()
    ref_rot = c_rotated << grating_raw
    ref_rot.rotate(angle)
    
    # Create the square aperture/mask (Operand B)
    c_mask = gf.Component()
    c_mask << gf.components.rectangle(size=(size, size), layer=layer, centered=True)
    
    # Perform boolean AND
    # We return the result of the boolean operation
    c_final = gf.geometry.boolean(A=c_rotated, B=c_mask, operation="and", layer=layer)
    
    return c_final

def generate_grating_array(
    sample_width: float = 10000.0,
    sample_height: float = 10000.0,
    active_width: float = 8000.0,
    active_height: float = 8000.0,
    cell_size: float = 500.0,
    linewidth: float = 2.0,
    spacing_range: tuple = (2.0, 10.0), # Min/Max Gap
    angle_range: tuple = (0.0, 90.0),   # Min/Max Angle
    spacing_matrix: np.ndarray = None,  # Optional override for spacing
    angle_matrix: np.ndarray = None,    # Optional override for angle
    layer_mechanical: tuple = (1, 0),
    layer_active: tuple = (2, 0),
    layer_grating: tuple = (3, 0),
    name: str = "grating_array_sample"
) -> gf.Component:
    """
    Generates a layout with a mechanical layer, active area layer, and an array of grating cells.
    
    The array dimensions are calculated to fit within the active area.
    Parameters vary across the array:
    - Default: Rows (Y) gradient in spacing, Cols (X) gradient in angle.
    - If matrices are provided, they override the gradients.
    
    Args:
        sample_width/height: Dimensions of Layer 1 (Mechanical).
        active_width/height: Dimensions of Layer 2 (Active Area).
        cell_size: Size of the square unit cell.
        linewidth: Fixed line width for the grating lines.
        spacing_range: (min_gap, max_gap) for default gradient.
        angle_range: (min_angle, max_angle) for default gradient.
        spacing_matrix: Optional (nx, ny) numpy array of spacing values.
        angle_matrix: Optional (nx, ny) numpy array of angle values.
        layer_mechanical: Layer for sample boundary.
        layer_active: Layer for active area.
        layer_grating: Layer for grating structure.
        name: Name of the component.
    """
    c = gf.Component(name)

    # 1. Layer 1: Sample Mechanical Edge
    c << gf.components.rectangle(
        size=(sample_width, sample_height), 
        layer=layer_mechanical,
        centered=True
    )

    # 2. Layer 2: Effective/Active Area
    c << gf.components.rectangle(
        size=(active_width, active_height), 
        layer=layer_active,
        centered=True
    )

    # 3. Grating Array
    # Calculate grid dimensions
    nx = int(active_width // cell_size)
    ny = int(active_height // cell_size)
    
    if nx == 0 or ny == 0:
        print("Warning: Cell size is too large for the active area.")
        return c

    # Calculate centered start position
    grid_width = nx * cell_size
    grid_height = ny * cell_size
    
    start_x = -grid_width / 2 + cell_size / 2
    start_y = -grid_height / 2 + cell_size / 2

    # Prepare Parameter Matrices
    # If matrix not provided, generate default gradients
    
    # Angle Matrix (nx, ny)
    if angle_matrix is None:
        angle_matrix = np.zeros((nx, ny))
        if nx > 1:
            angles = np.linspace(angle_range[0], angle_range[1], nx)
        else:
            angles = [angle_range[0]]
        
        # Fill columns with same angle
        for i in range(nx):
            angle_matrix[i, :] = angles[i]
    else:
        # Validate shape
        if angle_matrix.shape != (nx, ny):
            print(f"Warning: angle_matrix shape {angle_matrix.shape} does not match grid ({nx}, {ny}). Resizing not implemented here.")
            # Could implement resize here too, but assume caller handles it via helper
            
    # Spacing Matrix (nx, ny)
    if spacing_matrix is None:
        spacing_matrix = np.zeros((nx, ny))
        if ny > 1:
            spacings = np.linspace(spacing_range[0], spacing_range[1], ny)
        else:
            spacings = [spacing_range[0]]
            
        # Fill rows with same spacing
        for j in range(ny):
            spacing_matrix[:, j] = spacings[j]
    else:
        if spacing_matrix.shape != (nx, ny):
             print(f"Warning: spacing_matrix shape {spacing_matrix.shape} does not match grid ({nx}, {ny}).")

    print(f"Generating {nx}x{ny} array ({nx*ny} cells)...")

    # Loop to generate and place cells
    for i in range(nx): # Col index
        for j in range(ny): # Row index
            
            angle = angle_matrix[i, j]
            spacing = spacing_matrix[i, j]
            
            # Create unique cell for this parameter set
            cell = create_grating_cell(
                width=linewidth,
                gap=spacing,
                angle=angle,
                size=cell_size,
                layer=layer_grating
            )
            
            ref = c << cell
            
            # Position
            x = start_x + i * cell_size
            y = start_y + j * cell_size
            ref.move((x, y))
            
    return c

if __name__ == "__main__":
    # Example 1: Default Gradient
    c = generate_grating_array(
        cell_size=1000.0,
        linewidth=5.0,
        spacing_range=(5.0, 20.0),
        angle_range=(0.0, 90.0),
        name="grating_array_gradient"
    )
    c.show()
    c.write_gds("grating_array_sample.gds")
    print("Layout written to grating_array_sample.gds")
    
    # Example 2: From Image
    image_path = "components/MyLayoutTemplate/PixelArt-KIRBY.jpg"
    # Fallback to dummy if not found, just for robustness in script
    import os
    if not os.path.exists(image_path):
        print(f"Image {image_path} not found, creating dummy.")
        image_path = "temp_test_pattern.png"
        img_size = (32, 32)
        dummy_img = Image.new('RGB', img_size) # RGB for Hue
        # Create a gradient pattern
        for x in range(img_size[0]):
            for y in range(img_size[1]):
                # Hue gradient in x, Brightness in y
                hue = int(x/img_size[0] * 255)
                val = int(y/img_size[1] * 255)
                dummy_img.putpixel((x, y), (hue, 255, val)) # This is actually RGB values, not HSV
                # To verify HSV logic we need real image or proper HSV->RGB conversion. 
                # But for dummy fallback this is fine.
        dummy_img.save("temp_test_pattern.png")
    
    # Calculate grid size for 8000um active area and 200um cell
    active_width = 8000.0
    cell_size = active_width/32.0 # Smaller cell size for better resolution
    nx = int(active_width // cell_size)
    ny = int(active_width // cell_size)
    
    # Generate Angle Matrix from Hue
    # Map Hue (0-360 roughly) to Angle (0-180) or (0-360)
    # Let's map to 0-180 since grating is symmetric
    angle_mat = image_to_parameter_matrix(
        image_path, 
        target_resolution=(nx, ny),
        value_range=(0.0, 180.0),
        mode='hue',
        save_debug_image=True
    )
    
    # Generate Spacing Matrix from Grayscale (Luminance)
    # Darker = ? Lighter = ? 
    # Usually we want contrast. Let's say darker = smaller gap (denser), lighter = larger gap.
    # range 2um to 20um
    spacing_mat = image_to_parameter_matrix(
        image_path,
        target_resolution=(nx, ny),
        value_range=(2.0, 8.0),
        mode='grayscale',
        inverse=False,
        save_debug_image=False
    )
    
    c_img = generate_grating_array(
        sample_width=10000.0,
        active_width=active_width,
        cell_size=cell_size,
        linewidth=2.0,
        angle_matrix=angle_mat,
        spacing_matrix=spacing_mat,
        name="grating_array_from_image"
    )
    c_img.show()
    c_img.write_gds("grating_array_from_image.gds")
    print("Layout written to grating_array_from_image.gds")
    
    # Clean up dummy
    if image_path == "temp_test_pattern.png" and os.path.exists("temp_test_pattern.png"):
        os.remove("temp_test_pattern.png")
