
import gdsfactory as gf
import numpy as np
import string
from datetime import datetime
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
    is_main_mark: bool = False,
    enable_frame: bool = False,
    frame_width: float = None,
    layer_frame: tuple = (4, 0),
    quadrant_indicator: int = None,
    center_coords: tuple = None,
    layer_auto_align: tuple = (61, 0),
    layer_manual_align: tuple = (63, 0),
    enable_alignment_layers: bool = True
) -> gf.Component:
    """
    Create a composite mark:
    - Center: Large crossbone
    - Corners: 4 small crossbones
    - Optional: Crosshair frame (L4) attached to the center mark
    
    Args:
        is_main_mark: If True, adds a special feature (e.g. an enclosing frame) to distinguish it.
        enable_frame: If True, adds a crosshair frame on layer_frame.
        frame_width: Line width of the frame arms.
        layer_frame: Layer for the frame.
        quadrant_indicator: If set (1-4), adds a small circle in the corresponding quadrant of the inner narrowed area.
        center_coords: If provided as (x, y), adds coordinate text labels in the 2nd and 4th quadrants of the inner narrowed area.
        layer_auto_align: Layer for L61 auto alignment marks.
        layer_manual_align: Layer for L63 manual alignment marks.
        enable_alignment_layers: If True, adds L61 and L63 features.
    """
    suffix = "Main" if is_main_mark else "Standard"
    f_suffix = "WFrame" if enable_frame else ""
    q_suffix = f"_Q{quadrant_indicator}" if quadrant_indicator else ""
    coords_suffix = f"_XY{int(center_coords[0])}_{int(center_coords[1])}" if center_coords else ""
    align_suffix = "_Align" if enable_alignment_layers else ""
    name = f"CompositeMark_{suffix}{f_suffix}{q_suffix}{coords_suffix}{align_suffix}_M{main_size}_S{small_size}_L{layer[0]}_{layer[1]}"
    
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

    # 4. Add Crosshair Frame if enabled
    if enable_frame:
        frame = create_crosshair_frame(
            mark_size=main_size,
            mark_width=main_width,
            frame_width=frame_width,
            layer=layer_frame
        )
        c << frame

    # 5. Quadrant Indicator Circle
    if quadrant_indicator:
        # Determine position based on quadrant
        # 1: TR (+,+), 2: TL (-,+), 3: BL (-,-), 4: BR (+,-)
        # Position: "inner narrowed area".
        # internal_width of main cross = main_width / 2.0
        internal_width = main_width
        
        # Place it in the corner formed by the cross arms
        dist = internal_width
        
        # Circle parameters
        circle_radius = internal_width / 4.0
        
        # Coordinates
        qx = 1 if quadrant_indicator in [1, 4] else -1
        qy = 1 if quadrant_indicator in [1, 2] else -1
        
        # Move to position
        cx = qx * dist
        cy = qy * dist
        
        # Create circle (polygon)
        circle = gf.components.circle(radius=circle_radius, layer=layer)
        c.add_ref(circle).move((cx, cy))

    # 6. Coordinate Labels: Q2 (X, right-aligned), Q4 (Y, left-aligned)
    if center_coords is not None:
        cx_val, cy_val = center_coords
        c_text_size = main_size / 25.0 # Slightly larger for better readability
        
        # Use main_width as a reference for spacing
        # Place text slightly away from the center thin arms
        offset = main_width * 1.5
        
        # Q2 (Top-Left): X coordinate, right-aligned
        txt_x_comp = gf.components.text(text=f"{cx_val:+.1f}", size=c_text_size, layer=layer)
        ref_x = c.add_ref(txt_x_comp)
        # Right-aligned: xmax at -offset.
        # Use .y = offset to center the text vertically at the offset, accounting for character height.
        ref_x.xmax = -offset
        ref_x.y = offset + main_width/2
        
        # Q4 (Bottom-Right): Y coordinate, left-aligned
        txt_y_comp = gf.components.text(text=f"{cy_val:+.1f}", size=c_text_size, layer=layer)
        ref_y = c.add_ref(txt_y_comp)
        # Left-aligned: xmin at offset.
        # Use .y = -offset to center the text vertically at -offset, accounting for character height.
        ref_y.xmin = offset
        ref_y.y = -offset - main_width/2

    # 7. Alignment Layers (L61 and L63)
    if enable_alignment_layers:
        # L63 Manual Alignment: Square framing the center bonecross tips
        manual_box = get_rect_component(width=main_size, height=main_size, layer=layer_manual_align)
        c.add_ref(manual_box)
        
        # Calculate wide part center offsets (same as create_bonecross)
        internal_length = (main_width + main_size) / 2.0
        end_length = (main_size - internal_length) / 2.0
        wide_part_offset = (internal_length + end_length) / 2.0
        
        # L61 Auto Alignment: Thin slits perpendicular to arms
        slit_w = 2.0
        slit_h = main_size * 0.6
        
        # Left arm (horizontal) -> Vertical slit
        auto_left = get_rect_component(width=slit_w, height=slit_h, layer=layer_auto_align)
        c.add_ref(auto_left).move((-wide_part_offset, 0))
        
        # Top arm (vertical) -> Horizontal slit
        auto_top = get_rect_component(width=slit_h, height=slit_w, layer=layer_auto_align)
        c.add_ref(auto_top).move((0, wide_part_offset))
            
    _component_cache[name] = c
    return c
            
    _component_cache[name] = c
    return c
            
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

