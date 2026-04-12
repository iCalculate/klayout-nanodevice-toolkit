import pya


class InterdigitatedFETPCell(pya.PCellDeclarationHelper):
    def __init__(self):
        super(InterdigitatedFETPCell, self).__init__()

        self.param("device_cx", self.TypeDouble, "Center X (um)", default=0.0)
        self.param("device_cy", self.TypeDouble, "Center Y (um)", default=0.0)

        self.param(
            "finger_orientation",
            self.TypeInt,
            "Inner electrode orientation",
            default=0,
            choices=[["vertical", 0], ["horizontal", 1]],
        )
        self.param("channel_width", self.TypeDouble, "Channel width (um)", default=30.0)
        self.param("channel_height", self.TypeDouble, "Channel height (um)", default=18.0)
        self.param("finger_width", self.TypeDouble, "Finger width W (um)", default=2.0)
        self.param("finger_spacing", self.TypeDouble, "Finger spacing S (um)", default=2.0)
        self.param("finger_extension", self.TypeDouble, "Finger extension on bus side (um)", default=8.0)
        self.param("finger_far_extension", self.TypeDouble, "Finger extension on far side (um)", default=0.0)
        self.param("bus_width", self.TypeDouble, "Bus width (um)", default=6.0)

        self.param("sd_lead_length", self.TypeDouble, "Source/Drain lead length (um)", default=10.0)
        self.param("sd_pad_width", self.TypeDouble, "Source/Drain pad width (um)", default=18.0)
        self.param("sd_pad_height", self.TypeDouble, "Source/Drain pad height (um)", default=14.0)
        self.param("sd_pad_gap", self.TypeDouble, "Source/Drain pad-to-pad gap (um)", default=12.0)

        self.param(
            "gate_mode",
            self.TypeInt,
            "Gate cover mode",
            default=0,
            choices=[["global", 0], ["channel_only", 1]],
        )
        self.param("gate_margin_x", self.TypeDouble, "Gate X grow/shrink (um)", default=0.0)
        self.param("gate_margin_y", self.TypeDouble, "Gate Y grow/shrink (um)", default=0.0)
        self.param("gate_lead_width", self.TypeDouble, "Gate lead width (um)", default=8.0)
        self.param("gate_pad_width", self.TypeDouble, "Gate pad width (um)", default=18.0)
        self.param("gate_pad_height", self.TypeDouble, "Gate pad height (um)", default=14.0)
        self.param("gate_pad_gap", self.TypeDouble, "Gate pad gap (um)", default=10.0)

        self.param("channel_layer", self.TypeLayer, "Channel layer", default=pya.LayerInfo(14, 0))
        self.param("sd_layer", self.TypeLayer, "Source/Drain layer", default=pya.LayerInfo(16, 0))
        self.param("gate_layer", self.TypeLayer, "Gate layer", default=pya.LayerInfo(18, 0))

    def display_text_impl(self):
        orient = "V" if self.finger_orientation == 0 else "H"
        return (
            "InterdigitatedFETPCell"
            f"({orient}, W={self.finger_width}, S={self.finger_spacing})"
        )

    def coerce_parameters_impl(self):
        self.channel_width = max(self.channel_width, 0.5)
        self.channel_height = max(self.channel_height, 0.5)
        self.finger_width = max(self.finger_width, 0.1)
        self.finger_spacing = max(self.finger_spacing, 0.0)
        self.finger_extension = max(self.finger_extension, 0.0)
        self.finger_far_extension = max(self.finger_far_extension, 0.0)
        self.bus_width = max(self.bus_width, 0.2)
        self.sd_lead_length = max(self.sd_lead_length, 0.0)
        self.sd_pad_width = max(self.sd_pad_width, 1.0)
        self.sd_pad_height = max(self.sd_pad_height, 1.0)
        self.sd_pad_gap = max(self.sd_pad_gap, 0.0)
        self.gate_lead_width = max(self.gate_lead_width, 0.2)
        self.gate_pad_width = max(self.gate_pad_width, 1.0)
        self.gate_pad_height = max(self.gate_pad_height, 1.0)
        self.gate_pad_gap = max(self.gate_pad_gap, 0.2)

        slots = self._auto_slot_count()
        comb_span = slots * self.finger_width + max(slots - 1, 0) * self.finger_spacing
        if self.finger_orientation == 0:
            self.channel_width = max(self.channel_width, comb_span)
        else:
            self.channel_height = max(self.channel_height, comb_span)

    def produce_impl(self):
        layout = self.layout
        dbu = layout.dbu
        sd_shapes = self.cell.shapes(layout.layer(self.sd_layer))
        gate_shapes = self.cell.shapes(layout.layer(self.gate_layer))
        channel_shapes = self.cell.shapes(layout.layer(self.channel_layer))

        def to_iu(value_um):
            return int(round(value_um / dbu))

        cx = self.device_cx
        cy = self.device_cy

        channel_box = self._center_box(cx, cy, self.channel_width, self.channel_height)
        channel_shapes.insert(self._to_box(channel_box, to_iu))

        if self.finger_orientation == 0:
            geometry = self._build_vertical_geometry(cx, cy)
        else:
            geometry = self._build_horizontal_geometry(cx, cy)

        for box in geometry["sd_boxes"]:
            sd_shapes.insert(self._to_box(box, to_iu))

        for lead_box in geometry["lead_boxes"]:
            sd_shapes.insert(self._to_box(lead_box, to_iu))

        gate_region, gate_anchor_rect = self._gate_geometry(geometry, to_iu)
        gate_shapes.insert(gate_region)
        gate_shapes.insert(self._to_box(geometry["gate_pad_box"], to_iu))

        gate_center = self._rect_center(gate_anchor_rect)
        gate_anchor = self._anchor_on_rect(gate_anchor_rect, geometry["gate_pad_center"])
        gate_pad_anchor = self._anchor_on_rect(geometry["gate_pad_box"], gate_center)
        gate_shapes.insert(self._to_box(self._edge_aligned_lead_box(gate_pad_anchor, gate_anchor, self.gate_lead_width), to_iu))

    def _build_vertical_geometry(self, cx, cy):
        left = cx - self.channel_width / 2.0
        right = cx + self.channel_width / 2.0
        bottom = cy - self.channel_height / 2.0
        top = cy + self.channel_height / 2.0

        slot_count = self._auto_slot_count()
        finger_array_width = slot_count * self.finger_width + (slot_count - 1) * self.finger_spacing
        x0 = cx - finger_array_width / 2.0
        pitch = self.finger_width + self.finger_spacing

        top_finger_top = top + self.finger_extension
        top_finger_bottom = bottom - self.finger_far_extension
        bottom_finger_bottom = bottom - self.finger_extension
        bottom_finger_top = top + self.finger_far_extension

        top_bus_center_y = top_finger_top + self.bus_width / 2.0
        bottom_bus_center_y = bottom_finger_bottom - self.bus_width / 2.0

        active_left = left
        active_right = right

        boxes = [
            self._center_box((active_left + active_right) / 2.0, top_bus_center_y, active_right - active_left, self.bus_width),
            self._center_box((active_left + active_right) / 2.0, bottom_bus_center_y, active_right - active_left, self.bus_width),
        ]

        for index in range(slot_count):
            x_left = x0 + index * pitch
            x_center = x_left + self.finger_width / 2.0
            if index % 2 == 0:
                boxes.append(self._xy_box(x_left, top_finger_bottom, x_left + self.finger_width, top_finger_top))
            else:
                boxes.append(self._xy_box(x_left, bottom_finger_bottom, x_left + self.finger_width, bottom_finger_top))

        top_bus_top = top_bus_center_y + self.bus_width / 2.0
        bottom_bus_bottom = bottom_bus_center_y - self.bus_width / 2.0

        pad_stack_height = 2 * self.sd_pad_height + self.sd_pad_gap
        source_pad_bottom = cy - pad_stack_height / 2.0
        drain_pad_bottom = source_pad_bottom + self.sd_pad_height + self.sd_pad_gap
        pad_right = active_left - self.sd_lead_length

        source_pad_box = self._xy_box(
            pad_right - self.sd_pad_width,
            source_pad_bottom,
            pad_right,
            source_pad_bottom + self.sd_pad_height,
        )
        drain_pad_box = self._xy_box(
            pad_right - self.sd_pad_width,
            drain_pad_bottom,
            pad_right,
            drain_pad_bottom + self.sd_pad_height,
        )
        gate_pad_center = (
            active_right + self.gate_pad_gap + self.gate_pad_width / 2.0,
            cy,
        )
        gate_pad_box = self._center_box(gate_pad_center[0], gate_pad_center[1], self.gate_pad_width, self.gate_pad_height)
        boxes.extend([source_pad_box, drain_pad_box])

        lead_boxes = []
        lead_boxes.extend(self._left_pad_to_hbus_leads(source_pad_box, active_left, bottom_bus_bottom, self.bus_width))
        lead_boxes.extend(self._left_pad_to_hbus_leads(drain_pad_box, active_left, top_bus_top - self.bus_width, self.bus_width))

        active_bottom = min(bottom_finger_bottom, bottom_bus_center_y - self.bus_width / 2.0)
        active_top = max(top_finger_top, top_bus_center_y + self.bus_width / 2.0)

        finger_active_box = self._xy_box(x0, min(bottom_finger_bottom, top_finger_bottom), x0 + finger_array_width, max(bottom_finger_top, top_finger_top))

        return {
            "orientation": "vertical",
            "sd_boxes": boxes,
            "lead_boxes": lead_boxes,
            "channel_box": self._center_box(cx, cy, self.channel_width, self.channel_height),
            "active_box": self._xy_box(active_left, active_bottom, active_right, active_top),
            "finger_active_box": finger_active_box,
            "finger_boxes": boxes[2:-2],
            "gate_pad_box": gate_pad_box,
            "gate_pad_center": gate_pad_center,
        }

    def _build_horizontal_geometry(self, cx, cy):
        left = cx - self.channel_width / 2.0
        right = cx + self.channel_width / 2.0
        bottom = cy - self.channel_height / 2.0
        top = cy + self.channel_height / 2.0

        slot_count = self._auto_slot_count()
        finger_array_height = slot_count * self.finger_width + (slot_count - 1) * self.finger_spacing
        y0 = cy - finger_array_height / 2.0
        pitch = self.finger_width + self.finger_spacing

        right_finger_right = right + self.finger_extension
        right_finger_left = left - self.finger_far_extension
        left_finger_left = left - self.finger_extension
        left_finger_right = right + self.finger_far_extension

        right_bus_center_x = right_finger_right + self.bus_width / 2.0
        left_bus_center_x = left_finger_left - self.bus_width / 2.0

        active_bottom = bottom
        active_top = top

        boxes = [
            self._center_box(left_bus_center_x, (active_bottom + active_top) / 2.0, self.bus_width, active_top - active_bottom),
            self._center_box(right_bus_center_x, (active_bottom + active_top) / 2.0, self.bus_width, active_top - active_bottom),
        ]

        for index in range(slot_count):
            y_bottom = y0 + index * pitch
            y_center = y_bottom + self.finger_width / 2.0
            if index % 2 == 0:
                boxes.append(self._xy_box(left_finger_left, y_bottom, left_finger_right, y_bottom + self.finger_width))
            else:
                boxes.append(self._xy_box(right_finger_left, y_bottom, right_finger_right, y_bottom + self.finger_width))

        left_bus_left = left_bus_center_x - self.bus_width / 2.0
        right_bus_right = right_bus_center_x + self.bus_width / 2.0

        pad_stack_width = 2 * self.sd_pad_width + self.sd_pad_gap
        source_pad_left = cx - pad_stack_width / 2.0
        drain_pad_left = source_pad_left + self.sd_pad_width + self.sd_pad_gap
        pad_top = active_bottom - self.sd_lead_length

        source_pad_box = self._xy_box(
            source_pad_left,
            pad_top - self.sd_pad_height,
            source_pad_left + self.sd_pad_width,
            pad_top,
        )
        drain_pad_box = self._xy_box(
            drain_pad_left,
            pad_top - self.sd_pad_height,
            drain_pad_left + self.sd_pad_width,
            pad_top,
        )
        gate_pad_center = (
            cx,
            active_top + self.gate_pad_gap + self.gate_pad_height / 2.0,
        )
        gate_pad_box = self._center_box(gate_pad_center[0], gate_pad_center[1], self.gate_pad_width, self.gate_pad_height)
        boxes.extend([source_pad_box, drain_pad_box])

        lead_boxes = []
        lead_boxes.extend(self._bottom_pad_to_vbus_leads(source_pad_box, left_bus_left, active_bottom, self.bus_width))
        lead_boxes.extend(self._bottom_pad_to_vbus_leads(drain_pad_box, right_bus_right - self.bus_width, active_bottom, self.bus_width))

        active_left = min(left_finger_left, left_bus_center_x - self.bus_width / 2.0)
        active_right = max(right_finger_right, right_bus_center_x + self.bus_width / 2.0)

        finger_active_box = self._xy_box(min(left_finger_left, right_finger_left), y0, max(left_finger_right, right_finger_right), y0 + finger_array_height)

        return {
            "orientation": "horizontal",
            "sd_boxes": boxes,
            "lead_boxes": lead_boxes,
            "channel_box": self._center_box(cx, cy, self.channel_width, self.channel_height),
            "active_box": self._xy_box(active_left, active_bottom, active_right, active_top),
            "finger_active_box": finger_active_box,
            "finger_boxes": boxes[2:-2],
            "gate_pad_box": gate_pad_box,
            "gate_pad_center": gate_pad_center,
        }

    def _gate_geometry(self, geometry, to_iu):
        if self.gate_mode == 0:
            target_box = geometry["channel_box"]
            grown = self._grow_box(target_box, self.gate_margin_x, self.gate_margin_y)
            region = pya.Region(self._to_box(grown, to_iu))
            return region, grown

        region, anchor_rect = self._build_channel_only_gate_region(geometry, to_iu)

        dx = to_iu(self.gate_margin_x)
        dy = to_iu(self.gate_margin_y)
        if dx != 0 or dy != 0:
            region = region.sized(dx, dy, 2)
        region = region.merged()
        bbox = region.bbox()
        grown_anchor = (
            bbox.left * self.layout.dbu,
            bbox.bottom * self.layout.dbu,
            bbox.right * self.layout.dbu,
            bbox.top * self.layout.dbu,
        )
        return region, grown_anchor

    def _build_channel_only_gate_region(self, geometry, to_iu):
        channel_box = geometry["channel_box"]
        fingers = [self._intersect_boxes(finger_box, channel_box) for finger_box in geometry["finger_boxes"]]
        fingers = [box for box in fingers if box is not None]

        if geometry["orientation"] == "vertical":
            gaps = self._vertical_gap_boxes(channel_box, fingers)
            region = pya.Region()
            for gap in gaps:
                region.insert(self._to_box(gap, to_iu))
            bridge_h = max(min(self.finger_spacing, self.channel_height / 3.0), 0.2)
            for idx in range(len(gaps) - 1):
                left_gap = gaps[idx]
                right_gap = gaps[idx + 1]
                if idx % 2 == 0:
                    bridge = self._xy_box(left_gap[2], channel_box[3] - bridge_h, right_gap[0], channel_box[3])
                else:
                    bridge = self._xy_box(left_gap[2], channel_box[1], right_gap[0], channel_box[1] + bridge_h)
                region.insert(self._to_box(bridge, to_iu))
            return region.merged(), channel_box

        gaps = self._horizontal_gap_boxes(channel_box, fingers)
        region = pya.Region()
        for gap in gaps:
            region.insert(self._to_box(gap, to_iu))
        bridge_w = max(min(self.finger_spacing, self.channel_width / 3.0), 0.2)
        for idx in range(len(gaps) - 1):
            lower_gap = gaps[idx]
            upper_gap = gaps[idx + 1]
            if idx % 2 == 0:
                bridge = self._xy_box(channel_box[2] - bridge_w, lower_gap[3], channel_box[2], upper_gap[1])
            else:
                bridge = self._xy_box(channel_box[0], lower_gap[3], channel_box[0] + bridge_w, upper_gap[1])
            region.insert(self._to_box(bridge, to_iu))
        return region.merged(), channel_box

    def _edge_aligned_lead_box(self, start_um, end_um, width_um):
        start_x, start_y = start_um
        end_x, end_y = end_um
        if abs(start_x - end_x) >= abs(start_y - end_y):
            y1 = min(start_y, end_y)
            y2 = y1 + width_um
            return self._xy_box(start_x, y1, end_x, y2)
        x1 = min(start_x, end_x)
        x2 = x1 + width_um
        return self._xy_box(x1, start_y, x2, end_y)

    def _anchor_on_rect(self, rect_box, target):
        cx = (rect_box[0] + rect_box[2]) / 2.0
        cy = (rect_box[1] + rect_box[3]) / 2.0
        half_w = max((rect_box[2] - rect_box[0]) / 2.0, 1e-6)
        half_h = max((rect_box[3] - rect_box[1]) / 2.0, 1e-6)
        dx = target[0] - cx
        dy = target[1] - cy
        if abs(dx) < 1e-9 and abs(dy) < 1e-9:
            return (cx + half_w, cy)
        scale = 1.0 / max(abs(dx) / half_w, abs(dy) / half_h)
        return (cx + dx * scale, cy + dy * scale)

    def _center_box(self, cx, cy, width, height):
        half_w = width / 2.0
        half_h = height / 2.0
        return (cx - half_w, cy - half_h, cx + half_w, cy + half_h)

    def _grow_box(self, box, grow_x, grow_y):
        return (box[0] - grow_x, box[1] - grow_y, box[2] + grow_x, box[3] + grow_y)

    def _xy_box(self, x1, y1, x2, y2):
        return (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))

    def _rect_center(self, box):
        return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)

    def _intersect_boxes(self, a, b):
        x1 = max(a[0], b[0])
        y1 = max(a[1], b[1])
        x2 = min(a[2], b[2])
        y2 = min(a[3], b[3])
        if x2 <= x1 or y2 <= y1:
            return None
        return (x1, y1, x2, y2)

    def _vertical_gap_boxes(self, channel_box, finger_boxes):
        left, bottom, right, top = channel_box
        xs = [left]
        sorted_fingers = sorted(finger_boxes, key=lambda b: b[0])
        for box in sorted_fingers:
            xs.extend([box[0], box[2]])
        xs.append(right)

        gaps = []
        cursor = left
        for box in sorted_fingers:
            if box[0] > cursor:
                gaps.append((cursor, bottom, box[0], top))
            cursor = max(cursor, box[2])
        if cursor < right:
            gaps.append((cursor, bottom, right, top))
        return [gap for gap in gaps if gap[2] - gap[0] > 1e-9]

    def _horizontal_gap_boxes(self, channel_box, finger_boxes):
        left, bottom, right, top = channel_box
        sorted_fingers = sorted(finger_boxes, key=lambda b: b[1])
        gaps = []
        cursor = bottom
        for box in sorted_fingers:
            if box[1] > cursor:
                gaps.append((left, cursor, right, box[1]))
            cursor = max(cursor, box[3])
        if cursor < top:
            gaps.append((left, cursor, right, top))
        return [gap for gap in gaps if gap[3] - gap[1] > 1e-9]

    def _auto_slot_count(self):
        span = self.channel_width if self.finger_orientation == 0 else self.channel_height
        usable = max(span, self.finger_width)
        pitch = self.finger_width + self.finger_spacing
        count = int((usable + self.finger_spacing) // pitch)
        return max(count, 2)

    def _left_pad_to_hbus_leads(self, pad_box, bus_left_x, bus_y_bottom, width):
        pad_right = pad_box[2]
        pad_mid_y = (pad_box[1] + pad_box[3]) / 2.0
        y1 = pad_mid_y - width / 2.0
        y2 = pad_mid_y + width / 2.0
        leads = [self._xy_box(pad_right, y1, bus_left_x, y2)]
        if abs(pad_mid_y - (bus_y_bottom + width / 2.0)) > 1e-9:
            vx1 = bus_left_x - width
            vx2 = bus_left_x
            vy1 = min(y1, bus_y_bottom)
            vy2 = max(y2, bus_y_bottom + width)
            leads.append(self._xy_box(vx1, vy1, vx2, vy2))
        return leads

    def _bottom_pad_to_vbus_leads(self, pad_box, bus_x_left, bus_bottom_y, width):
        pad_top = pad_box[3]
        pad_mid_x = (pad_box[0] + pad_box[2]) / 2.0
        x1 = pad_mid_x - width / 2.0
        x2 = pad_mid_x + width / 2.0
        leads = [self._xy_box(x1, pad_top, x2, bus_bottom_y)]
        if abs(pad_mid_x - (bus_x_left + width / 2.0)) > 1e-9:
            hy1 = bus_bottom_y
            hy2 = bus_bottom_y + width
            hx1 = min(x1, bus_x_left)
            hx2 = max(x2, bus_x_left + width)
            leads.append(self._xy_box(hx1, hy1, hx2, hy2))
        return leads

    def _to_box(self, box, to_iu):
        return pya.Box(to_iu(box[0]), to_iu(box[1]), to_iu(box[2]), to_iu(box[3]))
