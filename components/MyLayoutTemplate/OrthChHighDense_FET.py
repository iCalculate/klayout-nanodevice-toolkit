# -*- coding: utf-8 -*-
"""
Orthogonal Channel High-Density FET Component Module
KLayout-based Field Effect Transistor Layout Generator

This module provides a flexible and easy-to-use interface for generating
high-density FET device arrays with configurable parameters.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import klayout.db as db
from utils.geometry import GeometryUtils, Point, Polygon
from utils.mark_utils import MarkUtils
from utils.fanout_utils import draw_pad, draw_trapezoidal_fanout
from utils.text_utils import TextUtils
from utils.digital_utils import DigitalDisplay
from config import LAYER_DEFINITIONS, DEFAULT_UNIT_SCALE


class DeviceConfig:
    """Device configuration class - centralized parameter management"""
    
    def __init__(self, **kwargs):
        """
        Initialize device configuration
        
        Args:
            **kwargs: Configuration parameters (see default values below)
        """
        # ===== Device Core Parameters =====
        self.ch_len = kwargs.get('ch_len', 16.0)           # Channel length (Y direction, vertical, μm)
        self.ch_width = kwargs.get('ch_width', 5.0)          # Channel width (X direction, horizontal, μm)
        
        # ===== Device Boundary Parameters =====
        self.device_width = kwargs.get('device_width', 300.0)    # Device area width (X direction, horizontal, μm)
        self.device_height = kwargs.get('device_height', 180.0)   # Device area height (Y direction, vertical, μm)
        self.mark_margin = kwargs.get('mark_margin', 0.0)        # Mark center distance from boundary (μm)
        
        # ===== Mark Parameters =====
        self.mark_size = kwargs.get('mark_size', 30.0)          # Mark size (μm)
        self.mark_width = kwargs.get('mark_width', 4.0)         # Mark line width (μm)
        
        # ===== Source Electrode Parameters =====
        self.source_outer_x = kwargs.get('source_outer_x', -95.0)      # Outer pad X coordinate
        self.source_outer_y = kwargs.get('source_outer_y', 10.0)       # Outer pad Y coordinate
        self.source_outer_width = kwargs.get('source_outer_width', 120.0)  # Outer pad width (horizontal)
        self.source_outer_length = kwargs.get('source_outer_length', 70.0) # Outer pad length (vertical)
        self.source_inner_x = kwargs.get('source_inner_x', -5.0)       # Inner pad X coordinate
        self.source_inner_y_offset = kwargs.get('source_inner_y_offset', 4.0) # Inner pad Y offset
        self.source_inner_width = kwargs.get('source_inner_width', 8.0)    # Inner pad width (horizontal)
        self.source_inner_length = kwargs.get('source_inner_length', 70.0)  # Inner pad length (vertical)
        
        # ===== Drain Electrode Parameters =====
        self.drain_outer_x = kwargs.get('drain_outer_x', 95.0)        # Outer pad X coordinate
        self.drain_outer_y = kwargs.get('drain_outer_y', -10.0)      # Outer pad Y coordinate
        self.drain_outer_width = kwargs.get('drain_outer_width', 120.0)   # Outer pad width (horizontal)
        self.drain_outer_length = kwargs.get('drain_outer_length', 70.0)  # Outer pad length (vertical)
        self.drain_inner_x = kwargs.get('drain_inner_x', 5.0)         # Inner pad X coordinate
        self.drain_inner_y_offset = kwargs.get('drain_inner_y_offset', 4.0)  # Inner pad Y offset
        self.drain_inner_width = kwargs.get('drain_inner_width', 8.0)     # Inner pad width (horizontal)
        self.drain_inner_length = kwargs.get('drain_inner_length', 70.0)  # Inner pad length (vertical)
        
        # ===== Gate Electrode Parameters =====
        self.gate_part1_width_offset = kwargs.get('gate_part1_width_offset', 6.0)  # Gate width = ch_width + offset
        self.gate_part1_length_offset = kwargs.get('gate_part1_length_offset', 108.0)  # Gate length offset
        self.gate_part2_width = kwargs.get('gate_part2_width', 100.0)  # Gate hexagon width
        self.gate_part2_height = kwargs.get('gate_part2_height', 80.0)  # Gate hexagon height
        self.gate_chamfer_distance = kwargs.get('gate_chamfer_distance', 60.0)  # Gate chamfer distance
        
        # ===== Channel Material Parameters =====
        self.channel_length_extension = kwargs.get('channel_length_extension', 30.0)  # Channel length extension
        
        # ===== Dielectric Layer Parameters =====
        self.dielectric_window_reduction = kwargs.get('dielectric_window_reduction', 8.0)  # Window size reduction
        
        # ===== Labeling Parameters =====
        self.label_size = kwargs.get('label_size', 30.0)           # Label size (μm)
        self.label_spacing = kwargs.get('label_spacing', 0.6)      # Label character spacing (relative)
        self.label_font = kwargs.get('label_font', 'C:/Windows/Fonts/OCRAEXT.TTF')  # Label font path
        self.label_offset_x = kwargs.get('label_offset_x', -100.0)   # Label position X offset (μm)
        self.label_offset_y = kwargs.get('label_offset_y', -6.0)     # Label position Y offset (μm)
        self.use_digital_display = kwargs.get('use_digital_display', False)  # Use DigitalDisplay (False = TextUtils)
    
    def update(self, **kwargs):
        """Update configuration parameters"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise AttributeError(f"Unknown configuration parameter: {key}")
    
    def copy(self):
        """Create a copy of the configuration"""
        return DeviceConfig(**self.__dict__)


