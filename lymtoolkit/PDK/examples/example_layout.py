# -*- coding: utf-8 -*-
"""
LabPDK example: draw alignment marks, bottom gate, metal routing, and bonding pad.
Run from KLayout (Macros → Run) or from command line with klayout -b -r this_script.py

Units: 1 dbu = 1 nm. This script uses um, converted to dbu via scale.
"""
import sys
import os

# Allow importing layers from PDK (when script is run from repo or from tech/LabPDK)
_script_dir = os.path.dirname(os.path.abspath(__file__))
_pdk_layers = os.path.join(os.path.dirname(_script_dir), "layers")
if os.path.isdir(_pdk_layers) and _pdk_layers not in sys.path:
    sys.path.insert(0, os.path.dirname(_pdk_layers))

import pya
from layers.layers import Layers

DBU = 0.001  # 1 nm
SCALE = 1.0 / DBU  # um -> dbu

def um_to_dbu(um):
    return int(round(um * SCALE))

def main():
    layout = pya.Layout()
    layout.dbu = DBU
    layout.technology_name = "LabPDK"
    L = Layers(layout)
    cell = layout.create_cell("ExampleTop")

    # --- 1) Chip mechanical boundary (alignment) ---
    chip_size_um = 500.0
    chip_box = pya.Box(0, 0, um_to_dbu(chip_size_um), um_to_dbu(chip_size_um))
    cell.shapes(L.CHIP_MECHANICAL_BOUNDARY).insert(chip_box)

    # --- 2) Primary alignment mark (cross at corner) ---
    mark_center_um = (50.0, 50.0)
    mark_size_um = 20.0
    mark_w_um = 2.0
    cx, cy = um_to_dbu(mark_center_um[0]), um_to_dbu(mark_center_um[1])
    half = um_to_dbu(mark_size_um / 2)
    w = um_to_dbu(mark_w_um / 2)
    # Horizontal bar
    cell.shapes(L.PRIMARY_ALIGNMENT_MARK).insert(
        pya.Box(cx - half, cy - w, cx + half, cy + w)
    )
    # Vertical bar
    cell.shapes(L.PRIMARY_ALIGNMENT_MARK).insert(
        pya.Box(cx - w, cy - half, cx + w, cy + half)
    )

    # --- 3) Bottom gate (device) ---
    gate_x_um, gate_y_um = 150.0, 150.0
    gate_w_um, gate_h_um = 5.0, 2.0
    cell.shapes(L.BOTTOM_GATE).insert(
        pya.Box(
            um_to_dbu(gate_x_um), um_to_dbu(gate_y_um),
            um_to_dbu(gate_x_um + gate_w_um), um_to_dbu(gate_y_um + gate_h_um),
        )
    )

    # --- 4) Metal routing (Metal1 and Via1) ---
    # Metal1 wire from gate toward pad
    m1_x_um, m1_y_um = 155.0, 148.0
    m1_w_um, m1_h_um = 100.0, 6.0
    cell.shapes(L.METAL1).insert(
        pya.Box(
            um_to_dbu(m1_x_um), um_to_dbu(m1_y_um),
            um_to_dbu(m1_x_um + m1_w_um), um_to_dbu(m1_y_um + m1_h_um),
        )
    )
    # Via1 at end of wire (small square)
    via_um = 4.0
    vx = m1_x_um + m1_w_um - via_um
    vy = m1_y_um + (m1_h_um - via_um) / 2.0
    cell.shapes(L.VIA1).insert(
        pya.Box(um_to_dbu(vx), um_to_dbu(vy), um_to_dbu(vx + via_um), um_to_dbu(vy + via_um))
    )

    # --- 5) Bonding pad ---
    pad_x_um, pad_y_um = 400.0, 350.0
    pad_size_um = 80.0
    cell.shapes(L.PAD).insert(
        pya.Box(
            um_to_dbu(pad_x_um), um_to_dbu(pad_y_um),
            um_to_dbu(pad_x_um + pad_size_um), um_to_dbu(pad_y_um + pad_size_um),
        )
    )

    # Optional: write GDS
    # layout.write("example_layout.gds")

    # In KLayout: load into current view (uncomment to use)
    # try:
    #     v = pya.Application.instance().main_window().current_view()
    #     if v and v.active_cellview():
    #         v.active_cellview().layout().assign(layout)
    #         v.active_cellview().cell_name = "ExampleTop"
    # except Exception:
    #     pass
    print("Example layout: chip boundary, alignment mark, bottom gate, metal/via, pad.")
    return layout

if __name__ == "__main__":
    main()
