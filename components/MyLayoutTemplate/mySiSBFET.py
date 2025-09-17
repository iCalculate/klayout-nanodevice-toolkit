# -*- coding: utf-8 -*-
"""
FET器件组件模块 - 基于KLayout的场效应晶体管版图生成器
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import klayout.db as db
from utils.geometry import GeometryUtils
from utils.mark_utils import MarkUtils
from utils.fanout_utils import draw_pad, draw_trapezoidal_fanout
from utils.text_utils import TextUtils
from utils.digital_utils import DigitalDisplay
from config import LAYER_DEFINITIONS, DEFAULT_UNIT_SCALE

class FET:
    """场效应晶体管器件类"""
    
    def __init__(self, layout=None, **kwargs):
        """
        初始化FET器件类
        
        Args:
            layout: KLayout布局对象，如果为None则创建新的
            **kwargs: 其他参数，包括器件、标记、扇出、编号等相关参数
        """
        self.layout = layout or db.Layout()
        self.setup_layers()
        
        # ===== 器件核心参数 =====
        self.ch_len = kwargs.get('ch_len', 16.0)           # 沟道长度 (μm)
        self.ch_width = kwargs.get('ch_width', 5.0)        # 沟道宽度 (μm)
        self.gate_space = kwargs.get('gate_space', 20.0)   # 栅极边缘到边缘间距 (μm)
        self.gate_width = kwargs.get('gate_width', 15.0)   # 栅极宽度 (μm)
        
        # ===== 器件边界参数 =====
        self.device_margin_x = kwargs.get('device_margin_x', 170.0)  # 器件核心区域横向边界距离 (μm)
        self.device_margin_y = kwargs.get('device_margin_y', 170.0)  # 器件核心区域纵向边界距离 (μm)
        self.mark_margin = kwargs.get('mark_margin', 0.0)           # 标记中心点距离边界收缩距离 (μm)
        
        # ===== 标记参数 =====
        self.mark_size = kwargs.get('mark_size', 20.0)              # 标记尺寸 (μm)
        self.mark_width = kwargs.get('mark_width', 2.0)             # 标记线宽 (μm)
        # 四个角落的标记类型，对应MarkUtils中的函数名:
        # 'cross', 'square', 'circle', 'diamond', 'triangle', 'l', 't', 
        # 'semi_cross', 'cross_pos', 'cross_neg', 'l_shape', 't_shape',
        # 'sq_missing', 'sq_missing_border', 'cross_tri', 'regular_polygon', 'chamfered_octagon'
        self.mark_types = kwargs.get('mark_types', ['sq_missing', 'l', 'l', 'cross_tri'])  # [左上, 右上, 左下, 右下]
        # 四个角落标记的旋转角度: 0=不旋转, 1=90度, 2=180度, 3=270度
        self.mark_rotations = kwargs.get('mark_rotations', [0, 0, 2, 1])  # [左上, 右上, 左下, 右下]
        
        # ===== 扇出参数 =====
        self.outer_pad_size = kwargs.get('outer_pad_size', 100.0)   # 外部焊盘尺寸 (μm)
        self.chamfer_size = kwargs.get('chamfer_size', 10.0)        # 倒角尺寸 (μm)
        self.chamfer_type = kwargs.get('chamfer_type', 'straight')  # 倒角类型: 'straight', 'rounded', 'none'
        
        # ===== 电极参数 =====
        # 底栅电极参数
        self.bottom_gate_inner_width_ratio = kwargs.get('bottom_gate_inner_width_ratio', 1.5)  # 内焊盘宽度相对于沟道宽度的比例
        self.bottom_gate_outer_offset_x = kwargs.get('bottom_gate_outer_offset_x', 50.0)      # 外焊盘X偏移 (μm)
        self.bottom_gate_outer_offset_y = kwargs.get('bottom_gate_outer_offset_y', -100.0)    # 外焊盘Y偏移 (μm)
        self.bottom_gate_inner_chamfer = kwargs.get('bottom_gate_inner_chamfer', 'none')      # 内焊盘倒角类型
        self.bottom_gate_outer_chamfer = kwargs.get('bottom_gate_outer_chamfer', 'straight')  # 外焊盘倒角类型
        
        # 源漏电极参数
        self.source_drain_inner_width_ratio = kwargs.get('source_drain_inner_width_ratio', 1.2)  # 内焊盘宽度相对于沟道宽度的比例
        self.source_drain_outer_offset_x = kwargs.get('source_drain_outer_offset_x', 110.0)     # 外焊盘X偏移 (μm)
        self.source_drain_outer_offset_y = kwargs.get('source_drain_outer_offset_y', 20.0)     # 外焊盘Y偏移 (μm)
        self.source_drain_inner_chamfer = kwargs.get('source_drain_inner_chamfer', 'none')      # 内焊盘倒角类型
        self.source_drain_outer_chamfer = kwargs.get('source_drain_outer_chamfer', 'straight')  # 外焊盘倒角类型
        
        # 顶栅电极参数
        self.top_gate_inner_width_ratio = kwargs.get('top_gate_inner_width_ratio', 1.2)  # 内焊盘宽度相对于沟道宽度的比例
        self.top_gate_outer_offset_x = kwargs.get('top_gate_outer_offset_x', 0.0)        # 外焊盘X偏移 (μm)
        self.top_gate_outer_offset_y = kwargs.get('top_gate_outer_offset_y', 100.0)      # 外焊盘Y偏移 (μm)
        self.top_gate_inner_chamfer = kwargs.get('top_gate_inner_chamfer', 'none')       # 内焊盘倒角类型
        self.top_gate_outer_chamfer = kwargs.get('top_gate_outer_chamfer', 'straight')   # 外焊盘倒角类型
        
        # ===== 编号参数 =====
        self.label_size = kwargs.get('label_size', 20.0)           # 编号大小 (μm)
        self.label_spacing = kwargs.get('label_spacing', 0.5)      # 编号字符间距 (相对于字符大小的比例)
        self.label_font = kwargs.get('label_font', 'C:/Windows/Fonts/OCRAEXT.TTF')  # 编号字体路径
        self.label_offset_x = kwargs.get('label_offset_x', 0.0)    # 编号位置X偏移量 (μm)
        self.label_offset_y = kwargs.get('label_offset_y', 0.0)  # 编号位置Y偏移量 (μm)
        self.use_digital_display = kwargs.get('use_digital_display', False)  # 是否使用DigitalDisplay，默认False（使用TextUtils）
        
    def setup_layers(self):
        """设置图层"""
        for layer_name, layer_info in LAYER_DEFINITIONS.items():
            # 在KLayout中，使用layer()方法获取或创建图层
            # layer()方法需要(layer_number, datatype)参数
            self.layout.layer(layer_info['id'], 0)  # 使用datatype=0
    
    def set_device_parameters(self, ch_width=None, ch_len=None, gate_space=None, gate_width=None):
        """
        设置器件参数
        
        Args:
            ch_width: 沟道宽度 (μm)
            ch_len: 沟道长度 (μm)
            gate_space: 栅极边缘到边缘间距 (μm)
            gate_width: 栅极宽度 (μm)
        """
        if ch_width is not None:
            self.ch_width = ch_width
        if ch_len is not None:
            self.ch_len = ch_len
        if gate_space is not None:
            self.gate_space = gate_space
        if gate_width is not None:
            self.gate_width = gate_width
    
    def create_bottom_gate_electrodes(self, cell, x=0.0, y=0.0):
        """
        创建底栅电极
        
        Args:
            cell: 目标单元格
            x, y: 器件中心坐标
        """
        layer_id = LAYER_DEFINITIONS['bottom_gate']['id']
        
        # 底栅1电极 (左侧)
        # Inner pad - 左栅极右边缘距离中心 gate_space/2
        inner_pad1 = draw_pad(
            center=(x - self.gate_space/2 - self.gate_width/2, y),
            length=self.gate_width,
            width=self.ch_width * self.bottom_gate_inner_width_ratio,
            chamfer_size=0 if self.bottom_gate_inner_chamfer == 'none' else self.chamfer_size,
            chamfer_type=self.bottom_gate_inner_chamfer
        )
        cell.shapes(layer_id).insert(inner_pad1.polygon)
        
        # Outer pad
        outer_pad1 = draw_pad(
            center=(x - self.bottom_gate_outer_offset_x - self.gate_space/2 - self.gate_width/2, 
                   y + self.bottom_gate_outer_offset_y),
            length=self.outer_pad_size,
            width=self.outer_pad_size,
            chamfer_size=0 if self.bottom_gate_outer_chamfer == 'none' else self.chamfer_size,
            chamfer_type=self.bottom_gate_outer_chamfer
        )
        cell.shapes(layer_id).insert(outer_pad1.polygon)
        
        # 梯形扇出
        fanout1 = draw_trapezoidal_fanout(inner_pad1, outer_pad1)
        cell.shapes(layer_id).insert(fanout1)
        
        # 底栅2电极 (右侧)
        # Inner pad - 右栅极左边缘距离中心 gate_space/2
        inner_pad2 = draw_pad(
            center=(x + self.gate_space/2 + self.gate_width/2, y),
            length=self.gate_width,
            width=self.ch_width * self.bottom_gate_inner_width_ratio,
            chamfer_size=0 if self.bottom_gate_inner_chamfer == 'none' else self.chamfer_size,
            chamfer_type=self.bottom_gate_inner_chamfer
        )
        cell.shapes(layer_id).insert(inner_pad2.polygon)
        
        # Outer pad
        outer_pad2 = draw_pad(
            center=(x + self.bottom_gate_outer_offset_x + self.gate_space/2 + self.gate_width/2, 
                   y + self.bottom_gate_outer_offset_y),
            length=self.outer_pad_size,
            width=self.outer_pad_size,
            chamfer_size=0 if self.bottom_gate_outer_chamfer == 'none' else self.chamfer_size,
            chamfer_type=self.bottom_gate_outer_chamfer
        )
        cell.shapes(layer_id).insert(outer_pad2.polygon)
        
        # 梯形扇出
        fanout2 = draw_trapezoidal_fanout(inner_pad2, outer_pad2)
        cell.shapes(layer_id).insert(fanout2)
    
    def create_dielectric_layer(self, cell, x=0.0, y=0.0):
        """
        创建绝缘层：覆盖整个器件region的大矩形，只在source和drain的outer pad上开两个窗口（窗口略小于outer pad，带倒角）
        Args:
            cell: 目标单元格
            x, y: 器件中心坐标
        """
        try:
            import pya
            Region = pya.Region
        except Exception:
            import klayout.db as db
            Region = db.Region
        layer_id = LAYER_DEFINITIONS['top_dielectric']['id']

        # 1. 生成大矩形region，覆盖整个器件区域
        region_width = self.device_margin_x * 2
        region_height = self.device_margin_y * 2
        dielectric_rect = GeometryUtils.create_rectangle_polygon(x, y, region_width, region_height, center=True)
        dielectric_region = Region(dielectric_rect)

        # 2. 生成source/drain outer pad窗口（略小于pad，带倒角）
        shrink_ratio = 0.85  # 窗口比pad略小
        window_length = self.outer_pad_size * shrink_ratio
        window_width = self.outer_pad_size * shrink_ratio
        chamfer_size = self.chamfer_size * shrink_ratio if self.source_drain_outer_chamfer != 'none' else 0
        chamfer_type = self.source_drain_outer_chamfer

        # source outer pad中心
        source_outer_center = (
            x - self.ch_len/2 - self.source_drain_outer_offset_x,
            y + self.source_drain_outer_offset_y
        )
        source_window = draw_pad(
            center=source_outer_center,
            length=window_length,
            width=window_width,
            chamfer_size=chamfer_size,
            chamfer_type=chamfer_type
        ).polygon

        # drain outer pad中心
        drain_outer_center = (
            x + self.ch_len/2 + self.source_drain_outer_offset_x,
            y + self.source_drain_outer_offset_y
        )
        drain_window = draw_pad(
            center=drain_outer_center,
            length=window_length,
            width=window_width,
            chamfer_size=chamfer_size,
            chamfer_type=chamfer_type
        ).polygon

        # 3. 用Region布尔减法开窗口
        dielectric_region -= Region(source_window)
        dielectric_region -= Region(drain_window)

        # 4. 插入到cell
        cell.shapes(layer_id).insert(dielectric_region)
    
    def create_dielectric_layer_top_gate_outer(self, cell, x=0.0, y=0.0):
        """
        创建绝缘层：覆盖整个器件region的大矩形，只在source和drain的outer pad上开两个窗口（窗口略小于outer pad，带倒角）
        Args:
            cell: 目标单元格
            x, y: 器件中心坐标
        """
        try:
            import pya
            Region = pya.Region
        except Exception:
            import klayout.db as db
            Region = db.Region
        layer_id = LAYER_DEFINITIONS['top_dielectric']['id']

        # 1. 生成大矩形region，覆盖整个器件区域
        region_width = self.device_margin_x * 2
        region_height = self.device_margin_y * 2
        dielectric_rect = GeometryUtils.create_rectangle_polygon(x, y, region_width, region_height, center=True)
        dielectric_region = Region(dielectric_rect)

        # 2. 生成source/drain outer pad窗口（略小于pad，带倒角）
        shrink_ratio = 0.85  # 窗口比pad略小
        window_length = self.outer_pad_size * shrink_ratio
        window_width = self.outer_pad_size * shrink_ratio
        chamfer_size = self.chamfer_size * shrink_ratio if self.source_drain_outer_chamfer != 'none' else 0
        chamfer_type = self.source_drain_outer_chamfer

        # top gate outer pad中心
        source_outer_center = (
            x,
            y + self.top_gate_outer_offset_y
        )
        gate_window = draw_pad(
            center=source_outer_center,
            length=window_length,
            width=window_width,
            chamfer_size=chamfer_size,
            chamfer_type=chamfer_type
        ).polygon


        # 3. 用Region布尔减法开窗口
        dielectric_region -= Region(gate_window)

        # 4. 插入到cell
        cell.shapes(layer_id).insert(dielectric_region)

    def create_dielectric_layer_inner_window(self, cell, x=0.0, y=0.0):
        """
        创建绝缘层：覆盖整个器件region的大矩形，只在source和drain的inner pad上开两个窗口（窗口与源漏inner pad形状完全一致，仅略小，倒角类型一致）
        Args:
            cell: 目标单元格
            x, y: 器件中心坐标
        """
        try:
            import pya
            Region = pya.Region
        except Exception:
            import klayout.db as db
            Region = db.Region
        layer_id = LAYER_DEFINITIONS['top_dielectric']['id']

        # 1. 生成大矩形region，覆盖整个器件区域
        region_width = self.device_margin_x * 2
        region_height = self.device_margin_y * 2
        dielectric_rect = GeometryUtils.create_rectangle_polygon(x, y, region_width, region_height, center=True)
        dielectric_region = Region(dielectric_rect)

        # 2. 生成source/drain inner pad窗口（与源漏inner pad参数完全一致，仅略小）
        shrink_ratio = 0.95  # 窗口比inner pad略小
        inner_length = self.ch_len * shrink_ratio
        inner_width = self.ch_width * self.source_drain_inner_width_ratio * shrink_ratio
        chamfer_size = self.chamfer_size * shrink_ratio if self.source_drain_inner_chamfer != 'none' else 0
        chamfer_type = self.source_drain_inner_chamfer

        # source inner pad中心
        source_inner_center = (
            x - self.ch_len, y
        )
        source_window = draw_pad(
            center=source_inner_center,
            length=inner_length,
            width=inner_width,
            chamfer_size=chamfer_size,
            chamfer_type=chamfer_type
        ).polygon

        # drain inner pad中心
        drain_inner_center = (
            x + self.ch_len, y
        )
        drain_window = draw_pad(
            center=drain_inner_center,
            length=inner_length,
            width=inner_width,
            chamfer_size=chamfer_size,
            chamfer_type=chamfer_type
        ).polygon

        # 3. 用Region布尔减法开窗口
        dielectric_region -= Region(source_window)
        dielectric_region -= Region(drain_window)

        # 4. 插入到cell
        cell.shapes(layer_id).insert(dielectric_region)
    
    def create_channel_material(self, cell, x=0.0, y=0.0):
        """
        创建沟道材料层
        
        Args:
            cell: 目标单元格
            x, y: 器件中心坐标
        """
        layer_id = LAYER_DEFINITIONS['channel']['id']
        
        # 沟道材料矩形
        channel = GeometryUtils.create_rectangle(
            x, y,
            self.ch_len * 3,
            self.ch_width,
            center=True
        )
        cell.shapes(layer_id).insert(channel)
    
    def create_source_drain_electrodes(self, cell, x=0.0, y=0.0):
        """
        创建源漏电极（含inner/outer pad和扇出）
        """
        layer_id = LAYER_DEFINITIONS['source_drain']['id']

        # 源极 inner pad
        source_inner = draw_pad(
            center=(x - self.ch_len, y),
            length=self.ch_len,
            width=self.ch_width * self.source_drain_inner_width_ratio,
            chamfer_size=0 if self.source_drain_inner_chamfer == 'none' else self.chamfer_size,
            chamfer_type=self.source_drain_inner_chamfer
        )
        cell.shapes(layer_id).insert(source_inner.polygon)

        # 源极 outer pad
        source_outer = draw_pad(
            center=(x - self.ch_len/2 - self.source_drain_outer_offset_x, 
                   y + self.source_drain_outer_offset_y),
            length=self.outer_pad_size,
            width=self.outer_pad_size,
            chamfer_size=0 if self.source_drain_outer_chamfer == 'none' else self.chamfer_size,
            chamfer_type=self.source_drain_outer_chamfer
        )
        cell.shapes(layer_id).insert(source_outer.polygon)

        # 源极扇出
        source_fanout = draw_trapezoidal_fanout(source_inner, source_outer)
        cell.shapes(layer_id).insert(source_fanout)

        # 漏极 inner pad
        drain_inner = draw_pad(
            center=(x + self.ch_len, y),
            length=self.ch_len,
            width=self.ch_width * self.source_drain_inner_width_ratio,
            chamfer_size=0 if self.source_drain_inner_chamfer == 'none' else self.chamfer_size,
            chamfer_type=self.source_drain_inner_chamfer
        )
        cell.shapes(layer_id).insert(drain_inner.polygon)

        # 漏极 outer pad
        drain_outer = draw_pad(
            center=(x + self.ch_len/2 + self.source_drain_outer_offset_x, 
                   y + self.source_drain_outer_offset_y),
            length=self.outer_pad_size,
            width=self.outer_pad_size,
            chamfer_size=0 if self.source_drain_outer_chamfer == 'none' else self.chamfer_size,
            chamfer_type=self.source_drain_outer_chamfer
        )
        cell.shapes(layer_id).insert(drain_outer.polygon)

        # 漏极扇出
        drain_fanout = draw_trapezoidal_fanout(drain_inner, drain_outer)
        cell.shapes(layer_id).insert(drain_fanout)
    
    def create_top_gate_electrode(self, cell, x=0.0, y=0.0):
        """
        创建顶栅电极
        
        Args:
            cell: 目标单元格
            x, y: 器件中心坐标
        """
        layer_id = LAYER_DEFINITIONS['top_gate']['id']
        
        # Inner pad
        inner_pad = draw_pad(
            center=(x, y),
            length=self.ch_len * self.top_gate_inner_width_ratio,
            width=self.ch_width * self.bottom_gate_inner_width_ratio,  # 使用与底栅相同的宽度比例
            chamfer_size=0 if self.top_gate_inner_chamfer == 'none' else self.chamfer_size,
            chamfer_type=self.top_gate_inner_chamfer
        )
        cell.shapes(layer_id).insert(inner_pad.polygon)
        
        # Outer pad
        outer_pad = draw_pad(
            center=(x + self.top_gate_outer_offset_x, y + self.top_gate_outer_offset_y),
            length=self.outer_pad_size,
            width=self.outer_pad_size,
            chamfer_size=0 if self.top_gate_outer_chamfer == 'none' else self.chamfer_size,
            chamfer_type=self.top_gate_outer_chamfer
        )
        cell.shapes(layer_id).insert(outer_pad.polygon)
        
        # 梯形扇出
        fanout = draw_trapezoidal_fanout(inner_pad, outer_pad)
        cell.shapes(layer_id).insert(fanout)
    
    def create_alignment_marks(self, cell, x=0.0, y=0.0, device_id=None, row=None, col=None, label_type=None):
        """
        创建对准标记
        
        Args:
            cell: 目标单元格
            x, y: 器件中心坐标
            device_id: 器件编号，用于数字标记
            row: 行号（用于生成字母+数字格式的标记）
            col: 列号（用于生成字母+数字格式的标记）
            label_type: 标签类型，'textutils' 或 'digital'
        """
        layer_id = LAYER_DEFINITIONS['alignment_marks']['id']
        
        # 计算器件边界
        device_width = self.device_margin_x * 2
        device_height = self.device_margin_y * 2
        
        # 四个角落的标记位置
        mark_positions = [
            (x - device_width/2 + self.mark_margin, y + device_height/2 - self.mark_margin),  # 左上
            (x + device_width/2 - self.mark_margin, y + device_height/2 - self.mark_margin),  # 右上
            (x - device_width/2 + self.mark_margin, y - device_height/2 + self.mark_margin),  # 左下
            (x + device_width/2 - self.mark_margin, y - device_height/2 + self.mark_margin)   # 右下
        ]
        
        # 创建标记
        for i, (mark_x, mark_y) in enumerate(mark_positions):
            mark_type = self.mark_types[i] if i < len(self.mark_types) else 'cross'
            
            # 根据MarkUtils中的函数名创建对应的标记
            if mark_type == 'cross':
                marks = MarkUtils.cross(mark_x, mark_y, self.mark_size, self.mark_width)
            elif mark_type == 'square':
                marks = MarkUtils.square(mark_x, mark_y, self.mark_size)
            elif mark_type == 'circle':
                marks = MarkUtils.circle(mark_x, mark_y, self.mark_size)
            elif mark_type == 'diamond':
                marks = MarkUtils.diamond(mark_x, mark_y, self.mark_size)
            elif mark_type == 'triangle':
                marks = MarkUtils.triangle(mark_x, mark_y, self.mark_size)
            elif mark_type == 'l':
                marks = MarkUtils.l(mark_x, mark_y, self.mark_size, self.mark_width)
            elif mark_type == 't':
                marks = MarkUtils.t(mark_x, mark_y, self.mark_size, self.mark_width)
            elif mark_type == 'semi_cross':
                marks = MarkUtils.semi_cross(mark_x, mark_y, self.mark_size, self.mark_width)
            elif mark_type == 'cross_pos':
                marks = MarkUtils.cross_pos(mark_x, mark_y, self.mark_size)
            elif mark_type == 'cross_neg':
                marks = MarkUtils.cross_neg(mark_x, mark_y, self.mark_size)
            elif mark_type == 'l_shape':
                marks = MarkUtils.l_shape(mark_x, mark_y, self.mark_size)
            elif mark_type == 't_shape':
                marks = MarkUtils.t_shape(mark_x, mark_y, self.mark_size)
            elif mark_type == 'sq_missing':
                marks = MarkUtils.sq_missing(mark_x, mark_y, self.mark_size)
            elif mark_type == 'sq_missing_border':
                marks = MarkUtils.sq_missing_border(mark_x, mark_y, self.mark_size)
            elif mark_type == 'cross_tri':
                marks = MarkUtils.cross_tri(mark_x, mark_y, self.mark_size)
            elif mark_type == 'regular_polygon':
                marks = MarkUtils.regular_polygon(mark_x, mark_y, self.mark_size)
            elif mark_type == 'chamfered_octagon':
                marks = MarkUtils.chamfered_octagon(mark_x, mark_y, self.mark_size)
            else:
                # 默认使用十字标记
                marks = MarkUtils.cross(mark_x, mark_y, self.mark_size, self.mark_width)
            
            # 根据mark_rotations参数旋转标记
            rotation_angle = self.mark_rotations[i] if i < len(self.mark_rotations) else 0
            if rotation_angle > 0:
                marks = marks.rotate(rotation_angle)  # 直接使用0,1,2,3作为旋转参数
            
            # 插入标记
            shapes = marks.get_shapes()
            if isinstance(shapes, list):
                for shape in shapes:
                    cell.shapes(layer_id).insert(shape)
            else:
                cell.shapes(layer_id).insert(shapes)
        
        # 在右上角cross mark的右下角添加数字编号
        if device_id is not None:
            # 计算数字标记位置（右上角cross mark的右下角）
            mark_x, mark_y = mark_positions[0]  # 右上角位置
            # 向右下偏移，避开cross mark
            label_x = mark_x + self.mark_size * 0.8
            label_y = mark_y - self.mark_size * 0.8
            
            # 如果有行列信息，使用字母+数字格式；否则使用纯数字
            if row is not None and col is not None:
                self.create_device_label(cell, label_x, label_y, row, col, label_type)
            else:
                # 将 device_id 转换为字符串，作为纯数字标记
                self.create_device_label(cell, label_x, label_y, device_id - 1, 0, label_type)  # 假设为第0列
    
    def create_device_label(self, cell, x, y, row, col, label_type=None):
        """
        在指定位置创建字母+数字格式的器件标记
        
        Args:
            cell: 目标单元格
            x, y: 标记起始坐标
            row: 行号（数字）
            col: 列号（字母）
            label_type: 标签类型，'textutils' 或 'digital'，如果为None则使用初始化时的设置
        """
        # 如果没有指定label_type，使用初始化时的设置
        if label_type is None:
            label_type = 'digital' if self.use_digital_display else 'textutils'
        
        if label_type == 'textutils':
            self._create_device_label_textutils(cell, x, y, row, col)
        elif label_type == 'digital':
            self._create_device_label_digital(cell, x, y, row, col)
        else:
            # 默认使用textutils
            self._create_device_label_textutils(cell, x, y, row, col)
    
    def _create_device_label_textutils(self, cell, x, y, row, col):
        """
        使用TextUtils创建器件标签（推荐方式）
        """
        layer_id = LAYER_DEFINITIONS['labels']['id']
        
        # 生成字母+数字格式的标记
        col_letter = chr(ord('A') + col)  # 0->A, 1->B, 2->C, ...
        row_number = str(row + 1)  # 行号从1开始
        label = col_letter + row_number  # 如 A1, B2, C3
        
        # 应用偏移量
        label_x = x + self.label_offset_x
        label_y = y + self.label_offset_y
        
        # 设置字符大小和间距
        char_size = self.label_size
        char_spacing = char_size * self.label_spacing  # 字符间距
        
        # 创建每个字符
        for i, char in enumerate(label):
            char_x = label_x + i * char_spacing
            char_y = label_y
            
            # 使用 TextUtils 创建文本
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
        使用DigitalDisplay创建器件标签（传统方式）
        """
        layer_id = LAYER_DEFINITIONS['labels']['id']
        
        # 生成字母+数字格式的标记
        col_letter = chr(ord('A') + col)  # 0->A, 1->B, 2->C, ...
        row_number = str(row + 1)  # 行号从1开始
        label = col_letter + row_number  # 如 A1, B2, C3
        
        # 应用偏移量
        label_x = x + self.label_offset_x
        label_y = y + self.label_offset_y
        
        # 设置字符大小和间距
        char_size = self.label_size * 0.25  # DigitalDisplay通常需要较小的尺寸
        stroke_width = self.mark_width * 0.8
        char_spacing = char_size * 1.7  # 字符间距
        
        # 创建每个字符
        for i, char in enumerate(label):
            char_x = label_x + i * char_spacing
            char_y = label_y
            
            # 使用 DigitalDisplay 创建数字显示
            polygons = DigitalDisplay.create_digit(
                char, char_x, char_y, 
                size=char_size, 
                stroke_width=stroke_width
            )
            
            for polygon in polygons:
                cell.shapes(layer_id).insert(polygon)
    
    def create_parameter_labels(self, cell, x, y, device_params):
        """
        在器件区域内创建参数标注，使用pya.Text
        
        Args:
            cell: 目标单元格
            x, y: 器件中心坐标
            device_params: 器件参数字典
        """
        layer_id = LAYER_DEFINITIONS['labels']['id']
        
        # 计算标注起始位置（器件中心上方）
        start_x = x - self.device_margin_x * 0.9  # 向左偏移
        start_y = y - self.device_margin_y * 0.7  # 向上偏移
        
        # 创建参数标注文本
        param_texts = []
        
        # 添加沟道宽度标注
        if 'ch_width' in device_params:
            ch_width = device_params['ch_width']
            param_texts.append(f"W:{ch_width:.1f}")
        
        # 添加沟道长度标注
        if 'ch_len' in device_params:
            ch_len = device_params['ch_len']
            param_texts.append(f"L:{ch_len:.1f}")
        
        # 添加栅极间距标注
        if 'gate_space' in device_params:
            gate_space = device_params['gate_space']
            param_texts.append(f"GS:{gate_space:.1f}")
        
        # 添加栅极宽度标注
        if 'gate_width' in device_params:
            gate_width = device_params['gate_width']
            param_texts.append(f"GW:{gate_width:.1f}")
        
        # 创建每行参数标注
        line_spacing = 10.0  # 行间距 (μm)
        for i, text in enumerate(param_texts):
            text_y = start_y - i * line_spacing
            
            # 使用db.Text创建文本
            text_obj = db.Text(
                text,
                int(start_x * 1000),  # 转换为数据库单位
                int(text_y * 1000)    # 转换为数据库单位
            )
            
            cell.shapes(layer_id).insert(text_obj)
    
    def create_single_device(self, cell_name="FET_Device", x=0, y=0, device_id=None, row=None, col=None, device_params=None, label_type=None):
        """
        创建单个FET器件
        
        Args:
            cell_name: 单元格名称
            x, y: 器件中心坐标
            device_id: 器件编号
            row: 行号（用于生成字母+数字格式的标记）
            col: 列号（用于生成字母+数字格式的标记）
            device_params: 器件参数字典，用于标注
            label_type: 标签类型，'textutils' 或 'digital'
            
        Returns:
            创建的单元格
        """
        cell = self.layout.create_cell(cell_name)
        
        # 确保坐标是浮点数
        x = float(x)
        y = float(y)
        
        # 按层次顺序创建器件结构
        self.create_bottom_gate_electrodes(cell, x, y)
        # self.create_dielectric_layer(cell, x, y)
        self.create_dielectric_layer_top_gate_outer(cell, x, y)
        # self.create_dielectric_layer_inner_window(cell, x, y)
        self.create_channel_material(cell, x, y)
        self.create_source_drain_electrodes(cell, x, y)
        self.create_top_gate_electrode(cell, x, y)
        self.create_alignment_marks(cell, x, y, device_id, row, col, label_type)
        
        # 如果有器件参数，添加参数标注
        if device_params:
            self.create_parameter_labels(cell, x, y, device_params)
        
        return cell
    
    def create_device_array(self, rows=10, cols=10, device_spacing_x=None, device_spacing_y=None, label_type=None):
        """
        创建器件阵列
        
        Args:
            rows: 行数
            cols: 列数
            device_spacing_x: 器件横向间距，如果为None则自动计算
            device_spacing_y: 器件纵向间距，如果为None则自动计算
            label_type: 标签类型，'textutils' 或 'digital'
            
        Returns:
            阵列单元格
        """
        # 计算器件间距
        if device_spacing_x is None:
            device_spacing_x = self.device_margin_x * 2 + 50  # 额外50μm间距
        if device_spacing_y is None:
            device_spacing_y = self.device_margin_y * 2 + 50  # 额外50μm间距
        
        # 创建阵列单元格
        array_cell = self.layout.create_cell("FET_Array")
        
        # 创建器件阵列
        device_id = 1
        for row in range(rows):
            for col in range(cols):
                # 计算器件位置
                device_x = int(col * device_spacing_x)
                device_y = int(row * device_spacing_y)
                
                # 创建单个器件
                device_cell = self.create_single_device(
                    f"FET_{device_id:03d}", 
                    device_x, device_y, 
                    device_id, row, col,
                    label_type=label_type
                )
                
                # 将器件单元格插入到阵列中
                array_cell.insert(db.CellInstArray(
                    device_cell.cell_index(),
                    db.Trans(0, 0)
                ))
                
                device_id += 1
        
        return array_cell
    
    def scan_parameters_and_create_array(self, param_ranges, rows=10, cols=10, offset_x=0, offset_y=0, label_type=None):
        """
        扫描参数并创建参数变化的器件阵列
        
        Args:
            param_ranges: 参数字典，格式为 {'param_name': [min, max, steps]}
            rows: 行数
            cols: 列数
            offset_x: 阵列起始X坐标偏移
            offset_y: 阵列起始Y坐标偏移
            label_type: 标签类型，'textutils' 或 'digital'
            
        Returns:
            参数扫描阵列单元格
        """
        # 创建参数扫描阵列单元格
        scan_cell = self.layout.create_cell("FET_Parameter_Scan")
        
        # 计算总器件数
        total_devices = rows * cols
        device_id = 1
        
        # 计算参数步长
        param_steps = {}
        for param_name, param_range in param_ranges.items():
            if len(param_range) == 3:
                min_val, max_val, steps = param_range
                param_steps[param_name] = (max_val - min_val) / (steps - 1) if steps > 1 else 0
            else:
                param_steps[param_name] = 0
        
        # 计算器件间距
        device_spacing_x = self.device_margin_x * 2 + 50
        device_spacing_y = self.device_margin_y * 2 + 50
        
        # 创建器件阵列
        for row in range(rows):
            for col in range(cols):
                # 计算当前器件的参数值
                current_params = {}
                
                # 行扫描：沟道宽度
                if 'ch_width' in param_ranges:
                    ch_width_range = param_ranges['ch_width']
                    if len(ch_width_range) == 3:
                        min_val, max_val, steps = ch_width_range
                        ch_width = min_val + row * (max_val - min_val) / (steps - 1)
                        current_params['ch_width'] = ch_width
                    else:
                        current_params['ch_width'] = ch_width_range[0]
                
                # 列扫描：沟道长度
                if 'ch_len' in param_ranges:
                    ch_len_range = param_ranges['ch_len']
                    if len(ch_len_range) == 3:
                        min_val, max_val, steps = ch_len_range
                        ch_len = min_val + col * (max_val - min_val) / (steps - 1)
                        current_params['ch_len'] = ch_len
                    else:
                        current_params['ch_len'] = ch_len_range[0]
                
                # gate_space 使用全局设置的值
                current_params['gate_space'] = self.gate_space
                
                # gate_width 为 (ch_len - 2μm) / 2
                if 'ch_len' in current_params:
                    current_params['gate_width'] = (current_params['ch_len'] - 5.0) / 2
                
                # 设置当前器件的参数
                self.set_device_parameters(**current_params)
                
                # 计算器件位置（加上偏移）
                device_x = int(offset_x + col * device_spacing_x)
                device_y = int(offset_y + row * device_spacing_y)
                
                # 创建单个器件
                device_cell = self.create_single_device(
                    f"FET_Scan_{device_id:03d}", 
                    device_x, device_y, 
                    device_id, row, col,
                    current_params,
                    label_type=label_type
                )
                
                # 将器件单元格插入到扫描阵列中
                scan_cell.insert(db.CellInstArray(
                    device_cell.cell_index(),
                    db.Trans(0, 0)
                ))
                
                device_id += 1
        
        return scan_cell


