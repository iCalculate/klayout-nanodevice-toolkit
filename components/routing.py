# -*- coding: utf-8 -*-
"""
Routing component module.
"""

from __future__ import annotations

import os
import sys
from typing import Optional, Sequence

import klayout.db as db

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import LAYER_DEFINITIONS
from utils.geometry import GeometryUtils
from utils.routing_utils import RouteResult, RoutingUtils


class Routing:
    """General-purpose routing component for single and bundled wires."""

    def __init__(self, layout: Optional[db.Layout] = None, layer_name: str = "routing", **kwargs):
        self.layout = layout or db.Layout()
        self.layout.dbu = kwargs.get("dbu", self.layout.dbu or 0.001)
        GeometryUtils.UNIT_SCALE = kwargs.get("unit_scale", GeometryUtils.UNIT_SCALE)
        self.layer_name = layer_name
        self.layer_id = LAYER_DEFINITIONS[layer_name]["id"]
        self.layer_index: Optional[int] = None
        self.setup_layers()

    def setup_layers(self) -> None:
        for name, layer_info in LAYER_DEFINITIONS.items():
            layer_index = self.layout.layer(layer_info["id"], 0)
            if name == self.layer_name:
                self.layer_index = layer_index

        if self.layer_index is None:
            self.layer_index = self.layout.layer(LAYER_DEFINITIONS[self.layer_name]["id"], 0)

    def route(
        self,
        start,
        end,
        waypoints: Optional[Sequence[object]] = None,
        line_width: float = 1.0,
        end_width: Optional[float] = None,
        width_profile: Optional[Sequence[tuple]] = None,
        route_mode: str = "manhattan",
        corner_style: str = "manhattan",
        corner_size: Optional[float] = None,
        avoid_regions: Optional[Sequence[object]] = None,
        clearance: float = 0.0,
        start_port: Optional[dict] = None,
        end_port: Optional[dict] = None,
        smoothing_points: int = 12,
        begin_extension: Optional[float] = None,
        end_extension: Optional[float] = None,
        extension_type: str = "flush",
        turn_offset: float = 0.0,
        turn_pattern: str = "auto",
    ) -> RouteResult:
        return RoutingUtils.build_route(
            start=start,
            end=end,
            waypoints=waypoints,
            line_width=line_width,
            end_width=end_width,
            width_profile=width_profile,
            route_mode=route_mode,
            corner_style=corner_style,
            corner_size=corner_size,
            start_port=start_port,
            end_port=end_port,
            avoid_regions=avoid_regions,
            clearance=clearance,
            smoothing_points=smoothing_points,
            begin_extension=begin_extension,
            end_extension=end_extension,
            extension_type=extension_type,
            turn_offset=turn_offset,
            turn_pattern=turn_pattern,
        )

    def route_parallel(
        self,
        start_points: Sequence[object],
        end_points: Sequence[object],
        shared_waypoints: Optional[Sequence[object]] = None,
        line_width: float = 1.0,
        end_width: Optional[float] = None,
        min_line_width: Optional[float] = None,
        bundle_spacing: Optional[float] = None,
        route_mode: str = "manhattan",
        corner_style: str = "manhattan",
        corner_size: Optional[float] = None,
        avoid_regions: Optional[Sequence[object]] = None,
        clearance: float = 0.0,
        start_ports: Optional[Sequence[Optional[dict]]] = None,
        end_ports: Optional[Sequence[Optional[dict]]] = None,
        smoothing_points: int = 12,
        begin_extension: Optional[float] = None,
        end_extension: Optional[float] = None,
        extension_type: str = "flush",
        turn_offset: float = 0.0,
        turn_pattern: str = "auto",
    ) -> Sequence[RouteResult]:
        return RoutingUtils.build_parallel_routes(
            start_points=start_points,
            end_points=end_points,
            shared_waypoints=shared_waypoints,
            line_width=line_width,
            end_width=end_width,
            min_line_width=min_line_width,
            bundle_spacing=bundle_spacing,
            route_mode=route_mode,
            corner_style=corner_style,
            corner_size=corner_size,
            start_ports=start_ports,
            end_ports=end_ports,
            avoid_regions=avoid_regions,
            clearance=clearance,
            smoothing_points=smoothing_points,
            begin_extension=begin_extension,
            end_extension=end_extension,
            extension_type=extension_type,
            turn_offset=turn_offset,
            turn_pattern=turn_pattern,
        )

    def insert_route(self, cell: db.Cell, **kwargs) -> RouteResult:
        result = self.route(**kwargs)
        for shape in result.shapes:
            cell.shapes(self.layer_index).insert(shape)
        return result

    def insert_parallel_routes(self, cell: db.Cell, **kwargs) -> Sequence[RouteResult]:
        results = self.route_parallel(**kwargs)
        for result in results:
            for shape in result.shapes:
                cell.shapes(self.layer_index).insert(shape)
        return results

    def insert_box_marker(
        self,
        cell: db.Cell,
        point,
        size: float = 6.0,
        layer_name: str = "note",
    ) -> object:
        layer_index = self.layout.layer(LAYER_DEFINITIONS[layer_name]["id"], 0)
        x, y = RoutingUtils._to_point(point)
        shape = GeometryUtils.create_rectangle(x, y, size, size, center=True)
        cell.shapes(layer_index).insert(shape)
        return shape

    def insert_obstacle_box(
        self,
        cell: db.Cell,
        center,
        width: float,
        height: float,
        layer_name: str = "note",
    ) -> object:
        layer_index = self.layout.layer(LAYER_DEFINITIONS[layer_name]["id"], 0)
        x, y = RoutingUtils._to_point(center)
        shape = GeometryUtils.create_rectangle(x, y, width, height, center=True)
        cell.shapes(layer_index).insert(shape)
        return shape

    def insert_note_text(
        self,
        cell: db.Cell,
        text: str,
        x: float,
        y: float,
        layer_name: str = "note",
    ) -> object:
        layer_index = self.layout.layer(LAYER_DEFINITIONS[layer_name]["id"], 0)
        text_shape = db.Text(text, int(round(x * GeometryUtils.UNIT_SCALE)), int(round(y * GeometryUtils.UNIT_SCALE)))
        cell.shapes(layer_index).insert(text_shape)
        return text_shape


