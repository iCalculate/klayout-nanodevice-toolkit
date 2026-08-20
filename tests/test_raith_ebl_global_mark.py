# -*- coding: utf-8 -*-

import os
import sys

import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config import DEFAULT_UNIT_SCALE
from components.markarray import MarkArrayBuilder, build_raith_ebl_global_mark_layout


def _square_centers_um(cell, layer_index, side_um):
    centers = []
    target = side_um * DEFAULT_UNIT_SCALE
    for shape in cell.shapes(layer_index).each():
        bbox = shape.bbox()
        if bbox.width() == pytest.approx(target) and bbox.height() == pytest.approx(target):
            centers.append((bbox.center().x / DEFAULT_UNIT_SCALE, bbox.center().y / DEFAULT_UNIT_SCALE))
    return sorted(centers)


def test_sw_uses_only_outward_third_quadrant_satellites():
    layout, cell = build_raith_ebl_global_mark_layout(
        center_x=0.0,
        center_y=0.0,
        span_x=1000.0,
        span_y=800.0,
        enabled_positions={
            "tl": False,
            "tc": False,
            "tr": False,
            "cl": False,
            "cc": False,
            "cr": False,
            "bl": True,
            "bc": False,
            "br": False,
        },
        enable_corner_text=False,
    )

    mark_layer = layout.find_layer(3, 0)
    manual_layer = layout.find_layer(63, 0)
    assert _square_centers_um(cell, mark_layer, 20.0) == [(-1120.0, -920.0), (-1060.0, -860.0)]
    assert _square_centers_um(cell, manual_layer, 100.0) == [(-1120.0, -920.0), (-1060.0, -860.0)]
    assert cell.shapes(layout.find_layer(4, 0)).size() == 4


def test_side_marks_use_both_outward_quadrants():
    layout, cell = build_raith_ebl_global_mark_layout(
        span_x=1000.0,
        span_y=800.0,
        enabled_positions={
            "tl": False,
            "tc": False,
            "tr": False,
            "cl": True,
            "cc": False,
            "cr": False,
            "bl": False,
            "bc": False,
            "br": False,
        },
        enable_corner_text=False,
    )

    manual_layer = layout.find_layer(63, 0)
    assert _square_centers_um(cell, manual_layer, 100.0) == [
        (-1120.0, -120.0),
        (-1120.0, 120.0),
        (-1060.0, -60.0),
        (-1060.0, 60.0),
    ]


def test_center_is_disabled_by_default_and_uses_all_quadrants_when_enabled():
    layout, cell = build_raith_ebl_global_mark_layout(enable_corner_text=False)
    manual_layer = layout.find_layer(63, 0)
    assert len(_square_centers_um(cell, manual_layer, 100.0)) == 24

    layout, cell = build_raith_ebl_global_mark_layout(
        enabled_positions={"cc": True},
        enable_corner_text=False,
    )
    manual_layer = layout.find_layer(63, 0)
    assert len(_square_centers_um(cell, manual_layer, 100.0)) == 32


def test_manual_boxes_remain_centered_when_sizes_are_customized():
    layout, cell = build_raith_ebl_global_mark_layout(
        enabled_positions={
            "tl": False,
            "tc": False,
            "tr": True,
            "cl": False,
            "cc": False,
            "cr": False,
            "bl": False,
            "bc": False,
            "br": False,
        },
        small_square_size=24.0,
        manual_box_size=110.0,
        enable_corner_text=False,
    )
    mark_centers = _square_centers_um(cell, layout.find_layer(3, 0), 24.0)
    manual_centers = _square_centers_um(cell, layout.find_layer(63, 0), 110.0)
    assert mark_centers == manual_centers


def test_far_offset_is_always_twice_the_near_offset():
    layout, cell = build_raith_ebl_global_mark_layout(
        span_x=1000.0,
        span_y=800.0,
        satellite_near_offset=75.0,
        enabled_positions={
            "tl": False,
            "tc": False,
            "tr": False,
            "cl": False,
            "cc": False,
            "cr": False,
            "bl": True,
            "bc": False,
            "br": False,
        },
        enable_corner_text=False,
    )
    mark1_layer = layout.find_layer(3, 0)
    assert _square_centers_um(cell, mark1_layer, 20.0) == [(-1150.0, -950.0), (-1075.0, -875.0)]


def test_corner_text_uses_raith_uv_and_delta_format_only_for_corners():
    builder = MarkArrayBuilder()
    rendered_text = []
    builder._deplof_text = lambda value, *_args, **_kwargs: rendered_text.append(value) or []
    builder.build_raith_ebl_global_mark(
        center_x=10.0,
        center_y=20.0,
        span_x=1000.0,
        span_y=800.0,
        satellite_near_offset=60.0,
        enabled_positions={
            "tl": False,
            "tc": False,
            "tr": False,
            "cl": True,
            "cc": False,
            "cr": False,
            "bl": True,
            "bc": False,
            "br": False,
        },
    )

    assert rendered_text == ["u: -990.0\nv: -780.0\nm: 60", "SW"]
