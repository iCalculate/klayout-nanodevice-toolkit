# -*- coding: utf-8 -*-
"""
Layout generator core module.
"""

import os
import pya
from config import LAYER_DEFINITIONS, PROCESS_CONFIG
from components.mosfet import MOSFET
from utils.text_utils import TextUtils
from utils.mark_utils import MarkUtils


class LayoutGenerator:
    """Layout generator class."""

    def __init__(self):
        self.devices = []
        self.last_saved_path = None

        self.array_config = {
            'rows': 3,
            'cols': 3,
            'spacing_x': 100.0,
            'spacing_y': 100.0,
            'start_x': 0.0,
            'start_y': 0.0,
        }

        self.scan_config = {
            'channel_width_range': [3.0, 5.0, 7.0],
            'channel_length_range': [10.0, 20.0, 30.0],
            'gate_overlap_range': [1.0, 2.0, 3.0],
            'scan_type': 'grid',
        }

        self.device_config = {
            'enable_bottom_gate': True,
            'enable_top_gate': True,
            'enable_source_drain': True,
            'fanout_enabled': True,
            'fanout_direction': 'horizontal',
            'show_device_labels': True,
            'show_parameter_labels': True,
            'show_alignment_marks': True,
        }

        self._initialize_layout()

    def _initialize_layout(self):
        """Initialize or reset the in-memory layout."""
        self.layout = pya.Layout()
        self.layout.dbu = PROCESS_CONFIG['dbu']
        self.layer_indices = {}
        for layer_name, layer_info in LAYER_DEFINITIONS.items():
            self.layer_indices[layer_name] = self.layout.layer(layer_info['id'], 0, layer_name)
        self.top_cell = self.layout.create_cell("MOSFET_Array")

    def set_array_config(self, **kwargs):
        for key, value in kwargs.items():
            if key in self.array_config:
                self.array_config[key] = value

    def set_scan_config(self, **kwargs):
        for key, value in kwargs.items():
            if key in self.scan_config:
                self.scan_config[key] = value

    def set_device_config(self, **kwargs):
        for key, value in kwargs.items():
            if key in self.device_config:
                self.device_config[key] = value

    def create_device_array(self):
        rows = self.array_config['rows']
        cols = self.array_config['cols']
        spacing_x = self.array_config['spacing_x']
        spacing_y = self.array_config['spacing_y']
        start_x = self.array_config['start_x']
        start_y = self.array_config['start_y']

        device_id = 1
        for i in range(rows):
            for j in range(cols):
                x = start_x + j * spacing_x
                y = start_y + i * spacing_y
                params = self.get_device_parameters(i, j, device_id)
                device = MOSFET(x, y, **params)
                device.generate()
                self.devices.append(device)
                device_id += 1

        return self.devices

    def get_device_parameters(self, row, col, device_id):
        scan_type = self.scan_config['scan_type']

        if scan_type == 'grid':
            width_idx = col % len(self.scan_config['channel_width_range'])
            length_idx = row % len(self.scan_config['channel_length_range'])
            channel_width = self.scan_config['channel_width_range'][width_idx]
            channel_length = self.scan_config['channel_length_range'][length_idx]
        elif scan_type == 'random':
            import random
            channel_width = random.choice(self.scan_config['channel_width_range'])
            channel_length = random.choice(self.scan_config['channel_length_range'])
        elif scan_type == 'custom':
            total_devices = self.array_config['rows'] * self.array_config['cols']
            progress = (row * self.array_config['cols'] + col) / max(total_devices - 1, 1)
            width_min = min(self.scan_config['channel_width_range'])
            width_max = max(self.scan_config['channel_width_range'])
            length_min = min(self.scan_config['channel_length_range'])
            length_max = max(self.scan_config['channel_length_range'])
            channel_width = width_min + progress * (width_max - width_min)
            channel_length = length_min + progress * (length_max - length_min)
        else:
            channel_width = self.scan_config['channel_width_range'][0]
            channel_length = self.scan_config['channel_length_range'][0]

        return {
            'channel_width': channel_width,
            'channel_length': channel_length,
            'gate_overlap': self.scan_config['gate_overlap_range'][0],
            'device_label': f"D{device_id}",
            'device_id': device_id,
            'enable_bottom_gate': self.device_config['enable_bottom_gate'],
            'enable_top_gate': self.device_config['enable_top_gate'],
            'enable_source_drain': self.device_config['enable_source_drain'],
            'fanout_enabled': self.device_config['fanout_enabled'],
            'fanout_direction': self.device_config['fanout_direction'],
            'show_device_labels': self.device_config['show_device_labels'],
            'show_parameter_labels': self.device_config['show_parameter_labels'],
            'show_alignment_marks': self.device_config['show_alignment_marks'],
        }

    def create_global_alignment_marks(self):
        rows = self.array_config['rows']
        cols = self.array_config['cols']
        spacing_x = self.array_config['spacing_x']
        spacing_y = self.array_config['spacing_y']
        start_x = self.array_config['start_x']
        start_y = self.array_config['start_y']

        end_x = start_x + (cols - 1) * spacing_x
        end_y = start_y + (rows - 1) * spacing_y

        corner_positions = [
            (start_x - 50, start_y - 50),
            (end_x + 50, start_y - 50),
            (start_x - 50, end_y + 50),
            (end_x + 50, end_y + 50),
        ]

        marks = []
        for pos_x, pos_y in corner_positions:
            corner_marks = MarkUtils.create_corner_marks(pos_x, pos_y, 40, 'L_shape', 3)
            marks.extend(corner_marks)

        return marks

    def create_global_labels(self):
        labels = []
        title_shapes = TextUtils.create_bold_text("2D Dual-Gate MOSFET Array", 0, 150, 'title', center=True)
        labels.extend(title_shapes)

        array_info = f"Array: {self.array_config['rows']}x{self.array_config['cols']}"
        labels.extend(TextUtils.create_text(array_info, 0, 140, 'default', center=True))

        scan_info = f"Scan Type: {self.scan_config['scan_type']}"
        labels.extend(TextUtils.create_text(scan_info, 0, 130, 'default', center=True))

        width_range = f"W: {min(self.scan_config['channel_width_range'])}-{max(self.scan_config['channel_width_range'])}um"
        length_range = f"L: {min(self.scan_config['channel_length_range'])}-{max(self.scan_config['channel_length_range'])}um"
        labels.extend(TextUtils.create_text(width_range, 0, 120, 'default', center=True))
        labels.extend(TextUtils.create_text(length_range, 0, 110, 'default', center=True))

        return labels

    def create_parameter_table(self):
        labels = []
        labels.extend(TextUtils.create_bold_text("Device Parameters", -200, 80, 'default', center=True))

        y_pos = 70
        for device in self.devices[:10]:
            info = device.get_device_info()
            text = f"D{info['device_id']}: W={info['channel_width']}um L={info['channel_length']}um"
            labels.extend(TextUtils.create_text(text, -200, y_pos, 'small', center=True))
            y_pos -= 8

        if len(self.devices) > 10:
            labels.extend(TextUtils.create_text(f"... and {len(self.devices) - 10} more devices", -200, y_pos, 'small', center=True))

        return labels

    def insert_shapes_to_layout(self):
        for device in self.devices:
            all_shapes = device.get_all_shapes()
            for component_name, shapes in all_shapes.items():
                if not isinstance(shapes, list):
                    continue
                for shape in shapes:
                    if component_name == 'bottom_gate':
                        self.top_cell.shapes(self.layer_indices['bottom_gate']).insert(shape)
                    elif component_name in ['source', 'drain']:
                        self.top_cell.shapes(self.layer_indices['source_drain']).insert(shape)
                    elif component_name == 'top_gate':
                        self.top_cell.shapes(self.layer_indices['top_gate']).insert(shape)

        for device in self.devices:
            for shape_name, shapes in device.shapes.items():
                if shape_name == 'channel':
                    for shape in shapes:
                        self.top_cell.shapes(self.layer_indices['channel']).insert(shape)
                elif shape_name == 'top_dielectric':
                    for shape in shapes:
                        self.top_cell.shapes(self.layer_indices['top_dielectric']).insert(shape)
                elif shape_name in ['device_label', 'parameter_labels']:
                    for shape in shapes:
                        self.top_cell.shapes(self.layer_indices['labels']).insert(shape)
                elif shape_name == 'alignment_marks':
                    for shape in shapes:
                        self.top_cell.shapes(self.layer_indices['alignment_marks']).insert(shape)

        for mark in self.create_global_alignment_marks():
            self.top_cell.shapes(self.layer_indices['alignment_marks']).insert(mark)

        for label in self.create_global_labels():
            self.top_cell.shapes(self.layer_indices['labels']).insert(label)

        for label in self.create_parameter_table():
            self.top_cell.shapes(self.layer_indices['labels']).insert(label)

    def generate_layout(self):
        print("开始生成MOSFET阵列版图...")

        self.devices = []
        self._initialize_layout()

        self.create_device_array()
        self.insert_shapes_to_layout()

        print("版图生成完成！")
        print(f"器件数量: {len(self.devices)}")
        print(f"阵列大小: {self.array_config['rows']}x{self.array_config['cols']}")
        print(f"扫描类型: {self.scan_config['scan_type']}")

        return self.layout

    def save_layout(self, filename="mosfet_array.gds"):
        if not os.path.isabs(filename):
            from config import get_gds_path
            filename = get_gds_path(filename)
        self.layout.write(filename)
        self.last_saved_path = filename
        print(f"版图已保存为: {filename}")

    def load_to_gui(self, filename=None):
        try:
            if filename is None:
                if self.last_saved_path:
                    filename = self.last_saved_path
                else:
                    from config import get_gds_path
                    filename = get_gds_path("mosfet_array.gds")

            main_window = pya.Application.instance().main_window()
            main_window.load_layout(filename, 0)
            print("版图已成功加载到GUI视图中！")
        except Exception as e:
            print(f"加载到GUI时出现错误: {e}")
            print(f"请手动在KLayout中打开文件: {filename}")

    def get_statistics(self):
        return {
            'total_devices': len(self.devices),
            'array_size': f"{self.array_config['rows']}x{self.array_config['cols']}",
            'scan_type': self.scan_config['scan_type'],
            'parameter_ranges': {
                'channel_width': self.scan_config['channel_width_range'],
                'channel_length': self.scan_config['channel_length_range'],
                'gate_overlap': self.scan_config['gate_overlap_range'],
            },
            'layout_size': {
                'width': self.array_config['cols'] * self.array_config['spacing_x'],
                'height': self.array_config['rows'] * self.array_config['spacing_y'],
            },
        }
