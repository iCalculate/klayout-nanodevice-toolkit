import klayout.db as db
import pytest

from components.crossbar import CrossBar


def _shapes(layout, cell, layer_id):
    return list(cell.shapes(layout.layer(layer_id, 0)).each())


def test_n_plus_m_pads_control_n_times_m_crossings():
    layout = db.Layout()
    layout.dbu = 0.001
    n, m = 3, 2
    device = CrossBar(layout=layout, x_num=n, y_num=m)
    cell = device.create_array_cell()
    expected_layers = {
        "bottom_gate": 11, "bottom_dielectric": 12,
        "top_dielectric": 17, "top_gate": 18,
        "pad": 41, "note": 6, "alignment_marks": 3,
    }
    assert device.get_layer_ids() == expected_layers
    assert len(_shapes(layout, cell, 11)) == m * 3  # M rows: bar+taper+pad
    assert len(_shapes(layout, cell, 18)) == n * 3  # N cols: bar+taper+pad
    assert len(_shapes(layout, cell, 12)) == n * m
    assert len(_shapes(layout, cell, 17)) == n * m
    assert len(_shapes(layout, cell, 41)) == n + m
    assert len(_shapes(layout, cell, 3)) == (n - 1) * (m - 1) * 2


def test_shared_lines_span_all_crossings():
    layout = db.Layout()
    layout.dbu = 0.001
    device = CrossBar(
        layout=layout, x_num=3, y_num=2, x_pitch=10, y_pitch=12,
        array_pad_size=6, show_center_mark=False,
    )
    cell = device.create_array_cell()
    bottom_bars = [
        s.bbox() for s in _shapes(layout, cell, 11)
        if s.bbox().left < 0 < s.bbox().right
    ]
    top_bars = [
        s.bbox() for s in _shapes(layout, cell, 18)
        if s.bbox().bottom < 0 < s.bbox().top
    ]
    assert len(bottom_bars) == 2
    assert len(top_bars) == 3
    assert all(box.left < -10_000 and box.right > 10_000 for box in bottom_bars)
    assert all(box.bottom < -6_000 and box.top > 6_000 for box in top_bars)


def test_equal_and_gradient_width_modes():
    equal = CrossBar(
        x_num=3, y_num=4, array_mode="equal",
        horizontal_bar_width=1.5, horizontal_bar_width_end=8.0,
        vertical_bar_width=2.5, vertical_bar_width_end=9.0,
    )
    assert equal.horizontal_widths() == [1.5] * 4
    assert equal.vertical_widths() == [2.5] * 3
    gradient = CrossBar(
        x_num=3, y_num=4, array_mode="gradient",
        horizontal_bar_width=1.0, horizontal_bar_width_end=4.0,
        vertical_bar_width=2.0, vertical_bar_width_end=6.0,
    )
    assert gradient.horizontal_widths() == pytest.approx([1.0, 2.0, 3.0, 4.0])
    assert gradient.vertical_widths() == pytest.approx([2.0, 4.0, 6.0])


def test_each_crossing_has_independently_extended_dielectrics():
    layout = db.Layout()
    layout.dbu = 0.001
    device = CrossBar(
        layout=layout, x_num=1, y_num=1,
        horizontal_bar_width=2.0, vertical_bar_width=4.0,
        bottom_dielectric_extension_x=3.0, bottom_dielectric_extension_y=4.0,
        top_dielectric_extension_x=5.0, top_dielectric_extension_y=6.0,
    )
    cell = device.create_array_cell(x=10.0, y=-5.0)
    assert _shapes(layout, cell, 12)[0].bbox() == db.Box(5_000, -10_000, 15_000, 0)
    assert _shapes(layout, cell, 17)[0].bbox() == db.Box(3_000, -12_000, 17_000, 2_000)


