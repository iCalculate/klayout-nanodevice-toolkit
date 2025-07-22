# NanoDevice KLayout Library

## 简介
NanoDevice 是一个集成多种参数化器件（PCell）和二维码生成能力的 KLayout Library，可在 KLayout GUI 的 Library 面板中直接插入。

## 安装方法
1. **推荐**：双击或右键以管理员身份运行 `lymtoolkit/install_NanoDeviceToolkit.bat`，自动安装到 KLayout 用户库目录。
2. 或手动将 `lymtoolkit/NanoDevice/` 文件夹复制到：
   - Windows: `C:/Users/你的用户名/KLayout/libraries/`
   - Linux/macOS: `~/.klayout/libraries/`
3. 重启 KLayout。

## 依赖
- 需在 KLayout 的 Python 环境中安装 `qrcode` 和 `numpy`：
  - 在 KLayout 的“Macros > Start Script Console”中运行：
    ```python
    import pip
    pip.main(['install', 'qrcode', 'numpy'])
    ```

## 用法
- 打开 KLayout，左侧 Library 面板会出现 `NanoDevice Library`。
- 拖拽或右键参数化插入：
  - **QRCodePCell**：生成二维码图案
  - **ComplexDevicePCell**：生成简单FET结构
- 可在参数窗口自定义内容、尺寸、图层等。

## 目录结构
```
NanoDevice/
  QRCodePCell.py           # 二维码PCell
  ComplexDevicePCell.py    # 复杂结构PCell
  lyplugin.xml             # 插件描述
  icon.png                 # 可选，库图标
```

---
如需扩展更多PCell或遇到问题，请联系开发者。 