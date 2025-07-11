# KLayout Semiconductor Device Layout Generator

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![KLayout](https://img.shields.io/badge/KLayout-0.28+-green.svg)](https://www.klayout.de/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.2.0-orange.svg)](https://github.com/yourusername/klayout-semiconductor-generator/releases)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](https://github.com/yourusername/klayout-semiconductor-generator)

[English](#english) | [中文](#chinese)

---

## English

### Overview

A comprehensive, modular KLayout Python script suite for rapid semiconductor device layout generation. This project provides a professional-grade solution for creating MOSFET arrays, parameter sweeps, and complex device structures with integrated alignment marks, text annotations, and fanout routing.

### 🚀 Key Features

- **Modular Architecture**: Clean separation of components, utilities, and configuration
- **Dual-Gate MOSFET Support**: Complete bottom and top gate electrode structures
- **Parameter Sweep Engine**: Grid, random, and custom parameter scanning capabilities
- **Advanced Fanout System**: Multiple routing styles (straight, curved, stepped)
- **Professional Marking System**: Comprehensive alignment marks and measurement tools
- **GUI Integration**: Native KLayout GUI interface with real-time preview
- **Multi-Language Support**: Built-in text utilities with multiple font styles
- **Process Documentation**: Integrated process notes and manufacturing guidelines

### 📋 Requirements

- **KLayout**: Version 0.28 or higher
- **Python**: 3.7 or higher
- **Operating System**: Windows, Linux, or macOS

### 🏗️ Project Structure

```
klayout-semiconductor-generator/
├── config.py                 # Global configuration and layer definitions
├── main.py                   # Main program entry point
├── layout_generator.py       # Core layout generation engine
├── gui_interface.py          # KLayout GUI integration
├── components/               # Device component modules
│   ├── __init__.py
│   ├── electrode.py          # Electrode components (gates, source/drain)
│   └── mosfet.py             # Complete MOSFET device implementation
├── utils/                    # Utility modules
│   ├── __init__.py
│   ├── geometry.py           # Geometric shape utilities
│   ├── text_utils.py         # Text rendering and annotation
│   ├── mark_utils.py         # Alignment and measurement marks
│   ├── fanout_utils.py       # Routing and fanout utilities
│   └── digital_utils.py      # Digital pattern generation
└── README.md                 # Project documentation
```

### 🎯 Core Components

#### 1. MOSFET Device (`components/mosfet.py`)
- **Dual-Gate Architecture**: Independent bottom and top gate electrodes
- **Source/Drain Design**: Configurable source and drain electrode structures
- **Dielectric Integration**: Built-in dielectric layer management
- **Alignment Marks**: Device-level alignment and measurement features
- **Parameter Labeling**: Automatic device parameter annotation

#### 2. Electrode System (`components/electrode.py`)
- **Multiple Shapes**: Rectangle, rounded, octagon, ellipse support
- **Configurable Fanout**: Straight, curved, and stepped routing options
- **Process Integration**: Manufacturing process notes and guidelines
- **Pad Generation**: Automatic test pad creation and management

#### 3. Geometry Utilities (`utils/geometry.py`)
- **Basic Shapes**: Rectangle, circle, polygon primitives
- **Complex Shapes**: Rounded rectangles, octagons, ellipses
- **Mark Patterns**: Cross, L-shape, T-shape, diamond, triangle marks
- **Routing Tools**: Advanced fanout and connection utilities

#### 4. Text System (`utils/text_utils.py`)
- **Multiple Fonts**: Default, title, and small font styles
- **Text Effects**: Bold, outline, and rotated text support
- **Multi-line Support**: Complex text layout and formatting
- **Parameter Display**: Automatic device parameter labeling

#### 5. Marking System (`utils/mark_utils.py`)
- **Alignment Marks**: Corner, center, and grid alignment patterns
- **Measurement Tools**: Distance and feature measurement marks
- **Process Marks**: Manufacturing and quality control indicators
- **Custom Patterns**: User-defined mark shapes and arrangements

### 🚀 Quick Start

#### 1. Basic Usage

```python
# Run the main program
exec(open('main.py').read())
```

#### 2. Create Device Array

```python
from layout_generator import LayoutGenerator

# Initialize generator
generator = LayoutGenerator()

# Configure array parameters
generator.set_array_config(
    rows=3, cols=3,
    spacing_x=100.0, spacing_y=100.0
)

# Set parameter sweep
generator.set_scan_config(
    channel_width_range=[3.0, 5.0, 7.0],
    channel_length_range=[10.0, 20.0, 30.0],
    scan_type='grid'
)

# Generate and save layout
generator.generate_layout()
generator.save_layout("device_array.gds")
generator.load_to_gui()
```

#### 3. Custom Device Creation

```python
from components.mosfet import MOSFET

# Create individual device
device = MOSFET(
    x=0, y=0,
    channel_width=5.0,
    channel_length=20.0,
    gate_overlap=2.0,
    device_label="Custom_Device",
    fanout_enabled=True
)

# Generate device layout
device.generate()
```

#### 4. GUI Interface

```python
from gui_interface import show_mosfet_layout_gui

# Launch GUI interface
show_mosfet_layout_gui()
```

### ⚙️ Configuration

#### Layer Definitions (`config.py`)

```python
LAYER_DEFINITIONS = {
    'bottom_gate': {'id': 1, 'name': 'Bottom Gate', 'color': 0xFF0000},
    'channel_etch': {'id': 2, 'name': 'Channel Etch', 'color': 0x00FF00},
    'source_drain': {'id': 3, 'name': 'Source/Drain', 'color': 0x0000FF},
    'dielectric': {'id': 4, 'name': 'Dielectric', 'color': 0xFFFF00},
    'top_gate': {'id': 5, 'name': 'Top Gate', 'color': 0xFF00FF},
    'alignment_marks': {'id': 6, 'name': 'Alignment Marks', 'color': 0x00FFFF},
    'labels': {'id': 7, 'name': 'Labels', 'color': 0xFFFFFF},
    'pads': {'id': 8, 'name': 'Pads', 'color': 0xFF8000},
    'routing': {'id': 9, 'name': 'Routing', 'color': 0x8000FF},
}
```

#### Process Parameters

```python
PROCESS_CONFIG = {
    'min_feature_size': 0.1,      # Minimum feature size (μm)
    'min_spacing': 0.1,           # Minimum spacing (μm)
    'min_overlap': 0.05,          # Minimum overlap (μm)
    'dbu': 0.001,                 # Database unit (μm)
}
```

### 🔧 Advanced Features

#### Parameter Sweep Types

1. **Grid Scan**: Systematic parameter variation in grid pattern
2. **Random Scan**: Random parameter combinations for statistical analysis
3. **Custom Scan**: User-defined parameter combinations

#### Fanout Styles

1. **Straight**: Direct routing to test pads
2. **Curved**: Smooth curved routing paths
3. **Stepped**: Multi-level stepped routing

#### Mark Types

1. **Alignment**: Corner and center alignment marks
2. **Measurement**: Distance and feature measurement tools
3. **Process**: Manufacturing quality indicators

### 🛠️ Development

#### Adding New Electrode Shapes

```python
@staticmethod
def create_custom_shape(x, y, width, height, **kwargs):
    """Create custom electrode shape"""
    # Implement custom shape logic
    pass
```

#### Creating New Device Types

```python
class CustomDevice(MOSFET):
    def __init__(self, x, y, **kwargs):
        super().__init__(x, y, **kwargs)
        # Add custom parameters
    
    def create_custom_component(self):
        """Create custom device component"""
        pass
```

#### Extending Scan Types

```python
elif scan_type == 'custom_scan':
    # Implement custom scanning logic
    pass
```

### 📊 Examples

The project includes several example layouts demonstrating different capabilities:

- **TEST_DIGITS_UTILS.gds**: Digital pattern generation examples
- **TEST_FANOUT_UTILS.gds**: Fanout routing demonstration
- **TEST_MARK_UTILS.gds**: Alignment and measurement mark examples

### 🐛 Troubleshooting

#### Common Issues

1. **Import Errors**: Check file paths and module imports
2. **Layer Conflicts**: Verify layer ID configuration
3. **GUI Loading**: Ensure KLayout version compatibility
4. **Parameter Errors**: Validate parameter ranges and types

#### Debug Tips

1. Use `print()` for debugging information
2. Check generated GDS files
3. Review KLayout error logs
4. Test modules individually

### 📈 Version History

- **v1.2.0**: Enhanced modular structure and extensibility
- **v1.1.0**: Added GUI interface and parameter sweep functionality
- **v1.0.0**: Initial release with basic dual-gate device arrays

### 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### 🤝 Contributing

We welcome contributions! Please feel free to submit issues and pull requests to improve this project.

---

## Chinese

### 概述

一个基于KLayout的模块化半导体器件版图生成器，提供专业的MOSFET阵列、参数扫描和复杂器件结构生成解决方案。集成对准标记、文本注释和扇出布线功能。

### 🚀 主要特性

- **模块化架构**: 清晰的组件、工具和配置分离
- **双栅MOSFET支持**: 完整的底栅和顶栅电极结构
- **参数扫描引擎**: 网格、随机和自定义参数扫描
- **高级扇出系统**: 多种布线样式（直线、曲线、阶梯）
- **专业标记系统**: 全面的对准标记和测量工具
- **GUI集成**: 原生KLayout GUI界面，实时预览
- **多语言支持**: 内置文本工具，多种字体样式
- **工艺文档**: 集成工艺说明和制造指南

### 📋 系统要求

- **KLayout**: 0.28或更高版本
- **Python**: 3.7或更高版本
- **操作系统**: Windows、Linux或macOS

### 🏗️ 项目结构

```
klayout-semiconductor-generator/
├── config.py                 # 全局配置和图层定义
├── main.py                   # 主程序入口
├── layout_generator.py       # 核心版图生成引擎
├── gui_interface.py          # KLayout GUI集成
├── components/               # 器件组件模块
│   ├── __init__.py
│   ├── electrode.py          # 电极组件（栅极、源漏极）
│   └── mosfet.py             # 完整MOSFET器件实现
├── utils/                    # 工具模块
│   ├── __init__.py
│   ├── geometry.py           # 几何形状工具
│   ├── text_utils.py         # 文本渲染和注释
│   ├── mark_utils.py         # 对准和测量标记
│   ├── fanout_utils.py       # 布线和扇出工具
│   └── digital_utils.py      # 数字图案生成
└── README.md                 # 项目文档
```

### 🎯 核心组件

#### 1. MOSFET器件 (`components/mosfet.py`)
- **双栅架构**: 独立的底栅和顶栅电极
- **源漏设计**: 可配置的源极和漏极电极结构
- **介电层集成**: 内置介电层管理
- **对准标记**: 器件级对准和测量功能
- **参数标注**: 自动器件参数注释

#### 2. 电极系统 (`components/electrode.py`)
- **多种形状**: 矩形、圆角、八边形、椭圆支持
- **可配置扇出**: 直线、曲线和阶梯布线选项
- **工艺集成**: 制造工艺说明和指南
- **焊盘生成**: 自动测试焊盘创建和管理

#### 3. 几何工具 (`utils/geometry.py`)
- **基础形状**: 矩形、圆形、多边形基元
- **复杂形状**: 圆角矩形、八边形、椭圆
- **标记图案**: 十字、L形、T形、菱形、三角形标记
- **布线工具**: 高级扇出和连接工具

#### 4. 文本系统 (`utils/text_utils.py`)
- **多种字体**: 默认、标题和小字体样式
- **文本效果**: 粗体、轮廓和旋转文本支持
- **多行支持**: 复杂文本布局和格式化
- **参数显示**: 自动器件参数标注

#### 5. 标记系统 (`utils/mark_utils.py`)
- **对准标记**: 角落、中心和网格对准图案
- **测量工具**: 距离和特征测量标记
- **工艺标记**: 制造和质量控制指示器
- **自定义图案**: 用户定义的标记形状和排列

### 🚀 快速开始

#### 1. 基本使用

```python
# 运行主程序
exec(open('main.py').read())
```

#### 2. 创建器件阵列

```python
from layout_generator import LayoutGenerator

# 初始化生成器
generator = LayoutGenerator()

# 配置阵列参数
generator.set_array_config(
    rows=3, cols=3,
    spacing_x=100.0, spacing_y=100.0
)

# 设置参数扫描
generator.set_scan_config(
    channel_width_range=[3.0, 5.0, 7.0],
    channel_length_range=[10.0, 20.0, 30.0],
    scan_type='grid'
)

# 生成并保存版图
generator.generate_layout()
generator.save_layout("device_array.gds")
generator.load_to_gui()
```

#### 3. 自定义器件创建

```python
from components.mosfet import MOSFET

# 创建单个器件
device = MOSFET(
    x=0, y=0,
    channel_width=5.0,
    channel_length=20.0,
    gate_overlap=2.0,
    device_label="Custom_Device",
    fanout_enabled=True
)

# 生成器件版图
device.generate()
```

#### 4. GUI界面

```python
from gui_interface import show_mosfet_layout_gui

# 启动GUI界面
show_mosfet_layout_gui()
```

### ⚙️ 配置

#### 图层定义 (`config.py`)

```python
LAYER_DEFINITIONS = {
    'bottom_gate': {'id': 1, 'name': 'Bottom Gate', 'color': 0xFF0000},
    'channel_etch': {'id': 2, 'name': 'Channel Etch', 'color': 0x00FF00},
    'source_drain': {'id': 3, 'name': 'Source/Drain', 'color': 0x0000FF},
    'dielectric': {'id': 4, 'name': 'Dielectric', 'color': 0xFFFF00},
    'top_gate': {'id': 5, 'name': 'Top Gate', 'color': 0xFF00FF},
    'alignment_marks': {'id': 6, 'name': 'Alignment Marks', 'color': 0x00FFFF},
    'labels': {'id': 7, 'name': 'Labels', 'color': 0xFFFFFF},
    'pads': {'id': 8, 'name': 'Pads', 'color': 0xFF8000},
    'routing': {'id': 9, 'name': 'Routing', 'color': 0x8000FF},
}
```

#### 工艺参数

```python
PROCESS_CONFIG = {
    'min_feature_size': 0.1,      # 最小特征尺寸 (μm)
    'min_spacing': 0.1,           # 最小间距 (μm)
    'min_overlap': 0.05,          # 最小重叠 (μm)
    'dbu': 0.001,                 # 数据库单位 (μm)
}
```

### 🔧 高级功能

#### 参数扫描类型

1. **网格扫描**: 网格模式的系统参数变化
2. **随机扫描**: 统计分析用的随机参数组合
3. **自定义扫描**: 用户定义的参数组合

#### 扇出样式

1. **直线**: 直接布线到测试焊盘
2. **曲线**: 平滑的曲线布线路径
3. **阶梯**: 多级阶梯布线

#### 标记类型

1. **对准**: 角落和中心对准标记
2. **测量**: 距离和特征测量工具
3. **工艺**: 制造质量指示器

### 🛠️ 开发

#### 添加新电极形状

```python
@staticmethod
def create_custom_shape(x, y, width, height, **kwargs):
    """创建自定义电极形状"""
    # 实现自定义形状逻辑
    pass
```

#### 创建新器件类型

```python
class CustomDevice(MOSFET):
    def __init__(self, x, y, **kwargs):
        super().__init__(x, y, **kwargs)
        # 添加自定义参数
    
    def create_custom_component(self):
        """创建自定义器件组件"""
        pass
```

#### 扩展扫描类型

```python
elif scan_type == 'custom_scan':
    # 实现自定义扫描逻辑
    pass
```

### 📊 示例

项目包含多个示例版图，展示不同功能：

- **TEST_DIGITS_UTILS.gds**: 数字图案生成示例
- **TEST_FANOUT_UTILS.gds**: 扇出布线演示
- **TEST_MARK_UTILS.gds**: 对准和测量标记示例

### 🐛 故障排除

#### 常见问题

1. **导入错误**: 检查文件路径和模块导入
2. **图层冲突**: 验证图层ID配置
3. **GUI加载**: 确保KLayout版本兼容性
4. **参数错误**: 验证参数范围和类型

#### 调试技巧

1. 使用 `print()` 输出调试信息
2. 检查生成的GDS文件
3. 查看KLayout错误日志
4. 单独测试各个模块

### 📈 版本历史

- **v1.2.0**: 增强模块化结构和可扩展性
- **v1.1.0**: 添加GUI界面和参数扫描功能
- **v1.0.0**: 初始版本，支持基本双栅器件阵列

### 📄 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件。

### 🤝 贡献

欢迎贡献！请随时提交问题和拉取请求来改进这个项目。 