def main():
    """主函数 - 用于测试FET器件生成"""
    
    # 创建FET器件实例
    fet = FET()
    
    # 全局设置gate_space为2μm（用于参数扫描中的所有器件）
    fet.gate_space = 2.0
    
    # 设置器件参数
    fet.set_device_parameters(
        ch_width=5.0,    # 沟道宽度 5μm
        ch_len=14.0,     # 沟道长度 14μm
        gate_width=5.0   # 栅极宽度 5μm
    )
    
    # 创建单个器件进行测试
    print("创建单个FET器件...")
    single_device = fet.create_single_device("Test_FET", 0, 0, 1, 0, 0)  # 位置A1
    print(f"单个器件已创建: {single_device.name}")
    
    # 创建10x10器件阵列
    #print("创建10x10器件阵列...")
    #device_array = fet.create_device_array(rows=10, cols=10)
    #print(f"器件阵列已创建: {device_array.name}")
    
    # 创建参数扫描阵列（行列扫描）
    print("创建参数扫描阵列...")
    param_ranges = {
        'ch_width': [10.0, 45.0, 14],    # 行扫描：沟道宽度从5μm到30μm，12个值
        'ch_len': [10.0, 30.0, 14],       # 列扫描：沟道长度从5μm到20μm，12个值
        # gate_space 固定为 1μm（通过 fet.gate_space 全局设置）
        # gate_width 为 (ch_len - 2μm) / 2
    }
    
    # 从原点开始创建参数扫描阵列
    scan_array = fet.scan_parameters_and_create_array(param_ranges, rows=14, cols=14, offset_x=0, offset_y=0)
    print(f"参数扫描阵列已创建: {scan_array.name}")

    # 保存布局文件
    output_file = "TEST_mySiSBFET_COMP.gds"
    fet.layout.write(output_file)
    print(f"布局文件已保存: {output_file}")
    
    print("mySiSBFET器件生成测试完成！")
    


if __name__ == "__main__":
    main()
