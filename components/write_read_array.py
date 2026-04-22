# -*- coding: utf-8 -*-
"""Write-Read array generator."""

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


class WriteReadArray:
    """Planar Write-Read pixel array."""

    def __init__(self, layout: db.Layout | None = None, **kwargs):
        self.layout = layout or db.Layout()
        self.layout.dbu = PROCESS_CONFIG["dbu"]
        GeometryUtils.UNIT_SCALE = int(round(1.0 / self.layout.dbu))

        # Array sizing. Prefer square array and square pixel.
        self.array_size = int(kwargs.get("array_size", 3))
        self.rows = int(kwargs.get("rows", self.array_size))
        self.cols = int(kwargs.get("cols", self.array_size))

        self.pixel_size = float(kwargs.get("pixel_size", 50.0))
        self.pixel_width = float(kwargs.get("pixel_width", self.pixel_size))
        self.pixel_height = float(kwargs.get("pixel_height", self.pixel_size))
        self.origin_mode = str(kwargs.get("origin_mode", "center")).lower()
        self.offset_x = float(kwargs.get("offset_x", 0.0))
        self.offset_y = float(kwargs.get("offset_y", 0.0))
        self.origin_x, self.origin_y = self._resolve_array_origin()

        # Device stack selection
        self.stack_base = int(kwargs.get("stack_base", 11))
        self.channel_type = str(kwargs.get("channel_type", "n")).lower()
        # Pixel geometry tuned toward the provided sketch
        self.edge_margin = float(kwargs.get("edge_margin", 2.0))
        self.trail_edge_margin = float(kwargs.get("trail_edge_margin", self.edge_margin))
        self.contact_spine_width = float(kwargs.get("contact_spine_width", 4.0))
        self.fet_gap = float(kwargs.get("fet_gap", 4.0))
        self.shared_contact_height = float(kwargs.get("shared_contact_height", 10.0))
        self.contact_tail_margin = float(kwargs.get("contact_tail_margin", 0.0))
        self.outer_contact_min_length = float(kwargs.get("outer_contact_min_length", 4.0))

        # User-facing tunable write/read transistor parameters
        self.gate_line_width = float(kwargs.get("gate_line_width", kwargs.get("gate_rail_height", 4.0)))
        self.write_width = float(kwargs.get("write_width", 30.0))
        self.read_width = float(kwargs.get("read_width", 13.0))
        self.write_length = float(kwargs.get("write_length", 5.0))
        self.read_length = float(kwargs.get("read_length", 13.5))
        self.write_channel_overlap = float(kwargs.get("write_channel_overlap", 2.0))
        self.read_channel_overlap = float(kwargs.get("read_channel_overlap", 5.0))
        self.write_pad_overhang = float(kwargs.get("write_pad_overhang", 2.0))
        self.read_pad_overhang = float(kwargs.get("read_pad_overhang", 1.0))
        self.write_left_contact_length = float(kwargs.get("write_left_contact_length", 10.0))
        self.write_right_contact_length = float(kwargs.get("write_right_contact_length", 6.0))
        self.read_contact_length = float(kwargs.get("read_contact_length", 10.0))
        self.coupling_gate_pad_size = float(kwargs.get("coupling_gate_pad_size", 15.0))
        self.coupling_via_size = float(kwargs.get("coupling_via_size", 2.0))
        self.read_gate_bridge_width = float(kwargs.get("read_gate_bridge_width", 12.0))
        self.write_gate_x_offset = float(kwargs.get("write_gate_x_offset", -1.5))
        self.rwl_up_extension = float(kwargs.get("rwl_up_extension", 6.0))
        self.read_bottom_overlap_height = float(kwargs.get("read_bottom_overlap_height", 10.0))
        self.write_coupling_via_inset = float(kwargs.get("write_coupling_via_inset", 1.0))
        forbidden = sorted(
            {
                "sens_width",
                "latch_width",
                "sens_length",
                "latch_length",
                "sens_channel_overlap",
                "latch_channel_overlap",
                "sens_pad_overhang",
                "latch_pad_overhang",
                "array_type",
                "center_contact_width",
                "center_contact_height",
            }.intersection(kwargs)
        )
        if forbidden:
            raise ValueError("WriteReadArray received unsupported parameters: " + ", ".join(forbidden))

        # Derived/secondary gate geometry
        self.gate_rail_height = self.gate_line_width
        self.gate_extension = float(kwargs.get("gate_extension", 2.0))
        self.gate_length_overhang = float(kwargs.get("gate_length_overhang", 4.0))
        self.gate_width_overhang = float(kwargs.get("gate_width_overhang", 2.0))
        self.gate_gap = float(kwargs.get("gate_gap", 3.0))

        self.channel_margin = float(kwargs.get("channel_margin", 2.0))
        self.channel_edge_gap = float(kwargs.get("channel_edge_gap", 2.0))
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

    def _default_cell_name(self) -> str:
        return "Write_Read_Array"

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
        return self.write_length + self.fet_gap + self.read_length

    def get_min_pixel_size_x(self) -> float:
        """Horizontal pixel threshold from contact trails and centered two-FET assembly."""
        return (
            2.0 * self.trail_edge_margin
            + self.contact_spine_width
            + self.write_left_contact_length
            + self.write_length
            + self.write_right_contact_length
            + self.fet_gap
            + self.read_width
        )

    def get_min_pixel_size_y(self) -> float:
        """Vertical pixel threshold from gate stack and widest contact/gate bodies."""
        write_contact_height = self.write_width + 2.0 * self.write_pad_overhang
        read_vertical_stack = self.read_contact_length + self.read_length + self.read_contact_length
        write_gate_height = self.write_width + 2.0 * self.gate_width_overhang
        read_gate_height = self.gate_line_width + 2.0 * self.gate_length_overhang
        return max(
            2.0 * self.edge_margin + 2.0 * self.gate_line_width + self.gate_gap,
            max(write_contact_height, read_vertical_stack, self.shared_contact_height) + 2.0 * self.contact_tail_margin,
            max(write_gate_height, read_gate_height) + 2.0 * self.contact_tail_margin,
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
            self.write_width,
            self.read_width,
            self.write_length,
            self.read_length,
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
            self.write_channel_overlap,
            self.read_channel_overlap,
            self.write_pad_overhang,
            self.read_pad_overhang,
            self.gate_length_overhang,
            self.gate_width_overhang,
            self.rwl_up_extension,
            self.read_bottom_overlap_height,
            self.write_coupling_via_inset,
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

        channel_height = min(self.write_width, self.read_width) - 2.0 * self.channel_margin
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
            "top_gate": ("WWL", "WWL"),
            "bottom_gate": ("RWL", "RWL"),
            "left_contact": ("WBL", "WBL"),
            "right_contact": ("RBL", "RBL"),
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
        bottom_edge_y = self.origin_y
        left_edge_x = self.origin_x
        top_edge_y = self.origin_y + self.rows * self.pixel_size
        right_edge_x = self.origin_x + self.cols * self.pixel_size
        half_pad = self.array_pad_size / 2.0
        upper_left_pad_x = left_edge_x - self.gate_pad_offset - half_pad + self.array_pad_overlap
        lower_right_pad_x = right_edge_x + self.gate_pad_offset + half_pad - self.array_pad_overlap
        bottom_contact_pad_y = bottom_edge_y - self.contact_pad_offset - half_pad + self.array_pad_overlap
        top_contact_pad_y = top_edge_y + self.contact_pad_offset + half_pad - self.array_pad_overlap

        specs = [
            (x0, y0 - 3.0, x1, y0 - 3.0, "pixel_size"),
            (x0, y1, x0, pixel["top_rail_y"] + self.gate_line_width / 2.0, "edge_margin"),
            (x0, y0 + 4.0, pixel["left_spine_x"] - self.contact_spine_width / 2.0, y0 + 4.0, "trail_edge_margin"),
            (pixel["left_spine_x"] - self.contact_spine_width / 2.0, y0 + 7.0, pixel["left_spine_x"] + self.contact_spine_width / 2.0, y0 + 7.0, "contact_spine_width"),
            (pixel["write_left_contact_left"], cy, pixel["write_left_contact_right"], cy, "write_left_contact_length"),
            (pixel["write_channel_left"], cy + 3.0, pixel["write_channel_right"], cy + 3.0, "write_length"),
            (pixel["write_channel_cx"], cy - pixel["write_channel_h"] / 2.0, pixel["write_channel_cx"], cy + pixel["write_channel_h"] / 2.0, "write_width"),
            (pixel["write_left_contact_right"], cy - 5.0, pixel["write_channel_left"], cy - 5.0, "write_channel_overlap"),
            (pixel["write_right_contact_left"], cy - 8.0, pixel["write_right_contact_right"], cy - 8.0, "write_right_contact_length"),
            (pixel["write_right_contact_right"], cy + 6.0, pixel["read_channel_left"], cy + 6.0, "fet_gap"),
            (pixel["read_channel_cx"], pixel["read_channel_bottom"], pixel["read_channel_cx"], pixel["read_channel_top"], "read_length"),
            (pixel["read_channel_left"], pixel["read_channel_y"], pixel["read_channel_right"], pixel["read_channel_y"], "read_width"),
            (pixel["read_channel_cx"] + 3.0, pixel["read_channel_top"], pixel["read_channel_cx"] + 3.0, pixel["read_top_contact_top"], "read_contact_length"),
            (pixel["read_channel_cx"] + 6.0, pixel["read_channel_bottom"], pixel["read_channel_cx"] + 6.0, pixel["read_bottom_contact_top"], "read_channel_overlap"),
            (pixel["read_channel_cx"] - 3.0, pixel["bottom_rail_y"] + self.gate_line_width / 2.0, pixel["read_channel_cx"] - 3.0, pixel["read_bottom_gate_stub_top"], "rwl_up_extension"),
            (pixel["read_channel_cx"] + 9.0, pixel["read_bottom_contact_bottom"], pixel["read_channel_cx"] + 9.0, pixel["read_bottom_gate_stub_top"], "read_bottom_overlap_height"),
            (pixel["write_left_contact_cx"], cy + self.write_width / 2.0, pixel["write_left_contact_cx"], cy + pixel["write_contact_h"] / 2.0, "write_pad_overhang"),
            (pixel["read_channel_right"], pixel["read_top_contact_y"], pixel["right_spine_x"] + self.contact_spine_width / 2.0, pixel["read_top_contact_y"], "read_pad_overhang"),
            (pixel["write_gate_x"], pixel["write_gate_body_bottom_y"], pixel["write_gate_x"], pixel["write_gate_body_top_y"], "write_gate_height"),
            ((pixel["write_channel_left"] + pixel["write_channel_right"]) / 2.0, pixel["cy"] + 8.0, pixel["write_gate_x"], pixel["cy"] + 8.0, "write_gate_x_offset"),
            (pixel["write_gate_pad_left"], pixel["coupling_y"], pixel["write_gate_pad_right"], pixel["coupling_y"], "write_gate_pad_size"),
            (pixel["coupling_x"], pixel["coupling_y"] - 3.0, pixel["coupling_x"] + self.coupling_via_size, pixel["coupling_y"] - 3.0, "coupling_via_size"),
            (pixel["write_channel_right"], pixel["coupling_y"] + 3.0, pixel["coupling_x"] - self.coupling_via_size / 2.0, pixel["coupling_y"] + 3.0, "write_coupling_via_inset"),
            (pixel["read_gate_left"], pixel["read_gate_y"], pixel["read_gate_right"], pixel["read_gate_y"], "read_gate_span"),
            (pixel["read_gate_left"], pixel["read_gate_bottom"], pixel["read_gate_left"], pixel["read_gate_top"], "read_gate_bridge_width"),
            (left_edge_x, pixel["top_rail_y"], upper_left_pad_x, pixel["top_rail_y"], "gate_pad_offset"),
            (right_edge_x, pixel["bottom_rail_y"], lower_right_pad_x, pixel["bottom_rail_y"], "gate_pad_offset"),
            (pixel["left_spine_x"], bottom_edge_y, pixel["left_spine_x"], bottom_contact_pad_y, "contact_pad_offset"),
            (pixel["right_spine_x"], top_edge_y, pixel["right_spine_x"], top_contact_pad_y, "contact_pad_offset"),
        ]
        return [self._build_ruler(rid, *spec) for rid, spec in enumerate(specs)]

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

    def _pixel_geometry_write_read(self, row: int, col: int) -> Dict[str, float]:
        x0, y0 = self._pixel_origin(row, col)
        x1 = x0 + self.pixel_size
        y1 = y0 + self.pixel_size
        cy = (y0 + y1) / 2.0

        top_rail_y = y1 - self.edge_margin - self.gate_line_width / 2.0   # WWL
        bottom_rail_y = y0 + self.edge_margin + self.gate_line_width / 2.0  # RWL
        left_spine_x = x0 + self.trail_edge_margin + self.contact_spine_width / 2.0   # WBL
        right_spine_x = x1 - self.trail_edge_margin - self.contact_spine_width / 2.0  # RBL

        write_contact_h = self.write_width + 2.0 * self.write_pad_overhang
        read_contact_w = self.read_width + 2.0 * self.read_pad_overhang
        write_gate_h = self.write_width + 2.0 * self.gate_width_overhang
        read_gate_h = self.gate_line_width + 2.0 * self.gate_length_overhang

        write_left_contact_left = left_spine_x - self.contact_spine_width / 2.0
        write_left_contact_right = write_left_contact_left + self.write_left_contact_length
        write_channel_left = write_left_contact_right - self.write_channel_overlap
        write_channel_right = write_channel_left + self.write_length + 2.0 * self.write_channel_overlap
        write_right_contact_left = write_channel_right - self.write_channel_overlap
        write_right_contact_right = write_right_contact_left + self.write_right_contact_length

        read_channel_left = write_right_contact_right + self.fet_gap
        read_channel_right = read_channel_left + self.read_width
        read_channel_cx = (read_channel_left + read_channel_right) / 2.0
        read_channel_bottom = cy - self.read_length / 2.0 - self.read_channel_overlap
        read_channel_top = cy + self.read_length / 2.0 + self.read_channel_overlap

        if read_channel_right + self.contact_spine_width / 2.0 > right_spine_x:
            raise ValueError("pixel_size is too small for the requested orthogonal Write-Read layout")

        read_top_contact_bottom = read_channel_top - self.read_channel_overlap
        read_top_contact_top = read_top_contact_bottom + self.read_contact_length
        read_bottom_contact_top = read_channel_bottom + self.read_channel_overlap
        bottom_rail_top = bottom_rail_y + self.gate_line_width / 2.0
        read_bottom_gate_stub_bottom = bottom_rail_y - self.gate_line_width / 2.0
        read_bottom_gate_stub_top = bottom_rail_top + self.rwl_up_extension
        read_bottom_contact_bottom = read_bottom_gate_stub_top - self.read_bottom_overlap_height
        if read_bottom_contact_bottom >= read_bottom_contact_top:
            raise ValueError("read_bottom_overlap_height is too large for the requested read FET geometry")

        read_gate_y = cy
        if not (read_channel_bottom < read_gate_y < read_channel_top):
            read_gate_y = (read_channel_bottom + read_channel_top) / 2.0

        write_gate_x = (write_channel_left + write_channel_right) / 2.0 + self.write_gate_x_offset
        write_gate_min_x = write_channel_left - self.gate_length_overhang
        write_gate_max_x = write_channel_right + self.gate_length_overhang
        if not (write_gate_min_x <= write_gate_x <= write_gate_max_x):
            raise ValueError("write_gate_x_offset moves the write gate outside its allowed channel window")
        write_gate_body_bottom_y = cy - write_gate_h / 2.0
        write_gate_body_top_y = cy + write_gate_h / 2.0
        read_gate_left = read_channel_left - self.gate_width_overhang
        read_gate_right = read_channel_right + self.gate_width_overhang
        read_gate_bottom = read_gate_y - read_gate_h / 2.0
        read_gate_top = read_gate_y + read_gate_h / 2.0
        write_gate_pad_left = write_right_contact_left
        write_gate_pad_right = write_right_contact_right
        write_gate_pad_bottom = cy - write_contact_h / 2.0
        write_gate_pad_top = cy + write_contact_h / 2.0
        write_coupling_safe_left = max(write_channel_right, write_gate_pad_left)
        write_coupling_safe_right = write_gate_pad_right
        write_coupling_via_left = min(
            write_coupling_safe_right - self.coupling_via_size,
            max(write_coupling_safe_left, write_coupling_safe_right - self.write_coupling_via_inset - self.coupling_via_size),
        )
        if write_coupling_via_left < write_coupling_safe_left:
            write_coupling_via_left = write_coupling_safe_left
        write_coupling_via_right = write_coupling_via_left + self.coupling_via_size
        if write_coupling_via_right > write_coupling_safe_right:
            raise ValueError("write_coupling_via_inset leaves no non-channel overlap area under the write-right contact")
        write_coupling_via_x = (write_coupling_via_left + write_coupling_via_right) / 2.0
        write_coupling_via_y = cy
        read_gate_bridge_left = write_coupling_via_x + self.coupling_via_size / 2.0
        read_gate_bridge_right = read_gate_left
        if read_gate_bridge_right <= read_gate_bridge_left:
            raise ValueError("write/read geometry leaves no horizontal span for the write-to-read gate bridge")

        overlap_bottom = max(read_bottom_contact_bottom, read_bottom_gate_stub_bottom)
        overlap_top = min(read_bottom_contact_top, read_bottom_gate_stub_top)
        if overlap_top - overlap_bottom < self.coupling_via_size:
            raise ValueError("RWL upward extension and read-bottom overlap do not leave enough via overlap area")
        read_bottom_via_y = (overlap_bottom + overlap_top) / 2.0

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
            "write_left_contact_left": write_left_contact_left,
            "write_left_contact_right": write_left_contact_right,
            "write_right_contact_left": write_right_contact_left,
            "write_right_contact_right": write_right_contact_right,
            "write_left_contact_cx": (write_left_contact_left + write_left_contact_right) / 2.0,
            "write_right_contact_cx": (write_right_contact_left + write_right_contact_right) / 2.0,
            "write_contact_h": write_contact_h,
            "read_contact_w": read_contact_w,
            "write_channel_left": write_channel_left,
            "write_channel_right": write_channel_right,
            "write_channel_cx": (write_channel_left + write_channel_right) / 2.0,
            "write_channel_w": write_channel_right - write_channel_left,
            "write_channel_h": self.write_width,
            "read_channel_left": read_channel_left,
            "read_channel_right": read_channel_right,
            "read_channel_cx": read_channel_cx,
            "read_channel_w": self.read_width,
            "read_channel_bottom": read_channel_bottom,
            "read_channel_top": read_channel_top,
            "read_channel_y": (read_channel_bottom + read_channel_top) / 2.0,
            "read_channel_h": read_channel_top - read_channel_bottom,
            "read_top_contact_y": (read_top_contact_bottom + read_top_contact_top) / 2.0,
            "read_top_contact_bottom": read_top_contact_bottom,
            "read_top_contact_top": read_top_contact_top,
            "read_bottom_contact_y": (read_bottom_contact_bottom + read_bottom_contact_top) / 2.0,
            "read_bottom_contact_bottom": read_bottom_contact_bottom,
            "read_bottom_contact_top": read_bottom_contact_top,
            "write_gate_x": write_gate_x,
            "write_gate_body_bottom_y": write_gate_body_bottom_y,
            "write_gate_body_top_y": write_gate_body_top_y,
            "write_gate_pad_left": write_gate_pad_left,
            "write_gate_pad_right": write_gate_pad_right,
            "write_gate_pad_bottom": write_gate_pad_bottom,
            "write_gate_pad_top": write_gate_pad_top,
            "coupling_x": write_coupling_via_x,
            "coupling_y": write_coupling_via_y,
            "read_gate_bridge_left": read_gate_bridge_left,
            "read_gate_bridge_right": read_gate_bridge_right,
            "read_gate_y": read_gate_y,
            "read_gate_left": read_gate_left,
            "read_gate_right": read_gate_right,
            "read_gate_bottom": read_gate_bottom,
            "read_gate_top": read_gate_top,
            "read_bottom_via_y": read_bottom_via_y,
            "read_bottom_gate_stub_bottom": read_bottom_gate_stub_bottom,
            "read_bottom_gate_stub_top": read_bottom_gate_stub_top,
        }

    def _pixel_geometry(self, row: int, col: int) -> Dict[str, float]:
        return self._pixel_geometry_write_read(row, col)

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
        contact_region = db.Region()
        # Write transistor: horizontal, with WBL on the left and a coupling contact on the right.
        contact_region += self._region_from_box(
            pixel["write_left_contact_cx"],
            pixel["cy"],
            pixel["write_left_contact_right"] - pixel["write_left_contact_left"],
            pixel["write_contact_h"],
        )
        contact_region += self._region_from_box(
            pixel["write_right_contact_cx"],
            pixel["cy"],
            pixel["write_right_contact_right"] - pixel["write_right_contact_left"],
            pixel["write_contact_h"],
        )
        # Read transistor: vertical, with RBL on top-right and RWL on bottom.
        top_contact_left = pixel["read_channel_left"] - self.read_pad_overhang
        top_contact_right = pixel["right_spine_x"] + self.contact_spine_width / 2.0
        contact_region += self._region_from_box(
            (top_contact_left + top_contact_right) / 2.0,
            pixel["read_top_contact_y"],
            top_contact_right - top_contact_left,
            pixel["read_top_contact_top"] - pixel["read_top_contact_bottom"],
        )
        contact_region += self._region_from_box(
            pixel["read_channel_cx"],
            pixel["read_bottom_contact_y"],
            pixel["read_contact_w"],
            pixel["read_bottom_contact_top"] - pixel["read_bottom_contact_bottom"],
        )
        cell.shapes(self.layers["contact"]).insert(contact_region.merged())

    def _draw_upper_gate_shape(self, cell: db.Cell, pixel: Dict[str, float]) -> None:
        gate_region = db.Region()
        # WWL to write gate.
        gate_region += self._region_from_box(
            pixel["write_gate_x"],
            (pixel["write_gate_body_bottom_y"] + pixel["write_gate_body_top_y"]) / 2.0,
            self.gate_line_width,
            pixel["write_gate_body_top_y"] - pixel["write_gate_body_bottom_y"],
        )
        gate_region += self._region_from_box(
            pixel["write_gate_x"],
            (pixel["write_gate_body_top_y"] + pixel["top_rail_y"] + self.gate_line_width / 2.0) / 2.0,
            self.gate_line_width,
            pixel["top_rail_y"] + self.gate_line_width / 2.0 - pixel["write_gate_body_top_y"],
        )
        # Coupling pad under the write-right contact, matching the contact size.
        gate_region += self._region_from_box(
            (pixel["write_gate_pad_left"] + pixel["write_gate_pad_right"]) / 2.0,
            (pixel["write_gate_pad_bottom"] + pixel["write_gate_pad_top"]) / 2.0,
            pixel["write_gate_pad_right"] - pixel["write_gate_pad_left"],
            pixel["write_gate_pad_top"] - pixel["write_gate_pad_bottom"],
        )
        # Read gate body stays separate from the WWL-controlled write gate.
        gate_region += self._region_from_box(
            (pixel["read_gate_left"] + pixel["read_gate_right"]) / 2.0,
            pixel["read_gate_y"],
            pixel["read_gate_right"] - pixel["read_gate_left"],
            pixel["read_gate_top"] - pixel["read_gate_bottom"],
        )
        # Coupling bridge from the write-right contact via node into the read gate.
        gate_region += self._region_from_box(
            (pixel["read_gate_bridge_left"] + pixel["read_gate_bridge_right"]) / 2.0,
            pixel["coupling_y"],
            pixel["read_gate_bridge_right"] - pixel["read_gate_bridge_left"],
            self.read_gate_bridge_width,
        )
        # RWL rail and the bottom-contact gate stub are on bottom_gate and connect only through their own via.
        gate_region += self._region_from_box(
            pixel["read_channel_cx"],
            (pixel["read_bottom_gate_stub_bottom"] + pixel["read_bottom_gate_stub_top"]) / 2.0,
            self.coupling_gate_pad_size,
            pixel["read_bottom_gate_stub_top"] - pixel["read_bottom_gate_stub_bottom"],
        )
        cell.shapes(self.layers["bottom_gate"]).insert(gate_region.merged())
        diel_region = db.Region()
        diel_region += db.Region(
            GeometryUtils.create_rectangle(
                pixel["coupling_x"],
                pixel["coupling_y"],
                self.coupling_via_size,
                self.coupling_via_size,
                center=True,
            )
        )
        diel_region += db.Region(
            GeometryUtils.create_rectangle(
                pixel["read_channel_cx"],
                pixel["read_bottom_via_y"],
                self.coupling_via_size,
                self.coupling_via_size,
                center=True,
            )
        )
        cell.shapes(self.layers["bottom_dielectric"]).insert(diel_region.merged())

    def _draw_lower_gate_shape(self, cell: db.Cell, pixel: Dict[str, float]) -> None:
        return

    def _draw_channel_shape(self, cell: db.Cell, pixel: Dict[str, float]) -> None:
        if not self.draw_channel:
            return

        channel_region = db.Region()
        channel_region += self._region_from_box(
            pixel["write_channel_cx"],
            pixel["cy"],
            pixel["write_channel_w"],
            pixel["write_channel_h"],
        )
        channel_region += self._region_from_box(
            pixel["read_channel_cx"],
            pixel["read_channel_y"],
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
                pixel["read_channel_y"],
                pixel["read_channel_w"] + 2.0 * self.contact_overlap_margin,
                pixel["read_channel_h"] + 2.0 * self.contact_overlap_margin,
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

            # WWL: fan out to the left on bottom_gate.
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

            # RWL: fan out to the right on bottom_gate.
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

        # WBL/RBL columns fan out vertically, aligned with the original left/right trail x positions.
        top_contact_pad_y = top_edge_y + self.contact_pad_offset + half_pad - self.array_pad_overlap
        bottom_contact_pad_y = bottom_edge_y - self.contact_pad_offset - half_pad + self.array_pad_overlap

        for col in range(self.cols):
            col_pixel = self._pixel_geometry(0, col)
            # WBL: left column bus fans out downward.
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

            # RBL: right column bus fans out upward.
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

    def get_array_size(self) -> Tuple[float, float]:
        return self.cols * self.pixel_size, self.rows * self.pixel_size

    def write_gds(
        self,
        filename: str | None = None,
        cell_name: str | None = None,
    ) -> str:
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
            fet_gap=4.0,
            shared_contact_height=10.0,
            # Minimum allowed outer-contact length after centering the full two-device assembly.
            outer_contact_min_length=4.0,

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

        write_read_kwargs = dict(
            # Write/Read unit geometry based on the S-to-G cascade sketch:
            # - write device source couples into the read device gate side
            # - four external ports are WWL / WBL / RBL / RWL
            # length = spacing between the two contact edges of one transistor
            # width  = channel material width of that transistor
            write_width=30.0,
            read_width=13.0,
            write_length=5.0,
            read_length=13.5,
            write_channel_overlap=2.0,
            read_channel_overlap=5.0,

            # Contact pad overhang beyond the channel width for write/read devices.
            write_pad_overhang=2.0,
            read_pad_overhang=1.0,
            write_left_contact_length=10.0,
            write_right_contact_length=6.0,
            read_contact_length=10.0,
            coupling_gate_pad_size=15.0,
            coupling_via_size=2.0,
            read_gate_bridge_width=12.0,
            write_gate_x_offset=-1.5,
            rwl_up_extension=6.0,
            read_bottom_overlap_height=10.0,
            write_coupling_via_inset=1.0,
        )

        component = WriteReadArray(**common_kwargs, **write_read_kwargs)
        output_path = component.write_gds(filename="WRITE_READ_ARRAY_TEST.gds", cell_name="Write_Read_Array")
        lys_path = component.write_rule_session(
            gds_filename="WRITE_READ_ARRAY_TEST.gds",
            lys_filename="WRITE_READ_ARRAY_TEST_rules.lys",
            cell_name="Write_Read_Array",
        )
        width, height = component.get_array_size()
        print(f"Write-Read array written to: {output_path}")
        print(f"Rule session written to: {lys_path}")
        print(f"Array size: {width:.1f} um x {height:.1f} um")
        print(f"Device stack base: {component.stack_base}, channel_type: {component.channel_type}")
    except Exception as exc:
        print(f"WriteReadArray failed: {exc}")
        raise


if __name__ == "__main__":
    main()
