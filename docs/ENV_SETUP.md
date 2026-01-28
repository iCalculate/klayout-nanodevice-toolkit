# Conda 环境设置指南

本项目使用 conda 来管理独立的 Python 环境。

## 快速开始

### 1. 创建环境

运行以下命令创建 conda 环境：

```bash
conda env create -f environment.yml
```

**注意**: 如果 Python 11 在 conda 中不可用，脚本会提示您。您可能需要：
- 等待 conda-forge 更新支持 Python 11
- 或者修改 `environment.yml` 中的 `python=11` 为 `python=3.11` 或其他可用版本

### 2. 激活环境

#### 在命令行中激活：

```bash
conda activate klayout-nanodevice-toolkit
```

#### 在 VS Code/Cursor 中：

1. 打开项目文件夹
2. 按 `Ctrl+Shift+P` 打开命令面板
3. 输入 "Python: Select Interpreter"
4. 选择 `klayout-nanodevice-toolkit` 环境

或者，VS Code/Cursor 会自动检测 `.vscode/settings.json` 中的配置。

### 3. 验证环境

激活环境后，运行以下命令验证：

```bash
python --version  # 应该显示 Python 11.x
conda list        # 查看已安装的包
```

## 环境信息

- **环境名称**: `klayout-nanodevice-toolkit`
- **Python 版本**: 11
- **主要依赖**:
  - gdsfactory
  - numpy
  - pandas
  - matplotlib
  - klayout
  - 等等（详见 `environment.yml`）

## 更新环境

如果需要更新依赖：

```bash
conda activate klayout-nanodevice-toolkit
conda env update -f environment.yml --prune
```

## 删除环境

如果需要删除环境重新创建：

```bash
conda env remove -n klayout-nanodevice-toolkit
```

## 常见问题

### Q: 如何确保每次运行代码时都使用正确的环境？

A: 
1. 在 VS Code/Cursor 中，确保选择了正确的 Python 解释器（右下角状态栏）
2. 使用终端时，先运行 `conda activate klayout-nanodevice-toolkit`

### Q: 环境创建失败怎么办？

A: 
1. 确保已安装 Anaconda 或 Miniconda
2. 确保 conda 在系统 PATH 中
3. 尝试更新 conda: `conda update conda`
4. 检查网络连接（conda 需要下载包）

### Q: Python 11 不可用怎么办？

A: 如果 conda 中还没有 Python 11，可以：
1. 等待 conda-forge 更新
2. 或者修改 `environment.yml` 中的 Python 版本为可用的版本（如 `python=3.11`）

## 文件说明

- `environment.yml`: Conda 环境配置文件
