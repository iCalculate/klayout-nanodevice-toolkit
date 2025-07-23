import pya
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../utils')))
from mark_utils import MarkUtils
from utils.geometry import GeometryUtils

class MarkPCell(pya.PCellDeclarationHelper):
    def __init__(self):
        super(MarkPCell, self).__init__()
        self.param("shape", self.TypeString, "Mark shape", default="cross",
                   choices=[
                       ("cross", "cross"),
                       ("square", "square"),
                       ("circle", "circle"),
                       ("diamond", "diamond"),
                       ("triangle_up", "triangle_up"),
                       ("triangle_down", "triangle_down"),
                       ("L", "L"),
                       ("T", "T"),
                       ("semi_cross", "semi_cross"),
                       ("cross_pos", "cross_pos"),
                       ("cross_neg", "cross_neg"),
                       ("l_shape", "l_shape"),
                       ("t_shape", "t_shape"),
                       ("sq_missing", "sq_missing"),
                       ("sq_missing_border", "sq_missing_border"),
                       ("cross_tri", "cross_tri"),
                       ("sq_missing_rotborder", "sq_missing_rotborder"),
                       ("sq_missing_diff_rotborder", "sq_missing_diff_rotborder"),
                       ("regular_polygon", "regular_polygon"),
                       ("chamfered_octagon", "chamfered_octagon")
                   ])
        self.param("x", self.TypeDouble, "X (um)", default=0.0)
        self.param("y", self.TypeDouble, "Y (um)", default=0.0)
        self.param("size", self.TypeDouble, "Size (um)", default=10.0)
        self.param("width", self.TypeDouble, "Line width (um)", default=1.0)
        self.param("rotation", self.TypeDouble, "Rotation (deg)", default=0.0)
        self.param("parameter1", self.TypeDouble, "Parameter1: ratio ", default=0.1)
        self.param("parameter2", self.TypeDouble, "Parameter2: insert_ratio ", default=0.0)
        self.param("parameter3", self.TypeDouble, "Parameter3: ", default=0.0)
        self.param("layer", self.TypeLayer, "Layer", default=pya.LayerInfo(10, 0))

    def display_text_impl(self):
        return f"MarkPCell: {self.shape}"

    def produce_impl(self):
        MarkUtils.set_unit_scale(1)
        GeometryUtils.UNIT_SCALE = 1000
        ly = self.layout
        cell = self.cell
        layer = self.layer
        shape = self.shape
        x = self.x
        y = self.y
        size = self.size
        width = self.width
        p1 = self.parameter1
        p2 = self.parameter2
        p3 = self.parameter3
        kwargs = {}
        if shape == "triangle_up":
            shape = "triangle"
            kwargs["direction"] = "up"
        elif shape == "triangle_down":
            shape = "triangle"
            kwargs["direction"] = "down"
        # 处理 missing 参数
        try:
            missing = tuple(int(i) for i in str(p3).split(",") if i.strip())
        except Exception:
            missing = (2,4)
        # 分发到不同 mark 类型
        if shape in ["cross", "square", "circle", "diamond", "triangle"]:
            mark = MarkUtils.create_mark(shape, x, y, size, width, **kwargs)
        elif shape == "L":
            mark = MarkUtils.l(x, y, size, width)
        elif shape == "T":
            mark = MarkUtils.t(x, y, size, width)
        elif shape == "semi_cross":
            mark = MarkUtils.semi_cross(x, y, size, width, head_size=p1, hole_radius=p2)
        elif shape == "cross_pos":
            mark = MarkUtils.cross_pos(x, y, size, ratio=p1)
        elif shape == "cross_neg":
            mark = MarkUtils.cross_neg(x, y, size, ratio=p1, insert_ratio=p2, box_margin=int(p3))
        elif shape == "l_shape":
            mark = MarkUtils.l_shape(x, y, size, ratio=p1, arm_ratio=p2)
        elif shape == "t_shape":
            mark = MarkUtils.t_shape(x, y, size, ratio=p1, arm_ratio=p2)
        elif shape == "sq_missing":
            mark = MarkUtils.sq_missing(x, y, size, missing=missing)
        elif shape == "sq_missing_border":
            mark = MarkUtils.sq_missing_border(x, y, size, border_ratio=p1, missing=missing)
        elif shape == "cross_tri":
            mark = MarkUtils.cross_tri(x, y, size, ratio=p1, triangle_leg_ratio=p2)
        elif shape == "sq_missing_rotborder":
            mark = MarkUtils.sq_missing_rotborder(x, y, size, missing=missing, border_ratio=p1)
        elif shape == "sq_missing_diff_rotborder":
            mark = MarkUtils.sq_missing_diff_rotborder(x, y, size, missing=missing, border_ratio=p1)
        elif shape == "regular_polygon":
            mark = MarkUtils.regular_polygon(x, y, size, n_sides=int(p1))
        elif shape == "chamfered_octagon":
            mark = MarkUtils.chamfered_octagon(x, y, size, chamfer_ratio=p1)
        else:
            mark = MarkUtils.cross(x, y, size, width)
        if hasattr(mark, 'rotate'):
            mark = mark.rotate(self.rotation)
        shapes = mark.get_shapes() if hasattr(mark, 'get_shapes') else mark
        # 插入
        if isinstance(shapes, list):
            # print(f"[DEBUG] shapes count: {len(shapes)}")
            for s in shapes:
                cell.shapes(layer).insert(s)
        else:
            print(f"[DEBUG] single shape")
            # cell.shapes(layer).insert(shapes) 