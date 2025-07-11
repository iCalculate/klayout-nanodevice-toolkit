# -*- coding: utf-8 -*-
"""
电极组件模块 - 支持多种形状和扇出配置
"""

import pya
from config import LAYER_DEFINITIONS, ELECTRODE_SHAPES, FANOUT_CONFIG
from utils.geometry import GeometryUtils

class Electrode:
    """电极基类"""
    
    def __init__(self, x, y, width, height, layer_name, shape='rectangle', **kwargs):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.layer_name = layer_name
        self.shape = shape
        self.layer_id = LAYER_DEFINITIONS[layer_name]['id']
        
        # 形状相关参数
        self.radius = kwargs.get('radius', 0)  # 圆角半径
        self.angle = kwargs.get('angle', 0)    # 旋转角度
        
        # 扇出配置
        self.fanout_enabled = kwargs.get('fanout_enabled', FANOUT_CONFIG['enabled'])
        self.fanout_direction = kwargs.get('fanout_direction', 'left')
        self.fanout_style = kwargs.get('fanout_style', 'straight')
        self.fanout_length = kwargs.get('fanout_length', 50)
        self.fanout_width = kwargs.get('fanout_width', FANOUT_CONFIG['wire_width'])
        self.pad_size = kwargs.get('pad_size', FANOUT_CONFIG['pad_size'])
        
        # 工艺备注
        self.process_notes = kwargs.get('process_notes', [])
        
        # 生成的形状
        self.shapes = []
        self.fanout_shapes = []
        self.pad_shapes = []
        
    def create_shape(self):
        """创建电极主体形状"""
        if self.shape == 'rectangle':
            shape = GeometryUtils.create_rectangle(self.x, self.y, self.width, self.height, center=True)
        elif self.shape == 'rounded':
            shape = GeometryUtils.create_rounded_rectangle(self.x, self.y, self.width, self.height, self.radius, center=True)
        elif self.shape == 'octagon':
            shape = GeometryUtils.create_octagon(self.x, self.y, self.width, self.height, center=True)
        elif self.shape == 'ellipse':
            shape = GeometryUtils.create_ellipse(self.x, self.y, self.width, self.height, center=True)
        else:
            # 默认矩形
            shape = GeometryUtils.create_rectangle(self.x, self.y, self.width, self.height, center=True)
        
        # 应用旋转
        if self.angle != 0:
            import math
            cos_a = math.cos(self.angle)
            sin_a = math.sin(self.angle)
            trans = pya.Trans(cos_a, sin_a, -sin_a, cos_a, self.x, self.y)
            shape = shape.transformed(trans)
        
        self.shapes.append(shape)
        return shape
    
    def create_fanout(self):
        """创建扇出引线"""
        if not self.fanout_enabled:
            return []
        
        # 计算扇出起点（电极边缘）
        if self.fanout_direction == 'left':
            start_x = self.x - self.width / 2
            start_y = self.y
            end_x = start_x - self.fanout_length
            end_y = start_y
        elif self.fanout_direction == 'right':
            start_x = self.x + self.width / 2
            start_y = self.y
            end_x = start_x + self.fanout_length
            end_y = start_y
        elif self.fanout_direction == 'up':
            start_x = self.x
            start_y = self.y + self.height / 2
            end_x = start_x
            end_y = start_y + self.fanout_length
        elif self.fanout_direction == 'down':
            start_x = self.x
            start_y = self.y - self.height / 2
            end_x = start_x
            end_y = start_y - self.fanout_length
        else:
            return []
        
        # 创建引线
        if self.fanout_style == 'straight':
            wire = GeometryUtils.create_rectangle(
                (start_x + end_x) / 2, (start_y + end_y) / 2,
                abs(end_x - start_x) + self.fanout_width, self.fanout_width,
                center=True
            )
        elif self.fanout_style == 'curved':
            wire = GeometryUtils.create_curved_wire(start_x, start_y, end_x, end_y, self.fanout_width)
        elif self.fanout_style == 'stepped':
            wire = GeometryUtils.create_stepped_wire(start_x, start_y, end_x, end_y, self.fanout_width)
        else:
            wire = GeometryUtils.create_rectangle(
                (start_x + end_x) / 2, (start_y + end_y) / 2,
                abs(end_x - start_x) + self.fanout_width, self.fanout_width,
                center=True
            )
        
        self.fanout_shapes.append(wire)
        return wire
    
    def create_pad(self):
        """创建测试焊盘"""
        if not self.fanout_enabled:
            return None
        
        # 计算焊盘位置
        if self.fanout_direction == 'left':
            pad_x = self.x - self.width / 2 - self.fanout_length
            pad_y = self.y
        elif self.fanout_direction == 'right':
            pad_x = self.x + self.width / 2 + self.fanout_length
            pad_y = self.y
        elif self.fanout_direction == 'up':
            pad_x = self.x
            pad_y = self.y + self.height / 2 + self.fanout_length
        elif self.fanout_direction == 'down':
            pad_x = self.x
            pad_y = self.y - self.height / 2 - self.fanout_length
        else:
            return None
        
        # 创建焊盘
        pad = GeometryUtils.create_rectangle(pad_x, pad_y, self.pad_size, self.pad_size, center=True)
        self.pad_shapes.append(pad)
        return pad
    
    def generate(self):
        """生成完整的电极结构"""
        # 创建主体
        self.create_shape()
        
        # 创建扇出
        self.create_fanout()
        
        # 创建焊盘
        self.create_pad()
        
        return self.shapes + self.fanout_shapes + self.pad_shapes
    
    def get_all_shapes(self):
        """获取所有形状"""
        return self.shapes + self.fanout_shapes + self.pad_shapes
    
    def add_process_note(self, note):
        """添加工艺备注"""
        self.process_notes.append(note)
    
    def get_process_notes(self):
        """获取工艺备注"""
        return self.process_notes

