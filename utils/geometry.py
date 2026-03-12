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

    @staticmethod
    def create_serpentine_wire(x, y, length, width, spacing, turns, direction='horizontal', curve_type='serpentine'):
        """
        创建蜿蜒线 - 支持蛇形、皮亚诺曲线、希尔伯特曲线
        
        Args:
            x, y: 蜿蜒线中心坐标
            length: 蜿蜒线总长度
            width: 线宽
            spacing: 线间距（相邻线段之间的距离）
            turns: 转折次数（奇数）
            direction: 起始方向 'horizontal' 或 'vertical'
            curve_type: 曲线类型 'serpentine', 'peano', 'hilbert'
            
        Returns:
            Polygon: 蜿蜒线多边形
        """
        s = GeometryUtils.UNIT_SCALE
        x, y = x * s, y * s
        length, width, spacing = length * s, width * s, spacing * s
        
        if curve_type == 'serpentine':
            return GeometryUtils._create_serpentine_curve(x, y, length, width, spacing, turns, direction)
        elif curve_type == 'peano':
            return GeometryUtils._create_peano_curve(x, y, length, width, spacing, turns)
        elif curve_type == 'hilbert':
            return GeometryUtils._create_hilbert_curve(x, y, length, width, spacing, turns)
        else:
            return GeometryUtils._create_serpentine_curve(x, y, length, width, spacing, turns, direction)
    
    @staticmethod
    def _create_serpentine_curve(x, y, region_width, region_height, line_width, line_spacing, direction, bend_style='rect', margin=0):
        """创建蛇形曲线 - 连续路径，只有直角U形转折"""
        
        # 计算pitch（线宽+间距）
        pitch = line_width + line_spacing
        
        # 验证区域尺寸
        if direction == 'horizontal':
            available_height = region_height - 2 * margin
            num_lanes = int(available_height / pitch)
            if num_lanes < 2:
                print(f"Warning: Region height {region_height} too small for at least 2 lanes")
                num_lanes = 2
        else:
            available_width = region_width - 2 * margin
            num_lanes = int(available_width / pitch)
            if num_lanes < 2:
                print(f"Warning: Region width {region_width} too small for at least 2 lanes")
                num_lanes = 2
        
        # 生成连续的中心线路径点（只有H/V段）
        points = []
        
        if direction == 'horizontal':
            # 水平蛇形：左右来回
            # 计算实际使用的区域
            actual_height = num_lanes * pitch
            start_y = y - actual_height / 2 + line_width / 2
            
            # 边界位置（考虑边距）
            left_bound = x - region_width / 2 + margin + line_width / 2
            right_bound = x + region_width / 2 - margin - line_width / 2
            
            current_y = start_y
            
            for i in range(num_lanes):
                if i % 2 == 0:
                    # 偶数行：从左到右
                    points.append((left_bound, current_y))
                    points.append((right_bound, current_y))
                else:
                    # 奇数行：从右到左
                    points.append((right_bound, current_y))
                    points.append((left_bound, current_y))
                
                # 移动到下一行：添加垂直步进
                if i < num_lanes - 1:
                    current_y += pitch
                    
        else:
            # 垂直蛇形：上下来回
            # 计算实际使用的区域
            actual_width = num_lanes * pitch
            start_x = x - actual_width / 2 + line_width / 2
            
            # 边界位置（考虑边距）
            bottom_bound = y - region_height / 2 + margin + line_width / 2
            top_bound = y + region_height / 2 - margin - line_width / 2
            
            current_x = start_x
            
            for i in range(num_lanes):
                if i % 2 == 0:
                    # 偶数列：从下到上
                    points.append((current_x, bottom_bound))
                    points.append((current_x, top_bound))
                else:
                    # 奇数列：从上到下
                    points.append((current_x, top_bound))
                    points.append((current_x, bottom_bound))
                
                # 移动到下一列：添加水平步进
                if i < num_lanes - 1:
                    current_x += pitch
        
        # 使用pya.Path创建连续路径
        return GeometryUtils._create_path_polygon(points, line_width)
    
    @staticmethod
    def _segment_to_parallelogram(ax, ay, bx, by, width):
        """
        由线段 (ax,ay)->(bx,by) 和线宽 width 生成平行四边形（0°/90° 时为矩形）。
        宽度方向为垂直于线段方向的单位法向，保证线宽一致。
        返回四个顶点 [(x,y), ...]，逆时针顺序。
        """
        dx = bx - ax
        dy = by - ay
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1e-12:
            return [(ax, ay), (ax, ay), (ax, ay), (ax, ay)]
        ux = dx / length
        uy = dy / length
        # 单位法向（逆时针旋转 90°）：(-uy, ux)
        nx = -uy
        ny = ux
        half = width / 2.0
        # 四个顶点：A+perp, B+perp, B-perp, A-perp（逆时针）
        return [
            (ax + half * nx, ay + half * ny),
            (bx + half * nx, by + half * ny),
            (bx - half * nx, by - half * ny),
            (ax - half * nx, ay - half * ny),
        ]
    
    @staticmethod
    def _segment_to_parallelogram_width_dir(ax, ay, bx, by, width, width_dir_x, width_dir_y):
        """
        由线段 (ax,ay)->(bx,by) 和线宽 width、指定宽度方向 (width_dir_x, width_dir_y) 生成平行四边形。
        宽度沿给定方向，保证连接短线与车道线宽一致（连接段用车道方向 u 作为宽度方向）。
        返回四个顶点 [(x,y), ...]，逆时针顺序。
        """
        d_len = math.sqrt(width_dir_x * width_dir_x + width_dir_y * width_dir_y)
        if d_len < 1e-12:
            return [(ax, ay), (bx, by), (bx, by), (ax, ay)]
        wx = width_dir_x / d_len
        wy = width_dir_y / d_len
        half = width / 2.0
        return [
            (ax + half * wx, ay + half * wy),
            (bx + half * wx, by + half * wy),
            (bx - half * wx, by - half * wy),
            (ax - half * wx, ay - half * wy),
        ]
    
    @staticmethod
    def _segment_rect_clip(x0, y0, x1, y1, half_w, half_h):
        """
        将线段 (x0,y0)->(x1,y1) 裁剪到矩形 [-half_w,half_w] x [-half_h,half_h] 内。
        返回裁剪后的线段端点 [(xa,ya), (xb,yb)]，若无交则返回 []。
        """
        dx = x1 - x0
        dy = y1 - y0
        eps = 1e-12
        if abs(dx) < eps and abs(dy) < eps:
            if -half_w - eps <= x0 <= half_w + eps and -half_h - eps <= y0 <= half_h + eps:
                return [(x0, y0), (x0, y0)]
            return []
        t_min, t_max = 0.0, 1.0
        for (p, d, lo, hi) in [
            (x0, dx, -half_w, half_w),
            (y0, dy, -half_h, half_h),
        ]:
            if abs(d) < eps:
                if p < lo - eps or p > hi + eps:
                    return []
                continue
            t_lo = (lo - p) / d
            t_hi = (hi - p) / d
            if d < 0:
                t_lo, t_hi = t_hi, t_lo
            t_min = max(t_min, t_lo)
            t_max = min(t_max, t_hi)
            if t_min > t_max + eps:
                return []
        xa = x0 + t_min * dx
        ya = y0 + t_min * dy
        xb = x0 + t_max * dx
        yb = y0 + t_max * dy
        return [(xa, ya), (xb, yb)]

    @staticmethod
    def _line_rect_intersection(n_x, n_y, c, half_w, half_h):
        """
        求直线 n_x*x + n_y*y = c 与矩形 [-half_w,half_w] x [-half_h,half_h] 的交点。
        返回最多两个交点列表 [(x,y), ...]。
        """
        points = []
        eps = 1e-9
        # 右边 x = half_w
        if abs(n_y) > eps:
            y = (c - n_x * half_w) / n_y
            if -half_h - eps <= y <= half_h + eps:
                points.append((half_w, y))
        # 左边 x = -half_w
        if abs(n_y) > eps:
            y = (c + n_x * half_w) / n_y
            if -half_h - eps <= y <= half_h + eps:
                p = (-half_w, y)
                if not any(abs(p[0] - q[0]) < eps and abs(p[1] - q[1]) < eps for q in points):
                    points.append(p)
        # 上边 y = half_h
        if abs(n_x) > eps:
            x = (c - n_y * half_h) / n_x
            if -half_w - eps <= x <= half_w + eps:
                p = (x, half_h)
                if not any(abs(p[0] - q[0]) < eps and abs(p[1] - q[1]) < eps for q in points):
                    points.append(p)
        # 下边 y = -half_h
        if abs(n_x) > eps:
            x = (c + n_y * half_h) / n_x
            if -half_w - eps <= x <= half_w + eps:
                p = (x, -half_h)
                if not any(abs(p[0] - q[0]) < eps and abs(p[1] - q[1]) < eps for q in points):
                    points.append(p)
        return points[:2]
    
    @staticmethod
    def create_angled_meander_in_rect(cx, cy, width, height, line_width, line_spacing, angle_deg):
        """
        在矩形区域限制内按给定取向绘制蜿蜒线。
        
        严格按用户方法：
        1) 先生成水平的、完整宽度的平行条带（每条带宽 line_width，长于 2 倍限制区域）
        2) 将条带旋转到要求角度
        3) 与限制区域求交，得到所需取向的等宽条纹（每条线宽严格一致）
        4) 再做转角连接（平行四边形，宽度同样为 line_width）
        
        Args:
            cx, cy: 矩形中心 (μm)
            width, height: 矩形宽、高 (μm)，一般为正方形
            line_width: 线宽 (μm)
            line_spacing: 线间距 (μm)
            angle_deg: 蜿蜒线取向角度 (度)，0=水平，90=垂直，30/60 等为斜向
            
        Returns:
            Region: 限定在矩形内的蜿蜒线多边形区域
        """
        try:
            import pya
            Region = pya.Region
            Polygon = pya.Polygon
            Point = pya.Point
            Trans = pya.Trans
            Box = pya.Box
        except (ImportError, AttributeError):
            import klayout.db as db
            Region = db.Region
            Polygon = db.Polygon
            Point = db.Point
            Trans = db.Trans
            Box = db.Box
        s = GeometryUtils.UNIT_SCALE  # μm -> dbu (1 μm = s dbu，如 dbu=0.001μm 则 s=1000)
        pitch = line_width + line_spacing
        half_w = width / 2.0
        half_h = height / 2.0
        angle_rad = math.radians(angle_deg)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        u_x, u_y = cos_a, sin_a
        n_x, n_y = -sin_a, cos_a

        def u_coord(x, y):
            return x * u_x + y * u_y

        def n_coord(x, y):
            return x * n_x + y * n_y

        def rotate(x, y):
            return (x * cos_a - y * sin_a, x * sin_a + y * cos_a)

        # 1) 水平条带：每条为完整宽度 line_width，长度 > 2*限制区域
        L = 2.0 * max(half_w, half_h) + width + height
        span_n = (2.0 * half_w) * abs(sin_a) + (2.0 * half_h) * abs(cos_a)
        num_lanes = max(2, int(span_n / pitch))
        c0 = -span_n / 2.0 + pitch / 2.0
        lane_centers = [c0 + i * pitch for i in range(num_lanes)]

        # 矩形限制（本地坐标 μm，输出时乘 s 转为 dbu）
        rect_poly = Polygon([
            Point(int(round(-half_w * s)), int(round(-half_h * s))),
            Point(int(round(half_w * s)), int(round(-half_h * s))),
            Point(int(round(half_w * s)), int(round(half_h * s))),
            Point(int(round(-half_w * s)), int(round(half_h * s))),
        ])
        rect_region = Region([rect_poly])

        # 2) 对每条车道：生成水平条带（矩形，宽 line_width），旋转后与矩形求交 → 等宽条纹
        stripe_polygons = []
        for c in lane_centers:
            y_lo = c - line_width / 2.0
            y_hi = c + line_width / 2.0
            band_corners = [(-L, y_lo), (L, y_lo), (L, y_hi), (-L, y_hi)]
            rot_corners = [rotate(x, y) for x, y in band_corners]
            band_poly = Polygon([Point(int(round(p[0] * s)), int(round(p[1] * s))) for p in rot_corners])
            stripe_region = (Region([band_poly]) & rect_region).merged()
            for poly in stripe_region.each():
                stripe_polygons.append((poly, c))
                break

        if len(stripe_polygons) < 1:
            return Region()

        def polygon_vertices(poly):
            p = getattr(poly, 'polygon', poly)
            try:
                return [(float(pt.x), float(pt.y)) for pt in p.each_point()]
            except AttributeError:
                try:
                    return [(float(pt.x), float(pt.y)) for pt in p.each_point_hull()]
                except AttributeError:
                    n = getattr(p, 'num_points_hull', lambda: 0)()
                    if n == 0:
                        return []
                    return [(float(p.point_hull(i).x), float(p.point_hull(i).y)) for i in range(n)]

        def get_caps(vertices, u_coord_fn, n_coord_fn):
            if not vertices:
                return None, None
            u_vals = [u_coord_fn(x, y) for x, y in vertices]
            u_min, u_max = min(u_vals), max(u_vals)
            eps = 1e-9
            left = [(x, y) for (x, y), u in zip(vertices, u_vals) if u <= u_min + eps]
            right = [(x, y) for (x, y), u in zip(vertices, u_vals) if u >= u_max - eps]
            left.sort(key=lambda p: n_coord_fn(p[0], p[1]))
            right.sort(key=lambda p: n_coord_fn(p[0], p[1]))
            # 取 cap 在 n 方向上的两端点（允许多于 2 个顶点时取首尾）
            left_cap = [left[0], left[-1]] if len(left) >= 2 else None
            right_cap = [right[0], right[-1]] if len(right) >= 2 else None
            return (left_cap, right_cap)

        def poly_center_n(poly):
            verts = polygon_vertices(poly)
            if not verts:
                return 0.0
            return sum(n_coord(x, y) for x, y in verts) / len(verts)

        stripe_polygons.sort(key=lambda t: -poly_center_n(t[0]))

        stripe_caps = []
        for poly, _ in stripe_polygons:
            verts = polygon_vertices(poly)
            left_cap, right_cap = get_caps(verts, u_coord, n_coord)
            stripe_caps.append((left_cap, right_cap))

        # 矩形边界（dbu），用于内移连接端点使连接线宽完整落在矩形内
        left_dbu = -half_w * s
        right_dbu = half_w * s
        bottom_dbu = -half_h * s
        top_dbu = half_h * s
        tol_dbu = max(1.0, line_width * s * 0.01)

        def inward_normal_dbu(px, py):
            """点 (px,py) 在矩形边上时的单位内向法向 (dbu)"""
            nx, ny = 0.0, 0.0
            if px <= left_dbu + tol_dbu:
                nx = 1.0
            if px >= right_dbu - tol_dbu:
                nx = -1.0
            if py <= bottom_dbu + tol_dbu:
                ny = 1.0
            if py >= top_dbu - tol_dbu:
                ny = -1.0
            if nx == 0 and ny == 0:
                return (0.0, 0.0)
            d = math.sqrt(nx * nx + ny * ny)
            return (nx / d, ny / d)

        # 备用：由车道中心线裁剪到矩形得到每条纹的左右端（μm→dbu），按已排序的 stripe 顺序
        def lane_ends_dbu(c):
            x0, y0 = rotate(-half_w - 1.0, c)
            x1, y1 = rotate(half_w + 1.0, c)
            clip = GeometryUtils._segment_rect_clip(x0, y0, x1, y1, half_w, half_h)
            if len(clip) < 2:
                return (None, None)
            u_pts = [(p[0] * u_x + p[1] * u_y, p) for p in clip]
            u_pts.sort(key=lambda t: t[0])
            left_um, right_um = u_pts[0][1], u_pts[-1][1]
            return ((left_um[0] * s, left_um[1] * s), (right_um[0] * s, right_um[1] * s))

        lane_ends_ordered = [lane_ends_dbu(c) for (_, c) in stripe_polygons]

        # 3) 平行线间连接：平行四边形，线宽=设定值；端点内移使 0°/90° 时不被裁掉一半
        path_region = Region()
        for i, (poly, _) in enumerate(stripe_polygons):
            path_region.insert(poly)

        line_width_dbu = line_width * s
        for i in range(len(stripe_caps) - 1):
            left0, right0 = stripe_caps[i]
            left1, right1 = stripe_caps[i + 1]
            if i % 2 == 0:
                cap_exit, cap_entry = right0, right1
            else:
                cap_exit, cap_entry = left0, left1

            if cap_exit is not None and len(cap_exit) >= 2:
                exit_cx = (cap_exit[0][0] + cap_exit[1][0]) / 2.0
                exit_cy = (cap_exit[0][1] + cap_exit[1][1]) / 2.0
            elif i < len(lane_ends_ordered):
                le = lane_ends_ordered[i]
                end = le[1] if i % 2 == 0 else le[0]
                if end is None:
                    continue
                exit_cx, exit_cy = end[0], end[1]
            else:
                continue

            if cap_entry is not None and len(cap_entry) >= 2:
                entry_cx = (cap_entry[0][0] + cap_entry[1][0]) / 2.0
                entry_cy = (cap_entry[0][1] + cap_entry[1][1]) / 2.0
            elif i + 1 < len(lane_ends_ordered):
                le1 = lane_ends_ordered[i + 1]
                end = le1[1] if i % 2 == 0 else le1[0]
                if end is None:
                    continue
                entry_cx, entry_cy = end[0], end[1]
            else:
                continue

            seg_len_sq = (entry_cx - exit_cx) ** 2 + (entry_cy - exit_cy) ** 2
            if seg_len_sq < (line_width_dbu * 0.1) ** 2:
                continue

            in_ex = inward_normal_dbu(exit_cx, exit_cy)
            in_en = inward_normal_dbu(entry_cx, entry_cy)
            half_dbu = line_width_dbu / 2.0
            exit_cx = exit_cx + half_dbu * in_ex[0]
            exit_cy = exit_cy + half_dbu * in_ex[1]
            entry_cx = entry_cx + half_dbu * in_en[0]
            entry_cy = entry_cy + half_dbu * in_en[1]

            verts = GeometryUtils._segment_to_parallelogram_width_dir(
                exit_cx, exit_cy, entry_cx, entry_cy, line_width_dbu, u_x, u_y
            )
            conn_poly = Polygon([Point(int(round(p[0])), int(round(p[1]))) for p in verts])
            path_region.insert(conn_poly)

        path_region = path_region.merged()
        result_local = path_region & rect_region
        result_local.transform(Trans(0, False, int(round(cx * s)), int(round(cy * s))))
        return result_local
    
    @staticmethod
    def _create_hilbert_curve(x, y, length, width, spacing, turns):
        """创建希尔伯特曲线 - 连续路径"""
        # 计算网格大小
        grid_size = length / (2 ** turns)
        current_x = x - length / 2
        current_y = y - length / 2
        
        # 递归生成希尔伯特曲线路径
        path_points = GeometryUtils._generate_hilbert_path(turns, current_x, current_y, grid_size)
        
        # 将路径转换为连续的多边形
        return GeometryUtils._path_to_polygon(path_points, width)
    
    
    @staticmethod
    def _generate_hilbert_path(order, x, y, size):
        """生成希尔伯特曲线路径点 - 递归实现"""
        if order == 0:
            return [(x, y)]
        
        # 递归生成希尔伯特曲线
        points = []
        step = size / 2
        
        # 基础2x2希尔伯特曲线
        if order == 1:
            pattern = [
                (0, 0), (0, 1), (1, 1), (1, 0)
            ]
        else:
            # 递归生成更高阶的希尔伯特曲线
            pattern = GeometryUtils._hilbert_pattern(order)
        
        for px, py in pattern:
            points.append((x + px * step, y + py * step))
        
        return points
    
    
    @staticmethod
    def _hilbert_pattern(order):
        """生成希尔伯特曲线模式 - 递归实现"""
        if order == 1:
            return [(0, 0), (0, 1), (1, 1), (1, 0)]
        
        # 递归生成更高阶的希尔伯特曲线
        prev_pattern = GeometryUtils._hilbert_pattern(order - 1)
        new_pattern = []
        
        # 将前一个模式复制到四个象限
        size = 2 ** (order - 1)
        
        # 左下象限（旋转180度）
        for px, py in prev_pattern:
            new_pattern.append((size - 1 - px, size - 1 - py))
        
        # 右下象限（不变）
        for px, py in prev_pattern:
            new_pattern.append((size + px, size - 1 - py))
        
        # 右上象限（不变）
        for px, py in prev_pattern:
            new_pattern.append((size + px, size + py))
        
        # 左上象限（旋转180度）
        for px, py in prev_pattern:
            new_pattern.append((size - 1 - px, size + py))
        
        return new_pattern
    
    
    @staticmethod
    def _create_path_polygon(points, line_width):
        """使用pya.Path创建连续路径多边形"""
        import pya
        
        if len(points) < 2:
            return GeometryUtils.create_rectangle(points[0][0], points[0][1], line_width, line_width, center=True)
        
        # 创建pya.Path对象
        # 使用方形端点，斜接连接，保持尖锐的角和恒定宽度
        path = pya.Path(points, line_width, 0, 0, 0)  # width, bgn_ext=0, end_ext=0, round=False
        
        # 转换为多边形
        polygon = path.polygon()
        
        # 转换为Region并合并（确保单一连续多边形）
        region = pya.Region([polygon])
        merged_region = region.merged()
        
        return merged_region
    
    @staticmethod
    def make_hilbert(order, step, line_w, margin=0.0):
        """
        生成正交Hilbert曲线 - 使用整数网格Hilbert索引器
        
        Args:
            order: 曲线阶数 (≥1)
            step: 线段长度 (μm)
            line_w: 线条宽度 (μm)
            margin: 边距 (μm)
            
        Returns:
            pya.Region: 连续的多边形区域
        """
        import pya
        
        if order < 1:
            raise ValueError("Order must be >= 1")
        
        # 计算网格大小
        N = 1 << order  # N = 2**order
        
        # 生成Hilbert曲线点
        points = []
        for d in range(N * N):
            xi, yi = GeometryUtils._d2xy(N, d)
            # 直接使用微米坐标，不转换DBU
            x = margin + xi * step
            y = margin + yi * step
            points.append(pya.Point(x, y))
        
        # 验证点序列（点数应为 N*N）
        GeometryUtils._validate_hilbert_points(points, order, step)
        
        # 创建单一连续路径
        path = pya.Path(points, line_w, 0, 0, 0)  # width, bgn_ext=0, end_ext=0, round=False
        
        # 转换为多边形并合并
        polygon = path.polygon()
        region = pya.Region([polygon])
        merged_region = region.merged()
        
        return merged_region
    
    @staticmethod
    def _validate_hilbert_points(points, order, step):
        """验证 Hilbert 曲线点序列：点数应为 N*N，且相邻点间距为 step。"""
        N = 1 << order
        expected_count = N * N
        if len(points) != expected_count:
            raise ValueError(
                f"Hilbert points count mismatch: got {len(points)}, expected {expected_count} (order={order})"
            )
    
    @staticmethod
    def _d2xy(N, d):
        """Hilbert曲线d到(x,y)的映射"""
        x = y = 0
        s = 1
        t = d
        while s < N:
            rx = 1 & (t // 2)
            ry = 1 & (t ^ rx)
            if ry == 0:
                if rx == 1:
                    x, y = (s-1 - x), (s-1 - y)
                x, y = y, x
            x += s * rx
            y += s * ry
            t //= 4
            s *= 2
        return x, y 
    
    @staticmethod
    def _create_peano_curve(x, y, length, width, spacing, turns):
        """Create Peano curve - space-filling curve that divides space into 9 parts"""
        import pya
        s = GeometryUtils.UNIT_SCALE
        x, y = x * s, y * s
        length, width, spacing = length * s, width * s, spacing * s
        
        # Generate Peano curve points
        points = GeometryUtils._generate_peano_path(turns, x, y, length)
        
        # Create path from points
        path = pya.Path(points, width, 0, 0, 0)  # width, bgn_ext=0, end_ext=0, round=False
        
        # Convert to polygon
        polygon = path.polygon()
        
        # Convert to Region and merge (ensure single continuous polygon)
        region = pya.Region([polygon])
        merged_region = region.merged()
        
        return merged_region
    
    @staticmethod
    def _generate_peano_path(order, x, y, size):
        """Generate Peano curve path points"""
        points = []
        step = size / (3 ** order)
        
        for i in range(3 ** (2 * order)):
            px, py = GeometryUtils._peano_point(i, order)
            points.append(Point(int(x + px * step), int(y + py * step)))
        
        return points
    
    @staticmethod
    def _peano_point(t, order):
        """Get point on Peano curve at parameter t"""
        x, y = 0, 0
        s = 1
        
        for i in range(order):
            # Peano curve divides space into 3x3 grid
            tx = t % 3
            ty = (t // 3) % 3
            
            # Apply Peano transformation
            if tx == 0:
                if ty == 0:
                    x, y = x, y
                elif ty == 1:
                    x, y = s - x, y
                else:  # ty == 2
                    x, y = x, y
            elif tx == 1:
                if ty == 0:
                    x, y = x, s - y
                elif ty == 1:
                    x, y = s - x, s - y
                else:  # ty == 2
                    x, y = x, s - y
            else:  # tx == 2
                if ty == 0:
                    x, y = x, y
                elif ty == 1:
                    x, y = s - x, y
                else:  # ty == 2
                    x, y = x, y
            
            t //= 9
            s *= 3
        
        return x, y
    
    @staticmethod
    def _create_gosper_curve(x, y, length, width, spacing, turns):
        """Create Gosper curve (flowsnake) - hexagonal space-filling curve"""
        import pya
        from utils.gosper_curve import make_gosper_polygon
        
        s = GeometryUtils.UNIT_SCALE
        x, y = x * s, y * s
        length, width, spacing = length * s, width * s, spacing * s
        
        # Use the robust Gosper implementation
        # Calculate step size based on length and order
        order = max(1, turns)  # Ensure at least order 1
        step = length / (7 ** order) if order > 0 else length
        
        # Generate Gosper polygon
        dpolygon = make_gosper_polygon(order, step, width, origin=(x, y), dbu=1.0)
        
        # Convert to Region for compatibility
        region = pya.Region([dpolygon])
        merged_region = region.merged()
        
        return merged_region
    
    @staticmethod
    def _generate_gosper_path(order, x, y, size):
        """Generate Gosper curve path points"""
        points = []
        step = size / (7 ** order)
        
        for i in range(7 ** order):
            px, py = GeometryUtils._gosper_point(i, order)
            points.append(Point(int(x + px * step), int(y + py * step)))
        
        return points
    
    @staticmethod
    def _gosper_point(t, order):
        """Get point on Gosper curve at parameter t"""
        x, y = 0, 0
        s = 1
        
        for i in range(order):
            # Gosper curve uses 7-fold symmetry
            direction = t % 7
            
            # Apply Gosper transformation based on direction
            if direction == 0:
                x, y = x, y
            elif direction == 1:
                x, y = x + s, y
            elif direction == 2:
                x, y = x + s/2, y + s * 0.866  # sqrt(3)/2
            elif direction == 3:
                x, y = x - s/2, y + s * 0.866
            elif direction == 4:
                x, y = x - s, y
            elif direction == 5:
                x, y = x - s/2, y - s * 0.866
            else:  # direction == 6
                x, y = x + s/2, y - s * 0.866
            
            t //= 7
            s *= 7
        
        return x, y
    
    @staticmethod
    def _create_moore_curve(x, y, length, width, spacing, turns):
        """Create Moore curve - closed version of Hilbert curve"""
        import pya
        s = GeometryUtils.UNIT_SCALE
        x, y = x * s, y * s
        length, width, spacing = length * s, width * s, spacing * s
        
        # Generate Moore curve points
        points = GeometryUtils._generate_moore_path(turns, x, y, length)
        
        # Create path from points
        path = pya.Path(points, width, 0, 0, 0)  # width, bgn_ext=0, end_ext=0, round=False
        
        # Convert to polygon
        polygon = path.polygon()
        
        # Convert to Region and merge (ensure single continuous polygon)
        region = pya.Region([polygon])
        merged_region = region.merged()
        
        return merged_region
    
    @staticmethod
    def _generate_moore_path(order, x, y, size):
        """Generate Moore curve path points"""
        points = []
        step = size / (2 ** order)
        
        # Moore curve is a closed Hilbert curve
        for i in range(4 ** order):
            px, py = GeometryUtils._moore_point(i, order)
            points.append(Point(int(x + px * step), int(y + py * step)))
        
        # Close the curve by connecting last point to first
        if points:
            points.append(points[0])
        
        return points
    
    @staticmethod
    def _moore_point(t, order):
        """Get point on Moore curve at parameter t"""
        # Moore curve is essentially a Hilbert curve with connection
        # Use the existing Hilbert pattern generation
        pattern = GeometryUtils._hilbert_pattern(order)
        if t < len(pattern):
            return pattern[t]
        else:
            # If t exceeds pattern length, return the last point
            return pattern[-1]
