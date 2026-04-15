# lymtoolkit

## 简介
`lymtoolkit/` 现在统一承载 KLayout 相关内容，分为工具库、PDK、资源和单一安装入口。

## 当前结构
```text
lymtoolkit/
  toolkit/
    nanodevice-toolkit/       # NanoDevice GUI 工具与 NanoDeviceToolkitLib
    nanodevice-pcell/         # NanoDeviceLib PCells
  pdk/                        # LabPDK 技术文件
  assets/                     # 图标与示意图片
  install_lymtoolkit.bat      # 统一安装脚本
  README.md
```

## 安装方法
1. 运行 `lymtoolkit/install_lymtoolkit.bat`。
2. 脚本会把 `toolkit/` 下的库和 GUI 一起安装到 `KLayout\salt\nanodevice-toolkit`。
3. 重启 KLayout。

## 安装内容
- `NanoDeviceLib` PCells
- `NanoDeviceToolkitLib` PCells
- 统一的 `NanoDevice Toolkit` GUI 菜单入口

## 说明
- `pdk/` 目前保留为独立技术目录，不包含在统一安装脚本中。
- `assets/` 只存放图标和示意图，不参与安装。
