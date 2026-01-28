# 快速配置指南

## 🚀 三步快速配置

### 步骤 1: 创建环境

运行以下命令创建 conda 环境：
```bash
conda env create -f environment.yml
```

**如果 Python 11 不可用**，请先修改 `environment.yml`：
- 将 `python=11` 改为 `python=3.11` 或 `python=3.12`

### 步骤 3: 激活环境

**在命令行中：**
```cmd
conda activate klayout-nanodevice-toolkit
```

**在 Cursor/VS Code 中：**
1. 按 `Ctrl+Shift+P`
2. 输入 "Python: Select Interpreter"
3. 选择 `klayout-nanodevice-toolkit` 环境

## ✅ 验证配置

激活环境后，运行：
```python
python --version
python -c "import gdsfactory; print('gdsfactory 已安装')"
```

## 📝 常见问题

### Q: Python 11 找不到？
A: Python 11 可能还未在 conda 中发布。请使用 Python 3.11：
```yaml
# 在 environment.yml 中修改
- python=3.11  # 替代 python=11
```

### Q: 如何确保 Cursor 使用正确的环境？
A: 
1. 查看 Cursor 右下角的 Python 版本
2. 点击它，选择 `klayout-nanodevice-toolkit`
3. 或按 `Ctrl+Shift+P` → "Python: Select Interpreter"

### Q: 环境创建很慢？
A: 这是正常的，conda 需要下载和安装所有依赖包。请耐心等待。

## 🔧 详细配置步骤

1. **打开 Anaconda Prompt 或 PowerShell**

2. **导航到项目目录**
   ```bash
   cd "项目路径"
   ```

3. **创建环境**
   ```bash
   conda env create -f environment.yml
   ```

4. **激活环境**
   ```bash
   conda activate klayout-nanodevice-toolkit
   ```

5. **验证安装**
   ```bash
   python --version
   pip list
   ```

6. **在 Cursor/VS Code 中选择解释器**
   - 打开 Cursor/VS Code
   - 按 `Ctrl+Shift+P`
   - 输入 "Python: Select Interpreter"
   - 选择 `klayout-nanodevice-toolkit` 环境
