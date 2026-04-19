# KLayout Nanodevice Toolkit 中文说明

根目录的 [README](../README.md) 现在是项目的英文主入口，这份文档保留中文导航，帮助你快速找到正确的使用方式。

## 项目是什么

这是一个面向 KLayout 与 Python 工作流的纳米器件版图工具包，主要覆盖：

- 参数化器件生成：MOSFET、FET、Hall bar、TLM、electrode、meander、resolution pattern
- 阵列与参数扫描：通过 `layout_generator.py` 批量生成版图
- 图形界面：通过 `gui_interface.py` 配置阵列、扫描参数和输出
- KLayout 宏与 PDK：位于 `lymtoolkit/`
- 灰度图与图像驱动结构：位于 `components/greyscale/`

## 常用入口

### Python 脚本入口

```bash
python main.py
```

### GUI 入口

```bash
python gui_interface.py
```

### 安装 KLayout 宏

```bash
.\lymtoolkit\install_lymtoolkit.bat
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