class ArrayConfig:
    """Array configuration class - for managing array parameters"""
    
    def __init__(self, **kwargs):
        """
        Initialize array configuration
        
        Args:
            **kwargs: Array configuration parameters
        """
        self.rows = kwargs.get('rows', 10)                    # Number of rows
        self.cols = kwargs.get('cols', 10)                   # Number of columns
        self.device_spacing_x = kwargs.get('device_spacing_x', None)  # Horizontal spacing (None = auto)
        self.device_spacing_y = kwargs.get('device_spacing_y', None)  # Vertical spacing (None = auto)
        self.offset_x = kwargs.get('offset_x', 0.0)         # Array starting X coordinate
        self.offset_y = kwargs.get('offset_y', 0.0)         # Array starting Y coordinate
        self.label_type = kwargs.get('label_type', None)    # Label type ('textutils' or 'digital')
        self.enable_labels = kwargs.get('enable_labels', True)  # Enable device labels
        self.enable_param_labels = kwargs.get('enable_param_labels', False)  # Enable parameter labels


class OrthChHighDenseFET:
    """Orthogonal Channel High-Density FET Device Class"""
    
    def __init__(self, layout=None, config=None, **kwargs):
        """
        Initialize FET Device Class
        
        Args:
            layout: KLayout layout object, create new one if None
            config: DeviceConfig instance (optional, can pass parameters via kwargs)
            **kwargs: Device parameters (will create/update config)
        """
        self.layout = layout or db.Layout()
        self.setup_layers()
        
        # Initialize or update configuration
        if config is None:
            self.config = DeviceConfig(**kwargs)
        elif isinstance(config, DeviceConfig):
            self.config = config
            if kwargs:
                self.config.update(**kwargs)
        else:
            raise TypeError("config must be a DeviceConfig instance or None")
    
    def setup_layers(self):
        """Setup layers"""
        for layer_name, layer_info in LAYER_DEFINITIONS.items():
            self.layout.layer(layer_info['id'], 0)  # Use datatype=0
    
    @staticmethod
    def _get_region_class():
        """
        Get Region class (pya.Region or db.Region)
        
        Returns:
            Region class for boolean operations
        """
        try:
            import pya
            return pya.Region
        except Exception:
            return db.Region
    
    def set_device_parameters(self, ch_width=None, ch_len=None):
        """
        Set device parameters (convenience method)
        
        Args:
            ch_width: Channel width (X direction, horizontal, μm)
            ch_len: Channel length (Y direction, vertical, μm)
        """
        if ch_width is not None:
            self.config.ch_width = ch_width
        if ch_len is not None:
            self.config.ch_len = ch_len
    
    def create_source_electrode(self, cell, x=0.0, y=0.0):
        """Create source electrode"""
        layer_id = LAYER_DEFINITIONS['source_drain']['id']
        cfg = self.config
        
        # Calculate inner pad Y coordinate
        source_inner_y = y + cfg.ch_len/2 + cfg.source_inner_y_offset
        
        # Source outer pad
        source_outer = draw_pad(
            center=(x + cfg.source_outer_x, y + cfg.source_outer_y),
            width=cfg.source_outer_width,
            length=cfg.source_outer_length,
            chamfer_size=0,
            chamfer_type='none'
        )
        
        # Source inner pad
        source_inner = draw_pad(
            center=(x + cfg.source_inner_x, source_inner_y),
            width=cfg.source_inner_width,
            length=cfg.source_inner_length,
            chamfer_size=0,
            chamfer_type='none'
        )
        
        # Trapezoidal fanouts
        fanout1 = draw_trapezoidal_fanout(source_outer, source_inner)
        fanout2 = draw_trapezoidal_fanout(source_outer, source_inner, inner_edge='U', outer_edge='U')
        
        # Combine all source parts
        Region = self._get_region_class()
        region1 = Region(source_outer.polygon)
        region2 = Region(source_inner.polygon)
        region3 = Region(fanout1)
        region4 = Region(fanout2)
        combined_source = (region1 + region2 + region3 + region4).merged()
        
        cell.shapes(layer_id).insert(combined_source)
    
    def create_drain_electrode(self, cell, x=0.0, y=0.0):
        """Create drain electrode"""
        layer_id = LAYER_DEFINITIONS['source_drain']['id']
        cfg = self.config
        
        # Calculate inner pad Y coordinate
        drain_inner_y = y - cfg.ch_len/2 - cfg.drain_inner_y_offset
        
        # Drain outer pad
        drain_outer = draw_pad(
            center=(x + cfg.drain_outer_x, y + cfg.drain_outer_y),
            width=cfg.drain_outer_width,
            length=cfg.drain_outer_length,
            chamfer_size=0,
            chamfer_type='none'
        )
        
        # Drain inner pad
        drain_inner = draw_pad(
            center=(x + cfg.drain_inner_x, drain_inner_y),
            width=cfg.drain_inner_width,
            length=cfg.drain_inner_length,
            chamfer_size=0,
            chamfer_type='none'
        )
        
        # Trapezoidal fanouts
        fanout1 = draw_trapezoidal_fanout(drain_outer, drain_inner)
        fanout2 = draw_trapezoidal_fanout(drain_outer, drain_inner, inner_edge='D', outer_edge='D')
        
        # Combine all drain parts
        Region = self._get_region_class()
        region1 = Region(drain_outer.polygon)
        region2 = Region(drain_inner.polygon)
        region3 = Region(fanout1)
        region4 = Region(fanout2)
        combined_drain = (region1 + region2 + region3 + region4).merged()
        
        cell.shapes(layer_id).insert(combined_drain)
    
    def create_gate_electrode(self, cell, x=0.0, y=0.0):
        """Create gate electrode with rectangular and hexagonal parts"""
        from utils.geometry import Point, Polygon
        from config import DEFAULT_UNIT_SCALE
        
        layer_id = LAYER_DEFINITIONS['top_gate']['id']
        cfg = self.config
        
        # Part 1: Main rectangular region
        gate_part1_width = cfg.ch_width + cfg.gate_part1_width_offset
        gate_part1_length = cfg.ch_len / 2.0 + cfg.gate_part1_length_offset
        gate_part1_x = x
        gate_part1_y = y - cfg.device_height/2 + gate_part1_length/2
        
        gate_part1 = GeometryUtils.create_rectangle(
            gate_part1_x, gate_part1_y,
            gate_part1_width, gate_part1_length,
            center=True
        )
        
        # Part 2: Hexagon with chamfered corners
        gate_part2_x = x
        gate_part2_y = y - cfg.device_height/2
        
        rect_left = gate_part2_x - cfg.gate_part2_width/2
        rect_right = gate_part2_x + cfg.gate_part2_width/2
        rect_bottom = gate_part2_y - cfg.gate_part2_height/2
        rect_top = gate_part2_y + cfg.gate_part2_height/2
        
        # Reference line for chamfer calculation
        ref_start_x = -30.0
        ref_start_y = -cfg.ch_len/2.0 - 8.0
        ref_end_x = 60.0
        ref_end_y = -70.0
        
        ref_dx = ref_end_x - ref_start_x
        ref_dy = ref_end_y - ref_start_y
        ref_length = (ref_dx**2 + ref_dy**2)**0.5
        ref_unit_dx = ref_dx / ref_length
        ref_unit_dy = ref_dy / ref_length
        
        # Calculate chamfer offsets
        chamfer_ratio = cfg.gate_chamfer_distance / ref_length
        tr_x_offset = chamfer_ratio * abs(ref_dx)
        tr_y_offset = chamfer_ratio * abs(ref_dy)
        bl_x_offset = tr_x_offset
        bl_y_offset = tr_y_offset
        
        # Create hexagon points
        hexagon_points = [
            Point(int(rect_left * DEFAULT_UNIT_SCALE), int(rect_top * DEFAULT_UNIT_SCALE)),
            Point(int((rect_right - tr_x_offset) * DEFAULT_UNIT_SCALE), int(rect_top * DEFAULT_UNIT_SCALE)),
            Point(int(rect_right * DEFAULT_UNIT_SCALE), int((rect_top - tr_y_offset) * DEFAULT_UNIT_SCALE)),
            Point(int(rect_right * DEFAULT_UNIT_SCALE), int(rect_bottom * DEFAULT_UNIT_SCALE)),
            Point(int((rect_left + bl_x_offset) * DEFAULT_UNIT_SCALE), int(rect_bottom * DEFAULT_UNIT_SCALE)),
            Point(int(rect_left * DEFAULT_UNIT_SCALE), int((rect_bottom + bl_y_offset) * DEFAULT_UNIT_SCALE))
        ]
        
        hexagon = Polygon(hexagon_points)
        
        # Combine both parts
        Region = self._get_region_class()
        region1 = Region(gate_part1)
        region2 = Region(hexagon)
        combined_gate = (region1 + region2).merged()
        
        cell.shapes(layer_id).insert(combined_gate)
    
    def create_channel_material(self, cell, x=0.0, y=0.0):
        """Create channel material layer"""
        layer_id = LAYER_DEFINITIONS['channel']['id']
        cfg = self.config
        
        channel = GeometryUtils.create_rectangle(
            x, y,
            cfg.ch_width,
            cfg.ch_len + cfg.channel_length_extension,
            center=True
        )
        cell.shapes(layer_id).insert(channel)
    
    def create_dielectric_layer(self, cell, x=0.0, y=0.0):
        """Create dielectric layer with windows on source and drain pads"""
        Region = self._get_region_class()
        layer_id = LAYER_DEFINITIONS['top_dielectric']['id']
        cfg = self.config
        
        # Main dielectric region
        dielectric_rect = GeometryUtils.create_rectangle(
            x, y,
            cfg.device_width,
            cfg.device_height,
            center=True
        )
        dielectric_region = Region(dielectric_rect)
        
        # Source window
        source_window_rect = GeometryUtils.create_rectangle(
            x + cfg.source_outer_x, y + cfg.source_outer_y,
            cfg.source_outer_length - cfg.dielectric_window_reduction,
            cfg.source_outer_width - cfg.dielectric_window_reduction,
            center=True
        )
        source_window_region = Region(source_window_rect)
        
        # Drain window
        drain_window_rect = GeometryUtils.create_rectangle(
            x + cfg.drain_outer_x, y + cfg.drain_outer_y,
            cfg.drain_outer_length - cfg.dielectric_window_reduction,
            cfg.drain_outer_width - cfg.dielectric_window_reduction,
            center=True
        )
        drain_window_region = Region(drain_window_rect)
        
        # Create windows by subtraction
        dielectric_region -= source_window_region
        dielectric_region -= drain_window_region
        
        cell.shapes(layer_id).insert(dielectric_region)
    
    def create_alignment_mark(self, cell, x=0.0, y=0.0):
        """Create top-right corner alignment mark"""
        layer_id = LAYER_DEFINITIONS['alignment_marks']['id']
        cfg = self.config
        
        mark_x = x + cfg.device_width/2 - cfg.mark_margin
        mark_y = y + cfg.device_height/2 - cfg.mark_margin
        
        marks = MarkUtils.sq_missing(mark_x, mark_y, cfg.mark_size)
        
        shapes = marks.get_shapes()
        if isinstance(shapes, list):
            for shape in shapes:
                cell.shapes(layer_id).insert(shape)
        else:
            cell.shapes(layer_id).insert(shapes)
    
    def create_device_label(self, cell, x, y, row, col, label_type=None):
        """Create A01 format device label"""
        if label_type is None:
            label_type = 'digital' if self.config.use_digital_display else 'textutils'
        
        if label_type == 'textutils':
            self._create_device_label_textutils(cell, x, y, row, col)
        elif label_type == 'digital':
            self._create_device_label_digital(cell, x, y, row, col)
        else:
            self._create_device_label_textutils(cell, x, y, row, col)
    
    def _get_column_label(self, col):
        """Generate column label: A-Z, a-z cycle"""
        if col < 26:
            return chr(ord('A') + col)
        elif col < 52:
            return chr(ord('a') + (col - 26))
        else:
            remainder = col % 52
            if remainder < 26:
                return chr(ord('A') + remainder)
            else:
                return chr(ord('a') + (remainder - 26))
    
    def _create_device_label_textutils(self, cell, x, y, row, col):
        """Create device label using TextUtils"""
        layer_id = LAYER_DEFINITIONS['labels']['id']
        cfg = self.config
        
        col_letter = self._get_column_label(col)
        row_number = f"{row:02d}"
        label = col_letter + row_number
        
        label_x = x + cfg.label_offset_x
        label_y = y + cfg.label_offset_y
        char_size = cfg.label_size
        char_spacing = char_size * cfg.label_spacing
        
        for i, char in enumerate(label):
            char_x = label_x + i * char_spacing
            char_y = label_y
            
            text_shapes = TextUtils.create_text_freetype(
                char, char_x, char_y, 
                size_um=int(char_size), 
                font_path=cfg.label_font,
                spacing_um=0.5
            )
            
            for shape in text_shapes:
                cell.shapes(layer_id).insert(shape)
    
    def _create_device_label_digital(self, cell, x, y, row, col):
        """Create device label using DigitalDisplay"""
        layer_id = LAYER_DEFINITIONS['labels']['id']
        cfg = self.config
        
        col_letter = self._get_column_label(col)
        row_number = f"{row:02d}"
        label = col_letter + row_number
        
        label_x = x + cfg.label_offset_x
        label_y = y + cfg.label_offset_y
        char_size = cfg.label_size * 0.25
        stroke_width = cfg.mark_width * 0.8
        char_spacing = char_size * 1.7
        
        for i, char in enumerate(label):
            char_x = label_x + i * char_spacing
            char_y = label_y
            
            polygons = DigitalDisplay.create_digit(
                char, char_x, char_y, 
                size=char_size, 
                stroke_width=stroke_width
            )
            
            for polygon in polygons:
                cell.shapes(layer_id).insert(polygon)
    
    def create_parameter_labels(self, cell, x, y, device_params):
        """Create parameter labels within device area"""
        layer_id = LAYER_DEFINITIONS['labels']['id']
        cfg = self.config
        
        start_x = x - cfg.device_width * 0.4
        start_y = y - cfg.device_height * 0.4
        
        param_texts = []
        if 'ch_width' in device_params:
            param_texts.append(f"W:{device_params['ch_width']:.1f}")
        if 'ch_len' in device_params:
            param_texts.append(f"L:{device_params['ch_len']:.1f}")
        
        line_spacing = 20.0
        for i, text in enumerate(param_texts):
            text_y = start_y - i * line_spacing
            text_obj = db.Text(
                text,
                int(start_x * 1000),
                int(text_y * 1000)
            )
            cell.shapes(layer_id).insert(text_obj)
    
    def create_single_device(self, cell_name="FET_Device", x=0, y=0, 
                            device_id=None, row=None, col=None, 
                            device_params=None, label_type=None):
        """
        Create single FET device
        
        Args:
            cell_name: Cell name
            x, y: Device center coordinates
            device_id: Device ID (optional)
            row: Row number (for generating A01 format label, starting from 1)
            col: Column number (for generating A01 format label, starting from 0)
            device_params: Device parameters dictionary for labeling
            label_type: Label type, 'textutils' or 'digital'
            
        Returns:
            Created cell
        """
        cell = self.layout.create_cell(cell_name)
        
        x = float(x)
        y = float(y)
        
        # Create device structure in layer order
        self.create_source_electrode(cell, x, y)
        self.create_drain_electrode(cell, x, y)
        self.create_gate_electrode(cell, x, y)
        self.create_channel_material(cell, x, y)
        self.create_dielectric_layer(cell, x, y)
        self.create_alignment_mark(cell, x, y)
        
        # Add device label if row/col provided
        if row is not None and col is not None:
            cfg = self.config
            mark_x = x + cfg.device_width/2 - cfg.mark_margin
            mark_y = y + cfg.device_height/2 - cfg.mark_margin
            label_x = mark_x + cfg.mark_size * 1.2
            label_y = mark_y
            self.create_device_label(cell, label_x, label_y, row, col, label_type)
        
        # Add parameter labels if provided
        if device_params:
            self.create_parameter_labels(cell, x, y, device_params)
        
        return cell
    
    def create_device_array(self, array_config=None, **kwargs):
        """
        Create device array with flexible configuration
        
        Args:
            array_config: ArrayConfig instance (optional, can pass parameters via kwargs)
            **kwargs: Array parameters (rows, cols, device_spacing_x, device_spacing_y, 
                     offset_x, offset_y, label_type, enable_labels, enable_param_labels)
            
        Returns:
            Array cell
            
        Example:
            # Simple array
            array = device.create_device_array(rows=10, cols=10)
            
            # Custom spacing
            array = device.create_device_array(
                rows=5, cols=5,
                device_spacing_x=350.0,
                device_spacing_y=200.0
            )
            
            # Using ArrayConfig
            config = ArrayConfig(rows=10, cols=10, offset_x=1000, offset_y=1000)
            array = device.create_device_array(array_config=config)
        """
        # Initialize or update array configuration
        if array_config is None:
            array_config = ArrayConfig(**kwargs)
        elif isinstance(array_config, ArrayConfig):
            if kwargs:
                for key, value in kwargs.items():
                    if hasattr(array_config, key):
                        setattr(array_config, key, value)
        else:
            raise TypeError("array_config must be an ArrayConfig instance or None")
        
        cfg = self.config
        
        # Calculate device spacing
        device_spacing_x = array_config.device_spacing_x or cfg.device_width
        device_spacing_y = array_config.device_spacing_y or cfg.device_height
        
        # Create array cell
        array_cell = self.layout.create_cell("FET_Array")
        
        # Create device array
        device_id = 1
        for row in range(array_config.rows):
            for col in range(array_config.cols):
                device_x = array_config.offset_x + col * device_spacing_x
                device_y = array_config.offset_y + row * device_spacing_y
                
                device_cell = self.create_single_device(
                    f"FET_{device_id:03d}", 
                    device_x, device_y, 
                    device_id,
                    row + 1 if array_config.enable_labels else None,
                    col if array_config.enable_labels else None,
                    None,
                    array_config.label_type
                )
                
                array_cell.insert(db.CellInstArray(
                    device_cell.cell_index(),
                    db.Trans(0, 0)
                ))
                
                device_id += 1
        
        return array_cell
    
    def create_parameter_scan_array(self, param_ranges, array_config=None, **kwargs):
        """
        Create parameter scan array with parameter variations
        
        Args:
            param_ranges: Parameter dictionary, format {'param_name': [min, max, steps]}
                         or {'param_name': [value1, value2, value3, ...]} for custom values
            array_config: ArrayConfig instance (optional)
            **kwargs: Array parameters (rows, cols, offset_x, offset_y, label_type, etc.)
            
        Returns:
            Parameter scan array cell
            
        Example:
            # Row scan for ch_len, column scan for ch_width
            param_ranges = {
                'ch_len': [1.0, 40.0, 27],      # Row: 27 values from 1.0 to 40.0
                'ch_width': [1.0, 40.0, 16],    # Column: 16 values from 1.0 to 40.0
            }
            scan_array = device.create_parameter_scan_array(
                param_ranges, 
                rows=27, cols=16,
                enable_param_labels=True
            )
            
            # Custom parameter values
            param_ranges = {
                'ch_len': [5.0, 10.0, 15.0, 20.0],  # 4 specific values
                'ch_width': [2.0, 4.0, 6.0, 8.0],   # 4 specific values
            }
            scan_array = device.create_parameter_scan_array(
                param_ranges, rows=4, cols=4
            )
        """
        # Initialize or update array configuration
        if array_config is None:
            array_config = ArrayConfig(**kwargs)
        elif isinstance(array_config, ArrayConfig):
            if kwargs:
                for key, value in kwargs.items():
                    if hasattr(array_config, key):
                        setattr(array_config, key, value)
        
        # Create scan cell
        scan_cell = self.layout.create_cell("FET_Parameter_Scan")
        
        cfg = self.config
        device_spacing_x = array_config.device_spacing_x or cfg.device_width
        device_spacing_y = array_config.device_spacing_y or cfg.device_height
        
        # Prepare parameter values
        param_values = {}
        for param_name, param_range in param_ranges.items():
            if len(param_range) == 3:
                # Format: [min, max, steps] - linear scan
                min_val, max_val, steps = param_range
                if steps > 1:
                    param_values[param_name] = [
                        min_val + i * (max_val - min_val) / (steps - 1)
                        for i in range(steps)
                    ]
                else:
                    param_values[param_name] = [min_val]
            else:
                # Format: [value1, value2, ...] - custom values
                param_values[param_name] = list(param_range)
        
        # Create device array
        device_id = 1
        for row in range(array_config.rows):
            for col in range(array_config.cols):
                # Get current device parameter values
                current_params = {}
                
                if 'ch_len' in param_values:
                    row_idx = min(row, len(param_values['ch_len']) - 1)
                    current_params['ch_len'] = param_values['ch_len'][row_idx]
                
                if 'ch_width' in param_values:
                    col_idx = min(col, len(param_values['ch_width']) - 1)
                    current_params['ch_width'] = param_values['ch_width'][col_idx]
                
                # Update device parameters
                if current_params:
                    self.set_device_parameters(**current_params)
                
                # Calculate device position
                device_x = array_config.offset_x + col * device_spacing_x
                device_y = array_config.offset_y + row * device_spacing_y
                
                # Create single device
                device_cell = self.create_single_device(
                    f"FET_Scan_{device_id:03d}", 
                    device_x, device_y, 
                    device_id,
                    row + 1 if array_config.enable_labels else None,
                    col if array_config.enable_labels else None,
                    current_params if array_config.enable_param_labels else None,
                    array_config.label_type
                )
                
                scan_cell.insert(db.CellInstArray(
                    device_cell.cell_index(),
                    db.Trans(0, 0)
                ))
                
                device_id += 1
        
        return scan_cell


