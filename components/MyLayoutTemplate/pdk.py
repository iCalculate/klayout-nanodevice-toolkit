# -*- coding: utf-8 -*-
"""
Generic nanodevice PDK (Process Design Kit) layer definitions and registration.

Layer numbering:
- 1–9:   Utility (mechanical, active, marks, calipers, etc.)
- 10–19: Front-end (gate / dielectric / channel)
- 20–29: Back-end (contact, metal, spacer)
- 61–63: Alignment (LineScan / ImgScan / Manual)

Compatible with Python 3.11+ and current gdsfactory (Pdk requires layers to be a LayerMap subclass).
Usage:
    from components.MyLayoutTemplate.pdk import LAYER, PDK
    PDK.activate()
    layer_tuple = gf.get_layer("MARK")  # or tuple(LAYER.MARK)
    layer_tuple = tuple(LAYER.MARK)     # (3, 0) for indexing layer[0], layer[1]
"""

from __future__ import annotations

import gdsfactory as gf
from gdsfactory.technology import LayerMap
from gdsfactory.typings import Layer


class GenericNanoDeviceLayerMap(LayerMap):
    """
    Generic nanodevice PDK layer map (LayerMap subclass for gdsfactory Pdk).
    - 1–9:  Utility layers
    - 10–19: Front-end (bottom/mid/top gate & dielectric, N/P channel)
    - 20–29: Back-end (N/P contact, Routing Metal 1–4, Spacer 1–4)
    - 61–63: Alignment
    """

    # ----- 1–9 Utility -----
    MECHANICAL: Layer = (1, 0)   # Sample outline
    ACTIVE: Layer = (2, 0)       # Active area
    MARK: Layer = (3, 0)        # All marks
    MARK_FRAME: Layer = (4, 0)   # Crosshair frames
    CALIPER: Layer = (5, 0)      # Calipers
    L6: Layer = (6, 0)
    L7: Layer = (7, 0)
    L8: Layer = (8, 0)
    L9: Layer = (9, 0)

    # ----- 10–19 Front-end -----
    FE_BOTTOM_GATE: Layer = (10, 0)
    FE_BOTTOM_DIELEC: Layer = (11, 0)
    FE_N1_CHANNEL: Layer = (12, 0)
    FE_N2_CHANNEL: Layer = (13, 0)
    FE_P1_CHANNEL: Layer = (14, 0)
    FE_P2_CHANNEL: Layer = (15, 0)
    FE_MID_DIELEC: Layer = (16, 0)
    FE_MID_GATE: Layer = (17, 0)
    FE_TOP_DIELEC: Layer = (18, 0)
    FE_TOP_GATE: Layer = (19, 0)

    # ----- 20–29 Back-end -----
    BE_N_CONTACT: Layer = (20, 0)
    BE_P_CONTACT: Layer = (21, 0)
    BE_M1: Layer = (22, 0)
    BE_SPACER1: Layer = (23, 0)
    BE_M2: Layer = (24, 0)
    BE_SPACER2: Layer = (25, 0)
    BE_M3: Layer = (26, 0)
    BE_SPACER3: Layer = (27, 0)
    BE_M4: Layer = (28, 0)
    BE_SPACER4: Layer = (29, 0)

    # ----- Alignment 61–63 -----
    ALIGN_LINESCAN: Layer = (61, 0)   # Auto LineScan Align
    ALIGN_IMGSCAN: Layer = (62, 0)    # Auto ImgScan Align
    ALIGN_MANUAL: Layer = (63, 0)     # Manual Align


LAYER = GenericNanoDeviceLayerMap

# Layer name -> (gdslayer, gdspurpose) for resolving GDS layer from LayerMap enum (enum .value may be int)
LAYER_TUPLES = {
    "MECHANICAL": (1, 0), "ACTIVE": (2, 0), "MARK": (3, 0), "MARK_FRAME": (4, 0), "CALIPER": (5, 0),
    "L6": (6, 0), "L7": (7, 0), "L8": (8, 0), "L9": (9, 0),
    "FE_BOTTOM_GATE": (10, 0), "FE_BOTTOM_DIELEC": (11, 0), "FE_N1_CHANNEL": (12, 0), "FE_N2_CHANNEL": (13, 0),
    "FE_P1_CHANNEL": (14, 0), "FE_P2_CHANNEL": (15, 0), "FE_MID_DIELEC": (16, 0), "FE_MID_GATE": (17, 0),
    "FE_TOP_DIELEC": (18, 0), "FE_TOP_GATE": (19, 0),
    "BE_N_CONTACT": (20, 0), "BE_P_CONTACT": (21, 0), "BE_M1": (22, 0), "BE_SPACER1": (23, 0),
    "BE_M2": (24, 0), "BE_SPACER2": (25, 0), "BE_M3": (26, 0), "BE_SPACER3": (27, 0),
    "BE_M4": (28, 0), "BE_SPACER4": (29, 0),
    "ALIGN_LINESCAN": (61, 0), "ALIGN_IMGSCAN": (62, 0), "ALIGN_MANUAL": (63, 0),
}


# Register PDK (gdsfactory requires layers to be a LayerMap subclass)
PDK = gf.Pdk(
    name="nanodevice",
    layers=GenericNanoDeviceLayerMap,
)


def activate() -> None:
    """Activate nanodevice PDK so gf.get_layer(name) etc. use this PDK's layers."""
    PDK.activate()


# Auto-activate on import so mark_writefield_gdsfactory etc. can use LAYER defaults
activate()
