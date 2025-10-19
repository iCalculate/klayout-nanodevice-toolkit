# -*- coding: utf-8 -*-
"""
UV Lithography TLM器件阵列生成器
符合UV光刻精度限制的TLM器件生成脚本
- 最小沟道宽度: 1μm
- 最大沟道宽度: 100μm  
- 四种间距分布方式: linear, log, exp, inv
- 填充6mm×6mm空间
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import klayout.db as db
from config import LAYER_DEFINITIONS
from components.tlm import TLM
from utils.text_utils import TextUtils
import math

class UVLithoTLMArray:
    """UV Lithography TLM器件阵列生成器"""
    
    def __init__(self, layout=None):
        self.layout = layout or db.Layout()
        self.setup_layers()
        
        # UV Lithography精度限制参数
        self.min_channel_width = 1.0    # 最小沟道宽度 (μm)
        self.max_channel_width = 60.0   # 最大沟道宽度 (μm)
        self.array_size = 6000.0         # 6mm = 6000μm
        
        # 四种间距分布方式
        self.distributions = ['linear', 'log', 'exp', 'inv']
        
        # 器件参数
        self.num_electrodes = 8          # 电极数量
        self.min_spacing = 1.0           # 最小电极间距
        # 计算最大间距，确保总长度不超过250μm
        # 8个电极有7个间距，总长度 = 7 * max_spacing
        # 250μm / 7 ≈ 35.7μm，所以设置max_spacing为35μm
        self.max_spacing = 35.0         # 最大电极间距，确保总长度≤250μm
        
        # 器件尺寸参数
        self.inner_pad_length = 4.0      # inner pad长度，固定为4μm
        self.inner_pad_width = None      # inner pad宽度，使用默认值（自动计算）
        self.outer_pad_length = 60.0     # outer pad长度
        self.outer_pad_width = 60.0       # outer pad宽度
        self.outer_pad_spacing = None     # outer pad间距，自动计算
        self.outer_pad_offset_y = 100.0  # outer pad偏移
        
        # 单元参数（包含四种分布方式的单元）
        self.unit_size = 600.0           # 单元尺寸 (0.6mm) - 更紧凑
        self.unit_margin = 15.0           # 单元边距 - 进一步减少边距
        
        # 版图布局参数
        self.device_margin_x = 80.0      # 器件X方向边距 - 进一步减少边距
        self.device_margin_y = 70.0       # 器件Y方向边距 - 进一步减少边距
        
        # 标记参数 - 扩大一倍，每个单元只用一个mark
        self.mark_size = 40.0
        self.mark_width = 4.0
        self.mark_type = 'sq_missing'  # 只使用一个mark样式
        self.mark_rotation = 0  # 统一旋转角度
        
        # 标签参数 - 扩大一倍
        self.label_offset_x = 60.0
        self.label_offset_y = -20.0
        self.label_anchor = 'left_top'
        
    def setup_layers(self):
        """设置图层"""
        for layer_name, layer_info in LAYER_DEFINITIONS.items():
            self.layout.layer(layer_info['id'], 0)
    
    def calculate_unit_spacing(self):
        """计算单元间距，确保在6mm×6mm空间内合理分布"""
        # 计算可容纳的单元数量 - 更紧凑的布局
        max_cols = int(self.array_size / self.unit_size)
        max_rows = int(self.array_size / self.unit_size)
        
        # 计算实际使用的单元数量 - 增加单元数量
        cols = min(max_cols, 10)  # 最多10列
        rows = min(max_rows, 10)  # 最多10行
        
        # 计算单元间距，确保完全填充
        unit_spacing_x = self.array_size / cols if cols > 1 else self.unit_size
        unit_spacing_y = self.array_size / rows if rows > 1 else self.unit_size
        
        return cols, rows, unit_spacing_x, unit_spacing_y
    
    def create_single_tlm_device(self, distribution, channel_width, x=0, y=0, device_id=1):
        """创建单个TLM器件"""
        # 创建TLM实例 - 不添加mark，在单元级别添加
        tlm = TLM(
            layout=self.layout,
            num_electrodes=self.num_electrodes,
            min_spacing=self.min_spacing,
            max_spacing=self.max_spacing,
            distribution=distribution,
            spacing_mode='centered',
            channel_width=channel_width,
            inner_pad_length=self.inner_pad_length,
            inner_pad_width=self.inner_pad_width,
            outer_pad_length=self.outer_pad_length,
            outer_pad_width=self.outer_pad_width,
            outer_pad_spacing=self.outer_pad_spacing,
            outer_pad_offset_y=self.outer_pad_offset_y,
            fanout_type='trapezoid',
            outer_pad_chamfer_type='round',
            outer_pad_chamfer_size=6.0,
            device_margin_x=self.device_margin_x,
            device_margin_y=self.device_margin_y,
            mark_size=self.mark_size,
            mark_width=self.mark_width,
            add_alignment_mark=False,  # 不在器件级别添加mark
            mark_types=[self.mark_type],
            mark_rotations=[self.mark_rotation],
            label_offset_x=self.label_offset_x,
            label_offset_y=self.label_offset_y,
            label_anchor=self.label_anchor
        )
        
        # 生成器件
        cell_name = f"UV_TLM_{distribution}_{device_id:02d}"
        device_cell = tlm.create_single_device(cell_name, x, y)
        
        return device_cell, tlm
    
    def create_tlm_unit(self, unit_id, channel_width, x=0, y=0):
        """创建包含四种分布方式的TLM单元"""
        unit_cell = self.layout.create_cell(f"TLM_Unit_{unit_id:02d}")
        label_layer = LAYER_DEFINITIONS['labels']['id']
        
        # 单元内器件间距 - 更紧凑的布局
        device_spacing_x = self.unit_size / 2 - self.unit_margin
        device_spacing_y = self.unit_size / 2 - self.unit_margin
        
        # 单元内器件位置 - 更紧凑的2x2布局
        device_positions = [
            (-device_spacing_x/2, device_spacing_y/2),   # 左上
            (device_spacing_x/2, device_spacing_y/2),    # 右上
            (-device_spacing_x/2, -device_spacing_y/2),  # 左下
            (device_spacing_x/2, -device_spacing_y/2)    # 右下
        ]
        
        device_id = 1
        for i, (dist_x, dist_y) in enumerate(device_positions):
            if i >= len(self.distributions):
                break
                
            distribution = self.distributions[i]
            device_x = x + dist_x
            device_y = y + dist_y
            
            # 创建器件
            device_cell, tlm = self.create_single_tlm_device(
                distribution, channel_width, device_x, device_y, device_id
            )
            
            # 插入器件到单元
            unit_cell.insert(db.CellInstArray(
                device_cell.cell_index(),
                db.Trans(device_x, device_y)
            ))
            
            # 添加分布方式标签 - 使用gdsfactory生成
            label_x = device_x - tlm.device_margin_x + 10
            label_y = device_y + tlm.device_margin_y - 40
            
            dist_label = f"{distribution[:3]}"  # 只显示前3个字符
            
            # 使用gdsfactory生成文本
            try:
                import gdsfactory as gf
                text_component = gf.components.text(
                    text=dist_label,
                    size=20,  # 20μm
                    position=(label_x, label_y),
                    layer=(LAYER_DEFINITIONS['labels']['id'], 0)
                )
                # 将gdsfactory组件转换为KLayout shapes
                for poly in text_component.get_polygons():
                    unit_cell.shapes(label_layer).insert(poly)
            except ImportError:
                # 如果gdsfactory不可用，回退到原来的方法
                dist_text = db.Text(dist_label, int(label_x * 1000), int(label_y * 1000))
                unit_cell.shapes(label_layer).insert(dist_text)
            
            device_id += 1
        
        # 添加单个mark - 基于当前位置向右10μm，向上20μm
        mark_x = x - self.unit_size/2 + self.mark_size/2 - 20 + 10  # 向左移动20μm，再向右10μm = 向左10μm
        mark_y = y + self.unit_size/2 - self.mark_size/2 - 10 + 20  # 向下移动10μm，再向上20μm = 向上10μm
        
        # 添加单元标签（沟道宽度） - 位于mark的右侧，向上移动15μm
        unit_label_x = mark_x + self.mark_size/2 + 10  # 位于mark的右侧
        unit_label_y = mark_y + 15  # 向上移动15μm
        unit_label = f"W={channel_width}"
        
        # 使用gdsfactory生成文本
        try:
            import gdsfactory as gf
            text_component = gf.components.text(
                text=unit_label,
                size=20,  # 20μm
                position=(unit_label_x, unit_label_y),
                layer=(LAYER_DEFINITIONS['labels']['id'], 0)
            )
            # 将gdsfactory组件转换为KLayout shapes
            for poly in text_component.get_polygons():
                unit_cell.shapes(label_layer).insert(poly)
        except ImportError:
            # 如果gdsfactory不可用，回退到原来的方法
            unit_text = db.Text(unit_label, int(unit_label_x * 1000), int(unit_label_y * 1000))
            unit_cell.shapes(label_layer).insert(unit_text)
        
        # 导入MarkUtils
        from utils.mark_utils import MarkUtils
        
        # 创建mark
        if hasattr(MarkUtils, self.mark_type):
            if self.mark_type == 'sq_missing':
                mark = getattr(MarkUtils, self.mark_type)(mark_x, mark_y, self.mark_size).rotate(self.mark_rotation)
            else:
                mark = getattr(MarkUtils, self.mark_type)(mark_x, mark_y, self.mark_size, self.mark_width).rotate(self.mark_rotation)
        else:
            mark = MarkUtils.cross(mark_x, mark_y, self.mark_size, self.mark_width).rotate(self.mark_rotation)
        
        # 插入mark到单元
        mark_layer = LAYER_DEFINITIONS['alignment_marks']['id']
        shapes = mark.get_shapes() if hasattr(mark, 'get_shapes') else [mark]
        if isinstance(shapes, list):
            for shape in shapes:
                if isinstance(shape, db.Region):
                    for poly in shape.each():
                        unit_cell.shapes(mark_layer).insert(poly)
                elif isinstance(shape, (db.Polygon, db.Box)):
                    unit_cell.shapes(mark_layer).insert(shape)
        else:
            if isinstance(shapes, db.Region):
                for poly in shapes.each():
                    unit_cell.shapes(mark_layer).insert(poly)
            elif isinstance(shapes, (db.Polygon, db.Box)):
                unit_cell.shapes(mark_layer).insert(shapes)
        
        return unit_cell
    
    def create_uv_tlm_array(self):
        """创建UV Lithography TLM器件阵列"""
        # 计算单元间距
        cols, rows, unit_spacing_x, unit_spacing_y = self.calculate_unit_spacing()
        
        # 创建主阵列cell
        array_cell = self.layout.create_cell("UV_TLM_Array_6mm")
        label_layer = LAYER_DEFINITIONS['labels']['id']
        
        # 定义沟道宽度 - 按A1→An→B1→Bn线性增大
        # 从1μm到60μm线性分布
        min_width = 1.0
        max_width = 60.0
        total_units = cols * rows
        channel_widths = []
        
        for i in range(total_units):
            if total_units > 1:
                width = min_width + (max_width - min_width) * i / (total_units - 1)
            else:
                width = min_width
            channel_widths.append(round(width, 1))
        
        # 计算偏移量，使原点位于E和F列的中心以及5和6行的中心
        # 对于10列：A(0), B(1), C(2), D(3), E(4), F(5), G(6), H(7), I(8), J(9)
        # E和F列的中心 = (4 + 5) / 2 = 4.5
        # 对于10行：1(0), 2(1), 3(2), 4(3), 5(4), 6(5), 7(6), 8(7), 9(8), 10(9)
        # 5和6行的中心 = (4 + 5) / 2 = 4.5
        
        center_col = 4.5  # E和F列的中心
        center_row = 4.5  # 5和6行的中心
        
        # 计算偏移量，使原点位于指定位置
        offset_x = -center_col * unit_spacing_x
        offset_y = -center_row * unit_spacing_y
        
        
        
        
        
        unit_id = 1
        
        # 生成单元阵列
        for row in range(rows):
            for col in range(cols):
                if unit_id > len(channel_widths):
                    break
                    
                # 计算单元位置 - 居中到原点
                unit_x = offset_x + col * unit_spacing_x
                unit_y = offset_y + row * unit_spacing_y
                
                # 选择沟道宽度
                channel_width = channel_widths[unit_id - 1]
                
                # 创建单元
                unit_cell = self.create_tlm_unit(unit_id, channel_width, unit_x, unit_y)
                
                # 插入单元到阵列
                array_cell.insert(db.CellInstArray(
                    unit_cell.cell_index(),
                    db.Trans(unit_x, unit_y)
                ))
                
                # 添加Excel格式标签 - 位于mark的右侧
                excel_label = f"{chr(ord('A') + col)}{row + 1}"
                # 计算mark位置（与单元内mark位置一致）
                mark_x = unit_x - self.unit_size/2 + self.mark_size/2 - 20 + 10  # 向左10μm
                mark_y = unit_y + self.unit_size/2 - self.mark_size/2 - 10 + 20  # 向上10μm
                label_x = mark_x + self.mark_size/2 + 10  # 位于mark的右侧
                label_y = mark_y + 15  # 向上移动15μm
                
                # 使用gdsfactory生成文本
                try:
                    import gdsfactory as gf
                    text_component = gf.components.text(
                        text=excel_label,
                        size=30,  # 30μm
                        position=(label_x, label_y),
                        layer=(LAYER_DEFINITIONS['labels']['id'], 0)
                    )
                    # 将gdsfactory组件转换为KLayout shapes
                    for poly in text_component.get_polygons():
                        array_cell.shapes(label_layer).insert(poly)
                except ImportError:
                    # 如果gdsfactory不可用，回退到原来的方法
                    text_shapes = TextUtils.create_text_freetype(
                        excel_label, 
                        label_x, 
                        label_y,
                        size_um=30, 
                        font_path='C:/Windows/Fonts/OCRAEXT.TTF', 
                        spacing_um=0.4,
                        anchor='left_top'
                    )
                    for shape in text_shapes:
                        array_cell.shapes(label_layer).insert(shape)
                
                unit_id += 1
        
        return array_cell
    

def main():
    """主函数 - 生成UV Lithography TLM器件阵列"""
    print("开始生成UV Lithography TLM器件阵列...")
    
    # 创建布局
    layout = db.Layout()
    
    # 创建UV TLM阵列生成器
    uv_tlm_generator = UVLithoTLMArray(layout=layout)
    
    # 生成主阵列
    print("生成主TLM器件阵列...")
    main_array = uv_tlm_generator.create_uv_tlm_array()
    print(f"主阵列已创建: {main_array.name}")
    
    # 保存文件
    output_file = "UV_TLM_Array_6mm.gds"
    layout.write(output_file)
    print(f"布局文件已保存: {output_file}")
    
    # 打印器件信息
    print("\n=== UV Lithography TLM器件信息 ===")
    print(f"阵列尺寸: {uv_tlm_generator.array_size/1000:.1f}mm × {uv_tlm_generator.array_size/1000:.1f}mm")
    print(f"单元尺寸: {uv_tlm_generator.unit_size/1000:.1f}mm × {uv_tlm_generator.unit_size/1000:.1f}mm")
    print(f"沟道宽度范围: {uv_tlm_generator.min_channel_width}μm - {uv_tlm_generator.max_channel_width}μm")
    print(f"沟道长度计算: 基于电极边缘间距，考虑电极长度({uv_tlm_generator.inner_pad_length}μm)，确保无交叠")
    print(f"间距分布方式: {', '.join(uv_tlm_generator.distributions)}")
    print(f"电极数量: {uv_tlm_generator.num_electrodes}")
    print(f"间距范围: {uv_tlm_generator.min_spacing}μm - {uv_tlm_generator.max_spacing}μm")
    print(f"Inner pad长度: {uv_tlm_generator.inner_pad_length}μm")
    print(f"Inner pad宽度: 自动计算（基于沟道宽度）")
    print(f"总长度限制: ≤250μm (8个电极，7个间距)")
    print(f"每个单元包含: 4个TLM器件（四种分布方式）")
    print(f"整体布局: 居中到原点")
    print(f"单元标签格式: A1, B1, A2, B2 等")
    
    print("\nUV Lithography TLM器件阵列生成完成！")

if __name__ == "__main__":
    main()

