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

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import klayout.db as db

try:
    import pya
except ImportError:
    pya = db

from config import DEFAULT_DBU, DEFAULT_UNIT_SCALE
from utils.geometry import GeometryUtils
from utils.text_utils import TextUtils


class MarkArrayBuilder:
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
            c_text_size = main_size / 25.0
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
