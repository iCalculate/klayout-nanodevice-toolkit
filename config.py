# -*- coding: utf-8 -*-
"""
配置文件 - 定义全局参数和设置
Configuration file - defines global parameters and settings.
"""

# 工艺参数
# Process parameters
PROCESS_CONFIG = {
    'min_feature_size': 0.001,      # 最小特征尺寸 (μm)
    'min_spacing': 0.001,           # 最小间距 (μm)
    'min_overlap': 0.05,          # 最小重叠 (μm)
    'dbu': 0.001,                 # 数据库单位 (μm)
}

# 图层定义
# Layer definitions
LAYER_DEFINITIONS = {
    'bottom_gate': {'id': 1, 'name': 'Bottom Gate', 'color': 0xFF0000, 'description': '底栅电极'},
    'bottom_dielectric': {'id': 2, 'name': 'Bottom Dielectric', 'color': 0x00FF00, 'description': '底介电层'},
    'channel': {'id': 3, 'name': 'Channel', 'color': 0x0000FF, 'description': '沟道材料'},
    'source_drain': {'id': 4, 'name': 'Source/Drain', 'color': 0xFFFF00, 'description': '源漏电极'},
    'top_dielectric': {'id': 5, 'name': 'Top Dielectric', 'color': 0xFF00FF, 'description': '顶介电层'},
    'top_gate': {'id': 6, 'name': 'Top Gate', 'color': 0xFF8000, 'description': '顶栅电极'},
    'alignment_marks': {'id': 7, 'name': 'Alignment Marks', 'color': 0x00FFFF, 'description': '对准标记'},
    'alignment_layer1': {'id': 11, 'name': 'Alignment Layer 1', 'color': 0x00FF80, 'description': '套刻对准层1'},
    'alignment_layer2': {'id': 12, 'name': 'Alignment Layer 2', 'color': 0x80FF00, 'description': '套刻对准层2'},
    'labels': {'id': 8, 'name': 'Labels', 'color': 0xFFFFFF, 'description': '标签'},
    'pads': {'id': 9, 'name': 'Pads', 'color': 0x8000FF, 'description': '测试焊盘'},
    'routing': {'id': 10, 'name': 'Routing', 'color': 0xFF0080, 'description': '布线层'},
}

# 字体设置
# Font settings
FONT_CONFIG = {
    'default': {
        'family': 'Arial',
        'size': 2.0,
        'style': 'normal'
    },
    'title': {
        'family': 'Arial',
        'size': 3.0,
        'style': 'bold'
    },
    'small': {
        'family': 'Arial',
        'size': 1.0,
        'style': 'normal'
    },
    'large': {
        'family': 'Arial',
        'size': 4.0,
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
# Fanout configuration
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

# 套刻对准配置
# Alignment configuration
ALIGNMENT_CONFIG = {
    'caliper_size': 20.0,          # caliper标记尺寸 (μm)
    'caliper_width': 2.0,          # caliper线条宽度 (μm)
    'clearance': 5.0,              # 周围清空区域 (μm)
    'min_spacing': 10.0,           # 最小间距 (μm)
    'styles': {
        'cross': 'cross',          # 十字形
        'box': 'box',              # 方形
        'circle': 'circle',        # 圆形
        'diamond': 'diamond'       # 菱形
    }
}

# 默认缩放参数
# Default scaling parameters
DEFAULT_UNIT_SCALE = 1000      # 1 um = 1000 nm
DEFAULT_DBU = 0.001           # 1 dbu = 0.001 um = 1 nm 