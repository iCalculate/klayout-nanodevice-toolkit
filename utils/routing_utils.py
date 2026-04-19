# -*- coding: utf-8 -*-
"""
Routing utility helpers for KLayout Path-based routing.
"""

from __future__ import annotations

import math
import heapq
import os
import site
import importlib
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

import klayout.db as db

from utils.geometry import GeometryUtils


Point2D = Tuple[float, float]


@dataclass
class RouteResult:
    """Container for a routed path and its centerline."""

    shapes: List[object]
    points: List[Point2D]
    width: float
    begin_extension: float
    end_extension: float


class RoutingUtils:
    """Routing helpers built on top of native KLayout Path objects."""

    @staticmethod
    def build_route(
        start: Point2D,
        end: Point2D,
        waypoints: Optional[Sequence[Point2D]] = None,
        line_width: float = 1.0,
        end_width: Optional[float] = None,
        width_profile: Optional[Sequence[Tuple[float, float]]] = None,
        route_mode: str = "manhattan",
        corner_style: str = "manhattan",
        corner_size: Optional[float] = None,
        start_port: Optional[dict] = None,
        end_port: Optional[dict] = None,
        avoid_regions: Optional[Sequence[object]] = None,
        clearance: float = 0.0,
        smoothing_points: int = 12,
        begin_extension: Optional[float] = None,
        end_extension: Optional[float] = None,
        extension_type: str = "flush",
    ) -> RouteResult:
        """
        Create a single routed path.

        Notes:
        - Gradient width is intentionally ignored for native Path routing.
        - corner_style is treated as route topology selector and only supports
          'manhattan' or 'diagonal'.
        """
        del end_width, width_profile, corner_size, smoothing_points

        mode = RoutingUtils._normalize_route_mode(route_mode, corner_style)

        control_points = [RoutingUtils._to_point(start)]
        control_points.extend(RoutingUtils._to_point(pt) for pt in (waypoints or []))
        control_points.append(RoutingUtils._to_point(end))

        control_points = RoutingUtils._apply_ports(control_points, start_port, end_port)
        points = RoutingUtils._build_mode_polyline(control_points, mode)
        points = RoutingUtils._dedupe_points(points)

        if avoid_regions:
            obstacles = [
                RoutingUtils._normalize_obstacle(obstacle, clearance + line_width / 2.0)
                for obstacle in avoid_regions
            ]
        else:
            obstacles = []

        points = RoutingUtils._avoid_obstacles(points, obstacles, mode)
        points = RoutingUtils._dedupe_points(points)
        bgn_ext, end_ext = RoutingUtils._resolve_extensions(
            line_width=line_width,
            extension_type=extension_type,
            begin_extension=begin_extension,
            end_extension=end_extension,
            start_port=start_port,
            end_port=end_port,
        )
        shapes = [RoutingUtils._polyline_to_path(points, line_width, bgn_ext, end_ext)]
        return RouteResult(
            shapes=shapes,
            points=points,
            width=float(line_width),
            begin_extension=bgn_ext,
            end_extension=end_ext,
        )

    @staticmethod
    def build_parallel_routes(
        start_points: Sequence[Point2D],
        end_points: Sequence[Point2D],
        shared_waypoints: Optional[Sequence[Point2D]] = None,
        line_width: float = 1.0,
        end_width: Optional[float] = None,
        min_line_width: Optional[float] = None,
        bundle_spacing: Optional[float] = None,
        route_mode: str = "manhattan",
        corner_style: str = "manhattan",
        corner_size: Optional[float] = None,
        start_ports: Optional[Sequence[Optional[dict]]] = None,
        end_ports: Optional[Sequence[Optional[dict]]] = None,
        avoid_regions: Optional[Sequence[object]] = None,
        clearance: float = 0.0,
        smoothing_points: int = 12,
        begin_extension: Optional[float] = None,
        end_extension: Optional[float] = None,
        extension_type: str = "flush",
    ) -> List[RouteResult]:
        """Create a parallel route bundle using shared intermediate waypoints."""
        del end_width, corner_size, smoothing_points

        if len(start_points) != len(end_points):
            raise ValueError("start_points and end_points must have the same length")
        if not start_points:
            return []

        mode = RoutingUtils._normalize_route_mode(route_mode, corner_style)
        route_count = len(start_points)
        widths = RoutingUtils._expand_width_list(line_width, route_count)

        if min_line_width is not None:
            widths = [max(width, min_line_width) for width in widths]

        pitch = bundle_spacing
        if pitch is None:
            max_width = max(widths)
            pitch = max_width + max(clearance, 0.0)

        if not shared_waypoints and mode == "manhattan":
            return RoutingUtils._build_parallel_manhattan_shortest_routes(
                start_points=start_points,
                end_points=end_points,
                widths=widths,
                pitch=pitch,
                clearance=clearance,
                obstacles=[RoutingUtils._normalize_obstacle(obstacle, clearance) for obstacle in (avoid_regions or [])],
                begin_extension=begin_extension,
                end_extension=end_extension,
                extension_type=extension_type,
            )

        base_points = [RoutingUtils._mean_point(start_points)]
        base_points.extend(RoutingUtils._to_point(pt) for pt in (shared_waypoints or []))
        base_points.append(RoutingUtils._mean_point(end_points))
        base_points = RoutingUtils._build_mode_polyline(base_points, mode)
        base_points = RoutingUtils._dedupe_points(base_points)

        results: List[RouteResult] = []
        centers = RoutingUtils._bundle_offsets(route_count, pitch)
        for index in range(route_count):
            route_waypoints: List[Point2D] = []
            if shared_waypoints:
                route_waypoints = RoutingUtils._offset_polyline(base_points, centers[index])[1:-1]

            result = RoutingUtils.build_route(
                start=RoutingUtils._to_point(start_points[index]),
                end=RoutingUtils._to_point(end_points[index]),
                waypoints=route_waypoints,
                line_width=widths[index],
                route_mode=mode,
                corner_style=mode,
                start_port=(start_ports[index] if start_ports and index < len(start_ports) else None),
                end_port=(end_ports[index] if end_ports and index < len(end_ports) else None),
                avoid_regions=avoid_regions,
                clearance=clearance,
                begin_extension=begin_extension,
                end_extension=end_extension,
                extension_type=extension_type,
            )
            results.append(result)

        return results

    @staticmethod
    def _normalize_route_mode(route_mode: str, corner_style: str) -> str:
        mode = (route_mode or corner_style or "manhattan").lower()
        if mode in {"orthogonal", "manhattan"}:
            return "manhattan"
        if mode in {"diagonal", "45", "direct"}:
            return "diagonal"
        raise ValueError("route_mode must be 'manhattan' or 'diagonal'")

    @staticmethod
    def _resolve_extensions(
        line_width: float,
        extension_type: str,
        begin_extension: Optional[float],
        end_extension: Optional[float],
        start_port: Optional[dict],
        end_port: Optional[dict],
    ) -> Tuple[float, float]:
        if begin_extension is not None or end_extension is not None:
            return (
                float(begin_extension or 0.0),
                float(end_extension or 0.0),
            )

        if start_port and "extension" in start_port:
            begin_extension = float(start_port["extension"])
        if end_port and "extension" in end_port:
            end_extension = float(end_port["extension"])
        if begin_extension is not None or end_extension is not None:
            return (
                float(begin_extension or 0.0),
                float(end_extension or 0.0),
            )

        ext = (extension_type or "flush").lower()
        if ext == "flush":
            return (0.0, 0.0)
        if ext in {"half_width", "half"}:
            half = float(line_width) / 2.0
            return (half, half)
        raise ValueError("extension_type must be 'flush' or 'half_width'")

    @staticmethod
    def _to_point(value: object) -> Point2D:
        if isinstance(value, dict):
            if "point" in value:
                return RoutingUtils._to_point(value["point"])
            return (float(value["x"]), float(value["y"]))
        if hasattr(value, "x") and hasattr(value, "y"):
            return (float(value.x), float(value.y))
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            return (float(value[0]), float(value[1]))
        raise ValueError(f"Unsupported point value: {value}")

    @staticmethod
    def _apply_ports(
        points: Sequence[Point2D],
        start_port: Optional[dict],
        end_port: Optional[dict],
    ) -> List[Point2D]:
        routed = list(points)
        if start_port:
            start = routed[0]
            direction = RoutingUtils._port_direction(start_port)
            lead_in = float(start_port.get("lead_in", 0.0))
            if lead_in > 0:
                routed.insert(1, (start[0] + direction[0] * lead_in, start[1] + direction[1] * lead_in))
        if end_port:
            end = routed[-1]
            direction = RoutingUtils._port_direction(end_port)
            lead_in = float(end_port.get("lead_in", 0.0))
            if lead_in > 0:
                routed.insert(-1, (end[0] - direction[0] * lead_in, end[1] - direction[1] * lead_in))
        return routed

    @staticmethod
    def _port_direction(port: dict) -> Point2D:
        direction = port.get("direction", (1.0, 0.0))
        if isinstance(direction, str):
            mapping = {
                "right": (1.0, 0.0),
                "east": (1.0, 0.0),
                "left": (-1.0, 0.0),
                "west": (-1.0, 0.0),
                "up": (0.0, 1.0),
                "north": (0.0, 1.0),
                "down": (0.0, -1.0),
                "south": (0.0, -1.0),
            }
            return mapping.get(direction.lower(), (1.0, 0.0))
        vector = RoutingUtils._to_point(direction)
        norm = math.hypot(vector[0], vector[1])
        if norm == 0:
            return (1.0, 0.0)
        return (vector[0] / norm, vector[1] / norm)

    @staticmethod
    def _expand_route_mode(points: Sequence[Point2D], route_mode: str) -> List[Point2D]:
        return RoutingUtils._build_mode_polyline(points, route_mode)

    @staticmethod
    def _build_mode_polyline(points: Sequence[Point2D], route_mode: str) -> List[Point2D]:
        if len(points) <= 1:
            return list(points)

        polyline: List[Point2D] = [points[0]]
        for target in points[1:]:
            segment_points = RoutingUtils._best_segment_expansion(polyline, target, route_mode)
            polyline.extend(segment_points[1:])
        return RoutingUtils._dedupe_points(polyline)

    @staticmethod
    def _best_segment_expansion(
        existing_points: Sequence[Point2D],
        target: Point2D,
        route_mode: str,
    ) -> List[Point2D]:
        start = existing_points[-1]
        candidates = RoutingUtils._segment_candidates(start, target, route_mode)
        if not candidates:
            return [start, target]

        best_candidate = candidates[0]
        best_score = float("inf")
        for candidate in candidates:
            combined = list(existing_points[:-1]) + candidate
            penalty = RoutingUtils._polyline_conflict_penalty(combined)
            score = RoutingUtils._polyline_length(candidate) + penalty
            if score < best_score:
                best_score = score
                best_candidate = candidate
        return best_candidate

    @staticmethod
    def _segment_candidates(start: Point2D, end: Point2D, route_mode: str) -> List[List[Point2D]]:
        ax, ay = start
        bx, by = end
        dx = bx - ax
        dy = by - ay
        if abs(dx) < 1e-9 and abs(dy) < 1e-9:
            return [[start]]

        if route_mode == "manhattan":
            candidates = []
            if abs(dx) < 1e-9 or abs(dy) < 1e-9:
                candidates.append([start, end])
            else:
                candidates.append([start, (bx, ay), end])
                candidates.append([start, (ax, by), end])
            return [RoutingUtils._dedupe_points(candidate) for candidate in candidates]

        candidates: List[List[Point2D]] = []
        adx = abs(dx)
        ady = abs(dy)
        sx = 1.0 if dx >= 0 else -1.0
        sy = 1.0 if dy >= 0 else -1.0

        if abs(adx - ady) < 1e-9:
            candidates.append([start, end])
            return candidates

        d = min(adx, ady)
        diag_end_from_start = (ax + sx * d, ay + sy * d)
        if adx > ady:
            candidates.append([start, diag_end_from_start, end])
            axis_first = (bx - sx * d, ay)
            candidates.append([start, axis_first, end])
        else:
            candidates.append([start, diag_end_from_start, end])
            axis_first = (ax, by - sy * d)
            candidates.append([start, axis_first, end])

        if abs(dx) > 1e-9 and abs(dy) > 1e-9:
            if adx > ady:
                candidates.append([start, (ax + dx - sx * d, ay), end])
            elif ady > adx:
                candidates.append([start, (ax, ay + dy - sy * d), end])
        return [RoutingUtils._dedupe_points(candidate) for candidate in candidates]

    @staticmethod
    def _polyline_conflict_penalty(points: Sequence[Point2D]) -> float:
        penalty = 0.0
        segments = [(points[index - 1], points[index]) for index in range(1, len(points))]
        for i in range(len(segments)):
            for j in range(i + 1):
                if j >= i - 1:
                    continue
                if RoutingUtils._segments_conflict(segments[i], segments[j]):
                    penalty += 1e6
        return penalty

    @staticmethod
    def _segments_conflict(
        seg_a: Tuple[Point2D, Point2D],
        seg_b: Tuple[Point2D, Point2D],
    ) -> bool:
        a0, a1 = seg_a
        b0, b1 = seg_b
        if RoutingUtils._points_close(a0, b0) or RoutingUtils._points_close(a0, b1) or RoutingUtils._points_close(a1, b0) or RoutingUtils._points_close(a1, b1):
            return False
        return RoutingUtils._segments_intersect(seg_a, seg_b)

    @staticmethod
    def _segments_intersect(
        seg_a: Tuple[Point2D, Point2D],
        seg_b: Tuple[Point2D, Point2D],
    ) -> bool:
        p1, p2 = seg_a
        q1, q2 = seg_b

        def orient(a: Point2D, b: Point2D, c: Point2D) -> float:
            return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

        def on_segment(a: Point2D, b: Point2D, c: Point2D) -> bool:
            return (
                min(a[0], b[0]) - 1e-9 <= c[0] <= max(a[0], b[0]) + 1e-9
                and min(a[1], b[1]) - 1e-9 <= c[1] <= max(a[1], b[1]) + 1e-9
            )

        o1 = orient(p1, p2, q1)
        o2 = orient(p1, p2, q2)
        o3 = orient(q1, q2, p1)
        o4 = orient(q1, q2, p2)

        if (o1 > 1e-9 and o2 < -1e-9 or o1 < -1e-9 and o2 > 1e-9) and (
            o3 > 1e-9 and o4 < -1e-9 or o3 < -1e-9 and o4 > 1e-9
        ):
            return True

        if abs(o1) <= 1e-9 and on_segment(p1, p2, q1):
            return True
        if abs(o2) <= 1e-9 and on_segment(p1, p2, q2):
            return True
        if abs(o3) <= 1e-9 and on_segment(q1, q2, p1):
            return True
        if abs(o4) <= 1e-9 and on_segment(q1, q2, p2):
            return True
        return False

    @staticmethod
    def _points_close(a: Point2D, b: Point2D) -> bool:
        return abs(a[0] - b[0]) < 1e-9 and abs(a[1] - b[1]) < 1e-9

    @staticmethod
    def _normalize_obstacle(obstacle: object, margin: float) -> Tuple[float, float, float, float]:
        if isinstance(obstacle, dict):
            if {"x1", "y1", "x2", "y2"} <= set(obstacle.keys()):
                x1, y1, x2, y2 = obstacle["x1"], obstacle["y1"], obstacle["x2"], obstacle["y2"]
            elif {"x", "y", "width", "height"} <= set(obstacle.keys()):
                x = float(obstacle["x"])
                y = float(obstacle["y"])
                width = float(obstacle["width"])
                height = float(obstacle["height"])
                x1, y1, x2, y2 = x - width / 2.0, y - height / 2.0, x + width / 2.0, y + height / 2.0
            elif "points" in obstacle:
                xs = [RoutingUtils._to_point(pt)[0] for pt in obstacle["points"]]
                ys = [RoutingUtils._to_point(pt)[1] for pt in obstacle["points"]]
                x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
            else:
                raise ValueError(f"Unsupported obstacle definition: {obstacle}")
        elif isinstance(obstacle, (list, tuple)) and len(obstacle) == 4:
            x1, y1, x2, y2 = [float(value) for value in obstacle]
        else:
            raise ValueError(f"Unsupported obstacle definition: {obstacle}")

        return (
            min(x1, x2) - margin,
            min(y1, y2) - margin,
            max(x1, x2) + margin,
            max(y1, y2) + margin,
        )

    @staticmethod
    def _avoid_obstacles(
        points: Sequence[Point2D],
        obstacles: Sequence[Tuple[float, float, float, float]],
        route_mode: str,
    ) -> List[Point2D]:
        if route_mode != "manhattan":
            return list(points)

        refined = list(points)
        changed = True
        while changed:
            changed = False
            next_points: List[Point2D] = [refined[0]]
            for point in refined[1:]:
                segment = [next_points[-1], point]
                rerouted = False
                for obstacle in obstacles:
                    if RoutingUtils._segment_hits_box(segment[0], segment[1], obstacle):
                        detour = RoutingUtils._detour_around_box(segment[0], segment[1], obstacle)
                        next_points.extend(detour[1:])
                        rerouted = True
                        changed = True
                        break
                if not rerouted:
                    next_points.append(point)
            refined = RoutingUtils._dedupe_points(next_points)
        return refined

    @staticmethod
    def _segment_hits_box(a: Point2D, b: Point2D, box: Tuple[float, float, float, float]) -> bool:
        x1, y1, x2, y2 = box
        if abs(a[0] - b[0]) < 1e-9:
            x = a[0]
            if x < x1 or x > x2:
                return False
            low, high = sorted((a[1], b[1]))
            return not (high <= y1 or low >= y2)
        if abs(a[1] - b[1]) < 1e-9:
            y = a[1]
            if y < y1 or y > y2:
                return False
            low, high = sorted((a[0], b[0]))
            return not (high <= x1 or low >= x2)
        return False

    @staticmethod
    def _detour_around_box(a: Point2D, b: Point2D, box: Tuple[float, float, float, float]) -> List[Point2D]:
        x1, y1, x2, y2 = box
        step = max(x2 - x1, y2 - y1) * 0.25 + 1.0

        if abs(a[0] - b[0]) < 1e-9:
            left_path = [a, (x1 - step, a[1]), (x1 - step, b[1]), b]
            right_path = [a, (x2 + step, a[1]), (x2 + step, b[1]), b]
            return left_path if RoutingUtils._polyline_length(left_path) <= RoutingUtils._polyline_length(right_path) else right_path

        lower_path = [a, (a[0], y1 - step), (b[0], y1 - step), b]
        upper_path = [a, (a[0], y2 + step), (b[0], y2 + step), b]
        return lower_path if RoutingUtils._polyline_length(lower_path) <= RoutingUtils._polyline_length(upper_path) else upper_path

    @staticmethod
    def _polyline_to_path(
        points: Sequence[Point2D],
        width: float,
        begin_extension: float,
        end_extension: float,
    ) -> object:
        if len(points) == 1:
            return GeometryUtils.create_rectangle(points[0][0], points[0][1], width, width, center=True)

        dbu_points = [
            db.Point(
                int(round(point[0] * GeometryUtils.UNIT_SCALE)),
                int(round(point[1] * GeometryUtils.UNIT_SCALE)),
            )
            for point in points
        ]
        dbu_width = int(round(width * GeometryUtils.UNIT_SCALE))
        dbu_bgn_ext = int(round(begin_extension * GeometryUtils.UNIT_SCALE))
        dbu_end_ext = int(round(end_extension * GeometryUtils.UNIT_SCALE))
        return db.Path(dbu_points, dbu_width, dbu_bgn_ext, dbu_end_ext, False)

    @staticmethod
    def _vertex_directions(points: Sequence[Point2D]) -> List[Point2D]:
        directions: List[Point2D] = []
        for index in range(len(points)):
            if index == 0:
                direction = RoutingUtils._unit_vector(points[index], points[index + 1])
            elif index == len(points) - 1:
                direction = RoutingUtils._unit_vector(points[index - 1], points[index])
            else:
                prev_dir = RoutingUtils._unit_vector(points[index - 1], points[index])
                next_dir = RoutingUtils._unit_vector(points[index], points[index + 1])
                direction = (prev_dir[0] + next_dir[0], prev_dir[1] + next_dir[1])
                length = math.hypot(direction[0], direction[1])
                if length < 1e-9:
                    direction = next_dir
                else:
                    direction = (direction[0] / length, direction[1] / length)
            directions.append(direction)
        return directions

    @staticmethod
    def _unit_vector(a: Point2D, b: Point2D) -> Point2D:
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        length = math.hypot(dx, dy)
        if length < 1e-9:
            return (1.0, 0.0)
        return (dx / length, dy / length)

    @staticmethod
    def _offset_polyline(points: Sequence[Point2D], offset: float) -> List[Point2D]:
        if len(points) <= 1 or abs(offset) < 1e-9:
            return list(points)
        if RoutingUtils._is_manhattan_polyline(points):
            return RoutingUtils._offset_manhattan_polyline(points, offset)

        directions = RoutingUtils._vertex_directions(points)
        normals = [(-direction[1], direction[0]) for direction in directions]
        return [
            (point[0] + normals[index][0] * offset, point[1] + normals[index][1] * offset)
            for index, point in enumerate(points)
        ]

    @staticmethod
    def _is_manhattan_polyline(points: Sequence[Point2D]) -> bool:
        for index in range(1, len(points)):
            dx = points[index][0] - points[index - 1][0]
            dy = points[index][1] - points[index - 1][1]
            if abs(dx) > 1e-9 and abs(dy) > 1e-9:
                return False
        return True

    @staticmethod
    def _offset_manhattan_polyline(points: Sequence[Point2D], offset: float) -> List[Point2D]:
        offset_segments = []
        for index in range(len(points) - 1):
            p0 = points[index]
            p1 = points[index + 1]
            dx = p1[0] - p0[0]
            dy = p1[1] - p0[1]
            length = math.hypot(dx, dy)
            if length < 1e-9:
                continue
            nx = -dy / length
            ny = dx / length
            offset_segments.append((
                (p0[0] + nx * offset, p0[1] + ny * offset),
                (p1[0] + nx * offset, p1[1] + ny * offset),
            ))

        if not offset_segments:
            return list(points)

        offset_points: List[Point2D] = [offset_segments[0][0]]
        for index in range(1, len(offset_segments)):
            prev_seg = offset_segments[index - 1]
            next_seg = offset_segments[index]
            offset_points.append(RoutingUtils._orthogonal_intersection(prev_seg, next_seg))
        offset_points.append(offset_segments[-1][1])
        return RoutingUtils._dedupe_points(offset_points)

    @staticmethod
    def _orthogonal_intersection(
        seg_a: Tuple[Point2D, Point2D],
        seg_b: Tuple[Point2D, Point2D],
    ) -> Point2D:
        a0, a1 = seg_a
        b0, b1 = seg_b
        a_is_vertical = abs(a0[0] - a1[0]) < 1e-9
        b_is_vertical = abs(b0[0] - b1[0]) < 1e-9

        if a_is_vertical == b_is_vertical:
            return a1
        if a_is_vertical:
            return (a0[0], b0[1])
        return (b0[0], a0[1])

    @staticmethod
    def _bundle_offsets(count: int, pitch: float) -> List[float]:
        center = (count - 1) / 2.0
        return [(index - center) * pitch for index in range(count)]

    @staticmethod
    def _build_parallel_manhattan_shortest_routes(
        start_points: Sequence[Point2D],
        end_points: Sequence[Point2D],
        widths: Sequence[float],
        pitch: float,
        clearance: float,
        obstacles: Sequence[Tuple[float, float, float, float]],
        begin_extension: Optional[float],
        end_extension: Optional[float],
        extension_type: str,
    ) -> List[RouteResult]:
        starts = [RoutingUtils._to_point(point) for point in start_points]
        ends = [RoutingUtils._to_point(point) for point in end_points]
        obstacle_bundle_results = RoutingUtils._build_obstacle_avoiding_bundle_routes(
            starts=starts,
            ends=ends,
            widths=widths,
            pitch=pitch,
            clearance=clearance,
            obstacles=obstacles,
            begin_extension=begin_extension,
            end_extension=end_extension,
            extension_type=extension_type,
        )
        if obstacle_bundle_results is not None:
            return obstacle_bundle_results

        pairings = RoutingUtils._pair_bundle_ports(starts, ends)
        if not pairings:
            return []

        try:
            gf = RoutingUtils._get_gdsfactory()
            RoutingUtils._activate_gdsfactory_pdk(gf)
            component = gf.Component()
            route_width = max(widths)
            start_orientation, end_orientation = RoutingUtils._bundle_port_orientations(starts, ends)

            ports1 = []
            ports2 = []
            for order, (start_index, end_index) in enumerate(pairings):
                ports1.append(
                    component.add_port(
                        name=f"s{order}",
                        center=starts[start_index],
                        width=route_width,
                        orientation=start_orientation,
                        layer=(1, 0),
                        port_type="electrical",
                    )
                )
                ports2.append(
                    component.add_port(
                        name=f"e{order}",
                        center=ends[end_index],
                        width=route_width,
                        orientation=end_orientation,
                        layer=(1, 0),
                        port_type="electrical",
                    )
                )

            kwargs = dict(
                ports1=ports1,
                ports2=ports2,
                layer=(1, 0),
                route_width=route_width,
                separation=max(pitch, route_width + clearance),
                auto_taper=False,
                sort_ports=False,
                start_straight_length=0,
                end_straight_length=0,
                on_collision="show_error",
                raise_on_error=False,
            )
            waypoint_candidates = RoutingUtils._bundle_obstacle_waypoints(
                starts=starts,
                ends=ends,
                obstacles=obstacles,
                pitch=max(pitch, route_width + clearance),
                route_width=route_width,
                clearance=clearance,
            )
            if waypoint_candidates:
                kwargs["waypoints"] = waypoint_candidates
            if obstacles:
                import klayout.db as kdb
                kwargs["bboxes"] = [kdb.DBox(x1, y1, x2, y2) for x1, y1, x2, y2 in obstacles]

            bundle_routes = gf.routing.route_bundle_electrical(component, **kwargs)
            results: List[Optional[RouteResult]] = [None] * len(starts)

            for route, (start_index, _) in zip(bundle_routes, pairings):
                points = [
                    (
                        float(point.x) / GeometryUtils.UNIT_SCALE,
                        float(point.y) / GeometryUtils.UNIT_SCALE,
                    )
                    for point in route.backbone
                ]
                points = RoutingUtils._dedupe_points(points)
                bgn_ext, fin_ext = RoutingUtils._resolve_extensions(
                    line_width=widths[start_index],
                    extension_type=extension_type,
                    begin_extension=begin_extension,
                    end_extension=end_extension,
                    start_port=None,
                    end_port=None,
                )
                shapes = [
                    RoutingUtils._polyline_to_path(
                        points=points,
                        width=widths[start_index],
                        begin_extension=bgn_ext,
                        end_extension=fin_ext,
                    )
                ]
                results[start_index] = RouteResult(
                    shapes=shapes,
                    points=points,
                    width=float(widths[start_index]),
                    begin_extension=bgn_ext,
                    end_extension=fin_ext,
                )

            return [result for result in results if result is not None]
        except Exception:
            return RoutingUtils._build_parallel_bundle_fallback_routes(
                starts=starts,
                ends=ends,
                widths=widths,
                pitch=pitch,
                clearance=clearance,
                pairings=pairings,
                begin_extension=begin_extension,
                end_extension=end_extension,
                extension_type=extension_type,
            )

    @staticmethod
    def _build_parallel_bundle_fallback_routes(
        starts: Sequence[Point2D],
        ends: Sequence[Point2D],
        widths: Sequence[float],
        pitch: float,
        clearance: float,
        pairings: Sequence[Tuple[int, int]],
        begin_extension: Optional[float],
        end_extension: Optional[float],
        extension_type: str,
    ) -> List[RouteResult]:
        if not pairings:
            return []

        pitch_eff = max(pitch, max(widths) + clearance, 1.0)
        start_center = RoutingUtils._mean_point(starts)
        end_center = RoutingUtils._mean_point(ends)
        start_x_span = max(point[0] for point in starts) - min(point[0] for point in starts)
        start_y_span = max(point[1] for point in starts) - min(point[1] for point in starts)
        end_x_span = max(point[0] for point in ends) - min(point[0] for point in ends)
        end_y_span = max(point[1] for point in ends) - min(point[1] for point in ends)
        starts_are_rows = start_x_span >= start_y_span
        ends_are_rows = end_x_span >= end_y_span
        starts_are_columns = start_y_span > start_x_span
        ends_are_columns = end_y_span > end_x_span

        if starts_are_rows and ends_are_rows:
            horizontal = False
        elif starts_are_columns and ends_are_columns:
            horizontal = True
        else:
            horizontal = abs(end_center[0] - start_center[0]) >= abs(end_center[1] - start_center[1])
        results: List[Optional[RouteResult]] = [None] * len(starts)

        if horizontal:
            ordered = sorted(pairings, key=lambda item: starts[item[0]][1], reverse=True)
            mid_x = (start_center[0] + end_center[0]) / 2.0
            for lane_index, (start_index, end_index) in enumerate(ordered):
                offset = (lane_index - (len(ordered) - 1) / 2.0) * pitch_eff
                elbow_x = mid_x + offset
                points = [
                    starts[start_index],
                    (elbow_x, starts[start_index][1]),
                    (elbow_x, ends[end_index][1]),
                    ends[end_index],
                ]
                points = RoutingUtils._dedupe_points(points)
                bgn_ext, fin_ext = RoutingUtils._resolve_extensions(
                    line_width=widths[start_index],
                    extension_type=extension_type,
                    begin_extension=begin_extension,
                    end_extension=end_extension,
                    start_port=None,
                    end_port=None,
                )
                results[start_index] = RouteResult(
                    shapes=[RoutingUtils._polyline_to_path(points, widths[start_index], bgn_ext, fin_ext)],
                    points=points,
                    width=float(widths[start_index]),
                    begin_extension=bgn_ext,
                    end_extension=fin_ext,
                )
        else:
            ordered = sorted(pairings, key=lambda item: starts[item[0]][0])
            mid_y = (start_center[1] + end_center[1]) / 2.0
            for lane_index, (start_index, end_index) in enumerate(ordered):
                offset = (lane_index - (len(ordered) - 1) / 2.0) * pitch_eff
                elbow_y = mid_y + offset
                points = [
                    starts[start_index],
                    (starts[start_index][0], elbow_y),
                    (ends[end_index][0], elbow_y),
                    ends[end_index],
                ]
                points = RoutingUtils._dedupe_points(points)
                bgn_ext, fin_ext = RoutingUtils._resolve_extensions(
                    line_width=widths[start_index],
                    extension_type=extension_type,
                    begin_extension=begin_extension,
                    end_extension=end_extension,
                    start_port=None,
                    end_port=None,
                )
                results[start_index] = RouteResult(
                    shapes=[RoutingUtils._polyline_to_path(points, widths[start_index], bgn_ext, fin_ext)],
                    points=points,
                    width=float(widths[start_index]),
                    begin_extension=bgn_ext,
                    end_extension=fin_ext,
                )

        return [result for result in results if result is not None]

    @staticmethod
    def _build_obstacle_avoiding_bundle_routes(
        starts: Sequence[Point2D],
        ends: Sequence[Point2D],
        widths: Sequence[float],
        pitch: float,
        clearance: float,
        obstacles: Sequence[Tuple[float, float, float, float]],
        begin_extension: Optional[float],
        end_extension: Optional[float],
        extension_type: str,
    ) -> Optional[List[RouteResult]]:
        if not obstacles or len(starts) != len(ends) or not starts:
            return None

        start_ys = [point[1] for point in starts]
        end_ys = [point[1] for point in ends]
        if max(start_ys) <= max(end_ys):
            return None

        pairings = RoutingUtils._pair_bundle_ports(starts, ends)
        if len(pairings) != len(starts):
            return None

        group_x1 = min([point[0] for point in starts] + [point[0] for point in ends])
        group_x2 = max([point[0] for point in starts] + [point[0] for point in ends])
        start_band_y = min(start_ys)
        end_band_y = max(end_ys)
        blocking = [
            obstacle
            for obstacle in obstacles
            if obstacle[0] <= group_x2 and obstacle[2] >= group_x1 and obstacle[1] <= start_band_y and obstacle[3] >= end_band_y
        ]
        if not blocking:
            return None

        obstacle_x1 = min(obstacle[0] for obstacle in blocking)
        obstacle_y1 = min(obstacle[1] for obstacle in blocking)
        obstacle_x2 = max(obstacle[2] for obstacle in blocking)
        obstacle_y2 = max(obstacle[3] for obstacle in blocking)

        pitch_eff = max(pitch, max(widths) + clearance, 1.0)
        lane_margin = pitch_eff * 2.0
        left_base_x = obstacle_x1 - lane_margin
        right_base_x = obstacle_x2 + lane_margin
        top_base_y = max(start_ys) + lane_margin
        bottom_base_y = min(end_ys) - lane_margin

        left_cost = sum(abs(point[0] - left_base_x) for point in starts + ends)
        right_cost = sum(abs(point[0] - right_base_x) for point in starts + ends)
        use_left = left_cost <= right_cost

        ordered_pairings = sorted(pairings, key=lambda item: starts[item[0]][0], reverse=not use_left)
        results: List[Optional[RouteResult]] = [None] * len(starts)

        for lane_index, (start_index, end_index) in enumerate(ordered_pairings):
            side_x = (left_base_x - lane_index * pitch_eff) if use_left else (right_base_x + lane_index * pitch_eff)
            top_y = top_base_y + lane_index * pitch_eff
            bottom_y = bottom_base_y - lane_index * pitch_eff
            points = [
                starts[start_index],
                (starts[start_index][0], top_y),
                (side_x, top_y),
                (side_x, bottom_y),
                (ends[end_index][0], bottom_y),
                ends[end_index],
            ]
            points = RoutingUtils._dedupe_points(points)
            bgn_ext, fin_ext = RoutingUtils._resolve_extensions(
                line_width=widths[start_index],
                extension_type=extension_type,
                begin_extension=begin_extension,
                end_extension=end_extension,
                start_port=None,
                end_port=None,
            )
            results[start_index] = RouteResult(
                shapes=[RoutingUtils._polyline_to_path(points, widths[start_index], bgn_ext, fin_ext)],
                points=points,
                width=float(widths[start_index]),
                begin_extension=bgn_ext,
                end_extension=fin_ext,
            )

        return [result for result in results if result is not None]

    @staticmethod
    def _bundle_obstacle_waypoints(
        starts: Sequence[Point2D],
        ends: Sequence[Point2D],
        obstacles: Sequence[Tuple[float, float, float, float]],
        pitch: float,
        route_width: float,
        clearance: float,
    ) -> Optional[List[Point2D]]:
        if not obstacles:
            return None

        all_x = [point[0] for point in starts] + [point[0] for point in ends]
        all_y = [point[1] for point in starts] + [point[1] for point in ends]
        group_x1 = min(all_x)
        group_x2 = max(all_x)
        group_y1 = min(all_y)
        group_y2 = max(all_y)
        if group_x1 == group_x2 or group_y1 == group_y2:
            pass

        start_center = RoutingUtils._mean_point(starts)
        end_center = RoutingUtils._mean_point(ends)
        vertical_bundle = abs(end_center[1] - start_center[1]) >= abs(end_center[0] - start_center[0])
        if not vertical_bundle:
            return None

        bundle_margin = max(route_width + clearance, pitch) * max(len(starts), 2)
        best_waypoints: Optional[List[Point2D]] = None
        best_cost = float("inf")

        for x1, y1, x2, y2 in obstacles:
            blocks_bundle = (
                x1 <= group_x2
                and x2 >= group_x1
                and y1 <= max(point[1] for point in starts)
                and y2 >= min(point[1] for point in ends)
            )
            if not blocks_bundle:
                continue

            top_y = max(max(point[1] for point in starts), y2) + bundle_margin
            bottom_y = min(min(point[1] for point in ends), y1) - bundle_margin
            left_x = x1 - bundle_margin
            right_x = x2 + bundle_margin

            left_cost = sum(abs(point[0] - left_x) for point in starts + ends)
            right_cost = sum(abs(point[0] - right_x) for point in starts + ends)

            for side_x, side_cost in ((left_x, left_cost), (right_x, right_cost)):
                waypoints = [(side_x, top_y), (side_x, bottom_y)]
                if side_cost < best_cost:
                    best_cost = side_cost
                    best_waypoints = waypoints

        return best_waypoints

    @staticmethod
    def _get_gdsfactory():
        try:
            return importlib.import_module("gdsfactory")
        except ModuleNotFoundError:
            candidates = []
            try:
                candidates.append(site.getusersitepackages())
            except Exception:
                pass
            appdata = os.environ.get("APPDATA")
            if appdata:
                candidates.append(os.path.join(appdata, "Python", "Python313", "site-packages"))
            for path in candidates:
                if path and path not in os.sys.path and os.path.exists(path):
                    os.sys.path.append(path)
            gf = importlib.import_module("gdsfactory")
            return gf

    @staticmethod
    def _activate_gdsfactory_pdk(gf) -> None:
        try:
            import gdsfactory.gpdk as gpdk
            gpdk.get_generic_pdk().activate()
        except Exception:
            import gdsfactory.generic_tech as generic_tech
            generic_tech.get_generic_pdk().activate()

    @staticmethod
    def _infer_orientation(a: Point2D, b: Point2D) -> float:
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        if abs(dx) >= abs(dy):
            return 0.0 if dx >= 0 else 180.0
        return 90.0 if dy >= 0 else 270.0

    @staticmethod
    def _bundle_port_orientations(
        starts: Sequence[Point2D],
        ends: Sequence[Point2D],
    ) -> Tuple[float, float]:
        start_x_span = max(point[0] for point in starts) - min(point[0] for point in starts)
        start_y_span = max(point[1] for point in starts) - min(point[1] for point in starts)
        end_x_span = max(point[0] for point in ends) - min(point[0] for point in ends)
        end_y_span = max(point[1] for point in ends) - min(point[1] for point in ends)
        start_center = RoutingUtils._mean_point(starts)
        end_center = RoutingUtils._mean_point(ends)

        if start_x_span <= start_y_span and end_x_span <= end_y_span:
            if end_center[0] >= start_center[0]:
                return (0.0, 180.0)
            return (180.0, 0.0)

        if start_y_span < start_x_span and end_y_span < end_x_span:
            if end_center[1] >= start_center[1]:
                return (90.0, 270.0)
            return (270.0, 90.0)

        if abs(end_center[0] - start_center[0]) >= abs(end_center[1] - start_center[1]):
            if end_center[0] >= start_center[0]:
                return (0.0, 180.0)
            return (180.0, 0.0)

        if end_center[1] >= start_center[1]:
            return (90.0, 270.0)
        return (270.0, 90.0)

    @staticmethod
    def _build_gdsfactory_route_shapes(
        points: Sequence[Point2D],
        width: float,
        mode: str,
        obstacles: Sequence[Tuple[float, float, float, float]],
    ) -> List[object]:
        gf = RoutingUtils._get_gdsfactory()
        RoutingUtils._activate_gdsfactory_pdk(gf)
        if mode == "manhattan":
            component = gf.Component()
            start = points[0]
            end = points[-1]
            start_orientation = RoutingUtils._infer_orientation(points[0], points[1]) if len(points) > 1 else 0.0
            end_orientation = RoutingUtils._infer_orientation(points[-1], points[-2]) if len(points) > 1 else 180.0
            p1 = component.add_port(
                name="p1",
                center=start,
                width=width,
                orientation=start_orientation,
                layer=(1, 0),
                port_type="electrical",
            )
            p2 = component.add_port(
                name="p2",
                center=end,
                width=width,
                orientation=end_orientation,
                layer=(1, 0),
                port_type="electrical",
            )
            kwargs = dict(
                ports1=[p1],
                ports2=[p2],
                layer=(1, 0),
                route_width=width,
                separation=max(width * 2.0, 1.0),
                auto_taper=False,
                sort_ports=False,
                start_straight_length=0,
                end_straight_length=0,
            )
            if len(points) > 2:
                kwargs["waypoints"] = list(points[1:-1])
            if obstacles:
                import klayout.db as kdb
                kwargs["bboxes"] = [kdb.DBox(x1, y1, x2, y2) for x1, y1, x2, y2 in obstacles]
            gf.routing.route_bundle_electrical(component, **kwargs)
            return RoutingUtils._gf_component_to_polygons(component)

        path = gf.path.Path(points)
        xs = gf.cross_section.cross_section(width=width, layer=(1, 0), port_names=("o1", "o2"))
        component = gf.path.extrude(path, cross_section=xs)
        return RoutingUtils._gf_component_to_polygons(component)

    @staticmethod
    def _build_gdsfactory_manhattan_points(
        points: Sequence[Point2D],
        width: float,
        obstacles: Sequence[Tuple[float, float, float, float]],
    ) -> List[Point2D]:
        if len(points) <= 2 and not obstacles:
            return list(points)

        gf = RoutingUtils._get_gdsfactory()
        RoutingUtils._activate_gdsfactory_pdk(gf)
        component = gf.Component()
        start_orientation = RoutingUtils._infer_orientation(points[0], points[1]) if len(points) > 1 else 0.0
        end_orientation = RoutingUtils._infer_orientation(points[-1], points[-2]) if len(points) > 1 else 180.0
        p1 = component.add_port(
            name="p1",
            center=points[0],
            width=width,
            orientation=start_orientation,
            layer=(1, 0),
            port_type="electrical",
        )
        p2 = component.add_port(
            name="p2",
            center=points[-1],
            width=width,
            orientation=end_orientation,
            layer=(1, 0),
            port_type="electrical",
        )

        kwargs = dict(
            ports1=[p1],
            ports2=[p2],
            layer=(1, 0),
            route_width=width,
            separation=max(width * 2.0, 1.0),
            auto_taper=False,
            sort_ports=False,
            start_straight_length=0,
            end_straight_length=0,
            on_collision="show_error",
            raise_on_error=False,
        )
        if len(points) > 2:
            kwargs["waypoints"] = list(points[1:-1])
        if obstacles:
            import klayout.db as kdb
            kwargs["bboxes"] = [kdb.DBox(x1, y1, x2, y2) for x1, y1, x2, y2 in obstacles]

        routes = gf.routing.route_bundle_electrical(component, **kwargs)
        if not routes:
            return list(points)
        return [
            (
                float(point.x) / GeometryUtils.UNIT_SCALE,
                float(point.y) / GeometryUtils.UNIT_SCALE,
            )
            for point in routes[0].backbone
        ]

    @staticmethod
    def _pair_bundle_ports(
        starts: Sequence[Point2D],
        ends: Sequence[Point2D],
    ) -> List[Tuple[int, int]]:
        if not starts or not ends:
            return []
        x_span = max([p[0] for p in starts] + [p[0] for p in ends]) - min([p[0] for p in starts] + [p[0] for p in ends])
        y_span = max([p[1] for p in starts] + [p[1] for p in ends]) - min([p[1] for p in starts] + [p[1] for p in ends])
        key = (lambda item: item[1][1]) if y_span >= x_span else (lambda item: item[1][0])
        starts_sorted = sorted(list(enumerate(starts)), key=key, reverse=True)
        ends_sorted = sorted(list(enumerate(ends)), key=key, reverse=True)
        return [(start_index, end_index) for (start_index, _), (end_index, _) in zip(starts_sorted, ends_sorted)]

    @staticmethod
    def _gf_component_to_polygons(component) -> List[object]:
        polygons = []
        polys = component.get_polygons_points()
        for _, polygon_list in polys.items():
            for polygon in polygon_list:
                db_points = [
                    db.Point(
                        int(round(float(point[0]) * GeometryUtils.UNIT_SCALE)),
                        int(round(float(point[1]) * GeometryUtils.UNIT_SCALE)),
                    )
                    for point in polygon
                ]
                polygons.append(db.Polygon(db_points))
        return polygons

    @staticmethod
    def _gf_route_to_polygons(route) -> List[object]:
        polygons = []
        for polygon in getattr(route, "polygons", []):
            db_points = [
                db.Point(
                    int(round(float(point.x) * GeometryUtils.UNIT_SCALE)),
                    int(round(float(point.y) * GeometryUtils.UNIT_SCALE)),
                )
                for point in polygon.each_point_hull()
            ]
            polygons.append(db.Polygon(db_points))
        return polygons

    @staticmethod
    def _bundle_route_order(starts: Sequence[Point2D], ends: Sequence[Point2D]) -> List[int]:
        centers = [
            ((starts[index][0] + ends[index][0]) / 2.0, (starts[index][1] + ends[index][1]) / 2.0, index)
            for index in range(len(starts))
        ]
        if not centers:
            return []
        x_span = max(item[0] for item in centers) - min(item[0] for item in centers)
        y_span = max(item[1] for item in centers) - min(item[1] for item in centers)
        if y_span >= x_span:
            centers.sort(key=lambda item: item[1], reverse=True)
        else:
            centers.sort(key=lambda item: item[0])
        if len(centers) <= 2:
            return [item[2] for item in centers]
        ordered = [centers[0][2], centers[-1][2]]
        ordered.extend(item[2] for item in centers[1:-1])
        return ordered

    @staticmethod
    def _route_manhattan_on_grid(
        start: Point2D,
        end: Point2D,
        blocked_rects: Sequence[Tuple[float, float, float, float]],
        width: float,
        min_spacing: float,
        grid_step: float,
    ) -> List[Point2D]:
        xs = {float(start[0]), float(end[0])}
        ys = {float(start[1]), float(end[1])}
        margin = grid_step * 2.0 + width + min_spacing

        for x1, y1, x2, y2 in blocked_rects:
            xs.update([x1 - grid_step, x1, x2, x2 + grid_step])
            ys.update([y1 - grid_step, y1, y2, y2 + grid_step])

        xs.update([start[0] - margin, start[0] + margin, end[0] - margin, end[0] + margin])
        ys.update([start[1] - margin, start[1] + margin, end[1] - margin, end[1] + margin])

        xs_sorted = sorted(xs)
        ys_sorted = sorted(ys)
        start_node = (float(start[0]), float(start[1]))
        end_node = (float(end[0]), float(end[1]))

        def is_blocked_point(node: Point2D) -> bool:
            x, y = node
            for x1, y1, x2, y2 in blocked_rects:
                if x1 < x < x2 and y1 < y < y2:
                    return True
            return False

        def segment_clear(a: Point2D, b: Point2D) -> bool:
            if RoutingUtils._points_close(a, b):
                return True
            for rect in blocked_rects:
                if RoutingUtils._segment_hits_or_touches_box(a, b, rect):
                    return False
            return True

        x_neighbors = {value: [] for value in xs_sorted}
        y_neighbors = {value: [] for value in ys_sorted}
        for index, value in enumerate(xs_sorted):
            if index > 0:
                x_neighbors[value].append(xs_sorted[index - 1])
            if index + 1 < len(xs_sorted):
                x_neighbors[value].append(xs_sorted[index + 1])
        for index, value in enumerate(ys_sorted):
            if index > 0:
                y_neighbors[value].append(ys_sorted[index - 1])
            if index + 1 < len(ys_sorted):
                y_neighbors[value].append(ys_sorted[index + 1])

        open_heap: List[Tuple[float, float, Point2D]] = []
        heapq.heappush(open_heap, (0.0, 0.0, start_node))
        came_from: dict[Point2D, Point2D] = {}
        g_score = {start_node: 0.0}
        visited = set()

        while open_heap:
            _, current_cost, current = heapq.heappop(open_heap)
            if current in visited:
                continue
            visited.add(current)

            if RoutingUtils._points_close(current, end_node):
                path = RoutingUtils._reconstruct_node_path(came_from, current)
                return RoutingUtils._dedupe_points(path)

            cx, cy = current
            candidates = [(nx, cy) for nx in x_neighbors[cx]] + [(cx, ny) for ny in y_neighbors[cy]]
            for neighbor in candidates:
                if neighbor in visited:
                    continue
                if is_blocked_point(neighbor):
                    continue
                if not segment_clear(current, neighbor):
                    continue
                tentative_g = current_cost + RoutingUtils._segment_length(current, neighbor)
                if tentative_g >= g_score.get(neighbor, float("inf")):
                    continue
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                heuristic = abs(neighbor[0] - end_node[0]) + abs(neighbor[1] - end_node[1])
                heapq.heappush(open_heap, (tentative_g + heuristic, tentative_g, neighbor))

        return RoutingUtils._dedupe_points([start, end])

    @staticmethod
    def _reconstruct_node_path(came_from: dict, current: Point2D) -> List[Point2D]:
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path

    @staticmethod
    def _path_to_blocked_rects(
        points: Sequence[Point2D],
        width: float,
        min_spacing: float,
    ) -> List[Tuple[float, float, float, float]]:
        half = width / 2.0 + min_spacing / 2.0
        rects: List[Tuple[float, float, float, float]] = []
        for index in range(1, len(points)):
            a = points[index - 1]
            b = points[index]
            if abs(a[0] - b[0]) < 1e-9:
                x1 = a[0] - half
                x2 = a[0] + half
                y1 = min(a[1], b[1]) - half
                y2 = max(a[1], b[1]) + half
            else:
                x1 = min(a[0], b[0]) - half
                x2 = max(a[0], b[0]) + half
                y1 = a[1] - half
                y2 = a[1] + half
            rects.append((x1, y1, x2, y2))
        return rects

    @staticmethod
    def _segment_hits_or_touches_box(
        a: Point2D,
        b: Point2D,
        box: Tuple[float, float, float, float],
    ) -> bool:
        x1, y1, x2, y2 = box
        if abs(a[0] - b[0]) < 1e-9:
            x = a[0]
            if x <= x1 or x >= x2:
                return False
            low, high = sorted((a[1], b[1]))
            return not (high <= y1 or low >= y2)
        if abs(a[1] - b[1]) < 1e-9:
            y = a[1]
            if y <= y1 or y >= y2:
                return False
            low, high = sorted((a[0], b[0]))
            return not (high <= x1 or low >= x2)
        return False

    @staticmethod
    def _mean_point(points: Sequence[Point2D]) -> Point2D:
        normalized = [RoutingUtils._to_point(point) for point in points]
        return (
            sum(point[0] for point in normalized) / len(normalized),
            sum(point[1] for point in normalized) / len(normalized),
        )

    @staticmethod
    def _expand_width_list(value: object, count: int) -> List[float]:
        if isinstance(value, (list, tuple)):
            if len(value) != count:
                raise ValueError("Width list length must match route count")
            return [float(item) for item in value]
        return [float(value) for _ in range(count)]

    @staticmethod
    def _segment_length(a: Point2D, b: Point2D) -> float:
        return math.hypot(b[0] - a[0], b[1] - a[1])

    @staticmethod
    def _polyline_length(points: Sequence[Point2D]) -> float:
        return sum(
            RoutingUtils._segment_length(points[index - 1], points[index])
            for index in range(1, len(points))
        )

    @staticmethod
    def _dedupe_points(points: Iterable[Point2D]) -> List[Point2D]:
        result: List[Point2D] = []
        for point in points:
            if not result:
                result.append(point)
                continue
            if abs(point[0] - result[-1][0]) < 1e-9 and abs(point[1] - result[-1][1]) < 1e-9:
                continue
            result.append(point)
        return result
