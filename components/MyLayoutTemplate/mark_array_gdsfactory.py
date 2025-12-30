
import gdsfactory as gf
import string

def generate_mark_array(
    sample_width: float = 10000.0,
    sample_height: float = 10000.0,
    active_width: float = 8000.0,
    active_height: float = 8000.0,
    mark_width: float = 10.0,
    mark_size: float = 50.0,
    mark_pitch_x: float = 500.0,
    mark_pitch_y: float = 500.0,
    label_interval: int = 4,
    layer_mechanical: tuple = (1, 0),
    layer_active: tuple = (2, 0),
    layer_mark: tuple = (3, 0),
    label_offset: tuple = None,
) -> gf.Component:
    """
    Generates a layout with a mechanical layer, active area layer, and a mark array with labels.

    Args:
        sample_width: Width of the sample (Layer 1) in um. Default 10mm.
        sample_height: Height of the sample (Layer 1) in um. Default 10mm.
        active_width: Width of the active area (Layer 2) in um. Default 8mm.
        active_height: Height of the active area (Layer 2) in um. Default 8mm.
        mark_width: Width of the cross mark lines in um.
        mark_size: Size (length) of the cross mark in um.
        mark_pitch_x: Horizontal pitch between marks in um.
        mark_pitch_y: Vertical pitch between marks in um.
        label_interval: Generate a label every N marks.
        layer_mechanical: GDS layer for the mechanical edge (sample boundary).
        layer_active: GDS layer for the active area.
        layer_mark: GDS layer for the marks and labels.
        label_offset: (x, y) offset for the label relative to the mark center. 
                      If None, defaults to (mark_size, mark_size * 0.4).
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
    # Create the base cross mark
    cross_mark = gf.components.cross(
        length=mark_size,
        width=mark_width,
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

    # Loop to place marks and labels
    for i in range(nx): # Columns (x)
        for j in range(ny): # Rows (y)
            x = start_x + i * mark_pitch_x
            y = start_y + j * mark_pitch_y
            
            # Place Mark
            ref = c << cross_mark
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
                
                # Convert to String (A, B, C... and 1, 2, 3...)
                # Rows: A, B, C... (from bottom to top usually? Or top to bottom?)
                # Let's assume bottom to top A, B, C matching standard Cartesian
                row_char = string.ascii_uppercase[row_label_idx % 26]
                if row_label_idx >= 26:
                    row_char += str(row_label_idx // 26) # Handle overflow simply if needed
                    
                col_num = str(col_label_idx + 1)
                
                label_text_str = f"{row_char}{col_num}"
                
                # Generate text component
                # Size: Let's pick something visible, maybe 80% of spacing or similar to mark size
                # Mark size is 50um. 
                text_comp = gf.components.text(
                    text=label_text_str,
                    size=40,
                    layer=layer_mark,
                    justify='center'
                )
                
                text_ref = c << text_comp
                # Place label near the mark. 
                # e.g. Quadrant 1 (top right) or just offset
                text_ref.move((x + label_offset[0], y + label_offset[1]))

    return c

if __name__ == "__main__":
    # Generate and show with custom label offset
    # Example: Offset label by (40um, 40um) from mark center
    c = generate_mark_array()
    c.show()
    
    # Optionally save to GDS
    output_gds = "mark_array_sample.gds"
    c.write_gds(output_gds)
    print(f"Layout written to {output_gds}")

