# -*- coding: utf-8 -*-
"""
版图生成器主模块 - 实现阵列排布和参数扫描
"""

import pya
from config import LAYER_DEFINITIONS, PROCESS_CONFIG
from components.mosfet import MOSFET
from utils.text_utils import TextUtils
from utils.mark_utils import MarkUtils
from utils.geometry import GeometryUtils

class LayoutGenerator:
    """版图生成器类"""
    
    def __init__(self):
        # 创建新的布局
        self.layout = pya.Layout()
        self.layout.dbu = PROCESS_CONFIG['dbu']
        
        # 创建图层
        for layer_name, layer_info in LAYER_DEFINITIONS.items():
            self.layout.layer(layer_info['id'], 0, layer_name)
        
        # 获取顶层单元
        self.top_cell = self.layout.create_cell("MOSFET_Array")
        
        # 器件列表
        self.devices = []
        
        # 阵列配置
        self.array_config = {
            'rows': 3,
            'cols': 3,
            'spacing_x': 100.0,
            'spacing_y': 100.0,
            'start_x': 0.0,
            'start_y': 0.0
        }
        
        # 参数扫描配置
        self.scan_config = {
            'channel_width_range': [3.0, 5.0, 7.0],
            'channel_length_range': [10.0, 20.0, 30.0],
            'gate_overlap_range': [1.0, 2.0, 3.0],
            'scan_type': 'grid'  # 'grid', 'random', 'custom'
        }
        
    def set_array_config(self, **kwargs):
        """设置阵列配置"""
        for key, value in kwargs.items():
            if key in self.array_config:
                self.array_config[key] = value
    
    def set_scan_config(self, **kwargs):
        """设置参数扫描配置"""
        for key, value in kwargs.items():
            if key in self.scan_config:
                self.scan_config[key] = value
    
    def create_device_array(self):
        """创建器件阵列"""
        rows = self.array_config['rows']
        cols = self.array_config['cols']
        spacing_x = self.array_config['spacing_x']
        spacing_y = self.array_config['spacing_y']
        start_x = self.array_config['start_x']
        start_y = self.array_config['start_y']
        
        device_id = 1
        
        for i in range(rows):
            for j in range(cols):
                # 计算器件位置
                x = start_x + j * spacing_x
                y = start_y + i * spacing_y
                
                # 根据扫描类型确定参数
                params = self.get_device_parameters(i, j, device_id)
                
                # 创建器件
                device = MOSFET(x, y, **params)
                device.generate()
                
                self.devices.append(device)
                device_id += 1
        
        return self.devices
    
    def get_device_parameters(self, row, col, device_id):
        """根据扫描配置获取器件参数"""
        scan_type = self.scan_config['scan_type']
        
        if scan_type == 'grid':
            # 网格扫描
            width_idx = col % len(self.scan_config['channel_width_range'])
            length_idx = row % len(self.scan_config['channel_length_range'])
            
            channel_width = self.scan_config['channel_width_range'][width_idx]
            channel_length = self.scan_config['channel_length_range'][length_idx]
            
        elif scan_type == 'random':
            # 随机参数
            import random
            channel_width = random.choice(self.scan_config['channel_width_range'])
            channel_length = random.choice(self.scan_config['channel_length_range'])
            
        elif scan_type == 'custom':
            # 自定义参数（线性变化）
            total_devices = self.array_config['rows'] * self.array_config['cols']
            progress = (row * self.array_config['cols'] + col) / (total_devices - 1)
            
            width_min, width_max = min(self.scan_config['channel_width_range']), max(self.scan_config['channel_width_range'])
            length_min, length_max = min(self.scan_config['channel_length_range']), max(self.scan_config['channel_length_range'])
            
            channel_width = width_min + progress * (width_max - width_min)
            channel_length = length_min + progress * (length_max - length_min)
            
        else:
            # 默认参数
            channel_width = self.scan_config['channel_width_range'][0]
            channel_length = self.scan_config['channel_length_range'][0]
        
        return {
            'channel_width': channel_width,
            'channel_length': channel_length,
            'gate_overlap': self.scan_config['gate_overlap_range'][0],
            'device_label': f"D{device_id}",
            'device_id': device_id,
            'fanout_enabled': True,
            'fanout_direction': 'horizontal'
        }
    
    def create_global_alignment_marks(self):
        """创建全局对准标记"""
        # 计算阵列边界
        rows = self.array_config['rows']
        cols = self.array_config['cols']
        spacing_x = self.array_config['spacing_x']
        spacing_y = self.array_config['spacing_y']
        start_x = self.array_config['start_x']
        start_y = self.array_config['start_y']
        
        end_x = start_x + (cols - 1) * spacing_x
        end_y = start_y + (rows - 1) * spacing_y
        
        # 创建四个角落的对准标记
        corner_positions = [
            (start_x - 50, start_y - 50),  # 左上
            (end_x + 50, start_y - 50),    # 右上
            (start_x - 50, end_y + 50),    # 左下
            (end_x + 50, end_y + 50)       # 右下
        ]
        
        marks = []
        for pos_x, pos_y in corner_positions:
            corner_marks = MarkUtils.create_corner_marks(pos_x, pos_y, 40, 'L_shape', 3)
            marks.extend(corner_marks)
        
        return marks
    
    def create_global_labels(self):
        """创建全局标签"""
        labels = []
        
        # 主标题
        title = "2D Dual-Gate MOSFET Array"
        title_shapes = TextUtils.create_bold_text(title, 0, 150, 'title', center=True)
        labels.extend(title_shapes)
        
        # 阵列信息
        array_info = f"Array: {self.array_config['rows']}×{self.array_config['cols']}"
        array_shapes = TextUtils.create_text(array_info, 0, 140, 'default', center=True)
        labels.extend(array_shapes)
        
        # 扫描信息
        scan_info = f"Scan Type: {self.scan_config['scan_type']}"
        scan_shapes = TextUtils.create_text(scan_info, 0, 130, 'default', center=True)
        labels.extend(scan_shapes)
        
        # 参数范围信息
        width_range = f"W: {min(self.scan_config['channel_width_range'])}-{max(self.scan_config['channel_width_range'])}μm"
        length_range = f"L: {min(self.scan_config['channel_length_range'])}-{max(self.scan_config['channel_length_range'])}μm"
        
        width_shapes = TextUtils.create_text(width_range, 0, 120, 'default', center=True)
        length_shapes = TextUtils.create_text(length_range, 0, 110, 'default', center=True)
        
        labels.extend(width_shapes)
        labels.extend(length_shapes)
        
        return labels
    
    def create_parameter_table(self):
        """创建参数表格"""
        labels = []
        
        # 表格标题
        table_title = "Device Parameters"
        title_shapes = TextUtils.create_bold_text(table_title, -200, 80, 'default', center=True)
        labels.extend(title_shapes)
        
        # 表格内容
        y_pos = 70
        for i, device in enumerate(self.devices[:10]):  # 只显示前10个器件
            info = device.get_device_info()
            device_text = f"D{info['device_id']}: W={info['channel_width']}μm L={info['channel_length']}μm"
            text_shapes = TextUtils.create_text(device_text, -200, y_pos, 'small', center=True)
            labels.extend(text_shapes)
            y_pos -= 8
        
        if len(self.devices) > 10:
            more_text = f"... and {len(self.devices) - 10} more devices"
            more_shapes = TextUtils.create_text(more_text, -200, y_pos, 'small', center=True)
            labels.extend(more_shapes)
        
        return labels
    
    def insert_shapes_to_layout(self):
        """将所有形状插入到布局中"""
        # 插入器件形状
        for device in self.devices:
            all_shapes = device.get_all_shapes()
            
            # 插入组件形状
            for component_name, shapes in all_shapes.items():
                if isinstance(shapes, list):
                    for shape in shapes:
                        if hasattr(shape, 'layer_name'):
                            layer_id = LAYER_DEFINITIONS[shape.layer_name]['id']
                            self.top_cell.shapes(layer_id).insert(shape)
                        else:
                            # 直接形状，需要确定图层
                            if component_name == 'bottom_gate':
                                self.top_cell.shapes(LAYER_DEFINITIONS['bottom_gate']['id']).insert(shape)
                            elif component_name == 'source' or component_name == 'drain':
                                self.top_cell.shapes(LAYER_DEFINITIONS['source_drain']['id']).insert(shape)
                            elif component_name == 'top_gate':
                                self.top_cell.shapes(LAYER_DEFINITIONS['top_gate']['id']).insert(shape)
        
        # 插入直接形状
        for device in self.devices:
            for shape_name, shapes in device.shapes.items():
                if shape_name == 'channel_etch':
                    for shape in shapes:
                        self.top_cell.shapes(LAYER_DEFINITIONS['channel_etch']['id']).insert(shape)
                elif shape_name == 'dielectric':
                    for shape in shapes:
                        self.top_cell.shapes(LAYER_DEFINITIONS['dielectric']['id']).insert(shape)
                elif shape_name in ['device_label', 'parameter_labels']:
                    for shape in shapes:
                        self.top_cell.shapes(LAYER_DEFINITIONS['labels']['id']).insert(shape)
                elif shape_name == 'alignment_marks':
                    for shape in shapes:
                        self.top_cell.shapes(LAYER_DEFINITIONS['alignment_marks']['id']).insert(shape)
        
        # 插入全局标记和标签
        global_marks = self.create_global_alignment_marks()
        for mark in global_marks:
            self.top_cell.shapes(LAYER_DEFINITIONS['alignment_marks']['id']).insert(mark)
        
        global_labels = self.create_global_labels()
        for label in global_labels:
            self.top_cell.shapes(LAYER_DEFINITIONS['labels']['id']).insert(label)
        
        parameter_labels = self.create_parameter_table()
        for label in parameter_labels:
            self.top_cell.shapes(LAYER_DEFINITIONS['labels']['id']).insert(label)
    
    def generate_layout(self):
        """生成完整版图

        Generate the complete layout.
        """
        print("开始生成MOSFET阵列版图...")  # Starting layout generation
        
        # 创建器件阵列
        self.create_device_array()
        
        # 插入所有形状到布局
        self.insert_shapes_to_layout()
        
        print(f"版图生成完成！")  # Layout generation finished
        print(f"器件数量: {len(self.devices)}")  # Number of devices
        print(f"阵列大小: {self.array_config['rows']}×{self.array_config['cols']}")  # Array size
        print(f"扫描类型: {self.scan_config['scan_type']}")  # Scan type
        
        return self.layout
    
    def save_layout(self, filename="mosfet_array.gds"):
        """保存版图文件"""
        self.layout.write(filename)
        print(f"版图已保存为: {filename}")
    
    def load_to_gui(self):
        """加载版图到GUI

        Load the generated layout into the GUI.
        """
        try:
            # 获取主窗口
            # Get the main window instance
            main_window = pya.Application.instance().main_window()
            
            # 加载版图到GUI
            # Load layout into the GUI
            main_window.load_layout("mosfet_array.gds", 0)
            
            print("版图已成功加载到GUI视图中！")  # Layout loaded successfully
            
        except Exception as e:
            print(f"加载到GUI时出现错误: {e}")  # Error when loading into GUI
            print("请手动在KLayout中打开 mosfet_array.gds 文件")  # Please open manually
    
    def get_statistics(self):
        """获取版图统计信息"""
        stats = {
            'total_devices': len(self.devices),
            'array_size': f"{self.array_config['rows']}×{self.array_config['cols']}",
            'scan_type': self.scan_config['scan_type'],
            'parameter_ranges': {
                'channel_width': self.scan_config['channel_width_range'],
                'channel_length': self.scan_config['channel_length_range'],
                'gate_overlap': self.scan_config['gate_overlap_range']
            },
            'layout_size': {
                'width': self.array_config['cols'] * self.array_config['spacing_x'],
                'height': self.array_config['rows'] * self.array_config['spacing_y']
            }
        }
        return stats 