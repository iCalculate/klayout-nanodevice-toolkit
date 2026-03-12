# Mark 版图命令行与配置说明

## 命令行调用

主脚本 `mark_writefield_gdsfactory.py` 支持通过**配置文件**和**命令行参数**生成不同尺寸的 mark 版图，无需改脚本。

### 基本用法

```bash
# 使用默认 10mm 参数，输出到 output/mark_writefield_array_<日期>.gds
python mark_writefield_gdsfactory.py

# 使用 5mm 配置生成
python mark_writefield_gdsfactory.py --config mark_writefield_gdsfactory_5mm.yaml

# 指定输出文件
python mark_writefield_gdsfactory.py --config mark_writefield_gdsfactory_5mm.yaml -o ../output/mark_5mm.gds

# 生成后不在 KLayout 中打开
python mark_writefield_gdsfactory.py --config mark_writefield_gdsfactory_5mm.yaml --no-show
```

### 命令行覆盖

在已有配置基础上，可用命令行覆盖部分参数（单位：um）：

```bash
python mark_writefield_gdsfactory.py --config mark_writefield_gdsfactory_5mm.yaml \
  --sample-width 5000 --sample-height 5000 \
  --active-width 3600 --active-height 3600 \
  --writefield-size 700 -o output/mark_5mm.gds
```

### 5mm 专用入口

在 `MyLayoutTemplate` 目录下可直接运行：

```bash
python run_mark_5mm.py
python run_mark_5mm.py -o ../../output/mark_5mm.gds --no-show
```

等价于带 `--config mark_writefield_gdsfactory_5mm.yaml` 调用主脚本。

## 5mm 配置说明（mark_writefield_gdsfactory_5mm.yaml）

- **样品外框**: 5000 × 5000 µm（5mm 见方）
- **有效曝光区**: 3500 × 3500 µm（四边各约 750 µm 边距）
- **写场**: 700 µm 边长，5×5 共 25 个写场
- 四角全局 mark 尺寸已按 5mm 片子比例缩小

可根据工艺需求直接编辑 `mark_writefield_gdsfactory_5mm.yaml` 中数值，或复制后另存为新配置（如 `mark_writefield_gdsfactory_5mm_v2.yaml`）再通过 `--config` 指定。

## 配置文件格式

- 支持 **YAML**（需安装 `pyyaml`）或 **JSON**。
- 键名与 `generate_writefield_array()` 参数名一致；元组类参数在 YAML/JSON 中写为列表，如 `mark_offset_from_corner: [80.0, 80.0]`。
- 未在配置中给出的参数使用脚本内默认值（图层等 PDK 相关参数一般无需在配置里写）。
