"""
Fanout electrode utility functions
All dimensions are in micrometers (µm).
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from typing import Tuple, Literal, Dict, Any, cast, Optional
from utils.geometry import GeometryUtils
import math
from utils.text_utils import TextUtils
from config import DEFAULT_DBU
from dataclasses import dataclass

# Pad parameter type
PadType = Dict[str, Any]  # center: (x, y), length, width, chamfer_size, chamfer_type

Point = GeometryUtils.Point
Polygon = GeometryUtils.Polygon


@dataclass
class PadInfo:
    polygon: object
    center: tuple
    length: float
    width: float
    chamfer_size: float
    chamfer_type: str
    corner_pts: int = 4


def draw_pad(center: Tuple[float, float], length: float, width: float, chamfer_size: float = 0.0, chamfer_type: Literal['none', 'straight', 'round'] = 'none', corner_pts: int = 4) -> PadInfo:
    """
    Draw a pad (rectangle with optional chamfered corners).
    Args:
        center: (x, y) center of the pad in µm
        length: pad length in µm
        width: pad width in µm
        chamfer_size: chamfer size in µm
        chamfer_type: 'none', 'straight', or 'round'
        corner_pts: number of points per corner for round chamfer (resolution)
    Returns:
        Polygon representing the pad
    Raises:
        ValueError: if chamfer_size is too large for the given pad size
    """
    s = GeometryUtils.UNIT_SCALE
    x, y = center
    x, y = x * s, y * s
    length, width, chamfer_size = length * s, width * s, chamfer_size * s
    min_side = min(length, width)
    if chamfer_type == 'none' or chamfer_size <= 0:
        poly = GeometryUtils.create_rectangle_polygon(x / s, y / s, length / s, width / s, center=True)
    elif chamfer_type == 'straight':
        if chamfer_size * 2 > min_side:
            raise ValueError(f"[ERROR] Straight chamfer too large: chamfer_size*2={chamfer_size*2/s:.3f}um > min(length, width)={min_side/s:.3f}um")
        half_l, half_w = length / 2, width / 2
        c = chamfer_size
        points = [
            Point(int(x - half_l + c), int(y - half_w)),
            Point(int(x + half_l - c), int(y - half_w)),
            Point(int(x + half_l), int(y - half_w + c)),
            Point(int(x + half_l), int(y + half_w - c)),
            Point(int(x + half_l - c), int(y + half_w)),
            Point(int(x - half_l + c), int(y + half_w)),
            Point(int(x - half_l), int(y + half_w - c)),
            Point(int(x - half_l), int(y - half_w + c))
        ]
        poly = Polygon(points)
    elif chamfer_type == 'round':
        if chamfer_size * 2 > min_side:
            raise ValueError(f"[ERROR] Round chamfer too large: chamfer_size*2={chamfer_size*2/s:.3f}um > min(length, width)={min_side/s:.3f}um")
        radius = min(chamfer_size, min(length, width) / 2)
        num_corner_pts = max(2, corner_pts)
        half_l, half_w = length / 2, width / 2
        corners = [
            (x + half_l - radius, y + half_w - radius),
            (x - half_l + radius, y + half_w - radius),
            (x - half_l + radius, y - half_w + radius),
            (x + half_l - radius, y - half_w + radius),
        ]
        corner_angles = [
            (0, 90),
            (90, 180),
            (180, 270),
            (270, 360)
        ]
        points = []
        for (cx, cy), (a0, a1) in zip(corners, corner_angles):
            for i in range(num_corner_pts):
                angle = math.radians(a0 + (a1 - a0) * i / (num_corner_pts - 1))
                px = cx + radius * math.cos(angle)
                py = cy + radius * math.sin(angle)
                points.append(Point(int(px), int(py)))
        poly = Polygon(points)
    else:
        raise ValueError(f"Unknown chamfer_type: {chamfer_type}")
    return PadInfo(poly, center, length / s, width / s, chamfer_size / s, chamfer_type, corner_pts)


def _pad_edge_points(center, length, width, chamfer_size, chamfer_type, edge: Literal['left', 'right', 'top', 'bottom']):
    s = GeometryUtils.UNIT_SCALE
    x, y = center
    x, y = x * s, y * s
    length, width, chamfer_size = length * s, width * s, chamfer_size * s
    half_l, half_w = length / 2, width / 2
    if chamfer_type == 'none' or chamfer_size <= 0:
        if edge == 'left':
            return (x - half_l, y - half_w), (x - half_l, y + half_w)
        elif edge == 'right':
            return (x + half_l, y - half_w), (x + half_l, y + half_w)
        elif edge == 'top':
            return (x - half_l, y + half_w), (x + half_l, y + half_w)
        elif edge == 'bottom':
            return (x - half_l, y - half_w), (x + half_l, y - half_w)
    else:
        c = chamfer_size
        if edge == 'left':
            return (x - half_l, y - half_w + c), (x - half_l, y + half_w - c)
        elif edge == 'right':
            return (x + half_l, y - half_w + c), (x + half_l, y + half_w - c)
        elif edge == 'top':
            return (x - half_l + c, y + half_w), (x + half_l - c, y + half_w)
        elif edge == 'bottom':
            return (x - half_l + c, y - half_w), (x + half_l - c, y - half_w)
    raise ValueError(f"Unknown edge: {edge}")

def _get_chamfered_edge_width(length, width, chamfer_size, chamfer_type, edge: Literal['left', 'right', 'top', 'bottom']):
    """获取倒角后边缘的实际宽度"""
    if chamfer_type == 'none' or chamfer_size <= 0:
        if edge in ['left', 'right']:
            return width
        else:  # 'top', 'bottom'
            return length
    else:
        if edge in ['left', 'right']:
            return width - 2 * chamfer_size
        else:  # 'top', 'bottom'
            return length - 2 * chamfer_size


def draw_trapezoidal_fanout(
    inner_pad: PadInfo,
    outer_pad: PadInfo,
    inner_edge: Optional[Literal['U','D','L','R']] = None,
    outer_edge: Optional[Literal['U','D','L','R']] = None,
) -> 'Polygon':
    s = GeometryUtils.UNIT_SCALE
    cx1, cy1 = inner_pad.center
    cx2, cy2 = outer_pad.center
    cx1, cy1, cx2, cy2 = cx1 * s, cy1 * s, cx2 * s, cy2 * s
    dx, dy = cx2 - cx1, cy2 - cy1
    edge_map: Dict[str, Literal['left','right','top','bottom']] = {'U': 'top', 'D': 'bottom', 'L': 'left', 'R': 'right'}
    if inner_edge is not None and inner_edge in edge_map:
        inner_edge_str: Literal['left','right','top','bottom'] = edge_map[inner_edge]
    else:
        if abs(dx) > abs(dy):
            inner_edge_str = 'right' if dx > 0 else 'left'
        else:
            inner_edge_str = 'top' if dy > 0 else 'bottom'
    if outer_edge is not None and outer_edge in edge_map:
        outer_edge_str: Literal['left','right','top','bottom'] = edge_map[outer_edge]
    else:
        if abs(dx) > abs(dy):
            outer_edge_str = 'left' if dx > 0 else 'right'
        else:
            outer_edge_str = 'bottom' if dy > 0 else 'top'
    ip1, ip2 = _pad_edge_points(
        inner_pad.center, inner_pad.length, inner_pad.width,
        inner_pad.chamfer_size, inner_pad.chamfer_type, inner_edge_str)
    op1, op2 = _pad_edge_points(
        outer_pad.center, outer_pad.length, outer_pad.width,
        outer_pad.chamfer_size, outer_pad.chamfer_type, outer_edge_str)
    points = [Point(int(ip1[0]), int(ip1[1])), Point(int(ip2[0]), int(ip2[1])), Point(int(op2[0]), int(op2[1])), Point(int(op1[0]), int(op1[1]))]
    return Polygon(points)


def _pad_edge_center(center, length, width, chamfer_size, chamfer_type, edge: Literal['left', 'right', 'top', 'bottom']):
    s = GeometryUtils.UNIT_SCALE
    x, y = center
    x, y = x * s, y * s
    length, width, chamfer_size = length * s, width * s, chamfer_size * s
    half_l, half_w = length / 2, width / 2
    if edge == 'left':
        return (x - half_l, y)
    elif edge == 'right':
        return (x + half_l, y)
    elif edge == 'top':
        return (x, y + half_w)
    elif edge == 'bottom':
        return (x, y - half_w)
    raise ValueError(f"Unknown edge: {edge}")


def draw_lead_fanout(
    inner_pad: PadInfo,
    outer_pad: PadInfo,
    line_width: float = 1.0,
    corner_type: Literal['right_angle', 'straight_chamfer', 'round_chamfer'] = 'right_angle',
    chamfer_size: float = 10.0,
) -> 'Polygon':
    s = GeometryUtils.UNIT_SCALE
    from math import atan2, cos, sin, pi, hypot, isclose
    def safe_sign(val):
        if val > 0:
            return 1
        elif val < 0:
            return -1
        else:
            return 0
    def perp(dx, dy):
        length = (dx**2 + dy**2) ** 0.5
        if length == 0:
            return (0, 0)
        return (-dy / length, dx / length)
    def offset_point(p, dx, dy, width):
        length = (dx**2 + dy**2) ** 0.5
        if length == 0:
            return (p[0], p[1]), (p[0], p[1])
        ox, oy = -dy / length * width / 2, dx / length * width / 2
        return (p[0] + ox, p[1] + oy), (p[0] - ox, p[1] - oy)
    def arc_points(center, r, start_angle, end_angle, n=10):
        # Returns list of points along arc from start_angle to end_angle (inclusive)
        return [
            (center[0] + r * cos(start_angle + (end_angle - start_angle) * t / (n-1)),
             center[1] + r * sin(start_angle + (end_angle - start_angle) * t / (n-1)))
            for t in range(n)
        ]
    cx1, cy1 = inner_pad.center
    cx2, cy2 = outer_pad.center
    cx1, cy1, cx2, cy2 = cx1 * s, cy1 * s, cx2 * s, cy2 * s
    width = line_width * s
    chamfer_size = chamfer_size * s
    # If centers are identical, return empty polygon
    if isclose(cx1, cx2, abs_tol=1e-6) and isclose(cy1, cy2, abs_tol=1e-6):
        return Polygon([])
    if corner_type in ('straight_chamfer', 'round_chamfer'):
        # 先生成L型折线
        if abs(cx2 - cx1) < abs(cy2 - cy1):
            corner = (cx1, cy2)
            seg1 = hypot(corner[0] - cx1, corner[1] - cy1)
            seg2 = hypot(cx2 - corner[0], cy2 - corner[1])
            dir1 = ((corner[0] - cx1) / seg1 if seg1 > 1e-6 else 0, (corner[1] - cy1) / seg1 if seg1 > 1e-6 else 0)
            dir2 = ((cx2 - corner[0]) / seg2 if seg2 > 1e-6 else 0, (cy2 - corner[1]) / seg2 if seg2 > 1e-6 else 0)
        else:
            corner = (cx2, cy1)
            seg1 = hypot(corner[0] - cx1, corner[1] - cy1)
            seg2 = hypot(cx2 - corner[0], cy2 - corner[1])
            dir1 = ((corner[0] - cx1) / seg1 if seg1 > 1e-6 else 0, (corner[1] - cy1) / seg1 if seg1 > 1e-6 else 0)
            dir2 = ((cx2 - corner[0]) / seg2 if seg2 > 1e-6 else 0, (cy2 - corner[1]) / seg2 if seg2 > 1e-6 else 0)
        # chamfer_size不能超过段长/2
        chamfer1 = min(chamfer_size, seg1/2)
        chamfer2 = min(chamfer_size, seg2/2)
        # 退让点
        p1 = (corner[0] - dir1[0]*chamfer1, corner[1] - dir1[1]*chamfer1)
        p2 = (corner[0] + dir2[0]*chamfer2, corner[1] + dir2[1]*chamfer2)
        if corner_type == 'straight_chamfer':
            points = [(cx1, cy1), p1, p2, (cx2, cy2)]
        elif corner_type == 'round_chamfer':
            # 切线连续的最短圆弧倒角
            from math import atan2, pi, cos, sin
            # 切点A、B
            A = p1
            B = p2
            def rot90(v):
                return (-v[1], v[0])
            n1 = rot90(dir1)
            n2 = rot90(dir2)
            dx = B[0] - A[0]
            dy = B[1] - A[1]
            det = n1[0]*n2[1] - n1[1]*n2[0]
            if abs(det) < 1e-8:
                points = [(cx1, cy1), A, B, (cx2, cy2)]
            else:
                t1 = (dx*n2[1] - dy*n2[0]) / det
                center = (A[0] + n1[0]*t1, A[1] + n1[1]*t1)
                vA = (A[0] - center[0], A[1] - center[1])
                vB = (B[0] - center[0], B[1] - center[1])
                angleA = atan2(vA[1], vA[0])
                angleB = atan2(vB[1], vB[0])
                dtheta = angleB - angleA
                while dtheta <= -pi: dtheta += 2*pi
                while dtheta > pi: dtheta -= 2*pi
                n_arc = max(8, int(abs(dtheta) / (pi / 24)))
                arc_pts = [
                    (center[0] + chamfer_size * cos(angleA + dtheta * t / (n_arc-1)),
                     center[1] + chamfer_size * sin(angleA + dtheta * t / (n_arc-1)))
                    for t in range(n_arc)
                ]
                points = [(cx1, cy1), A] + arc_pts + [B, (cx2, cy2)]
    elif corner_type == 'right_angle':
        if abs(cx2 - cx1) < abs(cy2 - cy1):
            corner = (cx1, cy2)
        else:
            corner = (cx2, cy1)
        points = [(cx1, cy1), corner, (cx2, cy2)]
    else:
        points = [(cx1, cy1), (cx2, cy2)]
    # Remove consecutive duplicate points
    filtered_points = [points[0]]
    for pt in points[1:]:
        if not (isclose(pt[0], filtered_points[-1][0], abs_tol=1e-6) and isclose(pt[1], filtered_points[-1][1], abs_tol=1e-6)):
            filtered_points.append(pt)
    points = filtered_points
    n = len(points)
    left_pts = []
    right_pts = []
    for i in range(n):
        p = points[i]
        if i == 0:
            dx, dy = points[1][0] - p[0], points[1][1] - p[1]
            lpt, rpt = offset_point(p, dx, dy, width)
            left_pts.append(Point(int(lpt[0]), int(lpt[1])))
            right_pts.append(Point(int(rpt[0]), int(rpt[1])))
        elif i == n - 1:
            dx, dy = p[0] - points[i-1][0], p[1] - points[i-1][1]
            lpt, rpt = offset_point(p, dx, dy, width)
            left_pts.append(Point(int(lpt[0]), int(lpt[1])))
            right_pts.append(Point(int(rpt[0]), int(rpt[1])))
        else:
            dx0, dy0 = p[0] - points[i-1][0], p[1] - points[i-1][1]
            dx1, dy1 = points[i+1][0] - p[0], points[i+1][1] - p[1]
            l0, _ = offset_point(p, dx0, dy0, width)
            l1, _ = offset_point(p, dx1, dy1, width)
            _, r0 = offset_point(p, dx0, dy0, width)
            _, r1 = offset_point(p, dx1, dy1, width)
            angle0 = atan2(l0[1] - p[1], l0[0] - p[0])
            angle1 = atan2(l1[1] - p[1], l1[0] - p[0])
            if (angle1 - angle0) <= -pi:
                angle1 += 2 * pi
            if (angle1 - angle0) > pi:
                angle1 -= 2 * pi
            n_arc = max(6, int(abs(angle1 - angle0) / (pi / 12)))
            arc_l = arc_points(p, width / 2, angle0, angle1, n_arc)
            left_pts.extend([Point(int(pt[0]), int(pt[1])) for pt in arc_l])
            angle0r = atan2(r0[1] - p[1], r0[0] - p[0])
            angle1r = atan2(r1[1] - p[1], r1[0] - p[0])
            if (angle1r - angle0r) <= -pi:
                angle1r += 2 * pi
            if (angle1r - angle0r) > pi:
                angle1r -= 2 * pi
            arc_r = arc_points(p, width / 2, angle0r, angle1r, n_arc)
            right_pts.extend([Point(int(pt[0]), int(pt[1])) for pt in arc_r])
    poly_points = left_pts + right_pts[::-1]
    return Polygon(poly_points)


def get_polygon_points(poly):
    return [ (poly.point_hull(i).x, poly.point_hull(i).y) for i in range(poly.num_points_hull()) ]


if __name__ == '__main__':
    # 单位缩放设置，所有坐标均以um为单位
    unit_scale = 1000  # 1 um = 1000 nm
    GeometryUtils.UNIT_SCALE = unit_scale

    try:
        import klayout.db as pya
        layout = pya.Layout()
        layout.dbu = DEFAULT_DBU
        layer_pads = layout.layer(8, 0)  # pads
        layer_routing = layout.layer(9, 0)  # routing
        layer_text = layout.layer(10, 0)  # text labels
        test_cell = layout.create_cell("FANOUT_TEST")

        # 测试参数
        outer_size = 20
        outer_chamfer = 4
        inner_size_x = 8
        inner_size_y = 4
        inner_chamfer = 0
        pad_dx = 50
        pad_dy = -30
        region_spacing_x = 100  # 每组fanout横向间隔
        region_spacing_y = -80  # 每组fanout纵向间隔
        n_cols = 3  # 每行最多3组
        fanout_types = [
            ("trapezoidal", None),
            ("lead_right_angle", "right_angle"),
            ("lead_straight_chamfer", "straight_chamfer"),
            ("lead_round_chamfer", "round_chamfer"),
        ]
        unit_scale = GeometryUtils.UNIT_SCALE

        for idx, (ftype, corner_type) in enumerate(fanout_types):
            col = idx % n_cols
            row = idx // n_cols
            x0 = col * region_spacing_x
            y0 = row * region_spacing_y
            # Outer pad
            outer = draw_pad((x0, y0), outer_size, outer_size, chamfer_size=outer_chamfer, chamfer_type='straight')
            # Inner pad
            inner = draw_pad((x0 + pad_dx, y0 + pad_dy), inner_size_x, inner_size_y, chamfer_size=inner_chamfer, chamfer_type='none')
            # Fanout
            if ftype == "trapezoidal":
                fanout = draw_trapezoidal_fanout(inner, outer)
                test_cell.shapes(layer_routing).insert(fanout)
            else:
                chamfer_val = 15 if 'chamfer' in ftype else 10
                fanout = draw_lead_fanout(inner, outer, line_width=3, corner_type=corner_type, chamfer_size=chamfer_val)
                test_cell.shapes(layer_routing).insert(fanout)
            # Pads
            test_cell.shapes(layer_pads).insert(outer.polygon)
            test_cell.shapes(layer_pads).insert(inner.polygon)
            # Label
            label = f"Fanout {idx+1}: {ftype}"
            lx = int((x0 + pad_dx/2) * unit_scale)
            ly = int((y0 + pad_dy/2 - 10) * unit_scale)
            test_cell.shapes(layer_text).insert(pya.Text.new(label, lx, ly))

        layout.write("TEST_FANOUT_UTILS.gds")
        print("GDS file TEST_FANOUT_UTILS.gds generated in project root.")
    except Exception as e:
        print("[WARN] GDS export failed:", e) 