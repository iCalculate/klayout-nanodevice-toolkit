"""
对准标记工具模块
基于已有版图文件创建对准标记
"""

import klayout.db as db
import os


class AlignmentMark:
    """基于已有版图文件的对准标记类"""
    
    def __init__(self, layout=None):
        """
        初始化对准标记工具
        
        Args:
            layout: KLayout数据库对象，如果为None则创建新的
        """
        if layout is None:
            self.layout = db.Layout()
        else:
            self.layout = layout
        
        # 默认对准标记文件路径
        self.default_mark_path = os.path.join("utils", "layoutLib", "AlignmentMark_1.gds")
    
    def load_gds_file(self, gds_file_path, cell_name=None):
        """
        加载GDS文件并返回指定单元
        
        Args:
            gds_file_path: GDS文件路径
            cell_name: 单元名称，如果为None则返回第一个单元
            
        Returns:
            Cell对象
        """
        if not os.path.exists(gds_file_path):
            raise FileNotFoundError(f"GDS文件不存在: {gds_file_path}")
        
        # 创建新的布局来读取GDS文件
        temp_layout = db.Layout()
        temp_layout.read(gds_file_path)
        
        # 获取所有单元
        cells = []
        for i in range(temp_layout.cells()):
            cell = temp_layout.cell(i)
            cells.append(cell)
        
        if not cells:
            raise ValueError(f"GDS文件中没有找到单元: {gds_file_path}")
        
        # 选择要加载的单元
        if cell_name is None:
            target_cell = cells[0]
        else:
            target_cell = None
            for cell in cells:
                if cell.name == cell_name:
                    target_cell = cell
                    break
            
            if target_cell is None:
                raise ValueError(f"未找到指定单元: {cell_name}")
        
        # 将单元复制到当前布局 - 简化版本，只复制实例
        new_cell = self.layout.create_cell(target_cell.name)
        
        # 复制所有子单元实例
        for inst in target_cell.each_inst():
            new_cell.insert(inst)
        
        return new_cell
    
    def create_text(self, text, position, layer=1, size=10000):
        """
        创建文本标签
        
        Args:
            text: 文本内容
            position: 位置 (x, y)
            layer: 图层
            size: 字体大小
            
        Returns:
            Cell对象
        """
        text_cell = self.layout.create_cell(f"TEXT_{text}")
        
        # 创建文本形状
        text_shape = db.Text(text, db.Trans(db.Point(int(position[0]), int(position[1]))))
        text_shape.size = size
        
        # 获取或创建图层
        text_layer = self.layout.layer(layer, 0, f"Text_Layer_{layer}")
        text_cell.shapes(text_layer).insert(text_shape)
        
        return text_cell
    
    def create_four_quadrant_marks(self, positions=None, mark_file=None, spacing=1000000):
        """
        创建四个象限的对准标记
        
        Args:
            positions: 四个位置列表 [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]
                      如果为None，则基于原点对称生成
            mark_file: 对准标记GDS文件路径，如果为None则使用默认文件
            spacing: 默认间距（当positions为None时使用）
            
        Returns:
            Cell对象（包含四个象限的对准标记）
        """
        if mark_file is None:
            mark_file = self.default_mark_path
        
        if not os.path.exists(mark_file):
            raise FileNotFoundError(f"默认对准标记文件不存在: {mark_file}")
        
        # 创建主单元
        main_cell = self.layout.create_cell("FOUR_QUADRANT_ALIGNMENT_MARKS")
        
        # 确定四个位置
        if positions is None:
            # 基于原点对称生成四个位置
            positions = [
                (spacing, spacing),      # 右上 (NE)
                (-spacing, spacing),     # 左上 (NW)
                (-spacing, -spacing),    # 左下 (SW)
                (spacing, -spacing)      # 右下 (SE)
            ]
        
        # 象限标签
        labels = ["NE", "NW", "SW", "SE"]
        
        # 加载对准标记
        mark_cell = self.load_gds_file(mark_file)
        
        # 创建四个象限的对准标记
        for i, (x, y) in enumerate(positions):
            # 插入对准标记实例
            main_cell.insert(db.CellInstArray(
                mark_cell.cell_index(),
                db.Trans(db.Point(int(x), int(y)))
            ))
            
            # 创建象限标签
            label_cell = self.create_text(
                labels[i],
                (x, y + 50000),  # 标签位置稍微偏移
                layer=1,
                size=20000
            )
            
            # 插入标签实例
            main_cell.insert(db.CellInstArray(
                label_cell.cell_index(),
                db.Trans(db.Point(int(x), int(y + 50000)))
            ))
        
        return main_cell
    
    def create_single_mark(self, position=(0, 0), mark_file=None):
        """
        创建单个对准标记
        
        Args:
            position: 位置 (x, y)
            mark_file: 对准标记GDS文件路径，如果为None则使用默认文件
            
        Returns:
            Cell对象
        """
        if mark_file is None:
            mark_file = self.default_mark_path
        
        if not os.path.exists(mark_file):
            raise FileNotFoundError(f"默认对准标记文件不存在: {mark_file}")
        
        # 创建主单元
        main_cell = self.layout.create_cell("SINGLE_ALIGNMENT_MARK")
        
        # 加载对准标记
        mark_cell = self.load_gds_file(mark_file)
        
        # 插入对准标记实例
        main_cell.insert(db.CellInstArray(
            mark_cell.cell_index(),
            db.Trans(db.Point(int(position[0]), int(position[1])))
        ))
        
        return main_cell
    
    def save_to_gds(self, filename, cell=None):
        """
        保存到GDS文件
        
        Args:
            filename: 输出文件名
            cell: 要保存的单元，如果为None则保存整个布局
        """
        if cell is not None:
            # 直接保存整个布局（包含所有单元）
            self.layout.write(filename)
        else:
            # 保存整个布局
            self.layout.write(filename)


def main():
    """主函数 - 演示对准标记功能"""
    print("对准标记工具演示")
    print("=" * 30)
    
    # 创建对准标记工具
    align_mark = AlignmentMark()
    
    try:
        # 创建四个象限的对准标记
        print("创建四个象限的对准标记...")
        four_marks = align_mark.create_four_quadrant_marks()
        align_mark.save_to_gds("TEST_ALIGNMENT_UTILS.gds", four_marks)
        print("四个象限对准标记已保存到: TEST_ALIGNMENT_UTILS.gds")
        
        print("\n对准标记工具演示完成！")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
