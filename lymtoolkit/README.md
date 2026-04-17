# lymtoolkit

## 简介
`lymtoolkit/` 现在统一承载 KLayout 相关内容，分为工具库、PDK、资源和单一安装入口。

## 当前结构
```text
lymtoolkit/
  toolkit/
    nanodevice-toolkit/       # NanoDevice GUI 工具与 NanoDeviceToolkitLib
    nanodevice-pcell/         # NanoDeviceLib PCells
  PDK/                        # LabPDK 技术文件
  assets/                     # 图标与示意图片
  install_lymtoolkit.bat      # 统一安装脚本
  install_pdk.bat             # 单独安装 LabPDK
  README.md
```

## 安装方法
1. 运行 `lymtoolkit/install_lymtoolkit.bat`。
2. 脚本会把 `toolkit/` 下的库和 GUI 一起安装到 `KLayout\salt\nanodevice-toolkit`。
3. 如需单独安装工艺文件，运行 `lymtoolkit/install_pdk.bat`。
4. 重启 KLayout。

## 安装内容
- `NanoDeviceLib` PCells
- `NanoDeviceToolkitLib` PCells
- 统一的 `NanoDevice Toolkit` GUI 菜单入口
- `config.py`、`utils`、`components`、`PDK` 运行时文件

## 说明
- `install_lymtoolkit.bat` 会把 toolkit 运行时依赖和 `PDK` 一起复制到 `KLayout\salt\nanodevice-toolkit`。
- `install_pdk.bat` 用于把 `PDK/` 单独安装到 `KLayout\tech\LabPDK`，方便作为技术目录使用。
- `assets/` 只存放图标和示意图，不参与安装。
