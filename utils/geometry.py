# -*- coding: utf-8 -*-
"""
几何工具模块 - 提供基础几何形状绘制功能
"""

import math
from config import PROCESS_CONFIG, DEFAULT_UNIT_SCALE
import klayout.db as db
Box = db.Box
Point = db.Point
Polygon = db.Polygon
Path = db.Path

class GeometryUtils:
    """几何工具类"""
    UNIT_SCALE = DEFAULT_UNIT_SCALE  # 全局单位缩放，默认为DEFAULT_UNIT_SCALE
    # Add Point and Polygon as class attributes for external use
    try:
        import pya
        Point = pya.Point
        Polygon = pya.Polygon
    except Exception:
        import klayout.db as db
        Point = db.Point
        Polygon = db.Polygon
    
    @staticmethod
    def create_rectangle(x, y, width, height, center=True):
        s = GeometryUtils.UNIT_SCALE
        """创建矩形"""
        if center:
            return Box(x * s - width * s / 2, y * s - height * s / 2, x * s + width * s / 2, y * s + height * s / 2)
        else:
            return Box(x * s, y * s, (x + width) * s, (y + height) * s)
    
    @staticmethod
    def create_line(x1, y1, x2, y2, width):
        """创建线条（使用细矩形）"""
        s = GeometryUtils.UNIT_SCALE
        # 计算线条的长度和角度
        dx = (x2 - x1) * s
        dy = (y2 - y1) * s
        length = math.sqrt(dx*dx + dy*dy)
        
        if length == 0:
            return Box(x1 * s, y1 * s, x1 * s, y1 * s)
        
        # 计算线条的中心点
        center_x = (x1 + x2) * s / 2
        center_y = (y1 + y2) * s / 2
        
        # 计算角度
        angle = math.atan2(dy, dx)
        
        # 创建矩形
        half_length = length / 2
        half_width = width * s / 2
        
        # 创建矩形的四个角点
        points = [
            Point(-half_length, -half_width),
            Point(half_length, -half_width),
            Point(half_length, half_width),
            Point(-half_length, half_width)
        ]
        
        # 旋转矩形
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        rotated_points = []
        for point in points:
            px = point.x * cos_a - point.y * sin_a + center_x
            py = point.x * sin_a + point.y * cos_a + center_y
            rotated_points.append(Point(px, py))
        
        return Polygon(rotated_points)
    
    @staticmethod
    def create_rounded_rectangle(x, y, width, height, radius, center=True):
        s = GeometryUtils.UNIT_SCALE
        """创建圆角矩形"""
        if center:
            x1, y1 = x * s - width * s / 2, y * s - height * s / 2
            x2, y2 = x * s + width * s / 2, y * s + height * s / 2
        else:
            x1, y1 = x * s, y * s
            x2, y2 = (x + width) * s, (y + height) * s
        
        # 限制圆角半径
        radius = min(radius * s, min(width * s, height * s) / 2)
        
        # 创建圆角矩形的路径
        path = Path()
        
        # 添加圆角
        path.append(Point(x1 + radius, y1))
        path.append(Point(x2 - radius, y1))
        path.append(Point(x2, y1 + radius))
        path.append(Point(x2, y2 - radius))
        path.append(Point(x2 - radius, y2))
        path.append(Point(x1 + radius, y2))
        path.append(Point(x1, y2 - radius))
        path.append(Point(x1, y1 + radius))
        path.append(Point(x1 + radius, y1))
        
        return path.polygon()
    
    @staticmethod
    def create_octagon(x, y, width, height, center=True):
        s = GeometryUtils.UNIT_SCALE
        """创建八边形"""
        if center:
            x1, y1 = x * s - width * s / 2, y * s - height * s / 2
            x2, y2 = x * s + width * s / 2, y * s + height * s / 2
        else:
            x1, y1 = x * s, y * s
            x2, y2 = (x + width) * s, (y + height) * s
        
        # 计算八边形的顶点
        points = []
        w, h = x2 - x1, y2 - y1
        offset = min(w, h) * 0.2
        
        points.extend([
            Point(x1 + offset, y1),
            Point(x2 - offset, y1),
            Point(x2, y1 + offset),
            Point(x2, y2 - offset),
            Point(x2 - offset, y2),
            Point(x1 + offset, y2),
            Point(x1, y2 - offset),
            Point(x1, y1 + offset)
        ])
        
        return Polygon(points)
    
    @staticmethod
    def create_ellipse(x, y, width, height, center=True):
        s = GeometryUtils.UNIT_SCALE
        """创建椭圆（近似为多边形）"""
        if center:
            cx, cy = x * s, y * s
        else:
            cx, cy = (x + width) * s / 2, (y + height) * s / 2
        
        # 创建椭圆的多边形近似
        points = []
        num_points = 32
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            px = cx + width * s / 2 * math.cos(angle)
            py = cy + height * s / 2 * math.sin(angle)
            points.append(Point(px, py))
        
        return Polygon(points)
    
    @staticmethod
    def create_cross(x, y, size, width):
        s = GeometryUtils.UNIT_SCALE
        """创建十字标记"""
        half_size = size * s / 2
        half_width = width * s / 2
        
        # 水平线
        h_line = Box(x * s - half_size, y * s - half_width, x * s + half_size, y * s + half_width)
        # 垂直线
        v_line = Box(x * s - half_width, y * s - half_size, x * s + half_width, y * s + half_size)
        
        return [h_line, v_line]
    
    @staticmethod
    def create_L_mark(x, y, size, width):
        s = GeometryUtils.UNIT_SCALE
        """创建L形标记"""
        half_size = size * s / 2
        half_width = width * s / 2
        
        # 水平部分
        h_part = Box(x * s - half_size, y * s - half_width, x * s + half_size, y * s + half_width)
        # 垂直部分
        v_part = Box(x * s - half_width, y * s - half_size, x * s + half_width, y * s + half_size)
        
        return h_part + v_part
    
    @staticmethod
    def create_T_mark(x, y, size, width):
        s = GeometryUtils.UNIT_SCALE
        """创建T形标记"""
        half_size = size * s / 2
        half_width = width * s / 2
        
        # 水平部分
        h_part = Box(x * s - half_size, y * s - half_width, x * s + half_size, y * s + half_width)
        # 垂直部分
        v_part = Box(x * s - half_width, y * s - half_size, x * s + half_width, y * s + half_size)
        
        return h_part + v_part
    
    @staticmethod
    def create_diamond(x, y, size):
        s = GeometryUtils.UNIT_SCALE
        """创建菱形标记"""
        half_size = size * s / 2
        points = [
            Point(x * s, y * s - half_size),
            Point(x * s + half_size, y * s),
            Point(x * s, y * s + half_size),
            Point(x * s - half_size, y * s)
        ]
        return Polygon(points)
    
    @staticmethod
    def create_triangle(x, y, size, direction='up'):
        s = GeometryUtils.UNIT_SCALE
        """创建三角形标记"""
        half_size = size * s / 2
        if direction == 'up':
            points = [
                Point(x * s, y * s - half_size),
                Point(x * s - half_size, y * s + half_size),
                Point(x * s + half_size, y * s + half_size)
            ]
        elif direction == 'down':
            points = [
                Point(x * s, y * s + half_size),
                Point(x * s - half_size, y * s - half_size),
                Point(x * s + half_size, y * s - half_size)
            ]
        elif direction == 'left':
            points = [
                Point(x * s - half_size, y * s),
                Point(x * s + half_size, y * s - half_size),
                Point(x * s + half_size, y * s + half_size)
            ]
        else:  # right
            points = [
                Point(x * s + half_size, y * s),
                Point(x * s - half_size, y * s - half_size),
                Point(x * s - half_size, y * s + half_size)
            ]
        
        return Polygon(points)
    
    @staticmethod
    def create_circle(x, y, radius, num_points=32):
        s = GeometryUtils.UNIT_SCALE
        """Create a circle (polygon approximation)"""
        points = []
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            px = x * s + radius * s * math.cos(angle)
            py = y * s + radius * s * math.sin(angle)
            points.append(Point(px, py))
        return Polygon(points)
    
    @staticmethod
    def create_arc(x, y, radius, start_angle, end_angle, num_points=16):
        s = GeometryUtils.UNIT_SCALE
        """创建圆弧（近似为多边形）"""
        cx, cy = x * s, y * s
        points = []
        for i in range(int(num_points)):
            angle = math.radians(start_angle + (end_angle - start_angle) * i / (num_points - 1))
            px = cx + radius * s * math.cos(angle)
            py = cy + radius * s * math.sin(angle)
            points.append(Point(px, py))
        return Polygon(points)
    
    @staticmethod
    def create_curved_wire(start_x, start_y, end_x, end_y, width, curvature=0.3):
        s = GeometryUtils.UNIT_SCALE
        """创建曲线引线"""
        # 计算控制点
        mid_x = (start_x * s + end_x * s) / 2
        mid_y = (start_y * s + end_y * s) / 2
        
        # 添加曲率
        dx = end_x * s - start_x * s
        dy = end_y * s - start_y * s
        length = math.sqrt(dx*dx + dy*dy)
        
        if length > 0:
            # 垂直偏移
            perp_x = -dy / length
            perp_y = dx / length
            offset = length * curvature
            
            control_x = mid_x + perp_x * offset
            control_y = mid_y + perp_y * offset
        else:
            control_x, control_y = mid_x, mid_y
        
        # 创建贝塞尔曲线路径
        path = Path()
        path.append(Point(start_x * s, start_y * s))
        path.append(Point(control_x, control_y))
        path.append(Point(end_x * s, end_y * s))
        
        return path.polygon(width * s)
    
    @staticmethod
    def create_stepped_wire(start_x, start_y, end_x, end_y, width, step_size=10):
        s = GeometryUtils.UNIT_SCALE
        """创建阶梯引线"""
        points = [Point(start_x * s, start_y * s)]
        
        # 计算步数
        dx = end_x * s - start_x * s
        dy = end_y * s - start_y * s
        steps = max(1, int(max(abs(dx), abs(dy)) / step_size))
        
        for i in range(1, steps):
            t = i / steps
            x = start_x * s + dx * t
            y = start_y * s + dy * t
            points.append(Point(x, y))
        
        points.append(Point(end_x * s, end_y * s))
        
        path = Path(points)
        return path.polygon(width * s) 

    @staticmethod
    def create_semiconductor_cross(x, y, size, width, head_size=0, hole_radius=0):
        s = GeometryUtils.UNIT_SCALE
        """标准半导体十字mark，可选端头和中心孔"""
        import math
        half = size * s / 2
        half_w = width * s / 2
        h_line = Box(x * s - half, y * s - half_w, x * s + half, y * s + half_w)
        v_line = Box(x * s - half_w, y * s - half, x * s + half_w, y * s + half)
        shapes = [h_line, v_line]
        # 加宽端头
        if head_size > 0:
            shapes.append(Box(x * s - half, y * s - head_size * s / 2, x * s - half + head_size * s, y * s + head_size * s / 2))
            shapes.append(Box(x * s + half - head_size * s, y * s - head_size * s / 2, x * s + half, y * s + head_size * s / 2))
            shapes.append(Box(x * s - head_size * s / 2, y * s - half, x * s + head_size * s / 2, y * s - half + head_size * s))
            shapes.append(Box(x * s - head_size * s / 2, y * s + half - head_size * s, x * s + head_size * s / 2, y * s + half))
        # 中心孔
        if hole_radius > 0:
            points = []
            num_points = 32
            for i in range(num_points):
                angle = 2 * math.pi * i / num_points
                px = x * s + hole_radius * s * math.cos(angle)
                py = y * s + hole_radius * s * math.sin(angle)
                points.append(Point(px, py))
            # 用负区域减去中心孔
            from pya import Region
            region = Region(h_line) + Region(v_line)
            for s in shapes[2:]:
                region = region + Region(s)
            region = region - Region(Polygon(points))
            return region
        if len(shapes) == 1:
            return shapes[0]
        return shapes

    @staticmethod
    def create_square_with_missing_quadrants(x, y, size, missing=(2,4)):
        s = GeometryUtils.UNIT_SCALE
        """方形缺角mark，缺二、四象限"""
        from pya import Region
        half = size * s / 2
        full = Box(x * s - half, y * s - half, x * s + half, y * s + half)
        region = Region(full)
        quarter = size * s / 2
        if 2 in missing:
            region = region - Region(Box(x * s - half, y * s, x * s, y * s + half))  # 二象限
        if 4 in missing:
            region = region - Region(Box(x * s, y * s - half, x * s + half, y * s))  # 四象限
        return region 

    @staticmethod
    def create_cross_positive(x, y, size, ratio=0.1):
        s = GeometryUtils.UNIT_SCALE
        """Positive cross mark: two center-aligned rectangles, adjustable line width by ratio"""
        width = size * s * ratio
        half = size * s / 2
        half_w = width / 2
        # Horizontal line
        h_line = Box(x * s - half, y * s - half_w, x * s + half, y * s + half_w)
        # Vertical line
        v_line = Box(x * s - half_w, y * s - half, x * s + half_w, y * s + half)
        return [h_line, v_line]

    @staticmethod
    def create_cross_negative(x, y, size, ratio=0.1, insert_ratio=0.8, box_margin=5):
        s = GeometryUtils.UNIT_SCALE
        """Negative cross mark: box with cross slot, adjustable line width and cross length by ratio and insert_ratio"""
        from pya import Region
        width = size * s * ratio
        cross_len = size * s * insert_ratio
        half_box = size * s / 2 + box_margin * s
        # Outer box
        box = Box(x * s - half_box, y * s - half_box, x * s + half_box, y * s + half_box)
        # Cross slot (centered)
        half_cross = cross_len / 2
        half_w = width / 2
        h_slot = Box(x * s - half_cross, y * s - half_w, x * s + half_cross, y * s + half_w)
        v_slot = Box(x * s - half_w, y * s - half_cross, x * s + half_w, y * s + half_cross)
        region = Region(box) - Region(h_slot) - Region(v_slot)
        return region

    @staticmethod
    def create_L_shape(x, y, size, ratio=0.1, arm_ratio=0.5):
        s = GeometryUtils.UNIT_SCALE
        """
        L-shape: (x, y) is the right-bottom corner, both arms are size/2 long.
        The right end of the horizontal arm and the right end of the vertical arm coincide at (x, y).
        The bottom of the horizontal arm and the bottom of the vertical arm coincide at (x, y).
        Args:
            x, y: right-bottom corner (intersection)
            size: mark size (full length)
            ratio: line width / size
            arm_ratio: arm length / size (default 0.5 for half size)
        Returns:
            [h_arm, v_arm]
        """
        width = size * s * ratio
        arm_len = size * s * arm_ratio
        # Horizontal arm: from (x-arm_len, y-width) to (x, y)
        h_arm = Box(x * s - arm_len, y * s - width, x * s, y * s)
        # Vertical arm: from (x-width, y-arm_len) to (x, y)
        v_arm = Box(x * s - width, y * s - arm_len, x * s, y * s)
        return [h_arm, v_arm]

    @staticmethod
    def create_T_shape(x, y, size, ratio=0.1, arm_ratio=0.5):
        s = GeometryUtils.UNIT_SCALE
        """
        Standard T-shape: (x, y) is the center of the horizontal arm.
        Horizontal arm is size long, vertical arm is size*arm_ratio long, both arms' top edges at y+width/2.
        Vertical arm's top edge与横线顶边齐平，竖线向下。
        """
        width = size * s * ratio
        h_len = size * s
        v_len = size * s * arm_ratio
        # Horizontal arm: centered at (x, y), moved down by half width
        h_arm = Box(x * s - h_len / 2, y * s - width / 2 - width / 2, x * s + h_len / 2, y * s + width / 2 - width / 2)
        # Vertical arm: from (x-width/2, y+width/2) downward, moved down by half width
        v_arm = Box(x * s - width / 2, y * s + width / 2 - width / 2, x * s + width / 2, y * s + width / 2 - width / 2 - v_len)
        return [v_arm, h_arm]

    @staticmethod
    def create_square_with_missing_quadrants_with_border(x, y, size, border_ratio=0.1, missing=(2,4)):
        s = GeometryUtils.UNIT_SCALE
        """Missing quadrant mark with adjustable border width (border_ratio)"""
        from pya import Region
        border = size * s * border_ratio
        half = size * s / 2
        # Outer and inner box for border
        outer = Box(x * s - half, y * s - half, x * s + half, y * s + half)
        inner = Box(x * s - half + border, y * s - half + border, x * s + half - border, y * s + half - border)
        frame = Region(outer) - Region(inner)
        # Remove missing quadrants
        if 2 in missing:
            frame = frame - Region(Box(x * s - half, y * s, x * s, y * s + half))
        if 4 in missing:
            frame = frame - Region(Box(x * s, y * s - half, x * s + half, y * s))
        return frame 

    @staticmethod
    def create_regular_polygon(x, y, radius, n_sides=6):
        s = GeometryUtils.UNIT_SCALE
        """Create a regular n-gon centered at (x, y) with given radius"""
        import math
        points = []
        for i in range(n_sides):
            angle = 2 * math.pi * i / n_sides
            px = x * s + radius * s * math.cos(angle)
            py = y * s + radius * s * math.sin(angle)
            points.append(Point(px, py))
        return Polygon(points)

    @staticmethod
    def create_chamfered_octagon(x, y, size, chamfer_ratio=0.25):
        s = GeometryUtils.UNIT_SCALE
        """Create a regular octagon by chamfering a square's corners. chamfer_ratio: 0~1, fraction of half-side to cut."""
        # size: full width of square
        half = size * s / 2.0
        c = half * chamfer_ratio
        # 8 points, starting from top, clockwise, all float
        points = [
            Point(float(x * s - half + c), float(y * s + half)),
            Point(float(x * s + half - c), float(y * s + half)),
            Point(float(x * s + half), float(y * s + half - c)),
            Point(float(x * s + half), float(y * s - half + c)),
            Point(float(x * s + half - c), float(y * s - half)),
            Point(float(x * s - half + c), float(y * s - half)),
            Point(float(x * s - half), float(y * s - half + c)),
            Point(float(x * s - half), float(y * s + half - c))
        ]
        return Polygon(points) 

    @staticmethod
    def create_cross_with_triangle(x, y, size=10.0, ratio=0.1, triangle_leg_ratio=0.3):
        s = GeometryUtils.UNIT_SCALE
        """
        Create a cross mark with a right isosceles triangle at the right-top corner of the cross.
        The right angle of the triangle is always at the cross's right-top (x+half, y+half),
        precisely aligned with the right end of the horizontal line and the top end of the vertical line.
        The triangle's legs extend leftward and downward from this point, with length controlled by triangle_leg_ratio.
        The triangle is always fully inside the cross's bounding box.
        Args:
            x, y: center of the cross
            size: cross size (full length)
            ratio: cross line width / size
            triangle_leg_ratio: triangle leg length / size (0~1)
        Returns:
            [h_line, v_line, triangle]
        """
        try:
            import pya
            Box = pya.Box
            Point = pya.Point
            Polygon = pya.Polygon
        except (ImportError, AttributeError):
            import klayout.db as db
            Box = db.Box
            Point = db.Point
            Polygon = db.Polygon
        width = size * s * ratio
        half = size * s / 2
        half_w = width / 2
        # Cross arms (centered at x, y)
        h_line = Box(x * s - half, y * s - half_w, x * s + half, y * s + half_w)
        v_line = Box(x * s - half_w, y * s - half, x * s + half_w, y * s + half)
        # Triangle parameters
        tri_leg = size * s * triangle_leg_ratio
        # Right angle at the right-top corner of the cross
        tri_right = (x * s + half, y * s + half)
        tri_p2 = (tri_right[0] - tri_leg, tri_right[1])      # leftward
        tri_p3 = (tri_right[0], tri_right[1] - tri_leg)      # downward
        triangle = Polygon([
            Point(*tri_right),
            Point(*tri_p2),
            Point(*tri_p3)
        ])
        return [h_line, v_line, triangle] 

    @staticmethod
    def create_cross_mark(x, y, size, width):
        # x, y: center; size: full length; width: line width
        s = GeometryUtils.UNIT_SCALE
        half_size = size * s / 2
        half_width = width * s / 2
        # Horizontal line
        h_line = Box(x * s - half_size, y * s - half_width, x * s + half_size, y * s + half_width)
        # Vertical line
        v_line = Box(x * s - half_width, y * s - half_size, x * s + half_width, y * s + half_size)
        return [h_line, v_line]

    @staticmethod
    def create_square_mark(x, y, size=10.0):
        # x, y: center; size: edge length
        s = GeometryUtils.UNIT_SCALE
        half = size * s / 2
        return Box(x * s - half, y * s - half, x * s + half, y * s + half)

    @staticmethod
    def create_diamond_mark(x, y, size=10.0):
        # x, y: center; size: diagonal length
        s = GeometryUtils.UNIT_SCALE
        half = size * s / 2
        points = [
            Point(x * s, y * s - half),
            Point(x * s + half, y * s),
            Point(x * s, y * s + half),
            Point(x * s - half, y * s)
        ]
        return Polygon(points)

    @staticmethod
    def create_triangle_mark(x, y, size=10.0, direction='up'):
        # x, y: center; size: bounding box edge
        s = GeometryUtils.UNIT_SCALE
        half = size * s / 2
        if direction == 'up':
            points = [
                Point(x * s, y * s - half),
                Point(x * s - half, y * s + half),
                Point(x * s + half, y * s + half)
            ]
        elif direction == 'down':
            points = [
                Point(x * s, y * s + half),
                Point(x * s - half, y * s - half),
                Point(x * s + half, y * s - half)
            ]
        elif direction == 'left':
            points = [
                Point(x * s - half, y * s),
                Point(x * s + half, y * s - half),
                Point(x * s + half, y * s + half)
            ]
        else:  # right
            points = [
                Point(x * s + half, y * s),
                Point(x * s - half, y * s - half),
                Point(x * s - half, y * s + half)
            ]
        return Polygon(points) 

    @staticmethod
    def create_square_with_missing_quadrants_and_border(x, y, size, missing=(2,4), border_ratio=0.1):
        s = GeometryUtils.UNIT_SCALE
        """
        Returns the union of create_square_with_missing_quadrants and a 90-degree rotated create_square_with_missing_quadrants_with_border.
        The rotation is around the mark's own center (x, y).
        Args:
            x, y: center of the square
            size: square size (full length)
            missing: tuple of quadrant numbers to remove (1=top-left, 2=top-right, 3=bottom-left, 4=bottom-right)
            border_ratio: border width / size (0~0.5)
        Returns:
            Region: original mark + rotated border mark
        """
        try:
            import pya
            Region = pya.Region
            Trans = pya.Trans
        except (ImportError, AttributeError):
            import klayout.db as db
            Region = db.Region
            Trans = db.Trans
        # Original mark
        region1 = GeometryUtils.create_square_with_missing_quadrants(x, y, size, missing)
        # Border mark
        region2 = GeometryUtils.create_square_with_missing_quadrants_with_border(x, y, size, border_ratio, missing)
        # Rotate border mark 90 degrees about (x, y)
        region2_rot = region2.dup()
        region2_rot.transform(Trans(0, False, -int(x * s), -int(y * s)))  # move to origin
        region2_rot.transform(Trans(1, False, 0, 0))                      # rotate 90 deg
        region2_rot.transform(Trans(0, False, int(x * s), int(y * s)))    # move back to (x, y)
        return region1 + region2_rot 

    @staticmethod
    def create_square_with_missing_quadrants_diff_and_rotated_border(x, y, size, missing=(2,4), border_ratio=0.1):
        s = GeometryUtils.UNIT_SCALE
        """
        Returns (create_square_with_missing_quadrants - create_square_with_missing_quadrants_with_border)
        plus a 90-degree rotated create_square_with_missing_quadrants_with_border, all centered at (x, y).
        Args:
            x, y: center of the square
            size: square size (full length)
            missing: tuple of quadrant numbers to remove (1=top-left, 2=top-right, 3=bottom-left, 4=bottom-right)
            border_ratio: border width / size (0~0.5)
        Returns:
            Region: (mark - border) + rotated border
        """
        try:
            import pya
            Region = pya.Region
            Trans = pya.Trans
        except (ImportError, AttributeError):
            import klayout.db as db
            Region = db.Region
            Trans = db.Trans
        # 1. Difference: mark - border
        mark = GeometryUtils.create_square_with_missing_quadrants(x, y, size, missing)
        border = GeometryUtils.create_square_with_missing_quadrants_with_border(x, y, size, border_ratio, missing)
        diff = mark - border
        # 2. Rotated border
        border_rot = border.dup()
        border_rot.transform(Trans(0, False, -int(x * s), -int(y * s)))
        border_rot.transform(Trans(1, False, 0, 0))
        border_rot.transform(Trans(0, False, int(x * s), int(y * s)))
        # 3. Union
        return diff + border_rot 

    @staticmethod
    def create_rectangle_polygon(x, y, width, height, center=True):
        s = GeometryUtils.UNIT_SCALE
        if center:
            cx, cy = x * s, y * s
        else:
            cx, cy = (x + width/2) * s, (y + height/2) * s
        w2, h2 = width * s / 2, height * s / 2
        points = [
            Point(int(cx - w2), int(cy - h2)),
            Point(int(cx + w2), int(cy - h2)),
            Point(int(cx + w2), int(cy + h2)),
            Point(int(cx - w2), int(cy + h2)),
        ]
        return Polygon(points) 