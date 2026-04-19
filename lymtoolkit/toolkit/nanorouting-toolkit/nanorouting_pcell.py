import os
import sys

import pya


def _discover_root_dir():
    current = os.path.abspath(os.path.dirname(__file__))
    candidates = [
        current,
        os.path.abspath(os.path.join(current, "..")),
        os.path.abspath(os.path.join(current, "..", "..")),
        os.path.abspath(os.path.join(current, "..", "..", "..")),
    ]
    for candidate in candidates:
        if (
            os.path.exists(os.path.join(candidate, "config.py"))
            and os.path.isdir(os.path.join(candidate, "components"))
            and os.path.isdir(os.path.join(candidate, "utils"))
        ):
            return candidate
    return os.path.abspath(os.path.join(current, "..", "..", ".."))


ROOT_DIR = _discover_root_dir()
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config import LAYER_DEFINITIONS
from components.routing import Routing


def _parse_points(value):
    points = []
    for item in (value or "").split(";"):
        item = item.strip()
        if not item:
            continue
        x_str, y_str = [part.strip() for part in item.split(",")[:2]]
        points.append((float(x_str), float(y_str)))
    return points


def _parse_rects(value):
    rects = []
    for item in (value or "").split(";"):
        item = item.strip()
        if not item:
            continue
        x1, y1, x2, y2 = [float(part.strip()) for part in item.split(",")[:4]]
        rects.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2})
    return rects


class _BaseRoutingPCell(pya.PCellDeclarationHelper):
    def _coerce_layer_name(self, layer_name):
        if layer_name in LAYER_DEFINITIONS:
            return layer_name
        return "routing"


class NanoRoutingPathPCell(_BaseRoutingPCell):
    def __init__(self):
        super().__init__()
        self.param("layer_name", self.TypeString, "Layer name", default="routing")
        self.param("start_x", self.TypeDouble, "Start X", default=0.0)
        self.param("start_y", self.TypeDouble, "Start Y", default=0.0)
        self.param("end_x", self.TypeDouble, "End X", default=100.0)
        self.param("end_y", self.TypeDouble, "End Y", default=0.0)
        self.param("waypoints", self.TypeString, "Waypoints x,y;x,y", default="")
        self.param("avoid_regions", self.TypeString, "Avoid x1,y1,x2,y2;...", default="")
        self.param("line_width", self.TypeDouble, "Line width", default=2.0)
        self.param("route_mode", self.TypeString, "Route mode", default="manhattan")
        self.param("extension_type", self.TypeString, "Extension type", default="flush")
        self.param("clearance", self.TypeDouble, "Clearance", default=0.0)

    def display_text_impl(self):
        return "NanoRoutingPath"

    def coerce_parameters_impl(self):
        if self.line_width <= 0:
            self.line_width = 0.1

    def produce_impl(self):
        routing = Routing(layout=self.layout, layer_name=self._coerce_layer_name(self.layer_name))
        routing.insert_route(
            self.cell,
            start=(self.start_x, self.start_y),
            end=(self.end_x, self.end_y),
            waypoints=_parse_points(self.waypoints),
            avoid_regions=_parse_rects(self.avoid_regions),
            line_width=self.line_width,
            route_mode=self.route_mode,
            extension_type=self.extension_type,
            clearance=self.clearance,
        )


class NanoRoutingBundlePCell(_BaseRoutingPCell):
    def __init__(self):
        super().__init__()
        self.param("layer_name", self.TypeString, "Layer name", default="routing")
        self.param("start_points", self.TypeString, "Start points x,y;x,y", default="0,0;20,0")
        self.param("end_points", self.TypeString, "End points x,y;x,y", default="0,-100;20,-100")
        self.param("avoid_regions", self.TypeString, "Avoid x1,y1,x2,y2;...", default="")
        self.param("line_width", self.TypeDouble, "Line width", default=2.0)
        self.param("min_line_width", self.TypeDouble, "Min line width", default=2.0)
        self.param("bundle_spacing", self.TypeDouble, "Bundle spacing", default=6.0)
        self.param("route_mode", self.TypeString, "Route mode", default="manhattan")
        self.param("extension_type", self.TypeString, "Extension type", default="flush")
        self.param("clearance", self.TypeDouble, "Clearance", default=2.0)

    def display_text_impl(self):
        return "NanoRoutingBundle"

    def coerce_parameters_impl(self):
        if self.line_width <= 0:
            self.line_width = 0.1
        if self.min_line_width <= 0:
            self.min_line_width = self.line_width
        if self.bundle_spacing <= 0:
            self.bundle_spacing = self.line_width + max(self.clearance, 0.0)

    def produce_impl(self):
        routing = Routing(layout=self.layout, layer_name=self._coerce_layer_name(self.layer_name))
        start_points = _parse_points(self.start_points)
        end_points = _parse_points(self.end_points)
        widths = [self.line_width for _ in start_points]
        routing.insert_parallel_routes(
            self.cell,
            start_points=start_points,
            end_points=end_points,
            avoid_regions=_parse_rects(self.avoid_regions),
            line_width=widths,
            min_line_width=self.min_line_width,
            bundle_spacing=self.bundle_spacing,
            route_mode=self.route_mode,
            extension_type=self.extension_type,
            clearance=self.clearance,
        )
