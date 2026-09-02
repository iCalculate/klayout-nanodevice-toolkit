"""Render an exact debugging diagram from the CrossBar layout generator."""

from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Polygon as MplPolygon, Rectangle

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import klayout.db as db

from components.crossbar import CrossBar


LAYER_STYLE = {
    "bottom_gate": dict(facecolor="#27B8E6", edgecolor="#087FA7", alpha=0.95, zorder=2),
    "bottom_dielectric": dict(facecolor="#FF5A67", edgecolor="#C92E3A", alpha=0.26, zorder=3),
    "top_dielectric": dict(facecolor="#C64ED9", edgecolor="#8D269D", alpha=0.24, zorder=4),
    "top_gate": dict(facecolor="#86D63E", edgecolor="#4B9620", alpha=0.92, zorder=5),
    "pad": dict(facecolor="#FFB300", edgecolor="#C17E00", alpha=0.28, zorder=6),
    "alignment_marks": dict(facecolor="#26364A", edgecolor="#101820", alpha=0.98, zorder=7),
}


def shape_points(shape, dbu):
    if shape.is_box():
        box = shape.box
        return [
            (box.left * dbu, box.bottom * dbu),
            (box.right * dbu, box.bottom * dbu),
            (box.right * dbu, box.top * dbu),
            (box.left * dbu, box.top * dbu),
        ]
    polygon = shape.polygon
    return [(point.x * dbu, point.y * dbu) for point in polygon.each_point_hull()]


def draw_layout(ax, device, cell, title):
    for key in ("bottom_gate", "bottom_dielectric", "top_dielectric", "top_gate", "pad", "alignment_marks"):
        layer_index = device.layout.layer(device.get_layer_ids()[key], 0)
        for shape in cell.shapes(layer_index).each():
            ax.add_patch(MplPolygon(shape_points(shape, device.layout.dbu), **LAYER_STYLE[key]))
    bbox = cell.bbox()
    margin = 12.0
    ax.set_xlim(bbox.left * device.layout.dbu - margin, bbox.right * device.layout.dbu + margin)
    ax.set_ylim(bbox.bottom * device.layout.dbu - margin, bbox.top * device.layout.dbu + margin)
    ax.set_aspect("equal")
    ax.grid(True, linewidth=0.45, color="#D8DEE8", alpha=0.7)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("X (um)")
    ax.set_ylabel("Y (um)")


def make_device(**kwargs):
    layout = db.Layout()
    layout.dbu = 0.001
    device = CrossBar(layout=layout, **kwargs)
    return device, device.create_array_cell()


