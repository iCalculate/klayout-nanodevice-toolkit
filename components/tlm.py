# -*- coding: utf-8 -*-
"""
TLM device generator.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import klayout.db as db
try:
    import pya
except ImportError:
    pya = db

from config import LAYER_DEFINITIONS, PROCESS_CONFIG
from utils.fanout_utils import draw_pad, draw_trapezoidal_fanout
from utils.geometry import GeometryUtils
from utils.mark_utils import MarkUtils


_GF_CACHE = None
_GF_IMPORT_ATTEMPTED = False


def _get_gdsfactory():
    global _GF_CACHE, _GF_IMPORT_ATTEMPTED
    if _GF_IMPORT_ATTEMPTED:
        return _GF_CACHE
    _GF_IMPORT_ATTEMPTED = True
    try:
        import gdsfactory as gf

        _GF_CACHE = gf
    except Exception:
        _GF_CACHE = None
    return _GF_CACHE


class TLM:
    """Transfer Length Method device."""

    def __init__(self, layout=None, **kwargs):
        self.layout = layout or db.Layout()
        self._layer_ids = {
            "channel": kwargs.get("channel_layer_id", 13),
            "source_drain": kwargs.get("source_drain_layer_id", 15),
            "labels": kwargs.get("label_layer_id", 3),
            "alignment_marks": kwargs.get("alignment_mark_layer_id", 3),
            "parameter_labels": kwargs.get("parameter_label_layer_id", 6),
        }
        MarkUtils.set_unit_scale(1000)
        self.setup_layers()

        self.num_electrodes = int(kwargs.get("num_electrodes", 6))
        self.min_spacing = float(kwargs.get("min_spacing", 1.0))
        self.max_spacing = float(kwargs.get("max_spacing", 20.0))
        self.distribution = kwargs.get("distribution", "log")
        self.spacing_mode = kwargs.get("spacing_mode", "centered")

        self.inner_pad_length = float(kwargs.get("inner_pad_length", 0.5))
        inner_pad_width = kwargs.get("inner_pad_width", None)
        self.inner_pad_width = None if inner_pad_width in (None, 0, 0.0) else float(inner_pad_width)
        self.outer_pad_length = float(kwargs.get("outer_pad_length", 60.0))
        self.outer_pad_width = float(kwargs.get("outer_pad_width", 60.0))
        outer_pad_spacing = kwargs.get("outer_pad_spacing", None)
        self.outer_pad_spacing = None if outer_pad_spacing in (None, 0, 0.0) else float(outer_pad_spacing)
        self.fanout_type = kwargs.get("fanout_type", "trapezoid")
        self.outer_pad_chamfer_type = kwargs.get("outer_pad_chamfer_type", "round")
        self.outer_pad_chamfer_size = float(kwargs.get("outer_pad_chamfer_size", 6.0))

        self.device_margin_x = float(kwargs.get("device_margin_x", 200.0))
        self.device_margin_y = float(kwargs.get("device_margin_y", 150.0))
        self.outer_pad_offset_y = float(kwargs.get("outer_pad_offset_y", 100.0))

        self.mark_size = float(kwargs.get("mark_size", 20.0))
        self.mark_width = float(kwargs.get("mark_width", 2.0))
        self.add_alignment_mark = bool(kwargs.get("add_alignment_mark", True))
        self.mark_types = list(kwargs.get("mark_types", ["sq_missing", "L_shape", "L_shape", "cross"]))
        self.mark_rotations = list(kwargs.get("mark_rotations", [0, 0, 2, 1]))

        channel_length = kwargs.get("channel_length", None)
        self.channel_length = None if channel_length in (None, 0, 0.0) else float(channel_length)
        self.channel_width = float(kwargs.get("channel_width", 5.0))

        self.label_size = float(kwargs.get("label_size", 20.0))
        self.label_text = str(kwargs.get("label_text", "TLM"))
        self.label_offset_x = float(kwargs.get("label_offset_x", 30.0))
        self.label_offset_y = float(kwargs.get("label_offset_y", -10.0))
        self.label_anchor = kwargs.get("label_anchor", kwargs.get("label_cursor", "left_top"))

    def setup_layers(self):
        for layer_info in LAYER_DEFINITIONS.values():
            self.layout.layer(layer_info["id"], 0)
        for layer_id in self._layer_ids.values():
            self.layout.layer(layer_id, 0)

    def _layer_index(self, layer_key):
        return self.layout.layer(self._layer_ids[layer_key], 0)

    def get_layer_ids(self):
        return dict(self._layer_ids)

    def set_device_parameters(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def _append_text_shape(self, text, x, y, layer_key, size=None):
        if not text:
            return []
        text = str(text)
        text_size = float(size if size is not None else self.label_size)
        layer_id = self._layer_ids[layer_key]

        gf = _get_gdsfactory()
        if gf is not None:
            try:
                text_component = gf.components.text(
                    text=text,
                    size=text_size,
                    justify="left",
                    layer=(layer_id, 0),
                )
                bbox = text_component.bbox
                offset_x = x - float(bbox[0][0])
                offset_y = y - float(bbox[0][1])
                polygons = []
                for polygon in text_component.get_polygons():
                    points = [pya.Point(int(px + offset_x), int(py + offset_y)) for px, py in polygon]
                    if len(points) >= 3:
                        polygons.append(pya.Polygon(points))
                if polygons:
                    return polygons
            except Exception:
                pass

        try:
            generator = pya.TextGenerator.default_generator()
            mag = text_size / max(generator.dheight(), 1e-9)
            region = generator.text(text, PROCESS_CONFIG["dbu"], mag, False, 0.0, 0.0, 0.0).merged()
            bbox = region.bbox()
            dx = int(round(x / PROCESS_CONFIG["dbu"] - bbox.left))
            dy = int(round(y / PROCESS_CONFIG["dbu"] - bbox.bottom))
            return [region.moved(dx, dy)]
        except Exception:
            return [pya.Text(text, int(x * 1000), int(y * 1000))]

    def _append_note_text(self, text, x, y):
        if not text:
            return []
        return [pya.Text(str(text), int(x * 1000), int(y * 1000))]

    def _normalized_mark_type(self, mark_type):
        aliases = {
            "l": "l_shape",
            "L_shape": "l_shape",
            "t": "t_shape",
            "T_shape": "t_shape",
        }
        return aliases.get(str(mark_type), mark_type)

    def _create_mark(self, x, y, mark_type, rotation):
        normalized = self._normalized_mark_type(mark_type)
        stroke_ratio = max(self.mark_width / max(self.mark_size, 1e-9), 1e-3)

        if normalized == "sq_missing":
            return MarkUtils.sq_missing(x, y, self.mark_size).rotate(rotation)
        if normalized in ("l_shape", "t_shape", "cross_tri"):
            return getattr(MarkUtils, normalized)(x, y, self.mark_size, stroke_ratio).rotate(rotation)
        if normalized in ("square", "circle", "diamond"):
            return getattr(MarkUtils, normalized)(x, y, self.mark_size).rotate(rotation)
        if normalized == "triangle":
            return MarkUtils.triangle(x, y, self.mark_size).rotate(rotation)
        if hasattr(MarkUtils, normalized):
            try:
                return getattr(MarkUtils, normalized)(x, y, self.mark_size, self.mark_width).rotate(rotation)
            except TypeError:
                return getattr(MarkUtils, normalized)(x, y, self.mark_size).rotate(rotation)
        return MarkUtils.cross(x, y, self.mark_size, self.mark_width).rotate(rotation)

    def create_device_label(self, cell, x=0.0, y=0.0, label_text=None):
        text = self.label_text if label_text is None else label_text
        if not text:
            return
        label_x = x - self.device_margin_x + self.label_offset_x
        label_y = y + self.device_margin_y + self.label_offset_y
        for shape in self._append_text_shape(text, label_x, label_y, "labels"):
            cell.shapes(self._layer_index("labels")).insert(shape)

    def generate_electrode_positions(self):
        n = self.num_electrodes
        if n < 3:
            raise ValueError("num_electrodes must be >= 3")

        pad_length = self.inner_pad_length
        if self.distribution == "log" and self.min_spacing > 0 and self.max_spacing > 0:
            edge_spacings = [
                self.min_spacing * (self.max_spacing / self.min_spacing) ** (i / (n - 2))
                for i in range(n - 1)
            ]
        elif self.distribution == "exp":
            edge_spacings = [
                self.min_spacing * (self.max_spacing / self.min_spacing) ** (i / (n - 2))
                for i in range(n - 1)
            ]
        elif self.distribution == "inv":
            edge_spacings = [
                1.0
                / (
                    1.0 / self.min_spacing
                    + (1.0 / self.max_spacing - 1.0 / self.min_spacing) * i / (n - 2)
                )
                for i in range(n - 1)
            ]
        else:
            edge_spacings = [
                self.min_spacing + (self.max_spacing - self.min_spacing) * i / (n - 2)
                for i in range(n - 1)
            ]

        spacings = [edge_spacing + pad_length for edge_spacing in edge_spacings]
        if self.spacing_mode == "centered":
            spacings_sorted = sorted(spacings)
            arranged = [0.0] * (n - 1)
            center = (n - 2) // 2
            left = center
            right = center + 1
            for index, value in enumerate(spacings_sorted):
                if index == 0:
                    arranged[center] = value
                elif index % 2 == 1 and right < len(arranged):
                    arranged[right] = value
                    right += 1
                elif left - 1 >= 0:
                    arranged[left - 1] = value
                    left -= 1
            spacings = arranged

        xs = [0.0]
        for spacing in spacings:
            xs.append(xs[-1] + spacing)
        x_shift = (xs[0] + xs[-1]) / 2.0
        return [position - x_shift for position in xs]

    def _resolved_inner_pad_width(self):
        if self.inner_pad_width is not None:
            return self.inner_pad_width
        relative_width = self.channel_width * 1.2
        excess_width = relative_width - self.channel_width
        excess_width = max(2.0, min(10.0, excess_width))
        return self.channel_width + excess_width

    def _resolved_channel_length(self, xs):
        ch_x0 = xs[0]
        ch_x1 = xs[-1]
        return self.channel_length if self.channel_length is not None else abs(ch_x1 - ch_x0) * 1.1

    def _distribute_outer_pads(self, x_list):
        if len(x_list) <= 1:
            return list(x_list)
        min_outer_pad_spacing = self.outer_pad_spacing if self.outer_pad_spacing is not None else self.outer_pad_width * 1.1
        x_list_sorted = sorted(x_list)
        min_dist = min(x_list_sorted[i + 1] - x_list_sorted[i] for i in range(len(x_list_sorted) - 1))
        if min_dist >= min_outer_pad_spacing:
            return list(x_list)
        total_length = (len(x_list) - 1) * min_outer_pad_spacing
        start = -total_length / 2.0
        return [start + i * min_outer_pad_spacing for i in range(len(x_list))]

    def create_single_device(self, cell_name="TLM_Device", x=0, y=0):
        cell = self.layout.create_cell(cell_name)
        xs = self.generate_electrode_positions()
        pad_width = self._resolved_inner_pad_width()
        source_drain_layer = self._layer_index("source_drain")
        channel_layer = self._layer_index("channel")
        mark_layer = self._layer_index("alignment_marks")
        label_layer = self._layer_index("labels")
        note_layer = self._layer_index("parameter_labels")

        for xc in xs:
            inner = draw_pad((xc + x, y), self.inner_pad_length, pad_width, chamfer_size=0, chamfer_type="none")
            if isinstance(inner.polygon, (db.Polygon, db.Box)):
                cell.shapes(source_drain_layer).insert(inner.polygon)

        upper_xs = [xc for index, xc in enumerate(xs) if index % 2 == 0]
        lower_xs = [xc for index, xc in enumerate(xs) if index % 2 == 1]
        upper_xs_dist = self._distribute_outer_pads(upper_xs)
        lower_xs_dist = self._distribute_outer_pads(lower_xs)
        upper_index = 0
        lower_index = 0

        for index, xc in enumerate(xs):
            if index % 2 == 0:
                outer_center = (upper_xs_dist[upper_index] + x, y + self.outer_pad_offset_y)
                upper_index += 1
                inner_edge = "U"
                outer_edge = "D"
            else:
                outer_center = (lower_xs_dist[lower_index] + x, y - self.outer_pad_offset_y)
                lower_index += 1
                inner_edge = "D"
                outer_edge = "U"

            outer = draw_pad(
                outer_center,
                self.outer_pad_length,
                self.outer_pad_width,
                chamfer_size=self.outer_pad_chamfer_size,
                chamfer_type=self.outer_pad_chamfer_type,
            )
            if isinstance(outer.polygon, (db.Polygon, db.Box)):
                cell.shapes(source_drain_layer).insert(outer.polygon)

            inner = draw_pad((xc + x, y), self.inner_pad_length, pad_width, chamfer_size=0, chamfer_type="none")
            if self.fanout_type == "trapezoid":
                fanout = draw_trapezoidal_fanout(inner, outer, inner_edge=inner_edge, outer_edge=outer_edge)
                cell.shapes(source_drain_layer).insert(fanout)

        channel_length = self._resolved_channel_length(xs)
        channel_center = x
        channel_box = GeometryUtils.create_rectangle(channel_center, y, channel_length, self.channel_width, center=True)
        cell.shapes(channel_layer).insert(channel_box)

        if self.add_alignment_mark:
            mark_positions = [
                (x - self.device_margin_x, y + self.device_margin_y),
                (x + self.device_margin_x, y + self.device_margin_y),
                (x - self.device_margin_x, y - self.device_margin_y),
                (x + self.device_margin_x, y - self.device_margin_y),
            ]
            for index, (mx, my) in enumerate(mark_positions):
                mark_type = self.mark_types[index] if index < len(self.mark_types) else "cross"
                rotation = self.mark_rotations[index] if index < len(self.mark_rotations) else 0
                mark = self._create_mark(mx, my, mark_type, rotation)
                shapes = mark.get_shapes() if hasattr(mark, "get_shapes") else [mark]
                if not isinstance(shapes, list):
                    shapes = [shapes]
                for shape in shapes:
                    if isinstance(shape, db.Region):
                        for polygon in shape.each():
                            cell.shapes(mark_layer).insert(polygon)
                    elif isinstance(shape, (db.Polygon, db.Box)):
                        cell.shapes(mark_layer).insert(shape)

        self.create_device_label(cell, x, y)

        note_x = x - self.device_margin_x + 10.0
        note_y = y - self.device_margin_y + 15.0
        line1 = f"W={self.channel_width:.2f}, L={channel_length:.2f}, N={self.num_electrodes}"
        line2 = f"S=[{self.min_spacing:.2f}, {self.max_spacing:.2f}], D={self.distribution}"
        for shape in self._append_note_text(line1, note_x, note_y):
            cell.shapes(note_layer).insert(shape)
        for shape in self._append_note_text(line2, note_x, note_y - 12.0):
            cell.shapes(note_layer).insert(shape)

        return cell

    def create_alignment_marks(self, cell, x=0.0, y=0.0):
        mark_layer = self._layer_index("alignment_marks")
        for mark_y in [y + self.device_margin_y, y - self.device_margin_y]:
            marks = MarkUtils.cross(x, mark_y, self.mark_size, self.mark_width)
            shapes = marks.get_shapes() if hasattr(marks, "get_shapes") else [marks]
            if not isinstance(shapes, list):
                shapes = [shapes]
            for shape in shapes:
                if isinstance(shape, db.Region):
                    for polygon in shape.each():
                        cell.shapes(mark_layer).insert(polygon)
                elif isinstance(shape, (db.Polygon, db.Box)):
                    cell.shapes(mark_layer).insert(shape)

    def create_device_array(self, rows=2, cols=2, device_spacing_x=None, device_spacing_y=None, label_prefix="TLM"):
        if device_spacing_x is None:
            device_spacing_x = self.device_margin_x * 2 + 50.0
        if device_spacing_y is None:
            device_spacing_y = self.device_margin_y * 2 + 50.0

        array_cell = self.layout.create_cell(f"{label_prefix}_Array")
        label_layer = self._layer_index("labels")
        device_id = 1
        for row in range(rows):
            for col in range(cols):
                device_x = float(col * device_spacing_x)
                device_y = float(row * device_spacing_y)
                excel_label = f"{chr(ord('A') + col)}{row + 1}"
                device_cell = self.create_single_device(f"TLM_{device_id:03d}", device_x, device_y)
                array_cell.insert(db.CellInstArray(device_cell.cell_index(), db.Trans(0, 0)))

                mark_x = device_x - self.device_margin_x
                mark_y = device_y + self.device_margin_y
                for shape in self._append_text_shape(
                    excel_label,
                    mark_x + self.label_offset_x,
                    mark_y + self.label_offset_y,
                    "labels",
                ):
                    array_cell.shapes(label_layer).insert(shape)
                device_id += 1
        return array_cell

    def scan_parameters_and_create_array(self, param_ranges, rows=3, cols=3, offset_x=0, offset_y=0):
        scan_cell = self.layout.create_cell("TLM_Parameter_Scan")
        device_spacing_x = self.device_margin_x * 2 + 50.0
        device_spacing_y = self.device_margin_y * 2 + 50.0
        device_id = 1

        for row in range(rows):
            for col in range(cols):
                current_params = {}
                for param_name, rng in param_ranges.items():
                    if len(rng) == 3 and isinstance(rng[0], (int, float)):
                        min_val, max_val, steps = rng
                        axis_index = col if param_name in ("max_spacing",) else row
                        value = min_val if steps <= 1 else min_val + axis_index * (max_val - min_val) / (steps - 1)
                        current_params[param_name] = value
                    elif len(rng) >= 1:
                        current_params[param_name] = rng[0]

                if "width" in current_params and "channel_width" not in current_params:
                    current_params["channel_width"] = current_params.pop("width")

                self.set_device_parameters(**current_params)
                device_x = float(offset_x + col * device_spacing_x)
                device_y = float(offset_y + row * device_spacing_y)
                device_cell = self.create_single_device(f"TLM_SCAN_{device_id:02d}", device_x, device_y)
                scan_cell.insert(db.CellInstArray(device_cell.cell_index(), db.Trans(0, 0)))

                mark_x = device_x - self.device_margin_x
                mark_y = device_y + self.device_margin_y
                excel_label = f"{chr(ord('A') + col)}{row + 1}"
                for shape in self._append_text_shape(
                    excel_label,
                    mark_x + self.label_offset_x,
                    mark_y + self.label_offset_y,
                    "labels",
                ):
                    scan_cell.shapes(self._layer_index("labels")).insert(shape)
                device_id += 1
        return scan_cell


def main():
    layout = db.Layout()
    tlm = TLM(layout=layout, num_electrodes=8)
    tlm.create_single_device("Test_TLM", 0, 0)


if __name__ == "__main__":
    main()
