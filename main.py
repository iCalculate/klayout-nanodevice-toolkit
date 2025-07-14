# -*- coding: utf-8 -*-
"""
主程序入口 - 整合所有模块并提供简单的使用示例
Main entry - integrates modules and provides simple usage examples.
"""

import pya
from layout_generator import LayoutGenerator
from gui_interface import show_mosfet_layout_gui

def create_simple_array():
    """创建简单的器件阵列示例

    Example for creating a simple device array.
    """
    print("创建简单的MOSFET阵列...")
    
    # 创建版图生成器
    generator = LayoutGenerator()
    
    # 设置阵列配置
    generator.set_array_config(
        rows=3,
        cols=3,
        spacing_x=100.0,
        spacing_y=100.0,
        start_x=0.0,
        start_y=0.0
    )
    
    # 设置参数扫描配置
    generator.set_scan_config(
        channel_width_range=[3.0, 5.0, 7.0],
        channel_length_range=[10.0, 20.0, 30.0],
        gate_overlap_range=[1.0, 2.0, 3.0],
        scan_type='grid'
    )
    
    # 生成版图
    generator.generate_layout()
    
    # 保存文件
    generator.save_layout("simple_mosfet_array.gds")
    
    # 加载到GUI
    generator.load_to_gui()
    
    # 显示统计信息
    stats = generator.get_statistics()
    print("\n版图统计信息:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    return generator

def create_parameter_scan():
    """创建参数扫描阵列示例

    Example for creating a parameter-scan device array.
    """
    print("创建参数扫描MOSFET阵列...")
    
    # 创建版图生成器
    generator = LayoutGenerator()
    
    # 设置更大的阵列
    generator.set_array_config(
        rows=5,
        cols=5,
        spacing_x=80.0,
        spacing_y=80.0,
        start_x=0.0,
        start_y=0.0
    )
    
    # 设置参数扫描配置
    generator.set_scan_config(
        channel_width_range=[2.0, 3.0, 4.0, 5.0, 6.0],
        channel_length_range=[5.0, 10.0, 15.0, 20.0, 25.0],
        gate_overlap_range=[1.0, 1.5, 2.0],
        scan_type='custom'
    )
    
    # 生成版图
    generator.generate_layout()
    
    # 保存文件
    generator.save_layout("parameter_scan_array.gds")
    
    # 加载到GUI
    generator.load_to_gui()
    
    return generator

def create_custom_device():
    """创建自定义器件示例

    Example for creating a custom device.
    """
    print("创建自定义MOSFET器件...")
    
    from components.mosfet import MOSFET
    
    # 创建单个器件
    device = MOSFET(
        x=0, y=0,
        channel_width=5.0,
        channel_length=20.0,
        gate_overlap=2.0,
        device_label="Custom_Device",
        device_id=1,
        fanout_enabled=True,
        fanout_direction='horizontal'
    )
    
    # 生成器件
    device.generate()
    
    # 获取器件信息
    info = device.get_device_info()
    print(f"器件信息: {info}")
    
    return device

def show_gui():
    """显示GUI界面

    Launch the graphical user interface.
    """
    print("启动GUI界面...")
    return show_mosfet_layout_gui()

def main():
    """主函数"""
    print("=== MOSFET Layout Generator ===")
    print("1. 创建简单阵列")
    print("2. 创建参数扫描阵列")
    print("3. 创建自定义器件")
    print("4. 显示GUI界面")
    print("5. 退出")
    
    try:
        choice = input("请选择操作 (1-5): ").strip()
        
        if choice == '1':
            create_simple_array()
        elif choice == '2':
            create_parameter_scan()
        elif choice == '3':
            create_custom_device()
        elif choice == '4':
            show_gui()
        elif choice == '5':
            print("退出程序")
        else:
            print("无效选择，创建默认简单阵列...")
            create_simple_array()
            
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序执行出错: {e}")

# 直接运行时的默认行为
if __name__ == "__main__":
    # 如果没有GUI环境，直接创建简单阵列
    try:
        create_simple_array()
    except Exception as e:
        print(f"自动创建阵列失败: {e}")
        print("请检查KLayout环境是否正确配置")

# 导出主要函数供其他模块使用
__all__ = [
    'create_simple_array',
    'create_parameter_scan', 
    'create_custom_device',
    'show_gui',
    'main'
] 