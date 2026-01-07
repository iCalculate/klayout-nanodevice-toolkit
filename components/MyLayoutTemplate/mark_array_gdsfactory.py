
import gdsfactory as gf
import string
import numpy as np

def index_to_letters(idx: int) -> str:
    """
    Convert an index to letter combination (A-Z, AA-ZZ, AAA-ZZZ, etc.).
    
    Args:
        idx: Zero-based index
        
    Returns:
        Letter combination string (A, B, ..., Z, AA, AB, ..., AZ, BA, ...)
    """
    if idx < 26:
        return string.ascii_uppercase[idx]
    else:
        # For indices >= 26, use multiple letters
        # 26 -> AA, 27 -> AB, ..., 51 -> AZ, 52 -> BA, etc.
        result = ""
        idx += 1  # Convert to 1-based for calculation
        while idx > 0:
            idx -= 1  # Convert back to 0-based for modulo
            result = string.ascii_uppercase[idx % 26] + result
            idx //= 26
        return result

def create_mark(
    mark_type: str = "cross",
    mark_size: float = 50.0,
    mark_width: float = 10.0,
    layer: tuple = (3, 0)
) -> gf.Component:
    """
    Create a mark component based on the specified type.
    
    Args:
        mark_type: Type of mark - 'cross', 'chessboard', or 'bone_cross'
        mark_size: Size (length) of the mark in um
        mark_width: Width of the mark lines/features in um
        layer: GDS layer for the mark
        
    Returns:
        gf.Component: The mark component
    """
    c = gf.Component()
    
    if mark_type == "cross":
        # Standard cross mark
        cross_mark = gf.components.cross(
            length=mark_size,
            width=mark_width,
            layer=layer
        )
        c << cross_mark
        
    elif mark_type == "chessboard":
        # Chessboard: two squares in quadrants II and IV with hollow centers
        # The two squares share a corner at the origin (0, 0)
        # Square size: proportional to mark_size
        square_size = mark_size * 0.4
        # Hollow rectangle size: mark_width
        hollow_size = mark_width
        
        # Square in quadrant II (upper left): bottom-right corner at origin
        # If centered=True, center should be at (-square_size/2, square_size/2)
        # Create outer square component
        square1_outer_comp = gf.Component()
        square1_outer = gf.components.rectangle(
            size=(square_size, square_size),
            layer=layer,
            centered=True
        )
        square1_outer_comp << square1_outer
        
        # Create hollow rectangle component (centered at same position)
        square1_hollow_comp = gf.Component()
        square1_hollow = gf.components.rectangle(
            size=(hollow_size, hollow_size),
            layer=layer,
            centered=True
        )
        square1_hollow_comp << square1_hollow
        
        # Perform boolean subtraction
        square1_final = gf.geometry.boolean(
            A=square1_outer_comp,
            B=square1_hollow_comp,
            operation="A-B",
            layer=layer
        )
        ref1 = c << square1_final
        # Move so bottom-right corner is at origin
        ref1.move((-square_size / 2, square_size / 2))
        
        # Square in quadrant IV (lower right): top-left corner at origin
        # If centered=True, center should be at (square_size/2, -square_size/2)
        # Create outer square component
        square2_outer_comp = gf.Component()
        square2_outer = gf.components.rectangle(
            size=(square_size, square_size),
            layer=layer,
            centered=True
        )
        square2_outer_comp << square2_outer
        
        # Create hollow rectangle component (centered at same position)
        square2_hollow_comp = gf.Component()
        square2_hollow = gf.components.rectangle(
            size=(hollow_size, hollow_size),
            layer=layer,
            centered=True
        )
        square2_hollow_comp << square2_hollow
        
        # Perform boolean subtraction
        square2_final = gf.geometry.boolean(
            A=square2_outer_comp,
            B=square2_hollow_comp,
            operation="A-B",
            layer=layer
        )
        ref2 = c << square2_final
        # Move so top-left corner is at origin
        ref2.move((square_size / 2, -square_size / 2))
        
    elif mark_type == "bone_cross":
        # Bone cross: a cross with thickened ends (like a bone shape)
        # size: overall shape size (total length of each arm)
        # width: external line width (width at ends)
        # internal width: width / 2
        # internal length: (width + size) / 2
        
        total_length = mark_size  # Total length of each arm
        external_width = mark_width  # Width at ends
        internal_width = mark_width / 2  # Width at center
        internal_length = (mark_width + mark_size) / 2  # Length of center part
        
        # Calculate end length: (total_length - internal_length) / 2
        end_length = (total_length - internal_length) / 2
        
        # Create horizontal arm
        # Center rectangle (thinner)
        h_center = gf.components.rectangle(
            size=(internal_length, internal_width),
            layer=layer,
            centered=True
        )
        ref_h_center = c << h_center
        ref_h_center.movex(0)
        
        # Left end (thicker)
        h_left = gf.components.rectangle(
            size=(end_length, external_width),
            layer=layer,
            centered=True
        )
        ref_h_left = c << h_left
        ref_h_left.movex(-(internal_length + end_length) / 2)
        
        # Right end (thicker)
        h_right = gf.components.rectangle(
            size=(end_length, external_width),
            layer=layer,
            centered=True
        )
        ref_h_right = c << h_right
        ref_h_right.movex((internal_length + end_length) / 2)
        
        # Create vertical arm
        # Center rectangle (thinner)
        v_center = gf.components.rectangle(
            size=(internal_width, internal_length),
            layer=layer,
            centered=True
        )
        ref_v_center = c << v_center
        ref_v_center.movey(0)
        
        # Bottom end (thicker)
        v_bottom = gf.components.rectangle(
            size=(external_width, end_length),
            layer=layer,
            centered=True
        )
        ref_v_bottom = c << v_bottom
        ref_v_bottom.movey(-(internal_length + end_length) / 2)
        
        # Top end (thicker)
        v_top = gf.components.rectangle(
            size=(external_width, end_length),
            layer=layer,
            centered=True
        )
        ref_v_top = c << v_top
        ref_v_top.movey((internal_length + end_length) / 2)
        
    else:
        # Default to cross if unknown type
        cross_mark = gf.components.cross(
            length=mark_size,
            width=mark_width,
            layer=layer
        )
        c << cross_mark
    
    return c

