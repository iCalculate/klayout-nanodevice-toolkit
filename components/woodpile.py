# -*- coding: utf-8 -*-
"""Single-cross woodpile device with independent bottom/top-gate bars."""

import klayout.db as db

try:
    import pya
except ImportError:
    pya = db

from config import DEFAULT_DBU, LAYER_DEFINITIONS
from utils.fanout_utils import draw_pad, draw_trapezoidal_fanout


class Woodpile:
    """Build two orthogonal gate bars separated by an n- or p-type material.

    The horizontal bar and its pads are written on the bottom-gate layer. The
    vertical bar and its pads are written on the top-gate layer.  Each bar has
    one inner landing and one outer probing pad.
    """

    def __init__(self, layout=None, **kwargs):
        self.layout = layout or pya.Layout()
        if self.layout.dbu <= 0:
            self.layout.dbu = DEFAULT_DBU

        self.channel_type = str(kwargs.get("channel_type", "n")).lower()
        self.equal_bar_widths = bool(kwargs.get("equal_bar_widths", True))
        self.bottom_bar_length = float(kwargs.get("bottom_bar_length", 20.0))
        self.top_bar_length = float(kwargs.get("top_bar_length", 20.0))
        self.bottom_bar_width = float(kwargs.get("bottom_bar_width", 2.0))
        requested_top_width = float(kwargs.get("top_bar_width", 2.0))
        self.top_bar_width = self.bottom_bar_width if self.equal_bar_widths else requested_top_width
        self.material_margin = float(kwargs.get("material_margin", 1.0))

        self.inner_pad_length = float(kwargs.get("inner_pad_length", 10.0))
        self.inner_pad_width = float(kwargs.get("inner_pad_width", 10.0))
        self.inner_pad_overlap = float(kwargs.get("inner_pad_overlap", 1.0))
        self.fanout_length = float(kwargs.get("fanout_length", 40.0))
        # One synchronized outer-pad definition is applied to both electrodes.
        # Length is measured along each bar and width across it. When importing
        # the short-lived independent-pad format, the top-pad values win.
        self.outer_pad_length = float(
            kwargs.get("outer_pad_length", kwargs.get("top_outer_pad_length", kwargs.get("bottom_outer_pad_length", kwargs.get("outer_pad_height", 80.0))))
        )
        self.outer_pad_width = float(
            kwargs.get("outer_pad_width", kwargs.get("top_outer_pad_width", kwargs.get("bottom_outer_pad_width", 80.0)))
        )
        self.outer_pad_chamfer_type = str(
            kwargs.get("outer_pad_chamfer_type", kwargs.get("top_outer_pad_chamfer_type", kwargs.get("bottom_outer_pad_chamfer_type", "none")))
        ).lower()
        self.outer_pad_chamfer_size = float(
            kwargs.get("outer_pad_chamfer_size", kwargs.get("top_outer_pad_chamfer_size", kwargs.get("bottom_outer_pad_chamfer_size", kwargs.get("outer_pad_chamfer", 6.0))))
        )

        self._validate()
        self._layer_ids = {
            "bottom_gate": LAYER_DEFINITIONS["bottom_gate"]["id"],
            "material": 13 if self.channel_type == "n" else 14,
            "top_gate": LAYER_DEFINITIONS["top_gate"]["id"],
        }

    def _validate(self):
        if self.channel_type not in ("n", "p"):
            raise ValueError("channel_type must be 'n' or 'p'")
        positive = {
            "bottom_bar_length": self.bottom_bar_length,
            "top_bar_length": self.top_bar_length,
            "bottom_bar_width": self.bottom_bar_width,
            "top_bar_width": self.top_bar_width,
            "inner_pad_length": self.inner_pad_length,
            "inner_pad_width": self.inner_pad_width,
            "outer_pad_length": self.outer_pad_length,
            "outer_pad_width": self.outer_pad_width,
        }
        for name, value in positive.items():
            if value <= 0:
                raise ValueError(f"{name} must be greater than zero")
        if self.material_margin < 0 or self.inner_pad_overlap < 0 or self.fanout_length < 0:
            raise ValueError("material_margin, inner_pad_overlap, and fanout_length must be non-negative")
        if self.inner_pad_overlap > min(self.inner_pad_length, self.bottom_bar_length, self.top_bar_length):
            raise ValueError("inner_pad_overlap is too large for the selected bar/pad dimensions")
        if self.outer_pad_chamfer_type not in ("none", "straight", "round"):
            raise ValueError("outer_pad_chamfer_type must be none, straight, or round")
        if self.outer_pad_chamfer_size < 0 or 2.0 * self.outer_pad_chamfer_size > min(self.outer_pad_length, self.outer_pad_width):
            raise ValueError("outer_pad_chamfer_size must fit inside the outer pads")

    def get_layer_ids(self):
        return dict(self._layer_ids)

    def _layer(self, key):
        return self.layout.layer(self._layer_ids[key], 0)

    def _box(self, cx, cy, width, height):
        scale = 1.0 / self.layout.dbu
        return pya.Box(
            int(round((cx - width / 2.0) * scale)),
            int(round((cy - height / 2.0) * scale)),
            int(round((cx + width / 2.0) * scale)),
            int(round((cy + height / 2.0) * scale)),
        )

    def create_single_device(self, cell_name="Woodpile_Device", x=0.0, y=0.0):
        x = float(x)
        y = float(y)
        cell = self.layout.create_cell(cell_name)
        bottom_layer = self._layer("bottom_gate")
        material_layer = self._layer("material")
        top_layer = self._layer("top_gate")

        # Central single-bar cross.
        cell.shapes(bottom_layer).insert(self._box(x, y, self.bottom_bar_length, self.bottom_bar_width))
        cell.shapes(top_layer).insert(self._box(x, y, self.top_bar_width, self.top_bar_length))
        cell.shapes(material_layer).insert(
            self._box(
                x,
                y,
                self.top_bar_width + 2.0 * self.material_margin,
                self.bottom_bar_width + 2.0 * self.material_margin,
            )
        )

        # Bottom-gate landing is on the left of the horizontal bar.
        bottom_inner_x = x - self.bottom_bar_length / 2.0 - self.inner_pad_length / 2.0 + self.inner_pad_overlap
        bottom_inner = draw_pad(
            (bottom_inner_x, y), self.inner_pad_length, self.inner_pad_width,
            chamfer_size=0.0, chamfer_type="none",
        )
        bottom_outer_x = bottom_inner_x - self.inner_pad_length / 2.0 - self.fanout_length - self.outer_pad_length / 2.0
        bottom_outer = draw_pad(
            (bottom_outer_x, y), self.outer_pad_length, self.outer_pad_width,
            chamfer_size=self.outer_pad_chamfer_size,
            chamfer_type=self.outer_pad_chamfer_type,
        )
        cell.shapes(bottom_layer).insert(bottom_inner.polygon)
        cell.shapes(bottom_layer).insert(bottom_outer.polygon)
        if self.fanout_length > 0:
            cell.shapes(bottom_layer).insert(
                draw_trapezoidal_fanout(bottom_inner, bottom_outer, inner_edge="L", outer_edge="R")
            )

        # Top-gate landing is above the vertical bar.
        top_inner_y = y + self.top_bar_length / 2.0 + self.inner_pad_length / 2.0 - self.inner_pad_overlap
        top_inner = draw_pad(
            (x, top_inner_y), self.inner_pad_width, self.inner_pad_length,
            chamfer_size=0.0, chamfer_type="none",
        )
        top_outer_y = top_inner_y + self.inner_pad_length / 2.0 + self.fanout_length + self.outer_pad_length / 2.0
        top_outer = draw_pad(
            (x, top_outer_y), self.outer_pad_width, self.outer_pad_length,
            chamfer_size=self.outer_pad_chamfer_size,
            chamfer_type=self.outer_pad_chamfer_type,
        )
        cell.shapes(top_layer).insert(top_inner.polygon)
        cell.shapes(top_layer).insert(top_outer.polygon)
        if self.fanout_length > 0:
            cell.shapes(top_layer).insert(
                draw_trapezoidal_fanout(top_inner, top_outer, inner_edge="U", outer_edge="D")
            )

        return cell
