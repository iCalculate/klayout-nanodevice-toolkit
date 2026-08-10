"""Parametric short-channel HEMT layout generator.

The layout follows the common probe-friendly topology used in the reference
micrographs: a gate pad and gate manifold on the left, drain fanout on the
right, and source contacts outside the gated channel.  A one-finger device is
laid out as S-G-D; a two-finger device is the symmetric S-G-D-G-S structure
with a shared drain and shared gate.

All public dimensions are in micrometres.  Generated KLayout geometry uses a
1 nm database grid, matching the rest of NanoDevice.
"""

import pya

from config import LAYER_DEFINITIONS


_DBU_PER_UM = 1000.0


class HEMT:
    """Build a single- or double-gate-finger HEMT test structure."""

    def __init__(
        self,
        x=0.0,
        y=0.0,
        finger_count=2,
        gate_length=0.2,
        gate_width=20.0,
        source_gate_spacing=1.5,
        gate_drain_spacing=2.0,
        ohmic_width=4.0,
        ohmic_overhang=2.0,
        gate_overhang=1.0,
        gate_head_length=4.0,
        mesa_width=0.0,
        mesa_margin_x=3.0,
        mesa_margin_y=3.0,
        dielectric_margin=0.3,
        draw_gate_dielectric=False,
        fanout_length=8.0,
        pad_size=45.0,
        pad_spacing=8.0,
        gate_pad_offset=0.0,
        hollow_fanout=False,
        fanout_wall_width=3.0,
        gate_fanout_contact_width=0.0,
        gate_fanout_pad_width=0.0,
        vertical_fanout_contact_width=0.0,
        vertical_fanout_pad_width=34.0,
        gate_control_margin=1.0,
        device_label="HEMT1",
        show_device_label=True,
        show_parameter_label=False,
        mark_mode="none",
        mark_shape="cross",
        mark_size=20.0,
        mark_width=2.0,
        mark_margin_x=15.0,
        mark_margin_y=15.0,
        **_kwargs,
    ):
        self.x = float(x)
        self.y = float(y)
        self.finger_count = int(finger_count)
        self.gate_length = float(gate_length)
        self.gate_width = float(gate_width)
        self.source_gate_spacing = float(source_gate_spacing)
        self.gate_drain_spacing = float(gate_drain_spacing)
        self.ohmic_width = float(ohmic_width)
        self.ohmic_overhang = float(ohmic_overhang)
        self.gate_overhang = float(gate_overhang)
        self.gate_head_length = float(gate_head_length)
        self.mesa_width = float(mesa_width)
        self.mesa_margin_x = float(mesa_margin_x)
        self.mesa_margin_y = float(mesa_margin_y)
        self.dielectric_margin = float(dielectric_margin)
        self.draw_gate_dielectric = bool(draw_gate_dielectric)
        self.fanout_length = float(fanout_length)
        self.pad_size = float(pad_size)
        self.pad_spacing = float(pad_spacing)
        self.gate_pad_offset = float(gate_pad_offset)
        self.hollow_fanout = bool(hollow_fanout)
        self.fanout_wall_width = float(fanout_wall_width)
        self.gate_fanout_contact_width = float(gate_fanout_contact_width)
        self.gate_fanout_pad_width = float(gate_fanout_pad_width)
        self.vertical_fanout_contact_width = float(vertical_fanout_contact_width)
        self.vertical_fanout_pad_width = float(vertical_fanout_pad_width)
        self.gate_control_margin = float(gate_control_margin)
        self.device_label = str(device_label)
        self.show_device_label = bool(show_device_label)
        self.show_parameter_label = bool(show_parameter_label)
        self.mark_mode = str(mark_mode)
        self.mark_shape = str(mark_shape)
        self.mark_size = float(mark_size)
        self.mark_width = float(mark_width)
        self.mark_margin_x = float(mark_margin_x)
        self.mark_margin_y = float(mark_margin_y)

        self.shapes = {
            "channel": [],
            "source": [],
            "drain": [],
            "gate": [],
            "gate_dielectric": [],
            "labels": [],
            "parameter_labels": [],
            "alignment_marks": [],
        }
        self._validate()

    def _validate(self):
        if self.finger_count not in (1, 2):
            raise ValueError("HEMT finger_count must be 1 or 2")
        positive = {
            "gate_length": self.gate_length,
            "gate_width": self.gate_width,
            "source_gate_spacing": self.source_gate_spacing,
            "gate_drain_spacing": self.gate_drain_spacing,
            "ohmic_width": self.ohmic_width,
            "gate_head_length": self.gate_head_length,
            "fanout_length": self.fanout_length,
            "pad_size": self.pad_size,
            "mark_size": self.mark_size,
            "mark_width": self.mark_width,
        }
        invalid = [name for name, value in positive.items() if value <= 0.0]
        if invalid:
            raise ValueError("HEMT dimensions must be positive: " + ", ".join(invalid))
        nonnegative = {
            "ohmic_overhang": self.ohmic_overhang,
            "gate_overhang": self.gate_overhang,
            "mesa_margin_x": self.mesa_margin_x,
            "mesa_margin_y": self.mesa_margin_y,
            "mesa_width": self.mesa_width,
            "dielectric_margin": self.dielectric_margin,
            "pad_spacing": self.pad_spacing,
            "gate_pad_offset": self.gate_pad_offset,
            "fanout_wall_width": self.fanout_wall_width,
            "gate_fanout_contact_width": self.gate_fanout_contact_width,
            "gate_fanout_pad_width": self.gate_fanout_pad_width,
            "vertical_fanout_contact_width": self.vertical_fanout_contact_width,
            "mark_margin_x": self.mark_margin_x,
            "mark_margin_y": self.mark_margin_y,
            "gate_control_margin": self.gate_control_margin,
        }
        invalid = [name for name, value in nonnegative.items() if value < 0.0]
        if invalid:
            raise ValueError("HEMT dimensions cannot be negative: " + ", ".join(invalid))
        positive_fanout = {"vertical_fanout_pad_width": self.vertical_fanout_pad_width}
        invalid = [name for name, value in positive_fanout.items() if value <= 0.0]
        if invalid:
            raise ValueError("HEMT fanout edge widths must be positive: " + ", ".join(invalid))
        if self.mark_mode not in ("none", "four_corners", "corners_and_sides"):
            raise ValueError("HEMT mark_mode must be none, four_corners, or corners_and_sides")
        if self.mark_shape not in ("cross", "box", "diamond"):
            raise ValueError("HEMT mark_shape must be cross, box, or diamond")

    @staticmethod
    def _coord(value):
        return int(round(value * _DBU_PER_UM))

    @classmethod
    def _box(cls, x1, y1, x2, y2):
        return pya.Box(cls._coord(x1), cls._coord(y1), cls._coord(x2), cls._coord(y2))

    @classmethod
    def _center_box(cls, cx, cy, width, height):
        return cls._box(cx - width / 2.0, cy - height / 2.0, cx + width / 2.0, cy + height / 2.0)

    @classmethod
    def _taper(cls, x1, y1, width1, x2, y2, width2):
        """Return a horizontal four-point taper between two vertical edges."""
        return pya.Polygon(
            [
                pya.Point(cls._coord(x1), cls._coord(y1 - width1 / 2.0)),
                pya.Point(cls._coord(x1), cls._coord(y1 + width1 / 2.0)),
                pya.Point(cls._coord(x2), cls._coord(y2 + width2 / 2.0)),
                pya.Point(cls._coord(x2), cls._coord(y2 - width2 / 2.0)),
            ]
        )

    @classmethod
    def _vertical_taper(cls, x1, y1, width1, x2, y2, width2):
        """Return a vertical four-point taper between two horizontal edges."""
        return pya.Polygon(
            [
                pya.Point(cls._coord(x1 - width1 / 2.0), cls._coord(y1)),
                pya.Point(cls._coord(x1 + width1 / 2.0), cls._coord(y1)),
                pya.Point(cls._coord(x2 + width2 / 2.0), cls._coord(y2)),
                pya.Point(cls._coord(x2 - width2 / 2.0), cls._coord(y2)),
            ]
        )

    def _fanout_shape(self, polygon):
        """Return a solid taper or a conductive hollow trapezoid frame."""
        if not self.hollow_fanout or self.fanout_wall_width <= 0.0:
            return polygon
        outer = pya.Region(polygon)
        inset = outer.sized(-self._coord(self.fanout_wall_width))
        if inset.is_empty():
            return polygon
        return outer - inset

    def get_layer_ids(self):
        return {
            "channel": LAYER_DEFINITIONS["channel"]["id"],
            "source": LAYER_DEFINITIONS["source_drain"]["id"],
            "drain": LAYER_DEFINITIONS["source_drain"]["id"],
            "gate": LAYER_DEFINITIONS["top_gate"]["id"],
            "gate_dielectric": LAYER_DEFINITIONS["top_dielectric"]["id"],
            "labels": LAYER_DEFINITIONS["labels"]["id"],
            "parameter_labels": LAYER_DEFINITIONS.get("note", LAYER_DEFINITIONS["labels"])["id"],
            "alignment_marks": LAYER_DEFINITIONS["alignment_marks"]["id"],
        }

    def _alignment_mark(self, cx, cy):
        half = self.mark_size / 2.0
        if self.mark_shape == "diamond":
            return pya.Polygon(
                [
                    pya.Point(self._coord(cx), self._coord(cy + half)),
                    pya.Point(self._coord(cx + half), self._coord(cy)),
                    pya.Point(self._coord(cx), self._coord(cy - half)),
                    pya.Point(self._coord(cx - half), self._coord(cy)),
                ]
            )
        if self.mark_shape == "box":
            outer = pya.Region(self._center_box(cx, cy, self.mark_size, self.mark_size))
            inner_size = self.mark_size - 2.0 * self.mark_width
            if inner_size <= 0.0:
                return outer
            return outer - pya.Region(self._center_box(cx, cy, inner_size, inner_size))
        horizontal = pya.Region(self._center_box(cx, cy, self.mark_size, self.mark_width))
        vertical = pya.Region(self._center_box(cx, cy, self.mark_width, self.mark_size))
        return (horizontal + vertical).merged()

    def _append_alignment_marks(self):
        if self.mark_mode == "none":
            return
        device_region = pya.Region()
        for name in ("channel", "source", "drain", "gate", "gate_dielectric"):
            for shape in self.shapes[name]:
                if isinstance(shape, pya.Region):
                    device_region += shape
                else:
                    device_region.insert(shape)
        bbox = device_region.bbox()
        left = bbox.left / _DBU_PER_UM - self.mark_margin_x
        right = bbox.right / _DBU_PER_UM + self.mark_margin_x
        bottom = bbox.bottom / _DBU_PER_UM - self.mark_margin_y
        top = bbox.top / _DBU_PER_UM + self.mark_margin_y
        center_x = (left + right) / 2.0
        center_y = (bottom + top) / 2.0
        positions = [(left, bottom), (left, top), (right, bottom), (right, top)]
        if self.mark_mode == "corners_and_sides":
            positions.extend([(center_x, bottom), (center_x, top), (left, center_y), (right, center_y)])
        self.shapes["alignment_marks"] = [self._alignment_mark(px, py) for px, py in positions]

    def _vertical_geometry(self):
        """Return gate, source and drain centre lines relative to device y."""
        sg = self.source_gate_spacing + (self.ohmic_width + self.gate_length) / 2.0
        gd = self.gate_drain_spacing + (self.ohmic_width + self.gate_length) / 2.0
        if self.finger_count == 1:
            # Centre a vertical D-G-S stack about y=0 even when access
            # spacings differ.  Keeping source above and drain below avoids
            # crossed connections to the compact outer metal fields.
            drain_y = 0.0
            gate_y = gd
            source_y = gd + sg
            offset = (source_y + drain_y) / 2.0
            return [gate_y - offset], [source_y - offset], [drain_y - offset]

        gate_y = self.ohmic_width / 2.0 + self.gate_drain_spacing + self.gate_length / 2.0
        source_y = gate_y + self.gate_length / 2.0 + self.source_gate_spacing + self.ohmic_width / 2.0
        return [-gate_y, gate_y], [-source_y, source_y], [0.0]

    def generate(self):
        """Generate and return geometry buckets keyed by process role."""
        for bucket in self.shapes.values():
            bucket[:] = []

        gate_ys, source_ys, drain_ys = self._vertical_geometry()
        gate_ys = [self.y + value for value in gate_ys]
        source_ys = [self.y + value for value in source_ys]
        drain_ys = [self.y + value for value in drain_ys]

        core_left = self.x - self.gate_width / 2.0
        core_right = self.x + self.gate_width / 2.0
        # Stop the ohmics at the active span's left edge so they cannot short
        # to the vertical gate manifold.  The adjustable overhang is placed at
        # the free (drain-pad) side of the fingers.
        ohmic_left = core_left - self.ohmic_overhang if self.finger_count == 1 else core_left
        ohmic_right = core_right + self.ohmic_overhang

        all_core_ys = source_ys + drain_ys + gate_ys
        core_bottom = min(all_core_ys) - max(self.ohmic_width, self.gate_length) / 2.0
        core_top = max(all_core_ys) + max(self.ohmic_width, self.gate_length) / 2.0
        if self.mesa_width > 0.0:
            mesa_half_x = self.mesa_width / 2.0
        else:
            mesa_half_x = max(self.x - ohmic_left, ohmic_right - self.x) + self.mesa_margin_x
        mesa_half_y = max(self.y - core_bottom, core_top - self.y) + self.mesa_margin_y
        mesa_left = self.x - mesa_half_x
        mesa_right = self.x + mesa_half_x
        mesa_bottom = self.y - mesa_half_y
        mesa_top = self.y + mesa_half_y
        self.shapes["channel"].append(
            self._box(mesa_left, mesa_bottom, mesa_right, mesa_top)
        )

        # Gate fingers and the shared left-side gate head/manifold.
        gate_left = min(core_left - self.gate_head_length, mesa_left - self.gate_overhang)
        gate_right = max(core_right + self.gate_overhang, mesa_right + self.gate_overhang, ohmic_right)
        if self.finger_count == 1:
            # Make the complete left/right gate system mirror-symmetric about
            # the requested device centre.  The half-span also carries both
            # triangle tips beyond the S/D contact footprint.
            gate_half_span = max(self.x - gate_left, gate_right - self.x, ohmic_right - self.x)
            gate_left = self.x - gate_half_span
            gate_right = self.x + gate_half_span
        # The upper/lower ohmic landing and its fanout are generated later as
        # one trapezoid.  The double-finger centre drain is extended as a
        # narrow bar beyond the Mesa before it is allowed to widen, preventing
        # the drain fanout from touching the full-Mesa gate fingers.
        if self.finger_count == 2:
            for drain_y in drain_ys:
                self.shapes["drain"].append(
                    self._box(ohmic_left, drain_y - self.ohmic_width / 2.0, gate_right, drain_y + self.ohmic_width / 2.0)
                )
        for gate_y in gate_ys:
            self.shapes["gate"].append(self._box(gate_left, gate_y - self.gate_length / 2.0, gate_right, gate_y + self.gate_length / 2.0))
            if self.draw_gate_dielectric:
                margin = self.dielectric_margin
                self.shapes["gate_dielectric"].append(
                    self._box(gate_left - margin, gate_y - self.gate_length / 2.0 - margin, gate_right + margin, gate_y + self.gate_length / 2.0 + margin)
                )
        manifold_bottom = min(gate_ys) - self.gate_length / 2.0
        manifold_top = max(gate_ys) + self.gate_length / 2.0
        self.shapes["gate"].append(self._box(gate_left, manifold_bottom, core_left, manifold_top))

        # Compact filled outer metal, matching the HEMT micrograph topology.
        # The upper/lower fields connect from their long horizontal edges;
        # left/right fields connect from their short vertical edges.
        neck = self.fanout_length
        left_edge = gate_left - neck - self.pad_size - self.gate_pad_offset
        right_field_left = gate_right + neck
        right_edge = right_field_left + self.pad_size
        vertical_pad_half_span = max(self.x - left_edge, right_edge - self.x)
        vertical_pad_left = self.x - vertical_pad_half_span
        vertical_pad_right = self.x + vertical_pad_half_span
        pad_delta = self.pad_size + self.pad_spacing
        if self.finger_count == 1:
            source_pad_ys = [self.y + pad_delta]
            drain_pad_ys = [self.y - pad_delta]
        else:
            source_pad_ys = [self.y - pad_delta, self.y + pad_delta]
            drain_pad_ys = [self.y]

        # Filled left gate pad with a solid triangle/trapezoid transition.
        gate_pad_right = gate_left - neck
        self.shapes["gate"].append(self._box(left_edge, self.y - self.pad_size / 2.0, gate_pad_right, self.y + self.pad_size / 2.0))
        # Single-finger gates taper to a point by default.  A double-finger
        # gate must meet the full common manifold, so its contact side is a
        # finite edge and the transition is a trapezoid.
        gate_contact_width = self.gate_fanout_contact_width
        gate_pad_edge = self.gate_fanout_pad_width or self.pad_size
        if self.finger_count == 2:
            gate_contact_width = max(gate_contact_width, manifold_top - manifold_bottom)
        self.shapes["gate"].append(
            self._taper(
                gate_pad_right,
                self.y,
                gate_pad_edge,
                gate_left,
                (manifold_bottom + manifold_top) / 2.0,
                gate_contact_width,
            )
        )

        inner_center_x = self.x
        inner_long_width = ohmic_right - ohmic_left
        requested_contact_width = self.vertical_fanout_contact_width or inner_long_width
        max_contact_width = (mesa_right - mesa_left) - 2.0 * self.gate_control_margin
        if max_contact_width <= 0.0:
            raise ValueError("Gate Control Margin leaves no usable vertical contact width")
        contact_taper_width = min(requested_contact_width, max_contact_width)
        outer_taper_width = self.vertical_fanout_pad_width

        def append_long_edge_field(bucket, inner_y, pad_y):
            direction = 1.0 if pad_y > self.y else -1.0
            # Start at the channel-facing edge of the internal ohmic landing,
            # so the landing and all fanout metal form one trapezoid.  Stop at
            # the inner long edge of a separate solid rectangular outer pad.
            contact_edge_y = inner_y - direction * self.ohmic_width / 2.0
            outer_pad_inner_y = pad_y - direction * self.pad_size / 2.0
            contact_and_fanout = self._vertical_taper(
                inner_center_x,
                contact_edge_y,
                contact_taper_width,
                inner_center_x,
                outer_pad_inner_y,
                outer_taper_width,
            )
            self.shapes[bucket].append(self._fanout_shape(contact_and_fanout))
            self.shapes[bucket].append(
                self._center_box(self.x, pad_y, vertical_pad_right - vertical_pad_left, self.pad_size)
            )

        # Single finger uses one-piece source/drain trapezoids above and below.
        # Its gate is contacted through solid triangles on both sides.
        if self.finger_count == 1:
            append_long_edge_field("source", source_ys[0], source_pad_ys[0])
            append_long_edge_field("drain", drain_ys[0], drain_pad_ys[0])
            right_gate_pad = self._box(right_field_left, self.y - self.pad_size / 2.0, right_edge, self.y + self.pad_size / 2.0)
            self.shapes["gate"].append(right_gate_pad)
            self.shapes["gate"].append(
                self._taper(
                    gate_right,
                    gate_ys[0],
                    self.gate_fanout_contact_width,
                    right_field_left,
                    self.y,
                    gate_pad_edge,
                )
            )
        else:
            for source_y, pad_y in zip(source_ys, source_pad_ys):
                append_long_edge_field("source", source_y, pad_y)
            for drain_y, pad_y in zip(drain_ys, drain_pad_ys):
                self.shapes["drain"].append(
                        self._taper(gate_right, drain_y, self.ohmic_width, right_field_left, pad_y, self.pad_size)
                )
                self.shapes["drain"].append(
                    self._center_box(right_field_left + self.pad_size / 2.0, pad_y, self.pad_size, self.pad_size)
                )

        label_y = max(source_pad_ys + drain_pad_ys) + self.pad_size / 2.0 + 8.0
        if self.show_device_label and self.device_label:
            self.shapes["labels"].append(pya.Text(self.device_label, self._coord(left_edge), self._coord(label_y)))
        if self.show_parameter_label:
            text = "HEMT Nf={} Lg={:.3f}um Wg={:.2f}um".format(self.finger_count, self.gate_length, self.gate_width)
            self.shapes["parameter_labels"].append(pya.Text(text, self._coord(left_edge), self._coord(label_y - 7.0)))
        self._append_alignment_marks()
        return self.shapes

    def get_all_shapes(self):
        return dict(self.shapes)

    def create_cell(self, layout, cell_name="HEMT_Device"):
        """Create a populated KLayout cell using this generator's layers."""
        self.generate()
        cell = layout.create_cell(cell_name)
        layer_ids = self.get_layer_ids()
        for name, shapes in self.shapes.items():
            layer_index = layout.layer(layer_ids[name], 0)
            for shape in shapes:
                cell.shapes(layer_index).insert(shape)
        return cell
