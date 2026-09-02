import math

import pytest
import pya

from components.tlm import TLM
from utils.fanout_utils import draw_pad, draw_tangent_fanout


def _region(cell, layer_id):
    region = pya.Region()
    for shape in cell.shapes(cell.layout().layer(layer_id, 0)).each():
        if shape.is_box():
            region.insert(shape.box)
        elif shape.is_polygon():
            region.insert(shape.polygon)
        elif shape.is_path():
            region.insert(shape.path.polygon())
    return region.merged()


def _device(**kwargs):
    layout = pya.Layout()
    layout.dbu = 0.001
    params = {
        "num_electrodes": 6,
        "add_alignment_mark": False,
        "label_text": "",
    }
    params.update(kwargs)
    device = TLM(
        layout=layout,
        **params,
    )
    return device, device.create_single_device("TLM_TEST")


def test_tangent_fanout_uses_outer_edge_endpoints_and_inner_incircle_tangencies():
    bridge = draw_pad((0.0, 20.0), 10.0, 10.0)
    outer = draw_pad((0.0, 100.0), 60.0, 60.0, chamfer_size=6.0, chamfer_type="straight")
    fanout = draw_tangent_fanout(bridge, outer, outer_edge="D")
    points = list(fanout.each_point_hull())

    assert len(points) == 4
    outer_points = [point for point in points if point.y == 70_000]
    tangent_points = [point for point in points if point.y != 70_000]
    assert {(point.x, point.y) for point in outer_points} == {(-24_000, 70_000), (24_000, 70_000)}
    assert len(tangent_points) == 2
    for tangent in tangent_points:
        radius = math.hypot(tangent.x, tangent.y - 20_000)
        assert radius == pytest.approx(5_000, abs=1.0)
        matching_outer = min(outer_points, key=lambda point: abs(point.x - tangent.x))
        radial = (tangent.x, tangent.y - 20_000)
        tangent_line = (matching_outer.x - tangent.x, matching_outer.y - tangent.y)
        assert radial[0] * tangent_line[0] + radial[1] * tangent_line[1] == pytest.approx(0, abs=60_000)


def test_split_ebl_is_disabled_by_default():
    device, cell = _device()

    assert device.get_layer_ids()["fine_source_drain"] == 25
    assert _region(cell, 25).is_empty()
    assert not _region(cell, 15).is_empty()


def test_split_ebl_separates_fine_contacts_from_coarse_pads_and_fanout():
    device, cell = _device(split_ebl_exposure=True)
    layers = device.get_layer_ids()
    fine = _region(cell, layers["fine_source_drain"])
    coarse = _region(cell, layers["source_drain"])
    channel = _region(cell, layers["channel"])

    assert not fine.is_empty()
    assert not coarse.is_empty()
    assert not (fine & channel).is_empty()
    assert (coarse & channel).is_empty()


def test_split_ebl_bridge_has_configured_concentric_fine_landing():
    device, cell = _device(
        split_ebl_exposure=True,
        inner_pad_length=2.0,
        bridge_pad_size=14.0,
        fine_route_width=1.0,
        fine_landing_size=6.0,
    )
    layers = device.get_layer_ids()
    fine = _region(cell, layers["fine_source_drain"])
    coarse = _region(cell, layers["source_drain"])

    fine_squares = []
    for shape in cell.shapes(cell.layout().layer(layers["fine_source_drain"], 0)).each():
        if not (shape.is_polygon() or shape.is_box()):
            continue
        polygon = shape.polygon if shape.is_polygon() else pya.Polygon(shape.box)
        bbox = polygon.bbox()
        if abs(bbox.width() - 6_000) <= 1 and abs(bbox.height() - 6_000) <= 1:
            fine_squares.append(bbox)

    assert len(fine_squares) == 6
    assert (fine & coarse).area() >= 6 * 6_000 * 6_000

    landing_centres = {(box.center().x, box.center().y) for box in fine_squares}
    fine_paths = [
        shape.path
        for shape in cell.shapes(cell.layout().layer(layers["fine_source_drain"], 0)).each()
        if shape.is_path()
    ]
    assert len(fine_paths) == 6
    for path in fine_paths:
        endpoint = list(path.each_point())[-1]
        assert any(
            abs(endpoint.x - centre_x) <= 1 and abs(endpoint.y - centre_y) <= 1
            for centre_x, centre_y in landing_centres
        )


def test_split_ebl_layer_follows_the_corresponding_second_stack_layer():
    device, cell = _device(
        split_ebl_exposure=True,
        source_drain_layer_id=16,
    )

    assert device.get_layer_ids()["fine_source_drain"] == 26
    assert not _region(cell, 26).is_empty()
    assert _region(cell, 25).is_empty()


