# -*- coding: utf-8 -*-
"""
Native KLayout mark-array builders used by the NanoMark GUI.

The writefield-mark path in this module mirrors the structure of
`components/MyLayoutTemplate/mark_writefield_gdsfactory.py` as closely as
possible while avoiding any gdsfactory dependency.
"""

import os
import sys
import math
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import klayout.db as db

try:
    import pya
except ImportError:
    pya = db

from config import DEFAULT_DBU, DEFAULT_UNIT_SCALE
from utils.geometry import GeometryUtils
from utils.mark_utils import MarkUtils
from utils.text_utils import TextUtils


class MarkArrayBuilder:
    _INDEX_EXPR_PATTERN = re.compile(r"\{([ij])(?:\s*([+-])\s*(\d+))?\}")

    def __init__(self, layout=None):
        self.layout = layout or db.Layout()
        self.layout.dbu = DEFAULT_DBU
        GeometryUtils.UNIT_SCALE = DEFAULT_UNIT_SCALE
        TextUtils.set_unit_scale(DEFAULT_UNIT_SCALE)

    def _layer_index(self, layer_spec):
        layer, datatype = layer_spec
        return self.layout.layer(int(layer), int(datatype))

    def _insert_shape(self, cell, layer_spec, shape):
        if shape is None:
            return
        layer_index = self._layer_index(layer_spec)
        if isinstance(shape, pya.Region):
            for polygon in shape.each():
                cell.shapes(layer_index).insert(polygon)
            return
        cell.shapes(layer_index).insert(shape)

    def _insert_shapes(self, cell, layer_spec, shapes):
        if shapes is None:
            return
        if isinstance(shapes, (list, tuple)):
            for shape in shapes:
                self._insert_shape(cell, layer_spec, shape)
            return
        self._insert_shape(cell, layer_spec, shapes)

    def _transform_shape(self, shape, trans):
        if isinstance(shape, pya.Region):
            region = pya.Region(shape)
            region.transform(trans)
            return region
        transformed = getattr(shape, "transformed", None)
        if callable(transformed):
            return transformed(trans)
        copied = getattr(shape, "dup", None)
        if callable(copied):
            dup = copied()
            dup.transform(trans)
            return dup
        return shape

    def _transform_shapes(self, shapes, trans):
        if isinstance(shapes, (list, tuple)):
            return [self._transform_shape(shape, trans) for shape in shapes]
        return self._transform_shape(shapes, trans)

    def _translate_shapes(self, shapes, dx_um, dy_um):
        trans = pya.Trans(int(round(dx_um * DEFAULT_UNIT_SCALE)), int(round(dy_um * DEFAULT_UNIT_SCALE)))
        return self._transform_shapes(shapes, trans)

    def _rotate_shapes(self, shapes, angle_deg, cx_um=0.0, cy_um=0.0):
        rot_map = {0: 0, 90: 1, 180: 2, 270: 3, -90: 3}
        rot = rot_map.get(int(angle_deg), 0)
        cx = int(round(cx_um * DEFAULT_UNIT_SCALE))
        cy = int(round(cy_um * DEFAULT_UNIT_SCALE))
        trans = pya.Trans(0, False, cx, cy) * pya.Trans(rot, False, 0, 0) * pya.Trans(0, False, -cx, -cy)
        return self._transform_shapes(shapes, trans)

    def _outline_rectangles(self, cx, cy, width, height, line_width):
        half_w = width / 2.0
        half_h = height / 2.0
        lw = max(float(line_width), self.layout.dbu)
        shapes = [
            GeometryUtils.create_rectangle(cx, cy + half_h - lw / 2.0, width, lw, center=True),
            GeometryUtils.create_rectangle(cx, cy - half_h + lw / 2.0, width, lw, center=True),
        ]
        inner_height = max(height - 2.0 * lw, 0.0)
        if inner_height > 0.0:
            shapes.extend(
                [
                    GeometryUtils.create_rectangle(cx - half_w + lw / 2.0, cy, lw, inner_height, center=True),
                    GeometryUtils.create_rectangle(cx + half_w - lw / 2.0, cy, lw, inner_height, center=True),
                ]
            )
        return shapes

    def _rect_polygon_with_hole(self, cx, cy, outer_w, outer_h, inner_w, inner_h):
        ox1 = int(round((cx - outer_w / 2.0) * DEFAULT_UNIT_SCALE))
        oy1 = int(round((cy - outer_h / 2.0) * DEFAULT_UNIT_SCALE))
        ox2 = int(round((cx + outer_w / 2.0) * DEFAULT_UNIT_SCALE))
        oy2 = int(round((cy + outer_h / 2.0) * DEFAULT_UNIT_SCALE))
        ix1 = int(round((cx - inner_w / 2.0) * DEFAULT_UNIT_SCALE))
        iy1 = int(round((cy - inner_h / 2.0) * DEFAULT_UNIT_SCALE))
        ix2 = int(round((cx + inner_w / 2.0) * DEFAULT_UNIT_SCALE))
        iy2 = int(round((cy + inner_h / 2.0) * DEFAULT_UNIT_SCALE))
        poly = pya.Polygon(
            [pya.Point(ox1, oy1), pya.Point(ox2, oy1), pya.Point(ox2, oy2), pya.Point(ox1, oy2)]
        )
        poly.insert_hole([pya.Point(ix1, iy1), pya.Point(ix1, iy2), pya.Point(ix2, iy2), pya.Point(ix2, iy1)])
        return poly

    def _simple_cross_shapes(self, x, y, size, width):
        return GeometryUtils.create_cross(x, y, size, width)

    def _bonecross_shapes(self, x, y, size, width):
        total_length = float(size)
        external_width = float(width)
        internal_width = float(width) / 5.0
        internal_length = min(1.5 * float(width), 20.0)
        end_length = (total_length - internal_length) / 2.0
        return [
            GeometryUtils.create_rectangle(x, y, internal_length, internal_width, center=True),
            GeometryUtils.create_rectangle(x - (internal_length + end_length) / 2.0, y, end_length, external_width, center=True),
            GeometryUtils.create_rectangle(x + (internal_length + end_length) / 2.0, y, end_length, external_width, center=True),
            GeometryUtils.create_rectangle(x, y, internal_width, internal_length, center=True),
            GeometryUtils.create_rectangle(x, y - (internal_length + end_length) / 2.0, external_width, end_length, center=True),
            GeometryUtils.create_rectangle(x, y + (internal_length + end_length) / 2.0, external_width, end_length, center=True),
        ]

    def _split_bonecross_shapes(self, x, y, size, width, mode="main"):
        total_length = float(size)
        external_width = float(width)
        internal_width = 2.0 * float(width) / 5.0
        internal_length = min(1.5 * float(width), 20.0)
        end_length = (total_length - internal_length) / 2.0
        shapes = []

        def add_rect(w, h, dx, dy):
            shapes.append(GeometryUtils.create_rectangle(x + dx, y + dy, w, h, center=True))

        if mode == "main":
            add_rect(end_length, external_width, -(internal_length + end_length) / 2.0, 0)
            add_rect(end_length, external_width, (internal_length + end_length) / 2.0, 0)
            add_rect(external_width, end_length, 0, -(internal_length + end_length) / 2.0)
            add_rect(external_width, end_length, 0, (internal_length + end_length) / 2.0)
            add_rect(internal_length / 2.0, internal_width / 2.0, -internal_length / 4.0, internal_width / 4.0)
            add_rect(internal_width / 2.0, internal_length / 2.0, -internal_width / 4.0, internal_length / 4.0)
            add_rect(internal_length / 2.0, internal_width / 2.0, internal_length / 4.0, -internal_width / 4.0)
            add_rect(internal_width / 2.0, internal_length / 2.0, internal_width / 4.0, -internal_length / 4.0)
        else:
            add_rect(internal_length / 2.0, internal_width / 2.0, internal_length / 4.0, internal_width / 4.0)
            add_rect(internal_width / 2.0, internal_length / 2.0, internal_width / 4.0, internal_length / 4.0)
            add_rect(internal_length / 2.0, internal_width / 2.0, -internal_length / 4.0, -internal_width / 4.0)
            add_rect(internal_width / 2.0, internal_length / 2.0, -internal_width / 4.0, -internal_length / 4.0)
        return shapes

    def _corner_marker_shapes(self, x, y, length, width):
        narrow_width = width / 2.0
        tip_length = length / 3.0
        root_length = length - tip_length
        shapes = []

        def add_rect_corners(x1, y1, x2, y2):
            shapes.append(
                GeometryUtils.create_rectangle((x1 + x2) / 2.0, (y1 + y2) / 2.0, abs(x2 - x1), abs(y2 - y1), center=True)
            )

        add_rect_corners(x, y, x + narrow_width, y + root_length)
        add_rect_corners(x, y + root_length, x + width, y + length)
        add_rect_corners(x, y, x + root_length, y + narrow_width)
        add_rect_corners(x + root_length, y, x + length, y + width)
        return shapes

    def _mark_shapes(self, x, y, mark_type, mark_size, mark_width):
        mark_type = str(mark_type).lower()
        if mark_type == "bonecross":
            return self._bonecross_shapes(x, y, mark_size, mark_width)
        if mark_type == "chessboard":
            square_size = float(mark_size) * 0.4
            hollow_size = min(float(mark_width), square_size * 0.9)
            return [
                self._rect_polygon_with_hole(x - square_size / 2.0, y + square_size / 2.0, square_size, square_size, hollow_size, hollow_size),
                self._rect_polygon_with_hole(x + square_size / 2.0, y - square_size / 2.0, square_size, square_size, hollow_size, hollow_size),
            ]
        return self._simple_cross_shapes(x, y, mark_size, mark_width)

    def _deplof_text(self, text, x, y, size_um, anchor="left_bottom", justify="left"):
        try:
            return TextUtils.create_text_deplof(str(text), float(x), float(y), float(size_um), anchor=anchor, justify=justify)
        except Exception:
            return [pya.Text(str(text), int(round(x * DEFAULT_UNIT_SCALE)), int(round(y * DEFAULT_UNIT_SCALE)))]

    def _safe_label_text(self, pattern, context, fallback):
        text = str(fallback)
        if pattern is None:
            return text
        try:
            rendered = str(pattern).format(**context).strip()
            if rendered:
                text = rendered
        except Exception:
            pass
        return text

    def _simple_mark_shapes(
        self,
        x,
        y,
        mark_style,
        mark_size,
        mark_width,
        mark_rotation=0,
        polygon_sides=6,
        chamfer_ratio=0.25,
    ):
        style = str(mark_style).lower()

        if style == "bonecross":
            shapes = self._bonecross_shapes(x, y, mark_size, mark_width)
        elif style == "chessboard":
            shapes = self._mark_shapes(x, y, "chessboard", mark_size, mark_width)
        elif style == "square":
            shapes = MarkUtils.square(x, y, mark_size).get_shapes()
        elif style == "circle":
            shapes = MarkUtils.circle(x, y, mark_size).get_shapes()
        elif style == "diamond":
            shapes = MarkUtils.diamond(x, y, mark_size).get_shapes()
        elif style == "triangle":
            shapes = MarkUtils.triangle(x, y, mark_size).get_shapes()
        elif style == "l_shape":
            shapes = MarkUtils.l_shape(x, y, mark_size, ratio=max(mark_width / max(mark_size, self.layout.dbu), 0.01)).get_shapes()
        elif style == "t_shape":
            shapes = MarkUtils.t_shape(x, y, mark_size, ratio=max(mark_width / max(mark_size, self.layout.dbu), 0.01)).get_shapes()
        elif style == "regular_polygon":
            shapes = MarkUtils.regular_polygon(x, y, mark_size, n_sides=max(int(polygon_sides), 3)).get_shapes()
        elif style == "chamfered_octagon":
            shapes = MarkUtils.chamfered_octagon(x, y, mark_size, chamfer_ratio=max(float(chamfer_ratio), 0.01)).get_shapes()
        else:
            shapes = MarkUtils.cross(x, y, mark_size, mark_width).get_shapes()

        if int(mark_rotation) % 360:
            shapes = self._rotate_shapes(shapes, int(mark_rotation), x, y)
        return shapes

    def _guide_grid_shapes(self, center_x, center_y, span_x, span_y, line_width):
        shapes = []
        line_width = max(float(line_width), self.layout.dbu)
        fallback_len = max(line_width * 8.0, self.layout.dbu)
        if span_x > 0.0 and span_y > 0.0:
            shapes.extend(self._outline_rectangles(center_x, center_y, 2.0 * span_x, 2.0 * span_y, line_width))
        if span_x > 0.0:
            shapes.append(GeometryUtils.create_rectangle(center_x - span_x / 2.0, center_y, line_width, 2.0 * span_y if span_y > 0.0 else fallback_len, center=True))
            shapes.append(GeometryUtils.create_rectangle(center_x + span_x / 2.0, center_y, line_width, 2.0 * span_y if span_y > 0.0 else fallback_len, center=True))
        if span_y > 0.0:
            shapes.append(GeometryUtils.create_rectangle(center_x, center_y - span_y / 2.0, 2.0 * span_x if span_x > 0.0 else fallback_len, line_width, center=True))
            shapes.append(GeometryUtils.create_rectangle(center_x, center_y + span_y / 2.0, 2.0 * span_x if span_x > 0.0 else fallback_len, line_width, center=True))
        cross_len = max(min(span_x if span_x > 0.0 else line_width * 8.0, span_y if span_y > 0.0 else line_width * 8.0), line_width * 4.0)
        shapes.extend(self._simple_cross_shapes(center_x, center_y, cross_len, line_width))
        return shapes

    def _evaluate_index_expr(self, axis_name, sign, magnitude, row_index, col_index):
        base_value = int(row_index) + 1 if axis_name == "i" else int(col_index)
        if sign and magnitude:
            offset = int(magnitude)
            if sign == "-":
                base_value -= offset
            else:
                base_value += offset
        return base_value

    def _index_to_letters_zero_based(self, idx):
        idx = int(idx)
        if idx < 0:
            return str(idx)
        return self._index_to_letters(idx)

    def _render_incremental_text(self, text_content, row_index=0, col_index=0, array_mode="2d"):
        text_content = str(text_content or "")
        if not text_content:
            return ""
        mode = str(array_mode).lower()
        axes_used = {match.group(1) for match in self._INDEX_EXPR_PATTERN.finditer(text_content)}
        if mode == "1d" and len(axes_used) > 1:
            raise ValueError("1D text pattern only supports one increment placeholder: use either {i} or {j}.")

        def replace_match(match):
            axis_name, sign, magnitude = match.groups()
            value = self._evaluate_index_expr(axis_name, sign, magnitude, row_index, col_index)
            if axis_name == "i":
                return str(value)
            return self._index_to_letters_zero_based(value)

        return self._INDEX_EXPR_PATTERN.sub(replace_match, text_content)

    def build_text_pattern_array(
        self,
        origin_x=0.0,
        origin_y=0.0,
        array_mode="2d",
        count_1d=5,
        step_1d_x=200.0,
        step_1d_y=0.0,
        row_count=5,
        col_count=5,
        row_vec_x=0.0,
        row_vec_y=200.0,
        col_vec_x=200.0,
        col_vec_y=0.0,
        text_content="WWL{i}{j}",
        text_size=80.0,
        text_anchor="center",
        text_justify="center",
        layer_text=(3, 0),
        name="text_pattern_array",
    ):
        cell = self.layout.create_cell(str(name))

        mode = str(array_mode).lower()
        if mode == "1d":
            total = max(int(count_1d), 1)
            for idx in range(total):
                pos_x = float(origin_x) + idx * float(step_1d_x)
                pos_y = float(origin_y) + idx * float(step_1d_y)
                item_text = self._render_incremental_text(text_content, row_index=idx, col_index=idx, array_mode="1d")
                if not item_text:
                    continue
                self._insert_shapes(
                    cell,
                    layer_text,
                    self._deplof_text(
                        item_text,
                        pos_x,
                        pos_y,
                        text_size,
                        anchor=text_anchor,
                        justify=text_justify,
                    ),
                )
            return self.layout, cell

        n_rows = max(int(row_count), 1)
        n_cols = max(int(col_count), 1)
        for row_idx in range(n_rows):
            for col_idx in range(n_cols):
                pos_x = float(origin_x) + row_idx * float(row_vec_x) + col_idx * float(col_vec_x)
                pos_y = float(origin_y) + row_idx * float(row_vec_y) + col_idx * float(col_vec_y)
                item_text = self._render_incremental_text(text_content, row_index=row_idx, col_index=col_idx, array_mode="2d")
                if not item_text:
                    continue
                self._insert_shapes(
                    cell,
                    layer_text,
                    self._deplof_text(
                        item_text,
                        pos_x,
                        pos_y,
                        text_size,
                        anchor=text_anchor,
                        justify=text_justify,
                    ),
                )

        return self.layout, cell

    def build_custom_global_mark_grid(
        self,
        chip_width=10000.0,
        chip_height=10000.0,
        active_width=8000.0,
        active_height=8000.0,
        center_x=0.0,
        center_y=0.0,
        span_x=2000.0,
        span_y=2000.0,
        enabled_positions=None,
        guide_line_width=5.0,
        mark_style="ebl_composite",
        mark_size=120.0,
        mark_width=10.0,
        mark_rotation=0,
        polygon_sides=6,
        chamfer_ratio=0.25,
        main_reference_slot="tl",
        ebl_main_size=400.0,
        ebl_main_width=10.0,
        ebl_small_size=50.0,
        ebl_small_width=4.0,
        ebl_small_dist=175.0,
        ebl_enable_frame=True,
        ebl_enable_alignment_layers=True,
        enable_coord_text=True,
        coord_text_size=16.0,
        enable_label=True,
        label_pattern="{slot}",
        label_size=24.0,
        label_offset=(80.0, 80.0),
        label_anchor="left_bottom",
        layer_chip=(1, 0),
        layer_active=(2, 0),
        layer_mechanical=(6, 0),
        layer_mark=(3, 0),
        layer_mark_frame=(4, 0),
        layer_auto_align=(61, 0),
        layer_manual_align=(63, 0),
        name="custom_global_mark_grid",
    ):
        cell = self.layout.create_cell(str(name))
        self._insert_shapes(cell, layer_chip, self._outline_rectangles(center_x, center_y, chip_width, chip_height, guide_line_width))
        self._insert_shapes(cell, layer_active, self._outline_rectangles(center_x, center_y, active_width, active_height, guide_line_width))
        self._insert_shapes(cell, layer_mechanical, self._guide_grid_shapes(center_x, center_y, span_x, span_y, guide_line_width))

        slot_defs = [
            ("tl", "NW", 0, 0, -1.0, 1.0),
            ("tc", "N", 0, 1, 0.0, 1.0),
            ("tr", "NE", 0, 2, 1.0, 1.0),
            ("cl", "W", 1, 0, -1.0, 0.0),
            ("cc", "C", 1, 1, 0.0, 0.0),
            ("cr", "E", 1, 2, 1.0, 0.0),
            ("bl", "SW", 2, 0, -1.0, -1.0),
            ("bc", "S", 2, 1, 0.0, -1.0),
            ("br", "SE", 2, 2, 1.0, -1.0),
        ]
        enabled_positions = dict(enabled_positions or {})
        label_dx, label_dy = label_offset
        main_slot = str(main_reference_slot).lower()

        for key, slot_name, row_idx, col_idx, mx, my in slot_defs:
            if not enabled_positions.get(key, False):
                continue

            pos_x = center_x + mx * span_x
            pos_y = center_y + my * span_y
            context = {
                "slot": slot_name,
                "slot_key": key,
                "row": row_idx + 1,
                "col": col_idx + 1,
                "row_index": row_idx,
                "col_index": col_idx,
                "x": pos_x,
                "y": pos_y,
            }

            if str(mark_style).lower() == "ebl_composite":
                mark_shapes, frame_shapes, auto_shapes, manual_shapes, text_shapes = self._composite_mark_shapes(
                    pos_x,
                    pos_y,
                    ebl_main_size,
                    ebl_main_width,
                    ebl_small_size,
                    ebl_small_width,
                    ebl_small_dist,
                    is_main_mark=(key == main_slot),
                    enable_frame=ebl_enable_frame,
                    frame_width=None,
                    quadrant_indicator=None,
                    center_coords=(pos_x, pos_y) if enable_coord_text else None,
                    coord_text_size=coord_text_size if enable_coord_text else None,
                    enable_alignment_layers=ebl_enable_alignment_layers,
                )
                self._insert_shapes(cell, layer_mark, mark_shapes + text_shapes)
                self._insert_shapes(cell, layer_mark_frame, frame_shapes)
                self._insert_shapes(cell, layer_auto_align, auto_shapes)
                self._insert_shapes(cell, layer_manual_align, manual_shapes)
            else:
                self._insert_shapes(
                    cell,
                    layer_mark,
                    self._simple_mark_shapes(
                        pos_x,
                        pos_y,
                        mark_style,
                        mark_size,
                        mark_width,
                        mark_rotation=mark_rotation,
                        polygon_sides=polygon_sides,
                        chamfer_ratio=chamfer_ratio,
                    ),
                )
                if enable_coord_text:
                    self._insert_shapes(
                        cell,
                        layer_mark,
                        self._deplof_text(
                            f"{pos_x:+.1f}",
                            pos_x - max(mark_width * 1.5, 8.0),
                            pos_y + max(mark_width * 1.5, 8.0),
                            coord_text_size,
                            anchor="right_bottom",
                            justify="right",
                        ),
                    )
                    self._insert_shapes(
                        cell,
                        layer_mark,
                        self._deplof_text(
                            f"{pos_y:+.1f}",
                            pos_x + max(mark_width * 1.5, 8.0),
                            pos_y - max(mark_width * 1.5, 8.0),
                            coord_text_size,
                            anchor="left_top",
                            justify="left",
                        ),
                    )

            if enable_label:
                label_text = self._safe_label_text(label_pattern, context, slot_name)
                self._insert_shapes(
                    cell,
                    layer_mark,
                    self._deplof_text(
                        label_text,
                        pos_x + label_dx,
                        pos_y + label_dy,
                        label_size,
                        anchor=label_anchor,
                        justify="left" if "left" in label_anchor else ("right" if "right" in label_anchor else "center"),
                    ),
                )

        return self.layout, cell

    def _composite_mark_shapes(
        self,
        x,
        y,
        main_size,
        main_width,
        small_size,
        small_width,
        small_offset_dist,
        is_main_mark=False,
        enable_frame=False,
        frame_width=None,
        quadrant_indicator=None,
        center_coords=None,
        coord_text_size=None,
        enable_alignment_layers=True,
    ):
        layer_shapes = []
        frame_shapes = []
        auto_shapes = []
        manual_shapes = []
        text_shapes = []

        layer_shapes.extend(self._split_bonecross_shapes(x, y, main_size, main_width, mode="main"))

        for dx in (-1, 1):
            for dy in (-1, 1):
                layer_shapes.extend(self._simple_cross_shapes(x + dx * small_offset_dist, y + dy * small_offset_dist, small_size, small_width))

        if is_main_mark:
            line_offset = small_offset_dist
            max_len = 2.0 * (small_offset_dist - small_size / 2.0 - 2.0)
            line_length = min(main_size, max_len)
            line_width = 2.0
            layer_shapes.extend(
                [
                    GeometryUtils.create_rectangle(x, y + line_offset, line_length, line_width, center=True),
                    GeometryUtils.create_rectangle(x, y - line_offset, line_length, line_width, center=True),
                    GeometryUtils.create_rectangle(x - line_offset, y, line_width, line_length, center=True),
                    GeometryUtils.create_rectangle(x + line_offset, y, line_width, line_length, center=True),
                ]
            )

        if enable_frame:
            frame_shapes.extend(self._split_bonecross_shapes(x, y, main_size, main_width, mode="complement"))

        if quadrant_indicator:
            internal_width = 2.0 * main_width / 5.0
            dist = internal_width
            qx = 1 if quadrant_indicator in (1, 4) else -1
            qy = 1 if quadrant_indicator in (1, 2) else -1
            layer_shapes.append(GeometryUtils.create_circle(x + qx * dist, y + qy * dist, internal_width / 4.0))

        if center_coords is not None:
            cx_val, cy_val = center_coords
            c_text_size = float(coord_text_size) if coord_text_size is not None else (main_size / 25.0)
            offset = main_width * 1.5
            text_shapes.extend(self._deplof_text(f"{cx_val:+.1f}", x - offset, y + offset + main_width / 2.0, c_text_size, anchor="right_bottom", justify="right"))
            text_shapes.extend(self._deplof_text(f"{cy_val:+.1f}", x + offset, y - offset - main_width / 2.0, c_text_size, anchor="left_top", justify="left"))

        if enable_alignment_layers:
            manual_shapes.append(GeometryUtils.create_rectangle(x, y, main_size, main_size, center=True))
            internal_length = min(1.5 * main_width, 20.0)
            end_length = (main_size - internal_length) / 2.0
            wide_part_center_x = -(internal_length + end_length) / 2.0
            wide_part_center_y = (internal_length + end_length) / 2.0
            auto_shapes.extend(
                [
                    GeometryUtils.create_rectangle(x + wide_part_center_x, y, 5.0, 50.0, center=True),
                    GeometryUtils.create_rectangle(x, y + wide_part_center_y, 50.0, 5.0, center=True),
                ]
            )

        return layer_shapes, frame_shapes, auto_shapes, manual_shapes, text_shapes

    def _caliper_shapes(self, cx, cy, num_ticks_side, pitch, width, tick_length, center_tick_length, orientation, tick_direction, limit_length=None):
        shapes = []
        center_len = center_tick_length if center_tick_length is not None else tick_length
        for i in range(-int(num_ticks_side), int(num_ticks_side) + 1):
            pos = i * pitch
            if limit_length is not None and abs(pos) > limit_length / 2.0:
                continue
            current_len = center_len if i == 0 else tick_length
            if orientation == "horizontal":
                shapes.append(GeometryUtils.create_rectangle(cx + pos, cy + tick_direction * current_len / 2.0, width, current_len, center=True))
            else:
                shapes.append(GeometryUtils.create_rectangle(cx + tick_direction * current_len / 2.0, cy + pos, current_len, width, center=True))
        return shapes

    def _index_to_letters(self, idx):
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        idx = int(idx)
        if idx < 26:
            return letters[idx]
        result = ""
        idx += 1
        while idx > 0:
            idx -= 1
            result = letters[idx % 26] + result
            idx //= 26
        return result

    def build_general_mark_array(
        self,
        sample_width=10000.0,
        sample_height=10000.0,
        active_width=8000.0,
        active_height=8000.0,
        mark_width=10.0,
        mark_size=50.0,
        mark_pitch_x=500.0,
        mark_pitch_y=500.0,
        mark_type="cross",
        label_interval=4,
        boundary_line_width=10.0,
        layer_mechanical=(1, 0),
        layer_active=(2, 0),
        layer_mark=(3, 0),
        label_offset=(50.0, 20.0),
        label_size=40.0,
        user_name="GEMsLab UserName",
        info_text_size=50.0,
        info_text_offset=(-100.0, -95.0),
        name="mark_array_sample",
    ):
        cell = self.layout.create_cell(str(name))
        self._insert_shapes(cell, layer_mechanical, self._outline_rectangles(0.0, 0.0, sample_width, sample_height, boundary_line_width))
        self._insert_shapes(cell, layer_active, self._outline_rectangles(0.0, 0.0, active_width, active_height, boundary_line_width))

        nx = max(int(active_width // max(mark_pitch_x, self.layout.dbu)), 1)
        ny = max(int(active_height // max(mark_pitch_y, self.layout.dbu)), 1)
        grid_width = (nx - 1) * mark_pitch_x
        grid_height = (ny - 1) * mark_pitch_y
        start_x = -grid_width / 2.0
        start_y = -grid_height / 2.0
        num_digits = len(str(max((nx - 1) // max(int(label_interval), 1) + 1, 1)))

        for i in range(nx):
            for j in range(ny):
                x = start_x + i * mark_pitch_x
                y = start_y + j * mark_pitch_y
                self._insert_shapes(cell, layer_mark, self._mark_shapes(x, y, mark_type, mark_size, mark_width))
                if i % max(int(label_interval), 1) == 0 and j % max(int(label_interval), 1) == 0:
                    row_label = self._index_to_letters(j // max(int(label_interval), 1))
                    col_label = str(i // max(int(label_interval), 1) + 1).zfill(num_digits)
                    self._insert_shapes(cell, layer_mark, self._deplof_text(f"{row_label}{col_label}", x + label_offset[0], y + label_offset[1], label_size, anchor="left_bottom", justify="left"))

        tl_anchor = (-active_width / 2.0, active_height / 2.0)
        de_um = (sample_width - active_width) / 2.0
        info_lines = [
            f"MP:{int(mark_pitch_x)}x{int(mark_pitch_y)}um, M:{int(mark_size)}um",
            f"AA:{int(active_width)}um, DE:{int(round(de_um))}um",
        ]
        info_x = tl_anchor[0] + mark_size + info_text_offset[0]
        info_y_start = tl_anchor[1] + mark_size / 2.0 + info_text_offset[1]
        for idx, line in enumerate(info_lines):
            self._insert_shapes(
                cell,
                layer_mark,
                self._deplof_text(
                    line,
                    info_x,
                    info_y_start - idx * info_text_size * 1.5,
                    info_text_size,
                    anchor="left_top",
                    justify="left",
                ),
            )
        self._insert_shapes(
            cell,
            layer_mark,
            self._deplof_text(
                user_name,
                info_x,
                info_y_start - len(info_lines) * info_text_size * 1.5,
                info_text_size,
                anchor="left_top",
                justify="left",
            ),
        )
        return self.layout, cell

    def build_writefield_array(
        self,
        sample_width=10000.0,
        sample_height=10000.0,
        active_width=7000.0,
        active_height=7000.0,
        writefield_size=1000.0,
        mark_main_size=80.0,
        mark_main_width=10.0,
        mark_small_size=15.0,
        mark_small_width=2.0,
        mark_small_dist=50.0,
        l_marker_length=100.0,
        l_marker_width=5.0,
        boundary_line_width=10.0,
        mark_offset_from_corner=(100.0, 100.0),
        global_mark_offset=200.0,
        global_mark_main_size=400.0,
        global_mark_main_width=10.0,
        global_mark_small_size=50.0,
        global_mark_small_width=4.0,
        global_mark_small_dist=175.0,
        label_size=15.0,
        label_offset=(-70.0, -75.0),
        enable_caliper=True,
        caliper_width=2.0,
        caliper_top_right_pitch=5.0,
        caliper_top_right_num_side=10,
        caliper_top_right_tick_length=10.0,
        caliper_top_right_center_length=20.0,
        caliper_bottom_left_pitch=5.1,
        caliper_bottom_left_num_side=10,
        caliper_bottom_left_tick_length=10.0,
        caliper_bottom_left_center_length=20.0,
        layer_mechanical=(1, 0),
        layer_active=(2, 0),
        layer_mark=(3, 0),
        layer_mark_frame=(4, 0),
        layer_caliper=(5, 0),
        layer_auto_align=(61, 0),
        layer_manual_align=(63, 0),
        frame_width=None,
        user_name="Xinchuan",
        info_text_size=50.0,
        info_text_offset=(-100.0, -95.0),
        info_text_line_width=0.0,
        enable_alignment_layers=True,
    ):
        del info_text_line_width
        cell = self.layout.create_cell("mark_writefield_array")
        self._insert_shapes(cell, layer_mechanical, self._outline_rectangles(0.0, 0.0, sample_width, sample_height, boundary_line_width))
        self._insert_shapes(cell, layer_active, self._outline_rectangles(0.0, 0.0, active_width, active_height, boundary_line_width))

        nx = int(math.ceil(active_width / writefield_size))
        ny = int(math.ceil(active_height / writefield_size))
        total_grid_width = nx * writefield_size
        total_grid_height = ny * writefield_size
        start_x = -total_grid_width / 2.0
        start_y = -total_grid_height / 2.0

        for i in range(nx):
            for j in range(ny):
                wf_center_x = start_x + i * writefield_size + writefield_size / 2.0
                wf_center_y = start_y + (ny - 1 - j) * writefield_size + writefield_size / 2.0

                pos_bl = (wf_center_x - writefield_size / 2.0 + mark_offset_from_corner[0], wf_center_y - writefield_size / 2.0 + mark_offset_from_corner[1])
                pos_br = (wf_center_x + writefield_size / 2.0 - mark_offset_from_corner[0], wf_center_y - writefield_size / 2.0 + mark_offset_from_corner[1])
                pos_tl = (wf_center_x - writefield_size / 2.0 + mark_offset_from_corner[0], wf_center_y + writefield_size / 2.0 - mark_offset_from_corner[1])
                pos_tr = (wf_center_x + writefield_size / 2.0 - mark_offset_from_corner[0], wf_center_y + writefield_size / 2.0 - mark_offset_from_corner[1])

                q3_shapes, q3_frame, q3_auto, q3_manual, _ = self._composite_mark_shapes(*pos_bl, mark_main_size, mark_main_width, mark_small_size, mark_small_width, mark_small_dist, False, True, frame_width, 3, None, enable_alignment_layers)
                q4_shapes, q4_frame, q4_auto, q4_manual, _ = self._composite_mark_shapes(*pos_br, mark_main_size, mark_main_width, mark_small_size, mark_small_width, mark_small_dist, False, True, frame_width, 4, None, enable_alignment_layers)
                q2_shapes, q2_frame, q2_auto, q2_manual, _ = self._composite_mark_shapes(*pos_tl, mark_main_size, mark_main_width, mark_small_size, mark_small_width, mark_small_dist, True, True, frame_width, 2, None, enable_alignment_layers)
                q1_shapes, q1_frame, q1_auto, q1_manual, _ = self._composite_mark_shapes(*pos_tr, mark_main_size, mark_main_width, mark_small_size, mark_small_width, mark_small_dist, False, True, frame_width, 1, None, enable_alignment_layers)

                self._insert_shapes(cell, layer_mark, q3_shapes + q4_shapes + q2_shapes + q1_shapes)
                self._insert_shapes(cell, layer_mark_frame, q3_frame + q4_frame + q2_frame + q1_frame)
                self._insert_shapes(cell, layer_auto_align, q3_auto + q4_auto + q2_auto + q1_auto)
                self._insert_shapes(cell, layer_manual_align, q3_manual + q4_manual + q2_manual + q1_manual)

                marker_l = self._corner_marker_shapes(0.0, 0.0, l_marker_length, l_marker_width)
                self._insert_shapes(cell, layer_mark, self._translate_shapes(self._rotate_shapes(marker_l, -90), wf_center_x - writefield_size / 2.0, wf_center_y + writefield_size / 2.0))
                self._insert_shapes(cell, layer_mark, self._translate_shapes(self._rotate_shapes(marker_l, 90), wf_center_x + writefield_size / 2.0, wf_center_y - writefield_size / 2.0))
                self._insert_shapes(cell, layer_mark_frame, self._translate_shapes(marker_l, wf_center_x - writefield_size / 2.0, wf_center_y - writefield_size / 2.0))
                self._insert_shapes(cell, layer_mark_frame, self._translate_shapes(self._rotate_shapes(marker_l, 180), wf_center_x + writefield_size / 2.0, wf_center_y + writefield_size / 2.0))

                label_text = f"{self._index_to_letters(i)}{j + 1}"
                label_configs = [
                    (pos_bl, (1, 1), ",3"),
                    (pos_br, (-1, 1), ",4"),
                    (pos_tl, (1, -1), ",2"),
                    (pos_tr, (-1, -1), ",1"),
                ]
                for (mx, my), (dx, dy), suffix in label_configs:
                    self._insert_shapes(cell, layer_mark, self._deplof_text(f"{label_text}{suffix}", mx + dx * label_offset[0], my + dy * label_offset[1], label_size, anchor="center", justify="center"))

                if enable_caliper:
                    self._insert_shapes(cell, layer_caliper, self._translate_shapes(self._caliper_shapes(0.0, 0.0, caliper_top_right_num_side, caliper_top_right_pitch, caliper_width, caliper_top_right_tick_length, caliper_top_right_center_length, "horizontal", -1, writefield_size), wf_center_x, wf_center_y + writefield_size / 2.0))
                    self._insert_shapes(cell, layer_caliper, self._translate_shapes(self._caliper_shapes(0.0, 0.0, caliper_top_right_num_side, caliper_top_right_pitch, caliper_width, caliper_top_right_tick_length, caliper_top_right_center_length, "vertical", -1, writefield_size), wf_center_x + writefield_size / 2.0, wf_center_y))
                    self._insert_shapes(cell, layer_caliper, self._translate_shapes(self._caliper_shapes(0.0, 0.0, caliper_bottom_left_num_side, caliper_bottom_left_pitch, caliper_width, caliper_bottom_left_tick_length, caliper_bottom_left_center_length, "horizontal", 1, writefield_size), wf_center_x, wf_center_y - writefield_size / 2.0))
                    self._insert_shapes(cell, layer_caliper, self._translate_shapes(self._caliper_shapes(0.0, 0.0, caliper_bottom_left_num_side, caliper_bottom_left_pitch, caliper_width, caliper_bottom_left_tick_length, caliper_bottom_left_center_length, "vertical", 1, writefield_size), wf_center_x - writefield_size / 2.0, wf_center_y))

        h_active_w = active_width / 2.0
        h_active_h = active_height / 2.0
        global_positions = [
            (-h_active_w - global_mark_offset, h_active_h + global_mark_offset),
            (h_active_w + global_mark_offset, h_active_h + global_mark_offset),
            (-h_active_w - global_mark_offset, -h_active_h - global_mark_offset),
            (h_active_w + global_mark_offset, -h_active_h - global_mark_offset),
            (0.0, h_active_h + global_mark_offset),
            (0.0, -h_active_h - global_mark_offset),
            (-h_active_w - global_mark_offset, 0.0),
            (h_active_w + global_mark_offset, 0.0),
        ]
        for idx, pos in enumerate(global_positions):
            layer_shapes, frame_shapes, auto_shapes, manual_shapes, text_shapes = self._composite_mark_shapes(
                pos[0], pos[1],
                global_mark_main_size, global_mark_main_width,
                global_mark_small_size, global_mark_small_width, global_mark_small_dist,
                is_main_mark=(idx == 0), enable_frame=True, frame_width=frame_width,
                quadrant_indicator=None, center_coords=pos, enable_alignment_layers=enable_alignment_layers,
            )
            self._insert_shapes(cell, layer_mark, layer_shapes + text_shapes)
            self._insert_shapes(cell, layer_mark_frame, frame_shapes)
            self._insert_shapes(cell, layer_auto_align, auto_shapes)
            self._insert_shapes(cell, layer_manual_align, manual_shapes)

        tl_mark_pos = (-h_active_w - global_mark_offset, h_active_h + global_mark_offset)
        offset_um = mark_offset_from_corner[0] if isinstance(mark_offset_from_corner, (tuple, list)) else mark_offset_from_corner
        de_um = (sample_width - active_width) / 2.0
        info_lines = [
            f"WF:{int(writefield_size)}um, Offset:{int(round(offset_um))}um",
            f"AA:{int(active_width)}um, DE:{int(round(de_um))}um",
        ]
        info_x = tl_mark_pos[0] + global_mark_main_size + info_text_offset[0]
        info_y_start = tl_mark_pos[1] + global_mark_main_size / 2.0 + info_text_offset[1]
        for idx, line in enumerate(info_lines):
            self._insert_shapes(cell, layer_mark, self._deplof_text(line, info_x, info_y_start - idx * info_text_size * 1.5, info_text_size, anchor="left_top", justify="left"))
        self._insert_shapes(cell, layer_mark, self._deplof_text(user_name, info_x, info_y_start - len(info_lines) * info_text_size * 1.5, info_text_size, anchor="left_top", justify="left"))
        return self.layout, cell


def build_general_mark_array_layout(**kwargs):
    builder = MarkArrayBuilder()
    return builder.build_general_mark_array(**kwargs)


def build_writefield_mark_layout(**kwargs):
    builder = MarkArrayBuilder()
    return builder.build_writefield_array(**kwargs)


def build_custom_global_mark_grid_layout(**kwargs):
    builder = MarkArrayBuilder()
    return builder.build_custom_global_mark_grid(**kwargs)


def build_text_pattern_array_layout(**kwargs):
    builder = MarkArrayBuilder()
    return builder.build_text_pattern_array(**kwargs)
