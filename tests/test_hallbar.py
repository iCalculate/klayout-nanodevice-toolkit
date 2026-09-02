import klayout.db as db
import pytest

from components.hallbar import HallBar
from utils.fanout_utils import draw_pad, draw_trapezoidal_fanout


def _shapes(layout, cell, layer_id):
    return list(cell.shapes(layout.layer(layer_id, 0)).each())


def _region(shapes):
    region = db.Region()
    for shape in shapes:
        if shape.is_box():
            region.insert(shape.box)
        elif shape.is_polygon():
            region.insert(shape.polygon)
    return region


def test_nonparallel_fanout_edge_pairing_is_mirror_symmetric():
    left = draw_trapezoidal_fanout(
        draw_pad((-23.25, 32.0), 10.0, 12.0),
        draw_pad((-123.0, 90.0), 80.0, 80.0, 10.0, "straight"),
        inner_edge="L",
        outer_edge="D",
    )
    right = draw_trapezoidal_fanout(
        draw_pad((23.25, 32.0), 10.0, 12.0),
        draw_pad((123.0, 90.0), 80.0, 80.0, 10.0, "straight"),
        inner_edge="R",
        outer_edge="D",
    )

    assert db.Region(left).area() == db.Region(right).area()


def test_default_fanout_covers_complete_usable_large_pad_edge():
    fanout = draw_trapezoidal_fanout(
        draw_pad((0.0, 0.0), 10.0, 10.0),
        draw_pad((0.0, 100.0), 80.0, 80.0, 10.0, "straight"),
        inner_edge="U",
        outer_edge="D",
    )
    landing_xs = [point.x for point in fanout.each_point_hull() if point.y == 60000]

    # The 80 um chamfered pad has a 60 um straight bottom edge.
    assert max(landing_xs) - min(landing_xs) == 60000


def test_default_hallbar_remains_two_pair_single_layer_geometry():
    layout = db.Layout()
    layout.dbu = 0.001
    device = HallBar(layout=layout)
    cell = device.create_single_device(show_param_label=False)

    assert device.get_v_contact_x_positions() == pytest.approx([-12.5, 12.5])
    assert device.get_v_outer_x_positions() == pytest.approx([-60.0, 60.0])
    assert device._resolved_v_outer_offset_y() == pytest.approx(120.0)
    assert len(_shapes(layout, cell, 13)) == 3  # main bar + two protrusions
    assert len(_shapes(layout, cell, 15)) == 18  # six contacts: inner + fanout + outer
    assert len(_shapes(layout, cell, 25)) == 0


def test_legacy_gui_defaults_keep_original_compact_pad_offsets():
    device = HallBar(
        v_contact_pairs=2,
        split_ebl_exposure=False,
        v_outer_length=80.0,
        v_outer_width=80.0,
        v_outer_offset_x=45.0,
        v_outer_offset_y=90.0,
        i_outer_length=80.0,
        i_outer_width=80.0,
        i_outer_offset_x=110.0,
    )

    assert device.get_v_outer_x_positions() == pytest.approx([-45.0, 45.0])
    assert device._resolved_v_outer_offset_y() == pytest.approx(90.0)


def test_configurable_v_pair_count_and_probe_pad_auto_spacing():
    layout = db.Layout()
    layout.dbu = 0.001
    device = HallBar(
        layout=layout,
        v_contact_pairs=4,
        bar_length=100.0,
        dist_v=15.0,
        v_outer_length=80.0,
        v_outer_offset_x=30.0,
        min_electrode_gap=3.0,
    )
    cell = device.create_single_device(show_param_label=False)

    assert device.get_v_contact_x_positions() == pytest.approx([-22.5, -7.5, 7.5, 22.5])
    outer_xs = device.get_v_outer_x_positions()
    assert all(b - a >= 83.0 for a, b in zip(outer_xs, outer_xs[1:]))
    assert device._resolved_i_outer_offset_x() >= abs(outer_xs[-1]) + 83.0
    assert len(_shapes(layout, cell, 13)) == 5
    assert len(_shapes(layout, cell, 15)) == 30  # two I contacts + eight V contacts


def test_split_ebl_uses_matching_coarse_and_fine_layers_with_overlap():
    layout = db.Layout()
    layout.dbu = 0.001
    device = HallBar(
        layout=layout,
        source_drain_layer_id=16,
        v_contact_pairs=3,
        bar_length=75.0,
        dist_v=15.0,
        split_ebl_exposure=True,
        ebl_overlap=2.0,
    )
    cell = device.create_single_device(show_param_label=False)

    assert device.get_layer_ids()["fine_source_drain"] == 26
    coarse = _shapes(layout, cell, 16)
    fine = _shapes(layout, cell, 26)
    assert len(coarse) == 24
    assert len(fine) == 24
    assert (_region(coarse) & _region(fine)).area() > 0


@pytest.mark.parametrize("split", [False, True])
def test_four_pair_routes_have_no_cross_electrode_interference(split):
    layout = db.Layout()
    layout.dbu = 0.001
    device = HallBar(
        layout=layout,
        v_contact_pairs=4,
        bar_length=100.0,
        dist_v=15.5,
        v_outer_length=80.0,
        v_outer_width=80.0,
        v_outer_offset_x=45.0,
        i_outer_length=80.0,
        i_outer_width=80.0,
        i_outer_offset_x=110.0,
        split_ebl_exposure=split,
    )
    cell = device.create_single_device(show_param_label=False)

    layer_ids = [15, 25] if split else [15]
    for layer_id in layer_ids:
        metal = _region(_shapes(layout, cell, layer_id))
        # Ten electrodes must remain ten connected components even after each
        # is expanded by almost half the requested 2 um clearance.
        assert metal.merged().count() == 10
        assert metal.sized(999).merged().count() == 10

    voltage_edges = [item for item in device._last_fanout_edges if item["name"].startswith("V")]
    assert all(item["minimum_angle"] >= device.min_fanout_corner_angle for item in voltage_edges)
    if split:
        assert device._resolved_v_outer_offset_y() > 90.0


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"v_contact_pairs": 0}, "v_contact_pairs"),
        ({"v_contact_pairs": 3, "bar_length": 40.0, "dist_v": 15.0}, "do not fit"),
        ({"v_contact_pairs": 3, "bar_length": 80.0, "dist_v": 6.0}, "channel contacts"),
        (
            {
                "v_contact_pairs": 3,
                "bar_length": 80.0,
                "dist_v": 11.0,
                "split_ebl_exposure": True,
                "bridge_pad_width": 10.0,
                "min_electrode_gap": 2.0,
            },
            "bridge pads",
        ),
        ({"split_ebl_exposure": True, "source_drain_layer_id": 31}, "11-19"),
        (
            {"split_ebl_exposure": True, "source_drain_layer_id": 15, "fine_source_drain_layer_id": 26},
            r"coarse layer \+ 10",
        ),
    ],
)
def test_rejects_interfering_or_invalid_hallbar_geometry(kwargs, message):
    with pytest.raises(ValueError, match=message):
        HallBar(**kwargs)
