# -*- coding: utf-8 -*-
"""
Hall Bar器件模块 - 定义完整的霍尔bar器件结构
Hall Bar device module - defines the complete Hall bar device structure.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import klayout.db as db
try:
    import pya
except ImportError:
    pya = db

from config import LAYER_DEFINITIONS, PROCESS_CONFIG
from utils.geometry import GeometryUtils
from utils.mark_utils import MarkUtils
from utils.fanout_utils import draw_pad, draw_trapezoidal_fanout
from typing import cast, Literal


_GF_CACHE = None
_GF_IMPORT_ATTEMPTED = False


def _get_gdsfactory():
    global _GF_CACHE, _GF_IMPORT_ATTEMPTED
    if _GF_IMPORT_ATTEMPTED:
        return _GF_CACHE
    _GF_IMPORT_ATTEMPTED = True
    try:
        import gdsfactory as gf
        _GF_CACHE = gf
    except Exception:
        _GF_CACHE = None
    return _GF_CACHE

class HallBar:
    """Hall Bar器件类
    Hall Bar device class.
    """
    def __init__(self, layout=None, **kwargs):
        self.layout = layout or db.Layout()
        dist_v_value = kwargs.get('dist_v', kwargs.get('Dist_V', 25.0))
        label_anchor_value = kwargs.get('label_anchor', kwargs.get('label_cursor', 'left_top'))
        self._layer_ids = {
            'channel': kwargs.get('channel_layer_id', 13),
            'source_drain': kwargs.get('source_drain_layer_id', 15),
            'labels': kwargs.get('label_layer_id', 3),
            'alignment_marks': kwargs.get('alignment_mark_layer_id', 3),
            'parameter_labels': kwargs.get('parameter_label_layer_id', 6),
        }
        self.setup_layers()

        # ===== 沟道与突出参数 =====
        self.bar_length = kwargs.get('bar_length', 50.0)      # 沟道长度 (μm)
        self.bar_width = kwargs.get('bar_width', 10.0)        # 沟道主宽度 (μm)
        self.v_protrude = kwargs.get('v_protrude_width', 3.0)       # V区突出宽度 (μm)
        self.v_protrude_length = kwargs.get('v_protrude_length', 5.0)  # V区突出区域长度(沿沟道方向)
        self.dist_v = dist_v_value                            # V电极间距 (μm)

        # ===== V电极参数 =====
        self.v_inner_length = kwargs.get('v_inner_length', None)  # 沿沟道方向，None时自动联动
        self.v_inner_width = kwargs.get('v_inner_width', 2.0)    # 沟道宽度方向
        self.v_outer_length = kwargs.get('v_outer_length', 100.0)
        self.v_outer_width = kwargs.get('v_outer_width', 100.0)
        self.v_outer_offset = kwargs.get('v_outer_offset', 18.0) 
        self.v_outer_chamfer = kwargs.get('v_outer_chamfer', 10.0)
        self.v_outer_chamfer_type = kwargs.get('v_outer_chamfer_type', 'straight')
        self.v_fanout_type = kwargs.get('v_fanout_type', 'trapezoidal')
        self.v_outer_offset_x = kwargs.get('v_outer_offset_x', 60)
        self.v_outer_offset_y = kwargs.get('v_outer_offset_y', 120)

        # ===== I电极参数 =====
        self.i_inner_length = kwargs.get('i_inner_length', 10.0)
        self.i_inner_width = kwargs.get('i_inner_width', None)  # None时自动联动
        self.i_outer_length = kwargs.get('i_outer_length', 100.0)
        self.i_outer_width = kwargs.get('i_outer_width', 100.0)
        self.i_outer_offset = kwargs.get('i_outer_offset', 25.0)
        self.i_outer_chamfer = kwargs.get('i_outer_chamfer', 10.0)
        self.i_outer_chamfer_type = kwargs.get('i_outer_chamfer_type', 'straight')
        self.i_fanout_type = kwargs.get('i_fanout_type', 'trapezoidal')
        self.i_outer_offset_x = kwargs.get('i_outer_offset_x', 150)
        self.i_outer_offset_y = kwargs.get('i_outer_offset_y', 0.0)

        # 自动调整outer_offset，保证pad间距不小于10um
        min_pad_gap = 10.0
        min_gap = 20.0
        # I电极outer pad中心x方向偏移
        self.i_outer_offset = kwargs.get('i_outer_offset', self.bar_length/2 + self.i_outer_length/2 + min_gap)
        # V电极outer pad中心y方向偏移
        self.v_outer_offset = kwargs.get('v_outer_offset', (self.bar_width + self.v_protrude)/2 + self.v_outer_length/2 + min_gap)

        # ===== 其余参数 =====
        self.device_margin_x = kwargs.get('device_margin_x', 250.0)
        self.device_margin_y = kwargs.get('device_margin_y', 200.0)
        self.mark_size = kwargs.get('mark_size', 15.0)
        self.mark_width = kwargs.get('mark_width', 2.0)
        self.mark_types = kwargs.get('mark_types', ['sq_missing', 'l', 'l', 'cross'])
        self.mark_rotations = kwargs.get('mark_rotations', [0, 0, 2, 1])
        self.label_size = kwargs.get('label_size', 20.0)
        self.label_font = kwargs.get('label_font', 'C:/Windows/Fonts/OCRAEXT.TTF')
        self.label_anchor = label_anchor_value  # 编号位置: 'right_bottom', 'right_top', 'left_bottom', 'left_top'
        self.label_offset_x = kwargs.get('label_offset_x',  10.0)
        self.label_offset_y = kwargs.get('label_offset_y', -10.0)
        self.electrode_text_label = kwargs.get('electrode_text_label', False)  # 是否为电极添加KLayout text label

    def setup_layers(self):
        for layer_name, layer_info in LAYER_DEFINITIONS.items():
            self.layout.layer(layer_info['id'], 0)
        for layer_id in self._layer_ids.values():
            self.layout.layer(layer_id, 0)

    def _layer_index(self, layer_key):
        return self.layout.layer(self._layer_ids[layer_key], 0)

    def set_device_parameters(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get_layer_ids(self):
        return dict(self._layer_ids)

    def _append_text_shape(self, text, x, y, layer_key):
        if not text:
            return []
        text = str(text)
        layer_id = self._layer_ids[layer_key]

        gf = _get_gdsfactory()
        if gf is not None:
            try:
                text_component = gf.components.text(
                    text=text,
                    size=self.label_size,
                    justify="left",
                    layer=(layer_id, 0),
                )
                bbox = text_component.bbox
                offset_x = x - float(bbox[0][0])
                offset_y = y - float(bbox[0][1])
                polygons = []
                for polygon in text_component.get_polygons():
                    points = [pya.Point(int(px + offset_x), int(py + offset_y)) for px, py in polygon]
                    if len(points) >= 3:
                        polygons.append(pya.Polygon(points))
                if polygons:
                    return polygons
            except Exception:
                pass

        try:
            generator = pya.TextGenerator.default_generator()
            mag = float(self.label_size) / max(generator.dheight(), 1e-9)
            region = generator.text(text, PROCESS_CONFIG["dbu"], mag, False, 0.0, 0.0, 0.0).merged()
            bbox = region.bbox()
            dx = int(round(x / PROCESS_CONFIG["dbu"] - bbox.left))
            dy = int(round(y / PROCESS_CONFIG["dbu"] - bbox.bottom))
            return [region.moved(dx, dy)]
        except Exception:
            return [pya.Text(text, int(x * 1000), int(y * 1000))]

    def _append_note_text(self, text, x, y):
        if not text:
            return []
        return [pya.Text(str(text), int(x * 1000), int(y * 1000))]

    def _normalized_mark_type(self, mark_type):
        aliases = {
            "l": "l_shape",
            "L_shape": "l_shape",
            "t": "t_shape",
            "T_shape": "t_shape",
        }
        return aliases.get(str(mark_type), mark_type)

    def _create_mark(self, x, y, mark_type, rotation):
        normalized = self._normalized_mark_type(mark_type)
        stroke_ratio = max(self.mark_width / max(self.mark_size, 1e-9), 1e-3)

        if normalized == "sq_missing":
            return MarkUtils.sq_missing(x, y, self.mark_size).rotate(rotation)
        if normalized in ("l_shape", "t_shape", "cross_tri"):
            return getattr(MarkUtils, normalized)(x, y, self.mark_size, stroke_ratio).rotate(rotation)
        if normalized in ("square", "circle", "diamond"):
            return getattr(MarkUtils, normalized)(x, y, self.mark_size).rotate(rotation)
        if normalized == "triangle":
            return MarkUtils.triangle(x, y, self.mark_size).rotate(rotation)
        if hasattr(MarkUtils, normalized):
            try:
                return getattr(MarkUtils, normalized)(x, y, self.mark_size, self.mark_width).rotate(rotation)
            except TypeError:
                return getattr(MarkUtils, normalized)(x, y, self.mark_size).rotate(rotation)
        return MarkUtils.cross(x, y, self.mark_size, self.mark_width).rotate(rotation)

    def create_bar(self, cell, x=0.0, y=0.0):
        layer_id = self._layer_index('channel')
        # 沟道主区
        bar = GeometryUtils.create_rectangle(
            x, y, self.bar_length, self.bar_width, center=True
        )
        cell.shapes(layer_id).insert(bar)
        # V区突出
        protrude = self.v_protrude
        dist_v = self.dist_v
        v_w = self.bar_width + protrude * 2
        v_len = self.v_protrude_length
        # 左V区突出区域，中心与左V inner pad对齐
        bar_left = GeometryUtils.create_rectangle(
            x - dist_v/2, y, v_len, v_w, center=True
        )
        cell.shapes(layer_id).insert(bar_left)
        # 右V区突出区域，中心与右V inner pad对齐
        bar_right = GeometryUtils.create_rectangle(
            x + dist_v/2, y, v_len, v_w, center=True
        )
        cell.shapes(layer_id).insert(bar_right)

    def create_contacts(self, cell, x=0.0, y=0.0):
        layer_id = self._layer_index('source_drain')
        # I电极
        I_contacts = [
            ("I_source", (x - self.bar_length/2, y), "left", (x - self.i_outer_offset_x, y + self.i_outer_offset_y)),
            ("I_drain", (x + self.bar_length/2, y), "right", (x + self.i_outer_offset_x, y + self.i_outer_offset_y)),
        ]
        i_inner_width = self.i_inner_width if self.i_inner_width is not None else self.bar_width * 1.1
        for name, (cx, cy), direction, (lx, ly) in I_contacts:
            inner = draw_pad((cx, cy), self.i_inner_length, i_inner_width, chamfer_size=0, chamfer_type='none')
            cell.shapes(layer_id).insert(inner.polygon)
            if direction == "left":
                outer_center = (x - self.i_outer_offset_x, y + self.i_outer_offset_y)
            else:
                outer_center = (x + self.i_outer_offset_x, y + self.i_outer_offset_y)
            outer = draw_pad(outer_center, self.i_outer_length, self.i_outer_width, chamfer_size=self.i_outer_chamfer, chamfer_type=cast(Literal['none', 'straight', 'round'], self.i_outer_chamfer_type))
            cell.shapes(layer_id).insert(outer.polygon)
            fanout = draw_trapezoidal_fanout(inner, outer)
            cell.shapes(layer_id).insert(fanout)
            if self.electrode_text_label:
                for shape in self._append_text_shape(name, outer_center[0], outer_center[1], 'labels'):
                    cell.shapes(self._layer_index('labels')).insert(shape)
        # V电极
        V_contacts = [
            ("V_source_pos", (x - self.dist_v/2, y + (self.bar_width + self.v_protrude)/2), "top", (x - self.v_outer_offset_x, y + self.v_outer_offset_y)),
            ("V_source_neg", (x - self.dist_v/2, y - (self.bar_width + self.v_protrude)/2), "bottom", (x - self.v_outer_offset_x, y - self.v_outer_offset_y)),
            ("V_drain_pos", (x + self.dist_v/2, y + (self.bar_width + self.v_protrude)/2), "top", (x + self.v_outer_offset_x, y + self.v_outer_offset_y)),
            ("V_drain_neg", (x + self.dist_v/2, y - (self.bar_width + self.v_protrude)/2), "bottom", (x + self.v_outer_offset_x, y - self.v_outer_offset_y)),
        ]
        v_inner_length = self.v_inner_length if self.v_inner_length is not None else self.v_protrude_length * 1.1
        for name, (cx, cy), direction, (lx, ly) in V_contacts:
            inner = draw_pad((cx, cy), v_inner_length, self.v_inner_width, chamfer_size=0, chamfer_type='none')
            outer_center = (lx, ly)
            outer = draw_pad(outer_center, self.v_outer_length, self.v_outer_width, chamfer_size=self.v_outer_chamfer, chamfer_type=cast(Literal['none', 'straight', 'round'], self.v_outer_chamfer_type))
            cell.shapes(layer_id).insert(inner.polygon)
            cell.shapes(layer_id).insert(outer.polygon)
            fanout = draw_trapezoidal_fanout(inner, outer)
            cell.shapes(layer_id).insert(fanout)
            if self.electrode_text_label:
                for shape in self._append_text_shape(name, outer_center[0], outer_center[1], 'labels'):
                    cell.shapes(self._layer_index('labels')).insert(shape)

    def create_alignment_marks(self, cell, x=0.0, y=0.0):
        layer_id = self._layer_index('alignment_marks')
        device_width = self.device_margin_x * 2
        device_height = self.device_margin_y * 2
        mark_positions = [
            (x - device_width/2, y + device_height/2),
            (x + device_width/2, y + device_height/2),
            (x - device_width/2, y - device_height/2),
            (x + device_width/2, y - device_height/2)
        ]
        for i, (mark_x, mark_y) in enumerate(mark_positions):
            mark_type = self.mark_types[i] if i < len(self.mark_types) else 'cross'
            rotation = self.mark_rotations[i] if i < len(self.mark_rotations) else 0
            marks = self._create_mark(mark_x, mark_y, mark_type, rotation)
            shapes = marks.get_shapes() if hasattr(marks, 'get_shapes') else [marks]
            if isinstance(shapes, list):
                for shape in shapes:
                    cell.shapes(layer_id).insert(shape)
            else:
                cell.shapes(layer_id).insert(shapes)

    def create_device_label(self, cell, x, y, label_text="HallBar", anchor="center"):
        layer_id = self._layer_index('labels')
        if anchor == "topleft_mark":
            label_x = x - self.device_margin_x + self.label_offset_x
            label_y = y + self.device_margin_y + self.label_offset_y
        else:
            label_x = x + self.label_offset_x
            label_y = y + self.label_offset_y
        text_shapes = self._append_text_shape(label_text, label_x, label_y, 'labels')
        for shape in text_shapes:
            cell.shapes(layer_id).insert(shape)

    def create_single_device(self, cell_name="HallBar_Device", x=0, y=0, label_text="HallBar", show_param_label=True):
        cell = self.layout.create_cell(cell_name)
        x = float(x)
        y = float(y)
        self.create_bar(cell, x, y)
        self.create_contacts(cell, x, y)
        self.create_alignment_marks(cell, x, y)
        self.create_device_label(cell, x, y, label_text, anchor="topleft_mark")
        # 在左下角mark的右上角offset(+10, +10)处标注参数
        if show_param_label:
            # 左下角mark中心
            mark_x = x - self.device_margin_x
            mark_y = y - self.device_margin_y
            label_x = mark_x + 10
            label_y = mark_y + 10
            param_text = f"W={self.bar_width:.2f}, L={self.bar_length:.2f}, VP={self.v_protrude_length:.2f}"
            layer_id = self._layer_index('parameter_labels')
            for shape in self._append_note_text(param_text, label_x, label_y):
                cell.shapes(layer_id).insert(shape)
        return cell

    def create_device_array(self, rows=4, cols=4, device_spacing_x=None, device_spacing_y=None, label_prefix="HB"):
        if device_spacing_x is None:
            device_spacing_x = self.device_margin_x * 2 + 50
        if device_spacing_y is None:
            device_spacing_y = self.device_margin_y * 2 + 50
        array_cell = self.layout.create_cell("HallBar_Array")
        device_id = 1
        label_layer = self._layer_index('labels')
        label_offset_x = 20.0  # um
        label_offset_y = -20.0 # um
        for row in range(rows):
            for col in range(cols):
                device_x = int(col * device_spacing_x)
                device_y = int(row * device_spacing_y)
                # Excel格式label
                excel_label = f"{chr(ord('A') + col)}{row + 1}"
                # 生成单元器件
                device_cell = self.create_single_device(
                    f"HallBar_{device_id:03d}",
                    device_x, device_y, excel_label, show_param_label=False
                )
                array_cell.insert(db.CellInstArray(
                    device_cell.cell_index(),
                    db.Trans(0, 0)
                ))
                # 左上角mark中心
                mark_x = device_x - self.device_margin_x
                mark_y = device_y + self.device_margin_y
                # 插入label（右下角偏移）
                for shape in self._append_text_shape(excel_label, mark_x + label_offset_x, mark_y + label_offset_y, 'labels'):
                    array_cell.shapes(label_layer).insert(shape)
                device_id += 1
        return array_cell 

    def scan_parameters_and_create_array(self, param_ranges, rows=3, cols=3, offset_x=0, offset_y=0, show_param_label=True):
        """
        扫描参数并创建参数变化的器件阵列
        param_ranges: {'param_name': [min, max, steps]}
        rows, cols: 阵列行列数
        offset_x, offset_y: 阵列起始坐标偏移
        show_param_label: 是否显示参数标注（KLayout text）
        """
        scan_cell = self.layout.create_cell("HallBar_Parameter_Scan")
        # 计算参数步长
        param_steps = {}
        for param_name, param_range in param_ranges.items():
            if len(param_range) == 3:
                min_val, max_val, steps = param_range
                param_steps[param_name] = (max_val - min_val) / (steps - 1) if steps > 1 else 0
            else:
                param_steps[param_name] = 0
        device_spacing_x = self.device_margin_x * 2 + 50
        device_spacing_y = self.device_margin_y * 2 + 50
        device_id = 1
        for row in range(rows):
            for col in range(cols):
                current_params = {}
                # 行扫描
                if 'bar_width' in param_ranges:
                    min_val, max_val, steps = param_ranges['bar_width']
                    bar_width = min_val + row * (max_val - min_val) / (steps - 1)
                    current_params['bar_width'] = bar_width
                # 列扫描
                if 'bar_length' in param_ranges:
                    min_val, max_val, steps = param_ranges['bar_length']
                    bar_length = min_val + col * (max_val - min_val) / (steps - 1)
                    current_params['bar_length'] = bar_length
                # 其它参数扫描
                if 'v_protrude_length' in param_ranges:
                    min_val, max_val, steps = param_ranges['v_protrude_length']
                    v_protrude_length = min_val + row * (max_val - min_val) / (steps - 1)
                    current_params['v_protrude_length'] = v_protrude_length
                self.set_device_parameters(**current_params)
                device_x = int(offset_x + col * device_spacing_x)
                device_y = int(offset_y + row * device_spacing_y)
                # Excel格式角标
                excel_label = f"{chr(ord('A') + col)}{row + 1}"
                cell_name = f"HB_SCAN_{device_id:02d}"
                dev_cell = self.create_single_device(cell_name, device_x, device_y, excel_label, show_param_label=show_param_label)
                scan_cell.insert(db.CellInstArray(dev_cell.cell_index(), db.Trans(0, 0)))
                device_id += 1
        return scan_cell


def main():
    """主函数 - 用于测试HallBar器件生成"""
    # 创建HallBar器件实例
    hallbar = HallBar()

    # 设置器件参数
    hallbar.set_device_parameters(
        bar_length=60.0,   # Hall bar长度 60μm
        bar_width=12.0,    # Hall bar宽度 12μm
    )

    # 创建单个器件进行测试
    print("创建单个HallBar器件...")
    single_device = hallbar.create_single_device("Test_HallBar", 0, 0, "Test_HallBar")
    print(f"单个器件已创建: {single_device.name}")

    # 创建4x4器件阵列
    print("创建4x4 HallBar器件阵列...")
    device_array = hallbar.create_device_array(rows=4, cols=4)
    print(f"器件阵列已创建: {device_array.name}")

    # 优雅的参数扫描测试
    print("参数扫描测试：批量生成不同参数的HallBar器件...")
    param_ranges = {
        'bar_width': [8.0, 16.0, 9],    # 行扫描
        'bar_length': [40.0, 80.0, 9],  # 列扫描
        'v_protrude_length': [4.0, 8.0, 4],
    }
    scan_cell = hallbar.scan_parameters_and_create_array(param_ranges, rows=9, cols=9, offset_x=0, offset_y=0)
    print(f"参数扫描器件已创建: {scan_cell.name}")

    # 保存布局文件
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from config import get_gds_path
    
    output_file = get_gds_path("TEST_HALLBAR_COMP.gds")
    hallbar.layout.write(output_file)
    print(f"布局文件已保存: {output_file}")

    print("HallBar器件生成测试完成！")


if __name__ == "__main__":
    main() 
