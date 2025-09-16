# -*- coding: utf-8 -*-
"""
Serpentine蜿蜒线器件组件模块 - 基于KLayout的蜿蜒线版图生成器
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import klayout.db as db
import pya
from utils.geometry import GeometryUtils
from utils.mark_utils import MarkUtils
from utils.fanout_utils import draw_pad, draw_trapezoidal_fanout
from utils.text_utils import TextUtils
from utils.digital_utils import DigitalDisplay
from config import LAYER_DEFINITIONS, DEFAULT_UNIT_SCALE

class Serpentine:
    """蜿蜒线器件类"""
    
    def __init__(self, layout=None, **kwargs):
        """
        初始化Serpentine器件类
        
        Args:
            layout: KLayout布局对象，如果为None则创建新的
            **kwargs: 其他参数，包括器件、标记、扇出、编号等相关参数
        """
        self.layout = layout or db.Layout()
        self.setup_layers()
        
        # ===== 蜿蜒线核心参数 =====
        self.region_width = kwargs.get('region_width', 200.0)        # 矩形区域宽度 (μm)
        self.region_height = kwargs.get('region_height', 100.0)      # 矩形区域高度 (μm)
        self.line_width = kwargs.get('line_width', 5.0)              # 线条宽度 (μm)
        self.line_spacing = kwargs.get('line_spacing', 10.0)         # 线条间距 (μm)
        self.direction = kwargs.get('direction', 'horizontal')       # 起始方向 'horizontal' 或 'vertical'
        self.margin = kwargs.get('margin', 0.0)                      # 边距 (μm)
        self.curve_type = kwargs.get('curve_type', 'serpentine')     # 曲线类型 'serpentine', 'peano', 'hilbert'
        
        # 保持向后兼容性
        self.channel_length = self.region_width
        self.channel_width = self.line_width
        self.channel_spacing = self.line_spacing
        self.turns = 5  # 不再使用turns参数
        
        # ===== 器件边界参数 =====
        self.device_margin_x = kwargs.get('device_margin_x', 300.0)  # 器件核心区域横向边界距离 (μm)
        self.device_margin_y = kwargs.get('device_margin_y', 300.0)  # 器件核心区域纵向边界距离 (μm)
        self.mark_margin = kwargs.get('mark_margin', 20.0)           # 标记中心点距离边界收缩距离 (μm)
        
        # ===== 标记参数 =====
        self.mark_size = kwargs.get('mark_size', 20.0)              # 标记尺寸 (μm)
        self.mark_width = kwargs.get('mark_width', 2.0)             # 标记线宽 (μm)
        # 四个角落的标记类型
        self.mark_types = kwargs.get('mark_types', ['sq_missing', 'l', 'l', 'cross_tri'])  # [左上, 右上, 左下, 右下]
        # 四个角落标记的旋转角度: 0=不旋转, 1=90度, 2=180度, 3=270度
        self.mark_rotations = kwargs.get('mark_rotations', [0, 0, 2, 1])  # [左上, 右上, 左下, 右下]
        
        # ===== 扇出参数 =====
        self.outer_pad_size = kwargs.get('outer_pad_size', 150.0)   # 外部焊盘尺寸 (μm)
        self.chamfer_size = kwargs.get('chamfer_size', 15.0)        # 倒角尺寸 (μm)
        self.chamfer_type = kwargs.get('chamfer_type', 'straight')  # 倒角类型: 'straight', 'rounded', 'none'
        
        # ===== 电极参数 =====
        # 源极电极参数
        self.source_inner_width_ratio = kwargs.get('source_inner_width_ratio', 1.5)  # 内焊盘宽度相对于沟道宽度的比例
        self.source_outer_offset_x = kwargs.get('source_outer_offset_x', -200.0)     # 外焊盘X偏移 (μm)
        self.source_outer_offset_y = kwargs.get('source_outer_offset_y', 0.0)        # 外焊盘Y偏移 (μm)
        self.source_inner_chamfer = kwargs.get('source_inner_chamfer', 'none')       # 内焊盘倒角类型
        self.source_outer_chamfer = kwargs.get('source_outer_chamfer', 'straight')   # 外焊盘倒角类型
        
        # 漏极电极参数
        self.drain_inner_width_ratio = kwargs.get('drain_inner_width_ratio', 1.5)    # 内焊盘宽度相对于沟道宽度的比例
        self.drain_outer_offset_x = kwargs.get('drain_outer_offset_x', 200.0)        # 外焊盘X偏移 (μm)
        self.drain_outer_offset_y = kwargs.get('drain_outer_offset_y', 0.0)          # 外焊盘Y偏移 (μm)
        self.drain_inner_chamfer = kwargs.get('drain_inner_chamfer', 'none')         # 内焊盘倒角类型
        self.drain_outer_chamfer = kwargs.get('drain_outer_chamfer', 'straight')     # 外焊盘倒角类型
        
        # ===== 编号参数 =====
        self.label_size = kwargs.get('label_size', 20.0)           # 编号大小 (μm)
        self.label_spacing = kwargs.get('label_spacing', 0.5)      # 编号字符间距 (相对于字符大小的比例)
        self.label_font = kwargs.get('label_font', 'C:/Windows/Fonts/OCRAEXT.TTF')  # 编号字体路径
        self.label_offset_x = kwargs.get('label_offset_x', 0.0)    # 编号位置X偏移量 (μm)
        self.label_offset_y = kwargs.get('label_offset_y', -30.0)  # 编号位置Y偏移量 (μm)
        self.use_digital_display = kwargs.get('use_digital_display', False)  # 是否使用DigitalDisplay，默认False（使用TextUtils）
        
        # ===== 芯片参数 =====
        self.chip_size = kwargs.get('chip_size', 10000.0)          # 芯片尺寸 (μm) - 1cm见方
        self.dummy_edge = kwargs.get('dummy_edge', 1000.0)         # 芯片边缘dummy区域 (μm) - 1mm
        self.pad_size = kwargs.get('pad_size', 200.0)              # 边缘pad尺寸 (μm)
        self.pad_spacing = kwargs.get('pad_spacing', 300.0)        # pad间距 (μm)
        
    def setup_layers(self):
        """设置图层"""
        for layer_name, layer_info in LAYER_DEFINITIONS.items():
            # 在KLayout中，使用layer()方法获取或创建图层
            # layer()方法需要(layer_number, datatype)参数
            self.layout.layer(layer_info['id'], 0)  # 使用datatype=0
    
    def set_serpentine_parameters(self, region_width=None, region_height=None, line_width=None, 
                                 line_spacing=None, direction=None, margin=None, curve_type=None):
        """
        设置蜿蜒线参数
        
        Args:
            region_width: 矩形区域宽度 (μm)
            region_height: 矩形区域高度 (μm)
            line_width: 线条宽度 (μm)
            line_spacing: 线条间距 (μm)
            direction: 起始方向 'horizontal' 或 'vertical'
            margin: 边距 (μm)
            curve_type: 曲线类型 'serpentine', 'peano', 'hilbert'
        """
        if region_width is not None:
            self.region_width = region_width
            self.channel_length = region_width  # 保持兼容性
        if region_height is not None:
            self.region_height = region_height
        if line_width is not None:
            self.line_width = line_width
            self.channel_width = line_width  # 保持兼容性
        if line_spacing is not None:
            self.line_spacing = line_spacing
            self.channel_spacing = line_spacing  # 保持兼容性
        if direction is not None:
            self.direction = direction
        if margin is not None:
            self.margin = margin
        if curve_type is not None:
            self.curve_type = curve_type
    
    def create_serpentine_channel(self, cell, x=0.0, y=0.0):
        """
        创建蜿蜒沟道
        
        Args:
            cell: 目标单元格
            x, y: 器件中心坐标
        """
        layer_id = LAYER_DEFINITIONS['channel_etch']['id']
        
        # 创建蜿蜒沟道
        if self.curve_type == 'serpentine':
            serpentine = GeometryUtils._create_serpentine_curve(
                x, y, self.region_width, self.region_height, 
                self.line_width, self.line_spacing, self.direction, 
                'rect', self.margin  # 只支持直角转折
            )
        else:
            # 其他曲线类型使用原有方法
            serpentine = GeometryUtils.create_serpentine_channel(
                x, y, self.channel_length, self.channel_width, 
                self.channel_spacing, self.turns, self.direction, self.curve_type
            )
        cell.shapes(layer_id).insert(serpentine)
    
    def create_source_electrode(self, cell, x=0.0, y=0.0):
        """
        创建源极电极
        
        Args:
            cell: 目标单元格
            x, y: 器件中心坐标
        """
        layer_id = LAYER_DEFINITIONS['source_drain']['id']
        
        # 计算源极位置（蜿蜒线起始端）
        if self.direction == 'horizontal':
            source_x = x - self.channel_length / 2
            source_y = y
        else:
            source_x = x
            source_y = y - self.channel_length / 2
        
        # 源极 inner pad
        source_inner = draw_pad(
            center=(source_x, source_y),
            length=self.channel_width * self.source_inner_width_ratio,
            width=self.channel_width * self.source_inner_width_ratio,
            chamfer_size=0 if self.source_inner_chamfer == 'none' else self.chamfer_size,
            chamfer_type=self.source_inner_chamfer
        )
        cell.shapes(layer_id).insert(source_inner.polygon)
        
        # 源极 outer pad
        source_outer = draw_pad(
            center=(source_x + self.source_outer_offset_x, source_y + self.source_outer_offset_y),
            length=self.outer_pad_size,
            width=self.outer_pad_size,
            chamfer_size=0 if self.source_outer_chamfer == 'none' else self.chamfer_size,
            chamfer_type=self.source_outer_chamfer
        )
        cell.shapes(layer_id).insert(source_outer.polygon)
        
        # 源极扇出
        source_fanout = draw_trapezoidal_fanout(source_inner, source_outer)
        cell.shapes(layer_id).insert(source_fanout)
    
    def create_drain_electrode(self, cell, x=0.0, y=0.0):
        """
        创建漏极电极
        
        Args:
            cell: 目标单元格
            x, y: 器件中心坐标
        """
        layer_id = LAYER_DEFINITIONS['source_drain']['id']
        
        # 计算漏极位置（蜿蜒线结束端）
        if self.direction == 'horizontal':
            drain_x = x + self.channel_length / 2
            drain_y = y
        else:
            drain_x = x
            drain_y = y + self.channel_length / 2
        
        # 漏极 inner pad
        drain_inner = draw_pad(
            center=(drain_x, drain_y),
            length=self.channel_width * self.drain_inner_width_ratio,
            width=self.channel_width * self.drain_inner_width_ratio,
            chamfer_size=0 if self.drain_inner_chamfer == 'none' else self.chamfer_size,
            chamfer_type=self.drain_inner_chamfer
        )
        cell.shapes(layer_id).insert(drain_inner.polygon)
        
        # 漏极 outer pad
        drain_outer = draw_pad(
            center=(drain_x + self.drain_outer_offset_x, drain_y + self.drain_outer_offset_y),
            length=self.outer_pad_size,
            width=self.outer_pad_size,
            chamfer_size=0 if self.drain_outer_chamfer == 'none' else self.chamfer_size,
            chamfer_type=self.drain_outer_chamfer
        )
        cell.shapes(layer_id).insert(drain_outer.polygon)
        
        # 漏极扇出
        drain_fanout = draw_trapezoidal_fanout(drain_inner, drain_outer)
        cell.shapes(layer_id).insert(drain_fanout)
    
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
            mark_x, mark_y = mark_positions[1]  # 右上角位置
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
    
    def create_single_device(self, cell_name="Serpentine_Device", x=0, y=0, device_id=None, row=None, col=None, device_params=None, label_type=None):
        """
        创建单个Serpentine器件
        
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
        self.create_serpentine_channel(cell, x, y)
        self.create_source_electrode(cell, x, y)
        self.create_drain_electrode(cell, x, y)
        self.create_alignment_marks(cell, x, y, device_id, row, col, label_type)
        
        return cell
    
    def create_device_array(self, rows=6, cols=6, device_spacing_x=None, device_spacing_y=None, label_type=None):
        """
        创建蜿蜒线器件阵列
        
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
            device_spacing_x = self.device_margin_x * 2 + 100  # 额外100μm间距
        if device_spacing_y is None:
            device_spacing_y = self.device_margin_y * 2 + 100  # 额外100μm间距
        
        # 创建阵列单元格
        array_cell = self.layout.create_cell("Serpentine_Array")
        
        # 创建器件阵列
        device_id = 1
        for row in range(rows):
            for col in range(cols):
                # 计算器件位置
                device_x = int(col * device_spacing_x)
                device_y = int(row * device_spacing_y)
                
                # 创建单个器件
                device_cell = self.create_single_device(
                    f"Serpentine_{device_id:03d}", 
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
    
    def create_chip_with_fanout(self, array_cell, chip_center_x=0, chip_center_y=0):
        """
        创建带扇出的芯片布局
        
        Args:
            array_cell: 器件阵列单元格
            chip_center_x, chip_center_y: 芯片中心坐标
            
        Returns:
            芯片单元格
        """
        # 创建芯片单元格
        chip_cell = self.layout.create_cell("Serpentine_Chip")
        
        # 计算芯片边界
        chip_half_size = self.chip_size / 2
        chip_left = chip_center_x - chip_half_size
        chip_right = chip_center_x + chip_half_size
        chip_bottom = chip_center_y - chip_half_size
        chip_top = chip_center_y + chip_half_size
        
        # 计算有效区域（去除dummy edge）
        effective_left = chip_left + self.dummy_edge
        effective_right = chip_right - self.dummy_edge
        effective_bottom = chip_bottom + self.dummy_edge
        effective_top = chip_top - self.dummy_edge
        
        # 将阵列插入到芯片中心
        array_inst = chip_cell.insert(db.CellInstArray(
            array_cell.cell_index(),
            db.Trans(0, chip_center_x, chip_center_y)
        ))
        
        # 创建边缘pad
        self._create_edge_pads(chip_cell, effective_left, effective_right, effective_bottom, effective_top)
        
        return chip_cell
    
    def _create_edge_pads(self, cell, left, right, bottom, top):
        """
        在芯片边缘创建pad
        
        Args:
            cell: 目标单元格
            left, right, bottom, top: 有效区域边界
        """
        layer_id = LAYER_DEFINITIONS['source_drain']['id']
        
        # 计算pad位置
        pad_half_size = self.pad_size / 2
        
        # 左侧pad
        left_pad_x = left - self.dummy_edge / 2
        left_pad_count = int((top - bottom) / self.pad_spacing)
        for i in range(left_pad_count):
            pad_y = bottom + i * self.pad_spacing + self.pad_spacing / 2
            if pad_y + pad_half_size <= top:
                pad = GeometryUtils.create_rectangle(
                    left_pad_x, pad_y, self.pad_size, self.pad_size, center=True
                )
                cell.shapes(layer_id).insert(pad)
        
        # 右侧pad
        right_pad_x = right + self.dummy_edge / 2
        for i in range(left_pad_count):
            pad_y = bottom + i * self.pad_spacing + self.pad_spacing / 2
            if pad_y + pad_half_size <= top:
                pad = GeometryUtils.create_rectangle(
                    right_pad_x, pad_y, self.pad_size, self.pad_size, center=True
                )
                cell.shapes(layer_id).insert(pad)
        
        # 底部pad
        bottom_pad_y = bottom - self.dummy_edge / 2
        bottom_pad_count = int((right - left) / self.pad_spacing)
        for i in range(bottom_pad_count):
            pad_x = left + i * self.pad_spacing + self.pad_spacing / 2
            if pad_x + pad_half_size <= right:
                pad = GeometryUtils.create_rectangle(
                    pad_x, bottom_pad_y, self.pad_size, self.pad_size, center=True
                )
                cell.shapes(layer_id).insert(pad)
        
        # 顶部pad
        top_pad_y = top + self.dummy_edge / 2
        for i in range(bottom_pad_count):
            pad_x = left + i * self.pad_spacing + self.pad_spacing / 2
            if pad_x + pad_half_size <= right:
                pad = GeometryUtils.create_rectangle(
                    pad_x, top_pad_y, self.pad_size, self.pad_size, center=True
                )
                cell.shapes(layer_id).insert(pad)


def main():
    """主函数 - 生成Hilbert和Serpentine测试结构"""
    
    print("=== 生成测试结构 ===")
    
    # 创建Serpentine器件实例
    serpentine = Serpentine()
    
    # 创建顶层测试单元格
    top_cell = serpentine.layout.create_cell("Test_Meander")
    
    # ===== 生成Hilbert曲线 =====
    print("生成Hilbert曲线...")
    try:
        hilbert_cell = serpentine.layout.create_cell("Hilbert_Test")
        
        # Hilbert参数: order=3, step=10μm, line_w=2μm, margin=2μm
        hilbert_region = GeometryUtils.make_hilbert(
            order=5,
            step=10.0,
            line_w=4.0,
            margin=2.0
        )
        
        layer_id = LAYER_DEFINITIONS['channel_etch']['id']
        hilbert_cell.shapes(layer_id).insert(hilbert_region)
        top_cell.insert(pya.CellInstArray(hilbert_cell.cell_index(), pya.Trans()))
        
        print("✓ Hilbert曲线生成成功")
        
    except Exception as e:
        print(f"✗ Hilbert曲线生成失败: {e}")
        return
    
    # ===== 生成Serpentine曲线 =====
    print("生成Serpentine曲线...")
    try:
        serpentine_cell = serpentine.layout.create_cell("Serpentine_Test")
        
        # Serpentine参数: 300x300μm, 4μm线宽, 5μm间距, 水平方向
        serpentine.set_serpentine_parameters(
            region_width=300.0,
            region_height=300.0,
            line_width=4.0,
            line_spacing=5.0,
            direction='horizontal',
            margin=0.0,
            curve_type='serpentine'
        )
        
        serpentine.create_serpentine_channel(serpentine_cell, 0.0, 0.0)
        top_cell.insert(pya.CellInstArray(serpentine_cell.cell_index(), pya.Trans(pya.Point(500, 150))))
        
        print("✓ Serpentine曲线生成成功")
        
    except Exception as e:
        print(f"✗ Serpentine曲线生成失败: {e}")
        return
    
    
    # ===== 保存结果 =====
    output_file = "TEST_MEANDER.gds"
    print(f"保存到: {output_file}")
    try:
        serpentine.layout.write(output_file)
        print("✓ 保存成功")
    except Exception as e:
        print(f"✗ 保存失败: {e}")
        return
    
    print("=== 完成 ===")
    print("包含结构:")
    print("  - Test_Meander")
    print("    - Hilbert_Test")
    print("    - Serpentine_Test")


if __name__ == "__main__":
    main()