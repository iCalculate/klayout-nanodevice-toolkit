# -*- coding: utf-8 -*-
"""
Spiral interdigitated electrode utility functions.

This module generates several spiral interdigitated electrode (IDE) families:
- round opposed spirals
- round same-direction spirals
- square same-direction spirals

All dimensions are in micrometers (um).
"""

import math
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Sequence, Tuple

if __package__:
    from .geometry import GeometryUtils
else:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from utils.geometry import GeometryUtils

try:
    import pya
except ImportError:
    import klayout.db as pya


SpiralStyle = Literal[
    "round_opposed",
    "round_same_direction",
    "square_same_direction",
]

Point = GeometryUtils.Point
Region = pya.Region
Path = pya.Path
Trans = pya.Trans
CellInstArray = pya.CellInstArray


@dataclass
class SpiralElectrodeResult:
    electrode_a: object
    electrode_b: object
    pad_a: Optional[object]
    pad_b: Optional[object]
    lead_a: Optional[object]
    lead_b: Optional[object]
    metadata: Dict[str, object]


def _to_point_sequence(points_um: Sequence[Tuple[float, float]]) -> List[object]:
    s = GeometryUtils.UNIT_SCALE
    return [Point(int(round(x * s)), int(round(y * s))) for x, y in points_um]


def _path_region(points_um: Sequence[Tuple[float, float]], width_um: float) -> object:
    if len(points_um) < 2:
        raise ValueError("Spiral path requires at least 2 points.")
    path = Path(_to_point_sequence(points_um), int(round(width_um * GeometryUtils.UNIT_SCALE)))
    return Region(path.polygon())


def _rectangle_region(center_x: float, center_y: float, width: float, height: float) -> object:
    return Region(GeometryUtils.create_rectangle(center_x, center_y, width, height, center=True))


def _archimedean_spiral_points(
    center_x: float,
    center_y: float,
    inner_radius: float,
    pitch: float,
    turns: float,
    theta_offset: float,
    angular_step_deg: float,
    radial_extension: float = 0.0,
    clockwise: bool = False,
) -> List[Tuple[float, float]]:
    if turns <= 0:
        raise ValueError("turns must be > 0")

    b = pitch / (2.0 * math.pi)
    theta_end = max(2.0 * math.pi * turns, math.radians(max(angular_step_deg, 0.5)))
    theta_step = math.radians(max(angular_step_deg, 0.5))
    direction = -1.0 if clockwise else 1.0

    points: List[Tuple[float, float]] = []
    theta = 0.0
    while theta <= theta_end + 1e-9:
        radius = inner_radius + b * theta
        angle = direction * theta + theta_offset
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        points.append((x, y))
        theta += theta_step

    if radial_extension > 0:
        end_radius = inner_radius + b * theta_end
        final_angle = direction * theta_end + theta_offset
        start_ext = (
            center_x + end_radius * math.cos(final_angle),
            center_y + end_radius * math.sin(final_angle),
        )
        end_ext = (
            center_x + (end_radius + radial_extension) * math.cos(final_angle),
            center_y + (end_radius + radial_extension) * math.sin(final_angle),
        )
        points.extend([start_ext, end_ext])

    return points


def _square_spiral_points(
    center_x: float,
    center_y: float,
    inner_radius: float,
    same_electrode_pitch: float,
    turns: float,
    offset_radius: float = 0.0,
    radial_extension: float = 0.0,
    clockwise: bool = False,
) -> List[Tuple[float, float]]:
    if turns <= 0:
        raise ValueError("turns must be > 0")

    start_radius = inner_radius + offset_radius
    segments = max(4, int(math.ceil(turns * 4.0)))
    direction_cycle = [(0, 1), (-1, 0), (0, -1), (1, 0)]
    if clockwise:
        direction_cycle = [(0, 1), (1, 0), (0, -1), (-1, 0)]

    # Start from the lower-right corner of the innermost square loop.
    points: List[Tuple[float, float]] = [(center_x + start_radius, center_y - start_radius)]
    current_x, current_y = points[0]

    for idx in range(segments):
        direction = direction_cycle[idx % 4]
        ring_index = idx // 2
        segment_length = 2.0 * start_radius + ring_index * same_electrode_pitch
        next_x = current_x + direction[0] * segment_length
        next_y = current_y + direction[1] * segment_length
        points.append((next_x, next_y))
        current_x, current_y = next_x, next_y

    if radial_extension > 0 and len(points) >= 2:
        last = points[-1]
        prev = points[-2]
        dx = last[0] - prev[0]
        dy = last[1] - prev[1]
        seg_len = math.hypot(dx, dy)
        if seg_len > 0:
            ux, uy = dx / seg_len, dy / seg_len
            points.append((last[0] + ux * radial_extension, last[1] + uy * radial_extension))

    return points


