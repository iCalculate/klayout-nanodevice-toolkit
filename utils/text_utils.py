# -*- coding: utf-8 -*-
"""
Text utilities for layout text handling
"""

UNIT_SCALE = 1.0  # 默认1μm=1dbu，可由外部设置

def set_unit_scale(scale):
    global UNIT_SCALE
    UNIT_SCALE = scale

def get_unit_scale():
    return UNIT_SCALE

import pya
from config import FONT_CONFIG
from utils.geometry import GeometryUtils

class TextUtils:
    """文本工具类"""
    
    @staticmethod
    def create_simple_text(text, x, y, font_config='default', center=True):
        """创建简单字符形状的文本（使用几何图形表示字母）"""
        config = FONT_CONFIG.get(font_config, FONT_CONFIG['default'])
        size = config['size']
        
        char_width = size * 0.6
        char_height = size
        
        if center:
            total_width = len(text) * char_width
            start_x = x - total_width / 2
        else:
            start_x = x
        
        text_shapes = []
        
        for i, char in enumerate(text):
            if char != ' ':
                char_x = start_x + i * char_width
                char_y = y
                
                # 为每个字符创建简单的几何形状
                char_shapes = TextUtils._create_char_shape(char, char_x, char_y, char_width, char_height)
                text_shapes.extend(char_shapes)
        
        return text_shapes
    
    @staticmethod
    def _create_char_shape(char, x, y, width, height):
        """为单个字符创建几何形状"""
        char = char.upper()
        shapes = []
        
        # 字符的线宽
        line_width = width * 0.1
        
        if char == 'A':
            # A: 两条斜线加一条横线
            # 左斜线
            left_line = GeometryUtils.create_line(x - width*0.3, y - height*0.4, x, y + height*0.4, line_width)
            shapes.append(left_line)
            # 右斜线
            right_line = GeometryUtils.create_line(x + width*0.3, y - height*0.4, x, y + height*0.4, line_width)
            shapes.append(right_line)
            # 横线
            cross_line = GeometryUtils.create_line(x - width*0.2, y, x + width*0.2, y, line_width)
            shapes.append(cross_line)
            
        elif char == 'B':
            # B: 竖线加两个半圆
            # 竖线
            vert_line = GeometryUtils.create_line(x - width*0.3, y - height*0.4, x - width*0.3, y + height*0.4, line_width)
            shapes.append(vert_line)
            # 上半圆
            top_arc = GeometryUtils.create_arc(x - width*0.3, y + height*0.2, width*0.3, 0, 180)
            shapes.append(top_arc)
            # 下半圆
            bottom_arc = GeometryUtils.create_arc(x - width*0.3, y - height*0.2, width*0.3, 180, 360)
            shapes.append(bottom_arc)
            
        elif char == 'C':
            # C: 半圆
            arc = GeometryUtils.create_arc(x, y, width*0.4, 45, 315)
            shapes.append(arc)
            
        elif char == 'D':
            # D: 竖线加半圆
            # 竖线
            vert_line = GeometryUtils.create_line(x - width*0.3, y - height*0.4, x - width*0.3, y + height*0.4, line_width)
            shapes.append(vert_line)
            # 半圆
            arc = GeometryUtils.create_arc(x - width*0.3, y, width*0.3, 90, 270)
            shapes.append(arc)
            
        elif char == 'E':
            # E: 竖线加三条横线
            # 竖线
            vert_line = GeometryUtils.create_line(x - width*0.3, y - height*0.4, x - width*0.3, y + height*0.4, line_width)
            shapes.append(vert_line)
            # 上横线
            top_line = GeometryUtils.create_line(x - width*0.3, y + height*0.4, x + width*0.3, y + height*0.4, line_width)
            shapes.append(top_line)
            # 中横线
            mid_line = GeometryUtils.create_line(x - width*0.3, y, x + width*0.2, y, line_width)
            shapes.append(mid_line)
            # 下横线
            bottom_line = GeometryUtils.create_line(x - width*0.3, y - height*0.4, x + width*0.3, y - height*0.4, line_width)
            shapes.append(bottom_line)
            
        elif char == 'F':
            # F: 竖线加两条横线
            # 竖线
            vert_line = GeometryUtils.create_line(x - width*0.3, y - height*0.4, x - width*0.3, y + height*0.4, line_width)
            shapes.append(vert_line)
            # 上横线
            top_line = GeometryUtils.create_line(x - width*0.3, y + height*0.4, x + width*0.3, y + height*0.4, line_width)
            shapes.append(top_line)
            # 中横线
            mid_line = GeometryUtils.create_line(x - width*0.3, y, x + width*0.2, y, line_width)
            shapes.append(mid_line)
            
        elif char == 'G':
            # G: 半圆加一条线
            # 半圆
            arc = GeometryUtils.create_arc(x, y, width*0.4, 45, 315)
            shapes.append(arc)
            # 横线
            cross_line = GeometryUtils.create_line(x, y, x + width*0.3, y, line_width)
            shapes.append(cross_line)
            
        elif char == 'H':
            # H: 两条竖线加一条横线
            # 左竖线
            left_line = GeometryUtils.create_line(x - width*0.3, y - height*0.4, x - width*0.3, y + height*0.4, line_width)
            shapes.append(left_line)
            # 右竖线
            right_line = GeometryUtils.create_line(x + width*0.3, y - height*0.4, x + width*0.3, y + height*0.4, line_width)
            shapes.append(right_line)
            # 横线
            cross_line = GeometryUtils.create_line(x - width*0.3, y, x + width*0.3, y, line_width)
            shapes.append(cross_line)
            
        elif char == 'I':
            # I: 竖线加两条横线
            # 竖线
            vert_line = GeometryUtils.create_line(x, y - height*0.4, x, y + height*0.4, line_width)
            shapes.append(vert_line)
            # 上横线
            top_line = GeometryUtils.create_line(x - width*0.2, y + height*0.4, x + width*0.2, y + height*0.4, line_width)
            shapes.append(top_line)
            # 下横线
            bottom_line = GeometryUtils.create_line(x - width*0.2, y - height*0.4, x + width*0.2, y - height*0.4, line_width)
            shapes.append(bottom_line)
            
        elif char == 'L':
            # L: 竖线加横线
            # 竖线
            vert_line = GeometryUtils.create_line(x - width*0.3, y - height*0.4, x - width*0.3, y + height*0.4, line_width)
            shapes.append(vert_line)
            # 横线
            bottom_line = GeometryUtils.create_line(x - width*0.3, y - height*0.4, x + width*0.3, y - height*0.4, line_width)
            shapes.append(bottom_line)
            
        elif char == 'M':
            # M: 两条竖线加两条斜线
            # 左竖线
            left_line = GeometryUtils.create_line(x - width*0.4, y - height*0.4, x - width*0.4, y + height*0.4, line_width)
            shapes.append(left_line)
            # 右竖线
            right_line = GeometryUtils.create_line(x + width*0.4, y - height*0.4, x + width*0.4, y + height*0.4, line_width)
            shapes.append(right_line)
            # 左斜线
            left_diag = GeometryUtils.create_line(x - width*0.4, y + height*0.4, x, y - height*0.2, line_width)
            shapes.append(left_diag)
            # 右斜线
            right_diag = GeometryUtils.create_line(x + width*0.4, y + height*0.4, x, y - height*0.2, line_width)
            shapes.append(right_diag)
            
        elif char == 'N':
            # N: 两条竖线加一条斜线
            # 左竖线
            left_line = GeometryUtils.create_line(x - width*0.3, y - height*0.4, x - width*0.3, y + height*0.4, line_width)
            shapes.append(left_line)
            # 右竖线
            right_line = GeometryUtils.create_line(x + width*0.3, y - height*0.4, x + width*0.3, y + height*0.4, line_width)
            shapes.append(right_line)
            # 斜线
            diag_line = GeometryUtils.create_line(x - width*0.3, y + height*0.4, x + width*0.3, y - height*0.4, line_width)
            shapes.append(diag_line)
            
        elif char == 'O':
            # O: 椭圆
            ellipse = GeometryUtils.create_ellipse(x, y, width*0.4, height*0.4)
            shapes.append(ellipse)
            
        elif char == 'P':
            # P: 竖线加半圆
            # 竖线
            vert_line = GeometryUtils.create_line(x - width*0.3, y - height*0.4, x - width*0.3, y + height*0.4, line_width)
            shapes.append(vert_line)
            # 半圆
            arc = GeometryUtils.create_arc(x - width*0.3, y + height*0.2, width*0.3, 90, 270)
            shapes.append(arc)
            
        elif char == 'Q':
            # Q: 椭圆加一条线
            # 椭圆
            ellipse = GeometryUtils.create_ellipse(x, y, width*0.4, height*0.4)
            shapes.append(ellipse)
            # 斜线
            diag_line = GeometryUtils.create_line(x + width*0.2, y - height*0.2, x + width*0.4, y - height*0.4, line_width)
            shapes.append(diag_line)
            
        elif char == 'R':
            # R: 竖线加半圆加斜线
            # 竖线
            vert_line = GeometryUtils.create_line(x - width*0.3, y - height*0.4, x - width*0.3, y + height*0.4, line_width)
            shapes.append(vert_line)
            # 半圆
            arc = GeometryUtils.create_arc(x - width*0.3, y + height*0.2, width*0.3, 90, 270)
            shapes.append(arc)
            # 斜线
            diag_line = GeometryUtils.create_line(x - width*0.3, y, x + width*0.3, y - height*0.4, line_width)
            shapes.append(diag_line)
            
        elif char == 'S':
            # S: 两个半圆
            # 上半圆
            top_arc = GeometryUtils.create_arc(x, y + height*0.2, width*0.3, 45, 225)
            shapes.append(top_arc)
            # 下半圆
            bottom_arc = GeometryUtils.create_arc(x, y - height*0.2, width*0.3, 225, 45)
            shapes.append(bottom_arc)
            
        elif char == 'T':
            # T: 横线加竖线
            # 横线
            top_line = GeometryUtils.create_line(x - width*0.3, y + height*0.4, x + width*0.3, y + height*0.4, line_width)
            shapes.append(top_line)
            # 竖线
            vert_line = GeometryUtils.create_line(x, y - height*0.4, x, y + height*0.4, line_width)
            shapes.append(vert_line)
            
        elif char == 'U':
            # U: 两条竖线加半圆
            # 左竖线
            left_line = GeometryUtils.create_line(x - width*0.3, y - height*0.4, x - width*0.3, y + height*0.2, line_width)
            shapes.append(left_line)
            # 右竖线
            right_line = GeometryUtils.create_line(x + width*0.3, y - height*0.4, x + width*0.3, y + height*0.2, line_width)
            shapes.append(right_line)
            # 半圆
            arc = GeometryUtils.create_arc(x, y + height*0.2, width*0.3, 0, 180)
            shapes.append(arc)
            
        elif char == 'V':
            # V: 两条斜线
            # 左斜线
            left_diag = GeometryUtils.create_line(x - width*0.3, y + height*0.4, x, y - height*0.4, line_width)
            shapes.append(left_diag)
            # 右斜线
            right_diag = GeometryUtils.create_line(x + width*0.3, y + height*0.4, x, y - height*0.4, line_width)
            shapes.append(right_diag)
            
        elif char == 'W':
            # W: 四条斜线
            # 左斜线
            left_diag = GeometryUtils.create_line(x - width*0.4, y + height*0.4, x - width*0.2, y - height*0.4, line_width)
            shapes.append(left_diag)
            # 中左斜线
            mid_left_diag = GeometryUtils.create_line(x - width*0.2, y - height*0.4, x, y + height*0.2, line_width)
            shapes.append(mid_left_diag)
            # 中右斜线
            mid_right_diag = GeometryUtils.create_line(x, y + height*0.2, x + width*0.2, y - height*0.4, line_width)
            shapes.append(mid_right_diag)
            # 右斜线
            right_diag = GeometryUtils.create_line(x + width*0.2, y - height*0.4, x + width*0.4, y + height*0.4, line_width)
            shapes.append(right_diag)
            
        elif char == 'X':
            # X: 两条交叉斜线
            # 左斜线
            left_diag = GeometryUtils.create_line(x - width*0.3, y - height*0.4, x + width*0.3, y + height*0.4, line_width)
            shapes.append(left_diag)
            # 右斜线
            right_diag = GeometryUtils.create_line(x - width*0.3, y + height*0.4, x + width*0.3, y - height*0.4, line_width)
            shapes.append(right_diag)
            
        elif char == 'Y':
            # Y: 两条斜线加一条竖线
            # 左斜线
            left_diag = GeometryUtils.create_line(x - width*0.2, y + height*0.4, x, y, line_width)
            shapes.append(left_diag)
            # 右斜线
            right_diag = GeometryUtils.create_line(x + width*0.2, y + height*0.4, x, y, line_width)
            shapes.append(right_diag)
            # 竖线
            vert_line = GeometryUtils.create_line(x, y, x, y - height*0.4, line_width)
            shapes.append(vert_line)
            
        elif char == 'Z':
            # Z: 两条横线加一条斜线
            # 上横线
            top_line = GeometryUtils.create_line(x - width*0.3, y + height*0.4, x + width*0.3, y + height*0.4, line_width)
            shapes.append(top_line)
            # 下横线
            bottom_line = GeometryUtils.create_line(x - width*0.3, y - height*0.4, x + width*0.3, y - height*0.4, line_width)
            shapes.append(bottom_line)
            # 斜线
            diag_line = GeometryUtils.create_line(x - width*0.3, y + height*0.4, x + width*0.3, y - height*0.4, line_width)
            shapes.append(diag_line)
            
        else:
            # 对于其他字符，创建简单的矩形
            char_box = GeometryUtils.create_rectangle(x, y, width * 0.8, height, center=True)
            shapes.append(char_box)
        
        return shapes

    @staticmethod
    def create_text(text, x, y, font_config='default', center=True):
        """创建文本标签"""
        config = FONT_CONFIG.get(font_config, FONT_CONFIG['default'])
        size = config['size']
        
        # 为每个字符创建简单的矩形作为标签
        char_width = size * 0.6
        char_height = size
        
        if center:
            # 计算文本总宽度
            total_width = len(text) * char_width
            start_x = x - total_width / 2
        else:
            start_x = x
        
        text_shapes = []
        
        for i, char in enumerate(text):
            if char != ' ':
                char_x = start_x + i * char_width
                char_box = GeometryUtils.create_rectangle(
                    char_x + char_width * 0.4, y, 
                    char_width * 0.8, char_height, 
                    center=True
                )
                text_shapes.append(char_box)
        
        return text_shapes
    
    @staticmethod
    def create_bold_text(text, x, y, font_config='default', center=True):
        """创建粗体文本"""
        config = FONT_CONFIG.get(font_config, FONT_CONFIG['default'])
        size = config['size']
        
        # 粗体文本使用更宽的字符
        char_width = size * 0.7
        char_height = size
        
        if center:
            total_width = len(text) * char_width
            start_x = x - total_width / 2
        else:
            start_x = x
        
        text_shapes = []
        
        for i, char in enumerate(text):
            if char != ' ':
                char_x = start_x + i * char_width
                # 创建多个重叠的矩形来模拟粗体效果
                for offset in [0, 0.2, 0.4]:
                    char_box = GeometryUtils.create_rectangle(
                        char_x + char_width * 0.4 + offset, y, 
                        char_width * 0.8, char_height, 
                        center=True
                    )
                    text_shapes.append(char_box)
        
        return text_shapes
    
    @staticmethod
    def create_outlined_text(text, x, y, font_config='default', outline_width=0.5, center=True):
        """创建轮廓文本"""
        config = FONT_CONFIG.get(font_config, FONT_CONFIG['default'])
        size = config['size']
        
        char_width = size * 0.6
        char_height = size
        
        if center:
            total_width = len(text) * char_width
            start_x = x - total_width / 2
        else:
            start_x = x
        
        text_shapes = []
        
        for i, char in enumerate(text):
            if char != ' ':
                char_x = start_x + i * char_width
                
                # 创建轮廓（外框）
                outline_box = GeometryUtils.create_rectangle(
                    char_x + char_width * 0.4, y, 
                    char_width * 0.8 + outline_width * 2, char_height + outline_width * 2, 
                    center=True
                )
                text_shapes.append(outline_box)
                
                # 创建内部填充
                fill_box = GeometryUtils.create_rectangle(
                    char_x + char_width * 0.4, y, 
                    char_width * 0.8, char_height, 
                    center=True
                )
                text_shapes.append(fill_box)
        
        return text_shapes
    
    @staticmethod
    def create_rotated_text(text, x, y, angle, font_config='default', center=True):
        """创建旋转文本"""
        config = FONT_CONFIG.get(font_config, FONT_CONFIG['default'])
        size = config['size']
        
        char_width = size * 0.6
        char_height = size
        
        if center:
            total_width = len(text) * char_width
            start_x = x - total_width / 2
        else:
            start_x = x
        
        text_shapes = []
        
        for i, char in enumerate(text):
            if char != ' ':
                char_x = start_x + i * char_width
                char_box = GeometryUtils.create_rectangle(
                    char_x + char_width * 0.4, y, 
                    char_width * 0.8, char_height, 
                    center=True
                )
                
                # 旋转字符
                import math
                cos_a = math.cos(angle)
                sin_a = math.sin(angle)
                
                # 创建变换矩阵
                trans = pya.Trans(cos_a, sin_a, -sin_a, cos_a, x, y)
                rotated_box = char_box.transformed(trans)
                text_shapes.append(rotated_box)
        
        return text_shapes
    
    @staticmethod
    def create_multiline_text(lines, x, y, line_spacing=1.5, font_config='default', center=True):
        """创建多行文本"""
        config = FONT_CONFIG.get(font_config, FONT_CONFIG['default'])
        size = config['size']
        
        all_shapes = []
        line_height = size * line_spacing
        
        for i, line in enumerate(lines):
            line_y = y - i * line_height
            line_shapes = TextUtils.create_text(line, x, line_y, font_config, center)
            all_shapes.extend(line_shapes)
        
        return all_shapes
    
    @staticmethod
    def create_text_with_background(text, x, y, background_padding=2.0, font_config='default', center=True):
        """创建带背景的文本"""
        config = FONT_CONFIG.get(font_config, FONT_CONFIG['default'])
        size = config['size']
        
        # 创建文本
        text_shapes = TextUtils.create_text(text, x, y, font_config, center)
        
        # 计算背景尺寸
        char_width = size * 0.6
        total_width = len(text) * char_width
        total_height = size
        
        if center:
            bg_x, bg_y = x, y
        else:
            bg_x = x + total_width / 2
            bg_y = y + total_height / 2
        
        # 创建背景
        background = GeometryUtils.create_rectangle(
            bg_x, bg_y,
            total_width + background_padding * 2,
            total_height + background_padding * 2,
            center=True
        )
        
        return [background] + text_shapes
    
    @staticmethod
    def create_numbered_text(text, x, y, number, font_config='default', center=True):
        """创建带编号的文本"""
        numbered_text = f"{number}. {text}"
        return TextUtils.create_text(numbered_text, x, y, font_config, center)
    
    @staticmethod
    def create_parameter_text(param_name, param_value, x, y, unit="", font_config='default', center=True):
        """创建参数文本"""
        if unit:
            text = f"{param_name}: {param_value}{unit}"
        else:
            text = f"{param_name}: {param_value}"
        return TextUtils.create_text(text, x, y, font_config, center) 

    @staticmethod
    def create_text_polygon(text, x, y, font_config='default', center=True, dbu=0.001):
        """使用KLayout TextGenerator生成多边形文本（兼容不同版本，支持dbu）"""
        import pya
        from config import FONT_CONFIG
        config = FONT_CONFIG.get(font_config, FONT_CONFIG['default'])
        size = config['size']
        try:
            generator = pya.TextGenerator.default_generator()
            height = float(size) / float(dbu)
            x_db = float(x) / float(dbu)
            y_db = float(y) / float(dbu)
            print(f"[DEBUG] TextGenerator.text: text='{text}', x={x_db}, y={y_db}, height={height}, dbu={dbu}")
            polys = generator.text(text, x_db, y_db, height)
            return list(polys)
        except Exception as e:
            print("[WARN] KLayout TextGenerator not available or failed: ", e)
            return [] 

    @staticmethod
    def create_text_freetype(text, x, y, size_um=10, font_path='C:/Windows/Fonts/arial.ttf', spacing_um=2.0):
        """
        使用 freetype-py 将字符串转为多边形点集（适用于KLayout Polygon）。
        - text: 字符串
        - x, y: 左下角起点（um）
        - size_um: 字高（um）
        - font_path: 字体文件路径
        - spacing_um: 字符间距（um）
        返回: [ [ (x1, y1), (x2, y2), ... ], ... ]  # 每个字符的多边形点集
        """
        import freetype
        import numpy as np
        polys_all = []
        cursor_x = x
        for char in text:
            face = freetype.Face(font_path)
            face.set_char_size(int(size_um * 64))
            face.load_char(char)
            outline = face.glyph.outline
            points = np.array(outline.points, dtype=float)
            # 轮廓分段
            start, polys = 0, []
            for c in outline.contours:
                end = c + 1
                poly = points[start:end]
                # 坐标归一化（freetype坐标是1/64像素，y轴向上）
                poly = poly / 64.0
                # y轴翻转（KLayout y向下，freetype y向上）
                poly[:, 1] = -poly[:, 1]
                # 平移到当前字符位置
                poly[:, 0] += cursor_x
                poly[:, 1] += y
                polys.append(poly.tolist())
                start = end
            polys_all.extend(polys)
            # 字符宽度推进
            advance = face.glyph.advance.x / 64.0
            cursor_x += advance + spacing_um
        return polys_all 