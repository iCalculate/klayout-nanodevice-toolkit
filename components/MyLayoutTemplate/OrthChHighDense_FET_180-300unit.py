# -*- coding: utf-8 -*-
"""
New Device Component Module - KLayout-based Field Effect Transistor Layout Generator
"""

import sys
import os
import math
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import klayout.db as db
from utils.geometry import GeometryUtils, Point, Polygon
from utils.mark_utils import MarkUtils
from utils.fanout_utils import draw_pad, draw_trapezoidal_fanout
from utils.text_utils import TextUtils
from utils.digital_utils import DigitalDisplay
from config import LAYER_DEFINITIONS, DEFAULT_UNIT_SCALE

class NewDevice:
    """New Device Class"""
    
    def __init__(self, layout=None, **kwargs):
        """
        Initialize New Device Class
        
        Args:
            layout: KLayout layout object, create new one if None
            **kwargs: Other parameters including device, mark, fanout, labeling related parameters
        """
        self.layout = layout or db.Layout()
        self.setup_layers()
        
        # ===== Device Core Parameters =====
        self.ch_len = kwargs.get('ch_len', 16.0)           # Channel length (Y direction, vertical, μm)
        self.ch_width = kwargs.get('ch_width', 5.0)        # Channel width (X direction, horizontal, μm)
        
        # ===== Device Boundary Parameters =====
        self.device_width = 300.0   # Device area width (X direction, horizontal, μm) - doubled from 150
        self.device_height = 180.0   # Device area height (Y direction, vertical, μm) - doubled from 90
        self.mark_margin = kwargs.get('mark_margin', 0.0)           # Mark center distance from boundary (μm)
        
        # ===== Mark Parameters =====
        self.mark_size = kwargs.get('mark_size', 30.0)              # Mark size (μm) - doubled from 20
        self.mark_width = kwargs.get('mark_width', 4.0)             # Mark line width (μm) - doubled from 2
        
        # ===== Electrode Parameters =====
        # Source electrode parameters
        self.source_outer_x = -95.0      # Outer pad X coordinate - doubled from -47.5
        self.source_outer_y = 10.0       # Outer pad Y coordinate - doubled from 5.0
        self.source_outer_width = 120.0  # Outer pad width (actual drawing horizontal) - doubled from 60
        self.source_outer_length = 70.0  # Outer pad length (actual drawing vertical) - doubled from 35
        self.source_inner_x = -5.0       # Inner pad X coordinate - doubled from -2.5
        self.source_inner_y_offset = 4.0 # Inner pad Y offset (relative to ch_width) - doubled from 2.0
        self.source_inner_width = 8.0    # Inner pad width (actual drawing horizontal) - doubled from 4
        self.source_inner_length = 70.0  # Inner pad length (actual drawing vertical) - doubled from 35
        
        # Drain electrode parameters
        self.drain_outer_x = 95.0        # Outer pad X coordinate - doubled from 47.5
        self.drain_outer_y = -10.0       # Outer pad Y coordinate - doubled from -5.0
        self.drain_outer_width = 120.0   # Outer pad width (actual drawing horizontal) - doubled from 60
        self.drain_outer_length = 70.0   # Outer pad length (actual drawing vertical) - doubled from 35
        self.drain_inner_x = 5.0         # Inner pad X coordinate - doubled from 2.5
        self.drain_inner_y_offset = 4.0  # Inner pad Y offset (relative to ch_width) - doubled from 2.0
        self.drain_inner_width = 8.0     # Inner pad width (actual drawing horizontal) - doubled from 4
        self.drain_inner_length = 70.0   # Inner pad length (actual drawing vertical) - doubled from 35
        
        # ===== Labeling Parameters =====
        self.label_size = kwargs.get('label_size', 30.0)           # Label size (μm) - doubled from 20
        self.label_spacing = kwargs.get('label_spacing', 0.6)      # Label character spacing (relative to character size)
        self.label_font = kwargs.get('label_font', 'C:/Windows/Fonts/OCRAEXT.TTF')  # Label font path
        self.label_offset_x = kwargs.get('label_offset_x', -100.0)   # Label position X offset (μm) - doubled from -62
        self.label_offset_y = kwargs.get('label_offset_y', -6.0)  # Label position Y offset (μm) - doubled from -3
        self.use_digital_display = kwargs.get('use_digital_display', False)  # Whether to use DigitalDisplay, default False (use TextUtils)
        
    def setup_layers(self):
        """Setup layers"""
        for layer_name, layer_info in LAYER_DEFINITIONS.items():
            # In KLayout, use layer() method to get or create layers
            # layer() method requires (layer_number, datatype) parameters
            self.layout.layer(layer_info['id'], 0)  # Use datatype=0
    
    def set_device_parameters(self, ch_width=None, ch_len=None):
        """
        Set device parameters
        
        Args:
            ch_width: Channel width (X direction, horizontal, μm)
            ch_len: Channel length (Y direction, vertical, μm)
        """
        if ch_width is not None:
            self.ch_width = ch_width
        if ch_len is not None:
            self.ch_len = ch_len
    
    def create_source_electrode(self, cell, x=0.0, y=0.0):
        """
        Create source electrode
        
        Args:
            cell: Target cell
            x, y: Device center coordinates
        """
        layer_id = LAYER_DEFINITIONS['source_drain']['id']
        
        # Calculate inner pad Y coordinate
        source_inner_y = y + self.ch_len/2 + self.source_inner_y_offset
        
        # Source outer pad
        source_outer = draw_pad(
            center=(x + self.source_outer_x, y + self.source_outer_y),
            width=self.source_outer_width,
            length=self.source_outer_length,
            chamfer_size=0,
            chamfer_type='none'
        )
        
        # Source inner pad
        source_inner = draw_pad(
            center=(x + self.source_inner_x, source_inner_y),
            width=self.source_inner_width,
            length=self.source_inner_length,
            chamfer_size=0,
            chamfer_type='none'
        )
        
        # Trapezoidal fanout - connect outer pad right edge to inner pad left edge
        fanout1 = draw_trapezoidal_fanout(source_outer, source_inner)
        
        # Trapezoidal fanout - connect outer pad top edge to inner pad top edge
        fanout2 = draw_trapezoidal_fanout(source_outer, source_inner, inner_edge='U', outer_edge='U')
        
        # Combine all source parts using boolean union operation
        try:
            import pya
            Region = pya.Region
        except Exception:
            import klayout.db as db
            Region = db.Region
            
        # Convert shapes to regions for boolean operations
        region1 = Region(source_outer.polygon)
        region2 = Region(source_inner.polygon)
        region3 = Region(fanout1)
        region4 = Region(fanout2)
        
        # Perform union operation and merge to eliminate internal boundaries
        combined_source = (region1 + region2 + region3 + region4).merged()
        
        # Insert the combined source electrode
        cell.shapes(layer_id).insert(combined_source)
    
    def create_drain_electrode(self, cell, x=0.0, y=0.0):
        """
        Create drain electrode
        
        Args:
            cell: Target cell
            x, y: Device center coordinates
        """
        layer_id = LAYER_DEFINITIONS['source_drain']['id']
        
        # Calculate inner pad Y coordinate
        drain_inner_y = y - self.ch_len/2 - self.drain_inner_y_offset
        
        # Drain outer pad
        drain_outer = draw_pad(
            center=(x + self.drain_outer_x, y + self.drain_outer_y),
            width=self.drain_outer_width,
            length=self.drain_outer_length,
            chamfer_size=0,
            chamfer_type='none'
        )
        
        # Drain inner pad
        drain_inner = draw_pad(
            center=(x + self.drain_inner_x, drain_inner_y),
            width=self.drain_inner_width,
            length=self.drain_inner_length,
            chamfer_size=0,
            chamfer_type='none'
        )
        
        # Trapezoidal fanout - connect outer pad left edge to inner pad right edge
        fanout1 = draw_trapezoidal_fanout(drain_outer, drain_inner)
        
        # Trapezoidal fanout - connect outer pad bottom edge to inner pad bottom edge
        fanout2 = draw_trapezoidal_fanout(drain_outer, drain_inner, inner_edge='D', outer_edge='D')
        
        # Combine all drain parts using boolean union operation
        try:
            import pya
            Region = pya.Region
        except Exception:
            import klayout.db as db
            Region = db.Region
            
        # Convert shapes to regions for boolean operations
        region1 = Region(drain_outer.polygon)
        region2 = Region(drain_inner.polygon)
        region3 = Region(fanout1)
        region4 = Region(fanout2)
        
        # Perform union operation and merge to eliminate internal boundaries
        combined_drain = (region1 + region2 + region3 + region4).merged()
        
        # Insert the combined drain electrode
        cell.shapes(layer_id).insert(combined_drain)
    
    def create_gate_electrode(self, cell, x=0.0, y=0.0):
        """
        Create gate electrode with two parts:
        Part 1: Rectangle with width=ch_width+3, length=ch_length/2+54
        Part 2: 50μm×40μm hexagon with chamfered corners
        
        Args:
            cell: Target cell
            x, y: Device center coordinates
        """
        from utils.geometry import Point, Polygon
        from config import DEFAULT_UNIT_SCALE
        
        layer_id = LAYER_DEFINITIONS['top_gate']['id']
        
        # Part 1: Main rectangular region
        gate_part1_width = self.ch_width + 6.0  # doubled from 3.0
        gate_part1_length = self.ch_len / 2.0 + 108.0  # doubled from 54.0
        gate_part1_x = x
        gate_part1_y = y - self.device_height/2 + gate_part1_length/2
        
        # Create Part 1: Main rectangular region
        gate_part1 = GeometryUtils.create_rectangle(
            gate_part1_x, gate_part1_y,
            gate_part1_width, gate_part1_length,
            center=True
        )
        
        # Part 2: 100μm×80μm hexagon with chamfered corners (doubled from 50×40)
        gate_part2_width = 100.0  # doubled from 50.0
        gate_part2_height = 80.0  # doubled from 40.0
        gate_part2_x = x
        gate_part2_y = y - self.device_height/2
        
        # Calculate rectangle corners
        rect_left = gate_part2_x - gate_part2_width/2
        rect_right = gate_part2_x + gate_part2_width/2
        rect_bottom = gate_part2_y - gate_part2_height/2
        rect_top = gate_part2_y + gate_part2_height/2
        
        # Reference line: (-30, -ch_length/2-8) to (60, -70) (doubled from (-15, -ch_length/2-4) to (30, -35))
        ref_start_x = -30.0  # doubled from -15.0
        ref_start_y = -self.ch_len/2.0 - 8.0  # doubled from -4.0
        ref_end_x = 60.0  # doubled from 30.0
        ref_end_y = -70.0  # doubled from -35.0
        
        # Calculate reference line direction
        ref_dx = ref_end_x - ref_start_x
        ref_dy = ref_end_y - ref_start_y
        ref_length = (ref_dx**2 + ref_dy**2)**0.5
        ref_unit_dx = ref_dx / ref_length
        ref_unit_dy = ref_dy / ref_length
        
        # Chamfer line is parallel to reference line, 24μm below it (doubled from 12μm)
        chamfer_scale = 1.0
        chamfer_distance = 60.0  # doubled from 30.0
        # Calculate chamfer line position (12μm below the reference line)
        chamfer_line_start_x = ref_start_x + ref_unit_dx * chamfer_distance
        chamfer_line_start_y = ref_start_y + ref_unit_dy * chamfer_distance
        chamfer_line_end_x = ref_end_x + ref_unit_dx * chamfer_distance
        chamfer_line_end_y = ref_end_y + ref_unit_dy * chamfer_distance
        
        # Calculate chamfer offsets based on chamfer_distance
        # The chamfer should be proportional to chamfer_distance and reference line direction
        chamfer_ratio = chamfer_distance / ref_length
        tr_x_offset = chamfer_ratio * abs(ref_dx)
        tr_y_offset = chamfer_ratio * abs(ref_dy)
        
        # Bottom-left chamfer: symmetric to top-right
        bl_x_offset = chamfer_scale*tr_x_offset
        bl_y_offset = chamfer_scale*tr_y_offset
        # Create hexagon points in clockwise order
        hexagon_points = [
            Point(int(rect_left * DEFAULT_UNIT_SCALE), int(rect_top * DEFAULT_UNIT_SCALE)),  # Top-left
            Point(int((rect_right - tr_x_offset) * DEFAULT_UNIT_SCALE), int(rect_top * DEFAULT_UNIT_SCALE)),  # Top chamfer
            Point(int(rect_right * DEFAULT_UNIT_SCALE), int((rect_top - tr_y_offset) * DEFAULT_UNIT_SCALE)),  # Right chamfer
            Point(int(rect_right * DEFAULT_UNIT_SCALE), int(rect_bottom * DEFAULT_UNIT_SCALE)),  # Bottom-right
            Point(int((rect_left + bl_x_offset) * DEFAULT_UNIT_SCALE), int(rect_bottom * DEFAULT_UNIT_SCALE)),  # Bottom-left chamfer
            Point(int(rect_left * DEFAULT_UNIT_SCALE), int((rect_bottom + bl_y_offset) * DEFAULT_UNIT_SCALE))  # Bottom-left
        ]
        
        # Create hexagon
        hexagon = Polygon(hexagon_points)
        
        # Combine both parts using boolean union operation
        try:
            import pya
            Region = pya.Region
        except Exception:
            import klayout.db as db
            Region = db.Region
            
        # Convert shapes to regions for boolean operations
        region1 = Region(gate_part1)
        region2 = Region(hexagon)
        
        # Perform union operation and merge to eliminate internal boundaries
        combined_gate = (region1 + region2).merged()
        
        # Insert the combined gate
        cell.shapes(layer_id).insert(combined_gate)
    
    def create_channel_material(self, cell, x=0.0, y=0.0):
        """
        Create channel material layer
        
        Args:
            cell: Target cell
            x, y: Device center coordinates
        """
        layer_id = LAYER_DEFINITIONS['channel']['id']
        
        # Channel material rectangle - width is ch_width (X direction, horizontal), length is ch_len+30 (Y direction, vertical) - doubled from 15
        channel = GeometryUtils.create_rectangle(
            x, y,
            self.ch_width,
            self.ch_len + 30.0,  # doubled from 15.0
            center=True
        )
        cell.shapes(layer_id).insert(channel)
    
    def create_dielectric_layer(self, cell, x=0.0, y=0.0):
        """
        Create dielectric layer - covers entire device area with windows on source and drain outer pads
        
        Args:
            cell: Target cell
            x, y: Device center coordinates
        """
        try:
            import pya
            Region = pya.Region
        except Exception:
            import klayout.db as db
            Region = db.Region
            
        layer_id = LAYER_DEFINITIONS['top_dielectric']['id']
        
        # 1. Generate large rectangle region covering entire device area
        dielectric_rect = GeometryUtils.create_rectangle(
            x, y,
            self.device_width,
            self.device_height,
            center=True
        )
        dielectric_region = Region(dielectric_rect)
        
        # 2. Generate source outer pad window (8μm smaller than pad in both dimensions) - doubled from 4μm
        source_window_rect = GeometryUtils.create_rectangle(
            x + self.source_outer_x, y + self.source_outer_y,
            self.source_outer_length - 8.0,  # doubled from 4.0
            self.source_outer_width - 8.0,   # doubled from 4.0
            center=True
        )
        source_window_region = Region(source_window_rect)
        
        # 3. Generate drain outer pad window (8μm smaller than pad in both dimensions) - doubled from 4μm
        drain_window_rect = GeometryUtils.create_rectangle(
            x + self.drain_outer_x, y + self.drain_outer_y,
            self.drain_outer_length - 8.0,   # doubled from 4.0
            self.drain_outer_width - 8.0,    # doubled from 4.0
            center=True
        )
        drain_window_region = Region(drain_window_rect)
        
        # 4. Use Region boolean subtraction to create windows
        dielectric_region -= source_window_region
        dielectric_region -= drain_window_region
        
        # 5. Insert into cell
        cell.shapes(layer_id).insert(dielectric_region)
    
    def create_alignment_mark(self, cell, x=0.0, y=0.0):
        """
        Create top-right corner alignment mark
        
        Args:
            cell: Target cell
            x, y: Device center coordinates
        """
        layer_id = LAYER_DEFINITIONS['alignment_marks']['id']
        
        # Calculate top-right corner mark position
        mark_x = x + self.device_width/2 - self.mark_margin
        mark_y = y + self.device_height/2 - self.mark_margin
        
        # Create sq_missing mark
        marks = MarkUtils.sq_missing(mark_x, mark_y, self.mark_size)
        
        # Insert mark
        shapes = marks.get_shapes()
        if isinstance(shapes, list):
            for shape in shapes:
                cell.shapes(layer_id).insert(shape)
        else:
            cell.shapes(layer_id).insert(shapes)
    
    def create_device_label(self, cell, x, y, row, col, label_type=None):
        """
        Create A01 format device label at specified position
        
        Args:
            cell: Target cell
            x, y: Label starting coordinates
            row: Row number (number, starting from 1)
            col: Column number (letter, starting from A)
            label_type: Label type, 'textutils' or 'digital', if None use initialization setting
        """
        # If label_type not specified, use initialization setting
        if label_type is None:
            label_type = 'digital' if self.use_digital_display else 'textutils'
        
        if label_type == 'textutils':
            self._create_device_label_textutils(cell, x, y, row, col)
        elif label_type == 'digital':
            self._create_device_label_digital(cell, x, y, row, col)
        else:
            # 默认使用textutils
            self._create_device_label_textutils(cell, x, y, row, col)
    
    def _get_column_label(self, col):
        """
        Generate column label: A-Z, a-z cycle
        
        Args:
            col: Column number (starting from 0)
        
        Returns:
            Column label string
        """
        if col < 26:
            # 0-25: A-Z
            return chr(ord('A') + col)
        elif col < 52:
            # 26-51: a-z
            return chr(ord('a') + (col - 26))
        else:
            # 52+: Cycle through A-Z, a-z
            cycle = col // 52
            remainder = col % 52
            if remainder < 26:
                return chr(ord('A') + remainder)
            else:
                return chr(ord('a') + (remainder - 26))
    
    def _create_device_label_textutils(self, cell, x, y, row, col):
        """
        Create device label using TextUtils (recommended method)
        """
        layer_id = LAYER_DEFINITIONS['labels']['id']
        
        # Generate A01 format label
        col_letter = self._get_column_label(col)  # Support A-Z, a-z cycle
        row_number = f"{row:02d}"  # Row number formatted as two digits, e.g., 01, 02, 03
        label = col_letter + row_number  # e.g., A01, B02, C03, a01, b02, ...
        
        # Apply offset
        label_x = x + self.label_offset_x
        label_y = y + self.label_offset_y
        
        # Set character size and spacing
        char_size = self.label_size
        char_spacing = char_size * self.label_spacing  # Character spacing
        
        # Create each character
        for i, char in enumerate(label):
            char_x = label_x + i * char_spacing
            char_y = label_y
            
            # Use TextUtils to create text
            text_shapes = TextUtils.create_text_freetype(
                char, char_x, char_y, 
                size_um=int(char_size), 
                font_path=self.label_font,
                spacing_um=0.5
            )
            
            for shape in text_shapes:
                cell.shapes(layer_id).insert(shape)
    
    def _create_device_label_digital(self, cell, x, y, row, col):
        """
        Create device label using DigitalDisplay (traditional method)
        """
        layer_id = LAYER_DEFINITIONS['labels']['id']
        
        # Generate A01 format label
        col_letter = self._get_column_label(col)  # Support A-Z, a-z cycle
        row_number = f"{row:02d}"  # Row number formatted as two digits, e.g., 01, 02, 03
        label = col_letter + row_number  # e.g., A01, B02, C03, a01, b02, ...
        
        # Apply offset
        label_x = x + self.label_offset_x
        label_y = y + self.label_offset_y
        
        # Set character size and spacing
        char_size = self.label_size * 0.25  # DigitalDisplay usually needs smaller size
        stroke_width = self.mark_width * 0.8
        char_spacing = char_size * 1.7  # Character spacing
        
        # Create each character
        for i, char in enumerate(label):
            char_x = label_x + i * char_spacing
            char_y = label_y
            
            # Use DigitalDisplay to create digit display
            polygons = DigitalDisplay.create_digit(
                char, char_x, char_y, 
                size=char_size, 
                stroke_width=stroke_width
            )
            
            for polygon in polygons:
                cell.shapes(layer_id).insert(polygon)
    
    def create_parameter_labels(self, cell, x, y, device_params):
        """
        Create parameter labels within device area using pya.Text
        
        Args:
            cell: Target cell
            x, y: Device center coordinates
            device_params: Device parameters dictionary
        """
        layer_id = LAYER_DEFINITIONS['labels']['id']
        
        # Calculate label starting position (above device center)
        start_x = x - self.device_width * 0.4  # Offset to left
        start_y = y - self.device_height * 0.4  # Offset upward
        
        # Create parameter label text
        param_texts = []
        
        # Add channel width label
        if 'ch_width' in device_params:
            ch_width = device_params['ch_width']
            param_texts.append(f"W:{ch_width:.1f}")
        
        # Add channel length label
        if 'ch_len' in device_params:
            ch_len = device_params['ch_len']
            param_texts.append(f"L:{ch_len:.1f}")
        
        # 创建每行参数标注
        line_spacing = 20.0  # 行间距 (μm) - doubled from 10.0
        for i, text in enumerate(param_texts):
            text_y = start_y - i * line_spacing
            
            # 使用db.Text创建文本
            text_obj = db.Text(
                text,
                int(start_x * 1000),  # 转换为数据库单位
                int(text_y * 1000)    # 转换为数据库单位
            )
            
            cell.shapes(layer_id).insert(text_obj)
    
    def create_single_device(self, cell_name="NewDevice", x=0, y=0, device_id=None, row=None, col=None, device_params=None, label_type=None):
        """
        Create single new device
        
        Args:
            cell_name: Cell name
            x, y: Device center coordinates
            device_id: Device ID
            row: Row number (for generating A01 format label)
            col: Column number (for generating A01 format label)
            device_params: Device parameters dictionary for labeling
            label_type: Label type, 'textutils' or 'digital'
            
        Returns:
            Created cell
        """
        cell = self.layout.create_cell(cell_name)
        
        # Ensure coordinates are float
        x = float(x)
        y = float(y)
        
        # Create device structure in layer order
        self.create_source_electrode(cell, x, y)
        self.create_drain_electrode(cell, x, y)
        self.create_gate_electrode(cell, x, y)
        self.create_channel_material(cell, x, y)
        self.create_dielectric_layer(cell, x, y)
        self.create_alignment_mark(cell, x, y)
        
        # If row and column information available, create A01 format label
        if row is not None and col is not None:
            # Add label to the right of top-right corner mark
            mark_x = x + self.device_width/2 - self.mark_margin
            mark_y = y + self.device_height/2 - self.mark_margin
            label_x = mark_x + self.mark_size * 1.2  # To the right of mark
            label_y = mark_y  # Same height as mark
            self.create_device_label(cell, label_x, label_y, row, col, label_type)
        
        # If device parameters available, add parameter labels
        if device_params:
            self.create_parameter_labels(cell, x, y, device_params)
        
        return cell
    
    def create_device_array(self, rows=10, cols=10, device_spacing_x=None, device_spacing_y=None, label_type=None):
        """
        Create device array
        
        Args:
            rows: Number of rows
            cols: Number of columns
            device_spacing_x: Device horizontal spacing, auto-calculated if None
            device_spacing_y: Device vertical spacing, auto-calculated if None
            label_type: Label type, 'textutils' or 'digital'
            
        Returns:
            Array cell
        """
        # Calculate device spacing
        if device_spacing_x is None:
            device_spacing_x = self.device_width  # Seamless connection
        if device_spacing_y is None:
            device_spacing_y = self.device_height  # Seamless connection
        
        # Create array cell
        array_cell = self.layout.create_cell("NewDevice_Array")
        
        # Create device array
        device_id = 1
        for row in range(rows):
            for col in range(cols):
                # Calculate device position
                device_x = int(col * device_spacing_x)
                device_y = int(row * device_spacing_y)
                
                # Create single device
                device_cell = self.create_single_device(
                    f"NewDevice_{device_id:03d}", 
                    device_x, device_y, 
                    device_id, row + 1, col,  # row starts from 1, col starts from 0
                    label_type=label_type
                )
                
                # Insert device cell into array
                array_cell.insert(db.CellInstArray(
                    device_cell.cell_index(),
                    db.Trans(0, 0)
                ))
                
                device_id += 1
        
        return array_cell
    
    def scan_parameters_and_create_array(self, param_ranges, rows=10, cols=10, offset_x=0, offset_y=0, label_type=None):
        """
        Scan parameters and create device array with parameter variations
        
        Args:
            param_ranges: Parameter dictionary, format {'param_name': [min, max, steps]}
            rows: Number of rows
            cols: Number of columns
            offset_x: Array starting X coordinate offset
            offset_y: Array starting Y coordinate offset
            label_type: Label type, 'textutils' or 'digital'
            
        Returns:
            Parameter scan array cell
        """
        # 创建参数扫描阵列单元格
        scan_cell = self.layout.create_cell("NewDevice_Parameter_Scan")
        
        # Calculate total number of devices
        total_devices = rows * cols
        device_id = 1
        
        # Calculate parameter step sizes
        param_steps = {}
        for param_name, param_range in param_ranges.items():
            if len(param_range) == 3:
                min_val, max_val, steps = param_range
                param_steps[param_name] = (max_val - min_val) / (steps - 1) if steps > 1 else 0
            else:
                param_steps[param_name] = 0
        
        # Calculate device spacing
        device_spacing_x = self.device_width
        device_spacing_y = self.device_height
        
        # Create device array
        for row in range(rows):
            for col in range(cols):
                # Calculate current device parameter values
                current_params = {}
                
                # Row scan: channel length
                if 'ch_len' in param_ranges:
                    ch_len_range = param_ranges['ch_len']
                    if len(ch_len_range) == 3:
                        min_val, max_val, steps = ch_len_range
                        ch_len = min_val + row * (max_val - min_val) / (steps - 1)
                        current_params['ch_len'] = ch_len
                    else:
                        current_params['ch_len'] = ch_len_range[0]
                
                # Column scan: channel width
                if 'ch_width' in param_ranges:
                    ch_width_range = param_ranges['ch_width']
                    if len(ch_width_range) == 3:
                        min_val, max_val, steps = ch_width_range
                        ch_width = min_val + col * (max_val - min_val) / (steps - 1)
                        current_params['ch_width'] = ch_width
                    else:
                        current_params['ch_width'] = ch_width_range[0]
                
                # Set current device parameters
                self.set_device_parameters(**current_params)
                
                # Calculate device position (add offset)
                device_x = int(offset_x + col * device_spacing_x)
                device_y = int(offset_y + row * device_spacing_y)
                
                # Create single device
                device_cell = self.create_single_device(
                    f"NewDevice_Scan_{device_id:03d}", 
                    device_x, device_y, 
                    device_id, row + 1, col,  # row starts from 1, col starts from 0
                    current_params,
                    label_type=label_type
                )
                
                # Insert device cell into scan array
                scan_cell.insert(db.CellInstArray(
                    device_cell.cell_index(),
                    db.Trans(0, 0)
                ))
                
                device_id += 1
        
        return scan_cell


