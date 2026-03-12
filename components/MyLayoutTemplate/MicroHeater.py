# -*- coding: utf-8 -*-
"""
MicroHeater device component module - KLayout-based microheater pattern generator
使用希尔伯特曲线生成微加热器阵列
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# KLayout 兼容：支持在 KLayout GUI 内运行（pya）或独立 Python（klayout.db）
_db = None
try:
    import klayout.db as _db
except ImportError as e:
    if "tlcore" in str(e) or "klayout" in str(e).lower():
        print("Error: klayout may not support this Python version (e.g. Python 3.14).")
        print("Use either: (1) Run in KLayout: File -> Run Macro, or (2) conda env with Python 3.11 + pip install klayout")
    raise
try:
    import pya
except ImportError:
    pya = _db
    sys.modules["pya"] = _db
db = _db
layout_module = _db

from utils.geometry import GeometryUtils
from config import LAYER_DEFINITIONS, PROCESS_CONFIG, DEFAULT_UNIT_SCALE

# Import gdsfactory for text generation
import gdsfactory as gf

class MicroHeater:
    """MicroHeater device class for generating Hilbert curve-based microheater arrays"""
    
    def __init__(self, layout=None, **kwargs):
        """
        Initialize MicroHeater device class
        
        Args:
            layout: KLayout layout object, create new if None
            **kwargs: Other parameters
        """
        self.layout = layout or layout_module.Layout()
        # 数据库单位：1 dbu = 0.001 μm = 1 nm，坐标按 dbu 存储
        self.layout.dbu = PROCESS_CONFIG.get('dbu', 0.001)
        # 几何输出：1 μm = UNIT_SCALE dbu（与 dbu 一致，保证亚微米精度）
        GeometryUtils.UNIT_SCALE = DEFAULT_UNIT_SCALE  # 1000 when dbu=0.001
        self.setup_layers()
        
        # ===== MicroHeater parameters =====
        self.line_width = kwargs.get('line_width', 4.0)          # Line width (μm)
        self.line_spacing = kwargs.get('line_spacing', 4.0)      # Line spacing (μm)
        self.array_spacing = kwargs.get('array_spacing', 1000.0) # Array spacing (μm) - 1mm
        self.array_size = kwargs.get('array_size', 6)            # Array size (6x6)
        self.hilbert_order = kwargs.get('hilbert_order', 4)      # Hilbert curve order
        self.hilbert_step = kwargs.get('hilbert_step', 10.0)     # Hilbert curve step size (μm)
        self.hilbert_margin = kwargs.get('hilbert_margin', 2.0)  # Hilbert curve margin (μm)
        # ===== 蛇形阵列参数 (4x4 大单元 × 4x4 小单元) =====
        self.meander_cell_size = kwargs.get('meander_cell_size', 450.0)   # 小单元方形边长 (μm)
        self.meander_line_width = kwargs.get('meander_line_width', 4.0)  # 蛇形线宽 (μm)
        self.meander_line_spacing = kwargs.get('meander_line_spacing', 4.0)  # 蛇形线间距 (μm)
        self.meander_cell_gap = kwargs.get('meander_cell_gap', 10.0)     # 小单元间距 (μm)
        self.meander_pad_size = kwargs.get('meander_pad_size', 10.0)      # 纳米线两端 pad 边长 (μm)
        self.meander_block_gap = kwargs.get('meander_block_gap', 10.0)   # 大单元间距 (μm)
        
    def setup_layers(self):
        """Setup layers"""
        for layer_name, layer_info in LAYER_DEFINITIONS.items():
            # In KLayout, use layer() method to get or create layers
            # layer() method requires (layer_number, datatype) parameters
            self.layout.layer(layer_info['id'], 0)  # Use datatype=0
    
    def set_parameters(self, line_width=None, line_spacing=None, array_spacing=None, 
                      array_size=None, hilbert_order=None, hilbert_step=None, hilbert_margin=None):
        """
        Set microheater parameters
        
        Args:
            line_width: Line width (μm)
            line_spacing: Line spacing (μm)
            array_spacing: Array spacing (μm)
            array_size: Array size (NxN)
            hilbert_order: Hilbert curve order
            hilbert_step: Hilbert curve step size (μm)
            hilbert_margin: Hilbert curve margin (μm)
        """
        if line_width is not None:
            self.line_width = line_width
        if line_spacing is not None:
            self.line_spacing = line_spacing
        if array_spacing is not None:
            self.array_spacing = array_spacing
        if array_size is not None:
            self.array_size = array_size
        if hilbert_order is not None:
            self.hilbert_order = hilbert_order
        if hilbert_step is not None:
            self.hilbert_step = hilbert_step
        if hilbert_margin is not None:
            self.hilbert_margin = hilbert_margin
    
    def create_single_hilbert_heater(self, cell, x=0.0, y=0.0, row=0, col=0):
        """
        Create a single Hilbert curve microheater with squares, mark and label
        
        Args:
            cell: Target cell
            x, y: Heater center coordinates
            row, col: Array position for labeling
        """
        layer_id = LAYER_DEFINITIONS['channel']['id']
        mark_layer_id = LAYER_DEFINITIONS['alignment_marks']['id']
        label_layer_id = LAYER_DEFINITIONS['labels']['id']
        
        # Generate Hilbert curve using GeometryUtils.make_hilbert
        hilbert_region = GeometryUtils.make_hilbert(
            order=self.hilbert_order,
            step=self.hilbert_step,
            line_w=self.line_width,
            margin=self.hilbert_margin
        )
        
        # Move the Hilbert curve to the specified position
        # Calculate the Hilbert curve size
        hilbert_size = (2 ** self.hilbert_order) * self.hilbert_step + 2 * self.hilbert_margin
        
        # Create transformation to center the curve at (x, y)
        # The original curve starts at (margin, margin), we need to move it to (x - hilbert_size/2, y - hilbert_size/2)
        offset_x = x - hilbert_size / 2
        offset_y = y - hilbert_size / 2
        
        # Apply transformation（坐标 μm -> dbu）
        scale = GeometryUtils.UNIT_SCALE
        transformed_region = hilbert_region.dup()
        transformed_region.transform(pya.Trans(pya.Point(int(round(offset_x * scale)), int(round(offset_y * scale)))))
        
        cell.shapes(layer_id).insert(transformed_region)
        
        # Add 30μm squares at bottom-left and bottom-right corners
        square_size = 7 * self.line_width  # 30μm
        half_hilbert = hilbert_size / 2
        
        # Calculate movement offsets
        move_up = square_size - self.line_width / 2  # 方块边长 - 线宽/2
        move_right = square_size - self.line_width / 2  # 方块边长 - 线宽/2
        move_left = square_size + 3 * self.line_width / 2  # 方块边长 + 线宽/2
        
        # Bottom-left square: move up and right by (square_size - line_width/2)
        bottom_left_x = x - half_hilbert - square_size / 2 + move_right
        bottom_left_y = y - half_hilbert - square_size / 2 + move_up
        bottom_left_square = GeometryUtils.create_rectangle(
            bottom_left_x, bottom_left_y, square_size, square_size, center=True
        )
        cell.shapes(layer_id).insert(bottom_left_square)
        
        # Bottom-right square: move left by (square_size + line_width/2) and up by (square_size - line_width/2)
        bottom_right_x = x + half_hilbert + square_size / 2 - move_left
        bottom_right_y = y - half_hilbert - square_size / 2 + move_up
        bottom_right_square = GeometryUtils.create_rectangle(
            bottom_right_x, bottom_right_y, square_size, square_size, center=True
        )
        cell.shapes(layer_id).insert(bottom_right_square)
        
        # Add missing square mark at top-left corner
        mark_size = 20.0  # 20μm mark size
        mark_x = x - half_hilbert - mark_size / 2
        mark_y = y + half_hilbert + mark_size / 2
        missing_square_mark = GeometryUtils.create_square_with_missing_quadrants(
            mark_x, mark_y, mark_size, missing=(2, 4)
        )
        cell.shapes(mark_layer_id).insert(missing_square_mark)
        
        # Add label to the right of the mark (following FET implementation)
        # Generate letter+number format like FET: col_letter + row_number
        col_letter = chr(ord('A') + col)  # 0->A, 1->B, 2->C, ...
        row_number = str(row + 1)  # 行号从1开始
        label_text = col_letter + row_number  # 如 A1, B2, C3
        
        # Position label closer to the mark
        label_x = mark_x + mark_size + 5.0  # 5μm spacing from mark
        label_y = mark_y  # Same Y position as mark
        label_size = 20.0  # 20μm text size (same as FET default)
        
        # Create text using gdsfactory components.text (official way)
        try:
            # Use gdsfactory components.text (official way)
            text_component = gf.components.text(
                text=label_text,
                size=label_size,
                justify="left",
                layer=(label_layer_id, 0)
            )
            
            # Get the bounding box of the text component
            bbox = text_component.bbox
            text_width = bbox[1][0] - bbox[0][0]  # right - left
            text_height = bbox[1][1] - bbox[0][1]  # top - bottom
            
            # Position the text component at the desired location
            # gdsfactory text starts at origin, we need to move it to our position
            offset_x = label_x - bbox[0][0]  # Move to our x position
            offset_y = label_y - bbox[0][1]  # Move to our y position
            
            # Convert gdsfactory component to KLayout shapes
            for polygon in text_component.polygons:
                # Convert gdsfactory polygon to KLayout polygon with offset
                points = []
                for p in polygon.points:
                    px = int(p[0] + offset_x)
                    py = int(p[1] + offset_y)
                    points.append(pya.Point(px, py))
                klayout_polygon = pya.Polygon(points)
                cell.shapes(label_layer_id).insert(klayout_polygon)
                
        except Exception as e:
            print(f"Warning: gdsfactory text creation failed for {label_text}: {e}")
            # Fallback: create a simple rectangle as placeholder
            fallback_rect = GeometryUtils.create_rectangle(
                label_x, label_y, len(label_text) * label_size * 0.6, label_size, center=False
            )
            cell.shapes(label_layer_id).insert(fallback_rect)
    
    def create_single_meander_cell(self, cell, cx, cy, angle_deg, layer_id=None):
        """
        创建单个蛇形小单元：在限定单元区域内按给定取向绘制蜿蜒线（不旋转单元），
        再在左上/右下角放置两枚 pad。
        
        蜿蜒线取向由角度设定：在单元区域内先画该角度的平行线，再首尾相接形成连续线，
        由 create_angled_meander_in_rect 实现。
        
        Args:
            cell: 目标 cell
            cx, cy: 小单元中心 (μm)
            angle_deg: 蜿蜒线取向角度 (0°, 30°, 60°, 90° 等)
            layer_id: 沟道图层；None 则用 config 的 channel
        """
        if layer_id is None:
            layer_id = LAYER_DEFINITIONS['channel']['id']
        pad_layer_id = LAYER_DEFINITIONS.get('pads', LAYER_DEFINITIONS['channel'])['id']
        sz = self.meander_cell_size
        lw = self.meander_line_width
        sp = self.meander_line_spacing
        pad_sz = self.meander_pad_size
        half = sz / 2.0
        # 在单元区域限制内按角度绘制蜿蜒线（平行线 + 首尾连接，再与矩形求交）
        serpentine = GeometryUtils.create_angled_meander_in_rect(
            cx, cy, sz, sz, lw, sp, angle_deg
        )
        cell.shapes(layer_id).insert(serpentine)
        # 左上角 pad（纳米线一端）
        pad_tl_x = cx - half + pad_sz / 2.0
        pad_tl_y = cy + half - pad_sz / 2.0
        pad_tl = GeometryUtils.create_rectangle(pad_tl_x, pad_tl_y, pad_sz, pad_sz, center=True)
        cell.shapes(pad_layer_id).insert(pad_tl)
        # 右下角 pad（纳米线另一端）
        pad_br_x = cx + half - pad_sz / 2.0
        pad_br_y = cy - half + pad_sz / 2.0
        pad_br = GeometryUtils.create_rectangle(pad_br_x, pad_br_y, pad_sz, pad_sz, center=True)
        cell.shapes(pad_layer_id).insert(pad_br)
    
    def create_meander_4x4_block(self, cell, base_x, base_y, layer_id=None):
        """
        在一个大单元内创建 4×4 个小单元；每行蛇形角度：第1行0°、第2行30°、第3行60°、第4行90°。
        base_x, base_y 为大单元左上角坐标（小单元 (0,0) 的左上角）。
        """
        if layer_id is None:
            layer_id = LAYER_DEFINITIONS['channel']['id']
        sz = self.meander_cell_size
        gap = self.meander_cell_gap
        step = sz + gap
        row_angles = [0, 30, 60, 90]
        for row in range(4):
            for col in range(4):
                cx = base_x + col * step + sz / 2.0
                cy = base_y - row * step - sz / 2.0
                self.create_single_meander_cell(cell, cx, cy, row_angles[row], layer_id)
    
    def create_meander_array_4x4(self, cell, center_x=0.0, center_y=0.0, layer_id=None):
        """
        生成 4×4 大单元阵列，每个大单元为 4×4 蛇形小单元。
        小单元：方形 450μm，线宽/间距 4μm，小单元间距 10μm，左上/右下 10μm pad。
        """
        if layer_id is None:
            layer_id = LAYER_DEFINITIONS['channel']['id']
        sz = self.meander_cell_size
        gap = self.meander_cell_gap
        block_gap = self.meander_block_gap
        small_step = sz + gap
        block_size = 4 * sz + 3 * gap
        block_step = block_size + block_gap
        total_size = 4 * block_size + 3 * block_gap
        start_x = center_x - total_size / 2.0
        start_y = center_y + total_size / 2.0
        for bi in range(4):
            for bj in range(4):
                base_x = start_x + bj * block_step
                base_y = start_y - bi * block_step
                self.create_meander_4x4_block(cell, base_x, base_y, layer_id)
    
    def create_heater_array(self, cell, center_x=0.0, center_y=0.0):
        """
        Create a 6x6 array of Hilbert curve microheaters
        
        Args:
            cell: Target cell
            center_x, center_y: Array center coordinates
        """
        # Calculate array layout
        # Each heater is spaced by array_spacing (1mm = 1000μm)
        spacing = self.array_spacing
        
        # Calculate the total array size
        total_width = (self.array_size - 1) * spacing
        total_height = (self.array_size - 1) * spacing
        
        # Calculate starting position (top-left corner)
        start_x = center_x - total_width / 2
        start_y = center_y + total_height / 2
        
        # Create individual heater cells
        for row in range(self.array_size):
            for col in range(self.array_size):
                # Calculate position for this heater
                heater_x = start_x + col * spacing
                heater_y = start_y - row * spacing
                
                # Create a unique cell for each heater
                heater_cell_name = f"Hilbert_Heater_{row}_{col}"
                heater_cell = self.layout.create_cell(heater_cell_name)
                
                # Generate the Hilbert curve for this heater
                self.create_single_hilbert_heater(heater_cell, 0.0, 0.0, row, col)
                
                # Insert the heater cell into the main cell（坐标 μm -> dbu）
                scale = GeometryUtils.UNIT_SCALE
                cell.insert(pya.CellInstArray(
                    heater_cell.cell_index(),
                    pya.Trans(pya.Point(int(round(heater_x * scale)), int(round(heater_y * scale))))
                ))
        


def main():
    """Main function - Generate 6x6 Hilbert curve microheater array"""
    
    print("=== Generating 6x6 Hilbert Curve MicroHeater Array ===")
    
    # Create MicroHeater device instance
    microheater = MicroHeater()
    
    # Set parameters for the specific requirements
    microheater.set_parameters(
        line_width=4.0,        # 线宽4μm
        line_spacing=4.0,      # 间距4μm
        array_spacing=1000.0,  # 阵列间距1mm
        array_size=6,          # 6x6阵列
        hilbert_order=6,       # 希尔伯特曲线阶数
        hilbert_step=8.0,     # 希尔伯特曲线步长
        hilbert_margin=0.0     # 希尔伯特曲线边距
    )
    
    # Create top-level cell
    top_cell = microheater.layout.create_cell("MicroHeater_Array_6x6")
    
    # Generate the 6x6 array centered at origin
    print("Generating 6x6 Hilbert curve microheater array...")
    try:
        microheater.create_heater_array(top_cell, 0.0, 0.0)
        print("✓ 6x6 Hilbert curve microheater array generated successfully")
        
    except Exception as e:
        print(f"✗ Array generation failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Save results
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from config import get_gds_path
    
    output_file = get_gds_path("MicroHeater_Array_6x6.gds")
    print(f"Saving to: {output_file}")
    try:
        microheater.layout.write(output_file)
        print("✓ Save successful")
    except Exception as e:
        print(f"✗ Save failed: {e}")
        return
    
    print("=== Complete ===")
    print("Generated structure:")
    print("  - MicroHeater_Array_6x6")
    print("    - 6x6 array of Hilbert curve microheaters")
    print("    - Line width: 4μm")
    print("    - Line spacing: 4μm")
    print("    - Array spacing: 1mm")
    print("    - Centered at origin (0, 0)")


def main_meander_array_4x4():
    """生成 4×4 大单元 × 4×4 小单元 蛇形微加热器阵列（小单元 450μm 方形，线宽/间距 4μm，pad 10μm）"""
    print("=== Generating 4×4 Meander MicroHeater Array (4×4 blocks, 4×4 cells each) ===")
    microheater = MicroHeater()
    microheater.set_parameters(
        line_width=4.0,
        line_spacing=4.0,
    )
    microheater.meander_cell_size = 450.0
    microheater.meander_line_width = 4.0
    microheater.meander_line_spacing = 4.0
    microheater.meander_cell_gap = 10.0
    microheater.meander_pad_size = 10.0
    microheater.meander_block_gap = 10.0
    top_cell = microheater.layout.create_cell("MicroHeater_Meander_4x4")
    print("Generating 4×4 meander array (row angles 0°, 30°, 60°, 90°)...")
    try:
        microheater.create_meander_array_4x4(top_cell, 0.0, 0.0)
        print("✓ 4×4 meander microheater array generated successfully")
    except Exception as e:
        print(f"✗ Array generation failed: {e}")
        import traceback
        traceback.print_exc()
        return
    from config import get_gds_path
    output_file = get_gds_path("MicroHeater_Meander_4x4.gds")
    print(f"Saving to: {output_file}")
    try:
        microheater.layout.write(output_file)
        print("✓ Save successful")
    except Exception as e:
        print(f"✗ Save failed: {e}")
        return
    print("=== Complete ===")
    print("  - 4×4 large blocks, each 4×4 small cells")
    print("  - Small cell: 450 μm square, line 4 μm, spacing 4 μm, gap 10 μm, pads 10 μm")
    print("  - Row angles: 0°, 30°, 60°, 90°")


if __name__ == "__main__":
    main_meander_array_4x4()