@pytest.mark.parametrize("distribution", ["linear", "log", "exp", "inv"])
@pytest.mark.parametrize("spacing_mode", ["centered", "left_to_right"])
def test_ebl_mode_supports_all_spacing_step_modes(distribution, spacing_mode):
    device, cell = _device(
        split_ebl_exposure=True,
        distribution=distribution,
        spacing_mode=spacing_mode,
    )

    assert len(device.generate_electrode_positions()) == 6
    layers = device.get_layer_ids()
    assert _region(cell, layers["fine_source_drain"]).size() == 6
    assert _region(cell, layers["source_drain"]).size() == 6


def test_split_ebl_rejects_fine_landing_larger_than_bridge_pad():
    with pytest.raises(ValueError, match="fine_landing_size"):
        _device(split_ebl_exposure=True, bridge_pad_size=2.0, fine_landing_size=3.0)


def test_bridge_pads_are_square_compact_and_close_to_the_channel():
    device, cell = _device(
        split_ebl_exposure=True,
        channel_width=10.0,
        inner_pad_length=2.0,
        bridge_pad_size=10.0,
        bridge_pad_spacing=2.0,
        bridge_pad_v_step=0.0,
        fine_fanout_length=2.0,
    )
    coarse_shapes = [
        shape.polygon if shape.is_polygon() else pya.Polygon(shape.box)
        for shape in cell.shapes(cell.layout().layer(device.get_layer_ids()["source_drain"], 0)).each()
        if shape.is_polygon() or shape.is_box()
    ]
    bridge_boxes = [
        polygon.bbox()
        for polygon in coarse_shapes
        if abs(polygon.bbox().width() - 10_000) <= 1 and abs(polygon.bbox().height() - 10_000) <= 1
        and abs(polygon.bbox().center().y) < 30_000
    ]

    assert len(bridge_boxes) == 6
    rows = {}
    for box in bridge_boxes:
        rows.setdefault(box.center().y, []).append(box.center().x)
    assert len(rows) == 2
    for centers in rows.values():
        ordered = sorted(centers)
        assert all(right - left >= 12_000 for left, right in zip(ordered, ordered[1:]))
        assert max(abs(center) for center in ordered) < 30_000
    # The requested 2 um is a minimum; three 1 um routes, 1 um clearance,
    # and the default 5 um overlay need a 10 um routing band.
    assert sorted({abs(box.p1.y) for box in bridge_boxes})[0] == 16_000


def test_split_ebl_uses_constant_width_manhattan_routes_without_interference():
    device, cell = _device(
        split_ebl_exposure=True,
        inner_pad_length=2.0,
        fine_route_width=1.0,
        route_clearance=1.0,
    )
    layers = device.get_layer_ids()
    fine_paths = [
        shape.path
        for shape in cell.shapes(cell.layout().layer(layers["fine_source_drain"], 0)).each()
        if shape.is_path()
    ]
    assert len(fine_paths) == 6
    assert {path.width for path in fine_paths} == {1_000}
    for path in fine_paths:
        points = list(path.each_point())
        assert all(
            first.x == second.x or first.y == second.y
            for first, second in zip(points, points[1:])
        )
    expanded_routes = [pya.Region(path.polygon()).sized(500) for path in fine_paths]
    assert all(
        (expanded_routes[first] & expanded_routes[second]).is_empty()
        for first in range(len(expanded_routes))
        for second in range(first + 1, len(expanded_routes))
    )
    assert _region(cell, layers["fine_source_drain"]).size() == 6
    assert _region(cell, layers["source_drain"]).size() == 6


def test_rectangular_frame_routes_preserve_the_requested_clearance():
    device, cell = _device(
        num_electrodes=12,
        inner_pad_length=2.0,
        split_ebl_exposure=True,
        outer_pad_layout="rectangular_frame",
        fine_route_width=1.0,
        route_clearance=1.0,
    )
    fine_layer = cell.layout().layer(device.get_layer_ids()["fine_source_drain"], 0)
    paths = [shape.path for shape in cell.shapes(fine_layer).each() if shape.is_path()]
    expanded_routes = [pya.Region(path.polygon()).sized(500) for path in paths]

    assert len(paths) == 12
    assert all(
        (expanded_routes[first] & expanded_routes[second]).is_empty()
        for first in range(len(expanded_routes))
        for second in range(first + 1, len(expanded_routes))
    )


