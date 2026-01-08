
import gdsfactory as gf
import numpy as np
import string

def index_to_letters(idx: int) -> str:
    """
    Convert an index to letter combination (A-Z, AA-ZZ, etc.).
    """
    if idx < 26:
        return string.ascii_uppercase[idx]
    else:
        result = ""
        idx += 1
        while idx > 0:
            idx -= 1
            result = string.ascii_uppercase[idx % 26] + result
            idx //= 26
        return result

def create_bonecross(
    size: float = 50.0,
    width: float = 10.0,
    layer: tuple = (1, 0)
) -> gf.Component:
    """
    Create a bonecross mark (cross with thickened ends).
    """
    c = gf.Component()
    
    total_length = size
    external_width = width
    internal_width = width / 2.0
    internal_length = (width + size) / 2.0
    
    end_length = (total_length - internal_length) / 2.0
    
    # Horizontal Arm
    h_center = c << gf.components.rectangle(size=(internal_length, internal_width), layer=layer, centered=True)
    h_left = c << gf.components.rectangle(size=(end_length, external_width), layer=layer, centered=True)
    h_left.movex(-(internal_length + end_length) / 2.0)
    h_right = c << gf.components.rectangle(size=(end_length, external_width), layer=layer, centered=True)
    h_right.movex((internal_length + end_length) / 2.0)
    
    # Vertical Arm
    v_center = c << gf.components.rectangle(size=(internal_width, internal_length), layer=layer, centered=True)
    v_bottom = c << gf.components.rectangle(size=(external_width, end_length), layer=layer, centered=True)
    v_bottom.movey(-(internal_length + end_length) / 2.0)
    v_top = c << gf.components.rectangle(size=(external_width, end_length), layer=layer, centered=True)
    v_top.movey((internal_length + end_length) / 2.0)
    
    return c

def create_composite_mark(
    main_size: float = 50.0,
    main_width: float = 10.0,
    small_size: float = 15.0,
    small_width: float = 3.0,
    small_offset_dist: float = 35.0,
    layer: tuple = (1, 0),
    is_main_mark: bool = False
) -> gf.Component:
    """
    Create a composite mark:
    - Center: Large crossbone
    - Corners: 4 small crossbones
    
    Args:
        is_main_mark: If True, adds a special feature (e.g. an enclosing frame) to distinguish it.
    """
    c = gf.Component()
    
    # 1. Main Center Crossbone
    c << create_bonecross(size=main_size, width=main_width, layer=layer)
    
    # 2. Small Corner Crossbones
    small_mark = create_bonecross(size=small_size, width=small_width, layer=layer)
    
    for dx in [-1, 1]:
        for dy in [-1, 1]:
            ref = c << small_mark
            ref.move((dx * small_offset_dist, dy * small_offset_dist))
            
    # 3. Special Feature for Main Mark (Top-Left corner of writefield)
    if is_main_mark:
        # Four lines around the mark, aligned with center, not overlapping
        # Effectively a broken frame
        
        # Distance from center to the center of the line segment
        # To align with small marks, we use small_offset_dist
        line_offset = small_offset_dist
        
        # Line dimensions
        # Length matches the mark size, but must be capped to avoid overlapping small marks
        # Small marks are at +/- small_offset_dist. Inner edge is small_offset_dist - small_size/2.
        # Leave a small gap (e.g. 2um)
        max_len = 2 * (small_offset_dist - small_size / 2.0 - 2.0)
        line_length = min(main_size, max_len)
        
        line_width = 2.0 # Thickness of the lines
        
        
        # Top Line (Horizontal)
        top = c << gf.components.rectangle(size=(line_length, line_width), layer=layer, centered=True)
        top.movey(line_offset)
        
        # Bottom Line (Horizontal)
        bot = c << gf.components.rectangle(size=(line_length, line_width), layer=layer, centered=True)
        bot.movey(-line_offset)
        
        # Left Line (Vertical)
        left = c << gf.components.rectangle(size=(line_width, line_length), layer=layer, centered=True)
        left.movex(-line_offset)
        
        # Right Line (Vertical)
        right = c << gf.components.rectangle(size=(line_width, line_length), layer=layer, centered=True)
        right.movex(line_offset)
            
    return c

