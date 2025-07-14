# -*- coding: utf-8 -*-
"""
MOSFET器件模块 - 定义完整的双栅器件结构
MOSFET device module - defines the complete dual-gate device structure.
"""

import pya
from config import LAYER_DEFINITIONS
from components.electrode import GateElectrode, SourceDrainElectrode
from utils.geometry import GeometryUtils
from utils.text_utils import TextUtils
from utils.mark_utils import MarkUtils

class MOSFET:
    """MOSFET器件类
    
    MOSFET device class.
    """
    
    def __init__(self, x, y, **kwargs):
        self.x = x
        self.y = y
        
        # 器件参数
        # Device parameters
        self.channel_width = kwargs.get('channel_width', 5.0)
        self.channel_length = kwargs.get('channel_length', 20.0)
        self.gate_overlap = kwargs.get('gate_overlap', 2.0)
        self.source_drain_width = kwargs.get('source_drain_width', 8.0)
        self.source_drain_length = kwargs.get('source_drain_length', 6.0)
        self.dielectric_thickness = kwargs.get('dielectric_thickness', 4.0)
        
        # 电极配置
        # Electrode configuration
        self.bottom_gate_enabled = kwargs.get('bottom_gate_enabled', True)
        self.top_gate_enabled = kwargs.get('top_gate_enabled', True)
        self.source_drain_enabled = kwargs.get('source_drain_enabled', True)
        
        # 扇出配置
        # Fanout configuration
        self.fanout_enabled = kwargs.get('fanout_enabled', True)
        self.fanout_direction = kwargs.get('fanout_direction', 'horizontal')
        
        # 标签配置
        # Label configuration
        self.device_label = kwargs.get('device_label', '')
        self.device_id = kwargs.get('device_id', 0)
        
        # 生成的组件
        # Generated components
        self.components = {}
        self.shapes = {}
        
    def create_bottom_gate(self):
        """创建底栅电极
        
        Create the bottom gate electrode.
        """
        if not self.bottom_gate_enabled:
            return None
        
        gate_width = self.channel_width + 2 * self.gate_overlap
        gate_length = self.channel_length + 2 * self.gate_overlap
        
        # 确定扇出方向
        fanout_dir = 'left' if self.fanout_direction == 'horizontal' else 'down'
        
        bottom_gate = GateElectrode(
            x=self.x,
            y=self.y,
            width=gate_length,
            height=gate_width,
            layer_name='bottom_gate',
            gate_type='bottom',
            gate_overlap=self.gate_overlap,
            fanout_enabled=self.fanout_enabled,
            fanout_direction=fanout_dir,
            fanout_style='straight',
            fanout_length=30,
            process_notes=['底栅电极 - 第一层金属']
        )
        
        self.components['bottom_gate'] = bottom_gate
        return bottom_gate
    
    def create_channel_etch(self):
        """创建沟道刻蚀区域

        Create the channel etch region.
        """
        etch_width = self.channel_width + 1.0
        etch_length = self.channel_length + 1.0
        
        etch = GeometryUtils.create_rectangle(
            self.x, self.y, etch_length, etch_width, center=True
        )
        
        self.shapes['channel_etch'] = [etch]
        return etch
    
    def create_source_drain(self):
        """创建源漏电极

        Create source and drain electrodes.
        """
        if not self.source_drain_enabled:
            return None
        
        # 源极
        source_x = self.x - self.channel_length/2 - self.source_drain_length/2
        source = SourceDrainElectrode(
            x=source_x,
            y=self.y,
            width=self.source_drain_length,
            height=self.source_drain_width,
            layer_name='source_drain',
            electrode_type='source',
            fanout_enabled=self.fanout_enabled,
            fanout_direction='left',
            fanout_style='straight',
            fanout_length=25,
            process_notes=['源极电极 - 第二层金属']
        )
        
        # 漏极
        drain_x = self.x + self.channel_length/2 + self.source_drain_length/2
        drain = SourceDrainElectrode(
            x=drain_x,
            y=self.y,
            width=self.source_drain_length,
            height=self.source_drain_width,
            layer_name='source_drain',
            electrode_type='drain',
            fanout_enabled=self.fanout_enabled,
            fanout_direction='right',
            fanout_style='straight',
            fanout_length=25,
            process_notes=['漏极电极 - 第二层金属']
        )
        
        self.components['source'] = source
        self.components['drain'] = drain
        return source, drain
    
    def create_dielectric(self):
        """创建介电层

        Create the dielectric layer.
        """
        dielectric_width = self.channel_width + self.dielectric_thickness
        dielectric_length = self.channel_length + self.dielectric_thickness
        
        dielectric = GeometryUtils.create_rectangle(
            self.x, self.y, dielectric_length, dielectric_width, center=True
        )
        
        self.shapes['dielectric'] = [dielectric]
        return dielectric
    
    def create_top_gate(self):
        """创建顶栅电极

        Create the top gate electrode.
        """
        if not self.top_gate_enabled:
            return None
        
        gate_width = self.channel_width + 2 * self.gate_overlap
        gate_length = self.channel_length + 2 * self.gate_overlap
        
        # 确定扇出方向
        fanout_dir = 'right' if self.fanout_direction == 'horizontal' else 'up'
        
        top_gate = GateElectrode(
            x=self.x,
            y=self.y,
            width=gate_length,
            height=gate_width,
            layer_name='top_gate',
            gate_type='top',
            gate_overlap=self.gate_overlap,
            fanout_enabled=self.fanout_enabled,
            fanout_direction=fanout_dir,
            fanout_style='straight',
            fanout_length=30,
            process_notes=['顶栅电极 - 第三层金属']
        )
        
        self.components['top_gate'] = top_gate
        return top_gate
    
    def create_device_label(self):
        """创建器件标签

        Create the device label.
        """
        if not self.device_label:
            return None
        
        label_shapes = TextUtils.create_text(
            self.device_label, self.x, self.y + self.channel_width/2 + 10,
            'small', center=True
        )
        
        self.shapes['device_label'] = label_shapes
        return label_shapes
    
    def create_parameter_labels(self):
        """创建参数标签

        Create labels for device parameters.
        """
        labels = []
        
        # 沟道尺寸标签
        channel_text = f"W={self.channel_width}μm L={self.channel_length}μm"
        channel_label = TextUtils.create_text(
            channel_text, self.x, self.y - self.channel_width/2 - 15,
            'small', center=True
        )
        labels.extend(channel_label)
        
        # 器件ID标签
        if self.device_id > 0:
            id_text = f"ID: {self.device_id}"
            id_label = TextUtils.create_text(
                id_text, self.x, self.y - self.channel_width/2 - 30,
                'small', center=True
            )
            labels.extend(id_label)
        
        self.shapes['parameter_labels'] = labels
        return labels
    
    def create_alignment_marks(self):
        """创建器件对准标记

        Create alignment marks for the device.
        """
        mark_size = 15
        mark_width = 2
        
        # 四个角落的标记
        positions = [
            (self.x - self.channel_length/2 - 10, self.y - self.channel_width/2 - 10),
            (self.x + self.channel_length/2 + 10, self.y - self.channel_width/2 - 10),
            (self.x - self.channel_length/2 - 10, self.y + self.channel_width/2 + 10),
            (self.x + self.channel_length/2 + 10, self.y + self.channel_width/2 + 10)
        ]
        
        marks = []
        for pos_x, pos_y in positions:
            mark = MarkUtils.create_cross_mark(pos_x, pos_y, mark_size, mark_width)
            marks.append(mark)
        
        self.shapes['alignment_marks'] = marks
        return marks
    
    def generate(self):
        """生成完整的MOSFET器件"""
        # 创建各层结构
        self.create_bottom_gate()
        self.create_channel_etch()
        self.create_source_drain()
        self.create_dielectric()
        self.create_top_gate()
        
        # 创建标签和标记
        self.create_device_label()
        self.create_parameter_labels()
        self.create_alignment_marks()
        
        # 生成所有组件的形状
        for component_name, component in self.components.items():
            if component:
                component.generate()
        
        return self.get_all_shapes()
    
    def get_all_shapes(self):
        """获取所有形状"""
        all_shapes = {}
        
        # 收集组件形状
        for component_name, component in self.components.items():
            if component:
                all_shapes[component_name] = component.get_all_shapes()
        
        # 收集直接形状
        for shape_name, shapes in self.shapes.items():
            all_shapes[shape_name] = shapes
        
        return all_shapes
    
    def get_layer_shapes(self, layer_name):
        """获取指定图层的形状"""
        layer_id = LAYER_DEFINITIONS[layer_name]['id']
        layer_shapes = []
        
        # 从组件中收集
        for component_name, component in self.components.items():
            if component and component.layer_name == layer_name:
                layer_shapes.extend(component.get_all_shapes())
        
        # 从直接形状中收集
        if layer_name in self.shapes:
            layer_shapes.extend(self.shapes[layer_name])
        
        return layer_shapes
    
    def get_process_notes(self):
        """获取所有工艺备注"""
        notes = []
        for component_name, component in self.components.items():
            if component:
                notes.extend(component.get_process_notes())
        return notes
    
    def set_device_parameters(self, **kwargs):
        """设置器件参数"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def get_device_info(self):
        """获取器件信息"""
        return {
            'position': (self.x, self.y),
            'channel_width': self.channel_width,
            'channel_length': self.channel_length,
            'gate_overlap': self.gate_overlap,
            'device_label': self.device_label,
            'device_id': self.device_id,
            'components': list(self.components.keys()),
            'process_notes': self.get_process_notes()
        } 