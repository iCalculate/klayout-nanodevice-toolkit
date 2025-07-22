import pya
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../utils')))
from fanout_utils import draw_pad, draw_trapezoidal_fanout, draw_lead_fanout
from utils.geometry import GeometryUtils

class FanoutPCell(pya.PCellDeclarationHelper):
    def __init__(self):
        super(FanoutPCell, self).__init__()
        self.param("inner_center_x", self.TypeDouble, "Inner pad center X (um)", default=0.0)
        self.param("inner_center_y", self.TypeDouble, "Inner pad center Y (um)", default=0.0)
        self.param("inner_length", self.TypeDouble, "Inner pad length (um)", default=8.0)
        self.param("inner_width", self.TypeDouble, "Inner pad width (um)", default=4.0)
        self.param("inner_chamfer_size", self.TypeDouble, "Inner pad chamfer size (um)", default=0.0)
        self.param("inner_chamfer_type", self.TypeInt, "Inner pad chamfer type", default=0, choices=[["none", 0], ["straight", 1], ["round", 2]])
        self.param("inner_corner_pts", self.TypeInt, "Inner pad round chamfer points", default=4)
        self.param("outer_center_x", self.TypeDouble, "Outer pad center X (um)", default=50.0)
        self.param("outer_center_y", self.TypeDouble, "Outer pad center Y (um)", default=-30.0)
        self.param("outer_length", self.TypeDouble, "Outer pad length (um)", default=20.0)
        self.param("outer_width", self.TypeDouble, "Outer pad width (um)", default=20.0)
        self.param("outer_chamfer_size", self.TypeDouble, "Outer pad chamfer size (um)", default=4.0)
        self.param("outer_chamfer_type", self.TypeInt, "Outer pad chamfer type", default=1, choices=[["none", 0], ["straight", 1], ["round", 2]])
        self.param("outer_corner_pts", self.TypeInt, "Outer pad round chamfer points", default=4)
        self.param("fanout_type", self.TypeInt, "Fanout type", default=0, choices=[["trapezoidal", 0], ["lead_right_angle", 1], ["lead_straight_chamfer", 2], ["lead_round_chamfer", 3]])
        self.param("lead_line_width", self.TypeDouble, "Lead line width (um)", default=3.0)
        self.param("lead_corner_type", self.TypeInt, "Lead corner type", default=0, choices=[["right_angle", 0], ["straight_chamfer", 1], ["round_chamfer", 2]])
        self.param("lead_chamfer_size", self.TypeDouble, "Lead chamfer size (um)", default=10.0)
        self.param("inner_edge", self.TypeString, "Inner pad edge (U/D/L/R or empty)", default="")
        self.param("outer_edge", self.TypeString, "Outer pad edge (U/D/L/R or empty)", default="")
        self.param("layer", self.TypeLayer, "Layer", default=pya.LayerInfo(8, 0))

    def display_text_impl(self):
        return f"FanoutPCell(inner=({self.inner_center_x},{self.inner_center_y}), outer=({self.outer_center_x},{self.outer_center_y}))"

    def produce_impl(self):
        GeometryUtils.UNIT_SCALE = 1000
        ly = self.layout
        cell = self.cell
        layer = self.layer

        # 参数缩小10倍
        inner_center = (self.inner_center_x / 10.0, self.inner_center_y / 10.0)
        outer_center = (self.outer_center_x / 10.0, self.outer_center_y / 10.0)
        inner_length = self.inner_length / 10.0
        inner_width = self.inner_width / 10.0
        inner_chamfer_size = self.inner_chamfer_size / 10.0
        inner_chamfer_type = self.inner_chamfer_type
        inner_corner_pts = self.inner_corner_pts

        outer_length = self.outer_length / 10.0
        outer_width = self.outer_width / 10.0
        outer_chamfer_size = self.outer_chamfer_size / 10.0
        outer_chamfer_type = self.outer_chamfer_type
        outer_corner_pts = self.outer_corner_pts

        fanout_type = self.fanout_type
        lead_line_width = self.lead_line_width / 10.0
        lead_corner_type = self.lead_corner_type
        lead_chamfer_size = self.lead_chamfer_size / 10.0

        inner_edge = self.inner_edge if self.inner_edge else None
        outer_edge = self.outer_edge if self.outer_edge else None

        chamfer_map = {0: 'none', 1: 'straight', 2: 'round'}
        lead_corner_type_map = {0: 'right_angle', 1: 'straight_chamfer', 2: 'round_chamfer'}

        # 生成 inner/outer pad
        inner_pad = draw_pad(inner_center, inner_length, inner_width, chamfer_size=inner_chamfer_size, chamfer_type=chamfer_map.get(inner_chamfer_type, 'none'), corner_pts=inner_corner_pts)
        outer_pad = draw_pad(outer_center, outer_length, outer_width, chamfer_size=outer_chamfer_size, chamfer_type=chamfer_map.get(outer_chamfer_type, 'straight'), corner_pts=outer_corner_pts)

        # 生成 fanout
        if fanout_type == 0:
            # Trapezoidal
            fanout = draw_trapezoidal_fanout(inner_pad, outer_pad, inner_edge=inner_edge, outer_edge=outer_edge)
        else:
            fanout = draw_lead_fanout(
                inner_pad, outer_pad,
                line_width=lead_line_width,
                corner_type=lead_corner_type_map.get(lead_corner_type, 'right_angle'),
                chamfer_size=lead_chamfer_size
            )

        # 插入 inner pad
        if hasattr(inner_pad, 'polygon'):
            cell.shapes(layer).insert(inner_pad.polygon)
        elif isinstance(inner_pad, list):
            for poly in inner_pad:
                cell.shapes(layer).insert(poly)

        # 插入 outer pad
        if hasattr(outer_pad, 'polygon'):
            cell.shapes(layer).insert(outer_pad.polygon)
        elif isinstance(outer_pad, list):
            for poly in outer_pad:
                cell.shapes(layer).insert(poly)

        # 插入 fanout
        if isinstance(fanout, list):
            for poly in fanout:
                cell.shapes(layer).insert(poly)
        elif hasattr(fanout, 'polygon'):
            cell.shapes(layer).insert(fanout.polygon)
        else:
            cell.shapes(layer).insert(fanout) 