def main():
    fig = plt.figure(figsize=(16, 10), facecolor="#F7F9FC")
    grid = fig.add_gridspec(2, 2, height_ratios=[1.25, 1.0], hspace=0.30, wspace=0.20)

    equal_device, equal_cell = make_device(x_num=3, y_num=2, array_mode="equal")
    ax_equal = fig.add_subplot(grid[:, 0])
    draw_layout(ax_equal, equal_device, equal_cell, "Equal-size array: x_num=3, y_num=2")
    ax_equal.text(
        0.02, 0.02,
        "N=3 columns + M=2 rows -> N*M=6 devices, N+M=5 pads.\n"
        "Each pad addresses one complete shared row or column.",
        transform=ax_equal.transAxes, fontsize=10, va="bottom",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="white", edgecolor="#BAC5D5", alpha=0.95),
        zorder=20,
    )

    gradient_device, gradient_cell = make_device(
        x_num=3,
        y_num=3,
        array_mode="gradient",
        horizontal_bar_width=1.0,
        horizontal_bar_width_end=5.0,
        vertical_bar_width=1.0,
        vertical_bar_width_end=5.0,
    )
    ax_gradient = fig.add_subplot(grid[0, 1])
    draw_layout(ax_gradient, gradient_device, gradient_cell, "Gradient array: 2D bar-width sweep")
    ax_gradient.annotate(
        "Vertical width increases along X",
        xy=(0.82, 0.94), xytext=(0.18, 0.94), xycoords="axes fraction",
        arrowprops=dict(arrowstyle="->", color="#4B9620", lw=2),
        color="#327215", fontsize=10, ha="center", va="center",
    )
    ax_gradient.annotate(
        "Horizontal width\nincreases along Y",
        xy=(0.05, 0.78), xytext=(0.05, 0.24), xycoords="axes fraction",
        arrowprops=dict(arrowstyle="->", color="#087FA7", lw=2),
        color="#086F91", fontsize=10, ha="center", va="center", rotation=90,
    )

    unit_device, unit_cell = make_device(
        x_num=1,
        y_num=1,
        horizontal_bar_width=4.0,
        vertical_bar_width=3.0,
        bottom_dielectric_extension_x=3.0,
        bottom_dielectric_extension_y=3.0,
        top_dielectric_extension_x=5.0,
        top_dielectric_extension_y=5.0,
    )
    ax_unit = fig.add_subplot(grid[1, 1])
    draw_layout(ax_unit, unit_device, unit_cell, "Single device detail")
    ax_unit.set_xlim(-68, 25)
    ax_unit.set_ylim(-18, 68)
    ax_unit.add_patch(Rectangle((-7, -7), 14, 14, fill=False, linestyle="--", linewidth=1.8, edgecolor="#202A38", zorder=10))
    ax_unit.annotate("Crossing + dielectric enclosure", xy=(7, 7), xytext=(19, 20),
                     arrowprops=dict(arrowstyle="->", color="#202A38"), fontsize=10)
    ax_unit.annotate("One pad per shared back-gate row", xy=(-28, 0), xytext=(-62, -14),
                     arrowprops=dict(arrowstyle="->", color="#087FA7"), color="#087FA7", fontsize=10)
    ax_unit.annotate("One pad per shared top-gate column", xy=(0, 28), xytext=(10, 57),
                     arrowprops=dict(arrowstyle="->", color="#4B9620"), color="#327215", fontsize=10)

    legend = [
        Patch(label="11/0 Back Gate: M shared rows + selected-side pads", **{k: v for k, v in LAYER_STYLE["bottom_gate"].items() if k in ("facecolor", "edgecolor", "alpha")}),
        Patch(label="12/0 Back Dielectric: crossing enclosure", **{k: v for k, v in LAYER_STYLE["bottom_dielectric"].items() if k in ("facecolor", "edgecolor", "alpha")}),
        Patch(label="17/0 Top Dielectric: crossing enclosure", **{k: v for k, v in LAYER_STYLE["top_dielectric"].items() if k in ("facecolor", "edgecolor", "alpha")}),
        Patch(label="18/0 Top Gate: N shared columns + selected-side pads", **{k: v for k, v in LAYER_STYLE["top_gate"].items() if k in ("facecolor", "edgecolor", "alpha")}),
        Patch(label="41/0 Breakout pad overlay", **{k: v for k, v in LAYER_STYLE["pad"].items() if k in ("facecolor", "edgecolor", "alpha")}),
        Patch(label="3/0 Mark in every selected grid gap", **{k: v for k, v in LAYER_STYLE["alignment_marks"].items() if k in ("facecolor", "edgecolor", "alpha")}),
    ]
    fig.legend(handles=legend, loc="lower center", ncol=3, frameon=True, fontsize=9,
               bbox_to_anchor=(0.5, 0.01), edgecolor="#BAC5D5")
    fig.suptitle("Cross Bar Array — exact geometry generated by components/crossbar.py",
                 fontsize=19, fontweight="bold", y=0.985, color="#162033")
    fig.subplots_adjust(bottom=0.105, top=0.93, left=0.06, right=0.98)

    output = Path(__file__).resolve().parent / "assets" / "crossbar_structure_diagram.png"
    fig.savefig(output, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(output)


if __name__ == "__main__":
    main()