def create_crosshair_frame(
    mark_size: float,
    mark_width: float,
    frame_width: float = None,
    layer: tuple = (4, 0)
) -> gf.Component:
    """
    Create a crosshair frame made of four L-shapes that frame the inner thin cross of a bonecross mark.
    The L-shapes match the dimensions of the internal cross arms exactly based on bonecross logic.
    
    Args:
        mark_size: Size parameter of the bonecross mark
        mark_width: Width parameter of the bonecross mark (the 'wide' part)
        frame_width: Line width of the L-shape arms. Defaults to (mark_width - internal_width).
        layer: Layer for the frame
    """
    # Use the exact same logic as create_bonecross to find internal dimensions
    internal_width = mark_width / 2.0
    internal_length = (mark_width + mark_size) / 2.0
    
    # Default frame_width is the single-sided difference between wide and narrow parts
    if frame_width is None:
        frame_width = (mark_width - internal_width) / 2.0
        
    name = f"CrosshairFrame_MS{mark_size}_MW{mark_width}_W{frame_width:.3g}_L{layer[0]}_{layer[1]}"
    
    if name in _component_cache:
        return _component_cache[name]
    
    c = gf.Component(name)
    
    # The tips of the thin part and the inner corner positions
    tip = internal_length / 2.0
    corner = internal_width / 2.0
    
    # The L-shape arm length is exactly the protruding part of the thin cross
    arm_len = tip - corner
    
    # Helper to add rectangle (center position)
    def add_rect(w, h, center_x, center_y):
        ref = c << get_rect_component(w, h, layer)
        ref.move((center_x, center_y))
    
    # Top-Left L: vertex at (-corner, corner), arms extend Left (to -tip) and Up (to tip)
    # Vertical arm (Up): x is fixed at -corner, y extends from corner to tip
    add_rect(frame_width, arm_len, -corner - frame_width / 2.0, corner + arm_len / 2.0)
    # Horizontal arm (Left): y is fixed at corner, x extends from -corner to -tip
    add_rect(arm_len, frame_width, -corner - arm_len / 2.0, corner + frame_width / 2.0)
    
    # Top-Right L: arms extend Right (to tip) and Up (to tip)
    add_rect(frame_width, arm_len, corner + frame_width / 2.0, corner + arm_len / 2.0)
    add_rect(arm_len, frame_width, corner + arm_len / 2.0, corner + frame_width / 2.0)
    
    # Bottom-Left L: arms extend Left (to -tip) and Down (to -tip)
    add_rect(frame_width, arm_len, -corner - frame_width / 2.0, -corner - arm_len / 2.0)
    add_rect(arm_len, frame_width, -corner - arm_len / 2.0, -corner - frame_width / 2.0)
    
    # Bottom-Right L: arms extend Right (to tip) and Down (to -tip)
    add_rect(frame_width, arm_len, corner + frame_width / 2.0, -corner - arm_len / 2.0)
    add_rect(arm_len, frame_width, corner + arm_len / 2.0, -corner - frame_width / 2.0)
    
    _component_cache[name] = c
    return c
    
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
    mark_q1: gf.Component,
    mark_q2: gf.Component,
    mark_q3: gf.Component,
    mark_q4: gf.Component,
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
    enable_caliper: bool,
    marker_l_l4: gf.Component = None  # L4 L-marker (same as L3 but on L4 layer)
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
    
    # Place Marks (Frames are now included inside the composite mark cells)
    # Q1: TR, Q2: TL, Q3: BL, Q4: BR
    c.add_ref(mark_q3).move(pos_BL)
    c.add_ref(mark_q4).move(pos_BR)
    c.add_ref(mark_q2).move(pos_TL)
    c.add_ref(mark_q1).move(pos_TR)
    
    # Place L-Markers at Corners (TL and BR) on L3
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
    
    # Place L-Markers at Corners (BL and TR) on L4
    if marker_l_l4:
        # BL Corner (-h_size, -h_size) -> Bottom-Left of Field
        # Base L extends +x and +y from origin
        # Position: (-h_size, -h_size)
        c.add_ref(marker_l_l4).move((-h_size, -h_size))
        
        # TR Corner (h_size, h_size) -> Top-Right of Field
        # Rotate 180 to point inward
        # Position: (h_size, h_size)
        c.add_ref(marker_l_l4).rotate(180).move((h_size, h_size))

    # Place Labels
    # Format: (Position, OffsetDirection, Suffix)
    label_configs = [
        (pos_BL, (1, 1), ",3"),   # Q3
        (pos_BR, (-1, 1), ",4"),  # Q4
        (pos_TL, (1, -1), ",2"),  # Q2
        (pos_TR, (-1, -1), ",1")  # Q1
    ]
    
    for (mx, my), (dx, dy), suffix in label_configs:
        full_label = f"{label_text}{suffix}"
        text_comp = gf.components.text(
            text=full_label,
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
    active_width: float = 7000.0,
    active_height: float = 7000.0,
    writefield_size: float = 1000.0,
    
    # Mark parameters
    mark_main_size: float = 80.0,
    mark_main_width: float = 5.0,
    mark_small_size: float = 15.0,
    mark_small_width: float = 2.0,
    mark_small_dist: float = 50.0,
    
    # L-Marker parameters
    l_marker_length: float = 100.0,
    l_marker_width: float = 5.0,
    
    # Boundary parameters
    boundary_line_width: float = 10.0,
    
    # Mark placement parameters
    mark_offset_from_corner: tuple = (100.0, 100.0),
    
    # Global corner marks parameters
    global_mark_offset: float = 200.0,  # Distance from active area corner to global mark center (outward)
    global_mark_main_size: float = 400.0,  # Size of main crossbone in global marks
    global_mark_main_width: float = 10.0,  # Width of main crossbone in global marks
    global_mark_small_size: float = 50.0,  # Size of small crossbones in global marks
    global_mark_small_width: float = 4.0,  # Width of small crossbones in global marks
    global_mark_small_dist: float = 175.0,  # Distance from center to small marks in global marks
    
    # Label parameters
    label_size: float = 15.0,
    label_offset: tuple = (-70.0, -75.0), # Distance from mark center to label center (x, y)
    
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
    layer_mark: tuple = (3, 0),  # L3: All marks
    layer_mark_frame: tuple = (4, 0),  # L4: Crosshair frames for main marks
    layer_caliper: tuple = (5, 0),  # L5: Calipers
    layer_auto_align: tuple = (61, 0), # L61: Auto alignment slits
    layer_manual_align: tuple = (63, 0), # L63: Manual alignment boxes
    
    # L4 frame parameters
    frame_width: float = None,  # Line width of the L-shape arms. Defaults to mark_width difference if None.
    
    # Info parameters
    user_name: str = "Xinchuan",
    info_text_size: float = 50.0,
    info_text_offset: tuple = (-100.0, -95.0), # Offset from the Top-Left global mark (x, y)
    info_text_line_width: float = 0.0,  # Bolder if > 0, thinner if < 0 (uses polygon offset)
    enable_alignment_layers: bool = True
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
    # Create 4 variants for the 4 quadrants of the writefield
    # Q1: Top-Right (Standard + Circle Q1)
    mark_q1 = create_composite_mark(
        main_size=mark_main_size,
        main_width=mark_main_width,
        small_size=mark_small_size,
        small_width=mark_small_width,
        small_offset_dist=mark_small_dist,
        layer=layer_mark,
        is_main_mark=False,
        enable_frame=True,
        frame_width=frame_width,
        layer_frame=layer_mark_frame,
        quadrant_indicator=1,
        layer_auto_align=layer_auto_align,
        layer_manual_align=layer_manual_align,
        enable_alignment_layers=enable_alignment_layers
    )
    
    # Q2: Top-Left (Main Mark + Circle Q2)
    mark_q2 = create_composite_mark(
        main_size=mark_main_size,
        main_width=mark_main_width,
        small_size=mark_small_size,
        small_width=mark_small_width,
        small_offset_dist=mark_small_dist,
        layer=layer_mark,
        is_main_mark=True, # Main mark is at TL
        enable_frame=True,
        frame_width=frame_width,
        layer_frame=layer_mark_frame,
        quadrant_indicator=2,
        layer_auto_align=layer_auto_align,
        layer_manual_align=layer_manual_align,
        enable_alignment_layers=enable_alignment_layers
    )
    
    # Q3: Bottom-Left (Standard + Circle Q3)
    mark_q3 = create_composite_mark(
        main_size=mark_main_size,
        main_width=mark_main_width,
        small_size=mark_small_size,
        small_width=mark_small_width,
        small_offset_dist=mark_small_dist,
        layer=layer_mark,
        is_main_mark=False,
        enable_frame=True,
        frame_width=frame_width,
        layer_frame=layer_mark_frame,
        quadrant_indicator=3,
        layer_auto_align=layer_auto_align,
        layer_manual_align=layer_manual_align,
        enable_alignment_layers=enable_alignment_layers
    )
    
    # Q4: Bottom-Right (Standard + Circle Q4)
    mark_q4 = create_composite_mark(
        main_size=mark_main_size,
        main_width=mark_main_width,
        small_size=mark_small_size,
        small_width=mark_small_width,
        small_offset_dist=mark_small_dist,
        layer=layer_mark,
        is_main_mark=False,
        enable_frame=True,
        frame_width=frame_width,
        layer_frame=layer_mark_frame,
        quadrant_indicator=4,
        layer_auto_align=layer_auto_align,
        layer_manual_align=layer_manual_align,
        enable_alignment_layers=enable_alignment_layers
    )
    
    # Create L-Marker (L3)
    marker_l = create_corner_marker(
        length=l_marker_length,
        width=l_marker_width,
        layer=layer_mark
    )
    
    # Create L-Marker for L4 (same structure, different layer)
    marker_l_l4 = create_corner_marker(
        length=l_marker_length,
        width=l_marker_width,
        layer=layer_mark_frame
    )

    # 3.5. Create Global Corner Alignment Marks (with custom sizes)
    def add_global_mark(pos, is_main=False):
        mark = create_composite_mark(
            main_size=global_mark_main_size,
            main_width=global_mark_main_width,
            small_size=global_mark_small_size,
            small_width=global_mark_small_width,
            small_offset_dist=global_mark_small_dist,
            layer=layer_mark,
            is_main_mark=is_main,
            enable_frame=True,
            frame_width=frame_width,
            layer_frame=layer_mark_frame,
            center_coords=pos,
            layer_auto_align=layer_auto_align,
            layer_manual_align=layer_manual_align,
            enable_alignment_layers=enable_alignment_layers
        )
        return c.add_ref(mark).move(pos)

    # 5. Tiling Write Fields
    nx = int(np.ceil(active_width / writefield_size))
    ny = int(np.ceil(active_height / writefield_size))

    # 3.6. Place Global Corner Alignment Marks (outside active area)
    # Calculate corner positions relative to active area boundaries
    h_active_w = active_width / 2.0
    h_active_h = active_height / 2.0
    
    # Four corners
    # Top-Left corner (Main mark, relative to active area, offset outward)
    tl_mark_pos = (-h_active_w - global_mark_offset, h_active_h + global_mark_offset)
    add_global_mark(tl_mark_pos, is_main=True)
    
    # Add info text to the right of the Top-Left global mark
    info_lines = [
        f"WF: {writefield_size} um, Mark Offset: -{mark_offset_from_corner} um",
        f"AA: {active_width} * {active_height} um, Mark Offset: +{global_mark_offset} um",
        f"User: {user_name}, Date: {datetime.now().strftime('%Y-%m-%d')}"
    ]
    
    info_x = tl_mark_pos[0] + global_mark_main_size + info_text_offset[0]  # Start text after the mark + offset
    info_y_start = tl_mark_pos[1] + global_mark_main_size / 2.0 + info_text_offset[1]
    
    for idx, line in enumerate(info_lines):
        text_comp = gf.components.text(
            text=line,
            size=info_text_size,
            layer=layer_mark,
            justify='left'
        )
        
        # Apply offset to change line width (boldness) if specified
        if info_text_line_width != 0:
            text_comp = gf.geometry.offset(
                text_comp, 
                distance=info_text_line_width, 
                layer=layer_mark
            )
            
        text_ref = c << text_comp
        
        # Position each line so its handle is Top-Left:
        # 1. Left edge (xmin) aligns with info_x
        # 2. Top edge (ymax) aligns with the calculated Y position for this line
        line_top_y = info_y_start - idx * info_text_size * 1.5
        text_ref.move((info_x - text_ref.xmin, line_top_y - text_ref.ymax))
    
    # Top-Right corner (relative to active area, offset outward)
    add_global_mark((h_active_w + global_mark_offset, h_active_h + global_mark_offset))
    
    # Bottom-Left corner (relative to active area, offset outward)
    add_global_mark((-h_active_w - global_mark_offset, -h_active_h - global_mark_offset))
    
    # Bottom-Right corner (relative to active area, offset outward)
    add_global_mark((h_active_w + global_mark_offset, -h_active_h - global_mark_offset))
    
    # Four edges (midpoints)
    # Top edge (center)
    add_global_mark((0, h_active_h + global_mark_offset))
    
    # Bottom edge (center)
    add_global_mark((0, -h_active_h - global_mark_offset))
    
    # Left edge (center)
    add_global_mark((-h_active_w - global_mark_offset, 0))
    
    # Right edge (center)
    add_global_mark((h_active_w + global_mark_offset, 0))

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
            layer=layer_caliper,
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
            layer=layer_caliper,
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
            layer=layer_caliper,
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
            layer=layer_caliper,
            orientation="vertical",
            tick_direction=1,
            limit_length=writefield_size
        )

    # 5. Tiling Write Fields (nx, ny already calculated above)
    total_grid_width = nx * writefield_size
    total_grid_height = ny * writefield_size
    
    start_x = -total_grid_width / 2.0
    start_y = -total_grid_height / 2.0
    
    for i in range(nx):
        for j in range(ny):
            # Calculate Center of the WriteField
            wf_center_x = start_x + i * writefield_size + writefield_size / 2.0
            # Reverse j order so that j=0 corresponds to top row (A1 at top-left)
            wf_center_y = start_y + (ny - 1 - j) * writefield_size + writefield_size / 2.0
            
            col_label = index_to_letters(i)  # Column (x-direction) uses letters
            row_label = str(j + 1)  # Row (y-direction) uses numbers
            label_text = f"{col_label}{row_label}"
            
            cell_name = f"Field_{label_text}"
            
            wf_cell = create_single_writefield(
                name=cell_name,
                size=writefield_size,
                mark_q1=mark_q1,
                mark_q2=mark_q2,
                mark_q3=mark_q3,
                mark_q4=mark_q4,
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
                enable_caliper=enable_caliper,
                marker_l_l4=marker_l_l4
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
        # gf.geometry.union(by_layer=True) flattens the hierarchy and merges polygons 
        # within each layer independently, ensuring no cross-layer merging.
        # c_merged = gf.geometry.union(c, by_layer=True)
        # c_merged.name = "TOP"

        # Update for gdsfactory >= 8.0 (geometry module removed)
        c_merged = gf.Component("TOP")
        polygons_dict = c.get_polygons(merge=True, by='tuple')
        for layer_spec, polygons in polygons_dict.items():
            layer_index = c_merged.layer(layer_spec)
            for p in polygons:
                c_merged.shapes(layer_index).insert(p)

        c_merged.write_gds("mark_writefield_array_merged.gds")
