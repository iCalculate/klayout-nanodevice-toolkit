# -*- coding: utf-8 -*-
"""
GUI界面模块 - 提供用户友好的参数配置界面
GUI interface module providing a user-friendly parameter configuration UI.
"""

import pya
from layout_generator import LayoutGenerator

class MOSFETLayoutGUI:
    """MOSFET版图生成器GUI界面

    GUI interface for the MOSFET layout generator.
    """
    
    def __init__(self):
        self.generator = LayoutGenerator()
        self.create_gui()
    
    def create_gui(self):
        """创建GUI界面

        Create the GUI interface.
        """
        # 创建主窗口
        self.dialog = pya.QDialog()
        self.dialog.setWindowTitle("MOSFET Layout Generator")
        self.dialog.resize(600, 800)
        
        # 创建主布局
        layout = pya.QVBoxLayout()
        
        # 创建选项卡
        tabs = pya.QTabWidget()
        
        # 阵列配置选项卡
        array_tab = self.create_array_tab()
        tabs.addTab(array_tab, "Array Configuration")
        
        # 参数扫描选项卡
        scan_tab = self.create_scan_tab()
        tabs.addTab(scan_tab, "Parameter Scan")
        
        # 器件配置选项卡
        device_tab = self.create_device_tab()
        tabs.addTab(device_tab, "Device Configuration")
        
        # 输出配置选项卡
        output_tab = self.create_output_tab()
        tabs.addTab(output_tab, "Output Settings")
        
        layout.addWidget(tabs)
        
        # 创建按钮
        button_layout = pya.QHBoxLayout()
        
        generate_btn = pya.QPushButton("Generate Layout")
        generate_btn.clicked.connect(self.generate_layout)
        
        preview_btn = pya.QPushButton("Preview")
        preview_btn.clicked.connect(self.preview_layout)
        
        cancel_btn = pya.QPushButton("Cancel")
        cancel_btn.clicked.connect(self.dialog.reject)
        
        button_layout.addWidget(generate_btn)
        button_layout.addWidget(preview_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.dialog.setLayout(layout)
    
    def create_array_tab(self):
        """创建阵列配置选项卡"""
        widget = pya.QWidget()
        layout = pya.QVBoxLayout()
        
        # 阵列大小
        size_group = pya.QGroupBox("Array Size")
        size_layout = pya.QHBoxLayout()
        
        size_layout.addWidget(pya.QLabel("Rows:"))
        self.rows_spin = pya.QSpinBox()
        self.rows_spin.setRange(1, 20)
        self.rows_spin.setValue(3)
        size_layout.addWidget(self.rows_spin)
        
        size_layout.addWidget(pya.QLabel("Columns:"))
        self.cols_spin = pya.QSpinBox()
        self.cols_spin.setRange(1, 20)
        self.cols_spin.setValue(3)
        size_layout.addWidget(self.cols_spin)
        
        size_group.setLayout(size_layout)
        layout.addWidget(size_group)
        
        # 间距配置
        spacing_group = pya.QGroupBox("Spacing")
        spacing_layout = pya.QFormLayout()
        
        self.spacing_x_spin = pya.QDoubleSpinBox()
        self.spacing_x_spin.setRange(10, 1000)
        self.spacing_x_spin.setValue(100)
        self.spacing_x_spin.setSuffix(" μm")
        spacing_layout.addRow("X Spacing:", self.spacing_x_spin)
        
        self.spacing_y_spin = pya.QDoubleSpinBox()
        self.spacing_y_spin.setRange(10, 1000)
        self.spacing_y_spin.setValue(100)
        self.spacing_y_spin.setSuffix(" μm")
        spacing_layout.addRow("Y Spacing:", self.spacing_y_spin)
        
        spacing_group.setLayout(spacing_layout)
        layout.addWidget(spacing_group)
        
        # 起始位置
        start_group = pya.QGroupBox("Start Position")
        start_layout = pya.QFormLayout()
        
        self.start_x_spin = pya.QDoubleSpinBox()
        self.start_x_spin.setRange(-1000, 1000)
        self.start_x_spin.setValue(0)
        self.start_x_spin.setSuffix(" μm")
        start_layout.addRow("X Position:", self.start_x_spin)
        
        self.start_y_spin = pya.QDoubleSpinBox()
        self.start_y_spin.setRange(-1000, 1000)
        self.start_y_spin.setValue(0)
        self.start_y_spin.setSuffix(" μm")
        start_layout.addRow("Y Position:", self.start_y_spin)
        
        start_group.setLayout(start_layout)
        layout.addWidget(start_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_scan_tab(self):
        """创建参数扫描选项卡"""
        widget = pya.QWidget()
        layout = pya.QVBoxLayout()
        
        # 扫描类型
        scan_type_group = pya.QGroupBox("Scan Type")
        scan_type_layout = pya.QVBoxLayout()
        
        self.scan_type_combo = pya.QComboBox()
        self.scan_type_combo.addItems(["Grid", "Random", "Custom"])
        scan_type_layout.addWidget(self.scan_type_combo)
        
        scan_type_group.setLayout(scan_type_layout)
        layout.addWidget(scan_type_group)
        
        # 沟道宽度范围
        width_group = pya.QGroupBox("Channel Width Range")
        width_layout = pya.QHBoxLayout()
        
        width_layout.addWidget(pya.QLabel("Min:"))
        self.width_min_spin = pya.QDoubleSpinBox()
        self.width_min_spin.setRange(0.1, 100)
        self.width_min_spin.setValue(3.0)
        self.width_min_spin.setSuffix(" μm")
        width_layout.addWidget(self.width_min_spin)
        
        width_layout.addWidget(pya.QLabel("Max:"))
        self.width_max_spin = pya.QDoubleSpinBox()
        self.width_max_spin.setRange(0.1, 100)
        self.width_max_spin.setValue(7.0)
        self.width_max_spin.setSuffix(" μm")
        width_layout.addWidget(self.width_max_spin)
        
        width_layout.addWidget(pya.QLabel("Steps:"))
        self.width_steps_spin = pya.QSpinBox()
        self.width_steps_spin.setRange(1, 10)
        self.width_steps_spin.setValue(3)
        width_layout.addWidget(self.width_steps_spin)
        
        width_group.setLayout(width_layout)
        layout.addWidget(width_group)
        
        # 沟道长度范围
        length_group = pya.QGroupBox("Channel Length Range")
        length_layout = pya.QHBoxLayout()
        
        length_layout.addWidget(pya.QLabel("Min:"))
        self.length_min_spin = pya.QDoubleSpinBox()
        self.length_min_spin.setRange(0.1, 100)
        self.length_min_spin.setValue(10.0)
        self.length_min_spin.setSuffix(" μm")
        length_layout.addWidget(self.length_min_spin)
        
        length_layout.addWidget(pya.QLabel("Max:"))
        self.length_max_spin = pya.QDoubleSpinBox()
        self.length_max_spin.setRange(0.1, 100)
        self.length_max_spin.setValue(30.0)
        self.length_max_spin.setSuffix(" μm")
        length_layout.addWidget(self.length_max_spin)
        
        length_layout.addWidget(pya.QLabel("Steps:"))
        self.length_steps_spin = pya.QSpinBox()
        self.length_steps_spin.setRange(1, 10)
        self.length_steps_spin.setValue(3)
        length_layout.addWidget(self.length_steps_spin)
        
        length_group.setLayout(length_layout)
        layout.addWidget(length_group)
        
        # 栅极重叠范围
        overlap_group = pya.QGroupBox("Gate Overlap Range")
        overlap_layout = pya.QHBoxLayout()
        
        overlap_layout.addWidget(pya.QLabel("Min:"))
        self.overlap_min_spin = pya.QDoubleSpinBox()
        self.overlap_min_spin.setRange(0.1, 10)
        self.overlap_min_spin.setValue(1.0)
        self.overlap_min_spin.setSuffix(" μm")
        overlap_layout.addWidget(self.overlap_min_spin)
        
        overlap_layout.addWidget(pya.QLabel("Max:"))
        self.overlap_max_spin = pya.QDoubleSpinBox()
        self.overlap_max_spin.setRange(0.1, 10)
        self.overlap_max_spin.setValue(3.0)
        self.overlap_max_spin.setSuffix(" μm")
        overlap_layout.addWidget(self.overlap_max_spin)
        
        overlap_layout.addWidget(pya.QLabel("Steps:"))
        self.overlap_steps_spin = pya.QSpinBox()
        self.overlap_steps_spin.setRange(1, 10)
        self.overlap_steps_spin.setValue(3)
        overlap_layout.addWidget(self.overlap_steps_spin)
        
        overlap_group.setLayout(overlap_layout)
        layout.addWidget(overlap_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_device_tab(self):
        """创建设备配置选项卡"""
        widget = pya.QWidget()
        layout = pya.QVBoxLayout()
        
        # 电极配置
        electrode_group = pya.QGroupBox("Electrode Configuration")
        electrode_layout = pya.QVBoxLayout()
        
        self.bottom_gate_check = pya.QCheckBox("Enable Bottom Gate")
        self.bottom_gate_check.setChecked(True)
        electrode_layout.addWidget(self.bottom_gate_check)
        
        self.top_gate_check = pya.QCheckBox("Enable Top Gate")
        self.top_gate_check.setChecked(True)
        electrode_layout.addWidget(self.top_gate_check)
        
        self.source_drain_check = pya.QCheckBox("Enable Source/Drain")
        self.source_drain_check.setChecked(True)
        electrode_layout.addWidget(self.source_drain_check)
        
        electrode_group.setLayout(electrode_layout)
        layout.addWidget(electrode_group)
        
        # 扇出配置
        fanout_group = pya.QGroupBox("Fanout Configuration")
        fanout_layout = pya.QVBoxLayout()
        
        self.fanout_check = pya.QCheckBox("Enable Fanout")
        self.fanout_check.setChecked(True)
        fanout_layout.addWidget(self.fanout_check)
        
        fanout_layout.addWidget(pya.QLabel("Fanout Direction:"))
        self.fanout_direction_combo = pya.QComboBox()
        self.fanout_direction_combo.addItems(["Horizontal", "Vertical"])
        fanout_layout.addWidget(self.fanout_direction_combo)
        
        fanout_group.setLayout(fanout_layout)
        layout.addWidget(fanout_group)
        
        # 标签配置
        label_group = pya.QGroupBox("Label Configuration")
        label_layout = pya.QVBoxLayout()
        
        self.device_labels_check = pya.QCheckBox("Show Device Labels")
        self.device_labels_check.setChecked(True)
        label_layout.addWidget(self.device_labels_check)
        
        self.parameter_labels_check = pya.QCheckBox("Show Parameter Labels")
        self.parameter_labels_check.setChecked(True)
        label_layout.addWidget(self.parameter_labels_check)
        
        label_group.setLayout(label_layout)
        layout.addWidget(label_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_output_tab(self):
        """创建输出配置选项卡"""
        widget = pya.QWidget()
        layout = pya.QVBoxLayout()
        
        # 文件配置
        file_group = pya.QGroupBox("File Configuration")
        file_layout = pya.QFormLayout()
        
        self.filename_edit = pya.QLineEdit("mosfet_array.gds")
        file_layout.addRow("Output Filename:", self.filename_edit)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # 显示配置
        display_group = pya.QGroupBox("Display Configuration")
        display_layout = pya.QVBoxLayout()
        
        self.auto_load_check = pya.QCheckBox("Auto-load to GUI")
        self.auto_load_check.setChecked(True)
        display_layout.addWidget(self.auto_load_check)
        
        self.show_stats_check = pya.QCheckBox("Show Statistics")
        self.show_stats_check.setChecked(True)
        display_layout.addWidget(self.show_stats_check)
        
        display_group.setLayout(display_layout)
        layout.addWidget(display_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def get_array_config(self):
        """获取阵列配置"""
        return {
            'rows': self.rows_spin.value(),
            'cols': self.cols_spin.value(),
            'spacing_x': self.spacing_x_spin.value(),
            'spacing_y': self.spacing_y_spin.value(),
            'start_x': self.start_x_spin.value(),
            'start_y': self.start_y_spin.value()
        }
    
    def get_scan_config(self):
        """获取扫描配置"""
        # 生成参数范围
        width_range = self.generate_parameter_range(
            self.width_min_spin.value(),
            self.width_max_spin.value(),
            self.width_steps_spin.value()
        )
        
        length_range = self.generate_parameter_range(
            self.length_min_spin.value(),
            self.length_max_spin.value(),
            self.length_steps_spin.value()
        )
        
        overlap_range = self.generate_parameter_range(
            self.overlap_min_spin.value(),
            self.overlap_max_spin.value(),
            self.overlap_steps_spin.value()
        )
        
        return {
            'channel_width_range': width_range,
            'channel_length_range': length_range,
            'gate_overlap_range': overlap_range,
            'scan_type': self.scan_type_combo.currentText().lower()
        }
    
    def generate_parameter_range(self, min_val, max_val, steps):
        """生成参数范围"""
        if steps == 1:
            return [min_val]
        
        step_size = (max_val - min_val) / (steps - 1)
        return [min_val + i * step_size for i in range(steps)]
    
    def generate_layout(self):
        """生成版图"""
        try:
            # 获取配置
            array_config = self.get_array_config()
            scan_config = self.get_scan_config()
            
            # 设置配置
            self.generator.set_array_config(**array_config)
            self.generator.set_scan_config(**scan_config)
            
            # 生成版图
            self.generator.generate_layout()
            
            # 保存文件
            filename = self.filename_edit.text()
            self.generator.save_layout(filename)
            
            # 自动加载到GUI
            if self.auto_load_check.isChecked():
                self.generator.load_to_gui()
            
            # 显示统计信息
            if self.show_stats_check.isChecked():
                stats = self.generator.get_statistics()
                self.show_statistics(stats)
            
            pya.QMessageBox.information(self.dialog, "Success", "Layout generated successfully!")
            
        except Exception as e:
            pya.QMessageBox.critical(self.dialog, "Error", f"Failed to generate layout: {str(e)}")
    
    def preview_layout(self):
        """预览版图"""
        try:
            # 获取配置
            array_config = self.get_array_config()
            scan_config = self.get_scan_config()
            
            # 设置配置
            self.generator.set_array_config(**array_config)
            self.generator.set_scan_config(**scan_config)
            
            # 显示预览信息
            stats = self.generator.get_statistics()
            preview_text = f"""
Layout Preview:
- Array Size: {stats['array_size']}
- Total Devices: {stats['total_devices']}
- Scan Type: {stats['scan_type']}
- Layout Size: {stats['layout_size']['width']:.1f} × {stats['layout_size']['height']:.1f} μm
- Parameter Ranges:
  * Width: {min(scan_config['channel_width_range']):.1f}-{max(scan_config['channel_width_range']):.1f} μm
  * Length: {min(scan_config['channel_length_range']):.1f}-{max(scan_config['channel_length_range']):.1f} μm
            """
            
            pya.QMessageBox.information(self.dialog, "Preview", preview_text)
            
        except Exception as e:
            pya.QMessageBox.critical(self.dialog, "Error", f"Failed to preview layout: {str(e)}")
    
    def show_statistics(self, stats):
        """显示统计信息"""
        stats_text = f"""
Layout Statistics:
- Total Devices: {stats['total_devices']}
- Array Size: {stats['array_size']}
- Scan Type: {stats['scan_type']}
- Layout Size: {stats['layout_size']['width']:.1f} × {stats['layout_size']['height']:.1f} μm
- Parameter Ranges:
  * Width: {stats['parameter_ranges']['channel_width']}
  * Length: {stats['parameter_ranges']['channel_length']}
  * Gate Overlap: {stats['parameter_ranges']['gate_overlap']}
        """
        
        pya.QMessageBox.information(self.dialog, "Statistics", stats_text)
    
    def show(self):
        """显示GUI界面

        Show the GUI window.
        """
        return self.dialog.exec_()

def show_mosfet_layout_gui():
    """显示MOSFET版图生成器GUI

    Display the MOSFET layout generator GUI.
    """
    gui = MOSFETLayoutGUI()
    return gui.show()

# 主函数
if __name__ == "__main__":
    show_mosfet_layout_gui() 