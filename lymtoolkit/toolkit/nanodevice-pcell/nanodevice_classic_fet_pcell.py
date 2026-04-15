import math
import pya


class NanoDeviceClassicFETPCell(pya.PCellDeclarationHelper):
    def __init__(self):
        super(NanoDeviceClassicFETPCell, self).__init__()

        self.param("device_cx", self.TypeDouble, "Device center X (um)", default=0.0)
        self.param("device_cy", self.TypeDouble, "Device center Y (um)", default=0.0)

        self.param("active_width", self.TypeDouble, "Interdigitated region width (um)", default=80.0)
        self.param("active_height", self.TypeDouble, "Interdigitated region height (um)", default=60.0)
        self.param("channel_gap", self.TypeDouble, "Channel gap between source/drain fingers (um)", default=4.0)
        self.param("finger_width", self.TypeDouble, "Finger line width (um)", default=2.0)
        self.param("finger_spacing", self.TypeDouble, "Finger spacing (um)", default=2.0)
        self.param("finger_count", self.TypeInt, "Finger count", default=10)
        self.param("finger_head_length", self.TypeDouble, "Finger head length (um)", default=3.0)
        self.param("finger_head_overhang", self.TypeDouble, "Finger head width overhang per side (um)", default=0.5)
        self.param("sd_bus_width", self.TypeDouble, "Source/drain bus width inside active region (um)", default=8.0)
        self.param("outer_bus_width", self.TypeDouble, "Source/drain outer lead width (um)", default=12.0)

        self.param("source_pad_width", self.TypeDouble, "Source pad width (um)", default=60.0)
        self.param("source_pad_height", self.TypeDouble, "Source pad height (um)", default=60.0)
        self.param("source_pad_cx", self.TypeDouble, "Source pad center X (um)", default=-120.0)
        self.param("source_pad_cy", self.TypeDouble, "Source pad center Y (um)", default=0.0)

        self.param("drain_pad_width", self.TypeDouble, "Drain pad width (um)", default=60.0)
        self.param("drain_pad_height", self.TypeDouble, "Drain pad height (um)", default=60.0)
        self.param("drain_pad_cx", self.TypeDouble, "Drain pad center X (um)", default=120.0)
        self.param("drain_pad_cy", self.TypeDouble, "Drain pad center Y (um)", default=0.0)

        self.param(
            "gate_mode",
            self.TypeInt,
            "Gate cover mode",
            default=0,
            choices=[["global", 0], ["channel_only", 1]],
        )
        self.param("gate_x_offset", self.TypeDouble, "Gate X offset (um)", default=0.0)
        self.param("gate_y_offset", self.TypeDouble, "Gate Y offset (um)", default=0.0)
        self.param("gate_enclosure_x", self.TypeDouble, "Gate X grow/shrink (um)", default=0.0)
        self.param("gate_enclosure_y", self.TypeDouble, "Gate Y grow/shrink (um)", default=0.0)
        self.param("gate_lead_width", self.TypeDouble, "Gate outer lead width (um)", default=10.0)
        self.param("gate_pad_width", self.TypeDouble, "Gate pad width (um)", default=50.0)
        self.param("gate_pad_height", self.TypeDouble, "Gate pad height (um)", default=50.0)
        self.param("gate_pad_cx", self.TypeDouble, "Gate pad center X (um)", default=0.0)
        self.param("gate_pad_cy", self.TypeDouble, "Gate pad center Y (um)", default=110.0)

        self.param("sd_layer", self.TypeLayer, "Source/Drain layer", default=pya.LayerInfo(16, 0))
        self.param("gate_layer", self.TypeLayer, "Gate layer", default=pya.LayerInfo(18, 0))

    def display_text_impl(self):
        return "InterdigitatedFETOriginalNanoDevice"

    def coerce_parameters_impl(self):
        self.active_width = max(self.active_width, 2.0)
        self.active_height = max(self.active_height, 2.0)
        self.channel_gap = max(self.channel_gap, 0.2)
        self.finger_width = max(self.finger_width, 0.1)
        self.finger_spacing = max(self.finger_spacing, 0.0)
        self.finger_count = max(int(self.finger_count), 1)
        self.sd_bus_width = max(self.sd_bus_width, 0.2)
        self.outer_bus_width = max(self.outer_bus_width, 0.2)
        self.finger_head_length = max(self.finger_head_length, 0.0)
        self.finger_head_overhang = max(self.finger_head_overhang, 0.0)
        self.gate_lead_width = max(self.gate_lead_width, 0.2)
        self.source_pad_width = max(self.source_pad_width, 1.0)
        self.source_pad_height = max(self.source_pad_height, 1.0)
        self.drain_pad_width = max(self.drain_pad_width, 1.0)
        self.drain_pad_height = max(self.drain_pad_height, 1.0)
        self.gate_pad_width = max(self.gate_pad_width, 1.0)
        self.gate_pad_height = max(self.gate_pad_height, 1.0)

    def produce_impl(self):
        sd_layer = self.layout.layer(self.sd_layer)
        gate_layer = self.layout.layer(self.gate_layer)
        sd_shapes = self.cell.shapes(sd_layer)
        gate_shapes = self.cell.shapes(gate_layer)

        dbu = self.layout.dbu

        def to_iu(value_um):
            return int(round(value_um / dbu))

        cx = self.device_cx
        cy = self.device_cy
        left = cx - self.active_width / 2.0
        right = cx + self.active_width / 2.0
        bottom = cy - self.active_height / 2.0
        top = cy + self.active_height / 2.0

        side_span = max((self.active_width - self.channel_gap) / 2.0, 0.2)
        bus_width = min(self.sd_bus_width, side_span)

        source_bus_x1 = left
        source_bus_x2 = left + bus_width
        drain_bus_x1 = right - bus_width
        drain_bus_x2 = right

        source_finger_x1 = source_bus_x2
        source_finger_x2 = max(source_finger_x1, cx - self.channel_gap / 2.0)
        drain_finger_x1 = min(drain_bus_x1, cx + self.channel_gap / 2.0)
        drain_finger_x2 = drain_bus_x1

        source_bus = pya.Box(to_iu(source_bus_x1), to_iu(bottom), to_iu(source_bus_x2), to_iu(top))
        drain_bus = pya.Box(to_iu(drain_bus_x1), to_iu(bottom), to_iu(drain_bus_x2), to_iu(top))
        sd_shapes.insert(source_bus)
        sd_shapes.insert(drain_bus)

        pitch = self.finger_width + self.finger_spacing
        max_fit = max(1, int(math.floor((self.active_height + self.finger_spacing) / max(pitch, 1e-9))))
        finger_count = min(self.finger_count, max_fit)
        used_height = finger_count * self.finger_width + max(0, finger_count - 1) * self.finger_spacing
        y0 = cy - used_height / 2.0

        head_half_extra = self.finger_head_overhang
        head_length = min(self.finger_head_length, max(0.0, source_finger_x2 - source_finger_x1))
        drain_head_length = min(self.finger_head_length, max(0.0, drain_finger_x2 - drain_finger_x1))

        for index in range(finger_count):
            finger_y1 = y0 + index * pitch
            finger_y2 = finger_y1 + self.finger_width

            if index % 2 == 0:
                sd_shapes.insert(
                    pya.Box(
                        to_iu(source_finger_x1),
                        to_iu(finger_y1),
                        to_iu(source_finger_x2),
                        to_iu(finger_y2),
                    )
                )
                if head_length > 0:
                    sd_shapes.insert(
                        pya.Box(
                            to_iu(source_finger_x2 - head_length),
                            to_iu(finger_y1 - head_half_extra),
                            to_iu(source_finger_x2),
                            to_iu(finger_y2 + head_half_extra),
                        )
                    )
            else:
                sd_shapes.insert(
                    pya.Box(
                        to_iu(drain_finger_x1),
                        to_iu(finger_y1),
                        to_iu(drain_finger_x2),
                        to_iu(finger_y2),
                    )
                )
                if drain_head_length > 0:
                    sd_shapes.insert(
                        pya.Box(
                            to_iu(drain_finger_x1),
                            to_iu(finger_y1 - head_half_extra),
                            to_iu(drain_finger_x1 + drain_head_length),
                            to_iu(finger_y2 + head_half_extra),
                        )
                    )

        source_pad = self._make_box(self.source_pad_cx, self.source_pad_cy, self.source_pad_width, self.source_pad_height, to_iu)
        drain_pad = self._make_box(self.drain_pad_cx, self.drain_pad_cy, self.drain_pad_width, self.drain_pad_height, to_iu)
        sd_shapes.insert(source_pad)
        sd_shapes.insert(drain_pad)

        source_anchor = self._anchor_on_box_towards((left + bus_width / 2.0, cy), (bus_width, self.active_height), (self.source_pad_cx, self.source_pad_cy))
        drain_anchor = self._anchor_on_box_towards((right - bus_width / 2.0, cy), (bus_width, self.active_height), (self.drain_pad_cx, self.drain_pad_cy))
        source_pad_anchor = self._anchor_on_box_towards((self.source_pad_cx, self.source_pad_cy), (self.source_pad_width, self.source_pad_height), source_anchor)
        drain_pad_anchor = self._anchor_on_box_towards((self.drain_pad_cx, self.drain_pad_cy), (self.drain_pad_width, self.drain_pad_height), drain_anchor)
        self._insert_lead(sd_shapes, source_anchor, source_pad_anchor, self.outer_bus_width, to_iu)
        self._insert_lead(sd_shapes, drain_anchor, drain_pad_anchor, self.outer_bus_width, to_iu)

        gate_box = self._build_gate_box(to_iu)
        gate_shapes.insert(gate_box)
        gate_pad = self._make_box(self.gate_pad_cx, self.gate_pad_cy, self.gate_pad_width, self.gate_pad_height, to_iu)
        gate_shapes.insert(gate_pad)

        gate_center, gate_size = self._gate_geometry()
        gate_anchor = self._anchor_on_box_towards(gate_center, gate_size, (self.gate_pad_cx, self.gate_pad_cy))
        gate_pad_anchor = self._anchor_on_box_towards((self.gate_pad_cx, self.gate_pad_cy), (self.gate_pad_width, self.gate_pad_height), gate_anchor)
        self._insert_lead(gate_shapes, gate_anchor, gate_pad_anchor, self.gate_lead_width, to_iu)

    def _build_gate_box(self, to_iu):
        gate_center, gate_size = self._gate_geometry()
        return self._make_box(gate_center[0], gate_center[1], gate_size[0], gate_size[1], to_iu)

    def _gate_geometry(self):
        cx = self.device_cx + self.gate_x_offset
        cy = self.device_cy + self.gate_y_offset
        if self.gate_mode == 0:
            width = self.active_width + 2.0 * self.gate_enclosure_x
            height = self.active_height + 2.0 * self.gate_enclosure_y
        else:
            width = self.channel_gap + 2.0 * self.gate_enclosure_x
            height = self.active_height + 2.0 * self.gate_enclosure_y
        return (cx, cy), (max(width, 0.2), max(height, 0.2))

    def _make_box(self, cx, cy, width, height, to_iu):
        half_w = width / 2.0
        half_h = height / 2.0
        return pya.Box(
            to_iu(cx - half_w),
            to_iu(cy - half_h),
            to_iu(cx + half_w),
            to_iu(cy + half_h),
        )

    def _insert_lead(self, shapes, start_um, end_um, width_um, to_iu):
        points = [pya.Point(to_iu(start_um[0]), to_iu(start_um[1])), pya.Point(to_iu(end_um[0]), to_iu(end_um[1]))]
        lead = pya.Path(points, to_iu(width_um), 0, 0, False).polygon()
        shapes.insert(lead)

    def _anchor_on_box_towards(self, box_center, box_size, target):
        cx, cy = box_center
        half_w = max(box_size[0] / 2.0, 1e-6)
        half_h = max(box_size[1] / 2.0, 1e-6)
        dx = target[0] - cx
        dy = target[1] - cy
        if abs(dx) < 1e-9 and abs(dy) < 1e-9:
            return (cx, cy + half_h)
        scale = 1.0 / max(abs(dx) / half_w, abs(dy) / half_h)
        return (cx + dx * scale, cy + dy * scale)
