# -*- coding: utf-8 -*-
"""
配置文件 - 定义全局参数和设置
"""

# 工艺参数
PROCESS_CONFIG = {
    'min_feature_size': 0.1,      # 最小特征尺寸 (μm)
    'min_spacing': 0.1,           # 最小间距 (μm)
    'min_overlap': 0.05,          # 最小重叠 (μm)
    'dbu': 0.001,                 # 数据库单位 (μm)
}

# 图层定义
LAYER_DEFINITIONS = {
    'bottom_gate': {'id': 1, 'name': 'Bottom Gate', 'color': 0xFF0000, 'description': '底栅电极'},
    'channel_etch': {'id': 2, 'name': 'Channel Etch', 'color': 0x00FF00, 'description': '沟道材料刻蚀'},
    'source_drain': {'id': 3, 'name': 'Source/Drain', 'color': 0x0000FF, 'description': '源漏电极'},
    'dielectric': {'id': 4, 'name': 'Dielectric', 'color': 0xFFFF00, 'description': '介电层'},
    'top_gate': {'id': 5, 'name': 'Top Gate', 'color': 0xFF00FF, 'description': '顶栅电极'},
    'alignment_marks': {'id': 6, 'name': 'Alignment Marks', 'color': 0x00FFFF, 'description': '对准标记'},
    'labels': {'id': 7, 'name': 'Labels', 'color': 0xFFFFFF, 'description': '标签'},
    'pads': {'id': 8, 'name': 'Pads', 'color': 0xFF8000, 'description': '测试焊盘'},
    'routing': {'id': 9, 'name': 'Routing', 'color': 0x8000FF, 'description': '布线层'},
}

# 字体设置
FONT_CONFIG = {
    'default': {
        'family': 'Arial',
        'size': 5.0,
        'style': 'normal'
    },
    'title': {
        'family': 'Arial',
        'size': 8.0,
        'style': 'bold'
    },
    'small': {
        'family': 'Arial',
        'size': 3.0,
        'style': 'normal'
    }
}

# 标记形状定义
MARK_SHAPES = {
    'cross': 'cross',
    'square': 'square',
    'circle': 'circle',
    'diamond': 'diamond',
    'triangle': 'triangle',
    'L_shape': 'L_shape',
    'T_shape': 'T_shape'
}

# 电极形状定义
ELECTRODE_SHAPES = {
    'rectangle': 'rectangle',
    'rounded': 'rounded',
    'octagon': 'octagon',
    'ellipse': 'ellipse'
}

# 扇出配置
FANOUT_CONFIG = {
    'enabled': True,
    'pad_size': 50.0,             # 焊盘尺寸 (μm)
    'wire_width': 5.0,            # 引线宽度 (μm)
    'spacing': 20.0,              # 引线间距 (μm)
    'styles': {
        'straight': 'straight',   # 直线扇出
        'curved': 'curved',       # 曲线扇出
        'stepped': 'stepped'      # 阶梯扇出
    }
}

# 默认缩放参数
DEFAULT_UNIT_SCALE = 1000      # 1 um = 1000 nm
DEFAULT_DBU = 0.001           # 1 dbu = 0.001 um = 1 nm 