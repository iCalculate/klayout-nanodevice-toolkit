
import gdsfactory as gf
import numpy as np
import string

# Cache to store created components and avoid name collisions
_component_cache = {}

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

def get_rect_component(
    width: float, 
    height: float, 
    layer: tuple
) -> gf.Component:
    """
    Get or create a simple rectangle component with a concise name.
    """
    w_str = f"{width:.3g}".replace('.', 'p')
    h_str = f"{height:.3g}".replace('.', 'p')
    name = f"Rect_W{w_str}_H{h_str}_L{layer[0]}_{layer[1]}"
    
    if name in _component_cache:
        return _component_cache[name]
    
    c = gf.Component(name)
    c.add_polygon(
        [
            (-width/2.0, -height/2.0), 
            (width/2.0, -height/2.0), 
            (width/2.0, height/2.0), 
            (-width/2.0, height/2.0)
        ], 
        layer=layer
    )
    
    _component_cache[name] = c
    return c

def get_rect_outline_component(
    width: float,
    height: float,
    line_width: float,
    layer: tuple
) -> gf.Component:
    """
    Get or create a rectangular outline component (using lines instead of fill).
    """
    w_str = f"{width:.3g}".replace('.', 'p')
    h_str = f"{height:.3g}".replace('.', 'p')
    lw_str = f"{line_width:.3g}".replace('.', 'p')
    name = f"RectOutline_W{w_str}_H{h_str}_LW{lw_str}_L{layer[0]}_{layer[1]}"

    if name in _component_cache:
        return _component_cache[name]

    c = gf.Component(name)

    # Top Bar
    c.add_ref(get_rect_component(width, line_width, layer)).move((0, (height - line_width) / 2.0))
    # Bottom Bar
    c.add_ref(get_rect_component(width, line_width, layer)).move((0, -(height - line_width) / 2.0))
    
    # Left and Right Bars (fitting between top and bottom to avoid overlap)
    v_height = height - 2 * line_width
    if v_height > 0:
        # Left
        c.add_ref(get_rect_component(line_width, v_height, layer)).move((-(width - line_width) / 2.0, 0))
        # Right
        c.add_ref(get_rect_component(line_width, v_height, layer)).move(((width - line_width) / 2.0, 0))
    
    _component_cache[name] = c
    return c