def main():
    """Main function - demonstration and testing"""
    
    # Example 1: Create a single device with default parameters
    print("Example 1: Creating single device...")
    device1 = OrthChHighDenseFET()
    single_device = device1.create_single_device("FET_Single", 0, 0, 1, 1, 0)
    print(f"Single device created: {single_device.name}")
    
    # Example 2: Create device with custom configuration
    print("\nExample 2: Creating device with custom config...")
    custom_config = DeviceConfig(
        ch_width=10.0,
        ch_len=10.0,
        device_width=350.0,
        device_height=200.0
    )
    device2 = OrthChHighDenseFET(config=custom_config)
    custom_device = device2.create_single_device("FET_Custom", 0, 0)
    print(f"Custom device created: {custom_device.name}")
    
    # Example 3: Create simple array
    print("\nExample 3: Creating device array...")
    device3 = OrthChHighDenseFET()
    array = device3.create_device_array(rows=5, cols=5)
    print(f"Array created: {array.name}")
    
    # Example 4: Create parameter scan array
    print("\nExample 4: Creating parameter scan array...")
    device4 = OrthChHighDenseFET()
    param_ranges = {
        'ch_len': [1.0, 40.0, 27],      # Row scan: 27 values
        'ch_width': [1.0, 40.0, 16],    # Column scan: 16 values
    }
    scan_array = device4.create_parameter_scan_array(
        param_ranges, 
        rows=27, 
        cols=16,
        enable_param_labels=True
    )
    print(f"Parameter scan array created: {scan_array.name}")
    
    # Example 5: Using ArrayConfig for complex arrays
    print("\nExample 5: Using ArrayConfig...")
    device5 = OrthChHighDenseFET()
    array_config = ArrayConfig(
        rows=10,
        cols=10,
        device_spacing_x=350.0,
        device_spacing_y=200.0,
        offset_x=1000.0,
        offset_y=1000.0,
        enable_labels=True
    )
    complex_array = device5.create_device_array(array_config=array_config)
    print(f"Complex array created: {complex_array.name}")
    
    # Save layout file
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from config import get_gds_path
    
    output_file = get_gds_path("FET_Device_Examples.gds")
    device5.layout.write(output_file)
    print(f"\nLayout file saved: {output_file}")
    print("All examples completed!")


if __name__ == "__main__":
    main()