def test_array_style_options_control_pads_grid_and_center_mark():
    layout = db.Layout()
    layout.dbu = 0.001
    device = CrossBar(
        layout=layout,
        x_num=2,
        y_num=3,
        pad_connection_style="block",
        show_pixel_outline=True,
        note_text_enabled=False,
        center_mark_size=12.0,
        center_mark_width=2.0,
        center_mark_offset_x=4.0,
    )
    cell = device.create_array_cell()
    assert len(_shapes(layout, cell, 41)) == 5
    assert len(_shapes(layout, cell, 6)) == 6
    mark_boxes = [shape.bbox() for shape in _shapes(layout, cell, 3)]
    assert len(mark_boxes) == (2 - 1) * (3 - 1) * 2
    assert db.Box(-2_000, -16_000, 10_000, -14_000) in mark_boxes
    assert db.Box(3_000, -21_000, 5_000, -9_000) in mark_boxes


def test_horizontal_and_vertical_pad_sides_are_independent():
    layout = db.Layout()
    layout.dbu = 0.001
    device = CrossBar(
        layout=layout, x_num=3, y_num=2,
        horizontal_pad_side="right", vertical_pad_side="bottom",
    )
    cell = device.create_array_cell()
    pad_boxes = [shape.bbox() for shape in _shapes(layout, cell, 41)]
    assert any(box.left > 30_000 for box in pad_boxes)
    assert any(box.top < -15_000 for box in pad_boxes)
    assert not any(box.right < -30_000 for box in pad_boxes)
    assert not any(box.bottom > 15_000 for box in pad_boxes)
    assert len(pad_boxes) == 5


@pytest.mark.parametrize("mark_type, expected_shapes", [
    ("cross", 2), ("box", 4), ("diamond", 1), ("circle", 1),
    ("triangle", 1), ("l_shape", 2), ("t_shape", 2),
])
def test_selectable_mark_types_are_placed_in_a_blank_grid_interval(mark_type, expected_shapes):
    layout = db.Layout()
    layout.dbu = 0.001
    device = CrossBar(layout=layout, x_num=3, y_num=3, center_mark_type=mark_type)
    cell = device.create_array_cell()
    marks = _shapes(layout, cell, 3)
    assert len(marks) == (3 - 1) * (3 - 1) * expected_shapes
    dielectric_regions = db.Region()
    for layer_id in (12, 17):
        for shape in _shapes(layout, cell, layer_id):
            dielectric_regions.insert(shape.polygon if shape.is_polygon() else shape.box)
    for shape in marks:
        mark_region = db.Region(shape.polygon if shape.is_polygon() else shape.box)
        assert (mark_region & dielectric_regions).area() == 0


def test_mark_interval_skip_subsamples_grid_gaps_in_both_directions():
    layout = db.Layout()
    layout.dbu = 0.001
    device = CrossBar(
        layout=layout,
        x_num=6,
        y_num=5,
        center_mark_type="diamond",
        mark_interval_skip=1,
    )
    cell = device.create_array_cell()
    # Five X gaps -> indices 0,2,4; four Y gaps -> indices 0,2.
    assert len(_shapes(layout, cell, 3)) == 3 * 2


@pytest.mark.parametrize("kwargs, message", [
    ({"x_num": 0}, "x_num"),
    ({"array_mode": "log"}, "array_mode"),
    ({"x_num": 2, "x_pitch": 2.0, "vertical_bar_width": 2.0}, "x_pitch"),
    ({"y_num": 2, "y_pitch": 2.0, "horizontal_bar_width": 2.0}, "y_pitch"),
    ({"bottom_dielectric_extension_x": 0.0}, "minimum overlap"),
    ({"pad_connection_style": "taper"}, "pad_connection_style"),
    ({"center_mark_size": 4.0, "center_mark_width": 5.0}, "center_mark_width"),
    ({"horizontal_pad_side": "top"}, "horizontal_pad_side"),
    ({"vertical_pad_side": "left"}, "vertical_pad_side"),
    ({"center_mark_type": "star"}, "center_mark_type"),
    ({"mark_interval_skip": -1}, "mark_interval_skip"),
])
def test_rejects_invalid_or_pdk_unsafe_geometry(kwargs, message):
    with pytest.raises(ValueError, match=message):
        CrossBar(**kwargs)
