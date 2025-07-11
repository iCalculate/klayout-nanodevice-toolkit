# -*- coding: utf-8 -*-
"""
Digital Display Module - Generate digits and letters using 7-segment/expanded display style
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pya
import math
from config import PROCESS_CONFIG
from utils.geometry import GeometryUtils

class DigitalDisplay:
    """7-segment digital display class (米字数码管风格，支持四斜+短横)"""

    @staticmethod
    def get_segments(size, stroke_width):
        min_size = max(size, 5.0)
        min_width = max(stroke_width, PROCESS_CONFIG['min_feature_size'])
        seg_len_h = min_size * 1 + min_width
        seg_len_v = min_size * 1 + min_width
        offset_x = min_size * 0.5
        offset_y = min_size * 1
        diag_len = (offset_x**2 + offset_y**2) ** 0.5
        diag_offset = min_size * 0.5
        mid_y = 0
        mid_x = 0
        # 米字数码管四斜线中心点都在(0,0)，长度为sqrt(2)*min_size
        diag = min_size * 1.1  # 适当加长
        # 短横线参数
        short_h_len = min_size * 0.5
        short_h_x = offset_x*0.5  # 居中
        return {
            'a': (0,  offset_y, 'h', None),   # Top horizontal
            'b': ( offset_x, 0.5 * offset_y, 'v', None), # Upper right vertical
            'c': ( offset_x, -0.5 * offset_y, 'v', None),# Lower right vertical
            'd': (0, -offset_y, 'h', None),  # Bottom horizontal
            'e': (-offset_x, -0.5 * offset_y, 'v', None),# Lower left vertical
            'f': (-offset_x, 0.5 * offset_y, 'v', None), # Upper left vertical
            'g': (0, mid_y, 'h', None),   # Middle horizontal
            'g1': (0, min_size * 0.25, 'h', None), # Upper midline
            'g2': (0, -min_size * 0.25, 'h', None), # Lower midline
            'sr': (short_h_x, 0, 'sh', None), # 右侧短横线
            'sl': (-short_h_x, 0, 'sh', None), # 左侧短横线
            # 米字四斜线
            'd1': (0, 0, 'd1', None),  # 左上-右下
            'd2': (0, 0, 'd2', None),  # 右上-左下
            'd3': (0, 0, 'd3', None),  # 左下-右上
            'd4': (0, 0, 'd4', None),  # 右下-左上
            'jl': (0, -offset_y/2, 'v', None),       # lower middle vertical stroke
            'jh': (0, offset_y/2, 'v', None),      # upper middle vertical stroke
            'k': (0, 0, 'd3', None),      # / diagonal (full height, 兼容旧用法)
            'l': (0, 0, 'd4', None),      # \ diagonal (full height, 兼容旧用法)
            'q': (offset_x*0.6, -offset_y*0.6, 'd3', None), # Q尾巴
        }, seg_len_h, seg_len_v, min_width, diag_len, diag_offset

    LETTERS = {
        'A': ['a', 'b', 'c', 'e', 'f', 'g'],
        'B': ['f', 'e', 'c', 'd', 'g1'],
        'C': ['a', 'd', 'e', 'f'],
        'D': ['e', 'd', 'c', 'b', 'g1'],
        'E': ['a', 'd', 'e', 'f', 'g'],
        'F': ['a', 'e', 'f', 'g'],
        'G': ['a', 'c', 'd', 'e', 'f', 'sr'],
        'H': ['b', 'c', 'e', 'f', 'g'],
        'I': ['jl', 'jh'],
        'J': ['b', 'c', 'd'],
        'K': ['f', 'e', 'sl', 'd2', 'd3'],
        'L': ['d', 'e', 'f'],
        'M': ['f', 'b', 'd1', 'd2', 'e', 'c'],
        'N': ['f', 'b', 'd3','e', 'c', 'd1'],
        'O': ['a', 'b', 'c', 'd', 'e', 'f'],
        'P': ['a', 'b', 'e', 'f', 'g'],
        'Q': ['a', 'b', 'c', 'd', 'e', 'f', 'd3'],
        'R': ['a', 'b', 'e', 'f', 'g', 'd3'],
        'S': ['a', 'c', 'd', 'f', 'g'],
        'T': ['a', 'jh', 'jl'],
        'U': ['b', 'c', 'd', 'e', 'f'],
        'V': ['f','e', 'd4', 'd2'],
        'W': ['e', 'f', 'd3', 'd4', 'b', 'c'],
        'X': ['d1', 'd2', 'd3', 'd4'],
        'Y': ['d1', 'd2', 'jl'],
        'Z': ['a', 'd', 'd2', 'd4'],
    }

    DIGITS = {
        '0': ['a', 'b', 'c', 'd', 'e', 'f'],
        '1': ['b', 'c'],
        '2': ['a', 'b', 'd', 'e', 'g'],
        '3': ['a', 'b', 'c', 'd', 'g'],
        '4': ['b', 'c', 'f', 'g'],
        '5': ['a', 'c', 'd', 'f', 'g'],
        '6': ['a', 'c', 'd', 'e', 'f', 'g'],
        '7': ['a', 'b', 'c'],
        '8': ['a', 'b', 'c', 'd', 'e', 'f', 'g'],
        '9': ['a', 'b', 'c', 'd', 'f', 'g'],
    }

    @staticmethod
    def create_digit(digit, x, y, size=10.0, stroke_width=1.0, center=True):
        segments_dict, seg_len_h, seg_len_v, min_width, diag_len, diag_offset = DigitalDisplay.get_segments(size, stroke_width)
        min_size = max(size, 5.0)
        offset_x = min_size * 0.5
        offset_y = min_size * 1
        diag = min_size * 1.0
        short_h_len = min_size * 0.5
        if digit in DigitalDisplay.DIGITS:
            segments = DigitalDisplay.DIGITS[digit]
        elif digit in DigitalDisplay.LETTERS:
            segments = DigitalDisplay.LETTERS[digit]
        else:
            print(f"[WARN] Unsupported digit/letter: {digit}")
            return []
        polygons = []
        for seg_name in segments:
            if seg_name not in segments_dict:
                continue
            dx, dy, orient, extra = segments_dict[seg_name]
            cx = x + dx
            cy = y + dy
            if orient == 'h':
                w, h = seg_len_h, min_width
                rect = GeometryUtils.create_rectangle_polygon(cx, cy, w, h, center=True)
                polygons.append(rect)
            elif orient == 'sh':  # 短横线
                w, h = short_h_len, min_width
                rect = GeometryUtils.create_rectangle_polygon(cx, cy, w, h, center=True)
                polygons.append(rect)
            elif orient == 'v':
                w, h = min_width, seg_len_v
                rect = GeometryUtils.create_rectangle_polygon(cx, cy, w, h, center=True)
                polygons.append(rect)
            elif orient == 'd1':  # 左上-右下
                s = GeometryUtils.UNIT_SCALE
                half = diag * s / 2
                wx = min_width * s / 2
                points = [
                    GeometryUtils.Point(int(cx * s), int(cy * s - wx)),
                    GeometryUtils.Point(int(cx * s - wx), int(cy * s - wx)),
                    GeometryUtils.Point(int(cx * s - half), int(cy * s + 2*half - wx)),
                    GeometryUtils.Point(int(cx * s - half), int(cy * s + 2*half + wx)),
                    GeometryUtils.Point(int(cx * s - half + wx), int(cy * s + 2*half + wx)),
                    GeometryUtils.Point(int(cx * s), int(cy * s + wx)),
                ]
                polygons.append(GeometryUtils.Polygon(points))
            elif orient == 'd2':  # 右上-左下
                s = GeometryUtils.UNIT_SCALE
                half = diag * s / 2
                wx = min_width * s / 2
                points = [
                    GeometryUtils.Point(int(cx * s), int(cy * s - wx)),
                    GeometryUtils.Point(int(cx * s + wx), int(cy * s - wx)),
                    GeometryUtils.Point(int(cx * s + half), int(cy * s + 2*half - wx)),
                    GeometryUtils.Point(int(cx * s + half), int(cy * s + 2*half + wx)),
                    GeometryUtils.Point(int(cx * s + half - wx), int(cy * s + 2*half + wx)),
                    GeometryUtils.Point(int(cx * s), int(cy * s + wx)),
                ]
                polygons.append(GeometryUtils.Polygon(points))
            elif orient == 'd3':  # 左下-右上
                s = GeometryUtils.UNIT_SCALE
                half = diag * s / 2
                wx = min_width * s / 2
                points = [
                    GeometryUtils.Point(int(cx * s), int(cy * s + wx)),
                    GeometryUtils.Point(int(cx * s + wx), int(cy * s + wx)),
                    GeometryUtils.Point(int(cx * s + half), int(cy * s - 2*half + wx)),
                    GeometryUtils.Point(int(cx * s + half), int(cy * s - 2*half - wx)),
                    GeometryUtils.Point(int(cx * s + half - wx), int(cy * s - 2*half - wx)),
                    GeometryUtils.Point(int(cx * s), int(cy * s - wx)),
                ]
                polygons.append(GeometryUtils.Polygon(points))
            elif orient == 'd4':  # 右下-左上
                s = GeometryUtils.UNIT_SCALE
                half = diag * s / 2
                wx = min_width * s / 2
                points = [
                    GeometryUtils.Point(int(cx * s), int(cy * s + wx)),
                    GeometryUtils.Point(int(cx * s - wx), int(cy * s + wx)),
                    GeometryUtils.Point(int(cx * s - half), int(cy * s - 2*half + wx)),
                    GeometryUtils.Point(int(cx * s - half), int(cy * s - 2*half - wx)),
                    GeometryUtils.Point(int(cx * s - half + wx), int(cy * s - 2*half - wx)),
                    GeometryUtils.Point(int(cx * s), int(cy * s - wx)),
                ]
                polygons.append(GeometryUtils.Polygon(points))
            elif orient == 'j':  # center vertical (full height)
                w, h = min_width, seg_len_v * 2
                rect = GeometryUtils.create_rectangle_polygon(cx, cy, w, h, center=True)
                polygons.append(rect)
            elif orient == 'd3':  # / diagonal (full height)
                s = GeometryUtils.UNIT_SCALE
                dx1 = -offset_x * s
                dy1 = -offset_y * s
                dx2 = offset_x * s
                dy2 = offset_y * s
                wx = min_width * 0.7 * s
                wy = min_width * 0.7 * s
                cx_scaled = cx * s
                cy_scaled = cy * s
                points = [
                    GeometryUtils.Point(int(cx_scaled + dx1), int(cy_scaled + dy1)),
                    GeometryUtils.Point(int(cx_scaled + dx2), int(cy_scaled + dy2)),
                    GeometryUtils.Point(int(cx_scaled + dx2 + wx), int(cy_scaled + dy2 + wy)),
                    GeometryUtils.Point(int(cx_scaled + dx1 + wx), int(cy_scaled + dy1 + wy)),
                ]
                polygons.append(GeometryUtils.Polygon(points))
            elif orient == 'd4':  # \\ diagonal (full height)
                s = GeometryUtils.UNIT_SCALE
                dx1 = -offset_x * s
                dy1 = offset_y * s
                dx2 = offset_x * s
                dy2 = -offset_y * s
                wx = min_width * 0.7 * s
                wy = min_width * 0.7 * s
                cx_scaled = cx * s
                cy_scaled = cy * s
                points = [
                    GeometryUtils.Point(int(cx_scaled + dx1), int(cy_scaled + dy1)),
                    GeometryUtils.Point(int(cx_scaled + dx2), int(cy_scaled + dy2)),
                    GeometryUtils.Point(int(cx_scaled + dx2 + wx), int(cy_scaled + dy2 + wy)),
                    GeometryUtils.Point(int(cx_scaled + dx1 + wx), int(cy_scaled + dy1 + wy)),
                ]
                polygons.append(GeometryUtils.Polygon(points))
        return polygons

# 末尾集成主程序测试入口
if __name__ == "__main__":
    import sys
    import os
    try:
        import pya
        Layout = pya.Layout
        Text = pya.Text
    except (ImportError, AttributeError):
        import klayout.db as pya
        Layout = pya.Layout
        Text = pya.Text
    from config import LAYER_DEFINITIONS
    from utils.mark_utils import MarkUtils
    from utils.geometry import GeometryUtils
    from utils.text_utils import set_unit_scale, get_unit_scale

    unit_scale = 1000
    MarkUtils.set_unit_scale(unit_scale)
    GeometryUtils.UNIT_SCALE = unit_scale
    set_unit_scale(unit_scale)

    # 数字行
    numbers = [str(i) for i in range(10)]
    # 大写字母
    letters = [c for c in DigitalDisplay.LETTERS.keys() if c.isupper()]
    letters.sort()

    layout = Layout()
    top = layout.create_cell('TEST_DIGITS_LETTERS')
    layer_info = LAYER_DEFINITIONS['labels']
    layer = layout.layer(layer_info['id'], 0, layer_info['name'])

    size = 10.0
    stroke = 2.0
    spacing_x = 30.0
    spacing_y = 40.0
    n_cols = 10
    unit_scale = get_unit_scale()

    # 绘制数字行
    for idx, char in enumerate(numbers):
        x = idx * spacing_x
        y = 0
        polygons = DigitalDisplay.create_digit(char, x, y, size=size, stroke_width=stroke)
        for poly in polygons:
            top.shapes(layer).insert(poly)
        text = Text(char, int(x * unit_scale), int((y - size*2) * unit_scale))
        top.shapes(layer).insert(text)

    # 绘制大写字母，整体下移一行
    for idx, char in enumerate(letters):
        col = idx % n_cols
        row = idx // n_cols
        x = col * spacing_x
        y = -(row + 1) * spacing_y
        polygons = DigitalDisplay.create_digit(char, x, y, size=size, stroke_width=stroke)
        for poly in polygons:
            top.shapes(layer).insert(poly)
        text = Text(char, int(x * unit_scale), int((y - size*2) * unit_scale))
        top.shapes(layer).insert(text)

    layout.write('TEST_DIGITS_UTILS.gds')
    print('GDS file TEST_DIGITS_UTILS.gds generated.') 