def _spiral_end_direction(points: Sequence[Tuple[float, float]], center_x: float, center_y: float) -> Tuple[float, float]:
    if len(points) >= 2:
        dx = points[-1][0] - points[-2][0]
        dy = points[-1][1] - points[-2][1]
    else:
        dx = points[-1][0] - center_x
        dy = points[-1][1] - center_y

    length = math.hypot(dx, dy)
    if length == 0:
        dx = points[-1][0] - center_x
        dy = points[-1][1] - center_y
        length = math.hypot(dx, dy)
    if length == 0:
        return (1.0, 0.0)
    return (dx / length, dy / length)


def _lead_to_pad(
    spiral_end: Tuple[float, float],
    lead_direction: Tuple[float, float],
    lead_width: float,
    pad_size: Tuple[float, float],
    pad_gap: float,
) -> Tuple[object, object, Tuple[float, float]]:
    ux, uy = lead_direction
    length = math.hypot(ux, uy)
    if length == 0:
        raise ValueError("lead_direction must be non-zero")
    ux, uy = ux / length, uy / length

    pad_w, pad_h = pad_size
    radial_clearance = pad_gap + pad_h / 2.0
    pad_center = (
        spiral_end[0] + ux * radial_clearance,
        spiral_end[1] + uy * radial_clearance,
    )
    lead_end = (
        pad_center[0] - ux * (pad_h / 2.0),
        pad_center[1] - uy * (pad_h / 2.0),
    )

    lead_region = _path_region([spiral_end, lead_end], lead_width)
    pad_region = _rectangle_region(pad_center[0], pad_center[1], pad_w, pad_h)
    return lead_region, pad_region, pad_center


def _build_spiral_pair_points(
    style: SpiralStyle,
    center_x: float,
    center_y: float,
    inner_radius: float,
    centerline_spacing: float,
    same_electrode_pitch: float,
    turns: float,
    angular_step_deg: float,
    phase_offset_deg: float,
    radial_extension: float,
) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]], Dict[str, object]]:
    if style == "round_opposed":
        theta_b = math.pi if abs(phase_offset_deg) < 1e-9 else math.radians(phase_offset_deg)
        points_a = _archimedean_spiral_points(
            center_x=center_x,
            center_y=center_y,
            inner_radius=inner_radius,
            pitch=same_electrode_pitch,
            turns=turns,
            theta_offset=0.0,
            angular_step_deg=angular_step_deg,
            radial_extension=radial_extension,
            clockwise=False,
        )
        points_b = _archimedean_spiral_points(
            center_x=center_x,
            center_y=center_y,
            inner_radius=inner_radius + centerline_spacing,
            pitch=same_electrode_pitch,
            turns=turns,
            theta_offset=theta_b,
            angular_step_deg=angular_step_deg,
            radial_extension=radial_extension,
            clockwise=True,
        )
        return points_a, points_b, {"family": "round", "rotation_mode": "opposed"}

    if style == "round_same_direction":
        theta_b = math.pi if abs(phase_offset_deg) < 1e-9 else math.radians(phase_offset_deg)
        points_a = _archimedean_spiral_points(
            center_x=center_x,
            center_y=center_y,
            inner_radius=inner_radius,
            pitch=same_electrode_pitch,
            turns=turns,
            theta_offset=0.0,
            angular_step_deg=angular_step_deg,
            radial_extension=radial_extension,
            clockwise=False,
        )
        points_b = _archimedean_spiral_points(
            center_x=center_x,
            center_y=center_y,
            inner_radius=inner_radius + centerline_spacing,
            pitch=same_electrode_pitch,
            turns=turns,
            theta_offset=theta_b,
            angular_step_deg=angular_step_deg,
            radial_extension=radial_extension,
            clockwise=False,
        )
        return points_a, points_b, {"family": "round", "rotation_mode": "same_direction"}

    if style == "square_same_direction":
        points_a = _square_spiral_points(
            center_x=center_x,
            center_y=center_y,
            inner_radius=inner_radius,
            same_electrode_pitch=same_electrode_pitch,
            turns=turns,
            offset_radius=0.0,
            radial_extension=radial_extension,
            clockwise=False,
        )
        points_b = _square_spiral_points(
            center_x=center_x,
            center_y=center_y,
            inner_radius=inner_radius,
            same_electrode_pitch=same_electrode_pitch,
            turns=turns,
            offset_radius=centerline_spacing,
            radial_extension=radial_extension,
            clockwise=False,
        )
        return points_a, points_b, {"family": "square", "rotation_mode": "same_direction"}

    raise ValueError(f"Unsupported spiral style: {style}")