def create_caliper(
    num_ticks_side: int,
    pitch: float,
    width: float,
    tick_length: float,
    center_tick_length: float = None,
    layer: tuple = (1, 0),
    orientation: str = "horizontal", # horizontal or vertical
    tick_direction: int = 1, # 1 for positive, -1 for negative direction relative to the axis
    limit_length: float = None # Maximum total span allowed (to clip ticks that exceed this)
) -> gf.Component:
    """
    Create a caliper component with ticks.
    
    Args:
        num_ticks_side: Number of ticks on each side of the center tick
        pitch: Pitch (interval) between ticks
        width: Width of the ticks (thickness of lines)
        tick_length: Length of regular ticks
        center_tick_length: Length of the center tick (if None, same as regular)
        orientation: 'horizontal' (ticks vertical) or 'vertical' (ticks horizontal)
        tick_direction: Direction of ticks relative to the axis (1 or -1)
        limit_length: If provided, ticks outside [-limit/2, limit/2] are skipped.
    """
    c = gf.Component()
    
    # Loop to create ticks
    # Ticks are placed symmetric around the center
    # Total ticks = 2 * num_ticks_side + 1
    
    for i in range(-num_ticks_side, num_ticks_side + 1):
        pos = i * pitch
        
        # Check limit
        if limit_length is not None:
            if abs(pos) > limit_length / 2.0:
                continue
        
        # Determine current tick length
        current_len = tick_length
        if center_tick_length is not None and i == 0:
            current_len = center_tick_length
            
        if orientation == "horizontal":
            # Ticks are vertical rectangles
            tick = c << gf.components.rectangle(size=(width, current_len), layer=layer, centered=True)
            # Center of tick is at (0, 0) relative to tick rect
            # We want it to start at 0 and go to tick_direction * len
            # Shift by tick_direction * len / 2
            tick.move((pos, tick_direction * current_len / 2.0))
            
        else: # vertical
            # Ticks are horizontal rectangles
            tick = c << gf.components.rectangle(size=(current_len, width), layer=layer, centered=True)
            # Shift by tick_direction * len / 2 in X
            tick.move((tick_direction * current_len / 2.0, pos))
            
    return c

