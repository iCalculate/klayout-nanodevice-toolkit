# -*- coding: utf-8 -*-
"""
Text utilities for layout text handling (only freetype method)
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    import pya
    Layout = pya.Layout
    Text = pya.Text
except (ImportError, AttributeError):
    import klayout.db as pya
    Layout = pya.Layout
    Text = pya.Text

from config import DEFAULT_UNIT_SCALE, DEFAULT_DBU
from utils.geometry import GeometryUtils

class TextUtils:
    """文本工具类"""
    UNIT_SCALE = DEFAULT_UNIT_SCALE  # 全局单位缩放，默认为DEFAULT_UNIT_SCALE
    
    @staticmethod
    def set_unit_scale(scale):
        """设置单位缩放"""
        TextUtils.UNIT_SCALE = scale
    
    @staticmethod
    def get_unit_scale():
        """获取单位缩放"""
        return TextUtils.UNIT_SCALE
    
    @staticmethod
    def create_text_freetype(text, x, y, size_um=10, font_path='C:/Windows/Fonts/arial.ttf', spacing_um=2.0):
        """
        使用 freetype-py 将字符串转为多边形点集（适用于KLayout Polygon）。
        参数：
            text (str): 要生成的字符串
            x, y (float): 右上角坐标（单位um）
            size_um (float): 字高（um）
            font_path (str): 字体文件路径（默认 'C:/Windows/Fonts/arial.ttf'）
            spacing_um (float): 字符间距（um）
        返回：
            List[Polygon]: 每个字符的多边形（含孔洞）
        """
        try:
            import freetype
            import numpy as np
        except ImportError:
            print("[WARN] freetype or numpy not available, fallback to rectangle")
            return [GeometryUtils.create_rectangle(x*TextUtils.UNIT_SCALE, y*TextUtils.UNIT_SCALE, size_um * 0.6 * len(text) * TextUtils.UNIT_SCALE, size_um * TextUtils.UNIT_SCALE, center=False)]
        
        polys_all = []
        # 计算字符串总宽度（nm）
        face = freetype.Face(font_path)
        face.set_char_size(int(size_um * 64))
        advances = []
        for char in text:
            face.load_char(char)
            char_advance = face.glyph.advance.x / 64.0 * TextUtils.UNIT_SCALE
            spacing_nm = spacing_um * TextUtils.UNIT_SCALE
            advances.append(char_advance + spacing_nm)
        total_width = sum(advances)
        cursor_x = x * TextUtils.UNIT_SCALE - total_width  # 从右上角向左排布
        y_top = y * TextUtils.UNIT_SCALE
        
        for idx, char in enumerate(text):
            try:
                face = freetype.Face(font_path)
                face.set_char_size(int(size_um * 64))
                face.load_char(char)
                outline = face.glyph.outline
                points = np.array(outline.points, dtype=float)
                start = 0
                ascent = face.size.ascender / 64.0 * TextUtils.UNIT_SCALE
                contours = []
                for c in outline.contours:
                    end = c + 1
                    poly = points[start:end]
                    poly = poly / 64.0
                    poly = poly * TextUtils.UNIT_SCALE
                    poly[:, 1] += y_top + ascent
                    poly[:, 0] += cursor_x
                    klayout_points = [GeometryUtils.Point(int(point[0]), int(point[1])) for point in poly]
                    if len(klayout_points) >= 3:
                        contours.append(klayout_points)
                    start = end
                if contours:
                    outer_contour = contours[0]
                    klayout_polygon = GeometryUtils.Polygon(outer_contour)
                    for i in range(1, len(contours)):
                        hole_points = contours[i]
                        if len(hole_points) >= 3:
                            klayout_polygon.insert_hole(hole_points)
                    polys_all.append(klayout_polygon)
                advance = face.glyph.advance.x / 64.0 * TextUtils.UNIT_SCALE + spacing_um * TextUtils.UNIT_SCALE
                cursor_x += advance
            except Exception as e:
                print(f"[WARN] Failed to process character '{char}': {e}")
                char_box = GeometryUtils.create_rectangle(cursor_x, y_top - size_um * TextUtils.UNIT_SCALE, size_um * 0.6 * TextUtils.UNIT_SCALE, size_um * TextUtils.UNIT_SCALE, center=False)
                polys_all.append(char_box)
                cursor_x += size_um * 0.6 * TextUtils.UNIT_SCALE + spacing_um * TextUtils.UNIT_SCALE
        return polys_all

# 测试部分
if __name__ == "__main__":
    from config import LAYER_DEFINITIONS
    from utils.geometry import GeometryUtils
    
    # 设置单位缩放和精度
    unit_scale = DEFAULT_UNIT_SCALE  # 1000, 1um = 1000dbu
    dbu = DEFAULT_DBU  # 0.001, 1dbu = 1nm
    GeometryUtils.UNIT_SCALE = unit_scale
    TextUtils.set_unit_scale(unit_scale)
    
    # 创建新layout和cell
    layout = Layout()
    layout.dbu = dbu
    top = layout.create_cell('TEST_TEXT_UTILS')
    layer_info = LAYER_DEFINITIONS['labels']
    layer = layout.layer(layer_info['id'], 0, layer_info['name'])
    
    size = 10  # um
    start_x = 0  # um，右上角x
    start_y = 0  # um，右上角y
    lines = [
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "abcdefghijklmnopqrstuvwxyz",
        "0123456789",
        "!@#$%^&*()_+-=[]{}|;:',.<>/?"
    ]
    line_height = size * 1.2
    for i, line in enumerate(lines):
        y_pos = start_y - i * line_height
        shapes = TextUtils.create_text_freetype(line, start_x, y_pos, size_um=size, spacing_um=2.0)
        for shape in shapes:
            top.shapes(layer).insert(shape)
    layout.write('TEST_TEXT_UTILS.gds')
    print('TEST_TEXT_UTILS.gds generated successfully.')