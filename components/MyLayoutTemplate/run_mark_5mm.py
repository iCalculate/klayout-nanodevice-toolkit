#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
针对 5mm 见方片子的 mark 版图生成入口脚本。
直接运行即可用 mark_writefield_gdsfactory_5mm.yaml 生成 GDS；可传 -o、--no-show 等参数。

用法示例:
  python run_mark_5mm.py
  python run_mark_5mm.py -o ../../output/mark_5mm.gds
  python run_mark_5mm.py --no-show
"""
import os
import sys
import subprocess

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_MAIN_SCRIPT = os.path.join(_SCRIPT_DIR, "mark_writefield_gdsfactory.py")
_CONFIG_5MM = os.path.join(_SCRIPT_DIR, "mark_writefield_gdsfactory_5mm.yaml")


def main():
    argv = [sys.executable, _MAIN_SCRIPT, "--config", _CONFIG_5MM] + sys.argv[1:]
    # 在项目根目录执行，便于主脚本找到 config 与 pdk
    root = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
    return subprocess.run(argv, cwd=root).returncode


if __name__ == "__main__":
    sys.exit(main())