def generate_writefield_array(
    sample_width: float = 10000.0,
    sample_height: float = 10000.0,
    active_width: float = 8000.0,
    active_height: float = 8000.0,
    writefield_size: float = 1000.0,
    
    # Mark parameters
    mark_main_size: float = 60.0,
    mark_main_width: float = 5.0,
    mark_small_size: float = 15.0,
    mark_small_width: float = 2.0,
    mark_small_dist: float = 35.0,
    
    # Mark placement parameters
    mark_offset_from_corner: tuple = (60.0, 60.0),
    
    # Label parameters
    label_size: float = 15.0,
    label_offset: tuple = (0.0, 50.0), # Distance from mark center to label center (x, y)
    
    # Caliper parameters
    enable_caliper: bool = True,
    caliper_width: float = 2.0,
    
    # Top/Right Caliper (Large pitch)
    caliper_top_right_pitch: float = 5.0,
    caliper_top_right_num_side: int = 10,
    caliper_top_right_tick_length: float = 10.0,
    caliper_top_right_center_length: float = 20.0,
    
    # Bottom/Left Caliper (Small pitch)
    caliper_bottom_left_pitch: float = 5.1,
    caliper_bottom_left_num_side: int = 10, 
    caliper_bottom_left_tick_length: float = 10.0,
    caliper_bottom_left_center_length: float = 20.0,
    
    # Layers
    layer_mechanical: tuple = (1, 0),
    layer_active: tuple = (2, 0),
    layer_mark: tuple = (3, 0),
) -> gf.Component:
    """
    Generates an array of EBL write fields with alignment marks and labels.
    """
    c = gf.Component("mark_writefield_array")

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

    # 3. Create Marks
    # Standard composite mark
    mark_standard = create_composite_mark(
        main_size=mark_main_size,
        main_width=mark_main_width,
        small_size=mark_small_size,
        small_width=mark_small_width,
        small_offset_dist=mark_small_dist,
        layer=layer_mark,
        is_main_mark=False
    )
    
    # Main composite mark (with special feature)
    mark_main = create_composite_mark(
        main_size=mark_main_size,
        main_width=mark_main_width,
        small_size=mark_small_size,
        small_width=mark_small_width,
        small_offset_dist=mark_small_dist,
        layer=layer_mark,
        is_main_mark=True
    )

    # 4. Create Calipers (if enabled)
    if enable_caliper:
        # Top Ruler (Horizontal axis, Ticks Down/-1)
        caliper_top = create_caliper(
            num_ticks_side=caliper_top_right_num_side,
            pitch=caliper_top_right_pitch,
            width=caliper_width,
            tick_length=caliper_top_right_tick_length,
            center_tick_length=caliper_top_right_center_length,
            layer=layer_mark,
            orientation="horizontal",
            tick_direction=-1,
            limit_length=writefield_size
        )
        
        # Right Ruler (Vertical axis, Ticks Left/-1)
        caliper_right = create_caliper(
            num_ticks_side=caliper_top_right_num_side,
            pitch=caliper_top_right_pitch,
            width=caliper_width,
            tick_length=caliper_top_right_tick_length,
            center_tick_length=caliper_top_right_center_length,
            layer=layer_mark,
            orientation="vertical",
            tick_direction=-1,
            limit_length=writefield_size
        )
        
        # Bottom Ruler (Horizontal axis, Ticks Up/1)
        caliper_bottom = create_caliper(
            num_ticks_side=caliper_bottom_left_num_side,
            pitch=caliper_bottom_left_pitch,
            width=caliper_width,
            tick_length=caliper_bottom_left_tick_length,
            center_tick_length=caliper_bottom_left_center_length,
            layer=layer_mark,
            orientation="horizontal",
            tick_direction=1,
            limit_length=writefield_size
        )
        
        # Left Ruler (Vertical axis, Ticks Right/1)
        caliper_left = create_caliper(
            num_ticks_side=caliper_bottom_left_num_side,
            pitch=caliper_bottom_left_pitch,
            width=caliper_width,
            tick_length=caliper_bottom_left_tick_length,
            center_tick_length=caliper_bottom_left_center_length,
            layer=layer_mark,
            orientation="vertical",
            tick_direction=1,
            limit_length=writefield_size
        )

    # 5. Tiling Write Fields
    nx = int(np.ceil(active_width / writefield_size))
    ny = int(np.ceil(active_height / writefield_size))
    
    total_grid_width = nx * writefield_size
    total_grid_height = ny * writefield_size
    
    start_x = -total_grid_width / 2.0
    start_y = -total_grid_height / 2.0
    
    ox, oy = mark_offset_from_corner
    
    for i in range(nx):
        for j in range(ny):
            # Write Field Origin (Bottom-Left)
            wf_x = start_x + i * writefield_size
            wf_y = start_y + j * writefield_size
            
            # Center of the write field
            wf_center_x = wf_x + writefield_size / 2.0
            wf_center_y = wf_y + writefield_size / 2.0
            
            # Label Text (e.g., A1, B2)
            # Rows usually A, B, C... (from bottom up or top down? Let's assume bottom up matches loop j)
            # Cols 1, 2, 3...
            row_label = index_to_letters(j)
            col_label = str(i + 1)
            label_text = f"{row_label}{col_label}"
            
            # Define corners for this write field
            # (x, y, is_main_mark_position, label_offset_direction)
            # label_offset_direction: multiplier for (label_distance) in x and y
            
            # Bottom-Left
            pos_BL = (wf_x + ox,                   wf_y + oy)
            # Bottom-Right
            pos_BR = (wf_x + writefield_size - ox, wf_y + oy)
            # Top-Left
            pos_TL = (wf_x + ox,                   wf_y + writefield_size - oy)
            # Top-Right (Main Mark)
            pos_TR = (wf_x + writefield_size - ox, wf_y + writefield_size - oy)
            
            # Place Marks
            # BL
            c.add_ref(mark_standard).move(pos_BL)
            # BR
            c.add_ref(mark_standard).move(pos_BR)
            # TL (Main)
            c.add_ref(mark_main).move(pos_TL)
            # TR 
            c.add_ref(mark_standard).move(pos_TR)
            
            # Place Labels at all 4 corners
            # We place labels towards the *center* of the write field relative to the mark
            # BL mark -> Label at (+, +) relative to mark
            # BR mark -> Label at (-, +) relative to mark
            # TL mark -> Label at (+, -) relative to mark
            # TR mark -> Label at (-, -) relative to mark
            
            label_offsets = [
                (pos_BL, (1, 1)),
                (pos_BR, (-1, 1)),
                (pos_TL, (1, -1)),
                (pos_TR, (-1, -1))
            ]
            
            for (mx, my), (dx, dy) in label_offsets:
                text_comp = gf.components.text(
                    text=label_text,
                    size=label_size,
                    layer=layer_mark,
                    justify='center'
                )
                text_ref = c << text_comp
                # Position label: Mark Center + Direction * Distance
                # Calculate target center position
                tx = mx + dx * label_offset[0]
                ty = my + dy * label_offset[1]
                
                # Center the text at the target position
                # This ensures the "handle" (visual center) of the text is at the calculated position
                if hasattr(text_ref, 'center'):
                    text_ref.center = (tx, ty)
                else:
                    # Fallback for some versions: move by difference between target and current center
                    cur_center = text_ref.center
                    text_ref.move((tx - cur_center[0], ty - cur_center[1]))
            
            # Place Calipers
            if enable_caliper:
                # Top (Large pitch)
                c.add_ref(caliper_top).move((wf_center_x, wf_y + writefield_size))
                # Right (Large pitch)
                c.add_ref(caliper_right).move((wf_x + writefield_size, wf_center_y))
                # Bottom (Small pitch)
                c.add_ref(caliper_bottom).move((wf_center_x, wf_y))
                # Left (Small pitch)
                c.add_ref(caliper_left).move((wf_x, wf_center_y))

    return c

if __name__ == "__main__":
    c = generate_writefield_array()
    c.show()
    c.write_gds("mark_writefield_array.gds")
