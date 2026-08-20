import math

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


def test_zero_lsg_and_lgd_are_allowed_and_make_contact_edges_touch():
    shapes = HEMT(
        finger_count=2,
        source_gate_spacing=0.0,
        gate_drain_spacing=0.0,
        split_ebl_exposure=True,
        show_device_label=False,
    ).generate()

    lower_source = _region([shapes["source_fine"][0]])
    lower_gate = _region([shapes["gate_fine"][0]])
    centre_drain = _region(shapes["drain_fine"])
    assert lower_source.bbox().top == lower_gate.bbox().bottom
    assert lower_gate.bbox().top == centre_drain.bbox().bottom
    assert (lower_source & lower_gate).area() == 0
    assert (lower_gate & centre_drain).area() == 0


def test_gate_source_and_gate_drain_overlap_lengths_are_exact():
    shapes = HEMT(
        finger_count=2,
        gate_length=8.0,
        source_gate_spacing=0.0,
        gate_drain_spacing=0.0,
        source_gate_overlap=0.6,
        gate_drain_overlap=0.8,
        split_ebl_exposure=True,
        show_device_label=False,
    ).generate()

    lower_source = _region([shapes["source_fine"][0]])
    lower_gate = _region([shapes["gate_fine"][0]])
    centre_drain = _region(shapes["drain_fine"])
    assert (lower_source & lower_gate).bbox().height() == 600
    assert (lower_gate & centre_drain).bbox().height() == 800


def test_overlap_extends_gate_edges_without_moving_source_or_drain():
    common = dict(
        finger_count=2,
        gate_length=8.0,
        source_gate_spacing=0.0,
        gate_drain_spacing=0.0,
        split_ebl_exposure=True,
        show_device_label=False,
    )
    baseline = HEMT(**common).generate()
    extended = HEMT(
        **common,
        source_gate_overlap=0.6,
        gate_drain_overlap=0.8,
    ).generate()

    assert (_region(baseline["source"] + baseline["source_fine"]) ^ _region(extended["source"] + extended["source_fine"])).area() == 0
    assert (_region(baseline["drain"] + baseline["drain_fine"]) ^ _region(extended["drain"] + extended["drain_fine"])).area() == 0
    baseline_gate = baseline["gate_fine"][0]
    extended_gate = extended["gate_fine"][0]
    assert extended_gate.bottom == baseline_gate.bottom - 600
    assert extended_gate.top == baseline_gate.top + 800
    assert extended_gate.height() == baseline_gate.height() + 1_400


def test_gate_overlap_may_extend_beyond_the_complete_channel():
    shapes = HEMT(
        finger_count=2,
        source_gate_overlap=20.0,
        gate_drain_overlap=20.0,
        split_ebl_exposure=True,
        show_device_label=False,
    ).generate()

    assert shapes["gate_fine"][0].height() == 40_200


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


@pytest.mark.parametrize(
    "finger_count, fine_source_count, fine_drain_count, fine_gate_count",
    [(1, 1, 1, 2), (2, 2, 1, 3)],
)
def test_split_ebl_moves_only_core_metal_to_corresponding_fine_layers(
    finger_count, fine_source_count, fine_drain_count, fine_gate_count
):
    device = HEMT(
        finger_count=finger_count,
        split_ebl_exposure=True,
        show_device_label=False,
    )
    shapes = device.generate()

    assert len(shapes["source_fine"]) == fine_source_count
    assert len(shapes["drain_fine"]) == fine_drain_count
    assert len(shapes["gate_fine"]) == fine_gate_count
    assert device.get_layer_ids()["source_fine"] == 26
    assert device.get_layer_ids()["drain_fine"] == 26
    assert device.get_layer_ids()["gate_fine"] == 28


def test_split_ebl_is_disabled_by_default():
    shapes = HEMT(show_device_label=False).generate()

    assert shapes["source_fine"] == []
    assert shapes["drain_fine"] == []
    assert shapes["gate_fine"] == []


@pytest.mark.parametrize("finger_count", [1, 2])
def test_split_ebl_outer_electrode_is_an_open_ended_fine_u(finger_count):
    split = HEMT(
        finger_count=finger_count,
        split_ebl_exposure=True,
        fine_fanout_depth=12.0,
        fine_fanout_width=1.0,
        show_device_label=False,
    ).generate()

    fine_u = _region([split["source_fine"][0]])
    bbox = fine_u.bbox()
    if bbox.center().y < 0:
        outer_slice = pya.Box(bbox.left, bbox.bottom, bbox.right, bbox.bottom + 1_000)
    else:
        outer_slice = pya.Box(bbox.left, bbox.top - 1_000, bbox.right, bbox.top)
    # The inner contact joins both arms into one U, while its open outer end
    # intersects a transverse slice as two separate legs.
    assert fine_u.size() == 1
    assert (fine_u & pya.Region(outer_slice)).size() == 2


def test_fine_u_depth_and_arm_width_are_independently_adjustable():
    shallow = HEMT(
        finger_count=2,
        split_ebl_exposure=True,
        fine_fanout_depth=6.0,
        fine_fanout_width=0.6,
        show_device_label=False,
    ).generate()["source_fine"][0]
    deep = HEMT(
        finger_count=2,
        split_ebl_exposure=True,
        fine_fanout_depth=12.0,
        fine_fanout_width=0.6,
        show_device_label=False,
    ).generate()["source_fine"][0]
    wide = HEMT(
        finger_count=2,
        split_ebl_exposure=True,
        fine_fanout_depth=12.0,
        fine_fanout_width=1.2,
        show_device_label=False,
    ).generate()["source_fine"][0]

    assert deep.bbox().height() - shallow.bbox().height() == 6_000
    assert wide.area() > deep.area()


