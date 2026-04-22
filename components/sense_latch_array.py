# -*- coding: utf-8 -*-
"""Sense-Latch array generator."""

from __future__ import annotations

import os
import sys
import site
from pathlib import Path
from typing import Dict, Tuple
import xml.etree.ElementTree as ET

def _bootstrap_windows_dll_dirs() -> None:
    """Help Windows find native DLLs bundled inside Python packages."""
    if os.name != "nt" or not hasattr(os, "add_dll_directory"):
        return

    candidates = []
    try:
        candidates.extend(site.getsitepackages())
    except Exception:
        pass
    try:
        user_site = site.getusersitepackages()
        if user_site:
            candidates.append(user_site)
    except Exception:
        pass

    seen = set()
    for base in candidates:
        if not base:
            continue
        klayout_dir = Path(base) / "klayout"
        if not klayout_dir.exists():
            continue
        resolved = str(klayout_dir.resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        try:
            os.add_dll_directory(resolved)
        except OSError:
            pass


_bootstrap_windows_dll_dirs()

import klayout.db as db

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import PROCESS_CONFIG, get_gds_path
from utils.geometry import GeometryUtils


class SenseLatchArray:
    """Planar Sense-Latch pixel array."""

    def __init__(self, layout: db.Layout | None = None, **kwargs):
        self.layout = layout or db.Layout()
        self.layout.dbu = PROCESS_CONFIG["dbu"]
        GeometryUtils.UNIT_SCALE = int(round(1.0 / self.layout.dbu))

        # Array sizing. Prefer square array and square pixel.
        self.array_size = int(kwargs.get("array_size", 8))
        self.rows = int(kwargs.get("rows", self.array_size))
        self.cols = int(kwargs.get("cols", self.array_size))

        self.pixel_size = float(kwargs.get("pixel_size", 120.0))
        self.pixel_width = float(kwargs.get("pixel_width", self.pixel_size))
        self.pixel_height = float(kwargs.get("pixel_height", self.pixel_size))
        self.origin_mode = str(kwargs.get("origin_mode", "center")).lower()
        self.offset_x = float(kwargs.get("offset_x", 0.0))
        self.offset_y = float(kwargs.get("offset_y", 0.0))
        self.origin_x, self.origin_y = self._resolve_array_origin()

        # Device stack selection
        self.stack_base = int(kwargs.get("stack_base", 11))
        self.channel_type = str(kwargs.get("channel_type", "n")).lower()
        self.array_type = "sense_latch"

        # Pixel geometry tuned toward the provided sketch
        self.edge_margin = float(kwargs.get("edge_margin", 10.0))
        self.trail_edge_margin = float(kwargs.get("trail_edge_margin", self.edge_margin))
        self.contact_spine_width = float(kwargs.get("contact_spine_width", 8.0))
        self.fet_gap = float(kwargs.get("fet_gap", kwargs.get("center_contact_width", 10.0)))
        self.shared_contact_height = float(kwargs.get("shared_contact_height", kwargs.get("center_contact_height", 52.0)))
        self.contact_tail_margin = float(kwargs.get("contact_tail_margin", 0.0))
        self.outer_contact_min_length = float(kwargs.get("outer_contact_min_length", 2.0))

        # User-facing tunable transistor parameters
        self.gate_line_width = float(kwargs.get("gate_line_width", kwargs.get("gate_rail_height", 8.0)))
        self.sens_width = float(kwargs.get("sens_width", 56.0))
        self.latch_width = float(kwargs.get("latch_width", 44.0))
        self.sens_length = float(kwargs.get("sens_length", 18.0))
        self.latch_length = float(kwargs.get("latch_length", 16.0))
        self.sense_fet_structure = self._normalize_sense_fet_structure(kwargs.get("sense_fet_structure", "plain"))
        self.sense_interdigit_finger_width = float(kwargs.get("sense_interdigit_finger_width", 2.0))
        self.sense_interdigit_finger_spacing = float(kwargs.get("sense_interdigit_finger_spacing", 1.0))
        self.sense_interdigit_tip_gap = float(kwargs.get("sense_interdigit_tip_gap", 1.5))
        self.sens_channel_overlap = float(kwargs.get("sens_channel_overlap", 2.0))
        self.latch_channel_overlap = float(kwargs.get("latch_channel_overlap", 2.0))
        self.sens_pad_overhang = float(kwargs.get("sens_pad_overhang", 4.0))
        self.latch_pad_overhang = float(kwargs.get("latch_pad_overhang", 4.0))
        forbidden = sorted(
            {
                "write_width",
                "read_width",
                "write_length",
                "read_length",
                "write_channel_overlap",
                "read_channel_overlap",
                "write_pad_overhang",
                "read_pad_overhang",
                "array_type",
            }.intersection(kwargs)
        )
        if forbidden:
            raise ValueError("SenseLatchArray received unsupported parameters: " + ", ".join(forbidden))

        # Derived/secondary gate geometry
        self.gate_rail_height = self.gate_line_width
        self.gate_extension = float(kwargs.get("gate_extension", 2.0))
        self.gate_length_overhang = float(kwargs.get("gate_length_overhang", self.gate_extension))
        self.gate_width_overhang = float(kwargs.get("gate_width_overhang", 4.0))
        self.gate_gap = float(kwargs.get("gate_gap", 6.0))

        self.channel_margin = float(kwargs.get("channel_margin", 6.0))
        self.channel_edge_gap = float(kwargs.get("channel_edge_gap", 4.0))
        self.contact_overlap_margin = float(kwargs.get("contact_overlap_margin", 2.0))
        self.draw_channel = bool(kwargs.get("draw_channel", True))
        self.draw_top_dielectric = bool(kwargs.get("draw_top_dielectric", False))
        self.draw_array_pads = bool(kwargs.get("draw_array_pads", True))
        self.array_pad_size = float(kwargs.get("array_pad_size", 20.0))
        self.array_pad_overlap = float(kwargs.get("array_pad_overlap", 4.0))
        self.gate_pad_offset = float(kwargs.get("gate_pad_offset", 18.0))
        self.contact_pad_offset = float(kwargs.get("contact_pad_offset", 18.0))
        self.gate_pad_pitch = float(kwargs.get("gate_pad_pitch", 26.0))
        self.pad_connection_style = str(kwargs.get("pad_connection_style", "line")).lower()

        # Annotations/debug
        self.note_text_enabled = bool(kwargs.get("note_text_enabled", True))
        self.show_pixel_outline = bool(kwargs.get("show_pixel_outline", False))
        self.pixel_outline_layer = int(kwargs.get("pixel_outline_layer", 6))

        self._setup_layers()
        self._validate()

    def _setup_layers(self) -> None:
        if self.stack_base not in (11, 21):
            raise ValueError("stack_base must be 11 or 21")
        if self.channel_type not in ("n", "p"):
            raise ValueError("channel_type must be 'n' or 'p'")

        channel_layer = self.stack_base + (2 if self.channel_type == "n" else 3)
        contact_layer = self.stack_base + (4 if self.channel_type == "n" else 5)

        self.layers: Dict[str, int] = {
            "bottom_gate": self.layout.layer(self.stack_base + 0, 0),
            "bottom_dielectric": self.layout.layer(self.stack_base + 1, 0),
            "channel": self.layout.layer(channel_layer, 0),
            "contact": self.layout.layer(contact_layer, 0),
            "top_dielectric": self.layout.layer(self.stack_base + 6, 0),
            "top_gate": self.layout.layer(self.stack_base + 7, 0),
            "metal1": self.layout.layer(31, 0),
            "via1": self.layout.layer(32, 0),
            "metal2": self.layout.layer(33, 0),
            "pad": self.layout.layer(41, 0),
            "note": self.layout.layer(6, 0),
        }

    @staticmethod
    def _normalize_sense_fet_structure(value: object) -> str:
        normalized = str(value or "plain").strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "plain": "plain",
            "naive": "plain",
            "current": "plain",
            "default": "plain",
            "interdigitated": "interdigitated",
            "finger": "interdigitated",
            "fingered": "interdigitated",
            "interdigit": "interdigitated",
        }
        if normalized not in aliases:
            raise ValueError("sense_fet_structure must be 'plain' or 'interdigitated'")
        return aliases[normalized]

    def _default_cell_name(self) -> str:
        return "Sense_Latch_Array"

    def _resolve_array_origin(self) -> Tuple[float, float]:
        total_w = self.cols * self.pixel_size
        total_h = self.rows * self.pixel_size

        if self.origin_mode in ("center", "center_at_origin"):
            return -total_w / 2.0 + self.offset_x, -total_h / 2.0 + self.offset_y
        if self.origin_mode in ("lower_left", "left_bottom", "corner"):
            return 0.0 + self.offset_x, 0.0 + self.offset_y
        raise ValueError("origin_mode must be 'center' or 'lower_left'")

    def _get_assembly_active_width(self) -> float:
        """Width of the two-FET assembly measured between outer contact edges."""
        return self.sens_length + self.fet_gap + self.latch_length

    def get_min_pixel_size_x(self) -> float:
        """Horizontal pixel threshold from contact trails and centered two-FET assembly."""
        return (
            2.0 * self.trail_edge_margin
            + self.contact_spine_width
            + 2.0 * self.outer_contact_min_length
            + self.sens_length
            + self.fet_gap
            + self.latch_length
        )

    def get_min_pixel_size_y(self) -> float:
        """Vertical pixel threshold from gate stack and widest contact/gate bodies."""
        sens_contact_height = self.sens_width + 2.0 * self.sens_pad_overhang
        latch_contact_height = self.latch_width + 2.0 * self.latch_pad_overhang
        sens_gate_height = self.sens_width + 2.0 * self.gate_width_overhang
        latch_gate_height = self.latch_width + 2.0 * self.gate_width_overhang
        return max(
            2.0 * self.edge_margin + 2.0 * self.gate_line_width + self.gate_gap,
            max(sens_contact_height, latch_contact_height, self.shared_contact_height) + 2.0 * self.contact_tail_margin,
            max(sens_gate_height, latch_gate_height) + 2.0 * self.contact_tail_margin,
        )

    def get_min_pixel_size(self) -> float:
        """Overall square-pixel threshold."""
        return max(self.get_min_pixel_size_x(), self.get_min_pixel_size_y())

    def _validate(self) -> None:
        if self.rows < 1 or self.cols < 1:
            raise ValueError("rows and cols must be >= 1")
        if abs(self.pixel_width - self.pixel_height) > 1e-9:
            raise ValueError("This compact version expects square pixels: pixel_width must equal pixel_height")
        if self.origin_mode not in ("center", "center_at_origin", "lower_left", "left_bottom", "corner"):
            raise ValueError("origin_mode must be 'center' or 'lower_left'")
        device_dims = (
            self.sens_width,
            self.latch_width,
            self.sens_length,
            self.latch_length,
            self.gate_line_width,
        )
        if min(device_dims) <= 0:
            raise ValueError("device widths, lengths, fet_gap, and gate_line_width must be > 0")

        if min(
            self.edge_margin,
            self.trail_edge_margin,
            self.contact_tail_margin,
            self.channel_margin,
            self.channel_edge_gap,
            self.array_pad_overlap,
            self.sens_channel_overlap,
            self.latch_channel_overlap,
            self.sens_pad_overhang,
            self.latch_pad_overhang,
            self.gate_length_overhang,
            self.gate_width_overhang,
        ) < 0:
            raise ValueError("all edge/channel/gate/contact overhang margins must be >= 0")
        if self.draw_array_pads and min(
            self.array_pad_size,
            self.gate_pad_offset,
            self.contact_pad_offset,
            self.gate_pad_pitch,
        ) <= 0:
            raise ValueError(
                "array_pad_size, gate_pad_offset, contact_pad_offset, and gate_pad_pitch must be > 0"
            )
        if self.pad_connection_style not in ("line", "block"):
            raise ValueError("pad_connection_style must be 'line' or 'block'")
        if self.sense_fet_structure not in ("plain", "interdigitated"):
            raise ValueError("sense_fet_structure must be 'plain' or 'interdigitated'")

        channel_height = min(self.sens_width, self.latch_width) - 2.0 * self.channel_margin
        channel_width = self.pixel_size - 2.0 * self.channel_edge_gap
        if self.draw_channel and channel_height <= 0:
            raise ValueError(
                "channel_margin is too large; channel height must remain positive and narrower than both contact pads"
            )
        if self.draw_channel and channel_width <= 0:
            raise ValueError("channel_edge_gap is too large; channel width must remain positive")

        min_size_x = self.get_min_pixel_size_x()
        min_size_y = self.get_min_pixel_size_y()
        min_size = max(min_size_x, min_size_y)
        if self.pixel_size < min_size:
            raise ValueError(
                f"pixel_size={self.pixel_size} is too small; "
                f"needs to be >= {min_size:.1f} um "
                f"(x-threshold={min_size_x:.1f} um, y-threshold={min_size_y:.1f} um)"
            )

        if self.sense_fet_structure == "interdigitated":
            if min(
                self.sense_interdigit_finger_width,
                self.sense_interdigit_tip_gap,
            ) <= 0:
                raise ValueError("sense_interdigit_finger_width and sense_interdigit_tip_gap must be > 0")
            if self.sense_interdigit_finger_spacing < 0:
                raise ValueError("sense_interdigit_finger_spacing must be >= 0")

            sense_contact_h = self.sens_width + 2.0 * self.sens_pad_overhang
            finger_count = self._sense_interdigit_finger_count(sense_contact_h)
            if finger_count < 2:
                raise ValueError(
                    "interdigitated sense FET does not fit vertically; "
                    "reduce sense_interdigit_finger_width or sense_interdigit_finger_spacing"
                )
            if self.sense_interdigit_tip_gap >= self.sens_length:
                raise ValueError("sense_interdigit_tip_gap must be smaller than sens_length")

    def _insert_box(self, cell: db.Cell, layer_key: str, cx: float, cy: float, w: float, h: float) -> db.Box:
        box = GeometryUtils.create_rectangle(cx, cy, w, h, center=True)
        cell.shapes(self.layers[layer_key]).insert(box)
        return box

    def _region_from_box(self, cx: float, cy: float, w: float, h: float) -> db.Region:
        return db.Region(GeometryUtils.create_rectangle(cx, cy, w, h, center=True))

    def _draw_pad_connection(
        self,
        cell: db.Cell,
        layer_key: str,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        line_width: float,
        pad_size: float,
    ) -> None:
        if self.pad_connection_style == "block":
            width = abs(x1 - x0) + pad_size
            height = abs(y1 - y0) + pad_size
            self._insert_box(cell, layer_key, (x0 + x1) / 2.0, (y0 + y1) / 2.0, width, height)
            return

        if abs(y1 - y0) < 1e-9:
            self._insert_box(
                cell,
                layer_key,
                (x0 + x1) / 2.0,
                y0,
                abs(x1 - x0) + pad_size,
                line_width,
            )
        elif abs(x1 - x0) < 1e-9:
            self._insert_box(
                cell,
                layer_key,
                x0,
                (y0 + y1) / 2.0,
                line_width,
                abs(y1 - y0) + pad_size,
            )
        else:
            # Fallback for any future jog connection.
            self._insert_box(cell, layer_key, (x0 + x1) / 2.0, y0, abs(x1 - x0) + pad_size, line_width)
            self._insert_box(cell, layer_key, x1, (y0 + y1) / 2.0, line_width, abs(y1 - y0) + pad_size)

    def _insert_note_text(self, cell: db.Cell, text: str, x: float, y: float) -> None:
        if not self.note_text_enabled:
            return
        scale = int(round(1.0 / self.layout.dbu))
        cell.shapes(self.layers["note"]).insert(db.Text(text, int(round(x * scale)), int(round(y * scale))))

    def _side_label_specs(self) -> dict:
        return {
            "top_gate": ("Scan Line", "SL"),
            "bottom_gate": ("Read", "R"),
            "left_contact": ("Switch", "Sw"),
            "right_contact": ("Data", "D"),
        }

    def _draw_note_labels(self, cell: db.Cell) -> None:
        if not self.note_text_enabled:
            return

        labels = self._side_label_specs()
        total_w = self.cols * self.pixel_size
        total_h = self.rows * self.pixel_size
        left_edge_x = self.origin_x
        right_edge_x = self.origin_x + total_w
        top_edge_y = self.origin_y + total_h
        bottom_edge_y = self.origin_y
        pad_offset = self.array_pad_size / 2.0 + 4.0

        top_name, top_prefix = labels["top_gate"]
        bottom_name, bottom_prefix = labels["bottom_gate"]
        left_name, left_prefix = labels["left_contact"]
        right_name, right_prefix = labels["right_contact"]

        # One side-level label per network, then per-pad index labels beside each breakout pad.
        self._insert_note_text(
            cell,
            top_name,
            left_edge_x - self.gate_pad_offset - self.array_pad_size * 2.0,
            top_edge_y + self.gate_line_width,
        )
        self._insert_note_text(
            cell,
            bottom_name,
            right_edge_x + self.gate_pad_offset + self.array_pad_size * 1.2,
            bottom_edge_y - self.gate_line_width - self.array_pad_size * 0.8,
        )
        self._insert_note_text(
            cell,
            left_name,
            left_edge_x - self.array_pad_size * 1.2,
            bottom_edge_y - self.contact_pad_offset - self.array_pad_size * 2.0,
        )
        self._insert_note_text(
            cell,
            right_name,
            right_edge_x + self.array_pad_size * 0.2,
            top_edge_y + self.contact_pad_offset + self.array_pad_size * 1.2,
        )

        for row in range(self.rows):
            pixel = self._pixel_geometry(row, 0)
            self._insert_note_text(
                cell,
                f"{top_prefix}[{row}]",
                left_edge_x - self.gate_pad_offset - self.array_pad_size / 2.0 + self.array_pad_overlap,
                pixel["top_rail_y"],
            )
            self._insert_note_text(
                cell,
                f"{bottom_prefix}[{row}]",
                right_edge_x + self.gate_pad_offset + self.array_pad_size / 2.0 - self.array_pad_overlap,
                pixel["bottom_rail_y"],
            )

        for col in range(self.cols):
            pixel = self._pixel_geometry(0, col)
            self._insert_note_text(
                cell,
                f"{left_prefix}[{col}]",
                pixel["left_spine_x"],
                bottom_edge_y - self.contact_pad_offset - self.array_pad_size / 2.0 + self.array_pad_overlap,
            )
            self._insert_note_text(
                cell,
                f"{right_prefix}[{col}]",
                pixel["right_spine_x"],
                top_edge_y + self.contact_pad_offset + self.array_pad_size / 2.0 - self.array_pad_overlap,
            )

    def _reference_indices(self) -> Tuple[int, int]:
        return self.rows // 2, self.cols // 2

    def _build_ruler(self, rid: int, x1: float, y1: float, x2: float, y2: float, label: str) -> ET.Element:
        annotation = ET.Element("annotation")
        klass = ET.SubElement(annotation, "class")
        klass.text = "ant::Object"
        value = ET.SubElement(annotation, "value")
        value.text = (
            f"id={rid},x1={x1:.6f},y1={y1:.6f},x2={x2:.6f},y2={y2:.6f},"
            f"category=_ruler,fmt='{label}=$D',fmt_x=$X,fmt_y=$Y,"
            "position=auto,xalign=auto,yalign=auto,"
            "xlabel_xalign=auto,xlabel_yalign=auto,"
            "ylabel_xalign=auto,ylabel_yalign=auto,"
            "style=ruler,outline=diag,snap=true,angle_constraint=global"
        )
        return annotation

    def _collect_parameter_rulers(self) -> list[ET.Element]:
        row, col = self._reference_indices()
        pixel = self._pixel_geometry(row, col)
        x0, y0, x1, y1, cy = pixel["x0"], pixel["y0"], pixel["x1"], pixel["y1"], pixel["cy"]
        left_spine_l = pixel["left_spine_x"] - self.contact_spine_width / 2.0
        left_spine_r = pixel["left_spine_x"] + self.contact_spine_width / 2.0
        right_spine_l = pixel["right_spine_x"] - self.contact_spine_width / 2.0
        right_spine_r = pixel["right_spine_x"] + self.contact_spine_width / 2.0
        center_contact_top = cy + pixel["center_contact_h"] / 2.0
        sens_channel_top = cy + pixel["sens_channel_h"] / 2.0
        latch_channel_top = cy + pixel["latch_channel_h"] / 2.0
        sens_contact_top = cy + pixel["sens_contact_h"] / 2.0
        latch_contact_top = cy + pixel["latch_contact_h"] / 2.0
        top_rail_top = pixel["top_rail_y"] + self.gate_line_width / 2.0
        gate_body_top = pixel["upper_gate_body_top_y"]

        left_edge_x = self.origin_x
        right_edge_x = self.origin_x + self.cols * self.pixel_size
        top_edge_y = self.origin_y + self.rows * self.pixel_size
        bottom_edge_y = self.origin_y
        half_pad = self.array_pad_size / 2.0
        upper_left_pad_x = left_edge_x - self.gate_pad_offset - half_pad + self.array_pad_overlap
        lower_right_pad_x = right_edge_x + self.gate_pad_offset + half_pad - self.array_pad_overlap
        top_contact_pad_y = top_edge_y + self.contact_pad_offset + half_pad - self.array_pad_overlap
        bottom_contact_pad_y = bottom_edge_y - self.contact_pad_offset - half_pad + self.array_pad_overlap

        specs = [
            (x0, y0 - 3.0, x1, y0 - 3.0, "pixel_size"),
            (x0, y1, x0, top_rail_top, "edge_margin"),
            (x0, y0 + 4.0, left_spine_l, y0 + 4.0, "trail_edge_margin"),
            (left_spine_l, y0 + 7.0, left_spine_r, y0 + 7.0, "contact_spine_width"),
            (left_spine_r, cy + 3.0, pixel["left_head_right"], cy + 3.0, "sens_outer_contact_length"),
            (pixel["left_head_right"], cy, pixel["center_contact_left"], cy, "sens_length"),
            (pixel["center_contact_right"], cy, pixel["right_head_left"], cy, "latch_length"),
            (pixel["right_head_left"], cy - 3.0, right_spine_l, cy - 3.0, "latch_outer_contact_length"),
            (pixel["sens_channel_cx"], cy - pixel["sens_channel_h"] / 2.0, pixel["sens_channel_cx"], sens_channel_top, "sens_width"),
            (pixel["latch_channel_cx"], cy - pixel["latch_channel_h"] / 2.0, pixel["latch_channel_cx"], latch_channel_top, "latch_width"),
            (pixel["left_head_right"], cy - 6.0, pixel["sens_channel_cx"] - pixel["sens_channel_w"] / 2.0, cy - 6.0, "sens_channel_overlap"),
            (pixel["latch_channel_cx"] + pixel["latch_channel_w"] / 2.0, cy - 9.0, pixel["right_head_left"], cy - 9.0, "latch_channel_overlap"),
            (pixel["left_head_cx"], sens_channel_top, pixel["left_head_cx"], sens_contact_top, "sens_pad_overhang"),
            (pixel["right_head_cx"], latch_channel_top, pixel["right_head_cx"], latch_contact_top, "latch_pad_overhang"),
            (pixel["center_contact_left"], center_contact_top + 3.0, pixel["center_contact_right"], center_contact_top + 3.0, "fet_gap"),
            (pixel["center_contact_x"], cy - pixel["center_contact_h"] / 2.0, pixel["center_contact_x"], center_contact_top, "shared_contact_height"),
            (x0 + 2.0, pixel["top_rail_y"] - self.gate_line_width / 2.0, x0 + 2.0, top_rail_top, "gate_line_width"),
            (pixel["left_head_right"], gate_body_top + 3.0, pixel["upper_gate_x0"], gate_body_top + 3.0, "gate_length_overhang"),
            (pixel["upper_gate_x0"], sens_channel_top, pixel["upper_gate_x0"], gate_body_top, "gate_width_overhang"),
            (x0 + 2.0, y0 + 12.0, x0 + 2.0 + self.outer_contact_min_length, y0 + 12.0, "outer_contact_min_length"),
            (left_edge_x, pixel["top_rail_y"], upper_left_pad_x, pixel["top_rail_y"], "gate_pad_offset"),
            (pixel["left_spine_x"], bottom_edge_y, pixel["left_spine_x"], bottom_contact_pad_y, "contact_pad_offset"),
            (upper_left_pad_x, pixel["top_rail_y"] + self.array_pad_size / 2.0 + 3.0, upper_left_pad_x + self.array_pad_size, pixel["top_rail_y"] + self.array_pad_size / 2.0 + 3.0, "array_pad_size"),
        ]

        rulers: list[ET.Element] = []
        for rid, spec in enumerate(specs):
            rulers.append(self._build_ruler(rid, *spec))
        return rulers

    def write_rule_session(
        self,
        gds_filename: str | None = None,
        lys_filename: str | None = None,
        cell_name: str | None = None,
    ) -> str:
        cell_name = cell_name or self._default_cell_name()
        gds_filename = gds_filename or f"{cell_name}.gds"
        lys_filename = lys_filename or f"{cell_name}_rules.lys"
        gds_path = self.write_gds(filename=gds_filename, cell_name=cell_name)
        total_w, total_h = self.get_array_size()
        left_edge_x = self.origin_x
        right_edge_x = self.origin_x + total_w
        top_edge_y = self.origin_y + total_h
        bottom_edge_y = self.origin_y
        extra = max(self.array_pad_size + self.gate_pad_offset, self.array_pad_size + self.contact_pad_offset, 10.0)

        session = ET.Element("session")
        layout = ET.SubElement(session, "layout")
        ET.SubElement(layout, "name").text = Path(gds_path).name
        ET.SubElement(layout, "file-path").text = gds_path

        view = ET.SubElement(session, "view")
        ET.SubElement(view, "title")
        ET.SubElement(view, "active-cellview-index").text = "0"
        display = ET.SubElement(view, "display")
        ET.SubElement(display, "x-left").text = f"{left_edge_x - extra:.6f}"
        ET.SubElement(display, "x-right").text = f"{right_edge_x + extra:.6f}"
        ET.SubElement(display, "y-bottom").text = f"{bottom_edge_y - extra:.6f}"
        ET.SubElement(display, "y-top").text = f"{top_edge_y + extra:.6f}"
        ET.SubElement(display, "min-hier").text = "0"
        ET.SubElement(display, "max-hier").text = "1"
        cellpaths = ET.SubElement(display, "cellpaths")
        cellpath = ET.SubElement(cellpaths, "cellpath")
        ET.SubElement(cellpath, "cellname").text = cell_name

        cellviews = ET.SubElement(view, "cellviews")
        cellview = ET.SubElement(cellviews, "cellview")
        ET.SubElement(cellview, "layout-ref").text = Path(gds_path).name
        ET.SubElement(cellview, "tech-name").text = "LabPDK"

        annotations = ET.SubElement(view, "annotations")
        for annotation in self._collect_parameter_rulers():
            annotations.append(annotation)

        ET.indent(session, space=" ", level=0)
        lys_path = str(Path(get_gds_path(lys_filename)).resolve())
        tree = ET.ElementTree(session)
        tree.write(lys_path, encoding="utf-8", xml_declaration=True)
        return lys_path

    def _pixel_origin(self, row: int, col: int) -> Tuple[float, float]:
        return (
            self.origin_x + col * self.pixel_size,
            self.origin_y + row * self.pixel_size,
        )

    def _pixel_geometry_sense_latch(self, row: int, col: int) -> Dict[str, float]:
        x0, y0 = self._pixel_origin(row, col)
        x1 = x0 + self.pixel_size
        y1 = y0 + self.pixel_size
        w = self.pixel_size
        h = self.pixel_size
        cy = y0 + h / 2.0

        top_rail_y = y0 + h - self.edge_margin - self.gate_line_width / 2.0
        bottom_rail_y = y0 + self.edge_margin + self.gate_line_width / 2.0
        left_spine_x = x0 + self.trail_edge_margin + self.contact_spine_width / 2.0
        right_spine_x = x1 - self.trail_edge_margin - self.contact_spine_width / 2.0
        available_x = right_spine_x - left_spine_x
        required_x = self._get_assembly_active_width()
        if available_x < required_x:
            raise ValueError(
                "pixel_size is too small for the requested device lengths and contact geometry"
            )
        slack_x = available_x - required_x
        left_contact_length = slack_x / 2.0
        right_contact_length = slack_x - left_contact_length
        if min(left_contact_length, right_contact_length) < self.outer_contact_min_length:
            raise ValueError(
                "pixel_size is too small for the requested centered FET assembly and minimum outer contact length"
            )

        left_head_left = left_spine_x
        left_head_right = left_head_left + left_contact_length
        center_contact_left = left_head_right + self.sens_length
        center_contact_right = center_contact_left + self.fet_gap
        right_head_left = center_contact_right + self.latch_length
        right_head_right = right_head_left + right_contact_length

        sens_channel_cx = (left_head_right + center_contact_left) / 2.0
        latch_channel_cx = (center_contact_right + right_head_left) / 2.0
        center_contact_x = (center_contact_left + center_contact_right) / 2.0
        head_center_y = cy
        left_head_cx = (left_head_left + left_head_right) / 2.0
        right_head_cx = (right_head_left + right_head_right) / 2.0

        sens_channel_h = self.sens_width
        latch_channel_h = self.latch_width
        sens_channel_left = left_head_right - self.sens_channel_overlap
        sens_channel_right = center_contact_left + self.sens_channel_overlap
        latch_channel_left = center_contact_right - self.latch_channel_overlap
        latch_channel_right = right_head_left + self.latch_channel_overlap
        sens_contact_h = self.sens_width + 2.0 * self.sens_pad_overhang
        latch_contact_h = self.latch_width + 2.0 * self.latch_pad_overhang
        center_contact_h = max(sens_contact_h, latch_contact_h, self.shared_contact_height)

        sens_gate_h = self.sens_width + 2.0 * self.gate_width_overhang
        latch_gate_h = self.latch_width + 2.0 * self.gate_width_overhang
        upper_gate_x0 = sens_channel_left - self.gate_length_overhang
        upper_gate_x1 = sens_channel_right + self.gate_length_overhang
        lower_gate_x0 = latch_channel_left - self.gate_length_overhang
        lower_gate_x1 = latch_channel_right + self.gate_length_overhang
        upper_gate_body_top_y = cy + sens_gate_h / 2.0
        upper_gate_body_bottom_y = cy - sens_gate_h / 2.0
        lower_gate_body_top_y = cy + latch_gate_h / 2.0
        lower_gate_body_bottom_y = cy - latch_gate_h / 2.0
        upper_gate_bottom_y = upper_gate_body_bottom_y
        upper_gate_top_y = top_rail_y + self.gate_line_width / 2.0
        lower_gate_bottom_y = bottom_rail_y - self.gate_line_width / 2.0
        lower_gate_top_y = lower_gate_body_top_y

        return {
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1,
            "w": w,
            "h": h,
            "cy": cy,
            "top_rail_y": top_rail_y,
            "bottom_rail_y": bottom_rail_y,
            "left_spine_x": left_spine_x,
            "right_spine_x": right_spine_x,
            "left_head_left": left_head_left,
            "left_head_right": left_head_right,
            "center_contact_x": center_contact_x,
            "center_contact_left": center_contact_left,
            "center_contact_right": center_contact_right,
            "right_head_left": right_head_left,
            "right_head_right": right_head_right,
            "left_head_cx": left_head_cx,
            "right_head_cx": right_head_cx,
            "head_center_y": head_center_y,
            "left_bridge_w": 0.0,
            "right_bridge_w": 0.0,
            "left_head_w": left_head_right - left_head_left,
            "right_head_w": right_head_right - right_head_left,
            "sens_contact_h": sens_contact_h,
            "latch_contact_h": latch_contact_h,
            "center_contact_h": center_contact_h,
            "sens_channel_cx": sens_channel_cx,
            "latch_channel_cx": latch_channel_cx,
            "sens_channel_w": sens_channel_right - sens_channel_left,
            "latch_channel_w": latch_channel_right - latch_channel_left,
            "sens_channel_h": sens_channel_h,
            "latch_channel_h": latch_channel_h,
            "upper_gate_x0": upper_gate_x0,
            "upper_gate_x1": upper_gate_x1,
            "upper_gate_cx": (upper_gate_x0 + upper_gate_x1) / 2.0,
            "upper_gate_w": upper_gate_x1 - upper_gate_x0,
            "upper_gate_bottom_y": upper_gate_bottom_y,
            "upper_gate_top_y": upper_gate_top_y,
            "upper_gate_body_top_y": upper_gate_body_top_y,
            "upper_gate_body_bottom_y": upper_gate_body_bottom_y,
            "lower_gate_x0": lower_gate_x0,
            "lower_gate_x1": lower_gate_x1,
            "lower_gate_cx": (lower_gate_x0 + lower_gate_x1) / 2.0,
            "lower_gate_w": lower_gate_x1 - lower_gate_x0,
            "lower_gate_bottom_y": lower_gate_bottom_y,
            "lower_gate_top_y": lower_gate_top_y,
            "lower_gate_body_top_y": lower_gate_body_top_y,
            "lower_gate_body_bottom_y": lower_gate_body_bottom_y,
        }

    def _pixel_geometry_write_read(self, row: int, col: int) -> Dict[str, float]:
        x0, y0 = self._pixel_origin(row, col)
        x1 = x0 + self.pixel_size
        y1 = y0 + self.pixel_size
        h = self.pixel_size
        cy = y0 + h / 2.0

        top_rail_y = y0 + h - self.edge_margin - self.gate_line_width / 2.0
        bottom_rail_y = y0 + self.edge_margin + self.gate_line_width / 2.0
        left_spine_x = x0 + self.trail_edge_margin + self.contact_spine_width / 2.0
        right_spine_x = x1 - self.trail_edge_margin - self.contact_spine_width / 2.0
        available_x = right_spine_x - left_spine_x
        required_x = self.write_length + self.fet_gap + self.read_length
        if available_x < required_x:
            raise ValueError("pixel_size is too small for the requested Write_Read geometry")

        slack_x = available_x - required_x
        left_contact_length = slack_x / 2.0
        right_contact_length = slack_x - left_contact_length
        if min(left_contact_length, right_contact_length) < self.outer_contact_min_length:
            raise ValueError("pixel_size is too small for the requested Write_Read outer contact length")

        left_head_left = left_spine_x
        left_head_right = left_head_left + left_contact_length
        center_contact_left = left_head_right + self.write_length
        center_contact_right = center_contact_left + self.fet_gap
        right_head_left = center_contact_right + self.read_length
        right_head_right = right_head_left + right_contact_length

        write_channel_left = left_head_right - self.write_channel_overlap
        write_channel_right = center_contact_left + self.write_channel_overlap
        read_channel_left = center_contact_right - self.read_channel_overlap
        read_channel_right = right_head_left + self.read_channel_overlap

        write_channel_h = self.write_width
        read_channel_h = self.read_width
        write_contact_h = self.write_width + 2.0 * self.write_pad_overhang
        read_contact_h = self.read_width + 2.0 * self.read_pad_overhang
        center_contact_h = max(write_contact_h, read_contact_h, self.shared_contact_height)

        upper_gate_x0 = write_channel_left - self.gate_length_overhang
        upper_gate_x1 = write_channel_right + self.gate_length_overhang
        lower_gate_x0 = read_channel_left - self.gate_length_overhang
        lower_gate_x1 = read_channel_right + self.gate_length_overhang
        upper_gate_h = self.write_width + 2.0 * self.gate_width_overhang
        lower_gate_h = self.read_width + 2.0 * self.gate_width_overhang

        return {
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1,
            "cy": cy,
            "top_rail_y": top_rail_y,
            "bottom_rail_y": bottom_rail_y,
            "left_spine_x": left_spine_x,
            "right_spine_x": right_spine_x,
            "left_head_left": left_head_left,
            "left_head_right": left_head_right,
            "center_contact_left": center_contact_left,
            "center_contact_right": center_contact_right,
            "center_contact_x": (center_contact_left + center_contact_right) / 2.0,
            "right_head_left": right_head_left,
            "right_head_right": right_head_right,
            "left_head_cx": (left_head_left + left_head_right) / 2.0,
            "right_head_cx": (right_head_left + right_head_right) / 2.0,
            "head_center_y": cy,
            "left_head_w": left_head_right - left_head_left,
            "right_head_w": right_head_right - right_head_left,
            "write_contact_h": write_contact_h,
            "read_contact_h": read_contact_h,
            "center_contact_h": center_contact_h,
            "write_channel_cx": (write_channel_left + write_channel_right) / 2.0,
            "read_channel_cx": (read_channel_left + read_channel_right) / 2.0,
            "write_channel_w": write_channel_right - write_channel_left,
            "read_channel_w": read_channel_right - read_channel_left,
            "write_channel_h": write_channel_h,
            "read_channel_h": read_channel_h,
            "upper_gate_x0": upper_gate_x0,
            "upper_gate_x1": upper_gate_x1,
            "upper_gate_cx": (upper_gate_x0 + upper_gate_x1) / 2.0,
            "upper_gate_w": upper_gate_x1 - upper_gate_x0,
            "upper_gate_body_bottom_y": cy - upper_gate_h / 2.0,
            "upper_gate_body_top_y": cy + upper_gate_h / 2.0,
            "upper_gate_top_y": top_rail_y + self.gate_line_width / 2.0,
            "lower_gate_x0": lower_gate_x0,
            "lower_gate_x1": lower_gate_x1,
            "lower_gate_cx": (lower_gate_x0 + lower_gate_x1) / 2.0,
            "lower_gate_w": lower_gate_x1 - lower_gate_x0,
            "lower_gate_body_bottom_y": cy - lower_gate_h / 2.0,
            "lower_gate_body_top_y": cy + lower_gate_h / 2.0,
            "lower_gate_bottom_y": bottom_rail_y - self.gate_line_width / 2.0,
        }

    def _pixel_geometry(self, row: int, col: int) -> Dict[str, float]:
        if self.array_type == "write_read":
            return self._pixel_geometry_write_read(row, col)
        return self._pixel_geometry_sense_latch(row, col)

    def _draw_global_networks(self, cell: db.Cell) -> None:
        total_w = self.cols * self.pixel_size
        total_h = self.rows * self.pixel_size
        center_x = self.origin_x + total_w / 2.0
        for row in range(self.rows):
            pixel = self._pixel_geometry(row, 0)
            self._insert_box(
                cell,
                "bottom_gate",
                center_x,
                pixel["top_rail_y"],
                total_w,
                self.gate_rail_height,
            )
            self._insert_box(
                cell,
                "bottom_gate",
                center_x,
                pixel["bottom_rail_y"],
                total_w,
                self.gate_rail_height,
            )
        trail_center_y = self.origin_y + total_h / 2.0
        trail_height = max(total_h - 2.0 * self.contact_tail_margin, 0.0)
        for col in range(self.cols):
            pixel = self._pixel_geometry(0, col)
            self._insert_box(
                cell,
                "contact",
                pixel["left_spine_x"],
                trail_center_y,
                self.contact_spine_width,
                trail_height,
            )
            self._insert_box(
                cell,
                "contact",
                pixel["right_spine_x"],
                trail_center_y,
                self.contact_spine_width,
                trail_height,
            )

    def _draw_contact_shape(self, cell: db.Cell, pixel: Dict[str, float]) -> None:
        if self.array_type == "write_read":
            contact_region = db.Region()
            left_body_left = pixel["left_spine_x"] - self.contact_spine_width / 2.0
            left_body_right = pixel["center_contact_x"] + max(self.fet_gap * 0.18, self.contact_spine_width / 2.0)
            right_body_left = pixel["center_contact_x"] - max(self.fet_gap * 0.18, self.contact_spine_width / 2.0)
            right_body_right = pixel["right_spine_x"] + self.contact_spine_width / 2.0

            contact_region += self._region_from_box(
                (left_body_left + left_body_right) / 2.0,
                pixel["head_center_y"],
                left_body_right - left_body_left,
                pixel["write_contact_h"],
            )
            contact_region -= self._region_from_box(
                pixel["write_channel_cx"],
                pixel["cy"],
                pixel["write_channel_w"],
                pixel["write_channel_h"],
            )

            contact_region += self._region_from_box(
                (right_body_left + right_body_right) / 2.0,
                pixel["head_center_y"],
                right_body_right - right_body_left,
                pixel["read_contact_h"],
            )
            contact_region -= self._region_from_box(
                pixel["read_channel_cx"],
                pixel["cy"],
                pixel["read_channel_w"],
                pixel["read_channel_h"],
            )
            cell.shapes(self.layers["contact"]).insert(contact_region.merged())
            return

        contact_region = db.Region()
        if pixel["left_bridge_w"] > 0:
            contact_region += self._region_from_box(
                pixel["left_spine_x"] + pixel["left_bridge_w"] / 2.0,
                pixel["head_center_y"],
                pixel["left_bridge_w"],
                pixel["sens_contact_h"],
            )
        contact_region += self._region_from_box(
            pixel["left_head_cx"],
            pixel["head_center_y"],
            pixel["left_head_w"],
            pixel["sens_contact_h"],
        )
        contact_region += self._region_from_box(
            pixel["right_head_cx"],
            pixel["head_center_y"],
            pixel["right_head_w"],
            pixel["latch_contact_h"],
        )
        if pixel["right_bridge_w"] > 0:
            contact_region += self._region_from_box(
                pixel["right_head_right"] + pixel["right_bridge_w"] / 2.0,
                pixel["head_center_y"],
                pixel["right_bridge_w"],
                pixel["latch_contact_h"],
            )
        contact_region += self._region_from_box(
            pixel["center_contact_x"],
            pixel["head_center_y"],
            self.fet_gap,
            pixel["center_contact_h"],
        )
        if self.sense_fet_structure == "interdigitated":
            contact_region += self._interdigitated_sense_contact_region(pixel)
        cell.shapes(self.layers["contact"]).insert(contact_region.merged())

    def _sense_interdigit_finger_count(self, active_height: float) -> int:
        pitch = self.sense_interdigit_finger_width + self.sense_interdigit_finger_spacing
        if pitch <= 0:
            return 0
        return max(0, int((active_height + self.sense_interdigit_finger_spacing) // pitch))

    def _interdigitated_sense_contact_region(self, pixel: Dict[str, float]) -> db.Region:
        region = db.Region()

        active_height = pixel["sens_contact_h"]
        if active_height <= 0 or self.sens_length <= 0:
            return region

        finger_width = self.sense_interdigit_finger_width
        finger_spacing = self.sense_interdigit_finger_spacing
        finger_count = self._sense_interdigit_finger_count(active_height)
        if finger_count < 2:
            return region

        used_height = finger_count * finger_width + max(0, finger_count - 1) * finger_spacing
        y0 = pixel["cy"] - used_height / 2.0

        source_x1 = pixel["left_head_right"]
        source_x2 = pixel["center_contact_left"] - self.sense_interdigit_tip_gap
        drain_x1 = pixel["left_head_right"] + self.sense_interdigit_tip_gap
        drain_x2 = pixel["center_contact_left"]

        source_finger_w = source_x2 - source_x1
        drain_finger_w = drain_x2 - drain_x1
        if source_finger_w <= 0 or drain_finger_w <= 0:
            return region

        for index in range(finger_count):
            y_bottom = y0 + index * (finger_width + finger_spacing)
            y_top = y_bottom + finger_width
            if index % 2 == 0:
                region += self._region_from_box(
                    (source_x1 + source_x2) / 2.0,
                    (y_bottom + y_top) / 2.0,
                    source_finger_w,
                    y_top - y_bottom,
                )
            else:
                region += self._region_from_box(
                    (drain_x1 + drain_x2) / 2.0,
                    (y_bottom + y_top) / 2.0,
                    drain_finger_w,
                    y_top - y_bottom,
                )
        return region

    def _draw_upper_gate_shape(self, cell: db.Cell, pixel: Dict[str, float]) -> None:
        if self.array_type == "write_read":
            gate_region = db.Region()
            body_left = pixel["left_head_right"] - self.gate_length_overhang
            body_right = pixel["right_head_right"] - self.contact_spine_width * 0.8
            body_bottom = pixel["cy"] - max(self.write_width, self.read_width) * 0.45
            body_top = pixel["top_rail_y"] + self.gate_line_width / 2.0
            gate_region += self._region_from_box(
                (body_left + body_right) / 2.0,
                (body_bottom + body_top) / 2.0,
                body_right - body_left,
                body_top - body_bottom,
            )
            gate_region -= self._region_from_box(
                pixel["write_channel_cx"],
                pixel["cy"],
                pixel["write_channel_w"] * 0.9,
                pixel["write_channel_h"] * 0.65,
            )
            cell.shapes(self.layers["bottom_gate"]).insert(gate_region.merged())
            return

        gate_region = db.Region()
        gate_region += self._region_from_box(
            pixel["upper_gate_cx"],
            (pixel["upper_gate_body_bottom_y"] + pixel["upper_gate_body_top_y"]) / 2.0,
            pixel["upper_gate_w"],
            pixel["upper_gate_body_top_y"] - pixel["upper_gate_body_bottom_y"],
        )
        gate_region += self._region_from_box(
            pixel["upper_gate_cx"],
            (pixel["upper_gate_body_top_y"] + pixel["upper_gate_top_y"]) / 2.0,
            self.gate_line_width,
            pixel["upper_gate_top_y"] - pixel["upper_gate_body_top_y"],
        )
        cell.shapes(self.layers["bottom_gate"]).insert(gate_region.merged())

    def _draw_lower_gate_shape(self, cell: db.Cell, pixel: Dict[str, float]) -> None:
        if self.array_type == "write_read":
            gate_region = db.Region()
            gate_region += self._region_from_box(
                pixel["lower_gate_cx"],
                (pixel["lower_gate_body_bottom_y"] + pixel["lower_gate_body_top_y"]) / 2.0,
                pixel["lower_gate_w"],
                pixel["lower_gate_body_top_y"] - pixel["lower_gate_body_bottom_y"],
            )
            gate_region += self._region_from_box(
                pixel["lower_gate_cx"],
                (pixel["lower_gate_bottom_y"] + pixel["lower_gate_body_bottom_y"]) / 2.0,
                self.gate_line_width,
                pixel["lower_gate_body_bottom_y"] - pixel["lower_gate_bottom_y"],
            )
            cell.shapes(self.layers["bottom_gate"]).insert(gate_region.merged())
            return

        gate_region = db.Region()
        gate_region += self._region_from_box(
            pixel["lower_gate_cx"],
            (pixel["lower_gate_body_bottom_y"] + pixel["lower_gate_body_top_y"]) / 2.0,
            pixel["lower_gate_w"],
            pixel["lower_gate_body_top_y"] - pixel["lower_gate_body_bottom_y"],
        )
        gate_region += self._region_from_box(
            pixel["lower_gate_cx"],
            (pixel["lower_gate_bottom_y"] + pixel["lower_gate_body_bottom_y"]) / 2.0,
            self.gate_line_width,
            pixel["lower_gate_body_bottom_y"] - pixel["lower_gate_bottom_y"],
        )
        cell.shapes(self.layers["bottom_gate"]).insert(gate_region.merged())

    def _draw_channel_shape(self, cell: db.Cell, pixel: Dict[str, float]) -> None:
        if not self.draw_channel:
            return

        channel_region = db.Region()
        if self.array_type == "write_read":
            channel_region += self._region_from_box(
                pixel["write_channel_cx"],
                pixel["cy"],
                pixel["write_channel_w"],
                pixel["write_channel_h"],
            )
            channel_region += self._region_from_box(
                pixel["read_channel_cx"],
                pixel["cy"],
                pixel["read_channel_w"],
                pixel["read_channel_h"],
            )
            cell.shapes(self.layers["channel"]).insert(channel_region.merged())

            if self.draw_top_dielectric:
                diel = db.Region()
                diel += self._region_from_box(
                    pixel["write_channel_cx"],
                    pixel["cy"],
                    pixel["write_channel_w"] + 2.0 * self.contact_overlap_margin,
                    pixel["write_channel_h"] + 2.0 * self.contact_overlap_margin,
                )
                diel += self._region_from_box(
                    pixel["read_channel_cx"],
                    pixel["cy"],
                    pixel["read_channel_w"] + 2.0 * self.contact_overlap_margin,
                    pixel["read_channel_h"] + 2.0 * self.contact_overlap_margin,
                )
                cell.shapes(self.layers["top_dielectric"]).insert(diel.merged())
            return

        channel_region += self._region_from_box(
            pixel["sens_channel_cx"],
            pixel["cy"],
            pixel["sens_channel_w"],
            pixel["sens_channel_h"],
        )
        channel_region += self._region_from_box(
            pixel["latch_channel_cx"],
            pixel["cy"],
            pixel["latch_channel_w"],
            pixel["latch_channel_h"],
        )
        cell.shapes(self.layers["channel"]).insert(channel_region.merged())

        if self.draw_top_dielectric:
            diel = db.Region()
            diel += self._region_from_box(
                pixel["sens_channel_cx"],
                pixel["cy"],
                pixel["sens_channel_w"] + 2.0 * self.contact_overlap_margin,
                pixel["sens_channel_h"] + 2.0 * self.contact_overlap_margin,
            )
            diel += self._region_from_box(
                pixel["latch_channel_cx"],
                pixel["cy"],
                pixel["latch_channel_w"] + 2.0 * self.contact_overlap_margin,
                pixel["latch_channel_h"] + 2.0 * self.contact_overlap_margin,
            )
            cell.shapes(self.layers["top_dielectric"]).insert(diel.merged())

    def _draw_array_pads(self, cell: db.Cell) -> None:
        if not self.draw_array_pads:
            return

        total_w = self.cols * self.pixel_size
        total_h = self.rows * self.pixel_size
        left_edge_x = self.origin_x
        right_edge_x = self.origin_x + total_w
        top_edge_y = self.origin_y + total_h
        bottom_edge_y = self.origin_y
        half_pad = self.array_pad_size / 2.0

        for row in range(self.rows):
            row_pixel = self._pixel_geometry(row, 0)
            upper_left_pad_x = left_edge_x - self.gate_pad_offset - half_pad + self.array_pad_overlap
            lower_right_pad_x = right_edge_x + self.gate_pad_offset + half_pad - self.array_pad_overlap

            # Upper gate: fan out to the left, aligned with the original top rail.
            self._insert_box(cell, "bottom_gate", upper_left_pad_x, row_pixel["top_rail_y"], self.array_pad_size, self.array_pad_size)
            self._insert_box(cell, "pad", upper_left_pad_x, row_pixel["top_rail_y"], self.array_pad_size, self.array_pad_size)
            self._draw_pad_connection(
                cell,
                "bottom_gate",
                left_edge_x,
                row_pixel["top_rail_y"],
                upper_left_pad_x,
                row_pixel["top_rail_y"],
                self.gate_line_width,
                self.array_pad_size,
            )

            # Lower gate: fan out to the right, aligned with the original bottom rail.
            self._insert_box(cell, "bottom_gate", lower_right_pad_x, row_pixel["bottom_rail_y"], self.array_pad_size, self.array_pad_size)
            self._insert_box(cell, "pad", lower_right_pad_x, row_pixel["bottom_rail_y"], self.array_pad_size, self.array_pad_size)
            self._draw_pad_connection(
                cell,
                "bottom_gate",
                right_edge_x,
                row_pixel["bottom_rail_y"],
                lower_right_pad_x,
                row_pixel["bottom_rail_y"],
                self.gate_line_width,
                self.array_pad_size,
            )

        # Contact trails fan out vertically, aligned with the original left/right trail x positions.
        top_contact_pad_y = top_edge_y + self.contact_pad_offset + half_pad - self.array_pad_overlap
        bottom_contact_pad_y = bottom_edge_y - self.contact_pad_offset - half_pad + self.array_pad_overlap

        for col in range(self.cols):
            col_pixel = self._pixel_geometry(0, col)
            # Left contact trail: fan out downward, aligned with original left trail x.
            self._insert_box(cell, "contact", col_pixel["left_spine_x"], bottom_contact_pad_y, self.array_pad_size, self.array_pad_size)
            self._insert_box(cell, "pad", col_pixel["left_spine_x"], bottom_contact_pad_y, self.array_pad_size, self.array_pad_size)
            self._draw_pad_connection(
                cell,
                "contact",
                col_pixel["left_spine_x"],
                bottom_edge_y,
                col_pixel["left_spine_x"],
                bottom_contact_pad_y,
                self.contact_spine_width,
                self.array_pad_size,
            )

            # Right contact trail: fan out upward, aligned with original right trail x.
            self._insert_box(cell, "contact", col_pixel["right_spine_x"], top_contact_pad_y, self.array_pad_size, self.array_pad_size)
            self._insert_box(cell, "pad", col_pixel["right_spine_x"], top_contact_pad_y, self.array_pad_size, self.array_pad_size)
            self._draw_pad_connection(
                cell,
                "contact",
                col_pixel["right_spine_x"],
                top_edge_y,
                col_pixel["right_spine_x"],
                top_contact_pad_y,
                self.contact_spine_width,
                self.array_pad_size,
            )

    def _draw_pixel(self, cell: db.Cell, pixel: Dict[str, float]) -> None:
        self._draw_upper_gate_shape(cell, pixel)
        self._draw_lower_gate_shape(cell, pixel)
        self._draw_channel_shape(cell, pixel)
        self._draw_contact_shape(cell, pixel)

        if self.show_pixel_outline:
            self._insert_box(
                cell,
                "note",
                (pixel["x0"] + pixel["x1"]) / 2.0,
                (pixel["y0"] + pixel["y1"]) / 2.0,
                self.pixel_size,
                self.pixel_size,
            )

    def create_array_cell(self, cell_name: str | None = None) -> db.Cell:
        cell_name = cell_name or self._default_cell_name()
        existing = self.layout.cell(cell_name)
        if existing is not None:
            return existing
        cell = self.layout.create_cell(cell_name)
        self._draw_global_networks(cell)

        for row in range(self.rows):
            for col in range(self.cols):
                self._draw_pixel(cell, self._pixel_geometry(row, col))

        self._draw_array_pads(cell)
        self._draw_note_labels(cell)

        return cell

    def create_variant_cells(self) -> dict[str, db.Cell]:
        created: dict[str, db.Cell] = {}
        current_type = self.array_type
        for variant in ("sense_latch", "write_read"):
            self.array_type = variant
            created[variant] = self.create_array_cell(self._default_cell_name())
        self.array_type = current_type
        return created

    def get_array_size(self) -> Tuple[float, float]:
        return self.cols * self.pixel_size, self.rows * self.pixel_size

    def write_gds(
        self,
        filename: str | None = None,
        cell_name: str | None = None,
        include_all_variants: bool = False,
    ) -> str:
        if include_all_variants:
            self.create_variant_cells()
        else:
            self.create_array_cell(cell_name=cell_name)
        filename = filename or f"{self._default_cell_name()}.gds"
        output_path = get_gds_path(filename)
        self.layout.write(output_path)
        return output_path


def main() -> None:
    try:
        common_kwargs = dict(
            # Array size: use array_size for square arrays, or override with rows/cols.
            array_size=3,

            # Pixel placement and overall pitch.
            pixel_size=50.0,
            # 'center': array center at (0, 0)
            # 'lower_left': array lower-left corner at (0, 0)
            origin_mode="center",
            # Optional additional translation after origin_mode is applied.
            offset_x=0.0,
            offset_y=0.0,

            # Device stack selection: 11 for stack-1, 21 for stack-2.
            stack_base=11,
            # Channel material type on the selected stack.
            channel_type="n",

            # General pixel margins.
            edge_margin=2.0,
            # Horizontal distance from pixel edge to left/right contact trails.
            trail_edge_margin=2.0,
            # Vertical trimming of the column trail at array ends.
            contact_tail_margin=0.0,

            # Contact trail widths inside the array.
            contact_spine_width=4.0,
            # Shared middle region: used as S/D shared node in sense-latch, and S-to-G
            # coupling region in write-read.
            fet_gap=12.0,
            shared_contact_height=12.0,
            # Minimum allowed outer-contact length after centering the full two-device assembly.
            outer_contact_min_length=2.0,

            # Gate rail width for row buses and breakout necks.
            gate_rail_height=4.0,

            # Gate overhang beyond the channel:
            # length_overhang extends along source-drain direction
            # width_overhang extends across the channel width
            gate_extension=2.0,
            gate_length_overhang=2.0,
            gate_width_overhang=2.0,
            # Vertical spacing budget between upper/lower gate routing zones.
            gate_gap=2.0,

            # Channel geometry trimming:
            # channel_margin shrinks channel height relative to device width
            # channel_edge_gap keeps channel away from pixel left/right edges
            channel_margin=2.0,
            channel_edge_gap=2.0,

            # Optional dielectric overlap around channel.
            contact_overlap_margin=2.0,
            draw_channel=True,
            draw_top_dielectric=False,

            # Array fanout pads.
            draw_array_pads=True,
            array_pad_size=20.0,
            # Overlap between breakout pad metal and the fanout connection block/line.
            array_pad_overlap=4.0,
            # Gate pads fan out horizontally from array left/right edges.
            gate_pad_offset=18.0,
            # Contact pads fan out vertically from array top/bottom edges.
            contact_pad_offset=18.0,
            # Reserved pitch for future gate pad staggering if needed.
            gate_pad_pitch=26.0,
            # 'line' keeps a thin neck; 'block' uses a solid rectangular join.
            pad_connection_style="line",

            # Debug drawing.
            note_text_enabled=True,
            show_pixel_outline=False,
            pixel_outline_layer=6,
        )

        sense_latch_kwargs = dict(
            # =========================
            # Sense-FET configuration
            # =========================
            #
            # Shared by both plain and interdigitated modes:
            # length = spacing between the two contact edges of one transistor
            # width  = channel material width of that transistor
            #
            # Choose "plain" to keep the current solid-electrode implementation.
            # Choose "interdigitated" to add alternating source/shared-contact fingers
            # inside the sense-FET footprint only.
            #
            # The example below intentionally uses "interdigitated" so this
            # standalone script demonstrates the full extra parameter set.
            sense_fet_structure="interdigitated",
            sens_width=30.0,
            sens_length=10.0,
            sens_channel_overlap=2.0,
            sens_pad_overhang=2.0,

            # Extra parameters used only when sense_fet_structure == "interdigitated":
            # Inner finger width of each interdigit electrode stripe.
            sense_interdigit_finger_width=2.0,
            # Spacing between adjacent inner electrode stripes.
            sense_interdigit_finger_spacing=1.0,
            # Gap from one side's finger tip to the opposite main electrode body.
            sense_interdigit_tip_gap=1.5,

            # If you want to switch this example back to the original plain
            # structure, set:
            # sense_fet_structure="plain"
            # The interdigit parameters above will then be ignored.

            # =========================
            # Latch-FET configuration
            # =========================
            # Latch-FET geometry always uses the original plain structure.
            latch_width=30.0,
            latch_length=5.0,
            latch_channel_overlap=2.0,
            latch_pad_overhang=2.0,
        )

        component = SenseLatchArray(**common_kwargs, **sense_latch_kwargs)
        output_path = component.write_gds(filename="SENSE_LATCH_ARRAY_TEST.gds", cell_name="Sense_Latch_Array")
        lys_path = component.write_rule_session(
            gds_filename="SENSE_LATCH_ARRAY_TEST.gds",
            lys_filename="SENSE_LATCH_ARRAY_TEST_rules.lys",
            cell_name="Sense_Latch_Array",
        )
        width, height = component.get_array_size()
        print(f"Sense-Latch array written to: {output_path}")
        print(f"Rule session written to: {lys_path}")
        print(f"Array size: {width:.1f} um x {height:.1f} um")
        print(f"Device stack base: {component.stack_base}, channel_type: {component.channel_type}")
    except Exception as exc:
        print(f"SenseLatchArray failed: {exc}")
        raise


if __name__ == "__main__":
    main()
