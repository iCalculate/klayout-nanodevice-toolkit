# -*- coding: utf-8 -*-
"""
分辨率测试图案生成器 - 创意优化版
包含多种微结构：十字、T型、H型、Z型、L型、三角形组合等
最大尺寸限制3μm，优化填充和边界控制，确保400个完全不同的测试区域
"""

import math
import random
import pya
import sys
import os
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LAYER_DEFINITIONS, PROCESS_CONFIG
from utils.geometry import GeometryUtils
from utils.text_utils import TextUtils

class ResolutionTestPattern:
    """分辨率测试图案生成器（创意优化版）"""
    def __init__(self, layer_name='resolution_test', **kwargs):
        self.layer_name = layer_name
        self.layer_id = LAYER_DEFINITIONS.get(layer_name, {'id': 10})['id']
        self.min_resolution = kwargs.get('min_resolution', 0.5)  # 500nm
        self.max_resolution = kwargs.get('max_resolution', 3.0)  # 3μm
        self.device_limit = kwargs.get('device_limit', 0.5)      # 500nm
        self.test_area_size = kwargs.get('test_area_size', 95.0)  # 95μm测试区域
        self.test_area_gap = kwargs.get('test_area_gap', 5.0)   # 5μm间隙
        self.margin = kwargs.get('margin', 50.0)
        self.shapes = []
        self.min_spacing = 0.8  # 800nm
        random.seed(42)

    def get_bounding_box_size(self, shape_type, size):
        """返回结构的最大外接尺寸（用于间距计算）"""
        if shape_type in ['circle', 'circular_dot', 'hexagonal_close_packed']:
            return size * 2
        elif shape_type in ['square', 'checkerboard', 'square_close_packed']:
            return size
        elif shape_type in ['cross', 'plus', 't_shape', 'h_shape', 'z_shape', 'l_shape']:
            # 复杂结构，取最大外接正方形
            return size * 2.5  # 经验系数，保证组合结构不会重叠
        else:
            return size

    def create_checkerboard_array(self, x, y, width, height, square_size=1.0, min_spacing=0.5):
        """创建棋盘格方阵阵列（优化居中）"""
        shapes = []
        spacing = square_size + min_spacing
        num_cols = int((width - min_spacing) / spacing)
        num_rows = int((height - min_spacing) / spacing)
        if num_cols < 1 or num_rows < 1:
            return shapes
        array_width = (num_cols - 1) * spacing + square_size
        array_height = (num_rows - 1) * spacing + square_size
        center_x = x + width / 2
        center_y = y + height / 2
        array_left = center_x - array_width / 2
        array_bottom = center_y - array_height / 2
        for row in range(num_rows):
            for col in range(num_cols):
                if (row + col) % 2 == 0:
                    cx = array_left + col * spacing + square_size / 2
                    cy = array_bottom + row * spacing + square_size / 2
                    shapes.append(GeometryUtils.create_rectangle(cx, cy, square_size, square_size, center=True))
        return shapes

    def create_square_close_packed_array(self, x, y, width, height, square_size=1.0, min_spacing=0.5):
        """创建四方密堆方阵阵列（优化居中）"""
        shapes = []
        spacing = square_size + min_spacing
        num_cols = int((width - min_spacing) / spacing)
        num_rows = int((height - min_spacing) / spacing)
        if num_cols < 1 or num_rows < 1:
            return shapes
        array_width = (num_cols - 1) * spacing + square_size
        array_height = (num_rows - 1) * spacing + square_size
        center_x = x + width / 2
        center_y = y + height / 2
        array_left = center_x - array_width / 2
        array_bottom = center_y - array_height / 2
        for row in range(num_rows):
            for col in range(num_cols):
                cx = array_left + col * spacing + square_size / 2
                cy = array_bottom + row * spacing + square_size / 2
                shapes.append(GeometryUtils.create_rectangle(cx, cy, square_size, square_size, center=True))
        return shapes

    # 以圆点阵列为例，所有阵列函数都用此逻辑
    def create_circular_dot_array(self, x, y, width, height, circle_size=0.5, min_spacing=0.5):
        shapes = []
        D = circle_size * 2
        spacing = D + min_spacing
        num_cols = int((width - min_spacing) / spacing)
        num_rows = int((height - min_spacing) / spacing)
        if num_cols < 1 or num_rows < 1:
            return shapes
        array_width = (num_cols - 1) * spacing + D
        array_height = (num_rows - 1) * spacing + D
        center_x = x + width / 2
        center_y = y + height / 2
        array_left = center_x - array_width / 2
        array_bottom = center_y - array_height / 2
        for row in range(num_rows):
            for col in range(num_cols):
                cx = array_left + col * spacing + circle_size
                cy = array_bottom + row * spacing + circle_size
                shapes.append(GeometryUtils.create_circle(cx, cy, circle_size))
        return shapes

    def create_hexagonal_close_packed_array(self, x, y, width, height, circle_size=0.5, min_spacing=0.5):
        """创建六方密堆点阵阵列（修正等边三角形排列，保证最小间距，整体居中）"""
        shapes = []
        D = circle_size * 2
        spacing = D + min_spacing
        row_spacing = spacing * math.sqrt(3) / 2

        # 计算最大可排布的行列数
        num_cols = int((width - min_spacing) / spacing)
        num_rows = int((height - min_spacing) / row_spacing)

        if num_cols < 1 or num_rows < 1:
            return shapes

        # 计算阵列实际宽高
        array_width = (num_cols - 1) * spacing + D
        array_height = (num_rows - 1) * row_spacing + D

        # 计算整体居中偏移
        center_x = x + width / 2
        center_y = y + height / 2
        array_left = center_x - array_width / 2
        array_bottom = center_y - array_height / 2

        for row in range(num_rows):
            for col in range(num_cols):
                cx = array_left + col * spacing + (row % 2) * spacing / 2
                cy = array_bottom + row * row_spacing
                shapes.append(GeometryUtils.create_circle(cx, cy, circle_size))
        return shapes

    # 复杂结构示例：十字阵列
    def create_cross_array(self, x, y, width, height, rect_w=1.0, rect_h=1.0, min_spacing=None):
        if min_spacing is None:
            min_spacing = self.min_spacing
        shapes = []
        bbox = max(rect_w*2, rect_h*2)
        spacing = bbox + min_spacing
        num_cols = int((width - min_spacing) / spacing)
        num_rows = int((height - min_spacing) / spacing)
        if num_cols < 1 or num_rows < 1:
            return shapes
        array_width = (num_cols - 1) * spacing + bbox
        array_height = (num_rows - 1) * spacing + bbox
        center_x = x + width / 2
        center_y = y + height / 2
        array_left = center_x - array_width / 2
        array_bottom = center_y - array_height / 2
        for row in range(num_rows):
            for col in range(num_cols):
                cx = array_left + col * spacing + bbox / 2
                cy = array_bottom + row * spacing + bbox / 2
                shapes.append(GeometryUtils.create_rectangle(cx, cy, rect_w, rect_h, center=True))
                shapes.append(GeometryUtils.create_rectangle(cx, cy, rect_h, rect_w, center=True))
        return shapes

    def create_t_shape_array(self, x, y, width, height, rect_w=1.0, rect_h=1.0, min_spacing=None):
        if min_spacing is None:
            min_spacing = self.min_spacing
        shapes = []
        bbox = max(rect_w*2, rect_h*2)
        spacing = bbox + min_spacing
        num_cols = int((width - min_spacing) / spacing)
        num_rows = int((height - min_spacing) / spacing)
        if num_cols < 1 or num_rows < 1:
            return shapes
        array_width = (num_cols - 1) * spacing + bbox
        array_height = (num_rows - 1) * spacing + bbox
        center_x = x + width / 2
        center_y = y + height / 2
        array_left = center_x - array_width / 2
        array_bottom = center_y - array_height / 2
        for row in range(num_rows):
            for col in range(num_cols):
                cx = array_left + col * spacing + bbox / 2
                cy = array_bottom + row * spacing + bbox / 2
                shapes.append(GeometryUtils.create_rectangle(cx, cy, rect_w, rect_h, center=True))
                shapes.append(GeometryUtils.create_rectangle(cx, cy+rect_h, rect_h, rect_w, center=True))
        return shapes

    def create_h_shape_array(self, x, y, width, height, rect_w=1.0, rect_h=1.0, min_spacing=None):
        if min_spacing is None:
            min_spacing = self.min_spacing
        shapes = []
        # H型参数
        vertical_bar_width = rect_h
        vertical_bar_height = rect_w * 3
        # 两根竖线中心间距，保证不交叠且有min_spacing
        bar_gap = max(vertical_bar_width + min_spacing, vertical_bar_width * 2)
        # 横线宽度不能大于两竖线中心间距减去两竖线宽度之和
        horizontal_bar_width = bar_gap
        horizontal_bar_height = rect_h
        bbox = max(bar_gap + vertical_bar_width, vertical_bar_height, horizontal_bar_width)
        spacing = bbox + min_spacing
        num_cols = int((width - min_spacing) / spacing)
        num_rows = int((height - min_spacing) / spacing)
        if num_cols < 1 or num_rows < 1:
            return shapes
        array_width = (num_cols - 1) * spacing + bbox
        array_height = (num_rows - 1) * spacing + bbox
        center_x = x + width / 2
        center_y = y + height / 2
        array_left = center_x - array_width / 2
        array_bottom = center_y - array_height / 2
        for row in range(num_rows):
            for col in range(num_cols):
                cx = array_left + col * spacing + bbox / 2
                cy = array_bottom + row * spacing + bbox / 2
                # 左竖线
                shapes.append(GeometryUtils.create_rectangle(cx - bar_gap/2, cy, vertical_bar_width, vertical_bar_height, center=True))
                # 右竖线
                shapes.append(GeometryUtils.create_rectangle(cx + bar_gap/2, cy, vertical_bar_width, vertical_bar_height, center=True))
                # 横线
                shapes.append(GeometryUtils.create_rectangle(cx, cy, horizontal_bar_width, horizontal_bar_height, center=True))
        return shapes

    def create_z_shape_array(self, x, y, width, height, rect_w=1.0, rect_h=1.0, min_spacing=None):
        if min_spacing is None:
            min_spacing = self.min_spacing
        shapes = []
        bbox = max(rect_w*2, rect_h*2)
        spacing = bbox + min_spacing
        num_cols = int((width - min_spacing) / spacing)
        num_rows = int((height - min_spacing) / spacing)
        if num_cols < 1 or num_rows < 1:
            return shapes
        array_width = (num_cols - 1) * spacing + bbox
        array_height = (num_rows - 1) * spacing + bbox
        center_x = x + width / 2
        center_y = y + height / 2
        array_left = center_x - array_width / 2
        array_bottom = center_y - array_height / 2
        for row in range(num_rows):
            for col in range(num_cols):
                cx = array_left + col * spacing + bbox / 2
                cy = array_bottom + row * spacing + bbox / 2
                shapes.append(GeometryUtils.create_rectangle(cx, cy+rect_h, rect_w*2, rect_h, center=True))
                shapes.append(GeometryUtils.create_rectangle(cx, cy, rect_h, rect_h, center=True))
                shapes.append(GeometryUtils.create_rectangle(cx, cy-rect_h, rect_w*2, rect_h, center=True))
        return shapes

    def create_l_shape_array(self, x, y, width, height, rect_w=1.0, rect_h=1.0, min_spacing=None):
        if min_spacing is None:
            min_spacing = self.min_spacing
        shapes = []
        bbox = max(rect_w*2, rect_h*2)
        spacing = bbox + min_spacing
        num_cols = int((width - min_spacing) / spacing)
        num_rows = int((height - min_spacing) / spacing)
        if num_cols < 1 or num_rows < 1:
            return shapes
        array_width = (num_cols - 1) * spacing + bbox
        array_height = (num_rows - 1) * spacing + bbox
        center_x = x + width / 2
        center_y = y + height / 2
        array_left = center_x - array_width / 2
        array_bottom = center_y - array_height / 2
        for row in range(num_rows):
            for col in range(num_cols):
                cx = array_left + col * spacing + bbox / 2
                cy = array_bottom + row * spacing + bbox / 2
                h_rect = GeometryUtils.create_rectangle(cx, cy, rect_w*2, rect_h, center=True)
                v_rect = GeometryUtils.create_rectangle(cx+rect_w, cy+rect_h, rect_h, rect_w*2, center=True)
                shapes.append(h_rect)
                shapes.append(v_rect)
        return shapes

    def create_plus_array(self, x, y, width, height, rect_w=1.0, rect_h=1.0, min_spacing=None):
        if min_spacing is None:
            min_spacing = self.min_spacing
        shapes = []
        bbox = max(rect_w*2, rect_h*2)
        spacing = bbox + min_spacing
        num_cols = int((width - min_spacing) / spacing)
        num_rows = int((height - min_spacing) / spacing)
        if num_cols < 1 or num_rows < 1:
            return shapes
        array_width = (num_cols - 1) * spacing + bbox
        array_height = (num_rows - 1) * spacing + bbox
        center_x = x + width / 2
        center_y = y + height / 2
        array_left = center_x - array_width / 2
        array_bottom = center_y - array_height / 2
        for row in range(num_rows):
            for col in range(num_cols):
                cx = array_left + col * spacing + bbox / 2
                cy = array_bottom + row * spacing + bbox / 2
                shapes.append(GeometryUtils.create_rectangle(cx, cy, rect_w*3, rect_h, center=True))
                shapes.append(GeometryUtils.create_rectangle(cx, cy, rect_h, rect_w*3, center=True))
        return shapes

    def create_triangle_array(self, x, y, width, height, triangle_size=1.0, min_spacing=0.5):
        """创建三角形阵列（优化居中）"""
        shapes = []
        spacing = triangle_size + min_spacing
        num_cols = int((width - min_spacing) / spacing)
        num_rows = int((height - min_spacing) / spacing)
        if num_cols < 1 or num_rows < 1:
            return shapes
        array_width = (num_cols - 1) * spacing + triangle_size
        array_height = (num_rows - 1) * spacing + triangle_size
        center_x = x + width / 2
        center_y = y + height / 2
        array_left = center_x - array_width / 2
        array_bottom = center_y - array_height / 2
        for row in range(num_rows):
            for col in range(num_cols):
                cx = array_left + col * spacing + spacing / 2
                cy = array_bottom + row * spacing + spacing / 2
                
                # 创建三角形
                shapes.append(GeometryUtils.create_triangle(cx, cy, triangle_size, 'up'))
        
        return shapes

    # 删除三角形组合、菱形、箭头、螺旋等相关结构函数
    # 删除create_grid_lines及其调用
    # 在generate_systematic_pattern中，去除网格线生成相关代码
    # 在generate_systematic_pattern中，所有阵列调用都传递min_spacing=MIN_SPACING
    # 例如：
    # new_shapes = self.create_cross_array(..., size, min_spacing=MIN_SPACING)
    # ...

    def create_star_array(self, x, y, width, height, star_size=1.0, min_spacing=0.5):
        """创建星形阵列（新创意结构）"""
        shapes = []
        spacing = star_size + min_spacing
        num_cols = int((width - min_spacing) / spacing)
        num_rows = int((height - min_spacing) / spacing)
        if num_cols < 1 or num_rows < 1:
            return shapes
        array_width = (num_cols - 1) * spacing + star_size
        array_height = (num_rows - 1) * spacing + star_size
        center_x = x + width / 2
        center_y = y + height / 2
        array_left = center_x - array_width / 2
        array_bottom = center_y - array_height / 2
        for row in range(num_rows):
            for col in range(num_cols):
                cx = array_left + col * spacing + spacing / 2
                cy = array_bottom + row * spacing + spacing / 2
                
                # 创建星形（五个矩形组成）
                for i in range(5):
                    angle = i * 72 * math.pi / 180  # 72度间隔
                    dx = star_size * math.cos(angle)
                    dy = star_size * math.sin(angle)
                    shapes.append(GeometryUtils.create_rectangle(cx+dx, cy+dy, star_size, star_size, center=True))
        
        return shapes

    def create_diamond_array(self, x, y, width, height, diamond_size=1.0, min_spacing=0.5):
        """创建菱形阵列（新创意结构）"""
        shapes = []
        spacing = diamond_size + min_spacing
        num_cols = int((width - min_spacing) / spacing)
        num_rows = int((height - min_spacing) / spacing)
        if num_cols < 1 or num_rows < 1:
            return shapes
        array_width = (num_cols - 1) * spacing + diamond_size
        array_height = (num_rows - 1) * spacing + diamond_size
        center_x = x + width / 2
        center_y = y + height / 2
        array_left = center_x - array_width / 2
        array_bottom = center_y - array_height / 2
        for row in range(num_rows):
            for col in range(num_cols):
                cx = array_left + col * spacing + spacing / 2
                cy = array_bottom + row * spacing + spacing / 2
                
                # 创建菱形（四个三角形）
                shapes.append(GeometryUtils.create_triangle(cx, cy-diamond_size/2, diamond_size, 'up'))
                shapes.append(GeometryUtils.create_triangle(cx, cy+diamond_size/2, diamond_size, 'down'))
                shapes.append(GeometryUtils.create_triangle(cx-diamond_size/2, cy, diamond_size, 'left'))
                shapes.append(GeometryUtils.create_triangle(cx+diamond_size/2, cy, diamond_size, 'right'))
        
        return shapes

    def create_arrow_array(self, x, y, width, height, arrow_size=1.0, min_spacing=0.5):
        """创建箭头阵列（新创意结构）"""
        shapes = []
        spacing = arrow_size + min_spacing
        num_cols = int((width - min_spacing) / spacing)
        num_rows = int((height - min_spacing) / spacing)
        if num_cols < 1 or num_rows < 1:
            return shapes
        array_width = (num_cols - 1) * spacing + arrow_size
        array_height = (num_rows - 1) * spacing + arrow_size
        center_x = x + width / 2
        center_y = y + height / 2
        array_left = center_x - array_width / 2
        array_bottom = center_y - array_height / 2
        for row in range(num_rows):
            for col in range(num_cols):
                cx = array_left + col * spacing + spacing / 2
                cy = array_bottom + row * spacing + spacing / 2
                
                # 创建箭头（矩形+三角形）
                # 箭头柄
                shapes.append(GeometryUtils.create_rectangle(cx, cy, arrow_size*2, arrow_size, center=True))
                # 箭头头（三角形）
                shapes.append(GeometryUtils.create_triangle(cx+arrow_size*1.5, cy, arrow_size, 'right'))
        
        return shapes

    def create_plus_array(self, x, y, width, height, rect_w=1.0, rect_h=1.0, min_spacing=None):
        if min_spacing is None:
            min_spacing = self.min_spacing
        shapes = []
        bbox = max(rect_w*2, rect_h*2)
        spacing = bbox + min_spacing
        num_cols = int((width - min_spacing) / spacing)
        num_rows = int((height - min_spacing) / spacing)
        if num_cols < 1 or num_rows < 1:
            return shapes
        array_width = (num_cols - 1) * spacing + bbox
        array_height = (num_rows - 1) * spacing + bbox
        center_x = x + width / 2
        center_y = y + height / 2
        array_left = center_x - array_width / 2
        array_bottom = center_y - array_height / 2
        for row in range(num_rows):
            for col in range(num_cols):
                cx = array_left + col * spacing + bbox / 2
                cy = array_bottom + row * spacing + bbox / 2
                shapes.append(GeometryUtils.create_rectangle(cx, cy, rect_w*3, rect_h, center=True))
                shapes.append(GeometryUtils.create_rectangle(cx, cy, rect_h, rect_w*3, center=True))
        return shapes

    def create_spiral_array(self, x, y, width, height, spiral_size=1.0, min_spacing=0.5):
        """创建螺旋阵列（新创意结构）"""
        shapes = []
        spacing = spiral_size + min_spacing
        num_cols = int((width - min_spacing) / spacing)
        num_rows = int((height - min_spacing) / spacing)
        if num_cols < 1 or num_rows < 1:
            return shapes
        array_width = (num_cols - 1) * spacing + spiral_size
        array_height = (num_rows - 1) * spacing + spiral_size
        center_x = x + width / 2
        center_y = y + height / 2
        array_left = center_x - array_width / 2
        array_bottom = center_y - array_height / 2
        for row in range(num_rows):
            for col in range(num_cols):
                cx = array_left + col * spacing + spacing / 2
                cy = array_bottom + row * spacing + spacing / 2
                
                # 创建螺旋（四个L型组成）
                # 四个L型围绕中心
                shapes.append(GeometryUtils.create_rectangle(cx-spiral_size, cy, spiral_size, spiral_size*2, center=True))
                shapes.append(GeometryUtils.create_rectangle(cx-spiral_size, cy-spiral_size, spiral_size*2, spiral_size, center=True))
                shapes.append(GeometryUtils.create_rectangle(cx, cy-spiral_size, spiral_size, spiral_size*2, center=True))
                shapes.append(GeometryUtils.create_rectangle(cx, cy, spiral_size*2, spiral_size, center=True))
        
        return shapes

    def create_stripe_pattern(self, x, y, width, height, orientation='horizontal', stripe_widths=[0.5], min_spacing=0.5):
        """创建条纹图案（优化边界控制）"""
        shapes = []
        
        for stripe_width in stripe_widths:
            if stripe_width * 3 > min(width, height):
                continue
                
            spacing = stripe_width + min_spacing
            
            if orientation == 'horizontal':
                num_stripes = int((height - min_spacing) / spacing)
                # 计算偏移量使条纹居中
                offset_y = (height - num_stripes * spacing) / 2
                
                for i in range(num_stripes):
                    cy = y + offset_y + i * spacing + spacing/2
                    # 确保条纹不超出边界
                    if cy + stripe_width/2 <= y + height and cy - stripe_width/2 >= y:
                        shapes.append(GeometryUtils.create_rectangle(x, cy, width, stripe_width, center=False))
                    
            elif orientation == 'vertical':
                num_stripes = int((width - min_spacing) / spacing)
                # 计算偏移量使条纹居中
                offset_x = (width - num_stripes * spacing) / 2
                
                for i in range(num_stripes):
                    cx = x + offset_x + i * spacing + spacing/2
                    # 确保条纹不超出边界
                    if cx + stripe_width/2 <= x + width and cx - stripe_width/2 >= x:
                        shapes.append(GeometryUtils.create_rectangle(cx, y, stripe_width, height, center=False))
                    
            elif orientation == 'left_diagonal':
                # 左斜条纹（从左上到右下）- 简化处理
                num_stripes = int((height - min_spacing) / spacing)
                offset_y = (height - num_stripes * spacing) / 2
                
                for i in range(num_stripes):
                    cy = y + offset_y + i * spacing + spacing/2
                    if cy + stripe_width/2 <= y + height and cy - stripe_width/2 >= y:
                        shapes.append(GeometryUtils.create_rectangle(x, cy, width, stripe_width, center=False))
                    
            elif orientation == 'right_diagonal':
                # 右斜条纹（从右上到左下）- 简化处理
                num_stripes = int((height - min_spacing) / spacing)
                offset_y = (height - num_stripes * spacing) / 2
                
                for i in range(num_stripes):
                    cy = y + offset_y + i * spacing + spacing/2
                    if cy + stripe_width/2 <= y + height and cy - stripe_width/2 >= y:
                        shapes.append(GeometryUtils.create_rectangle(x, cy, width, stripe_width, center=False))
        
        return shapes

    # 删除create_grid_lines及其调用
    # 在generate_systematic_pattern中，去除网格线生成相关代码
    # 在generate_systematic_pattern中，所有阵列调用都传递min_spacing=MIN_SPACING
    # 例如：
    # new_shapes = self.create_cross_array(..., size, min_spacing=MIN_SPACING)
    # ...

    def estimate_fill(self, area_w, area_h, structure_type, min_size, max_size, min_spacing, rect_w=None, rect_h=None):
        # 计算给定尺寸下的填充率
        size = max_size
        while size >= min_size:
            if structure_type == 'circular_dot':
                D = size * 2
                spacing = D + min_spacing
                ncol = int((area_w - min_spacing) / spacing)
                nrow = int((area_h - min_spacing) / spacing)
                single_area = 3.1416 * (size ** 2)
            elif structure_type == 'checkerboard' or structure_type == 'square_close_packed':
                spacing = size + min_spacing
                ncol = int((area_w - min_spacing) / spacing)
                nrow = int((area_h - min_spacing) / spacing)
                single_area = size * size
            elif structure_type == 'hexagonal_close_packed':
                D = size * 2
                spacing = D + min_spacing
                row_spacing = spacing * math.sqrt(3) / 2
                ncol = int((area_w - min_spacing) / spacing)
                nrow = int((area_h - min_spacing) / row_spacing)
                single_area = 3.1416 * (size ** 2)
            elif structure_type == 'cross':
                # 拼接结构，面积为两矩形面积之和
                if rect_w is None or rect_h is None:
                    rect_w = rect_h = size
                bbox = max(rect_w*2, rect_h*2)
                spacing = bbox + min_spacing
                ncol = int((area_w - min_spacing) / spacing)
                nrow = int((area_h - min_spacing) / spacing)
                single_area = rect_w * rect_h + rect_h * rect_w
            # 其它拼接结构同理...
            else:
                # 默认正方形
                spacing = size + min_spacing
                ncol = int((area_w - min_spacing) / spacing)
                nrow = int((area_h - min_spacing) / spacing)
                single_area = size * size
            if ncol < 1 or nrow < 1:
                size -= 0.1
                continue
            fill = ncol * nrow * single_area / (area_w * area_h)
            if 0.4 <= fill <= 0.6:
                return size, nrow, ncol
            size -= 0.1
        return min_size, nrow, ncol

    def get_random_rect_size(self, size_options, min_aspect=1.4):
        while True:
            w = random.choice(size_options)
            h = random.choice(size_options)
            aspect = max(w, h) / min(w, h)
            if aspect >= min_aspect:
                return w, h

    def generate_systematic_pattern(self, x, y, width, height, scale=None):
        """
        生成系统化测试图案
        scale: 指定阵列规模，如果为None则自动计算
        """
        shapes = []
        test_area_size = self.test_area_size
        test_area_gap = self.test_area_gap
        
        if scale is not None:
            # 根据指定规模调整测试区域大小
            if scale <= 5:
                # 小规模时使用更大的测试区域
                adjusted_test_area_size = min(width / scale, height / scale) * 0.8
                adjusted_test_area_gap = adjusted_test_area_size * 0.05
            else:
                adjusted_test_area_size = test_area_size
                adjusted_test_area_gap = test_area_gap
            
            effective_area_size = adjusted_test_area_size + adjusted_test_area_gap
            num_cols = scale
            num_rows = scale
        else:
            # 自动计算规模
            effective_area_size = test_area_size + test_area_gap
            num_cols = int(width / effective_area_size)
            num_rows = int(height / effective_area_size)
            adjusted_test_area_size = test_area_size
            adjusted_test_area_gap = test_area_gap
        
        total_areas = num_cols * num_rows
        print(f"📊 开始生成测试图案...")
        print(f"   测试区域布局: {num_cols} × {num_rows} = {total_areas} 个区域")
        print(f"   每个区域大小: {adjusted_test_area_size:.1f}μm × {adjusted_test_area_size:.1f}μm")
        print(f"   区域间隙: {adjusted_test_area_gap:.1f}μm")
        print(f"   总测试面积: {width}μm × {height}μm")
        print(f"   最大特征尺寸: {self.max_resolution}μm")
        print("-" * 60)
        
        # 根据规模选择测试类型
        if scale is None or scale >= 5:
            # 大规模：使用所有图案类型
            test_types = [
                'checkerboard', 'square_close_packed', 'circular_dot', 'hexagonal_close_packed',
                'cross', 't_shape', 'h_shape', 'z_shape', 'l_shape', 'plus',
                'horizontal_stripes', 'vertical_stripes', 'left_diagonal_stripes', 'right_diagonal_stripes'
            ]
        else:
            # 小规模：只使用带状方块及圆的点阵图案
            test_types = [
                'checkerboard', 'square_close_packed', 'circular_dot', 'hexagonal_close_packed',
                'horizontal_stripes', 'vertical_stripes'
            ]
        
        size_options = [round(x, 2) for x in np.arange(0.8, 3.01, 0.2)]
        type_names = {
            'checkerboard': '棋盘格方阵',
            'square_close_packed': '四方密堆方阵',
            'circular_dot': '圆形点阵',
            'hexagonal_close_packed': '六方密堆点阵',
            'cross': '十字阵列',
            't_shape': 'T型阵列',
            'h_shape': 'H型阵列',
            'z_shape': 'Z型阵列',
            'l_shape': 'L型阵列',
            'plus': '加号阵列',
            'horizontal_stripes': '横向条纹',
            'vertical_stripes': '纵向条纹',
            'left_diagonal_stripes': '左斜条纹',
            'right_diagonal_stripes': '右斜条纹'
        }
        print("🎲 分配测试类型和尺寸...")
        test_assignments = []
        for row in range(num_rows):
            for col in range(num_cols):
                index = row * num_cols + col
                test_type = test_types[index % len(test_types)]
                # 随机长宽比
                if test_type == 'cross':
                    rect_w, rect_h = self.get_random_rect_size(size_options, min_aspect=1.4)
                else:
                    rect_w = random.choice(size_options)
                    rect_h = random.choice(size_options)
                # 动态调整尺寸以满足填充率
                if test_type in ['circular_dot', 'checkerboard', 'square_close_packed', 'hexagonal_close_packed']:
                    size, _, _ = self.estimate_fill(adjusted_test_area_size, adjusted_test_area_size, test_type, min(size_options), max(size_options), self.min_spacing)
                    test_assignments.append((row, col, test_type, size, None, None))
                elif test_type in ['cross', 't_shape', 'h_shape', 'z_shape', 'l_shape', 'plus']:
                    size, _, _ = self.estimate_fill(adjusted_test_area_size, adjusted_test_area_size, test_type, min(size_options), max(size_options), self.min_spacing, rect_w, rect_h)
                    test_assignments.append((row, col, test_type, size, rect_w, rect_h))
                else:
                    size, _, _ = self.estimate_fill(adjusted_test_area_size, adjusted_test_area_size, test_type, min(size_options), max(size_options), self.min_spacing)
                    test_assignments.append((row, col, test_type, size, None, None))
        type_counts = {}
        for _, _, test_type, _, _, _ in test_assignments:
            type_counts[test_type] = type_counts.get(test_type, 0) + 1
        print("📈 测试类型分布:")
        for test_type, count in type_counts.items():
            percentage = count / total_areas * 100
            print(f"   {type_names[test_type]}: {count} 个区域 ({percentage:.1f}%)")
        print("-" * 60)
        print("🔧 开始生成图案...")
        current_area = 0
        for row, col, test_type, size, rect_w, rect_h in test_assignments:
            current_area += 1
            test_x = x + col * effective_area_size
            test_y = y + row * effective_area_size
            # 区域标号，左上角
            col_label = str(col + 1)
            row_label = chr(ord('A') + row)
            label = f"{row_label}{col_label}"
            # 标号位置：区域左上角，略微内移
            label_x = test_x
            label_y = test_y + adjusted_test_area_size + 1.5
            char_size = 2.5
            char_spacing = 4.5
            for i, char in enumerate(label):
                char_x = label_x + i * char_spacing
                char_shapes = TextUtils.create_text_freetype(char, char_x, label_y, size_um=int(char_size), font_path='C:/Windows/Fonts/OCRAEXT.TTF', spacing_um=0.5)
                shapes.extend(char_shapes)
            progress = current_area / total_areas * 100
            print(f"⏳ 进度: {current_area}/{total_areas} ({progress:.1f}%) - 区域({row},{col}): {type_names[test_type]} (尺寸:{size}μm)")
            new_shapes = []
            if test_type == 'checkerboard':
                new_shapes = self.create_checkerboard_array(test_x, test_y, adjusted_test_area_size, adjusted_test_area_size, size, min_spacing=self.min_spacing)
            elif test_type == 'square_close_packed':
                new_shapes = self.create_square_close_packed_array(test_x, test_y, adjusted_test_area_size, adjusted_test_area_size, size, min_spacing=self.min_spacing)
            elif test_type == 'circular_dot':
                new_shapes = self.create_circular_dot_array(test_x, test_y, adjusted_test_area_size, adjusted_test_area_size, size, min_spacing=self.min_spacing)
            elif test_type == 'hexagonal_close_packed':
                new_shapes = self.create_hexagonal_close_packed_array(test_x, test_y, adjusted_test_area_size, adjusted_test_area_size, size, min_spacing=self.min_spacing)
            elif test_type == 'cross':
                new_shapes = self.create_cross_array(test_x, test_y, adjusted_test_area_size, adjusted_test_area_size, rect_w=rect_w, rect_h=rect_h, min_spacing=self.min_spacing)
            elif test_type == 't_shape':
                new_shapes = self.create_t_shape_array(test_x, test_y, adjusted_test_area_size, adjusted_test_area_size, rect_w=rect_w, rect_h=rect_h, min_spacing=self.min_spacing)
            elif test_type == 'h_shape':
                new_shapes = self.create_h_shape_array(test_x, test_y, adjusted_test_area_size, adjusted_test_area_size, rect_w=rect_w, rect_h=rect_h, min_spacing=self.min_spacing)
            elif test_type == 'z_shape':
                new_shapes = self.create_z_shape_array(test_x, test_y, adjusted_test_area_size, adjusted_test_area_size, rect_w=rect_w, rect_h=rect_h, min_spacing=self.min_spacing)
            elif test_type == 'l_shape':
                new_shapes = self.create_l_shape_array(test_x, test_y, adjusted_test_area_size, adjusted_test_area_size, rect_w=rect_w, rect_h=rect_h, min_spacing=self.min_spacing)
            elif test_type == 'plus':
                new_shapes = self.create_plus_array(test_x, test_y, adjusted_test_area_size, adjusted_test_area_size, rect_w=rect_w, rect_h=rect_h, min_spacing=self.min_spacing)
            elif test_type == 'horizontal_stripes':
                new_shapes = self.create_stripe_pattern(test_x, test_y, adjusted_test_area_size, adjusted_test_area_size, 'horizontal', [size], min_spacing=self.min_spacing)
            elif test_type == 'vertical_stripes':
                new_shapes = self.create_stripe_pattern(test_x, test_y, adjusted_test_area_size, adjusted_test_area_size, 'vertical', [size], min_spacing=self.min_spacing)
            elif test_type == 'left_diagonal_stripes':
                new_shapes = self.create_stripe_pattern(test_x, test_y, adjusted_test_area_size, adjusted_test_area_size, 'left_diagonal', [size], min_spacing=self.min_spacing)
            elif test_type == 'right_diagonal_stripes':
                new_shapes = self.create_stripe_pattern(test_x, test_y, adjusted_test_area_size, adjusted_test_area_size, 'right_diagonal', [size], min_spacing=self.min_spacing)
            shapes.extend(new_shapes)
            print(f"   ✅ 生成了 {len(new_shapes)} 个图案")
        print("-" * 60)
        print(f"🎉 图案生成完成！总共生成 {len(shapes)} 个图案")
        self.shapes = shapes
        return shapes