def create_spiral_interdigitated_electrodes(
    center_x: float = 0.0,
    center_y: float = 0.0,
    inner_radius: float = 15.0,
    turns: float = 4.0,
    line_width: float = 4.0,
    gap: float = 4.0,
    style: SpiralStyle = "round_same_direction",
    angular_step_deg: float = 4.0,
    phase_offset_deg: float = 0.0,
    radial_extension: float = 20.0,
    add_pads: bool = True,
    pad_size: Tuple[float, float] = (40.0, 40.0),
    pad_gap: float = 10.0,
    lead_width: Optional[float] = None,
) -> SpiralElectrodeResult:
    """
    Create two interdigitated spiral electrodes with a default edge-to-edge gap.

    The gap is enforced through the spiral pitch and the centerline offset of the
    second electrode, so the two electrodes are separated by default.
    """
    if line_width <= 0:
        raise ValueError("line_width must be > 0")
    if gap <= 0:
        raise ValueError("gap must be > 0")
    if inner_radius <= line_width / 2.0:
        raise ValueError("inner_radius must be larger than half the line_width")

    centerline_spacing = line_width + gap
    same_electrode_pitch = 2.0 * centerline_spacing
    lead_width = lead_width or line_width

    points_a, points_b, style_meta = _build_spiral_pair_points(
        style=style,
        center_x=center_x,
        center_y=center_y,
        inner_radius=inner_radius,
        centerline_spacing=centerline_spacing,
        same_electrode_pitch=same_electrode_pitch,
        turns=turns,
        angular_step_deg=angular_step_deg,
        phase_offset_deg=phase_offset_deg,
        radial_extension=radial_extension,
    )

    electrode_a = _path_region(points_a, line_width).merged()
    electrode_b = _path_region(points_b, line_width).merged()

    pad_a = None
    pad_b = None
    lead_a = None
    lead_b = None
    pad_centers: Dict[str, Tuple[float, float]] = {}

    if add_pads:
        lead_a, pad_a, pad_center_a = _lead_to_pad(
            spiral_end=points_a[-1],
            lead_direction=_spiral_end_direction(points_a, center_x, center_y),
            lead_width=lead_width,
            pad_size=pad_size,
            pad_gap=pad_gap,
        )
        lead_b, pad_b, pad_center_b = _lead_to_pad(
            spiral_end=points_b[-1],
            lead_direction=_spiral_end_direction(points_b, center_x, center_y),
            lead_width=lead_width,
            pad_size=pad_size,
            pad_gap=pad_gap,
        )
        pad_centers["A"] = pad_center_a
        pad_centers["B"] = pad_center_b

    outer_radius = inner_radius + turns * same_electrode_pitch + centerline_spacing + radial_extension
    metadata = {
        "style": style,
        "center": (center_x, center_y),
        "inner_radius": inner_radius,
        "outer_radius_estimate": outer_radius,
        "turns": turns,
        "line_width": line_width,
        "gap": gap,
        "centerline_spacing": centerline_spacing,
        "same_electrode_pitch": same_electrode_pitch,
        "phase_offset_deg": phase_offset_deg,
        "pad_centers": pad_centers,
        "points_a": points_a,
        "points_b": points_b,
        **style_meta,
    }

    return SpiralElectrodeResult(
        electrode_a=electrode_a,
        electrode_b=electrode_b,
        pad_a=pad_a,
        pad_b=pad_b,
        lead_a=lead_a,
        lead_b=lead_b,
        metadata=metadata,
    )


def _insert_result(cell: object, spiral_layer: int, pad_layer: int, result: SpiralElectrodeResult) -> None:
    cell.shapes(spiral_layer).insert(result.electrode_a)
    cell.shapes(spiral_layer).insert(result.electrode_b)
    if result.lead_a is not None:
        cell.shapes(spiral_layer).insert(result.lead_a)
    if result.lead_b is not None:
        cell.shapes(spiral_layer).insert(result.lead_b)
    if result.pad_a is not None:
        cell.shapes(pad_layer).insert(result.pad_a)
    if result.pad_b is not None:
        cell.shapes(pad_layer).insert(result.pad_b)


