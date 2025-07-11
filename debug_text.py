#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# 测试 freetype 是否可用
try:
    import freetype
    print("✓ freetype 可用")
except ImportError:
    print("✗ freetype 不可用")
    sys.exit(1)

# 测试字体文件
font_path = 'C:/Windows/Fonts/arial.ttf'
if os.path.exists(font_path):
    print(f"✓ 字体文件存在: {font_path}")
else:
    print(f"✗ 字体文件不存在: {font_path}")
    # 尝试其他字体
    alternative_fonts = [
        'C:/Windows/Fonts/calibri.ttf',
        'C:/Windows/Fonts/tahoma.ttf',
        'C:/Windows/Fonts/verdana.ttf'
    ]
    for alt_font in alternative_fonts:
        if os.path.exists(alt_font):
            font_path = alt_font
            print(f"✓ 使用替代字体: {font_path}")
            break
    else:
        print("✗ 找不到可用的字体文件")
        sys.exit(1)

# 测试文本生成
from utils.text_utils import TextUtils

print("\n测试文本生成...")

# 测试简单的 freetype 文本生成
try:
    polys = TextUtils.create_text_freetype("Hello", 0, 0, size_um=10, font_path=font_path)
    print(f"✓ freetype 文本生成成功，生成了 {len(polys)} 个多边形")
    valid_polys = 0
    for i, poly in enumerate(polys):
        print(f"  多边形 {i}: {len(poly)} 个点")
        if len(poly) >= 3:
            valid_polys += 1
            print(f"    ✓ 有效多边形，第一个点: {poly[0]}")
        else:
            print(f"    ✗ 无效多边形（点数 < 3）")
    print(f"有效多边形数量: {valid_polys}/{len(polys)}")
except Exception as e:
    print(f"✗ freetype 文本生成失败: {e}")

# 测试 KLayout 文本生成
try:
    from utils.text_utils import TextUtils
    text_shapes = TextUtils.create_text("Test", 0, 0)
    print(f"✓ KLayout 文本生成成功，生成了 {len(text_shapes)} 个形状")
    for i, shape in enumerate(text_shapes):
        print(f"  形状 {i}: {type(shape)}")
        if hasattr(shape, 'num_points'):
            print(f"    点数: {shape.num_points()}")
        elif hasattr(shape, 'points'):
            print(f"    点数: {len(shape.points)}")
except Exception as e:
    print(f"✗ KLayout 文本生成失败: {e}")

# 测试字体加载
try:
    face = freetype.Face(font_path)
    face.set_char_size(0, 64*10, 0, 64)  # 10pt
    face.load_char('H')
    outline = face.glyph.outline
    print(f"✓ 字体加载成功，字符 'H' 有 {len(outline.points)} 个点")
    print(f"  轮廓数量: {len(outline.contours)}")
    for i, contour in enumerate(outline.contours):
        print(f"    轮廓 {i}: 结束于点 {contour}")
except Exception as e:
    print(f"✗ 字体加载失败: {e}")

# 测试坐标转换
print("\n测试坐标转换...")
try:
    polys = TextUtils.create_text_freetype("A", 100, 100, size_um=20, font_path=font_path)
    print(f"生成字符 'A' 在 (100, 100)，生成了 {len(polys)} 个多边形")
    
    # 转换为 KLayout 多边形
    from utils.geometry import GeometryUtils
    from utils.text_utils import set_unit_scale
    set_unit_scale(1000)  # 设置单位缩放
    
    klayout_polys = []
    for poly in polys:
        if len(poly) >= 3:
            klayout_poly = GeometryUtils.Polygon([
                GeometryUtils.Point(int(pt[0] * 1000), int(pt[1] * 1000))
                for pt in poly
            ])
            klayout_polys.append(klayout_poly)
            print(f"  转换后的多边形: {klayout_poly.num_points()} 个点")
    
    print(f"成功转换 {len(klayout_polys)} 个有效多边形")
    
except Exception as e:
    print(f"✗ 坐标转换失败: {e}")

print("\n调试完成") 