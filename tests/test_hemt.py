import pya
import pytest

from components.hemt import HEMT


def _region(shapes):
    region = pya.Region()
    for shape in shapes:
        if isinstance(shape, pya.Region):
            region += shape
        elif isinstance(shape, (pya.Box, pya.Polygon)):
            region.insert(shape)
    return region


@pytest.mark.parametrize(
    "finger_count, expected_gate_shapes, expected_source_shapes, expected_drain_shapes",
    [(1, 6, 2, 2), (2, 5, 4, 3)],
)
def test_hemt_finger_topology_and_clearance(finger_count, expected_gate_shapes, expected_source_shapes, expected_drain_shapes):
    device = HEMT(finger_count=finger_count, show_device_label=False)
    shapes = device.generate()

    assert len(shapes["gate"]) == expected_gate_shapes
    assert len(shapes["source"]) == expected_source_shapes
    assert len(shapes["drain"]) == expected_drain_shapes
    assert (_region(shapes["gate"]) & _region(shapes["source"] + shapes["drain"])).area() == 0
    assert (_region(shapes["source"]) & _region(shapes["drain"])).area() == 0


def test_double_finger_hemt_is_symmetric_about_centerline():
    shapes = HEMT(finger_count=2, y=7.5, show_device_label=False).generate()
    gate_fingers = shapes["gate"][:2]
    source_tapers = (shapes["source"][0], shapes["source"][2])

    assert gate_fingers[0].center().y + gate_fingers[1].center().y == 2 * 7500
    assert source_tapers[0].bbox().center().y + source_tapers[1].bbox().center().y == 2 * 7500
    assert shapes["source"][0].bbox().center().x == 0
    assert shapes["source"][1].bbox().center().x == 0
    assert shapes["source"][2].bbox().center().x == 0
    assert shapes["source"][3].bbox().center().x == 0


def test_default_outer_metal_is_compact_and_filled():
    shapes = HEMT(finger_count=2, show_device_label=False).generate()
    metal = _region(shapes["source"] + shapes["drain"] + shapes["gate"])
    bbox = metal.bbox()

    assert bbox.width() <= 140_000
    assert bbox.height() <= 160_000
    # The separate outer pad remains a wide filled rectangle.
    assert shapes["source"][-1].bbox().width() == bbox.width()


def test_single_finger_has_gate_pads_on_both_sides_and_long_edge_sd_fanout():
    shapes = HEMT(finger_count=1, show_device_label=False).generate()
    left_gate_pad = shapes["gate"][2]
    right_gate_pad = shapes["gate"][4]
    source_taper = shapes["source"][0]
    drain_taper = shapes["drain"][0]

    assert left_gate_pad.center().x < 0 < right_gate_pad.center().x
    assert isinstance(shapes["gate"][3], pya.Polygon)
    assert isinstance(shapes["gate"][5], pya.Polygon)
    assert len(list(shapes["gate"][3].each_point_hull())) == 3
    assert len(list(shapes["gate"][5].each_point_hull())) == 3
    # S/D transitions are vertical and widen along the horizontal long edge.
    assert source_taper.bbox().width() > source_taper.bbox().height()
    assert drain_taper.bbox().width() > drain_taper.bbox().height()


def test_single_finger_complete_layout_is_mirror_symmetric():
    shapes = HEMT(finger_count=1, x=0.0, y=0.0, show_device_label=False).generate()
    gate_bbox = _region(shapes["gate"]).bbox()
    source_bbox = _region(shapes["source"]).bbox()
    drain_bbox = _region(shapes["drain"]).bbox()
    channel_bbox = _region(shapes["channel"]).bbox()

    assert gate_bbox.left == -gate_bbox.right
    assert channel_bbox.left == -channel_bbox.right
    assert source_bbox.left == drain_bbox.left
    assert source_bbox.right == drain_bbox.right
    assert source_bbox.bottom == -drain_bbox.top
    assert source_bbox.top == -drain_bbox.bottom


