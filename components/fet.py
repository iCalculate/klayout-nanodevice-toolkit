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
from utils.digital_utils import DigitalDisplay
from config import LAYER_DEFINITIONS, DEFAULT_UNIT_SCALE

class FET:
    """场效应晶体管器件类"""
    
    def __init__(self, layout=None):
        """
        初始化FET器件类
        
        Args:
            layout: KLayout布局对象，如果为None则创建新的
        """
        self.layout = layout or db.Layout()
        self.setup_layers()
        
        # 默认器件参数
        self.ch_len = 10.0      # 沟道宽度 (μm)
        self.ch_width = 5.0         # 沟道长度 (μm)
        self.gate_space = 20.0    # 栅极边缘到边缘间距 (μm)
        self.gate_width = 15.0    # 栅极宽度 (μm)
        
        # 器件边界参数
        self.device_margin_x = 170.0  # 器件核心区域横向边界距离 (μm)
        self.device_margin_y = 170.0  # 器件核心区域纵向边界距离 (μm)
        self.mark_margin = 0.0       # 标记中心点距离边界收缩距离 (μm)
        
        # 标记参数
        self.mark_size = 20.0         # 标记尺寸 (μm)
        self.mark_width = 2.0         # 标记线宽 (μm)
        
        # 扇出参数
        self.outer_pad_size = 100.0   # 外部焊盘尺寸 (μm)
        self.chamfer_size = 10.0      # 倒角尺寸 (μm)
        
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
            width=self.ch_width * 1.5,
            chamfer_size=0,      # 不倒角
            chamfer_type='none'  # 不倒角
        )
        cell.shapes(layer_id).insert(inner_pad1.polygon)
        
        # Outer pad
        outer_pad1 = draw_pad(
            center=(x - 50 - self.gate_space/2 - self.gate_width/2, y - 100),
            length=self.outer_pad_size,
            width=self.outer_pad_size,
            chamfer_size=self.chamfer_size,
            chamfer_type='straight'
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
            width=self.ch_width * 1.5,
            chamfer_size=0,      # 不倒角
            chamfer_type='none'  # 不倒角
        )
        cell.shapes(layer_id).insert(inner_pad2.polygon)
        
        # Outer pad
        outer_pad2 = draw_pad(
            center=(x + 50 + self.gate_space/2 + self.gate_width/2, y - 100),
            length=self.outer_pad_size,
            width=self.outer_pad_size,
            chamfer_size=self.chamfer_size,
            chamfer_type='straight'
        )
        cell.shapes(layer_id).insert(outer_pad2.polygon)
        
        # 梯形扇出
        fanout2 = draw_trapezoidal_fanout(inner_pad2, outer_pad2)
        cell.shapes(layer_id).insert(fanout2)
    
    def create_dielectric_layer(self, cell, x=0.0, y=0.0):
        """
        创建绝缘层
        
        Args:
            cell: 目标单元格
            x, y: 器件中心坐标
        """
        layer_id = LAYER_DEFINITIONS['dielectric']['id']
        
        # 绝缘层矩形
        dielectric = GeometryUtils.create_rectangle(
            x, y,
            self.ch_len * 2,
            self.ch_width * 2,
            center=True
        )
        cell.shapes(layer_id).insert(dielectric)
    
    def create_channel_material(self, cell, x=0.0, y=0.0):
        """
        创建沟道材料层
        
        Args:
            cell: 目标单元格
            x, y: 器件中心坐标
        """
        layer_id = LAYER_DEFINITIONS['channel_etch']['id']
        
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
            width=self.ch_width * 1.2,
            chamfer_size=0,
            chamfer_type='none'
        )
        cell.shapes(layer_id).insert(source_inner.polygon)

        # 源极 outer pad
        source_outer = draw_pad(
            center=(x - self.ch_len /2 - 110, y+20),  # 100um向左
            length=100,
            width=100,
            chamfer_size=self.chamfer_size,
            chamfer_type='straight'
        )
        cell.shapes(layer_id).insert(source_outer.polygon)

        # 源极扇出
        source_fanout = draw_trapezoidal_fanout(source_inner, source_outer)
        cell.shapes(layer_id).insert(source_fanout)

        # 漏极 inner pad
        drain_inner = draw_pad(
            center=(x + self.ch_len, y),
            length=self.ch_len,
            width=self.ch_width * 1.2,
            chamfer_size=0,
            chamfer_type='none'
        )
        cell.shapes(layer_id).insert(drain_inner.polygon)

        # 漏极 outer pad
        drain_outer = draw_pad(
            center=(x + self.ch_len/2 + 110, y+20),  # 100um向右
            length=100,
            width=100,
            chamfer_size=self.chamfer_size,
            chamfer_type='straight'
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
            length=self.ch_len * 1.2,
            width=self.ch_width * 1.2,
            chamfer_size=0,      # 不倒角
            chamfer_type='none'  # 不倒角
        )
        cell.shapes(layer_id).insert(inner_pad.polygon)
        
        # Outer pad
        outer_pad = draw_pad(
            center=(x, y + 100),
            length=self.outer_pad_size,
            width=self.outer_pad_size,
            chamfer_size=self.chamfer_size,
            chamfer_type='straight'
        )
        cell.shapes(layer_id).insert(outer_pad.polygon)
        
        # 梯形扇出
        fanout = draw_trapezoidal_fanout(inner_pad, outer_pad)
        cell.shapes(layer_id).insert(fanout)
    
    def create_alignment_marks(self, cell, x=0.0, y=0.0, device_id=None, row=None, col=None):
        """
        创建对准标记
        
        Args:
            cell: 目标单元格
            x, y: 器件中心坐标
            device_id: 器件编号，用于数字标记
            row: 行号（用于生成字母+数字格式的标记）
            col: 列号（用于生成字母+数字格式的标记）
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
            if i == 0 or i == 3:  # 左上角和右下角使用十字标记
                marks = MarkUtils.cross(mark_x, mark_y, self.mark_size, self.mark_width)
                # 插入十字标记
                shapes = marks.get_shapes()
                if isinstance(shapes, list):
                    for shape in shapes:
                        cell.shapes(layer_id).insert(shape)
                else:
                    cell.shapes(layer_id).insert(shapes)
            elif i == 1:  # 右上角使用L型标记
                marks = MarkUtils.l(mark_x, mark_y, self.mark_size, self.mark_width)
                # 插入L型标记
                shapes = marks.get_shapes()
                if isinstance(shapes, list):
                    for shape in shapes:
                        cell.shapes(layer_id).insert(shape)
                else:
                    cell.shapes(layer_id).insert(shapes)
            elif i == 2:  # 左下角使用L型标记
                marks = MarkUtils.l(mark_x, mark_y, self.mark_size, self.mark_width).rotate(2)
                # 插入L型标记（旋转90度）
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
                self.create_device_label(cell, label_x, label_y, row, col)
            else:
                # 将 device_id 转换为字符串，作为纯数字标记
                self.create_device_label(cell, label_x, label_y, device_id - 1, 0)  # 假设为第0列
    
    def create_device_label(self, cell, x, y, row, col):
        """
        在指定位置创建字母+数字格式的器件标记
        
        Args:
            cell: 目标单元格
            x, y: 标记起始坐标
            row: 行号（数字）
            col: 列号（字母）
        """
        layer_id = LAYER_DEFINITIONS['labels']['id']
        
        # 生成字母+数字格式的标记
        col_letter = chr(ord('A') + col)  # 0->A, 1->B, 2->C, ...
        row_number = str(row + 1)  # 行号从1开始
        label = col_letter + row_number  # 如 A1, B2, C3
        
        # 设置字符大小和间距
        char_size = self.mark_size * 0.25
        stroke_width = self.mark_width * 0.8
        char_spacing = char_size * 1.7  # 字符间距
        
        # 创建每个字符
        for i, char in enumerate(label):
            char_x = x + i * char_spacing
            char_y = y
            
            # 使用 create_digit 方法处理字母和数字
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
    
    def create_single_device(self, cell_name="FET_Device", x=0, y=0, device_id=None, row=None, col=None, device_params=None):
        """
        创建单个FET器件
        
        Args:
            cell_name: 单元格名称
            x, y: 器件中心坐标
            device_id: 器件编号
            row: 行号（用于生成字母+数字格式的标记）
            col: 列号（用于生成字母+数字格式的标记）
            device_params: 器件参数字典，用于标注
            
        Returns:
            创建的单元格
        """
        cell = self.layout.create_cell(cell_name)
        
        # 确保坐标是浮点数
        x = float(x)
        y = float(y)
        
        # 按层次顺序创建器件结构
        self.create_bottom_gate_electrodes(cell, x, y)
        self.create_dielectric_layer(cell, x, y)
        self.create_channel_material(cell, x, y)
        self.create_source_drain_electrodes(cell, x, y)
        self.create_top_gate_electrode(cell, x, y)
        self.create_alignment_marks(cell, x, y, device_id, row, col)
        
        # 如果有器件参数，添加参数标注
        if device_params:
            self.create_parameter_labels(cell, x, y, device_params)
        
        return cell
    
    def create_device_array(self, rows=10, cols=10, device_spacing_x=None, device_spacing_y=None):
        """
        创建器件阵列
        
        Args:
            rows: 行数
            cols: 列数
            device_spacing_x: 器件横向间距，如果为None则自动计算
            device_spacing_y: 器件纵向间距，如果为None则自动计算
            
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
                    device_id, row, col
                )
                
                # 将器件单元格插入到阵列中
                array_cell.insert(db.CellInstArray(
                    device_cell.cell_index(),
                    db.Trans(0, 0)
                ))
                
                device_id += 1
        
        return array_cell
    
    def scan_parameters_and_create_array(self, param_ranges, rows=10, cols=10, offset_x=0, offset_y=0):
        """
        扫描参数并创建参数变化的器件阵列
        
        Args:
            param_ranges: 参数字典，格式为 {'param_name': [min, max, steps]}
            rows: 行数
            cols: 列数
            offset_x: 阵列起始X坐标偏移
            offset_y: 阵列起始Y坐标偏移
            
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
                
                # gate_space 固定为 2
                current_params['gate_space'] = 2.0
                
                # gate_width 固定为 ch_len/2
                if 'ch_len' in current_params:
                    current_params['gate_width'] = current_params['ch_len'] / 2
                
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
                    current_params
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
    
    # 设置器件参数
    fet.set_device_parameters(
        ch_width=5.0,    # 沟道宽度 5μm
        ch_len=10.0,     # 沟道长度 10μm
        gate_space=2.0,  # 栅极边缘到边缘间距 3.5μm
        gate_width=5.0   # 栅极宽度 5μm
    )
    
    # 创建单个器件进行测试
    print("创建单个FET器件...")
    single_device = fet.create_single_device("Test_FET", 0, 0, 1, 0, 0)  # 位置A1
    print(f"单个器件已创建: {single_device.name}")
    
    # 创建10x10器件阵列
    print("创建10x10器件阵列...")
    device_array = fet.create_device_array(rows=10, cols=10)
    print(f"器件阵列已创建: {device_array.name}")
    
    # 创建参数扫描阵列（行列扫描）
    print("创建参数扫描阵列...")
    param_ranges = {
        'ch_width': [5.0, 15.0, 5],    # 行扫描：沟道宽度从5μm到15μm，5个值
        'ch_len': [3.0, 8.0, 5],       # 列扫描：沟道长度从3μm到8μm，5个值
        # gate_space 固定为 2
        # gate_width 固定为 ch_len/2
    }
    
    # 计算阵列总尺寸并设置偏移
    device_spacing_x = fet.device_margin_x * 2 + 50
    device_spacing_y = fet.device_margin_y * 2 + 50
    array_width = 10 * device_spacing_x
    offset_x = array_width + 500  # 向右偏移阵列宽度+500μm
    
    scan_array = fet.scan_parameters_and_create_array(param_ranges, rows=10, cols=10, offset_x=int(offset_x), offset_y=0)
    print(f"参数扫描阵列已创建: {scan_array.name}")
    
    # 保存布局文件
    output_file = "TEST_FET_COMP.gds"
    fet.layout.write(output_file)
    print(f"布局文件已保存: {output_file}")
    
    print("FET器件生成测试完成！")


if __name__ == "__main__":
    main()
