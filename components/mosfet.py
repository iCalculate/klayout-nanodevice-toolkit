# -*- coding: utf-8 -*-
"""
MOSFET 器件组件模块 - 供 LayoutGenerator 使用的简化 MOSFET 版图生成
与 layout_generator 配合，生成可插入顶层 layout 的形状。
"""

import pya
from config import LAYER_DEFINITIONS, PROCESS_CONFIG

# 1 um = 1/dbu dbu
DBU_PER_UM = int(1.0 / PROCESS_CONFIG['dbu'])


class MOSFET:
    """供 LayoutGenerator 使用的 MOSFET 器件类。

    在给定 (x, y) 处生成底栅、源漏、顶栅、沟道、介电层、标签和对准标记等形状，
    通过 get_all_shapes() 和 shapes 提供给 layout_generator 插入到顶层 cell。
    """

    def __init__(self, x=0.0, y=0.0, channel_width=5.0, channel_length=20.0,
                 gate_overlap=2.0, device_label="D1", device_id=1,
                 fanout_enabled=True, fanout_direction='horizontal', **kwargs):
        self.x = x
        self.y = y
        self.channel_width = channel_width
        self.channel_length = channel_length
        self.gate_overlap = gate_overlap
        self.device_label = device_label
        self.device_id = device_id
        self.fanout_enabled = fanout_enabled
        self.fanout_direction = fanout_direction

        # 供 layout_generator 插入的形状：channel, top_dielectric, device_label, parameter_labels, alignment_marks
        self.shapes = {
            'channel': [],
            'top_dielectric': [],
            'device_label': [],
            'parameter_labels': [],
            'alignment_marks': [],
        }
        # 组件形状：get_all_shapes() 返回 bottom_gate, source, drain, top_gate
        self._component_shapes = {}

    def _dbu(self, um):
        """将微米转换为数据库单位 (dbu)。"""
        return int(um * DBU_PER_UM)

    def _box_um(self, x_um, y_um, w_um, h_um, center=True):
        """在 (x_um, y_um) 处创建 pya.Box，尺寸 w_um x h_um (um)，可选居中。"""
        s = DBU_PER_UM
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
        """生成所有层形状并填入 self.shapes 与 _component_shapes。"""
        x, y = self.x, self.y
        w, L = self.channel_width, self.channel_length
        overlap = self.gate_overlap

        # 沟道 (居中于 x, y)
        ch_box = self._box_um(x, y, L, w, center=True)
        self.shapes['channel'] = [ch_box]

        # 顶介电层 (略大于沟道)
        diel_box = self._box_um(x, y, L + 2 * overlap, w + 2 * overlap, center=True)
        self.shapes['top_dielectric'] = [diel_box]

        # 底栅：左右两段，与沟道重叠 gate_overlap
        half_L = L / 2
        half_w = w / 2
        gate_w = overlap * 2
        # 左底栅
        bg_left = self._box_um(x - half_L - overlap, y, gate_w, w * 1.2, center=True)
        # 右底栅
        bg_right = self._box_um(x + half_L + overlap, y, gate_w, w * 1.2, center=True)
        self._component_shapes['bottom_gate'] = [bg_left, bg_right]

        # 源漏：源在左、漏在右
        pad_ext = 5.0
        source_box = self._box_um(x - half_L - pad_ext, y, pad_ext * 2, w * 1.2, center=True)
        drain_box = self._box_um(x + half_L + pad_ext, y, pad_ext * 2, w * 1.2, center=True)
        self._component_shapes['source'] = [source_box]
        self._component_shapes['drain'] = [drain_box]

        # 顶栅：横跨沟道上方
        tg_box = self._box_um(x, y + half_w + overlap, L + 2 * overlap, gate_w, center=True)
        self._component_shapes['top_gate'] = [tg_box]

        # 简单标签：用一个小矩形占位 (layout_generator 若用 TextUtils 会覆盖或叠加)
        label_box = self._box_um(x - half_L - 15, y + half_w + 12, 8, 4, center=False)
        self.shapes['device_label'] = [label_box]

        # 参数标签占位
        param_box = self._box_um(x + half_L + 10, y - half_w - 8, 6, 3, center=False)
        self.shapes['parameter_labels'] = [param_box]

        # 四角对准标记 (L 形小矩形)
        mark_s = 8.0
        marks = [
            self._box_um(x - half_L - 30, y + half_w + 30, mark_s, mark_s, center=False),
            self._box_um(x + half_L + 30 - mark_s, y + half_w + 30, mark_s, mark_s, center=False),
            self._box_um(x - half_L - 30, y - half_w - 30 - mark_s, mark_s, mark_s, center=False),
            self._box_um(x + half_L + 30 - mark_s, y - half_w - 30 - mark_s, mark_s, mark_s, center=False),
        ]
        self.shapes['alignment_marks'] = marks

    def get_all_shapes(self):
        """返回组件名称到形状列表的映射，供 layout_generator 按层插入。"""
        return dict(self._component_shapes)

    def get_device_info(self):
        """返回器件信息字典。"""
        return {
            'device_id': self.device_id,
            'channel_width': self.channel_width,
            'channel_length': self.channel_length,
            'gate_overlap': self.gate_overlap,
            'device_label': self.device_label,
        }