def test_hollow_fanout_reduces_transition_area_but_keeps_connectivity():
    solid = HEMT(finger_count=2, hollow_fanout=False, show_device_label=False).generate()
    hollow = HEMT(finger_count=2, hollow_fanout=True, fanout_wall_width=1.0, show_device_label=False).generate()

    solid_taper = _region([solid["source"][2]])
    hollow_taper = _region([hollow["source"][2]])
    assert 0 < hollow_taper.area() < solid_taper.area()
    assert hollow_taper.is_merged()


def test_double_gate_uses_trapezoid_and_hollowing_only_targets_upper_lower_electrodes():
    single = HEMT(finger_count=1, hollow_fanout=True, show_device_label=False).generate()
    double = HEMT(finger_count=2, hollow_fanout=True, show_device_label=False).generate()

    assert len(list(double["gate"][4].each_point_hull())) == 4
    assert all(not isinstance(shape, pya.Region) for shape in single["gate"])
    assert all(not isinstance(shape, pya.Region) for shape in double["gate"])
    assert all(not isinstance(shape, pya.Region) for shape in double["drain"])
    assert isinstance(single["source"][0], pya.Region)
    assert isinstance(single["drain"][0], pya.Region)
    assert isinstance(double["source"][2], pya.Region)
    assert HEMT().fanout_wall_width == 3.0
    assert sum(polygon.holes() for polygon in double["source"][2].each()) == 1


def test_fanout_contact_and_pad_edge_widths_are_independently_controlled():
    shapes = HEMT(
        finger_count=1,
        gate_fanout_contact_width=1.0,
        gate_fanout_pad_width=18.0,
        vertical_fanout_contact_width=26.0,
        vertical_fanout_pad_width=40.0,
        show_device_label=False,
    ).generate()

    left_gate_taper = shapes["gate"][3]
    source_taper = shapes["source"][0]
    gate_points = list(left_gate_taper.each_point_hull())
    contact_x = max(point.x for point in gate_points)
    pad_x = min(point.x for point in gate_points)
    assert max(point.y for point in gate_points if point.x == contact_x) - min(point.y for point in gate_points if point.x == contact_x) == 1_000
    assert max(point.y for point in gate_points if point.x == pad_x) - min(point.y for point in gate_points if point.x == pad_x) == 18_000

    source_points = list(source_taper.each_point_hull())
    inner_y = min(point.y for point in source_points)
    outer_y = max(point.y for point in source_points)
    assert max(point.x for point in source_points if point.y == inner_y) - min(point.x for point in source_points if point.y == inner_y) == 26_000
    assert max(point.x for point in source_points if point.y == outer_y) - min(point.x for point in source_points if point.y == outer_y) == 40_000


def test_gate_dielectric_and_layout_layers_are_generated():
    device = HEMT(finger_count=2, draw_gate_dielectric=True)
    shapes = device.generate()
    assert len(shapes["gate_dielectric"]) == 2

    layout = pya.Layout()
    layout.dbu = 0.001
    cell = device.create_cell(layout, "HEMT_TEST")
    assert not cell.bbox().empty()
    for layer_name in ("channel", "source", "gate", "gate_dielectric"):
        layer = layout.layer(device.get_layer_ids()[layer_name], 0)
        assert not cell.shapes(layer).is_empty()


@pytest.mark.parametrize(
    "mark_mode, expected_count",
    [("none", 0), ("four_corners", 4), ("corners_and_sides", 8)],
)
def test_hemt_alignment_mark_placement_modes(mark_mode, expected_count):
    device = HEMT(
        finger_count=1,
        x=10.0,
        y=-5.0,
        mark_mode=mark_mode,
        mark_shape="cross",
        mark_margin_x=12.0,
        mark_margin_y=18.0,
        show_device_label=False,
    )
    shapes = device.generate()
    assert len(shapes["alignment_marks"]) == expected_count
    if expected_count:
        centers = [(shape.bbox().center().x, shape.bbox().center().y) for shape in shapes["alignment_marks"]]
        assert min(x for x, _ in centers) < 10_000 < max(x for x, _ in centers)
        assert min(y for _, y in centers) < -5_000 < max(y for _, y in centers)


