# -*- coding: utf-8 -*-
"""
套刻对准工具模块 - 基于gdsfactory实现caliper对准标记
Alignment utilities module - implements caliper alignment marks based on gdsfactory
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    import gdsfactory as gf
    GDSFACTORY_AVAILABLE = True
except ImportError:
    GDSFACTORY_AVAILABLE = False
    print("Warning: gdsfactory not available. Alignment features will be limited.")

from config import LAYER_DEFINITIONS, ALIGNMENT_CONFIG, DEFAULT_UNIT_SCALE
from utils.geometry import GeometryUtils

class AlignmentUtils:
    """套刻对准工具类
    
    Alignment utilities class for overlay alignment between different layers
    """
    
    def __init__(self):
        """初始化对准工具"""
        self.layer1_id = LAYER_DEFINITIONS['alignment_layer1']['id']
        self.layer2_id = LAYER_DEFINITIONS['alignment_layer2']['id']
        self.config = ALIGNMENT_CONFIG
        self.geo_utils = GeometryUtils()
    
    def create_caliper_cross(self, size=None, width=None, layer=None):
        """创建十字形caliper对准标记
        
        Create cross-shaped caliper alignment mark
        
        Args:
            size: 标记尺寸 (μm)
            width: 线条宽度 (μm) 
            layer: 图层ID
            
        Returns:
            KLayout region对象
        """
        if size is None:
            size = self.config['caliper_size']
        if width is None:
            width = self.config['caliper_width']
        if layer is None:
            layer = self.layer1_id
            
        # 转换为数据库单位
        size_db = int(size * DEFAULT_UNIT_SCALE)
        width_db = int(width * DEFAULT_UNIT_SCALE)
        
        # 创建十字形
        from klayout.db import Region, Box
        
        region = Region()
        
        # 水平线
        h_line = Box(-size_db//2, -width_db//2, size_db//2, width_db//2)
        # 垂直线  
        v_line = Box(-width_db//2, -size_db//2, width_db//2, size_db//2)
        
        region.insert(h_line)
        region.insert(v_line)
        
        return region
    
    def create_caliper_box(self, size=None, width=None, layer=None):
        """创建方形caliper对准标记
        
        Create box-shaped caliper alignment mark
        
        Args:
            size: 标记尺寸 (μm)
            width: 线条宽度 (μm)
            layer: 图层ID
            
        Returns:
            KLayout region对象
        """
        if size is None:
            size = self.config['caliper_size']
        if width is None:
            width = self.config['caliper_width']
        if layer is None:
            layer = self.layer1_id
            
        # 转换为数据库单位
        size_db = int(size * DEFAULT_UNIT_SCALE)
        width_db = int(width * DEFAULT_UNIT_SCALE)
        
        from klayout.db import Region, Box
        
        region = Region()
        
        # 外框
        outer_box = Box(-size_db//2, -size_db//2, size_db//2, size_db//2)
        # 内框
        inner_box = Box(-size_db//2 + width_db, -size_db//2 + width_db, 
                       size_db//2 - width_db, size_db//2 - width_db)
        
        region.insert(outer_box)
        region = region - Region(inner_box)
        
        return region
    
    def create_caliper_circle(self, size=None, width=None, layer=None):
        """创建圆形caliper对准标记
        
        Create circle-shaped caliper alignment mark
        
        Args:
            size: 标记尺寸 (μm)
            width: 线条宽度 (μm)
            layer: 图层ID
            
        Returns:
            KLayout region对象
        """
        if size is None:
            size = self.config['caliper_size']
        if width is None:
            width = self.config['caliper_width']
        if layer is None:
            layer = self.layer1_id
            
        # 转换为数据库单位
        size_db = int(size * DEFAULT_UNIT_SCALE)
        width_db = int(width * DEFAULT_UNIT_SCALE)
        
        from klayout.db import Region
        
        region = Region()
        
        # 外圆
        outer_circle = self.geo_utils.create_circle(0, 0, size_db//2, layer)
        # 内圆
        inner_circle = self.geo_utils.create_circle(0, 0, size_db//2 - width_db, layer)
        
        region = Region(outer_circle) - Region(inner_circle)
        
        return region
    
    def create_caliper_diamond(self, size=None, width=None, layer=None):
        """创建菱形caliper对准标记
        
        Create diamond-shaped caliper alignment mark
        
        Args:
            size: 标记尺寸 (μm)
            width: 线条宽度 (μm)
            layer: 图层ID
            
        Returns:
            KLayout region对象
        """
        if size is None:
            size = self.config['caliper_size']
        if width is None:
            width = self.config['caliper_width']
        if layer is None:
            layer = self.layer1_id
            
        # 转换为数据库单位
        size_db = int(size * DEFAULT_UNIT_SCALE)
        width_db = int(width * DEFAULT_UNIT_SCALE)
        
        from klayout.db import Region, Polygon, Point
        
        region = Region()
        
        # 外菱形
        outer_diamond = Polygon([
            Point(0, size_db//2),
            Point(size_db//2, 0),
            Point(0, -size_db//2),
            Point(-size_db//2, 0)
        ])
        
        # 内菱形
        inner_diamond = Polygon([
            Point(0, size_db//2 - width_db),
            Point(size_db//2 - width_db, 0),
            Point(0, -size_db//2 + width_db),
            Point(-size_db//2 + width_db, 0)
        ])
        
        region.insert(outer_diamond)
        region = region - Region(inner_diamond)
        
        return region
    
    def create_caliper_mark(self, style='cross', size=None, width=None, layer=None):
        """创建caliper对准标记
        
        Create caliper alignment mark with specified style
        
        Args:
            style: 标记样式 ('cross', 'box', 'circle', 'diamond')
            size: 标记尺寸 (μm)
            width: 线条宽度 (μm)
            layer: 图层ID
            
        Returns:
            KLayout region对象
        """
        if style == 'cross':
            return self.create_caliper_cross(size, width, layer)
        elif style == 'box':
            return self.create_caliper_box(size, width, layer)
        elif style == 'circle':
            return self.create_caliper_circle(size, width, layer)
        elif style == 'diamond':
            return self.create_caliper_diamond(size, width, layer)
        else:
            raise ValueError(f"Unsupported caliper style: {style}")
    
    def create_alignment_pair(self, x, y, style='cross', size=None, width=None, 
                            layer1=None, layer2=None, spacing=None):
        """创建一对对准标记用于套刻对准
        
        Create a pair of alignment marks for overlay alignment
        
        Args:
            x, y: 中心坐标 (μm)
            style: 标记样式
            size: 标记尺寸 (μm)
            width: 线条宽度 (μm)
            layer1: 第一层ID
            layer2: 第二层ID
            spacing: 两个标记间距 (μm)
            
        Returns:
            tuple: (layer1_region, layer2_region)
        """
        if layer1 is None:
            layer1 = self.layer1_id
        if layer2 is None:
            layer2 = self.layer2_id
        if spacing is None:
            spacing = self.config['min_spacing']
            
        # 转换为数据库单位
        x_db = int(x * DEFAULT_UNIT_SCALE)
        y_db = int(y * DEFAULT_UNIT_SCALE)
        spacing_db = int(spacing * DEFAULT_UNIT_SCALE)
        
        # 创建第一个标记
        mark1 = self.create_caliper_mark(style, size, width, layer1)
        mark1.move(x_db - spacing_db//2, y_db)
        
        # 创建第二个标记
        mark2 = self.create_caliper_mark(style, size, width, layer2)
        mark2.move(x_db + spacing_db//2, y_db)
        
        return mark1, mark2
    
    def create_alignment_array(self, positions, style='cross', size=None, width=None,
                             layer1=None, layer2=None, spacing=None):
        """创建对准标记阵列
        
        Create an array of alignment mark pairs
        
        Args:
            positions: 位置列表 [(x1, y1), (x2, y2), ...]
            style: 标记样式
            size: 标记尺寸 (μm)
            width: 线条宽度 (μm)
            layer1: 第一层ID
            layer2: 第二层ID
            spacing: 两个标记间距 (μm)
            
        Returns:
            tuple: (layer1_regions, layer2_regions)
        """
        if layer1 is None:
            layer1 = self.layer1_id
        if layer2 is None:
            layer2 = self.layer2_id
            
        from klayout.db import Region
        
        layer1_regions = Region()
        layer2_regions = Region()
        
        for x, y in positions:
            mark1, mark2 = self.create_alignment_pair(
                x, y, style, size, width, layer1, layer2, spacing
            )
            layer1_regions = layer1_regions + mark1
            layer2_regions = layer2_regions + mark2
            
        return layer1_regions, layer2_regions
    
    def create_gdsfactory_caliper(self, style='cross', size=None, width=None, layer=None):
        """使用gdsfactory创建caliper标记（如果可用）
        
        Create caliper mark using gdsfactory if available
        
        Args:
            style: 标记样式
            size: 标记尺寸 (μm)
            width: 线条宽度 (μm)
            layer: 图层ID
            
        Returns:
            gdsfactory Component对象或None
        """
        if not GDSFACTORY_AVAILABLE:
            print("gdsfactory not available, falling back to KLayout implementation")
            return None
            
        if size is None:
            size = self.config['caliper_size']
        if width is None:
            width = self.config['caliper_width']
        if layer is None:
            layer = (self.layer1_id, 0)
            
        c = gf.Component()
        
        if style == 'cross':
            # 创建十字形
            h_line = gf.components.rectangle(size=(size, width), layer=layer)
            v_line = gf.components.rectangle(size=(width, size), layer=layer)
            
            h_ref = c.add_ref(h_line)
            v_ref = c.add_ref(v_line)
            
            # 居中对齐
            h_ref.move(origin=(0, 0), destination=(-size/2, -width/2))
            v_ref.move(origin=(0, 0), destination=(-width/2, -size/2))
            
        elif style == 'box':
            # 创建方形框
            outer = gf.components.rectangle(size=(size, size), layer=layer)
            inner = gf.components.rectangle(size=(size-2*width, size-2*width), layer=layer)
            
            outer_ref = c.add_ref(outer)
            inner_ref = c.add_ref(inner)
            
            # 居中对齐
            outer_ref.move(origin=(0, 0), destination=(-size/2, -size/2))
            inner_ref.move(origin=(0, 0), destination=(-(size-2*width)/2, -(size-2*width)/2))
            
        elif style == 'circle':
            # 创建圆形
            outer = gf.components.circle(radius=size/2, layer=layer)
            inner = gf.components.circle(radius=size/2-width, layer=layer)
            
            outer_ref = c.add_ref(outer)
            inner_ref = c.add_ref(inner)
            
        elif style == 'diamond':
            # 创建菱形 - 使用add_polygon方法
            points = [
                (0, size/2),
                (size/2, 0),
                (0, -size/2),
                (-size/2, 0)
            ]
            c.add_polygon(points, layer=layer)
            
            inner_points = [
                (0, size/2-width),
                (size/2-width, 0),
                (0, -size/2+width),
                (-size/2+width, 0)
            ]
            c.add_polygon(inner_points, layer=layer)
            
        else:
            raise ValueError(f"Unsupported caliper style: {style}")
            
        return c
    
    def get_layer_info(self, layer_id):
        """获取图层信息
        
        Get layer information
        
        Args:
            layer_id: 图层ID
            
        Returns:
            dict: 图层信息
        """
        for layer_name, layer_info in LAYER_DEFINITIONS.items():
            if layer_info['id'] == layer_id:
                return layer_info
        return None