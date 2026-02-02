# -*- coding: utf-8 -*-
"""
通用纳米器件 PDK（Process Design Kit）层定义与注册。

层号约定：
- 1–9:  功能层（机械、活性区、标记、卡尺等）
- 10–19: 前道（gate / dielectric / channel）
- 20–29: 后道（contact、metal、spacer）
- 61–63: 对准（LineScan / ImgScan / Manual）

兼容 Python 3.11+ 与新版 gdsfactory（Pdk 要求 layers 为 LayerMap 子类）。
使用方式：
    from components.MyLayoutTemplate.pdk import LAYER, PDK
    PDK.activate()
    layer_tuple = gf.get_layer("MARK")  # 或 tuple(LAYER.MARK)
    layer_tuple = tuple(LAYER.MARK)     # (3, 0) 用于索引 layer[0], layer[1]
"""

from __future__ import annotations

import gdsfactory as gf
from gdsfactory.technology import LayerMap
from gdsfactory.typings import Layer


class GenericNanoDeviceLayerMap(LayerMap):
    """
    通用纳米器件 PDK 层映射（LayerMap 子类，满足新版 gdsfactory Pdk 校验）。
    - 1–9: 功能层
    - 10–19: 前道（bottom/mid/top gate & dielectric, N/P channel）
    - 20–29: 后道（N/P contact, Routing Metal 1–4, Spacer 1–4）
    - 61–63: 对准
    """

    # ----- 1–9 功能层 -----
    MECHANICAL: Layer = (1, 0)   # 样品机械轮廓 / Sample outline
    ACTIVE: Layer = (2, 0)       # 有效/活性区 / Active area
    MARK: Layer = (3, 0)         # 标记 / All marks
    MARK_FRAME: Layer = (4, 0)   # 标记十字框 / Crosshair frames
    CALIPER: Layer = (5, 0)      # 卡尺 / Calipers
    L6: Layer = (6, 0)
    L7: Layer = (7, 0)
    L8: Layer = (8, 0)
    L9: Layer = (9, 0)

    # ----- 10–19 前道 -----
    FE_BOTTOM_GATE: Layer = (10, 0)
    FE_BOTTOM_DIELEC: Layer = (11, 0)
    FE_N1_CHANNEL: Layer = (12, 0)
    FE_N2_CHANNEL: Layer = (13, 0)
    FE_P1_CHANNEL: Layer = (14, 0)
    FE_P2_CHANNEL: Layer = (15, 0)
    FE_MID_DIELEC: Layer = (16, 0)
    FE_MID_GATE: Layer = (17, 0)
    FE_TOP_DIELEC: Layer = (18, 0)
    FE_TOP_GATE: Layer = (19, 0)

    # ----- 20–29 后道 -----
    BE_N_CONTACT: Layer = (20, 0)
    BE_P_CONTACT: Layer = (21, 0)
    BE_M1: Layer = (22, 0)
    BE_SPACER1: Layer = (23, 0)
    BE_M2: Layer = (24, 0)
    BE_SPACER2: Layer = (25, 0)
    BE_M3: Layer = (26, 0)
    BE_SPACER3: Layer = (27, 0)
    BE_M4: Layer = (28, 0)
    BE_SPACER4: Layer = (29, 0)

    # ----- 对准 61–63 -----
    ALIGN_LINESCAN: Layer = (61, 0)   # Auto LineScan Align
    ALIGN_IMGSCAN: Layer = (62, 0)    # Auto ImgScan Align
    ALIGN_MANUAL: Layer = (63, 0)     # Manual Align


# 供本 PDK 及 mark_writefield_gdsfactory 等使用
LAYER = GenericNanoDeviceLayerMap

# 层名 -> (gdslayer, gdspurpose)，用于从 LayerMap 枚举成员解析出正确的 GDS 层号（新版 gdsfactory 枚举 .value 可能为 int）
LAYER_TUPLES = {
    "MECHANICAL": (1, 0), "ACTIVE": (2, 0), "MARK": (3, 0), "MARK_FRAME": (4, 0), "CALIPER": (5, 0),
    "L6": (6, 0), "L7": (7, 0), "L8": (8, 0), "L9": (9, 0),
    "FE_BOTTOM_GATE": (10, 0), "FE_BOTTOM_DIELEC": (11, 0), "FE_N1_CHANNEL": (12, 0), "FE_N2_CHANNEL": (13, 0),
    "FE_P1_CHANNEL": (14, 0), "FE_P2_CHANNEL": (15, 0), "FE_MID_DIELEC": (16, 0), "FE_MID_GATE": (17, 0),
    "FE_TOP_DIELEC": (18, 0), "FE_TOP_GATE": (19, 0),
    "BE_N_CONTACT": (20, 0), "BE_P_CONTACT": (21, 0), "BE_M1": (22, 0), "BE_SPACER1": (23, 0),
    "BE_M2": (24, 0), "BE_SPACER2": (25, 0), "BE_M3": (26, 0), "BE_SPACER3": (27, 0),
    "BE_M4": (28, 0), "BE_SPACER4": (29, 0),
    "ALIGN_LINESCAN": (61, 0), "ALIGN_IMGSCAN": (62, 0), "ALIGN_MANUAL": (63, 0),
}


# 注册并创建 PDK 实例（新版 gdsfactory 要求 layers 为 LayerMap 子类，不能为 dict）
PDK = gf.Pdk(
    name="nanodevice",
    layers=GenericNanoDeviceLayerMap,
)


def activate() -> None:
    """激活纳米器件 PDK，使 gf.get_layer(name) 等使用本 PDK 的层定义。"""
    PDK.activate()


# 模块加载时自动激活，便于 mark_writefield_gdsfactory 等直接使用 LAYER 默认值
activate()