def create_gds_file(shapes, filename, cell_name="Resolution_Test", layer_id=10):
    """创建GDS文件"""
    try:
        import pya
        layout = pya.Layout()
        layout.dbu = 0.001
        top_cell = layout.create_cell(cell_name)
        layer_info = pya.LayerInfo(layer_id, 0, "Resolution_Test")
        layer_index = layout.layer(layer_info)
        for shape in shapes:
            top_cell.shapes(layer_index).insert(shape)
        layout.write(filename)
        return True
    except Exception as e:
        print(f"生成GDS文件时出错: {e}")
        return False

if __name__ == "__main__":
    print("分辨率测试图案生成器（多规模版）")
    print("="*60)
    print("支持的测试类型：")
    print("- 棋盘格方阵阵列")
    print("- 四方密堆方阵阵列")
    print("- 圆形点阵阵列")
    print("- 六方密堆点阵（修正等边三角形排列）")
    print("- 十字阵列")
    print("- T型阵列")
    print("- H型阵列")
    print("- Z型阵列")
    print("- L型阵列")
    print("- 加号阵列")
    print("- 横向条纹")
    print("- 纵向条纹")
    print("- 左斜条纹")
    print("- 右斜条纹")
    print("="*60)
    
    # 规模选择菜单
    print("请选择要生成的阵列规模：")
    print("1. 自定义阵列大小 (1-50)")
    print("2. 自动计算 (基于可用空间)")
    
    while True:
        try:
            choice = input("\n请输入选择 (1-2): ").strip()
            if choice == "1":
                while True:
                    try:
                        scale_input = input("请输入阵列大小 (1-50): ").strip()
                        scale = int(scale_input)
                        if 1 <= scale <= 50:
                            # 根据规模调整掩模大小
                            if scale >= 20:
                                mask_size = (2000, 2000)  # 2mm × 2mm
                            elif scale >= 10:
                                mask_size = (1500, 1500)  # 1.5mm × 1.5mm
                            elif scale >= 5:
                                mask_size = (1200, 1200)  # 1.2mm × 1.2mm
                            else:
                                mask_size = (1000, 1000)  # 1mm × 1mm
                            break
                        else:
                            print("阵列大小必须在1到50之间，请重新输入")
                    except ValueError:
                        print("请输入有效的数字")
                    except KeyboardInterrupt:
                        print("\n程序已取消")
                        exit()
                break
            elif choice == "2":
                scale = None
                mask_size = (2000, 2000)  # 2mm × 2mm
                break
            else:
                print("无效选择，请输入 1-2 之间的数字")
        except KeyboardInterrupt:
            print("\n程序已取消")
            exit()
        except Exception as e:
            print(f"输入错误: {e}")
    
    # 显示图案类型信息
    if scale:
        if scale >= 5:
            pattern_type = "完整图案集"
        else:
            pattern_type = "简化图案集（仅带状方块及圆的点阵）"
        print(f"\n{'='*20} 生成 {scale}×{scale} {pattern_type} {'='*20}")
    else:
        print(f"\n{'='*20} 生成 自动计算 测试图案 {'='*20}")
    
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    margin = 50.0
    usable_width = mask_size[0] - 2*margin
    usable_height = mask_size[1] - 2*margin
    
    pattern = ResolutionTestPattern(
        min_resolution=0.5, 
        max_resolution=3.0, 
        device_limit=0.5, 
        test_area_size=95.0,   # 95μm测试区域
        test_area_gap=5.0,     # 5μm间隙
        margin=margin
    )
    
    shapes = pattern.generate_systematic_pattern(margin, margin, usable_width, usable_height, scale)
    
    # 生成文件名
    if scale:
        gds_filename = f"TEST_RESOLUTION_COMP_{scale}x{scale}.gds"
        cell_name = f"Resolution_Test_{scale}x{scale}"
    else:
        gds_filename = "TEST_RESOLUTION_COMP_AUTO.gds"
        cell_name = "Resolution_Test_Auto"
    
    gds_path = os.path.join(root_dir, gds_filename)
    
    if create_gds_file(shapes, gds_path, cell_name):
        print(f"✓ {gds_filename} 生成完成")
        print(f"  图案总数: {len(shapes)}")
        print(f"  测试面积: {mask_size[0]} x {mask_size[1]} 微米 = {mask_size[0]*mask_size[1]/1000000:.2f} 平方毫米")
        if scale:
            print(f"  阵列规模: {scale}×{scale}")
        print(f"  文件路径: {gds_path}")
    else:
        print("✗ GDS文件生成失败") 