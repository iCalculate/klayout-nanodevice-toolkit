# -*- coding: utf-8 -*-
"""
TLM器件自动生成模块 - Transfer Length Method device generator
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import klayout.db as db
from config import LAYER_DEFINITIONS
from utils.geometry import GeometryUtils
from utils.text_utils import TextUtils
from utils.mark_utils import MarkUtils
from utils.fanout_utils import draw_pad, draw_trapezoidal_fanout
import math

class TLM:
    """TLM (Transfer Length Method) 器件自动生成类"""
    def __init__(self, layout=None, **kwargs):
        self.layout = layout or db.Layout()
        MarkUtils.set_unit_scale(1000)  # 保证mark尺寸与hallbar一致
        self.setup_layers()
        # ===== 结构主参数 =====
        self.num_electrodes = kwargs.get('num_electrodes', 6)  # 电极数
        # self.width = kwargs.get('width', 20.0)  # 沟道宽度 (μm)  # 已废弃，统一用 channel_width
        self.min_spacing = kwargs.get('min_spacing', 1.0)      # 最小电极间距（inner pad中心间距）
        self.max_spacing = kwargs.get('max_spacing', 20.0)     # 最大电极间距
        self.distribution = kwargs.get('distribution', 'log')  # 间距分布
        self.spacing_mode = kwargs.get('spacing_mode', 'centered')  # 电极间距排列方式：'centered'（默认）或 'left_to_right'
        # ===== pad 参数 =====
        self.inner_pad_length = kwargs.get('inner_pad_length', 0.5)  # inner pad 沟道方向长度
        self.inner_pad_width = kwargs.get('inner_pad_width', None)   # inner pad 垂直方向宽度，None时自动设为 channel_width 的1.2倍
        self.outer_pad_length = kwargs.get('outer_pad_length', 60.0) # outer pad 沟道方向长度
        self.outer_pad_width = kwargs.get('outer_pad_width', 60.0)   # outer pad 垂直方向宽度
        self.outer_pad_spacing = kwargs.get('outer_pad_spacing', None) # outer pad 中心到中心的最小x间距，None时自动设为outer_pad_width的1.1倍
        self.fanout_type = kwargs.get('fanout_type', 'trapezoid')    # 扇出类型
        # outer pad倒角参数
        self.outer_pad_chamfer_type = kwargs.get('outer_pad_chamfer_type', 'round')
        self.outer_pad_chamfer_size = kwargs.get('outer_pad_chamfer_size', 6.0)
        # ===== 版图布局参数 =====
        self.device_margin_x = kwargs.get('device_margin_x', 200.0)
        self.device_margin_y = kwargs.get('device_margin_y', 150.0)
        self.outer_pad_offset_y = kwargs.get('outer_pad_offset_y', 100.0)  # outer pad 上下偏移
        # ===== 标记参数 =====
        self.mark_size = kwargs.get('mark_size', 20.0)
        self.mark_width = kwargs.get('mark_width', 2.0)
        self.add_alignment_mark = kwargs.get('add_alignment_mark', True)
        self.mark_types = kwargs.get('mark_types', ['sq_missing', 'l', 'l', 'cross'])  # 四角mark类型
        self.mark_rotations = kwargs.get('mark_rotations', [0, 0, 2, 1])  # 四角mark旋转角度
        # ===== channel 参数 =====
        self.channel_length = kwargs.get('channel_length', None)  # 沟道区长度，None时自动计算
        self.channel_width = kwargs.get('channel_width', 5.0)    # 沟道区宽度，默认5μm
        # ===== label offset 参数 =====
        self.label_offset_x = kwargs.get('label_offset_x', 30.0)  # Excel label X偏移（相对左上mark中心）
        self.label_offset_y = kwargs.get('label_offset_y', -10.0) # Excel label Y偏移（相对左上mark中心）
        self.label_anchor = kwargs.get('label_cursor', 'left_top')  # 编号位置: 'right_bottom', 'right_top', 'left_bottom', 'left_top'

    def setup_layers(self):
        for layer_name, layer_info in LAYER_DEFINITIONS.items():
            self.layout.layer(layer_info['id'], 0)

    def set_device_parameters(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def generate_electrode_positions(self):
        n = self.num_electrodes
        if n < 3:
            raise ValueError("num_electrodes 必须 >= 3")
        if self.distribution == 'log':
            spacings = [self.min_spacing * (self.max_spacing / self.min_spacing) ** (i / (n - 2)) for i in range(n - 1)]
        elif self.distribution == 'exp':
            # 指数型插值
            import numpy as np
            a = np.log(self.min_spacing)
            b = np.log(self.max_spacing)
            spacings = [np.exp(a + (b - a) * i / (n - 2)) for i in range(n - 1)]
        elif self.distribution == 'inv':
            # 倒数等间距
            spacings = [1 / (1 / self.min_spacing + (1 / self.max_spacing - 1 / self.min_spacing) * i / (n - 2)) for i in range(n - 1)]
        else:
            # 线性等间距
            spacings = [self.min_spacing + (self.max_spacing - self.min_spacing) * i / (n - 2) for i in range(n - 1)]
        # 根据 spacing_mode 排列间距
        if self.spacing_mode == 'centered':
            spacings_sorted = sorted(spacings)
            arranged = [0] * (n - 1)
            center = (n - 2) // 2
            left = center
            right = center + 1
            for idx, val in enumerate(spacings_sorted):
                if idx == 0:
                    arranged[center] = val
                elif idx % 2 == 1:
                    arranged[right] = val
                    right += 1
                else:
                    arranged[left - 1] = val
                    left -= 1
            spacings = arranged
        xs = [0]
        for s in spacings:
            xs.append(xs[-1] + s)
        x_shift = (xs[0] + xs[-1]) / 2
        xs = [x - x_shift for x in xs]
        return xs

    def create_single_device(self, cell_name="TLM_Device", x=0, y=0):
        cell = self.layout.create_cell(cell_name)
        xs = self.generate_electrode_positions()
        # 以(x, y)为本单元中心
        y0 = y
        # inner_pad_width 若为 None，自动设为 channel_width 的 1.2 倍
        pad_width = self.inner_pad_width if self.inner_pad_width is not None else self.channel_width * 1.2
        for i, xc in enumerate(xs):
            layer_id = LAYER_DEFINITIONS['source_drain']['id']
            # inner pad
            inner = draw_pad((xc + x, y0), self.inner_pad_length, pad_width, chamfer_size=0, chamfer_type='none')
            if isinstance(inner.polygon, (db.Polygon, db.Box)):
                cell.shapes(layer_id).insert(inner.polygon)
        # 统计上/下方outer pad的x坐标
        upper_xs = [xc for i, xc in enumerate(xs) if i % 2 == 0]
        lower_xs = [xc for i, xc in enumerate(xs) if i % 2 == 1]
        # 计算最小间距（由参数控制）
        min_outer_pad_spacing = self.outer_pad_spacing if self.outer_pad_spacing is not None else self.outer_pad_width * 1.1
        def distribute_outer_pads(x_list):
            n = len(x_list)
            if n <= 1:
                return x_list
            x_list_sorted = sorted(x_list)
            min_dist = min([x_list_sorted[i+1] - x_list_sorted[i] for i in range(n-1)])
            if min_dist >= min_outer_pad_spacing:
                return x_list  # 间距足够，直接用
            # 均匀分布并整体居中
            total_length = (n - 1) * min_outer_pad_spacing
            center = 0  # 沟道中心x
            start = center - total_length / 2
            return [start + i * min_outer_pad_spacing for i in range(n)]
        upper_xs_dist = distribute_outer_pads(upper_xs)
        lower_xs_dist = distribute_outer_pads(lower_xs)
        upper_idx = 0
        lower_idx = 0
        for i, xc in enumerate(xs):
            layer_id = LAYER_DEFINITIONS['source_drain']['id']
            if i % 2 == 0:
                outer_y = y0 + self.outer_pad_offset_y
                outer_x = upper_xs_dist[upper_idx] + x
                upper_idx += 1
            else:
                outer_y = y0 - self.outer_pad_offset_y
                outer_x = lower_xs_dist[lower_idx] + x
                lower_idx += 1
            outer = draw_pad((outer_x, outer_y), self.outer_pad_length, self.outer_pad_width, chamfer_size=self.outer_pad_chamfer_size, chamfer_type=self.outer_pad_chamfer_type)
            if isinstance(outer.polygon, (db.Polygon, db.Box)):
                cell.shapes(layer_id).insert(outer.polygon)
            # fanout
            inner = draw_pad((xc + x, y0), self.inner_pad_length, pad_width, chamfer_size=0, chamfer_type='none')
            if self.fanout_type == 'trapezoid':
                if i % 2 == 0:
                    # 向上扇出 inner上边->outer下边
                    fanout = draw_trapezoidal_fanout(inner, outer, inner_edge='U', outer_edge='D')
                else:
                    # 向下扇出 inner下边->outer上边
                    fanout = draw_trapezoidal_fanout(inner, outer, inner_edge='D', outer_edge='U')
                cell.shapes(layer_id).insert(fanout)
        # 沟道区域（可视化）
        channel_layer = LAYER_DEFINITIONS['channel_etch']['id']
        ch_x0 = xs[0] + x
        ch_x1 = xs[-1] + x
        # 支持自定义 channel 长宽
        channel_length = self.channel_length if self.channel_length is not None else abs(ch_x1 - ch_x0) * 1.1
        channel_width = self.channel_width
        channel_center = (ch_x0 + ch_x1) / 2
        ch_box = GeometryUtils.create_rectangle(channel_center, y0, channel_length, channel_width, center=True)
        cell.shapes(channel_layer).insert(ch_box)
        # 四角mark
        margin_x = self.device_margin_x
        margin_y = self.device_margin_y
        mark_positions = [
            (x - margin_x, y + margin_y),  # 左上
            (x + margin_x, y + margin_y),  # 右上
            (x - margin_x, y - margin_y),  # 左下
            (x + margin_x, y - margin_y),  # 右下
        ]
        mark_layer = LAYER_DEFINITIONS['alignment_marks']['id']
        for i, (mx, my) in enumerate(mark_positions):
            mark_type = self.mark_types[i] if i < len(self.mark_types) else 'cross'
            rotation = self.mark_rotations[i] if i < len(self.mark_rotations) else 0
            if hasattr(MarkUtils, mark_type):
                if mark_type == 'sq_missing':
                    mark = getattr(MarkUtils, mark_type)(mx, my, self.mark_size).rotate(rotation)
                else:
                    mark = getattr(MarkUtils, mark_type)(mx, my, self.mark_size, self.mark_width).rotate(rotation)
            else:
                mark = MarkUtils.cross(mx, my, self.mark_size, self.mark_width).rotate(rotation)
            shapes = mark.get_shapes() if hasattr(mark, 'get_shapes') else [mark]
            if isinstance(shapes, list):
                for shape in shapes:
                    if isinstance(shape, db.Region):
                        for poly in shape.each():
                            cell.shapes(mark_layer).insert(poly)
                    elif isinstance(shape, (db.Polygon, db.Box)):
                        cell.shapes(mark_layer).insert(shape)
            else:
                if isinstance(shapes, db.Region):
                    for poly in shapes.each():
                        cell.shapes(mark_layer).insert(poly)
                elif isinstance(shapes, (db.Polygon, db.Box)):
                    cell.shapes(mark_layer).insert(shapes)
        # 添加参数label（两行显示）
        label_layer = LAYER_DEFINITIONS['labels']['id']
        # 左下角mark中心
        mark_x = x - margin_x
        mark_y = y - margin_y
        label_x = mark_x + 10
        label_y = mark_y + 15
        line1 = f"W={self.channel_width}, L={channel_length:.2f}, N={self.num_electrodes}"
        line2 = f"Srange=[{self.min_spacing}, {self.max_spacing}], D={self.distribution}"
        text_obj1 = db.Text(line1, int(label_x * 1000), int(label_y * 1000))
        text_obj2 = db.Text(line2, int(label_x * 1000), int((label_y - 12) * 1000))  # 第二行向下偏移12um
        cell.shapes(label_layer).insert(text_obj1)
        cell.shapes(label_layer).insert(text_obj2)
        return cell

    def create_alignment_marks(self, cell, x=0.0, y=0.0):
        layer_id = LAYER_DEFINITIONS['alignment_marks']['id']
        # 上下方各加一个十字
        mark_y_offset = self.device_margin_y
        for mark_y in [y + mark_y_offset, y - mark_y_offset]:
            marks = MarkUtils.cross(x, mark_y, self.mark_size, self.mark_width)
            shapes = marks.get_shapes() if hasattr(marks, 'get_shapes') else [marks]
            if isinstance(shapes, list):
                for shape in shapes:
                    cell.shapes(layer_id).insert(shape)
            else:
                cell.shapes(layer_id).insert(shapes)

    def create_device_array(self, rows=2, cols=2, device_spacing_x=None, device_spacing_y=None, label_prefix="TLM"):
        if device_spacing_x is None:
            device_spacing_x = self.device_margin_x * 2 + 50
        if device_spacing_y is None:
            device_spacing_y = self.device_margin_y * 2 + 50
        array_cell = self.layout.create_cell(f"{label_prefix}_Array")
        label_layer = LAYER_DEFINITIONS['labels']['id']
        device_id = 1
        for row in range(rows):
            for col in range(cols):
                device_x = int(col * device_spacing_x)
                device_y = int(row * device_spacing_y)
                # Excel格式label
                excel_label = f"{chr(ord('A') + col)}{row + 1}"
                # 生成单元器件
                device_cell = self.create_single_device(
                    f"TLM_{device_id:03d}",
                    device_x, device_y
                )
                array_cell.insert(db.CellInstArray(
                    device_cell.cell_index(),
                    db.Trans(0, 0)
                ))
                # 左上角mark中心
                mark_x = device_x - self.device_margin_x
                mark_y = device_y + self.device_margin_y
                # 插入label（偏移由参数控制）
                text_shapes = TextUtils.create_text_freetype(
                    excel_label, mark_x + self.label_offset_x, mark_y + self.label_offset_y,
                    size_um=20, font_path='C:/Windows/Fonts/OCRAEXT.TTF', spacing_um=0.5,
                    anchor=self.label_anchor
                )
                for shape in text_shapes:
                    array_cell.shapes(label_layer).insert(shape)
                device_id += 1
        return array_cell

    def scan_parameters_and_create_array(self, param_ranges, rows=3, cols=3, offset_x=0, offset_y=0):
        """
        优雅的参数扫描阵列生成，支持任意参数映射到行/列/其它。
        param_ranges: {'param_name': [min, max, steps]}，如 {'width': [5, 15, 3], 'max_spacing': [2, 20, 3]}
        rows, cols: 阵列行列数
        offset_x, offset_y: 阵列起始坐标偏移
        """
        scan_cell = self.layout.create_cell("TLM_Parameter_Scan")
        device_spacing_x = self.device_margin_x * 2 + 50
        device_spacing_y = self.device_margin_y * 2 + 50
        device_id = 1
        # 预处理步长
        param_steps = {}
        for param, rng in param_ranges.items():
            if len(rng) == 3:
                min_val, max_val, steps = rng
                param_steps[param] = (max_val - min_val) / (steps - 1) if steps > 1 else 0
            else:
                param_steps[param] = 0
        for row in range(rows):
            for col in range(cols):
                current_params = {}
                # 行优先参数
                if 'width' in param_ranges:
                    min_val, max_val, steps = param_ranges['width']
                    current_params['width'] = min_val + row * (max_val - min_val) / (steps - 1)
                if 'max_spacing' in param_ranges:
                    min_val, max_val, steps = param_ranges['max_spacing']
                    current_params['max_spacing'] = min_val + col * (max_val - min_val) / (steps - 1)
                # 其它参数支持
                for pname, rng in param_ranges.items():
                    if pname in ['width', 'max_spacing']:
                        continue
                    if len(rng) == 3:
                        min_val, max_val, steps = rng
                        # 默认行扫描
                        current_params[pname] = min_val + row * (max_val - min_val) / (steps - 1)
                    else:
                        current_params[pname] = rng[0]
                self.set_device_parameters(**current_params)
                device_x = int(offset_x + col * device_spacing_x)
                device_y = int(offset_y + row * device_spacing_y)
                cell_name = f"TLM_SCAN_{device_id:02d}"
                device_cell = self.create_single_device(cell_name, device_x, device_y)
                scan_cell.insert(db.CellInstArray(device_cell.cell_index(), db.Trans(0, 0)))
                # Excel label
                label_layer = LAYER_DEFINITIONS['labels']['id']
                mark_x = device_x - self.device_margin_x
                mark_y = device_y + self.device_margin_y
                excel_label = f"{chr(ord('A') + col)}{row + 1}"
                text_shapes = TextUtils.create_text_freetype(
                    excel_label, mark_x + self.label_offset_x, mark_y + self.label_offset_y,
                    size_um=20, font_path='C:/Windows/Fonts/OCRAEXT.TTF', spacing_um=0.5
                )
                for shape in text_shapes:
                    scan_cell.shapes(label_layer).insert(shape)
                device_id += 1
        return scan_cell


# main函数生成2x2阵列，四种间距方式
import numpy as np

def main():
    layout = db.Layout()
    # 先生成原有两个单器件cell
    tlm_center = TLM(layout=layout, num_electrodes=8, spacing_mode='centered')
    cell1 = tlm_center.create_single_device("Test_TLM_center_mode", 0, 0)
    print(f"单元器件 Test_TLM_center_mode 已创建: {cell1.name}")
    tlm_order = TLM(layout=layout, num_electrodes=6, spacing_mode='left_to_right')
    cell2 = tlm_order.create_single_device("Test_TLM_order_mode", 0, 0)
    print(f"单元器件 Test_TLM_order_mode 已创建: {cell2.name}")
    # 新增2x2阵列功能
    distributions = ['linear', 'log', 'exp', 'inv']
    array_rows, array_cols = 2, 2
    device_spacing_x = 450
    device_spacing_y = 350
    tlm_list = []
    for idx, dist in enumerate(distributions):
        row = idx // 2
        col = idx % 2
        tlm = TLM(layout=layout, num_electrodes=10, distribution=dist, min_spacing=2, max_spacing=20)
        cell = tlm.create_single_device(f"TLM_{dist}", col * device_spacing_x, row * device_spacing_y)
        tlm_list.append((tlm, cell))
    array_cell = layout.create_cell("TLM_2x2_Array")
    label_layer = LAYER_DEFINITIONS['labels']['id']
    for idx, (tlm, cell) in enumerate(tlm_list):
        row = idx // 2
        col = idx % 2
        device_x = col * device_spacing_x
        device_y = row * device_spacing_y
        array_cell.insert(db.CellInstArray(
            cell.cell_index(),
            db.Trans(device_x, device_y)
        ))
        # 左上角mark中心
        mark_x = device_x - tlm.device_margin_x
        mark_y = device_y + tlm.device_margin_y
        excel_label = f"{chr(ord('A') + col)}{row + 1}"
        text_shapes = TextUtils.create_text_freetype(
            excel_label, mark_x + tlm.label_offset_x, mark_y + tlm.label_offset_y,
            size_um=20, font_path='C:/Windows/Fonts/OCRAEXT.TTF', spacing_um=0.5
        )
        for shape in text_shapes:
            array_cell.shapes(label_layer).insert(shape)
    # 新增参数扫描阵列测试cell
    print("参数扫描测试：批量生成不同参数的TLM器件...")
    tlm_scan = TLM(layout=layout, num_electrodes=8)
    param_ranges = {
        'channel_width': [5.0, 15.0, 3],         # 行扫描
        'max_spacing': [2.0, 20.0, 3],   # 列扫描
        'distribution': ['inv'],         # 固定值
    }
    scan_cell = tlm_scan.scan_parameters_and_create_array(param_ranges, rows=3, cols=3, offset_x=0, offset_y=0)
    print(f"参数扫描器件已创建: {scan_cell.name}")
    output_file = "TEST_TLM_COMP.gds"
    layout.write(output_file)
    print(f"布局文件已保存: {output_file}")
    print("TLM单元器件与2x2阵列生成测试完成！")

if __name__ == "__main__":
    main()