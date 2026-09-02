# -*- coding: utf-8 -*-
"""PDK-layered N-by-M shared-line crossbar matrix."""

import klayout.db as db

try:
    import pya
except ImportError:
    pya = db

from config import DEFAULT_DBU, LAYER_DEFINITIONS, PROCESS_CONFIG


class CrossBar:
    """Build N top-gate columns crossing M back-gate rows.

    ``x_num`` vertical column lines and ``y_num`` horizontal row lines create
    ``x_num * y_num`` devices, addressed through only ``x_num + y_num`` pads.
    Each crossing receives bottom- and top-dielectric enclosure geometry.
    """

    def __init__(self, layout=None, **kwargs):
        self.layout = layout or pya.Layout()
        if self.layout.dbu <= 0:
            self.layout.dbu = DEFAULT_DBU

        self.x_num = int(kwargs.get("x_num", 16))
        self.y_num = int(kwargs.get("y_num", 16))
        self.x_pitch = float(kwargs.get("x_pitch", 30.0))
        self.y_pitch = float(kwargs.get("y_pitch", 30.0))
        self.array_mode = str(kwargs.get("array_mode", "gradient")).lower()
        self.horizontal_bar_width = float(kwargs.get("horizontal_bar_width", 1.0))
        self.vertical_bar_width = float(kwargs.get("vertical_bar_width", 1.0))
        self.horizontal_bar_width_end = float(
            kwargs.get("horizontal_bar_width_end", 5.0)
        )
        self.vertical_bar_width_end = float(
            kwargs.get("vertical_bar_width_end", 5.0)
        )
        self.bottom_dielectric_extension_x = float(kwargs.get("bottom_dielectric_extension_x", 2.0))
        self.bottom_dielectric_extension_y = float(kwargs.get("bottom_dielectric_extension_y", 2.0))
        self.top_dielectric_extension_x = float(kwargs.get("top_dielectric_extension_x", 2.0))
        self.top_dielectric_extension_y = float(kwargs.get("top_dielectric_extension_y", 2.0))
        self.bar_end_extension = float(kwargs.get("bar_end_extension", 2.0))

        # Array breakout style shared with SenseLatchArray / WriteReadArray.
        self.draw_array_pads = bool(kwargs.get("draw_array_pads", True))
        self.array_pad_size = float(kwargs.get("array_pad_size", kwargs.get("electrode_pad_width", 20.0)))
        self.array_pad_overlap = float(kwargs.get("array_pad_overlap", 4.0))
        legacy_offset = float(kwargs.get("fanout_length", 18.0))
        self.row_pad_offset = float(kwargs.get("row_pad_offset", legacy_offset))
        self.column_pad_offset = float(kwargs.get("column_pad_offset", legacy_offset))
        self.pad_connection_style = str(kwargs.get("pad_connection_style", "line")).lower()
        self.horizontal_pad_side = str(kwargs.get("horizontal_pad_side", "left")).lower()
        self.vertical_pad_side = str(kwargs.get("vertical_pad_side", "top")).lower()

        # Array annotations and marks in the blank intervals of the grid.
        self.note_text_enabled = bool(kwargs.get("note_text_enabled", True))
        self.show_pixel_outline = bool(kwargs.get("show_pixel_outline", False))
        self.pixel_outline_layer = int(kwargs.get("pixel_outline_layer", LAYER_DEFINITIONS["note"]["id"]))
        self.show_center_mark = bool(kwargs.get("show_center_mark", True))
        self.center_mark_type = str(kwargs.get("center_mark_type", "cross")).lower()
        self.center_mark_size = float(kwargs.get("center_mark_size", 10.0))
        self.center_mark_width = float(kwargs.get("center_mark_width", 1.0))
        self.center_mark_offset_x = float(kwargs.get("center_mark_offset_x", 0.0))
        self.center_mark_offset_y = float(kwargs.get("center_mark_offset_y", 0.0))
        self.mark_interval_skip = int(kwargs.get("mark_interval_skip", 0))
        self.center_mark_layer = int(kwargs.get("center_mark_layer", LAYER_DEFINITIONS["alignment_marks"]["id"]))
        self._layer_ids = {
            "bottom_gate": LAYER_DEFINITIONS["bottom_gate"]["id"],
            "bottom_dielectric": LAYER_DEFINITIONS["bottom_dielectric"]["id"],
            "top_dielectric": LAYER_DEFINITIONS["top_dielectric"]["id"],
            "top_gate": LAYER_DEFINITIONS["top_gate"]["id"],
            "pad": LAYER_DEFINITIONS["pads"]["id"],
            "note": self.pixel_outline_layer,
            "alignment_marks": self.center_mark_layer,
        }
        self._validate()

    @staticmethod
    def _linear_values(start, end, count):
        if count == 1:
            return [float(start)]
        return [start + (end - start) * i / (count - 1) for i in range(count)]

    def horizontal_widths(self):
        if self.array_mode == "equal":
            return [self.horizontal_bar_width] * self.y_num
        return self._linear_values(self.horizontal_bar_width, self.horizontal_bar_width_end, self.y_num)

    def vertical_widths(self):
        if self.array_mode == "equal":
            return [self.vertical_bar_width] * self.x_num
        return self._linear_values(self.vertical_bar_width, self.vertical_bar_width_end, self.x_num)

    @staticmethod
    def _minimum_edge_spacing(widths, pitch):
        if len(widths) < 2:
            return float("inf")
        return min(pitch - (a + b) / 2.0 for a, b in zip(widths, widths[1:]))

    def _validate(self):
        if self.x_num < 1 or self.y_num < 1:
            raise ValueError("x_num and y_num must be at least 1")
        if self.array_mode not in ("equal", "gradient"):
            raise ValueError("array_mode must be 'equal' or 'gradient'")
        positive = {
            "x_pitch": self.x_pitch,
            "y_pitch": self.y_pitch,
            "horizontal_bar_width": self.horizontal_bar_width,
            "vertical_bar_width": self.vertical_bar_width,
            "horizontal_bar_width_end": self.horizontal_bar_width_end,
            "vertical_bar_width_end": self.vertical_bar_width_end,
            "array_pad_size": self.array_pad_size,
            "center_mark_size": self.center_mark_size,
            "center_mark_width": self.center_mark_width,
        }
        for name, value in positive.items():
            if value < PROCESS_CONFIG["min_feature_size"]:
                raise ValueError(f"{name} must be at least the PDK minimum feature size")
        if min(
            self.bar_end_extension,
            self.array_pad_overlap,
            self.row_pad_offset,
            self.column_pad_offset,
        ) < 0:
            raise ValueError("bar/pad extensions, overlap, and offsets must be non-negative")
        if self.pad_connection_style not in ("line", "block"):
            raise ValueError("pad_connection_style must be 'line' or 'block'")
        if self.horizontal_pad_side not in ("left", "right"):
            raise ValueError("horizontal_pad_side must be 'left' or 'right'")
        if self.vertical_pad_side not in ("top", "bottom"):
            raise ValueError("vertical_pad_side must be 'top' or 'bottom'")
        if self.center_mark_type not in ("cross", "box", "diamond", "circle", "triangle", "l_shape", "t_shape"):
            raise ValueError("unsupported center_mark_type")
        if self.center_mark_width > self.center_mark_size:
            raise ValueError("center_mark_width must not exceed center_mark_size")
        if self.mark_interval_skip < 0:
            raise ValueError("mark_interval_skip must be non-negative")
        for name in (
            "bottom_dielectric_extension_x", "bottom_dielectric_extension_y",
            "top_dielectric_extension_x", "top_dielectric_extension_y",
        ):
            if getattr(self, name) < PROCESS_CONFIG["min_overlap"]:
                raise ValueError(f"{name} must be at least the PDK minimum overlap")

        min_spacing = PROCESS_CONFIG["min_spacing"]
        if self._minimum_edge_spacing(self.vertical_widths(), self.x_pitch) < min_spacing:
            raise ValueError("x_pitch is too small for the selected vertical bar widths")
        if self._minimum_edge_spacing(self.horizontal_widths(), self.y_pitch) < min_spacing:
            raise ValueError("y_pitch is too small for the selected horizontal bar widths")
        if self.draw_array_pads and self.x_num > 1 and self.array_pad_size + min_spacing > self.x_pitch:
            raise ValueError("array_pad_size is too large for x_pitch")
        if self.draw_array_pads and self.y_num > 1 and self.array_pad_size + min_spacing > self.y_pitch:
            raise ValueError("array_pad_size is too large for y_pitch")
        if self.show_center_mark and self.x_num > 1 and self.y_num > 1:
            diel_x = max(self.bottom_dielectric_extension_x, self.top_dielectric_extension_x)
            diel_y = max(self.bottom_dielectric_extension_y, self.top_dielectric_extension_y)
            free_x = self.x_pitch - max(self.vertical_widths()) - 2.0 * diel_x
            free_y = self.y_pitch - max(self.horizontal_widths()) - 2.0 * diel_y
            if self.center_mark_size + 2.0 * abs(self.center_mark_offset_x) > free_x:
                raise ValueError("center mark does not fit inside the X grid interval")
            if self.center_mark_size + 2.0 * abs(self.center_mark_offset_y) > free_y:
                raise ValueError("center mark does not fit inside the Y grid interval")

    def get_layer_ids(self):
        return dict(self._layer_ids)

    def _layer(self, key):
        return self.layout.layer(self._layer_ids[key], 0)

    def _to_dbu(self, value):
        return int(round(float(value) / self.layout.dbu))

    def _box(self, left, bottom, right, top):
        return pya.Box(self._to_dbu(left), self._to_dbu(bottom), self._to_dbu(right), self._to_dbu(top))

    def _polygon(self, points):
        return pya.Polygon([pya.Point(self._to_dbu(x), self._to_dbu(y)) for x, y in points])

    @staticmethod
    def _centers(count, pitch, origin):
        first = origin - (count - 1) * pitch / 2.0
        return [first + i * pitch for i in range(count)]

    @staticmethod
    def crossing_bounds(cx, cy, horizontal_width, vertical_width):
        return (
            cx - vertical_width / 2.0, cy - horizontal_width / 2.0,
            cx + vertical_width / 2.0, cy + horizontal_width / 2.0,
        )

    def _insert_dielectric(self, cell, layer_key, bounds, extension_x, extension_y):
        left, bottom, right, top = bounds
        cell.shapes(self._layer(layer_key)).insert(self._box(
            left - extension_x, bottom - extension_y,
            right + extension_x, top + extension_y,
        ))

    def _insert_center_box(self, cell, layer_key, cx, cy, width, height):
        cell.shapes(self._layer(layer_key)).insert(self._box(
            cx - width / 2.0, cy - height / 2.0,
            cx + width / 2.0, cy + height / 2.0,
        ))

    def _draw_pad_connection(self, cell, layer_key, x0, y0, x1, y1, line_width):
        """Match the line/block breakout convention used by the other arrays."""
        if self.pad_connection_style == "block":
            self._insert_center_box(
                cell, layer_key, (x0 + x1) / 2.0, (y0 + y1) / 2.0,
                abs(x1 - x0) + self.array_pad_size,
                abs(y1 - y0) + self.array_pad_size,
            )
        elif abs(y1 - y0) < 1e-9:
            self._insert_center_box(
                cell, layer_key, (x0 + x1) / 2.0, y0,
                abs(x1 - x0) + self.array_pad_size, line_width,
            )
        else:
            self._insert_center_box(
                cell, layer_key, x0, (y0 + y1) / 2.0,
                line_width, abs(y1 - y0) + self.array_pad_size,
            )

    def _insert_note_text(self, cell, text, x, y):
        if not self.note_text_enabled:
            return
        cell.shapes(self._layer("note")).insert(
            pya.Text(str(text), self._to_dbu(x), self._to_dbu(y))
        )

    def _insert_gap_mark(self, cell, cx, cy):
        size = self.center_mark_size
        width = self.center_mark_width
        layer = self._layer("alignment_marks")
        if self.center_mark_type == "cross":
            self._insert_center_box(cell, "alignment_marks", cx, cy, size, width)
            self._insert_center_box(cell, "alignment_marks", cx, cy, width, size)
        elif self.center_mark_type == "box":
            self._insert_center_box(cell, "alignment_marks", cx, cy + (size - width) / 2.0, size, width)
            self._insert_center_box(cell, "alignment_marks", cx, cy - (size - width) / 2.0, size, width)
            self._insert_center_box(cell, "alignment_marks", cx + (size - width) / 2.0, cy, width, size)
            self._insert_center_box(cell, "alignment_marks", cx - (size - width) / 2.0, cy, width, size)
        elif self.center_mark_type == "diamond":
            cell.shapes(layer).insert(self._polygon([
                (cx, cy + size / 2.0), (cx + size / 2.0, cy),
                (cx, cy - size / 2.0), (cx - size / 2.0, cy),
            ]))
        elif self.center_mark_type == "triangle":
            cell.shapes(layer).insert(self._polygon([
                (cx, cy + size / 2.0), (cx + size / 2.0, cy - size / 2.0),
                (cx - size / 2.0, cy - size / 2.0),
            ]))
        elif self.center_mark_type == "circle":
            import math
            cell.shapes(layer).insert(self._polygon([
                (cx + size / 2.0 * math.cos(2.0 * math.pi * i / 32),
                 cy + size / 2.0 * math.sin(2.0 * math.pi * i / 32))
                for i in range(32)
            ]))
        elif self.center_mark_type == "l_shape":
            self._insert_center_box(cell, "alignment_marks", cx - (size - width) / 2.0, cy, width, size)
            self._insert_center_box(cell, "alignment_marks", cx, cy - (size - width) / 2.0, size, width)
        else:  # t_shape
            self._insert_center_box(cell, "alignment_marks", cx, cy + (size - width) / 2.0, size, width)
            self._insert_center_box(cell, "alignment_marks", cx, cy, width, size)

    def _draw_grid_gap_marks(self, cell, xs, ys):
        """Place one mark in every blank interval between four crossings."""
        if not self.show_center_mark or len(xs) < 2 or len(ys) < 2:
            return
        gap_xs = [
            (left + right) / 2.0 + self.center_mark_offset_x
            for left, right in zip(xs, xs[1:])
        ]
        gap_ys = [
            (bottom + top) / 2.0 + self.center_mark_offset_y
            for bottom, top in zip(ys, ys[1:])
        ]
        step = self.mark_interval_skip + 1
        for cy in gap_ys[::step]:
            for cx in gap_xs[::step]:
                self._insert_gap_mark(cell, cx, cy)

    def create_array_cell(self, cell_name="CrossBar_Array", x=0.0, y=0.0):
        cell = self.layout.create_cell(cell_name)
        xs = self._centers(self.x_num, self.x_pitch, float(x))
        ys = self._centers(self.y_num, self.y_pitch, float(y))
        horizontal_widths = self.horizontal_widths()
        vertical_widths = self.vertical_widths()
        matrix_left = min(cx - w / 2.0 for cx, w in zip(xs, vertical_widths))
        matrix_right = max(cx + w / 2.0 for cx, w in zip(xs, vertical_widths))
        matrix_bottom = min(cy - w / 2.0 for cy, w in zip(ys, horizontal_widths))
        matrix_top = max(cy + w / 2.0 for cy, w in zip(ys, horizontal_widths))

        # Each of the N*M crossing devices receives both dielectric masks.
        for row, cy in enumerate(ys):
            for col, cx in enumerate(xs):
                bounds = self.crossing_bounds(
                    cx, cy, horizontal_widths[row], vertical_widths[col]
                )
                self._insert_dielectric(
                    cell, "bottom_dielectric", bounds,
                    self.bottom_dielectric_extension_x, self.bottom_dielectric_extension_y,
                )
                self._insert_dielectric(
                    cell, "top_dielectric", bounds,
                    self.top_dielectric_extension_x, self.top_dielectric_extension_y,
                )

        if self.show_pixel_outline:
            for cy in ys:
                for cx in xs:
                    self._insert_center_box(cell, "note", cx, cy, self.x_pitch, self.y_pitch)

        # M shared back-gate row lines, each with one square left breakout pad.
        row_left = matrix_left - self.bar_end_extension
        row_right = matrix_right + self.bar_end_extension
        half_pad = self.array_pad_size / 2.0
        for row, (cy, width) in enumerate(zip(ys, horizontal_widths)):
            layer = self._layer("bottom_gate")
            cell.shapes(layer).insert(self._box(
                row_left, cy - width / 2.0,
                row_right, cy + width / 2.0,
            ))
            if self.draw_array_pads:
                use_right = self.horizontal_pad_side == "right"
                if use_right:
                    row_pad_x = row_right + self.row_pad_offset + half_pad - self.array_pad_overlap
                    connection_x = row_right
                else:
                    row_pad_x = row_left - self.row_pad_offset - half_pad + self.array_pad_overlap
                    connection_x = row_left
                self._insert_center_box(cell, "bottom_gate", row_pad_x, cy, self.array_pad_size, self.array_pad_size)
                self._insert_center_box(cell, "pad", row_pad_x, cy, self.array_pad_size, self.array_pad_size)
                self._draw_pad_connection(cell, "bottom_gate", connection_x, cy, row_pad_x, cy, width)
                self._insert_note_text(cell, f"R[{row}]", row_pad_x, cy)

        # N shared top-gate column lines, each with one square upper breakout pad.
        column_bottom = matrix_bottom - self.bar_end_extension
        column_top = matrix_top + self.bar_end_extension
        for col, (cx, width) in enumerate(zip(xs, vertical_widths)):
            layer = self._layer("top_gate")
            cell.shapes(layer).insert(self._box(
                cx - width / 2.0, column_bottom,
                cx + width / 2.0, column_top,
            ))
            if self.draw_array_pads:
                use_bottom = self.vertical_pad_side == "bottom"
                if use_bottom:
                    column_pad_y = column_bottom - self.column_pad_offset - half_pad + self.array_pad_overlap
                    connection_y = column_bottom
                else:
                    column_pad_y = column_top + self.column_pad_offset + half_pad - self.array_pad_overlap
                    connection_y = column_top
                self._insert_center_box(cell, "top_gate", cx, column_pad_y, self.array_pad_size, self.array_pad_size)
                self._insert_center_box(cell, "pad", cx, column_pad_y, self.array_pad_size, self.array_pad_size)
                self._draw_pad_connection(cell, "top_gate", cx, connection_y, cx, column_pad_y, width)
                self._insert_note_text(cell, f"C[{col}]", cx, column_pad_y)

        self._draw_grid_gap_marks(cell, xs, ys)
        return cell