def main() -> None:
    from config import get_gds_path

    routing = Routing()
    top = routing.layout.create_cell("ROUTING_DEMO")

    routing.insert_note_text(top, "P2P Diagonal", -10.0, 16.0)
    p2p_start = (0.0, 0.0)
    p2p_end = (70.0, 30.0)
    routing.insert_box_marker(top, p2p_start)
    routing.insert_box_marker(top, p2p_end)
    routing.insert_route(
        top,
        start=p2p_start,
        end=p2p_end,
        line_width=4.0,
        route_mode="diagonal",
        extension_type="half_width",
    )

    routing.insert_note_text(top, "P2P Manhattan", 110.0, 16.0)
    p2p_m_start = (120.0, 0.0)
    p2p_m_end = (190.0, 30.0)
    routing.insert_box_marker(top, p2p_m_start)
    routing.insert_box_marker(top, p2p_m_end)
    routing.insert_route(
        top,
        start=p2p_m_start,
        end=p2p_m_end,
        line_width=4.0,
        route_mode="manhattan",
        extension_type="half_width",
    )

    routing.insert_note_text(top, "Via Diagonal", -10.0, -54.0)
    via_start = (0.0, -70.0)
    via_end = (90.0, -70.0)
    via_points = [(28.0, -40.0), (58.0, -92.0)]
    routing.insert_box_marker(top, via_start)
    routing.insert_box_marker(top, via_end)
    for point in via_points:
        routing.insert_box_marker(top, point, size=4.0)
    routing.insert_route(
        top,
        start=via_start,
        end=via_end,
        waypoints=via_points,
        line_width=4.0,
        route_mode="diagonal",
        extension_type="flush",
    )

    routing.insert_note_text(top, "Via Manhattan", 120.0, -54.0)
    via_m_start = (120.0, -70.0)
    via_m_end = (210.0, -70.0)
    via_m_points = [(150.0, -40.0), (180.0, -92.0)]
    routing.insert_box_marker(top, via_m_start)
    routing.insert_box_marker(top, via_m_end)
    for point in via_m_points:
        routing.insert_box_marker(top, point, size=4.0)
    routing.insert_route(
        top,
        start=via_m_start,
        end=via_m_end,
        waypoints=via_m_points,
        line_width=4.0,
        route_mode="manhattan",
        extension_type="flush",
    )

    routing.insert_note_text(top, "Obstacle Manhattan", -10.0, -144.0)
    obstacle_center = (45.0, -200.0)
    obstacle_width = 24.0
    obstacle_height = 24.0
    block_start = (0.0, -200.0)
    block_end = (90.0, -200.0)
    routing.insert_box_marker(top, block_start)
    routing.insert_box_marker(top, block_end)
    routing.insert_obstacle_box(top, obstacle_center, obstacle_width, obstacle_height)
    routing.insert_route(
        top,
        start=block_start,
        end=block_end,
        line_width=4.0,
        route_mode="manhattan",
        avoid_regions=[{"x": obstacle_center[0], "y": obstacle_center[1], "width": obstacle_width, "height": obstacle_height}],
        clearance=6.0,
        extension_type="half_width",
    )

    routing.insert_note_text(top, "Parallel Manhattan Bundle", 120.0, -144.0)
    multi_starts = [(250.0, 35.0), (250.0, 15.0), (250.0, -5.0)]
    multi_ends = [(120.0, -175.0), (120.0, -215.0), (120.0, -245.0)]
    multi_waypoints = [(155.0, -226.0), (155.0, -172.0), (225.0, -172.0), (225.0, -226.0)]
    for point in multi_starts + multi_ends:
        routing.insert_box_marker(top, point)
    routing.insert_parallel_routes(
        top,
        start_points=multi_starts,
        end_points=multi_ends,
        line_width=[3.0, 3.0, 3.0],
        min_line_width=2.0,
        bundle_spacing=7.0,
        route_mode="manhattan",
        extension_type="flush",
        clearance=4.0,
    )

    routing.insert_note_text(top, "Obstacle Bundle Manhattan", -10.0, 80.0)
    obstacle_bundle_starts = [(75.0, 65.0), (105.0, 65.0), (135.0, 65.0), (165.0, 65.0)]
    obstacle_bundle_ends = [(75.0, -270.0), (105.0, -270.0), (135.0, -270.0), (165.0, -270.0)]
    obstacle_bundle_box = {"x1": -20.0, "y1": -250.0, "x2": 260.0, "y2": 50.0}
    for point in obstacle_bundle_starts + obstacle_bundle_ends:
        routing.insert_box_marker(top, point)
    routing.insert_obstacle_box(
        top,
        center=((obstacle_bundle_box["x1"] + obstacle_bundle_box["x2"]) / 2.0, (obstacle_bundle_box["y1"] + obstacle_bundle_box["y2"]) / 2.0),
        width=obstacle_bundle_box["x2"] - obstacle_bundle_box["x1"],
        height=obstacle_bundle_box["y2"] - obstacle_bundle_box["y1"],
    )
    routing.insert_parallel_routes(
        top,
        start_points=obstacle_bundle_starts,
        end_points=obstacle_bundle_ends,
        line_width=[3.0, 3.0, 3.0, 3.0],
        min_line_width=3.0,
        bundle_spacing=8.0,
        route_mode="manhattan",
        avoid_regions=[obstacle_bundle_box],
        extension_type="flush",
        clearance=5.0,
    )

    routing.insert_note_text(top, "Row Bundle Validation", 360.0, 120.0)
    row_bundle_starts = [(-220.0, 280.0), (-160.0, 280.0), (-100.0, 280.0), (-40.0, 280.0), (20.0, 280.0)]
    row_bundle_ends = [(-100.0, -70.0), (20.0, -70.0), (140.0, -70.0), (260.0, -70.0), (380.0, -70.0)]
    for point in row_bundle_starts + row_bundle_ends:
        routing.insert_box_marker(top, point, size=8.0)
    row_results = routing.insert_parallel_routes(
        top,
        start_points=row_bundle_starts,
        end_points=row_bundle_ends,
        line_width=[24.0, 24.0, 24.0, 24.0, 24.0],
        min_line_width=24.0,
        bundle_spacing=24.0,
        route_mode="manhattan",
        extension_type="flush",
        clearance=19.0,
    )

    row_region = db.Region()
    row_total_area = 0
    for result in row_results:
        for shape in result.shapes:
            polygon = shape.polygon() if hasattr(shape, "polygon") else shape
            row_region.insert(polygon)
            row_total_area += polygon.area()
    row_overlap_area = row_total_area - row_region.merged().area()
    print(f"Row bundle validation overlap area: {row_overlap_area}")

    routing.insert_note_text(top, "Mixed Row Bundle Validation", 720.0, 120.0)
    mixed_starts = [(-110.0, 200.0), (-90.0, 200.0), (-70.0, 200.0), (-50.0, 200.0), (-30.0, 200.0), (30.0, 200.0), (50.0, 200.0), (70.0, 200.0), (90.0, 200.0), (110.0, 200.0)]
    mixed_ends = [(-1105.0, -500.0), (-905.0, -500.0), (-705.0, -500.0), (-505.0, -500.0), (-305.0, -500.0), (305.0, -500.0), (505.0, -500.0), (705.0, -500.0), (905.0, -500.0), (1105.0, -500.0)]
    mixed_starts = [(x + 820.0, y) for x, y in mixed_starts]
    mixed_ends = [(x + 820.0, y) for x, y in mixed_ends]
    for point in mixed_starts + mixed_ends:
        routing.insert_box_marker(top, point, size=8.0)
    mixed_results = routing.insert_parallel_routes(
        top,
        start_points=mixed_starts,
        end_points=mixed_ends,
        line_width=[8.1] * len(mixed_starts),
        min_line_width=8.1,
        bundle_spacing=17.1,
        route_mode="manhattan",
        extension_type="half_width",
        clearance=0.0,
    )

    mixed_region = db.Region()
    mixed_total_area = 0
    for result in mixed_results:
        for shape in result.shapes:
            polygon = shape.polygon() if hasattr(shape, "polygon") else shape
            mixed_region.insert(polygon)
            mixed_total_area += polygon.area()
    mixed_overlap_area = mixed_total_area - mixed_region.merged().area()
    print(f"Mixed row bundle validation overlap area: {mixed_overlap_area}")

    routing.insert_note_text(top, "Exact GUI Bundle Validation", 720.0, 320.0)
    exact_starts = [(-90.0, 240.0), (10.0, 240.0), (110.0, 240.0), (210.0, 240.0)]
    exact_ends = [(-540.0, 10.0), (-140.0, 10.0), (260.0, 10.0), (660.0, 10.0)]
    exact_starts = [(x + 820.0, y + 200.0) for x, y in exact_starts]
    exact_ends = [(x + 820.0, y + 200.0) for x, y in exact_ends]
    for point in exact_starts + exact_ends:
        routing.insert_box_marker(top, point, size=8.0)
    exact_results = routing.insert_parallel_routes(
        top,
        start_points=exact_starts,
        end_points=exact_ends,
        line_width=[8.1] * len(exact_starts),
        min_line_width=8.1,
        bundle_spacing=17.1,
        route_mode="manhattan",
        extension_type="half_width",
        clearance=0.0,
    )

    exact_region = db.Region()
    exact_total_area = 0
    for result in exact_results:
        for shape in result.shapes:
            polygon = shape.polygon() if hasattr(shape, "polygon") else shape
            exact_region.insert(polygon)
            exact_total_area += polygon.area()
    exact_overlap_area = exact_total_area - exact_region.merged().area()
    print(f"Exact GUI bundle validation overlap area: {exact_overlap_area}")

    output_file = get_gds_path("TEST_ROUTING.gds")
    routing.layout.write(output_file)
    print(f"Routing demo written to: {output_file}")


if __name__ == "__main__":
    main()
