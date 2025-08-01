# -*- coding: utf-8 -*-
"""
标记工具模块 - 支持多种形状的对准标记
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import MARK_SHAPES, DEFAULT_UNIT_SCALE
from utils.geometry import GeometryUtils

class MarkWrapper:
    """Mark包装器类，支持链式调用的旋转功能

    Mark wrapper class supporting chained rotation operations.
    """
    
    def __init__(self, shapes, x, y):
        """
        初始化包装器
        
        Initialize the wrapper.
        ``shapes`` can be a single shape, region, or list of shapes.
        ``x`` and ``y`` specify the center coordinates of the mark.
        """
        self.shapes = shapes
        self.x = x
        self.y = y
        self.rotation = 0
    
    def rotate(self, angle):
        """
        旋转mark
        angle: 旋转角度（度），正值逆时针

        Rotate the mark. ``angle`` is in degrees, positive for counter-clockwise.
        """
        from klayout.db import Trans
        self.rotation = angle
        return self
    
    def get_shapes(self):
        """获取旋转后的shapes"""
        from klayout.db import Trans
        
        if self.rotation == 0:
            return self.shapes
        
        # 计算旋转中心（以mark中心为原点）
        # 注意：这里需要转换为数据库单位
        center_x = int(self.x * MarkUtils.UNIT_SCALE)
        center_y = int(self.y * MarkUtils.UNIT_SCALE)
        
        # 创建旋转变换：先移动到旋转中心，旋转，再移回
        # 1. 移动到旋转中心
        trans1 = Trans(0, False, -center_x, -center_y)
        # 2. 绕原点旋转
        trans2 = Trans(self.rotation, False, 0, 0)
        # 3. 移回原位置
        trans3 = Trans(0, False, center_x, center_y)
        # 组合变换
        trans = trans3 * trans2 * trans1
        
        # 应用旋转
        if isinstance(self.shapes, list):
            return [shape.transformed(trans) for shape in self.shapes]
        else:
            return self.shapes.transformed(trans)

class MarkUtils:
    """标记工具类

    Utility class for creating alignment and measurement marks.
    """
    UNIT_SCALE = DEFAULT_UNIT_SCALE  # 全局单位缩放，默认为DEFAULT_UNIT_SCALE
    # Global unit scale, defaults to ``DEFAULT_UNIT_SCALE``

    @staticmethod
    def set_unit_scale(scale):
        MarkUtils.UNIT_SCALE = scale
        GeometryUtils.UNIT_SCALE = scale

    @staticmethod
    def create_mark(shape, x, y, size, width=None, **kwargs):
        s = MarkUtils.UNIT_SCALE
        if shape == 'cross':
            return MarkUtils.cross(x, y, size * s, (width or size * 0.1) * s)
        elif shape == 'square':
            return MarkUtils.square(x, y, size * s)
        elif shape == 'circle':
            return MarkUtils.circle(x, y, size * s)
        elif shape == 'diamond':
            return MarkUtils.diamond(x, y, size * s)
        elif shape == 'triangle':
            direction = kwargs.get('direction', 'up')
            return MarkUtils.triangle(x, y, size * s, direction)
        elif shape == 'L_shape':
            return MarkUtils.l(x, y, size * s, (width or size * 0.1) * s)
        elif shape == 'T_shape':
            return MarkUtils.t(x, y, size * s, (width or size * 0.1) * s)
        else:
            return MarkUtils.cross(x, y, size * s, (width or size * 0.1) * s)

    # All mark creation functions below return MarkWrapper objects for chainable rotation
    @staticmethod
    def cross(x, y, size, width):
        shapes = GeometryUtils.create_cross(x, y, size, width)
        return MarkWrapper(shapes, x, y)

    @staticmethod
    def square(x, y, size=10.0):
        shapes = GeometryUtils.create_rectangle(x, y, size, size, center=True)
        return MarkWrapper(shapes, x, y)

    @staticmethod
    def circle(x, y, size=10.0):
        radius = size / 2
        shapes = GeometryUtils.create_circle(x, y, radius)
        return MarkWrapper(shapes, x, y)

    @staticmethod
    def diamond(x, y, size=10.0):
        shapes = GeometryUtils.create_diamond(x, y, size)
        return MarkWrapper(shapes, x, y)

    @staticmethod
    def triangle(x, y, size=10.0, direction='up'):
        shapes = GeometryUtils.create_triangle(x, y, size, direction)
        return MarkWrapper(shapes, x, y)

    @staticmethod
    def l(x, y, size, width):
        shapes = GeometryUtils.create_L_shape(x, y, size, width/size, 0.5)
        return MarkWrapper(shapes, x, y)

    @staticmethod
    def t(x, y, size, width):
        shapes = GeometryUtils.create_T_shape(x, y, size, width/size, 0.5)
        return MarkWrapper(shapes, x, y)

    @staticmethod
    def semi_cross(x, y, size, width, head_size=None, hole_radius=None):
        # 如果head_size和hole_radius为None，则使用size的0.4倍作为默认值
        if head_size is None:
            head_size = size * 0.2
        if hole_radius is None:
            hole_radius = size * 0.2
        shapes = GeometryUtils.create_semiconductor_cross(x, y, size, width, head_size, hole_radius)
        return MarkWrapper(shapes, x, y)

    @staticmethod
    def cross_pos(x, y, size=10.0, ratio=0.1):
        # Always return a list of shapes if compound
        shapes = GeometryUtils.create_cross_positive(x, y, size, ratio)
        return MarkWrapper(shapes, x, y)

    @staticmethod
    def cross_neg(x, y, size=10.0, ratio=0.1, insert_ratio=0.8, box_margin=5):
        shapes = GeometryUtils.create_cross_negative(x, y, size, ratio, insert_ratio, int(box_margin))
        return MarkWrapper(shapes, x, y)

    @staticmethod
    def l_shape(x, y, size=10.0, ratio=0.1, arm_ratio=0.5):
        shapes = GeometryUtils.create_L_shape(x, y, size, ratio, arm_ratio)
        return MarkWrapper(shapes, x, y)

    @staticmethod
    def t_shape(x, y, size=10.0, ratio=0.1, arm_ratio=0.5):
        shapes = GeometryUtils.create_T_shape(x, y, size, ratio, arm_ratio)
        return MarkWrapper(shapes, x, y)

    @staticmethod
    def sq_missing(x, y, size, missing=(2,4)):
        shapes = GeometryUtils.create_square_with_missing_quadrants(x, y, size, missing)
        return MarkWrapper(shapes, x, y)

    @staticmethod
    def sq_missing_border(x, y, size=10.0, border_ratio=0.1, missing=(2,4)):
        shapes = GeometryUtils.create_square_with_missing_quadrants_with_border(x, y, size, border_ratio, missing)
        return MarkWrapper(shapes, x, y)

    @staticmethod
    def create_mark_array(mark_func, start_x, start_y, n_row, n_col, dx, dy, *args, **kwargs):
        s = MarkUtils.UNIT_SCALE
        marks = []
        for i in range(n_row):
            for j in range(n_col):
                x = start_x + j * dx
                y = start_y + i * dy
                mark = mark_func(x * s, y * s, *args, **kwargs)
                marks.append(mark)
        return marks

    @staticmethod
    def create_alignment_marks(x, y, size, mark_type='cross', width=None):
        marks = []
        half_size = size * MarkUtils.UNIT_SCALE / 2
        positions = [
            (x - half_size, y - half_size),
            (x + half_size, y - half_size),
            (x - half_size, y + half_size),
            (x + half_size, y + half_size)
        ]
        for pos_x, pos_y in positions:
            mark = MarkUtils.create_mark(mark_type, pos_x, pos_y, size * MarkUtils.UNIT_SCALE * 0.3, width)
            marks.append(mark.get_shapes())
        return marks

    @staticmethod
    def create_corner_marks(x, y, size, mark_type='L_shape', width=None):
        marks = []
        half_size = size * MarkUtils.UNIT_SCALE / 2
        mark_size = size * MarkUtils.UNIT_SCALE * 0.2
        corners = [
            (x - half_size, y - half_size, 'up'),
            (x + half_size, y - half_size, 'up'),
            (x - half_size, y + half_size, 'down'),
            (x + half_size, y + half_size, 'down')
        ]
        for pos_x, pos_y, direction in corners:
            if mark_type == 'triangle':
                mark = MarkUtils.triangle(pos_x, pos_y, mark_size, direction)
            else:
                mark = MarkUtils.create_mark(mark_type, pos_x, pos_y, mark_size, width)
            marks.append(mark.get_shapes())
        return marks

    @staticmethod
    def create_center_mark(x, y, size, mark_type='cross', width=None):
        return MarkUtils.create_mark(mark_type, x, y, size, width)

    @staticmethod
    def create_grid_marks(start_x, start_y, end_x, end_y, spacing, mark_type='cross', size=20, width=None):
        marks = []
        x = start_x
        while x <= end_x:
            y = start_y
            while y <= end_y:
                mark = MarkUtils.create_mark(mark_type, x, y, size, width)
                marks.append(mark.get_shapes())
                y += spacing
            x += spacing
        return marks

    @staticmethod
    def create_measurement_marks(x, y, size, mark_type='cross', width=None):
        marks = []
        mark_size = size * MarkUtils.UNIT_SCALE * 0.15
        positions = [
            (x - size * MarkUtils.UNIT_SCALE / 2, y - size * MarkUtils.UNIT_SCALE / 2),
            (x + size * MarkUtils.UNIT_SCALE / 2, y - size * MarkUtils.UNIT_SCALE / 2),
            (x - size * MarkUtils.UNIT_SCALE / 2, y + size * MarkUtils.UNIT_SCALE / 2),
            (x + size * MarkUtils.UNIT_SCALE / 2, y + size * MarkUtils.UNIT_SCALE / 2),
            (x, y)
        ]
        for pos_x, pos_y in positions:
            mark = MarkUtils.create_mark(mark_type, pos_x, pos_y, mark_size, width)
            marks.append(mark.get_shapes())
        return marks

    @staticmethod
    def create_orientation_mark(x, y, size, mark_type='triangle', direction='up'):
        return MarkUtils.create_mark(mark_type, x, y, size, direction=direction)

    @staticmethod
    def create_identification_mark(x, y, size, mark_type='square', width=None):
        return MarkUtils.create_mark(mark_type, x, y, size, width)

    @staticmethod
    def create_mark_cell(layout, cell_name, mark_func, layer_id, x, y, *args, **kwargs):
        cell = layout.create_cell(cell_name)
        mark = mark_func(0, 0, *args, **kwargs)
        shapes = mark.get_shapes()
        if isinstance(shapes, list):
            for shape in shapes:
                cell.shapes(layer_id).insert(shape)
        else:
            cell.shapes(layer_id).insert(shapes)
        # The returned cell is always created in the provided layout, not a temp layout
        from klayout.db import Trans
        return cell, Trans(int(x * MarkUtils.UNIT_SCALE), int(y * MarkUtils.UNIT_SCALE))

    @staticmethod
    def cross_tri(x, y, size=10.0, ratio=0.1, triangle_leg_ratio=0.3):
        shapes = GeometryUtils.create_cross_with_triangle(x, y, size, ratio, triangle_leg_ratio)
        return MarkWrapper(shapes, x, y)

    @staticmethod
    def sq_missing_rotborder(x, y, size=10.0, missing=(2,4), border_ratio=0.1):
        # Based on previous create_square_with_missing_quadrants_and_border_mark
        original_mark = MarkUtils.sq_missing(x, y, size, missing)
        border_frame = GeometryUtils.create_square_with_missing_quadrants_and_border(x, y, size, missing, border_ratio)
        if isinstance(original_mark.shapes, list):
            shapes = original_mark.shapes + [border_frame]
        else:
            shapes = [original_mark.shapes, border_frame]
        return MarkWrapper(shapes, x, y)

    @staticmethod
    def sq_missing_diff_rotborder(x, y, size=10.0, missing=(2,4), border_ratio=0.1):
        shapes = GeometryUtils.create_square_with_missing_quadrants_diff_and_rotated_border(x, y, size, missing, border_ratio)
        return MarkWrapper(shapes, x, y)

    @staticmethod
    def regular_polygon(x, y, size=10.0, n_sides=6):
        shapes = GeometryUtils.create_regular_polygon(x, y, size/2, n_sides)
        return MarkWrapper(shapes, x, y)

    @staticmethod
    def chamfered_octagon(x, y, size=10.0, chamfer_ratio=0.25):
        shapes = GeometryUtils.create_chamfered_octagon(x, y, size, chamfer_ratio)
        return MarkWrapper(shapes, x, y) 

if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    try:
        import pya
        Layout = pya.Layout
    except (ImportError, AttributeError):
        import klayout.db as pya
        Layout = pya.Layout
    import numpy as np
    from utils.geometry import GeometryUtils
    from utils.text_utils import TextUtils
    from config import LAYER_DEFINITIONS

    # Set database unit scale (1 nm per unit, 0.001 um)
    MarkUtils.set_unit_scale(1000)  # All dimensions in um

    # Create a new layout and cell
    layout = Layout()
    layout.dbu = 0.001  # 1 nm per unit
    cell = layout.create_cell("Mark_Test")

    # Get the standard mark layer (alignment_marks) and text layer (labels)
    layer_info = LAYER_DEFINITIONS['alignment_marks']
    layer_id = layout.layer(layer_info['id'], 0, layer_info['name'])
    text_layer_info = LAYER_DEFINITIONS['labels']
    text_layer_id = layout.layer(text_layer_info['id'], 0, text_layer_info['name'])

    # Mark size and grid arrangement
    size_um = 10.0  # Each mark is 10um
    width_um = 1.0  # Default line width for marks
    n_cols = 5      # Number of columns in the grid
    n_rows = 4      # Number of rows in the grid
    spacing = 25.0  # Spacing between marks (um)
    start_x = 0
    start_y = 0

    # 全局旋转角度
    # Global rotation angle
    rotation = 2

    # List of (function, kwargs, description) for all mark types to test
    mark_tests = [
        (MarkUtils.cross, dict(size=size_um, width=size_um*0.1), "Cross"),
        (MarkUtils.square, dict(size=size_um), "Square"),
        (MarkUtils.circle, dict(size=size_um), "Circle"),
        (MarkUtils.diamond, dict(size=size_um), "Diamond"),
        (MarkUtils.triangle, dict(size=size_um, direction='up'), "Triangle Up"),
        (MarkUtils.triangle, dict(size=size_um, direction='down'), "Triangle Down"),
        (MarkUtils.l, dict(size=size_um, width=size_um*0.1), "L"),
        (MarkUtils.t, dict(size=size_um, width=size_um*0.1), "T"),
        (MarkUtils.semi_cross, dict(size=size_um, width=size_um*0.1, head_size=2.0, hole_radius=2.0), "Semi Cross"),
        (MarkUtils.cross_pos, dict(size=size_um, ratio=0.15), "Cross Pos"),
        (MarkUtils.cross_neg, dict(size=size_um, ratio=0.15, insert_ratio=0.7, box_margin=3), "Cross Neg"),
        (MarkUtils.l_shape, dict(size=size_um, ratio=0.15, arm_ratio=0.7), "L Shape"),
        (MarkUtils.t_shape, dict(size=size_um, ratio=0.15, arm_ratio=0.7), "T Shape"),
        (MarkUtils.sq_missing, dict(size=size_um, missing=(2,4)), "Sq Missing"),
        (MarkUtils.sq_missing_border, dict(size=size_um, border_ratio=0.15, missing=(2,4)), "Sq Missing Border"),
        (MarkUtils.cross_tri, dict(size=size_um, ratio=0.15, triangle_leg_ratio=0.3), "Cross Tri"),
        (MarkUtils.sq_missing_rotborder, dict(size=size_um, missing=(2,4), border_ratio=0.15), "Sq Missing Rot Border"),
        (MarkUtils.sq_missing_diff_rotborder, dict(size=size_um, missing=(2,4), border_ratio=0.15), "Sq Missing Diff Rot Border"),
        (MarkUtils.regular_polygon, dict(size=size_um, n_sides=6), "Hexagon"),
        (MarkUtils.chamfered_octagon, dict(size=size_um, chamfer_ratio=0.25), "Chamfered Oct"),
    ]

    total_marks = len(mark_tests)

    # Arrange marks in a grid
    for idx, (func, kwargs, desc) in enumerate(mark_tests):
        row = idx // n_cols
        col = idx % n_cols
        x = start_x + col * spacing
        y = start_y - row * spacing  # Negative y for top-down arrangement
        mark = func(x=x, y=y, **kwargs).rotate(rotation)
        # Get shapes from MarkWrapper and insert them
        shapes = mark.get_shapes()
        if isinstance(shapes, list):
            for shape in shapes:
                cell.shapes(layer_id).insert(shape)
        else:
            cell.shapes(layer_id).insert(shapes)
        # Determine label position and line splitting
        text_x = x - 5.0  # Move left
        text_y = y - size_um/2 - 8.0  # Move down
        # 直接插入KLayout文本标签（不换行）
        cell.shapes(text_layer_id).insert(pya.Text(desc, int(text_x / layout.dbu), int(text_y / layout.dbu)))

    print("All mark types (10um) have been generated and arranged in a grid with text labels.")
    output_gds = "TEST_MARK_UTILS.gds"
    layout.write(output_gds)
    print(f"Layout saved to {output_gds}") 