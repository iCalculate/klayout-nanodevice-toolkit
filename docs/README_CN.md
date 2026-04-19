# KLayout Nanodevice Toolkit 中文说明

根目录的 [README](../README.md) 现在是项目的英文主入口，这份文档保留中文导航，帮助你快速找到当前仍然维护的使用方式。

## 项目是什么

这是一个面向 KLayout 与 Python 工作流的纳米器件版图工具包，当前主要覆盖：

- 参数化器件生成：MOSFET、FET、Hall bar、TLM、electrode、meander、resolution pattern
- KLayout 图形界面、宏与 PDK：位于 `lymtoolkit/`
- Python 组件与工具函数：位于 `components/` 和 `utils/`
- 灰度图与图像驱动结构：位于 `components/greyscale/`

仓库根目录里旧的 `main.py`、`layout_generator.py`、`gui_interface.py` 已移除，避免和 `lymtoolkit` 中维护中的 GUI/工具链重复。

## 常用入口

### 安装 KLayout 工具包

```bash
.\lymtoolkit\install_lymtoolkit.bat
```

安装后在 KLayout 中打开：

```text
Tools -> NanoDevice -> NanoDevice GUI
```

## 环境安装

```bash
conda env create -f environment.yml
conda activate klayout-nanodevice-toolkit
pip install -r requirements.txt
```

当前仓库中的 `environment.yml` 已经使用 `python=3.11`。

## 输出位置

- GDS 文件：`output/`
- 灰度图输出：`output/grayscaleImg/`

## 建议优先阅读

- [English main README](../README.md)
- [环境配置说明](ENV_SETUP.md)
- [快速开始](QUICK_START.md)
- [KLayout 工具包说明](../lymtoolkit/README.md)
