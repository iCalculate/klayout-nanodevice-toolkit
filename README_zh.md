# KLayout 半导体器件版图生成器

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![KLayout](https://img.shields.io/badge/KLayout-0.28+-green.svg)](https://www.klayout.de/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 概述

**KLayout 半导体器件版图生成器** 是一个模块化、可扩展的 Python 工具包，专为在 [KLayout](https://www.klayout.de/) 环境下实现高效、专业的半导体器件版图生成而设计。本项目简化了 MOSFET 阵列、参数扫描和复杂器件结构的创建，集成了对准标记、文本注释和灵活扇出布线等高级功能，适用于学术研究和工业原型设计。

---

## 主要特性

- **模块化架构**：器件组件、工具和配置分离，便于维护和扩展。
- **丰富的器件支持**：支持双栅 MOSFET、自定义电极形状和参数化器件阵列。
- **灵活的参数扫描引擎**：支持网格、随机和自定义参数扫描，适合系统性或统计性研究。
- **高级扇出与标记系统**：多种布线风格，专业的对准与测量标记。
- **无缝 KLayout GUI 集成**：原生界面，实时版图预览与交互设计。
- **多语言文本注释**：内置器件标注与文档工具。
- **工艺感知配置**：集中管理图层与工艺参数，确保设计规则合规。

---

## 目录

- [项目结构](#项目结构)
- [安装](#安装)
- [快速开始](#快速开始)
- [用法示例](#用法示例)
- [配置说明](#配置说明)
- [故障排查](#故障排查)
- [贡献方式](#贡献方式)
- [许可证](#许可证)
- [致谢](#致谢)

---

## 项目结构

```
klayout-nanodevice-toolkit/
├── main.py                # 主程序入口
├── layout_generator.py    # 核心版图引擎
├── gui_interface.py       # KLayout GUI 集成
├── components/            # 器件模块（MOSFET、电极等）
├── utils/                 # 几何、文本、标记、扇出工具
├── config.py              # 图层与工艺配置
└── README.md
```

---

## 安装

1. **环境要求**
   - [KLayout](https://www.klayout.de/) >= 0.28
   - Python >= 3.7

2. **克隆仓库**
   ```bash
   git clone https://github.com/yourusername/klayout-nanodevice-toolkit.git
   cd klayout-nanodevice-toolkit
   ```

3. **（可选）创建虚拟环境**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows 下为 venv\Scripts\activate
   ```

4. **安装依赖**
   > 绝大多数依赖为标准 Python 库。如有额外依赖，请在此或 `requirements.txt` 中列出。

---

## 快速开始

**运行主程序：**
```python
exec(open('main.py').read())
```

**创建器件阵列：**
```python
from layout_generator import LayoutGenerator

generator = LayoutGenerator()
generator.set_array_config(rows=3, cols=3, spacing_x=100, spacing_y=100)
generator.set_scan_config(channel_width_range=[3,5,7], channel_length_range=[10,20,30], scan_type='grid')
generator.generate_layout()
generator.save_layout("device_array.gds")
generator.load_to_gui()
```

---

## 用法示例

**自定义器件创建**
```python
from components.mosfet import MOSFET

device = MOSFET(
    x=0, y=0,
    channel_width=5.0,
    channel_length=20.0,
    gate_overlap=2.0,
    device_label="Custom_Device",
    fanout_enabled=True
)
device.generate()
```

**启动 KLayout GUI 界面**
```python
from gui_interface import show_mosfet_layout_gui
show_mosfet_layout_gui()
```

---

## 配置说明

所有全局设置、图层定义和工艺参数均在 `config.py` 中集中管理，包括：

- **图层定义**：为每个工艺步骤分配图层 ID、名称和颜色。
- **工艺参数**：设置最小特征尺寸、间距、重叠和数据库单位。
- **可扩展性**：通过扩展 `components/` 和 `utils/` 目录，轻松添加新器件类型或布线风格。

高级配置与扩展说明请参见 [详细文档](docs/README.md)。

---

## 故障排查

- **ImportError**：请确保 Python 路径和模块名正确。
- **图层冲突**：检查 `config.py` 中是否有重复或冲突的图层 ID。
- **GUI 问题**：请确保 KLayout 版本 >= 0.28。
- **参数错误**：请在脚本中校验参数范围和类型。

如遇问题，请查阅 [FAQ](docs/README.md#faq) 或提交 issue。

---

## 贡献方式

欢迎贡献！请阅读我们的 [贡献指南](CONTRIBUTING.md)，通过 Pull Request 或 Issue 参与项目改进。

---

## 许可证

本项目采用 MIT 许可证，详见 [LICENSE](LICENSE) 文件。

---

## 致谢

- 本项目基于优秀的 [KLayout](https://www.klayout.de/) 平台开发。
- 感谢开源 EDA 与器件设计社区的启发与支持。

---

> 更多高级用法、开发指南与 API 参考，请参见 [docs/README.md](docs/README.md)。 