class GateElectrode(Electrode):
    """栅极电极类"""
    
    def __init__(self, x, y, width, height, layer_name, gate_type='bottom', **kwargs):
        super().__init__(x, y, width, height, layer_name, **kwargs)
        self.gate_type = gate_type  # 'bottom' 或 'top'
        self.gate_overlap = kwargs.get('gate_overlap', 2.0)
        self.contact_size = kwargs.get('contact_size', 3.0)
        
    def create_gate_contact(self):
        """创建栅极接触"""
        if self.gate_type == 'bottom':
            contact_x = self.x - self.width / 2 - self.gate_overlap
            contact_y = self.y
        else:  # top
            contact_x = self.x + self.width / 2 + self.gate_overlap
            contact_y = self.y
        
        contact = GeometryUtils.create_rectangle(
            contact_x, contact_y, self.contact_size, self.contact_size, center=True
        )
        self.shapes.append(contact)
        return contact

class SourceDrainElectrode(Electrode):
    """源漏电极类"""
    
    def __init__(self, x, y, width, height, layer_name, electrode_type='source', **kwargs):
        super().__init__(x, y, width, height, layer_name, **kwargs)
        self.electrode_type = electrode_type  # 'source' 或 'drain'
        self.contact_size = kwargs.get('contact_size', 3.0)
        
    def create_contact(self):
        """创建源漏接触"""
        if self.electrode_type == 'source':
            contact_x = self.x - self.width / 2 - self.contact_size
            contact_y = self.y
        else:  # drain
            contact_x = self.x + self.width / 2 + self.contact_size
            contact_y = self.y
        
        contact = GeometryUtils.create_rectangle(
            contact_x, contact_y, self.contact_size, self.contact_size, center=True
        )
        self.shapes.append(contact)
        return contact

class PadElectrode(Electrode):
    """焊盘电极类"""
    
    def __init__(self, x, y, size, layer_name='pads', **kwargs):
        super().__init__(x, y, size, size, layer_name, shape='rounded', **kwargs)
        self.pad_label = kwargs.get('pad_label', '')
        self.pad_number = kwargs.get('pad_number', 0)
        
    def create_pad_label(self):
        """创建焊盘标签"""
        if self.pad_label:
            from utils.text_utils import TextUtils
            label_shapes = TextUtils.create_text(
                self.pad_label, self.x, self.y - self.height/2 - 5, 'small', center=True
            )
            return label_shapes
        return [] 