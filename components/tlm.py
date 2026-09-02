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
from utils.fanout_utils import draw_pad, draw_tangent_fanout, draw_trapezoidal_fanout
from utils.geometry import GeometryUtils
from utils.mark_utils import MarkUtils
from utils.text_utils import TextUtils
from components.markarray import MarkArrayBuilder


class TLM:
    """Transfer Length Method device."""

    def __init__(self, layout=None, **kwargs):
        self.layout = layout or db.Layout()
        source_drain_layer_id = int(kwargs.get("source_drain_layer_id", 15))
        default_fine_layer_id = (
            source_drain_layer_id + 10
            if 11 <= source_drain_layer_id <= 19
            else LAYER_DEFINITIONS["fine_source_drain"]["id"]
        )
        self._layer_ids = {
            "channel": kwargs.get("channel_layer_id", 13),
            "source_drain": source_drain_layer_id,
            "fine_source_drain": int(kwargs.get("fine_source_drain_layer_id", default_fine_layer_id)),
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
        self.outer_pad_layout = str(kwargs.get("outer_pad_layout", "auto"))
        self.outer_pad_frame_threshold = int(kwargs.get("outer_pad_frame_threshold", 10))

        # In split EBL mode the small contact and its short lead are exposed on
        # the corresponding layer in the 21-29 device stack.  A coarse bridge
        # pad outside the channel provides a forgiving overlay target.
        self.split_ebl_exposure = bool(kwargs.get("split_ebl_exposure", False))
        self.fine_fanout_length = float(kwargs.get("fine_fanout_length", 2.0))
        bridge_pad_size = kwargs.get("bridge_pad_size", kwargs.get("bridge_pad_length", 10.0))
        self.bridge_pad_size = float(bridge_pad_size)
        # Retain these aliases for existing Python callers, but the bridge is
        # deliberately square in all newly generated geometry.
        self.bridge_pad_length = self.bridge_pad_size
        self.bridge_pad_width = self.bridge_pad_size
        self.bridge_pad_spacing = float(kwargs.get("bridge_pad_spacing", 12.0))
        self.bridge_pad_v_step = float(kwargs.get("bridge_pad_v_step", 5.0))
        self.fine_landing_size = float(
            kwargs.get("fine_landing_size", kwargs.get("ebl_overlap", 6.0))
        )
        self.ebl_overlap = self.fine_landing_size  # compatibility alias
        self.fine_route_width = float(kwargs.get("fine_route_width", min(1.0, self.inner_pad_length)))
        self.route_clearance = float(kwargs.get("route_clearance", 1.0))
        self.bridge_center_mark_enabled = bool(kwargs.get("bridge_center_mark_enabled", False))
        self.bridge_center_mark_type = str(kwargs.get("bridge_center_mark_type", "chessboard")).lower()
        self.bridge_center_mark_size = float(kwargs.get("bridge_center_mark_size", 4.0))
        self.bridge_center_mark_width = float(kwargs.get("bridge_center_mark_width", 0.8))

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
        self.channel_width = float(kwargs.get("channel_width", 10.0))

        self.label_size = float(kwargs.get("label_size", 20.0))
        self.label_text = str(kwargs.get("label_text", "TLM"))
        self.label_offset_x = float(kwargs.get("label_offset_x", 30.0))
        self.label_offset_y = float(kwargs.get("label_offset_y", -10.0))
        self.label_anchor = kwargs.get("label_anchor", kwargs.get("label_cursor", "left_top"))
        self._validate()

    def _validate(self):
        if self.num_electrodes < 3:
            raise ValueError("num_electrodes must be >= 3")
        if self.min_spacing < 0.0 or self.max_spacing < 0.0:
            raise ValueError("TLM electrode spacings cannot be negative")
        if self.outer_pad_layout not in ("auto", "two_rows", "rectangular_frame"):
            raise ValueError("TLM outer_pad_layout must be auto, two_rows, or rectangular_frame")
        if self.outer_pad_frame_threshold < 4:
            raise ValueError("TLM outer_pad_frame_threshold must be at least 4")
        if self.split_ebl_exposure:
            positive = {
                "bridge_pad_length": self.bridge_pad_length,
                "bridge_pad_width": self.bridge_pad_width,
                "fine_route_width": self.fine_route_width,
                "fine_landing_size": self.fine_landing_size,
            }
            invalid = [name for name, value in positive.items() if value <= 0.0]
            if invalid:
                raise ValueError("TLM EBL dimensions must be positive: " + ", ".join(invalid))
            if self.fine_fanout_length < 0.0:
                raise ValueError("TLM fine_fanout_length cannot be negative")
            if self.bridge_pad_spacing < 0.0:
                raise ValueError("TLM bridge_pad_spacing cannot be negative")
            if self.bridge_pad_v_step < 0.0:
                raise ValueError("TLM bridge_pad_v_step cannot be negative")
            if self.route_clearance < 0.0:
                raise ValueError("TLM route_clearance cannot be negative")
            if self.fine_landing_size > self.bridge_pad_size:
                raise ValueError("TLM fine_landing_size cannot exceed bridge_pad_size")
            if self.fine_route_width > min(self.inner_pad_length, self.bridge_pad_size):
                raise ValueError("TLM fine_route_width must fit the inner and bridge pads")
            if self.bridge_center_mark_type not in ("chessboard", "bonecross", "split_bonecross", "cross"):
                raise ValueError(
                    "TLM bridge_center_mark_type must be chessboard, bonecross, split_bonecross, or cross"
                )
            if self.bridge_center_mark_enabled:
                if self.bridge_center_mark_size <= 0.0 or self.bridge_center_mark_width <= 0.0:
                    raise ValueError("TLM bridge center mark dimensions must be positive")
                if self.bridge_center_mark_size > self.bridge_pad_size:
                    raise ValueError("TLM bridge_center_mark_size cannot exceed bridge_pad_size")
                if self.bridge_center_mark_width > self.bridge_center_mark_size:
                    raise ValueError("TLM bridge_center_mark_width cannot exceed bridge_center_mark_size")

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

        try:
            polygons = TextUtils.create_text_deplof(
                text=text,
                x=x,
                y=y,
                size_um=text_size,
                anchor="left_bottom",
                justify="left",
            )
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

    def _distribute_bridge_pads(self, x_list):
        """Keep bridge pads near their contacts while enforcing pad clearance."""
        if not x_list:
            return []
        pitch = self.bridge_pad_size + self.bridge_pad_spacing
        distributed = []
        for position in x_list:
            distributed.append(
                float(position)
                if not distributed
                else max(float(position), distributed[-1] + pitch)
            )
        # Preserve the contact row's centroid so the bridge row stays local to
        # the active channel rather than drifting as clearances are enforced.
        shift = sum(distributed) / len(distributed) - sum(x_list) / len(x_list)
        return [position - shift for position in distributed]

    def _insert_manhattan_bundle(self, cell, layer, starts, ends, width, side, begin_extension=0.0):
        """Insert a clearance-controlled row-to-row Manhattan fanout.

        Routes are ordered by their contact x coordinate.  Each successive
        horizontal segment is one full width-plus-clearance pitch farther from
        the channel, so it cannot form a near-T with a preceding vertical leg.
        """
        if not starts:
            return
        direction = 1.0 if side == "top" else -1.0
        pitch = width + self.route_clearance
        ordered = sorted(zip(starts, ends), key=lambda pair: pair[0][0])
        start_edge = max(direction * start[1] for start, _end in ordered)
        first_lane = start_edge + width + self.route_clearance
        left_moving = [index for index, (start, end) in enumerate(ordered) if end[0] < start[0] - 1e-9]
        straight = [index for index, (start, end) in enumerate(ordered) if abs(end[0] - start[0]) <= 1e-9]
        right_moving = [index for index, (start, end) in enumerate(ordered) if end[0] > start[0] + 1e-9]
        lane_rank = {}
        for rank, index in enumerate(left_moving + straight):
            lane_rank[index] = rank
        for offset, index in enumerate(right_moving):
            lane_rank[index] = len(ordered) - 1 - offset
        width_dbu = int(round(width * 1000.0))
        for order, (start, end) in enumerate(ordered):
            lane_y = direction * (first_lane + lane_rank[order] * pitch)
            inner_start = (start[0], start[1] - direction * begin_extension)
            points_um = [inner_start, start, (start[0], lane_y), (end[0], lane_y), end]
            compact = []
            for point in points_um:
                point_dbu = db.Point(int(round(point[0] * 1000.0)), int(round(point[1] * 1000.0)))
                if not compact or point_dbu != compact[-1]:
                    compact.append(point_dbu)
            cell.shapes(layer).insert(db.Path(compact, width_dbu))

    def _insert_side_manhattan_routes(self, cell, layer, starts, ends, width, side, begin_extension=0.0):
        """Route a vertical frame side without a shared contact-row segment."""
        direction = -1.0 if side == "left" else 1.0
        width_dbu = int(round(width * 1000.0))
        for start, end in zip(starts, ends):
            inner_start = (start[0] - direction * begin_extension, start[1])
            points_um = [inner_start, start, (start[0], end[1]), end]
            compact = []
            for point in points_um:
                point_dbu = db.Point(int(round(point[0] * 1000.0)), int(round(point[1] * 1000.0)))
                if not compact or point_dbu != compact[-1]:
                    compact.append(point_dbu)
            cell.shapes(layer).insert(db.Path(compact, width_dbu))

    def _bridge_mark_region(self, builder, center_x, center_y):
        region = db.Region()
        shapes = builder.create_mark_shapes(
            center_x,
            center_y,
            self.bridge_center_mark_type,
            self.bridge_center_mark_size,
            self.bridge_center_mark_width,
        )
        if not isinstance(shapes, (list, tuple)):
            shapes = [shapes]
        for shape in shapes:
            if isinstance(shape, db.Region):
                region += shape
            elif self.bridge_center_mark_type == "chessboard" and hasattr(shape, "bbox"):
                # NanoMark's positive chessboard uses two outlined diagonal
                # squares.  In a negative bridge mark the complete squares are
                # the apertures; retaining the outline holes would leave two
                # electrically isolated metal islands inside the bridge.
                region.insert(shape.bbox())
            else:
                region.insert(shape)
        return region.merged()

    def _resolved_outer_pad_layout(self):
        if self.outer_pad_layout == "auto":
            return "rectangular_frame" if self.num_electrodes >= self.outer_pad_frame_threshold else "two_rows"
        return self.outer_pad_layout

    def _pad_side_assignments(self, count):
        if self._resolved_outer_pad_layout() == "two_rows":
            return ["top" if index % 2 == 0 else "bottom" for index in range(count)]
        if count < 4:
            return ["top" if index % 2 == 0 else "bottom" for index in range(count)]
        # The extreme contacts feed the two vertical sides; the remaining
        # contacts alternate across the horizontal sides.  This creates a
        # four-sided ring without sending a side route through another inner
        # contact in the dense one-dimensional TLM contact array.
        sides = ["top" if index % 2 == 0 else "bottom" for index in range(count)]
        sides[0] = "left"
        sides[-1] = "right"
        return sides

    @staticmethod
    def _centered_positions(count, pitch):
        if count <= 0:
            return []
        start = -(count - 1) * pitch / 2.0
        return [start + index * pitch for index in range(count)]

    def _outer_pad_specs(self, xs, bridge_centers, sides, x, y):
        """Map each electrode to a two-row pad or a four-sided frame pad."""
        if self._resolved_outer_pad_layout() == "two_rows":
            upper_dist = self._distribute_outer_pads(xs[::2])
            lower_dist = self._distribute_outer_pads(xs[1::2])
            upper_index = 0
            lower_index = 0
            specs = []
            for index in range(len(xs)):
                if index % 2 == 0:
                    specs.append(((upper_dist[upper_index] + x, y + self.outer_pad_offset_y), "U", "D", "top"))
                    upper_index += 1
                else:
                    specs.append(((lower_dist[lower_index] + x, y - self.outer_pad_offset_y), "D", "U", "bottom"))
                    lower_index += 1
            return specs

        top_indices = [index for index, side in enumerate(sides) if side == "top"]
        bottom_indices = [index for index, side in enumerate(sides) if side == "bottom"]
        left_indices = [index for index, side in enumerate(sides) if side == "left"]
        right_indices = [index for index, side in enumerate(sides) if side == "right"]

        pitch_x = self.outer_pad_spacing if self.outer_pad_spacing is not None else self.outer_pad_length * 1.1
        pitch_y = self.outer_pad_spacing if self.outer_pad_spacing is not None else self.outer_pad_width * 1.1
        horizontal_count = max(len(top_indices), len(bottom_indices), 1)
        vertical_count = max(len(left_indices), len(right_indices), 1)
        frame_outer_half_width = max(
            self.outer_pad_offset_y,
            (horizontal_count - 1) * pitch_x / 2.0 + self.outer_pad_length / 2.0,
        )
        # The side-pad outer edge, rather than its centre, aligns with the
        # outer boundary of the horizontal pad rows.
        half_width = max(frame_outer_half_width - self.outer_pad_length / 2.0, 0.0)
        half_height = max(
            self.outer_pad_offset_y,
            (vertical_count - 1) * pitch_y / 2.0 + self.outer_pad_width / 2.0,
        )

        assignments = {}

        def assign(indices, positions, side, inner_edge, outer_edge):
            if side in ("top", "bottom"):
                ordered = sorted(indices, key=lambda idx: bridge_centers[idx][0])
            else:
                ordered = sorted(indices, key=lambda idx: bridge_centers[idx][1])
            for index, center in zip(ordered, positions):
                assignments[index] = (center, inner_edge, outer_edge, side)

        top_xs = self._centered_positions(len(top_indices), pitch_x)
        bottom_xs = self._centered_positions(len(bottom_indices), pitch_x)
        left_ys = self._centered_positions(len(left_indices), pitch_y)
        right_ys = self._centered_positions(len(right_indices), pitch_y)
        assign(top_indices, [(x + px, y + half_height) for px in top_xs], "top", "U", "D")
        assign(bottom_indices, [(x + px, y - half_height) for px in bottom_xs], "bottom", "D", "U")
        assign(left_indices, [(x - half_width, y + py) for py in left_ys], "left", "L", "R")
        assign(right_indices, [(x + half_width, y + py) for py in right_ys], "right", "R", "L")
        return [assignments[index] for index in range(len(xs))]

    def _bridge_pad_centers(self, xs, sides, x, y, pad_width, channel_length, gap):
        centers = [None] * len(xs)
        pitch = self.bridge_pad_size + self.bridge_pad_spacing
        core_half_y = max(self.channel_width, pad_width) / 2.0
        core_half_x = channel_length / 2.0

        for side in ("top", "bottom"):
            indices = [index for index, assigned in enumerate(sides) if assigned == side]
            distributed = self._distribute_bridge_pads([xs[index] for index in indices])
            direction = 1.0 if side == "top" else -1.0
            base_center_y = y + direction * (core_half_y + gap + self.bridge_pad_size / 2.0)
            for position, (index, center_x) in enumerate(zip(indices, distributed)):
                v_level = min(position, len(indices) - 1 - position)
                center_y = base_center_y + direction * v_level * self.bridge_pad_v_step
                centers[index] = (x + center_x, center_y)

        left_indices = [index for index, assigned in enumerate(sides) if assigned == "left"]
        right_indices = [index for index, assigned in enumerate(sides) if assigned == "right"]
        for side, indices, direction in (("left", left_indices, -1.0), ("right", right_indices, 1.0)):
            if len(indices) <= 1:
                ys = [0.0] * len(indices)
            else:
                side_route_offset = (
                    core_half_y
                    + gap
                    + self.bridge_pad_size / 2.0
                    + self.route_clearance
                    + self.fine_route_width
                )
                negative_count = len(indices) // 2
                negative = [-(side_route_offset + position * pitch) for position in range(negative_count)]
                positive = [side_route_offset + position * pitch for position in range(len(indices) - negative_count)]
                # Routes leave each contact vertically and then turn towards
                # the side.  Reverse the nesting on the right so horizontal
                # legs never cut across a neighbouring vertical leg.
                ys = negative + positive
                if side == "right":
                    ys = list(reversed(negative)) + list(reversed(positive))
            center_x = x + direction * (core_half_x + gap + self.bridge_pad_size / 2.0)
            for index, center_y in zip(indices, ys):
                centers[index] = (center_x, y + center_y)
        return centers

    def create_single_device(self, cell_name="TLM_Device", x=0, y=0):
        cell = self.layout.create_cell(cell_name)
        xs = self.generate_electrode_positions()
        pad_width = self._resolved_inner_pad_width()
        source_drain_layer = self._layer_index("source_drain")
        fine_source_drain_layer = self._layer_index("fine_source_drain")
        channel_layer = self._layer_index("channel")
        mark_layer = self._layer_index("alignment_marks")
        label_layer = self._layer_index("labels")
        note_layer = self._layer_index("parameter_labels")

        for xc in xs:
            inner = draw_pad((xc + x, y), self.inner_pad_length, pad_width, chamfer_size=0, chamfer_type="none")
            if isinstance(inner.polygon, (db.Polygon, db.Box)):
                target_layer = fine_source_drain_layer if self.split_ebl_exposure else source_drain_layer
                cell.shapes(target_layer).insert(inner.polygon)

        sides = self._pad_side_assignments(len(xs))
        max_fine_bundle_count = max(
            [sides.count(side) for side in ("top", "bottom", "left", "right")] + [1]
        )
        required_fine_route_gap = (
            self.bridge_pad_size / 2.0
            + (max_fine_bundle_count - 1) * (self.fine_route_width + self.route_clearance)
            + self.fine_route_width
        )
        resolved_fine_fanout_length = max(self.fine_fanout_length, required_fine_route_gap)
        channel_length = self._resolved_channel_length(xs)
        bridge_centers = self._bridge_pad_centers(
            xs, sides, x, y, pad_width, channel_length, resolved_fine_fanout_length
        )
        outer_specs = self._outer_pad_specs(xs, bridge_centers, sides, x, y)
        route_groups = {
            side: {"fine_starts": [], "fine_ends": []}
            for side in ("top", "bottom", "left", "right")
        }
        mark_builder = MarkArrayBuilder(self.layout) if self.bridge_center_mark_enabled else None

        for index, xc in enumerate(xs):
            side = sides[index]
            route_group = route_groups[side]
            bridge_center_x, bridge_center_y = bridge_centers[index]
            outer_center, bridge_outer_edge, outer_inner_edge, _outer_side = outer_specs[index]

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
                if self.split_ebl_exposure:
                    bridge = draw_pad(
                        (bridge_center_x, bridge_center_y),
                        self.bridge_pad_length,
                        self.bridge_pad_width,
                        chamfer_size=0,
                        chamfer_type="none",
                    )

                    fine_landing = draw_pad(
                        (bridge_center_x, bridge_center_y),
                        self.fine_landing_size,
                        self.fine_landing_size,
                        chamfer_size=0,
                        chamfer_type="none",
                    )
                    cell.shapes(fine_source_drain_layer).insert(fine_landing.polygon)

                    # Bundle routing mirrors NanoRoute: constant-width native
                    # Paths with horizontal/vertical segments and separate
                    # lanes for neighbouring electrodes.
                    if side == "top":
                        fine_start = (xc + x, y + pad_width / 2.0)
                    elif side == "bottom":
                        fine_start = (xc + x, y - pad_width / 2.0)
                    elif side == "left":
                        fine_start = (xc + x - self.inner_pad_length / 2.0, y)
                    else:
                        fine_start = (xc + x + self.inner_pad_length / 2.0, y)
                    route_group["fine_starts"].append(fine_start)
                    route_group["fine_ends"].append((bridge_center_x, bridge_center_y))
                    coarse_fanout = draw_tangent_fanout(
                        bridge,
                        outer,
                        outer_edge=outer_inner_edge,
                    )
                    if mark_builder is None:
                        cell.shapes(source_drain_layer).insert(bridge.polygon)
                        cell.shapes(source_drain_layer).insert(coarse_fanout)
                    else:
                        coarse_transition = db.Region(bridge.polygon)
                        coarse_transition.insert(coarse_fanout)
                        coarse_transition -= self._bridge_mark_region(
                            mark_builder, bridge_center_x, bridge_center_y
                        )
                        for polygon in coarse_transition.merged().each():
                            cell.shapes(source_drain_layer).insert(polygon)
                else:
                    fanout = draw_trapezoidal_fanout(
                        inner,
                        outer,
                        inner_edge=bridge_outer_edge,
                        outer_edge=outer_inner_edge,
                    )
                    cell.shapes(source_drain_layer).insert(fanout)

        if self.split_ebl_exposure and self.fanout_type == "trapezoid":
            begin_extension = min(self.fine_route_width, self.inner_pad_length / 2.0)
            for side, route_group in route_groups.items():
                if side in ("left", "right"):
                    self._insert_side_manhattan_routes(
                        cell,
                        fine_source_drain_layer,
                        route_group["fine_starts"],
                        route_group["fine_ends"],
                        self.fine_route_width,
                        side,
                        begin_extension=begin_extension,
                    )
                else:
                    self._insert_manhattan_bundle(
                        cell,
                        fine_source_drain_layer,
                        route_group["fine_starts"],
                        route_group["fine_ends"],
                        self.fine_route_width,
                        side,
                        begin_extension=begin_extension,
                    )

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
        if self.split_ebl_exposure:
            line2 += f", EBL={self._layer_ids['source_drain']}/{self._layer_ids['fine_source_drain']}"
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
