import klayout.db as db
import pytest

from components.woodpile import Woodpile


def _boxes_on(layout, cell, layer_id):
    layer = layout.layer(layer_id, 0)
    return [shape.bbox() for shape in cell.shapes(layer).each()]


def _shapes_on(layout, cell, layer_id):
    layer = layout.layer(layer_id, 0)
    return list(cell.shapes(layer).each())


def test_default_layers_and_outer_pads():
    layout = db.Layout()
    layout.dbu = 0.001
    device = Woodpile(layout=layout)
    cell = device.create_single_device()

    assert device.get_layer_ids() == {"bottom_gate": 11, "material": 13, "top_gate": 18}

    bottom_boxes = _boxes_on(layout, cell, 11)
    top_boxes = _boxes_on(layout, cell, 18)
    assert any(box.width() == 80_000 and box.height() == 80_000 for box in bottom_boxes)
    assert any(box.width() == 80_000 and box.height() == 80_000 for box in top_boxes)
    bottom_outer = min(_shapes_on(layout, cell, 11), key=lambda shape: shape.bbox().center().x)
    top_outer = max(_shapes_on(layout, cell, 18), key=lambda shape: shape.bbox().center().y)
    assert bottom_outer.area() == bottom_outer.bbox().area()
    assert top_outer.area() == top_outer.bbox().area()


def test_rectangular_outer_pad_length_follows_each_bar_direction():
    layout = db.Layout()
    layout.dbu = 0.001
    device = Woodpile(
        layout=layout,
        outer_pad_length=120.0,
        outer_pad_width=60.0,
    )
    cell = device.create_single_device()

    bottom_outer = min(_boxes_on(layout, cell, 11), key=lambda box: box.center().x)
    top_outer = max(_boxes_on(layout, cell, 18), key=lambda box: box.center().y)
    assert (bottom_outer.width(), bottom_outer.height()) == (120_000, 60_000)
    assert (top_outer.width(), top_outer.height()) == (60_000, 120_000)


def test_outer_pad_chamfers_are_synchronized():
    layout = db.Layout()
    layout.dbu = 0.001
    device = Woodpile(
        layout=layout,
        outer_pad_chamfer_type="straight",
        outer_pad_chamfer_size=8.0,
    )
    cell = device.create_single_device()

    bottom_outer = min(_shapes_on(layout, cell, 11), key=lambda shape: shape.bbox().center().x)
    top_outer = max(_shapes_on(layout, cell, 18), key=lambda shape: shape.bbox().center().y)
    assert bottom_outer.area() < bottom_outer.bbox().area()
    assert top_outer.area() < top_outer.bbox().area()


def test_independent_config_migration_uses_top_pad_values_for_both():
    layout = db.Layout()
    layout.dbu = 0.001
    device = Woodpile(
        layout=layout,
        bottom_outer_pad_length=120.0,
        bottom_outer_pad_width=60.0,
        top_outer_pad_length=100.0,
        top_outer_pad_width=40.0,
    )
    cell = device.create_single_device()

    bottom_outer = min(_boxes_on(layout, cell, 11), key=lambda box: box.center().x)
    top_outer = max(_boxes_on(layout, cell, 18), key=lambda box: box.center().y)
    assert (bottom_outer.width(), bottom_outer.height()) == (100_000, 40_000)
    assert (top_outer.width(), top_outer.height()) == (40_000, 100_000)


def test_p_material_uses_layer_14():
    layout = db.Layout()
    layout.dbu = 0.001
    device = Woodpile(layout=layout, channel_type="p")
    cell = device.create_single_device()

    assert device.get_layer_ids()["material"] == 14
    assert len(_boxes_on(layout, cell, 14)) == 1
    assert len(_boxes_on(layout, cell, 13)) == 0


def test_equal_width_mode_overrides_top_width():
    layout = db.Layout()
    layout.dbu = 0.001
    device = Woodpile(
        layout=layout,
        equal_bar_widths=True,
        bottom_bar_width=3.0,
        top_bar_width=7.0,
    )
    cell = device.create_single_device()

    central_top = next(
        box for box in _boxes_on(layout, cell, 18)
        if box.contains(db.Point(0, 0)) and box.height() == 20_000
    )
    assert central_top.width() == 3_000


def test_unequal_bar_widths_are_independent_and_orthogonal():
    layout = db.Layout()
    layout.dbu = 0.001
    device = Woodpile(
        layout=layout,
        equal_bar_widths=False,
        bottom_bar_width=3.0,
        top_bar_width=5.0,
        bottom_bar_length=24.0,
        top_bar_length=30.0,
    )
    cell = device.create_single_device()

    bottom_bar = next(
        box for box in _boxes_on(layout, cell, 11)
        if box.contains(db.Point(0, 0)) and box.width() == 24_000
    )
    top_bar = next(
        box for box in _boxes_on(layout, cell, 18)
        if box.contains(db.Point(0, 0)) and box.height() == 30_000
    )
    assert (bottom_bar.width(), bottom_bar.height()) == (24_000, 3_000)
    assert (top_bar.width(), top_bar.height()) == (5_000, 30_000)


@pytest.mark.parametrize("bad_type", ["", "x", "N-type"])
def test_rejects_unknown_material_type(bad_type):
    with pytest.raises(ValueError, match="channel_type"):
        Woodpile(channel_type=bad_type)