def main():
    """Main function - for testing new device generation"""
    
    # Create new device instance
    device = NewDevice()
    
    # Set device parameters
    device.set_device_parameters(
        ch_width=10.0,    # Channel width 10μm
        ch_len=10.0,     # Channel length 10μm
    )
    
    # Create single device for testing
    print("Creating single new device...")
    single_device = device.create_single_device("Test_NewDevice", 0, 0, 1, 1, 0)  # Position A01
    print(f"Single device created: {single_device.name}")
    
    # Create 55x33 device array
    print("Creating 55x33 device array...")
    device_array = device.create_device_array(rows=27, cols=16)
    print(f"Device array created: {device_array.name}")
    
    # Create parameter scan array (row-column scan)
    print("Creating parameter scan array...")
    param_ranges = {
        'ch_len': [1.0, 40.0, 27],      # Row scan: channel length from 0.5μm to 20μm, 55 values
        'ch_width': [1.0, 40.0, 16],    # Column scan: channel width from 1μm to 20μm, 33 values
    }
    
    # No offset, create scan array directly
    scan_array = device.scan_parameters_and_create_array(param_ranges, rows=27, cols=16, offset_x=0, offset_y=0)
    print(f"Parameter scan array created: {scan_array.name}")
    
    
    # Save layout file
    output_file = "TEST_NEW_DEVICE_180-300unit.gds"
    device.layout.write(output_file)
    print(f"Layout file saved: {output_file}")
    
    print("New device generation test completed!")


if __name__ == "__main__":
    main()
