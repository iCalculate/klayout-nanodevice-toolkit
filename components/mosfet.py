# -*- coding: utf-8 -*-
"""
Simplified MOSFET component used by LayoutGenerator.
"""

import pya
from config import PROCESS_CONFIG

DBU_PER_UM = int(1.0 / PROCESS_CONFIG['dbu'])


class MOSFET:
    """Simple MOSFET geometry builder."""

    def __init__(
        self,
        x=0.0,
        y=0.0,
        channel_width=5.0,
        channel_length=20.0,
        gate_overlap=2.0,
        device_label="D1",
        device_id=1,
        fanout_enabled=True,
        fanout_direction='horizontal',
        enable_bottom_gate=True,
        enable_top_gate=True,
        enable_source_drain=True,
        show_device_labels=True,
        show_parameter_labels=True,
        show_alignment_marks=True,
        **kwargs,
    ):
        self.x = x
        self.y = y
        self.channel_width = channel_width
        self.channel_length = channel_length
        self.gate_overlap = gate_overlap
        self.device_label = device_label
        self.device_id = device_id

        self.fanout_enabled = fanout_enabled
        self.fanout_direction = fanout_direction
        self.enable_bottom_gate = enable_bottom_gate
        self.enable_top_gate = enable_top_gate
        self.enable_source_drain = enable_source_drain
        self.show_device_labels = show_device_labels
        self.show_parameter_labels = show_parameter_labels
        self.show_alignment_marks = show_alignment_marks

        self.shapes = {
            'channel': [],
            'top_dielectric': [],
            'device_label': [],
            'parameter_labels': [],
            'alignment_marks': [],
        }
        self._component_shapes = {}

    def _dbu(self, um):
        return int(um * DBU_PER_UM)

    def _box_um(self, x_um, y_um, w_um, h_um, center=True):
        if center:
            return pya.Box(
                self._dbu(x_um - w_um / 2),
                self._dbu(y_um - h_um / 2),
                self._dbu(x_um + w_um / 2),
                self._dbu(y_um + h_um / 2),
            )
        return pya.Box(
            self._dbu(x_um),
            self._dbu(y_um),
            self._dbu(x_um + w_um),
            self._dbu(y_um + h_um),
        )

    def generate(self):
        x, y = self.x, self.y
        w, L = self.channel_width, self.channel_length
        overlap = self.gate_overlap

        ch_box = self._box_um(x, y, L, w, center=True)
        self.shapes['channel'] = [ch_box]

        diel_box = self._box_um(x, y, L + 2 * overlap, w + 2 * overlap, center=True)
        self.shapes['top_dielectric'] = [diel_box]

        half_L = L / 2
        half_w = w / 2
        gate_w = overlap * 2

        if self.enable_bottom_gate:
            bg_left = self._box_um(x - half_L - overlap, y, gate_w, w * 1.2, center=True)
            bg_right = self._box_um(x + half_L + overlap, y, gate_w, w * 1.2, center=True)
            self._component_shapes['bottom_gate'] = [bg_left, bg_right]
        else:
            self._component_shapes['bottom_gate'] = []

        if self.enable_source_drain:
            pad_ext = 5.0
            source_shapes = [self._box_um(x - half_L - pad_ext, y, pad_ext * 2, w * 1.2, center=True)]
            drain_shapes = [self._box_um(x + half_L + pad_ext, y, pad_ext * 2, w * 1.2, center=True)]

            if self.fanout_enabled:
                if self.fanout_direction == 'vertical':
                    source_shapes.append(self._box_um(x - half_L - pad_ext, y + 7.0, w * 0.8, 14.0, center=True))
                    drain_shapes.append(self._box_um(x + half_L + pad_ext, y + 7.0, w * 0.8, 14.0, center=True))
                else:
                    source_shapes.append(self._box_um(x - half_L - pad_ext - 7.0, y, 14.0, w * 0.8, center=True))
                    drain_shapes.append(self._box_um(x + half_L + pad_ext + 7.0, y, 14.0, w * 0.8, center=True))

            self._component_shapes['source'] = source_shapes
            self._component_shapes['drain'] = drain_shapes
        else:
            self._component_shapes['source'] = []
            self._component_shapes['drain'] = []

        if self.enable_top_gate:
            tg_box = self._box_um(x, y + half_w + overlap, L + 2 * overlap, gate_w, center=True)
            self._component_shapes['top_gate'] = [tg_box]
        else:
            self._component_shapes['top_gate'] = []

        if self.show_device_labels:
            label_box = self._box_um(x - half_L - 15, y + half_w + 12, 8, 4, center=False)
            self.shapes['device_label'] = [label_box]
        else:
            self.shapes['device_label'] = []

        if self.show_parameter_labels:
            param_box = self._box_um(x + half_L + 10, y - half_w - 8, 6, 3, center=False)
            self.shapes['parameter_labels'] = [param_box]
        else:
            self.shapes['parameter_labels'] = []

        if self.show_alignment_marks:
            mark_s = 8.0
            self.shapes['alignment_marks'] = [
                self._box_um(x - half_L - 30, y + half_w + 30, mark_s, mark_s, center=False),
                self._box_um(x + half_L + 30 - mark_s, y + half_w + 30, mark_s, mark_s, center=False),
                self._box_um(x - half_L - 30, y - half_w - 30 - mark_s, mark_s, mark_s, center=False),
                self._box_um(x + half_L + 30 - mark_s, y - half_w - 30 - mark_s, mark_s, mark_s, center=False),
            ]
        else:
            self.shapes['alignment_marks'] = []

    def get_all_shapes(self):
        return dict(self._component_shapes)

    def get_device_info(self):
        return {
            'device_id': self.device_id,
            'channel_width': self.channel_width,
            'channel_length': self.channel_length,
            'gate_overlap': self.gate_overlap,
            'device_label': self.device_label,
        }
