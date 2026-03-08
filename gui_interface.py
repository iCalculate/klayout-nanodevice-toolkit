# -*- coding: utf-8 -*-
"""GUI interface for MOSFET layout generation."""

import os
import sys

try:
    import pya
    qt = pya if getattr(pya, "QDialog", None) is not None else None
except ImportError:
    pya = None
    qt = None

if qt is None:
    try:
        from PyQt5 import QtWidgets
        qt = QtWidgets
        pya = None
    except ImportError:
        pass

if qt is None:
    raise ImportError("KLayout(pya+Qt) or PyQt5 is required for GUI.")

try:
    from layout_generator import LayoutGenerator
except Exception:
    LayoutGenerator = None


class MOSFETLayoutGUI:
    def __init__(self):
        self.generator = LayoutGenerator() if LayoutGenerator else None
        self.create_gui()

    def create_gui(self):
        self.dialog = qt.QDialog()
        self.dialog.setWindowTitle("MOSFET Layout Generator")
        self.dialog.resize(600, 800)

        layout = qt.QVBoxLayout()
        tabs = qt.QTabWidget()
        tabs.addTab(self.create_array_tab(), "Array Configuration")
        tabs.addTab(self.create_scan_tab(), "Parameter Scan")
        tabs.addTab(self.create_device_tab(), "Device Configuration")
        tabs.addTab(self.create_output_tab(), "Output Settings")
        layout.addWidget(tabs)

        button_layout = qt.QHBoxLayout()
        generate_btn = qt.QPushButton("Generate Layout")
        generate_btn.clicked.connect(self.generate_layout)
        preview_btn = qt.QPushButton("Preview")
        preview_btn.clicked.connect(self.preview_layout)
        cancel_btn = qt.QPushButton("Cancel")
        cancel_btn.clicked.connect(self.dialog.reject)

        button_layout.addWidget(generate_btn)
        button_layout.addWidget(preview_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        self.dialog.setLayout(layout)

    def create_array_tab(self):
        widget = qt.QWidget()
        layout = qt.QVBoxLayout()

        size_group = qt.QGroupBox("Array Size")
        size_layout = qt.QHBoxLayout()
        size_layout.addWidget(qt.QLabel("Rows:"))
        self.rows_spin = qt.QSpinBox()
        self.rows_spin.setRange(1, 100)
        self.rows_spin.setValue(3)
        size_layout.addWidget(self.rows_spin)
        size_layout.addWidget(qt.QLabel("Columns:"))
        self.cols_spin = qt.QSpinBox()
        self.cols_spin.setRange(1, 100)
        self.cols_spin.setValue(3)
        size_layout.addWidget(self.cols_spin)
        size_group.setLayout(size_layout)
        layout.addWidget(size_group)

        spacing_group = qt.QGroupBox("Spacing")
        spacing_layout = qt.QFormLayout()
        self.spacing_x_spin = qt.QDoubleSpinBox()
        self.spacing_x_spin.setRange(1, 10000)
        self.spacing_x_spin.setValue(100)
        self.spacing_x_spin.setSuffix(" um")
        spacing_layout.addRow("X Spacing:", self.spacing_x_spin)
        self.spacing_y_spin = qt.QDoubleSpinBox()
        self.spacing_y_spin.setRange(1, 10000)
        self.spacing_y_spin.setValue(100)
        self.spacing_y_spin.setSuffix(" um")
        spacing_layout.addRow("Y Spacing:", self.spacing_y_spin)
        spacing_group.setLayout(spacing_layout)
        layout.addWidget(spacing_group)

        start_group = qt.QGroupBox("Start Position")
        start_layout = qt.QFormLayout()
        self.start_x_spin = qt.QDoubleSpinBox()
        self.start_x_spin.setRange(-10000, 10000)
        self.start_x_spin.setValue(0)
        self.start_x_spin.setSuffix(" um")
        start_layout.addRow("X Position:", self.start_x_spin)
        self.start_y_spin = qt.QDoubleSpinBox()
        self.start_y_spin.setRange(-10000, 10000)
        self.start_y_spin.setValue(0)
        self.start_y_spin.setSuffix(" um")
        start_layout.addRow("Y Position:", self.start_y_spin)
        start_group.setLayout(start_layout)
        layout.addWidget(start_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_scan_tab(self):
        widget = qt.QWidget()
        layout = qt.QVBoxLayout()

        scan_type_group = qt.QGroupBox("Scan Type")
        scan_type_layout = qt.QVBoxLayout()
        self.scan_type_combo = qt.QComboBox()
        self.scan_type_combo.addItems(["Grid", "Random", "Custom"])
        scan_type_layout.addWidget(self.scan_type_combo)
        scan_type_group.setLayout(scan_type_layout)
        layout.addWidget(scan_type_group)

        width_group = qt.QGroupBox("Channel Width Range")
        width_layout = qt.QHBoxLayout()
        width_layout.addWidget(qt.QLabel("Min:"))
        self.width_min_spin = qt.QDoubleSpinBox()
        self.width_min_spin.setRange(0.001, 1000)
        self.width_min_spin.setValue(3.0)
        self.width_min_spin.setSuffix(" um")
        width_layout.addWidget(self.width_min_spin)
        width_layout.addWidget(qt.QLabel("Max:"))
        self.width_max_spin = qt.QDoubleSpinBox()
        self.width_max_spin.setRange(0.001, 1000)
        self.width_max_spin.setValue(7.0)
        self.width_max_spin.setSuffix(" um")
        width_layout.addWidget(self.width_max_spin)
        width_layout.addWidget(qt.QLabel("Steps:"))
        self.width_steps_spin = qt.QSpinBox()
        self.width_steps_spin.setRange(1, 100)
        self.width_steps_spin.setValue(3)
        width_layout.addWidget(self.width_steps_spin)
        width_group.setLayout(width_layout)
        layout.addWidget(width_group)

        length_group = qt.QGroupBox("Channel Length Range")
        length_layout = qt.QHBoxLayout()
        length_layout.addWidget(qt.QLabel("Min:"))
        self.length_min_spin = qt.QDoubleSpinBox()
        self.length_min_spin.setRange(0.001, 1000)
        self.length_min_spin.setValue(10.0)
        self.length_min_spin.setSuffix(" um")
        length_layout.addWidget(self.length_min_spin)
        length_layout.addWidget(qt.QLabel("Max:"))
        self.length_max_spin = qt.QDoubleSpinBox()
        self.length_max_spin.setRange(0.001, 1000)
        self.length_max_spin.setValue(30.0)
        self.length_max_spin.setSuffix(" um")
        length_layout.addWidget(self.length_max_spin)
        length_layout.addWidget(qt.QLabel("Steps:"))
        self.length_steps_spin = qt.QSpinBox()
        self.length_steps_spin.setRange(1, 100)
        self.length_steps_spin.setValue(3)
        length_layout.addWidget(self.length_steps_spin)
        length_group.setLayout(length_layout)
        layout.addWidget(length_group)

        overlap_group = qt.QGroupBox("Gate Overlap Range")
        overlap_layout = qt.QHBoxLayout()
        overlap_layout.addWidget(qt.QLabel("Min:"))
        self.overlap_min_spin = qt.QDoubleSpinBox()
        self.overlap_min_spin.setRange(0.001, 100)
        self.overlap_min_spin.setValue(1.0)
        self.overlap_min_spin.setSuffix(" um")
        overlap_layout.addWidget(self.overlap_min_spin)
        overlap_layout.addWidget(qt.QLabel("Max:"))
        self.overlap_max_spin = qt.QDoubleSpinBox()
        self.overlap_max_spin.setRange(0.001, 100)
        self.overlap_max_spin.setValue(3.0)
        self.overlap_max_spin.setSuffix(" um")
        overlap_layout.addWidget(self.overlap_max_spin)
        overlap_layout.addWidget(qt.QLabel("Steps:"))
        self.overlap_steps_spin = qt.QSpinBox()
        self.overlap_steps_spin.setRange(1, 100)
        self.overlap_steps_spin.setValue(3)
        overlap_layout.addWidget(self.overlap_steps_spin)
        overlap_group.setLayout(overlap_layout)
        layout.addWidget(overlap_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_device_tab(self):
        widget = qt.QWidget()
        layout = qt.QVBoxLayout()

        electrode_group = qt.QGroupBox("Electrode Configuration")
        electrode_layout = qt.QVBoxLayout()
        self.bottom_gate_check = qt.QCheckBox("Enable Bottom Gate")
        self.bottom_gate_check.setChecked(True)
        electrode_layout.addWidget(self.bottom_gate_check)
        self.top_gate_check = qt.QCheckBox("Enable Top Gate")
        self.top_gate_check.setChecked(True)
        electrode_layout.addWidget(self.top_gate_check)
        self.source_drain_check = qt.QCheckBox("Enable Source/Drain")
        self.source_drain_check.setChecked(True)
        electrode_layout.addWidget(self.source_drain_check)
        electrode_group.setLayout(electrode_layout)
        layout.addWidget(electrode_group)

        fanout_group = qt.QGroupBox("Fanout Configuration")
        fanout_layout = qt.QVBoxLayout()
        self.fanout_check = qt.QCheckBox("Enable Fanout")
        self.fanout_check.setChecked(True)
        fanout_layout.addWidget(self.fanout_check)
        fanout_layout.addWidget(qt.QLabel("Fanout Direction:"))
        self.fanout_direction_combo = qt.QComboBox()
        self.fanout_direction_combo.addItems(["Horizontal", "Vertical"])
        fanout_layout.addWidget(self.fanout_direction_combo)
        fanout_group.setLayout(fanout_layout)
        layout.addWidget(fanout_group)

        label_group = qt.QGroupBox("Label Configuration")
        label_layout = qt.QVBoxLayout()
        self.device_labels_check = qt.QCheckBox("Show Device Labels")
        self.device_labels_check.setChecked(True)
        label_layout.addWidget(self.device_labels_check)
        self.parameter_labels_check = qt.QCheckBox("Show Parameter Labels")
        self.parameter_labels_check.setChecked(True)
        label_layout.addWidget(self.parameter_labels_check)
        label_group.setLayout(label_layout)
        layout.addWidget(label_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_output_tab(self):
        widget = qt.QWidget()
        layout = qt.QVBoxLayout()

        file_group = qt.QGroupBox("File Configuration")
        file_layout = qt.QFormLayout()
        self.filename_edit = qt.QLineEdit("mosfet_array.gds")
        file_layout.addRow("Output Filename:", self.filename_edit)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        display_group = qt.QGroupBox("Display Configuration")
        display_layout = qt.QVBoxLayout()
        self.auto_load_check = qt.QCheckBox("Auto-load to GUI")
        self.auto_load_check.setChecked(True)
        display_layout.addWidget(self.auto_load_check)
        self.show_stats_check = qt.QCheckBox("Show Statistics")
        self.show_stats_check.setChecked(True)
        display_layout.addWidget(self.show_stats_check)
        display_group.setLayout(display_layout)
        layout.addWidget(display_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def get_array_config(self):
        return {
            'rows': self.rows_spin.value(),
            'cols': self.cols_spin.value(),
            'spacing_x': self.spacing_x_spin.value(),
            'spacing_y': self.spacing_y_spin.value(),
            'start_x': self.start_x_spin.value(),
            'start_y': self.start_y_spin.value(),
        }

    def get_scan_config(self):
        width_range = self.generate_parameter_range(
            self.width_min_spin.value(), self.width_max_spin.value(), self.width_steps_spin.value()
        )
        length_range = self.generate_parameter_range(
            self.length_min_spin.value(), self.length_max_spin.value(), self.length_steps_spin.value()
        )
        overlap_range = self.generate_parameter_range(
            self.overlap_min_spin.value(), self.overlap_max_spin.value(), self.overlap_steps_spin.value()
        )
        return {
            'channel_width_range': width_range,
            'channel_length_range': length_range,
            'gate_overlap_range': overlap_range,
            'scan_type': self.scan_type_combo.currentText().lower(),
        }

    def get_device_config(self):
        return {
            'enable_bottom_gate': self.bottom_gate_check.isChecked(),
            'enable_top_gate': self.top_gate_check.isChecked(),
            'enable_source_drain': self.source_drain_check.isChecked(),
            'fanout_enabled': self.fanout_check.isChecked(),
            'fanout_direction': self.fanout_direction_combo.currentText().lower(),
            'show_device_labels': self.device_labels_check.isChecked(),
            'show_parameter_labels': self.parameter_labels_check.isChecked(),
            'show_alignment_marks': True,
        }

    def generate_parameter_range(self, min_val, max_val, steps):
        if steps == 1:
            return [min_val]
        step_size = (max_val - min_val) / (steps - 1)
        return [min_val + i * step_size for i in range(steps)]

    def generate_layout(self):
        try:
            if self.generator is None:
                qt.QMessageBox.information(
                    self.dialog,
                    "Info",
                    "Layout generation requires running inside KLayout environment.",
                )
                return

            array_config = self.get_array_config()
            scan_config = self.get_scan_config()
            device_config = self.get_device_config()

            self.generator.set_array_config(**array_config)
            self.generator.set_scan_config(**scan_config)
            self.generator.set_device_config(**device_config)
            self.generator.generate_layout()

            from config import get_gds_path
            filename = self.filename_edit.text().strip() or "mosfet_array.gds"
            if not os.path.isabs(filename):
                filename = get_gds_path(filename)
            self.generator.save_layout(filename)

            if self.auto_load_check.isChecked():
                self.generator.load_to_gui(filename)

            if self.show_stats_check.isChecked():
                self.show_statistics(self.generator.get_statistics())

            qt.QMessageBox.information(self.dialog, "Success", "Layout generated successfully!")
        except Exception as e:
            qt.QMessageBox.critical(self.dialog, "Error", f"Failed to generate layout: {str(e)}")

    def preview_layout(self):
        try:
            if self.generator is None:
                qt.QMessageBox.information(
                    self.dialog,
                    "Info",
                    "Preview requires running inside KLayout environment.",
                )
                return

            array_config = self.get_array_config()
            scan_config = self.get_scan_config()
            device_config = self.get_device_config()

            self.generator.set_array_config(**array_config)
            self.generator.set_scan_config(**scan_config)
            self.generator.set_device_config(**device_config)

            stats = {
                'array_size': f"{array_config['rows']}x{array_config['cols']}",
                'total_devices': array_config['rows'] * array_config['cols'],
                'scan_type': scan_config['scan_type'],
                'layout_size': {
                    'width': array_config['cols'] * array_config['spacing_x'],
                    'height': array_config['rows'] * array_config['spacing_y'],
                },
            }

            preview_text = f"""
Layout Preview:
- Array Size: {stats['array_size']}
- Total Devices: {stats['total_devices']}
- Scan Type: {stats['scan_type']}
- Layout Size: {stats['layout_size']['width']:.1f} x {stats['layout_size']['height']:.1f} um
- Parameter Ranges:
  * Width: {min(scan_config['channel_width_range']):.3f}-{max(scan_config['channel_width_range']):.3f} um
  * Length: {min(scan_config['channel_length_range']):.3f}-{max(scan_config['channel_length_range']):.3f} um
"""
            qt.QMessageBox.information(self.dialog, "Preview", preview_text)
        except Exception as e:
            qt.QMessageBox.critical(self.dialog, "Error", f"Failed to preview layout: {str(e)}")

    def show_statistics(self, stats):
        stats_text = f"""
Layout Statistics:
- Total Devices: {stats['total_devices']}
- Array Size: {stats['array_size']}
- Scan Type: {stats['scan_type']}
- Layout Size: {stats['layout_size']['width']:.1f} x {stats['layout_size']['height']:.1f} um
- Parameter Ranges:
  * Width: {stats['parameter_ranges']['channel_width']}
  * Length: {stats['parameter_ranges']['channel_length']}
  * Gate Overlap: {stats['parameter_ranges']['gate_overlap']}
"""
        qt.QMessageBox.information(self.dialog, "Statistics", stats_text)

    def show(self):
        return self.dialog.exec_()


def show_mosfet_layout_gui():
    gui = MOSFETLayoutGUI()
    return gui.show()


if __name__ == "__main__":
    if pya is None:
        from PyQt5.QtWidgets import QApplication
        app = QApplication(sys.argv)
    else:
        app = None

    show_mosfet_layout_gui()

    if app is not None:
        sys.exit(app.exec_())
