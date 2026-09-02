"""Generate the default 16x16 gradient crossbar GDS and inspection preview."""

from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Polygon as MplPolygon

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import klayout.db as db

from components.crossbar import CrossBar


STYLES = {
    "bottom_gate": dict(facecolor="#25B5E2", edgecolor="#087FA7", alpha=0.92, zorder=2),
    "bottom_dielectric": dict(facecolor="#FF6673", edgecolor="#CB3440", alpha=0.25, zorder=3),
    "top_dielectric": dict(facecolor="#C955DA", edgecolor="#8D269D", alpha=0.23, zorder=4),
    "top_gate": dict(facecolor="#82D43B", edgecolor="#4B9620", alpha=0.90, zorder=5),
    "pad": dict(facecolor="#FFB300", edgecolor="#B97800", alpha=0.25, zorder=6),
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
    return [(point.x * dbu, point.y * dbu) for point in shape.polygon.each_point_hull()]


def draw_cell(ax, device, cell, limits=None):
    for key in STYLES:
        layer = device.layout.layer(device.get_layer_ids()[key], 0)
        for shape in cell.shapes(layer).each():
            ax.add_patch(MplPolygon(shape_points(shape, device.layout.dbu), **STYLES[key]))
    if limits:
        ax.set_xlim(limits[0], limits[1])
        ax.set_ylim(limits[2], limits[3])
    else:
        bbox = cell.bbox()
        margin = 12.0
        ax.set_xlim(bbox.left * device.layout.dbu - margin, bbox.right * device.layout.dbu + margin)
        ax.set_ylim(bbox.bottom * device.layout.dbu - margin, bbox.top * device.layout.dbu + margin)
    ax.set_aspect("equal")
    ax.grid(True, color="#D8DEE8", linewidth=0.4, alpha=0.65)
    ax.set_xlabel("X (um)")
    ax.set_ylabel("Y (um)")


def main():
    output_dir = PROJECT_ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    layout = db.Layout()
    layout.dbu = 0.001
    device = CrossBar(layout=layout)
    cell = device.create_array_cell("CrossBar_16x16_Gradient")

    gds_path = output_dir / "crossbar_16x16_gradient.gds"
    layout.write(str(gds_path))

    fig = plt.figure(figsize=(16, 10), facecolor="#F7F9FC")
    grid = fig.add_gridspec(2, 2, width_ratios=[1.45, 1.0], hspace=0.25, wspace=0.20)
    full = fig.add_subplot(grid[:, 0])
    thin = fig.add_subplot(grid[0, 1])
    thick = fig.add_subplot(grid[1, 1])

    draw_cell(full, device, cell)
    full.set_title("Full 16 x 16 shared-line crossbar", fontsize=15, fontweight="bold")

    half_span = (device.x_num - 1) * device.x_pitch / 2.0
    draw_cell(thin, device, cell, (-half_span - 38, -half_span + 72, -half_span - 38, -half_span + 72))
    thin.set_title("Lower-left: 1.0 um bars", fontsize=13, fontweight="bold")
    draw_cell(thick, device, cell, (half_span - 72, half_span + 38, half_span - 72, half_span + 38))
    thick.set_title("Upper-right: 5.0 um bars", fontsize=13, fontweight="bold")

    step_h = (device.horizontal_bar_width_end - device.horizontal_bar_width) / (device.y_num - 1)
    step_v = (device.vertical_bar_width_end - device.vertical_bar_width) / (device.x_num - 1)
    summary = (
        f"Devices: {device.x_num} x {device.y_num} = {device.x_num * device.y_num}\n"
        f"Pads: N + M = {device.x_num + device.y_num}\n"
        f"Gap marks: (N-1) x (M-1) = {(device.x_num - 1) * (device.y_num - 1)}\n"
        f"Pitch: {device.x_pitch:g} x {device.y_pitch:g} um\n"
        f"Horizontal width: {device.horizontal_bar_width:g} -> {device.horizontal_bar_width_end:g} um "
        f"(step {step_h:.4f} um/row)\n"
        f"Vertical width: {device.vertical_bar_width:g} -> {device.vertical_bar_width_end:g} um "
        f"(step {step_v:.4f} um/column)"
    )
    full.text(
        0.02, 0.02, summary, transform=full.transAxes, fontsize=10, va="bottom",
        bbox=dict(boxstyle="round,pad=0.55", facecolor="white", edgecolor="#BAC5D5", alpha=0.96),
        zorder=20,
    )

    legend = [
        Patch(label="11/0 Back Gate", **{k: v for k, v in STYLES["bottom_gate"].items() if k in ("facecolor", "edgecolor", "alpha")}),
        Patch(label="12/0 Back Dielectric", **{k: v for k, v in STYLES["bottom_dielectric"].items() if k in ("facecolor", "edgecolor", "alpha")}),
        Patch(label="17/0 Top Dielectric", **{k: v for k, v in STYLES["top_dielectric"].items() if k in ("facecolor", "edgecolor", "alpha")}),
        Patch(label="18/0 Top Gate", **{k: v for k, v in STYLES["top_gate"].items() if k in ("facecolor", "edgecolor", "alpha")}),
        Patch(label="41/0 Pads", **{k: v for k, v in STYLES["pad"].items() if k in ("facecolor", "edgecolor", "alpha")}),
        Patch(label="3/0 Gap Marks", **{k: v for k, v in STYLES["alignment_marks"].items() if k in ("facecolor", "edgecolor", "alpha")}),
    ]
    fig.legend(handles=legend, loc="lower center", ncol=6, fontsize=9, frameon=True,
               bbox_to_anchor=(0.5, 0.012), edgecolor="#BAC5D5")
    fig.suptitle("CrossBar 16 x 16 Gradient Inspection", fontsize=20, fontweight="bold", y=0.985)
    fig.subplots_adjust(top=0.93, bottom=0.10, left=0.055, right=0.98)

    preview_path = output_dir / "crossbar_16x16_gradient_preview.png"
    fig.savefig(preview_path, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(gds_path)
    print(preview_path)


if __name__ == "__main__":
    main()