def test_five_bridge_pads_per_row_follow_adjustable_v_levels():
    device, _cell = _device(
        num_electrodes=12,
        split_ebl_exposure=True,
        outer_pad_layout="rectangular_frame",
        bridge_pad_v_step=4.0,
    )
    xs = device.generate_electrode_positions()
    sides = device._pad_side_assignments(len(xs))
    pad_width = device._resolved_inner_pad_width()
    channel_length = device._resolved_channel_length(xs)
    max_group = max(sides.count(side) for side in ("top", "bottom", "left", "right"))
    gap = max(
        device.fine_fanout_length,
        device.bridge_pad_size / 2.0
        + (max_group - 1) * (device.fine_route_width + device.route_clearance)
        + device.fine_route_width,
    )
    centres = device._bridge_pad_centers(xs, sides, 0.0, 0.0, pad_width, channel_length, gap)

    top_y = [centres[index][1] for index, side in enumerate(sides) if side == "top"]
    bottom_y = [centres[index][1] for index, side in enumerate(sides) if side == "bottom"]
    assert [value - min(top_y) for value in top_y] == pytest.approx([0, 4, 8, 4, 0])
    assert [max(bottom_y) - value for value in bottom_y] == pytest.approx([0, 4, 8, 4, 0])


@pytest.mark.parametrize("mark_type", ["chessboard", "bonecross", "split_bonecross", "cross"])
def test_optional_nanomark_geometry_is_etched_from_each_bridge_pad(mark_type):
    plain_device, plain_cell = _device(split_ebl_exposure=True)
    etched_device, etched_cell = _device(
        split_ebl_exposure=True,
        bridge_center_mark_enabled=True,
        bridge_center_mark_type=mark_type,
        bridge_center_mark_size=4.0,
        bridge_center_mark_width=0.8,
    )
    plain = _region(plain_cell, plain_device.get_layer_ids()["source_drain"])
    etched = _region(etched_cell, etched_device.get_layer_ids()["source_drain"])

    assert etched.area() < plain.area()
    assert etched.size() == etched_device.num_electrodes


def test_rectangular_frame_side_pads_are_inset_to_the_horizontal_frame_boundary():
    device, cell = _device(
        num_electrodes=12,
        split_ebl_exposure=True,
        outer_pad_layout="rectangular_frame",
    )
    coarse_layer = cell.layout().layer(device.get_layer_ids()["source_drain"], 0)
    outer_boxes = []
    for shape in cell.shapes(coarse_layer).each():
        polygon = shape.polygon if shape.is_polygon() else pya.Polygon(shape.box) if shape.is_box() else None
        if polygon is not None and polygon.bbox().width() == 60_000 and polygon.bbox().height() == 60_000:
            outer_boxes.append(polygon.bbox())
    top_boxes = [box for box in outer_boxes if box.center().y > 0]
    left_box = min(outer_boxes, key=lambda box: box.center().x)
    right_box = max(outer_boxes, key=lambda box: box.center().x)

    assert left_box.left == min(box.left for box in top_boxes)
    assert right_box.right == max(box.right for box in top_boxes)


def test_many_electrodes_auto_use_an_isolated_rectangular_outer_pad_frame():
    device, cell = _device(
        num_electrodes=12,
        inner_pad_length=2.0,
        split_ebl_exposure=True,
        outer_pad_layout="auto",
        outer_pad_frame_threshold=10,
    )
    coarse_layer = device.get_layer_ids()["source_drain"]
    outer_boxes = []
    for shape in cell.shapes(cell.layout().layer(coarse_layer, 0)).each():
        polygon = shape.polygon if shape.is_polygon() else pya.Polygon(shape.box) if shape.is_box() else None
        if polygon is None:
            continue
        bbox = polygon.bbox()
        if bbox.width() == 60_000 and bbox.height() == 60_000:
            outer_boxes.append(bbox)

    assert len(outer_boxes) == 12
    assert any(box.center().x < -100_000 for box in outer_boxes)
    assert any(box.center().x > 100_000 for box in outer_boxes)
    assert any(box.center().y == 100_000 for box in outer_boxes)
    assert any(box.center().y == -100_000 for box in outer_boxes)
    coarse_region = _region(cell, coarse_layer)
    assert coarse_region.size() == 12
    assert coarse_region.sized(500).merged().size() == 12

    bridge_boxes = []
    for shape in cell.shapes(cell.layout().layer(coarse_layer, 0)).each():
        polygon = shape.polygon if shape.is_polygon() else pya.Polygon(shape.box) if shape.is_box() else None
        if polygon is None:
            continue
        bbox = polygon.bbox()
        if abs(bbox.width() - 10_000) <= 1 and abs(bbox.height() - 10_000) <= 1:
            bridge_boxes.append(bbox)
    assert len(bridge_boxes) == 12
    for row_y in {box.center().y for box in bridge_boxes}:
        row = sorted(box.center().x for box in bridge_boxes if box.center().y == row_y)
        assert all(right - left >= 19_999 for left, right in zip(row, row[1:]))