def test_fwid_controls_both_source_and_drain_fine_u_line_widths():
    common = dict(
        finger_count=2,
        split_ebl_exposure=True,
        show_device_label=False,
    )
    narrow = HEMT(**common, fine_fanout_width=0.6).generate()
    wide = HEMT(**common, fine_fanout_width=1.2).generate()

    assert _region(wide["source_fine"]).area() > _region(narrow["source_fine"]).area()
    assert _region(wide["drain_fine"]).area() > _region(narrow["drain_fine"]).area()


def test_double_finger_centre_drain_is_a_u_open_towards_coarse_fanout():
    shapes = HEMT(
        finger_count=2,
        split_ebl_exposure=True,
        fine_fanout_width=1.0,
        show_device_label=False,
    ).generate()

    drain_u = _region(shapes["drain_fine"])
    bbox = drain_u.bbox()
    open_end = drain_u & pya.Region(
        pya.Box(bbox.right - 1_000, bbox.bottom, bbox.right, bbox.top)
    )
    assert drain_u.area() < bbox.area()
    assert open_end.size() == 2


def test_split_ebl_adds_finite_overlap_at_all_coarse_fine_transitions():
    split = HEMT(
        finger_count=2,
        split_ebl_exposure=True,
        ebl_overlap=2.0,
        show_device_label=False,
    ).generate()

    assert (_region([split["source"][0]]) & _region([split["source_fine"][0]])).area() > 0
    assert (_region(split["drain"]) & _region(split["drain_fine"])).area() > 0
    assert (_region(split["gate"]) & _region(split["gate_fine"])).area() > 0


def test_fine_u_and_coarse_fanout_share_one_continuous_outer_envelope():
    split = HEMT(
        finger_count=2,
        split_ebl_exposure=True,
        ebl_overlap=2.0,
        show_device_label=False,
    ).generate()

    joined = (_region([split["source_fine"][0]]) + _region([split["source"][0]])).merged()
    hull_points = list(next(joined.each()).each_point_hull())
    left_half = hull_points[: len(hull_points) // 2]
    inner_vertical = next(
        index
        for index in range(len(left_half) - 1)
        if left_half[index].x == left_half[index + 1].x
    )
    left_side = left_half[: inner_vertical + 1]
    outer, inner = left_side[0], left_side[-1]
    side_length = math.hypot(inner.x - outer.x, inner.y - outer.y)
    for seam in left_side[1:-1]:
        distance = abs(
            (inner.x - outer.x) * (outer.y - seam.y)
            - (outer.x - seam.x) * (inner.y - outer.y)
        ) / side_length
        assert distance <= 1.0  # one 1 nm database unit
    assert all(a.y != b.y for a, b in zip(left_side, left_side[1:]))


def test_double_finger_gate_pad_retraction_creates_configured_gap():
    shapes = HEMT(
        finger_count=2,
        split_ebl_exposure=True,
        gate_pad_retraction=3.5,
        show_device_label=False,
    ).generate()

    gate_manifold = shapes["gate_fine"][2]
    centre_drain = shapes["drain_fine"][0].bbox()
    assert centre_drain.left - gate_manifold.right == 3_500


def test_gate_pad_retraction_does_not_move_contact_inner_electrode_or_gate_fingers():
    aligned = HEMT(
        finger_count=2,
        gate_pad_retraction=0.0,
        show_device_label=False,
    ).generate()
    separated = HEMT(
        finger_count=2,
        gate_pad_retraction=4.0,
        show_device_label=False,
    ).generate()

    assert aligned["drain"][0] == separated["drain"][0]
    assert aligned["gate"][:2] == separated["gate"][:2]
    assert aligned["gate"][2].left == separated["gate"][2].left
    assert aligned["gate"][2].right - separated["gate"][2].right == 4_000


def test_gate_pad_retraction_cannot_consume_the_complete_gate_pad():
    with pytest.raises(ValueError, match="no usable gate pad width"):
        HEMT(finger_count=2, gate_pad_retraction=10_000.0).generate()


def test_double_finger_center_drain_and_outer_sources_all_use_u_frames():
    split = HEMT(
        finger_count=2,
        split_ebl_exposure=True,
        show_device_label=False,
    ).generate()

    assert isinstance(split["drain_fine"][0], pya.Region)
    assert all(isinstance(shape, pya.Region) for shape in split["source_fine"])


def test_split_ebl_requires_nonzero_u_arm_width():
    with pytest.raises(ValueError, match="fine_fanout_width"):
        HEMT(split_ebl_exposure=True, fine_fanout_width=0.0)


def test_double_drain_u_requires_room_for_a_real_cavity():
    with pytest.raises(ValueError, match="less than half ohmic_width"):
        HEMT(
            finger_count=2,
            split_ebl_exposure=True,
            ohmic_width=4.0,
            fine_fanout_width=2.0,
        )


def test_split_ebl_writes_fine_metal_to_layers_26_and_28():
    device = HEMT(split_ebl_exposure=True, show_device_label=False)
    layout = pya.Layout()
    layout.dbu = 0.001
    cell = device.create_cell(layout, "HEMT_SPLIT_EBL")

    assert not cell.shapes(layout.layer(26, 0)).is_empty()
    assert not cell.shapes(layout.layer(28, 0)).is_empty()


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