def _build_demo_variant_cell(
    layout: object,
    name: str,
    spiral_layer: int,
    pad_layer: int,
    params: Dict[str, object],
) -> object:
    cell = layout.create_cell(name)
    result = create_spiral_interdigitated_electrodes(**params)
    _insert_result(cell, spiral_layer, pad_layer, result)
    return cell


def _build_demo_group(
    layout: object,
    group_cell: object,
    spiral_layer: int,
    pad_layer: int,
    base_params: Dict[str, object],
    sweep_name: str,
    sweep_values: Sequence[object],
    dx: float = 420.0,
) -> None:
    s = GeometryUtils.UNIT_SCALE

    for idx, value in enumerate(sweep_values):
        params = dict(base_params)
        params[sweep_name] = value
        child_name = f"{group_cell.name}_{sweep_name}_{str(value).replace('.', 'p')}"
        child = _build_demo_variant_cell(layout, child_name, spiral_layer, pad_layer, params)
        group_cell.insert(
            CellInstArray(
                child.cell_index(),
                Trans(int(round(idx * dx * s)), 0),
            )
        )


def build_spiral_ide_demo_layout(layout: object) -> object:
    spiral_layer = layout.layer(30, 0)
    pad_layer = layout.layer(31, 0)
    root = layout.create_cell("SPIRAL_IDE_DEMO")

    demo_groups = [
        {
            "group_name": "ROUND_SAME_DIRECTION_GAP_SWEEP",
            "base_params": {
                "style": "round_same_direction",
                "center_x": 0.0,
                "center_y": 0.0,
                "inner_radius": 18.0,
                "turns": 4.5,
                "line_width": 4.0,
                "gap": 3.0,
                "phase_offset_deg": 180.0,
                "radial_extension": 24.0,
                "add_pads": True,
                "pad_size": (45.0, 45.0),
                "pad_gap": 10.0,
            },
            "sweep_name": "gap",
            "sweep_values": [2.0, 4.0, 7.0],
            "offset_y": 0.0,
        },
        {
            "group_name": "ROUND_OPPOSED_TURN_SWEEP",
            "base_params": {
                "style": "round_opposed",
                "center_x": 0.0,
                "center_y": 0.0,
                "inner_radius": 18.0,
                "turns": 3.0,
                "line_width": 4.0,
                "gap": 4.0,
                "phase_offset_deg": 180.0,
                "radial_extension": 24.0,
                "add_pads": True,
                "pad_size": (45.0, 45.0),
                "pad_gap": 10.0,
            },
            "sweep_name": "turns",
            "sweep_values": [2.5, 4.0, 5.5],
            "offset_y": 430.0,
        },
        {
            "group_name": "SQUARE_SAME_DIRECTION_LINEWIDTH_SWEEP",
            "base_params": {
                "style": "square_same_direction",
                "center_x": 0.0,
                "center_y": 0.0,
                "inner_radius": 16.0,
                "turns": 4.0,
                "line_width": 3.0,
                "gap": 4.0,
                "radial_extension": 28.0,
                "add_pads": True,
                "pad_size": (45.0, 45.0),
                "pad_gap": 10.0,
            },
            "sweep_name": "line_width",
            "sweep_values": [2.0, 4.0, 6.0],
            "offset_y": 860.0,
        },
    ]

    s = GeometryUtils.UNIT_SCALE
    for group in demo_groups:
        group_root = layout.create_cell(group["group_name"])
        root.insert(
            CellInstArray(
                group_root.cell_index(),
                Trans(0, int(round(group["offset_y"] * s))),
            )
        )
        _build_demo_group(
            layout=layout,
            group_cell=group_root,
            spiral_layer=spiral_layer,
            pad_layer=pad_layer,
            base_params=group["base_params"],
            sweep_name=group["sweep_name"],
            sweep_values=group["sweep_values"],
        )

    return root


if __name__ == "__main__":
    from config import DEFAULT_DBU, get_gds_path

    layout = pya.Layout()
    layout.dbu = DEFAULT_DBU
    build_spiral_ide_demo_layout(layout)

    output_path = get_gds_path("spiral_interdigitated_electrodes_demo.gds")
    layout.write(output_path)
    print(f"GDS file generated: {output_path}")