def generate_mark_array(
    sample_width: float = 10000.0,
    sample_height: float = 10000.0,
    active_width: float = 8000.0,
    active_height: float = 8000.0,
    mark_width: float = 10.0,
    mark_size: float = 50.0,
    mark_pitch_x: float = 500.0,
    mark_pitch_y: float = 500.0,
    mark_type: str = "cross",
    label_interval: int = 4,
    layer_mechanical: tuple = (1, 0),
    layer_active: tuple = (2, 0),
    layer_mark: tuple = (3, 0),
    label_offset: tuple = None,
    label_size: float = 40.0,
) -> gf.Component:
    """
    Generates a layout with a mechanical layer, active area layer, and a mark array with labels.

    Args:
        sample_width: Width of the sample (Layer 1) in um. Default 10mm.
        sample_height: Height of the sample (Layer 1) in um. Default 10mm.
        active_width: Width of the active area (Layer 2) in um. Default 8mm.
        active_height: Height of the active area (Layer 2) in um. Default 8mm.
        mark_width: Width of the mark lines/features in um.
        mark_size: Size (length) of the mark in um.
        mark_pitch_x: Horizontal pitch between marks in um.
        mark_pitch_y: Vertical pitch between marks in um.
        mark_type: Type of mark - 'cross' (standard cross), 'chessboard' (two squares in quadrants II and IV), 
                   or 'bone_cross' (cross with thickened ends). Default 'cross'.
        label_interval: Generate a label every N marks.
        layer_mechanical: GDS layer for the mechanical edge (sample boundary).
        layer_active: GDS layer for the active area.
        layer_mark: GDS layer for the marks and labels.
        label_offset: (x, y) offset for the label relative to the mark center. 
                      If None, defaults to (mark_size, mark_size * 0.4).
        label_size: Font size for the labels in um. Default 40.0.
    """
    c = gf.Component("mark_array_sample")
    
    if label_offset is None:
        label_offset = (mark_size, mark_size * 0.4)

    # 1. Layer 1: Sample Mechanical Edge
    # Centered at (0,0)
    sample_rect = c << gf.components.rectangle(
        size=(sample_width, sample_height), 
        layer=layer_mechanical,
        centered=True
    )

    # 2. Layer 2: Effective/Active Area
    # Centered at (0,0)
    active_rect = c << gf.components.rectangle(
        size=(active_width, active_height), 
        layer=layer_active,
        centered=True
    )

    # 3. Layer 3: Mark Array and Labels
    # Create the base mark based on mark_type
    base_mark = create_mark(
        mark_type=mark_type,
        mark_size=mark_size,
        mark_width=mark_width,
        layer=layer_mark
    )

    # Calculate number of marks that fit in the active area
    # We want them inside the active area.
    # Let's assume the grid is centered in the active area.
    
    # Available space
    nx = int(active_width // mark_pitch_x)
    ny = int(active_height // mark_pitch_y)
    
    # Determine the starting position to center the grid
    # Grid dimensions
    grid_width = (nx - 1) * mark_pitch_x
    grid_height = (ny - 1) * mark_pitch_y
    
    start_x = -grid_width / 2
    start_y = -grid_height / 2

    # Calculate maximum label indices to determine padding
    max_row_label_idx = (ny - 1) // label_interval
    max_col_label_idx = (nx - 1) // label_interval
    
    # Determine number of digits needed for column numbers (with zero padding)
    max_col_num = max_col_label_idx + 1
    num_digits = len(str(max_col_num)) if max_col_num > 0 else 1

    # Loop to place marks and labels
    for i in range(nx): # Columns (x)
        for j in range(ny): # Rows (y)
            x = start_x + i * mark_pitch_x
            y = start_y + j * mark_pitch_y
            
            # Place Mark
            ref = c << base_mark
            ref.move((x, y))
            
            # Place Label every 'label_interval' marks
            # We want labels like A1, A2... where A corresponds to Row index / interval, 1 to Col index / interval
            # Or following user example: "Every 5 (row or column) generate label using A1, A2, B1..."
            # Interpretation: 
            # If we are at a grid point that is a multiple of label_interval
            if i % label_interval == 0 and j % label_interval == 0:
                # Calculate label indices
                row_label_idx = j // label_interval
                col_label_idx = i // label_interval
                
                # Convert row index to letters (A, B, ..., Z, AA, AB, ...)
                row_char = index_to_letters(row_label_idx)
                
                # Convert column index to number with zero padding
                col_num = str(col_label_idx + 1).zfill(num_digits)
                
                label_text_str = f"{row_char}{col_num}"
                
                # Generate text component
                text_comp = gf.components.text(
                    text=label_text_str,
                    size=label_size,
                    layer=layer_mark,
                    justify='center'
                )
                
                text_ref = c << text_comp
                # Place label near the mark. 
                # e.g. Quadrant 1 (top right) or just offset
                text_ref.move((x + label_offset[0], y + label_offset[1]))

    return c

if __name__ == "__main__":
    # Generate and show with different mark types
    # Example 1: Standard cross mark (default)
    c1 = generate_mark_array(mark_type="cross")
    c1.show()
    c1.write_gds("mark_array_cross.gds")
    print("Cross mark array written to mark_array_cross.gds")
    
    # Example 2: Chessboard mark
    c2 = generate_mark_array(
        mark_type="chessboard",
        mark_width=0.0,
        mark_size=5.0,
        mark_pitch_x=120.0,
        mark_pitch_y=120.0,
        label_interval=1,
        label_size=5.0
    )
    c2.show()
    c2.write_gds("mark_array_chessboard.gds")
    print("Chessboard mark array written to mark_array_chessboard.gds")
    
    # Example 3: Bone cross mark
    c3 = generate_mark_array(mark_type="bone_cross")
    c3.show()
    c3.write_gds("mark_array_bone_cross.gds")
    print("Bone cross mark array written to mark_array_bone_cross.gds")