def create_bonecross(
    size: float = 50.0,
    width: float = 10.0,
    layer: tuple = (1, 0)
) -> gf.Component:
    """
    Create a bonecross mark (cross with thickened ends).
    """
    name = f"BoneCross_S{size}_W{width}_L{layer[0]}_{layer[1]}"
    
    if name in _component_cache:
        return _component_cache[name]
        
    c = gf.Component(name)
    
    total_length = size
    external_width = width
    internal_width = width / 2.0
    internal_length = (width + size) / 2.0
    
    end_length = (total_length - internal_length) / 2.0
    
    # Helper to add centered rectangle ref
    def add_rect(w, h, dx, dy):
        ref = c << get_rect_component(w, h, layer)
        ref.move((dx, dy))
        return ref
    
    # Horizontal Arm
    add_rect(internal_length, internal_width, 0, 0)
    add_rect(end_length, external_width, -(internal_length + end_length) / 2.0, 0)
    add_rect(end_length, external_width, (internal_length + end_length) / 2.0, 0)
    
    # Vertical Arm
    add_rect(internal_width, internal_length, 0, 0)
    add_rect(external_width, end_length, 0, -(internal_length + end_length) / 2.0)
    add_rect(external_width, end_length, 0, (internal_length + end_length) / 2.0)
    
    _component_cache[name] = c
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
    suffix = "Main" if is_main_mark else "Standard"
    name = f"CompositeMark_{suffix}_M{main_size}_S{small_size}_L{layer[0]}_{layer[1]}"
    
    if name in _component_cache:
        return _component_cache[name]
        
    c = gf.Component(name)
    
    # 1. Main Center Crossbone
    c << create_bonecross(size=main_size, width=main_width, layer=layer)
    
    # 2. Small Corner Crossbones
    small_mark = create_bonecross(size=small_size, width=small_width, layer=layer)
    
    for dx in [-1, 1]:
        for dy in [-1, 1]:
            ref = c << small_mark
            ref.move((dx * small_offset_dist, dy * small_offset_dist))
            
    # 3. Special Feature for Main Mark
    if is_main_mark:
        line_offset = small_offset_dist
        max_len = 2 * (small_offset_dist - small_size / 2.0 - 2.0)
        line_length = min(main_size, max_len)
        line_width = 2.0
        
        def add_line(w, h, dx, dy):
            ref = c << get_rect_component(w, h, layer)
            ref.move((dx, dy))

        add_line(line_length, line_width, 0, line_offset)
        add_line(line_length, line_width, 0, -line_offset)
        add_line(line_width, line_length, -line_offset, 0)
        add_line(line_width, line_length, line_offset, 0)
            
    _component_cache[name] = c
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
    """
    name = f"Caliper_{orientation}_P{pitch}_N{num_ticks_side}_Dir{tick_direction}_L{layer[0]}_{layer[1]}"
    
    if name in _component_cache:
        return _component_cache[name]

    c = gf.Component(name)
    
    center_len = center_tick_length if center_tick_length is not None else tick_length
    
    comp_std = get_rect_component(width, tick_length, layer) if orientation == "horizontal" else get_rect_component(tick_length, width, layer)
    comp_center = get_rect_component(width, center_len, layer) if orientation == "horizontal" else get_rect_component(center_len, width, layer)

    for i in range(-num_ticks_side, num_ticks_side + 1):
        pos = i * pitch
        if limit_length is not None and abs(pos) > limit_length / 2.0:
            continue
        
        is_center = (i == 0)
        current_comp = comp_center if is_center else comp_std
        current_len = center_len if is_center else tick_length
        
        if orientation == "horizontal":
            ref = c << current_comp
            ref.move((pos, tick_direction * current_len / 2.0))
        else: # vertical
            ref = c << current_comp
            ref.move((tick_direction * current_len / 2.0, pos))
            
    _component_cache[name] = c
    return c

def create_corner_marker(
    length: float,
    width: float,
    layer: tuple
) -> gf.Component:
    """
    Create an L-shaped corner marker with optimized structure.
    Structure: Thin near the corner, Thick at the ends.
    Base orientation: Bottom-Left (extending +x and +y from origin (0,0)).
    Aligned to the outer edge (x=0, y=0).
    """
    name = f"CornerL_Len{length}_W{width}_L{layer[0]}_{layer[1]}"
    if name in _component_cache:
        return _component_cache[name]
    
    c = gf.Component(name)
    
    narrow_width = width / 2.0
    tip_length = length / 3.0
    root_length = length - tip_length
    
    # Helper to add rect by corners (BL, TR)
    def add_rect_corners(x1, y1, x2, y2):
        w = abs(x2 - x1)
        h = abs(y2 - y1)
        xc = (x1 + x2) / 2.0
        yc = (y1 + y2) / 2.0
        ref = c << get_rect_component(w, h, layer)
        ref.move((xc, yc))

    # Vertical Arm (Up)
    # Root (Narrow): x in [0, narrow_width], y in [0, root_length]
    add_rect_corners(0, 0, narrow_width, root_length)
    # Tip (Wide): x in [0, width], y in [root_length, length]
    add_rect_corners(0, root_length, width, length)
    
    # Horizontal Arm (Right)
    # Root (Narrow): x in [0, root_length], y in [0, narrow_width]
    # Note: Avoid double drawing the corner square [0, narrow_width]x[0, narrow_width] if possible, 
    # but GDS overlap is fine. To be cleaner, start x from narrow_width? 
    # Let's just overlap, it's safer for continuity.
    add_rect_corners(0, 0, root_length, narrow_width)
    # Tip (Wide): x in [root_length, length], y in [0, width]
    add_rect_corners(root_length, 0, length, width)
    
    _component_cache[name] = c
    return c

def create_single_writefield(
    name: str,
    size: float,
    mark_main: gf.Component,
    mark_standard: gf.Component,
    marker_l: gf.Component,
    caliper_top: gf.Component,
    caliper_right: gf.Component,
    caliper_bottom: gf.Component,
    caliper_left: gf.Component,
    label_text: str,
    label_size: float,
    label_layer: tuple,
    label_offset: tuple,
    mark_offset_from_corner: tuple,
    enable_caliper: bool
) -> gf.Component:
    """
    Create a single write field component containing marks, labels, and calipers.
    Origin (0,0) is the CENTER of the writefield.
    """
    c = gf.Component(name)
    
    h_size = size / 2.0
    ox, oy = mark_offset_from_corner
    
    # Define corners relative to (0,0) center
    pos_BL = (-h_size + ox, -h_size + oy)
    pos_BR = (h_size - ox, -h_size + oy)
    pos_TL = (-h_size + ox, h_size - oy)
    pos_TR = (h_size - ox, h_size - oy)
    
    # Place Marks
    c.add_ref(mark_standard).move(pos_BL)
    c.add_ref(mark_standard).move(pos_BR)
    c.add_ref(mark_main).move(pos_TL)
    c.add_ref(mark_standard).move(pos_TR)
    
    # Place L-Markers at Corners (TL and BR)
    if marker_l:
        # TL Corner (-h_size, h_size) -> Top-Left of Field
        # Base L is Bottom-Left (Extends +x, +y)
        # Rotate -90 (or 270) -> Extends +y (down, x>0 relative), +x (right, y>0 relative)... Wait.
        # Base L: 
        #   |
        #   |___
        # (0,0) is corner.
        
        # Rotate -90:
        #   ___ (0,0)
        #   |
        #   |
        # Extends +x (Right) and -y (Down).
        # This fits TL corner of field perfectly (extends INTO the field).
        # Position: (-h_size, h_size)
        c.add_ref(marker_l).rotate(-90).move((-h_size, h_size))
        
        # BR Corner (h_size, -h_size) -> Bottom-Right of Field
        # Rotate 90:
        #      |
        #      |
        #   ___| (0,0)
        # Extends -x (Left) and +y (Up).
        # This fits BR corner of field perfectly (extends INTO the field).
        # Position: (h_size, -h_size)
        c.add_ref(marker_l).rotate(90).move((h_size, -h_size))

    # Place Labels
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
            layer=label_layer,
            justify='center'
        )
        text_ref = c << text_comp
        
        tx = mx + dx * label_offset[0]
        ty = my + dy * label_offset[1]
        
        if hasattr(text_ref, 'center'):
            text_ref.center = (tx, ty)
        else:
            cur_center = text_ref.center
            text_ref.move((tx - cur_center[0], ty - cur_center[1]))

    # Place Calipers
    if enable_caliper:
        c.add_ref(caliper_top).move((0, h_size))
        c.add_ref(caliper_right).move((h_size, 0))
        c.add_ref(caliper_bottom).move((0, -h_size))
        c.add_ref(caliper_left).move((-h_size, 0))
        
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
    
    # L-Marker parameters
    l_marker_length: float = 100.0,
    l_marker_width: float = 5.0,
    
    # Boundary parameters
    boundary_line_width: float = 10.0,
    
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

    # 1. Layer 1: Sample Mechanical Edge (Outline)
    sample_boundary = get_rect_outline_component(
        width=sample_width, 
        height=sample_height, 
        line_width=boundary_line_width,
        layer=layer_mechanical
    )
    c.add_ref(sample_boundary).move((0, 0))

    # 2. Layer 2: Effective/Active Area (Outline)
    active_boundary = get_rect_outline_component(
        width=active_width, 
        height=active_height, 
        line_width=boundary_line_width,
        layer=layer_active
    )
    c.add_ref(active_boundary).move((0, 0))

    # 3. Create Shared Components (Marks)
    mark_standard = create_composite_mark(
        main_size=mark_main_size,
        main_width=mark_main_width,
        small_size=mark_small_size,
        small_width=mark_small_width,
        small_offset_dist=mark_small_dist,
        layer=layer_mark,
        is_main_mark=False
    )
    
    mark_main = create_composite_mark(
        main_size=mark_main_size,
        main_width=mark_main_width,
        small_size=mark_small_size,
        small_width=mark_small_width,
        small_offset_dist=mark_small_dist,
        layer=layer_mark,
        is_main_mark=True
    )
    
    # Create L-Marker
    marker_l = create_corner_marker(
        length=l_marker_length,
        width=l_marker_width,
        layer=layer_mark
    )

    # 4. Create Shared Components (Calipers)
    caliper_top = None
    caliper_right = None
    caliper_bottom = None
    caliper_left = None

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
    
    for i in range(nx):
        for j in range(ny):
            # Calculate Center of the WriteField
            wf_center_x = start_x + i * writefield_size + writefield_size / 2.0
            wf_center_y = start_y + j * writefield_size + writefield_size / 2.0
            
            row_label = index_to_letters(j)
            col_label = str(i + 1)
            label_text = f"{row_label}{col_label}"
            
            cell_name = f"Field_{label_text}"
            
            wf_cell = create_single_writefield(
                name=cell_name,
                size=writefield_size,
                mark_main=mark_main,
                mark_standard=mark_standard,
                marker_l=marker_l,
                caliper_top=caliper_top,
                caliper_right=caliper_right,
                caliper_bottom=caliper_bottom,
                caliper_left=caliper_left,
                label_text=label_text,
                label_size=label_size,
                label_layer=layer_mark,
                label_offset=label_offset,
                mark_offset_from_corner=mark_offset_from_corner,
                enable_caliper=enable_caliper
            )
            
            c.add_ref(wf_cell).move((wf_center_x, wf_center_y))

    return c

if __name__ == "__main__":
    # Parameters
    GENERATE_MERGED_GDS = True # Set to True to generate a flattened (no hierarchy) GDS file

    c = generate_writefield_array()
    c.show()
    c.write_gds("mark_writefield_array.gds")

    if GENERATE_MERGED_GDS:
        print("Generating merged GDS...")
        c_merged = c.copy()
        c_merged.name = f"{c.name}_merged"
        c_merged.flatten()
        c_merged.write_gds("mark_writefield_array_merged.gds")