def test_alignment_marks_are_written_to_alignment_layer():
    device = HEMT(mark_mode="corners_and_sides", mark_shape="box")
    layout = pya.Layout()
    layout.dbu = 0.001
    cell = device.create_cell(layout, "HEMT_WITH_MARKS")
    mark_layer = layout.layer(device.get_layer_ids()["alignment_marks"], 0)
    assert cell.shapes(mark_layer).size() == 8


@pytest.mark.parametrize("finger_count", [1, 2])
def test_gate_fingers_cover_the_complete_symmetric_mesa(finger_count):
    shapes = HEMT(finger_count=finger_count, show_device_label=False).generate()
    mesa = shapes["channel"][0]
    assert mesa.left == -mesa.right
    assert mesa.bottom == -mesa.top
    for gate_finger in shapes["gate"][:finger_count]:
        assert gate_finger.left <= mesa.left
        assert gate_finger.right >= mesa.right


def test_gate_pad_edge_tracks_outer_metal_depth_in_auto_mode():
    small = HEMT(finger_count=1, pad_size=36.0, gate_fanout_pad_width=0.0, show_device_label=False).generate()
    large = HEMT(finger_count=1, pad_size=72.0, gate_fanout_pad_width=0.0, show_device_label=False).generate()
    small_triangle = small["gate"][3]
    large_triangle = large["gate"][3]

    assert small_triangle.bbox().height() == 36_000
    assert large_triangle.bbox().height() == 72_000


def test_vertical_contact_edge_is_narrower_than_gate_coverage():
    device = HEMT(
        finger_count=1,
        vertical_fanout_contact_width=500.0,
        gate_control_margin=2.0,
        show_device_label=False,
    )
    shapes = device.generate()
    mesa = shapes["channel"][0]
    contact_taper = shapes["source"][0]
    points = list(contact_taper.each_point_hull())
    contact_y = min(point.y for point in points)
    contact_width = max(point.x for point in points if point.y == contact_y) - min(point.x for point in points if point.y == contact_y)

    assert contact_width == mesa.width() - 4_000
    assert contact_width < shapes["gate"][0].width()


@pytest.mark.parametrize("finger_count", [1, 2])
def test_explicit_mesa_width_can_define_a_narrower_channel(finger_count):
    device = HEMT(
        finger_count=finger_count,
        gate_width=20.0,
        mesa_width=8.0,
        gate_control_margin=1.0,
        show_device_label=False,
    )
    shapes = device.generate()
    mesa = shapes["channel"][0]
    source_taper = shapes["source"][0]
    points = list(source_taper.each_point_hull())
    contact_y = min(point.y for point in points) if finger_count == 1 else max(point.y for point in points)
    contact_width = max(point.x for point in points if point.y == contact_y) - min(point.x for point in points if point.y == contact_y)

    assert mesa.width() == 8_000
    assert mesa.width() < 20_000
    assert contact_width <= 6_000
    for gate_finger in shapes["gate"][:finger_count]:
        assert gate_finger.left <= mesa.left
        assert gate_finger.right >= mesa.right


def test_explicit_mesa_width_must_leave_room_for_gate_control_margin():
    with pytest.raises(ValueError, match="Gate Control Margin"):
        HEMT(mesa_width=1.0, gate_control_margin=0.6).generate()


@pytest.mark.parametrize("mesa_width", [3.0, 4.0, 6.0, 8.0, 10.0, 20.0])
@pytest.mark.parametrize("hollow_fanout", [False, True])
def test_narrow_double_finger_mesa_has_no_sd_or_gate_interference(mesa_width, hollow_fanout):
    shapes = HEMT(
        finger_count=2,
        mesa_width=mesa_width,
        gate_control_margin=1.0,
        hollow_fanout=hollow_fanout,
        show_device_label=False,
    ).generate()
    source = _region(shapes["source"])
    drain = _region(shapes["drain"])
    gate = _region(shapes["gate"])

    assert (source & drain).area() == 0
    assert (gate & (source + drain)).area() == 0


@pytest.mark.parametrize("finger_count", [0, 3])
def test_only_single_and_double_finger_are_allowed(finger_count):
    with pytest.raises(ValueError, match="finger_count"):
        HEMT(finger_count=finger_count)
