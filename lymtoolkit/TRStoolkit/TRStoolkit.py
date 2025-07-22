# $description: TRS-toolkit
# $version: v0.1
# $show-in-menu
# $priority: 1
import pya
from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QComboBox, QPushButton, QFormLayout,
    QHBoxLayout, QVBoxLayout, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt

class TransformDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Transform Selected Shapes")
        self.setMinimumWidth(350)

        # 控件定义
        self.mode = QComboBox()
        self.mode.addItems(["Translate", "Rotate", "Scale"])
        self.dx_input = QLineEdit("0.0")
        self.dy_input = QLineEdit("0.0")
        self.angle_input = QLineEdit("0.0")
        self.scale_input = QLineEdit("1.0")
        self.cx_input = QLineEdit("0.0")
        self.cy_input = QLineEdit("0.0")
        self.run_btn = QPushButton("Apply")
        self.cancel_btn = QPushButton("Cancel")

        # 表单布局
        form = QFormLayout()
        form.addRow("Operation:", self.mode)
        form.addRow("ΔX (µm):", self.dx_input)
        form.addRow("ΔY (µm):", self.dy_input)
        form.addRow("Angle (°):", self.angle_input)
        form.addRow("Scale ×:", self.scale_input)
        form.addRow("Center X (µm):", self.cx_input)
        form.addRow("Center Y (µm):", self.cy_input)

        # 按钮布局
        btns = QHBoxLayout()
        btns.addWidget(self.run_btn)
        btns.addWidget(self.cancel_btn)

        # 总体布局
        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addLayout(btns)
        self.setLayout(layout)

        # 连接信号
        self.mode.currentIndexChanged.connect(self.update_visibility)
        self.run_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        self.update_visibility()

    def update_visibility(self):
        mode = self.mode.currentText()
        self.dx_input.setVisible(mode == "Translate")
        self.dy_input.setVisible(mode == "Translate")
        self.angle_input.setVisible(mode == "Rotate")
        self.scale_input.setVisible(mode == "Scale")

    def get_values(self):
        return {
            "mode": self.mode.currentText(),
            "dx": float(self.dx_input.text() or 0.0),
            "dy": float(self.dy_input.text() or 0.0),
            "angle": float(self.angle_input.text() or 0.0),
            "scale": float(self.scale_input.text() or 1.0),
            "cx": float(self.cx_input.text() or 0.0),
            "cy": float(self.cy_input.text() or 0.0)
        }

def transform_selected():
    lv = pya.LayoutView.current()
    cv = lv.active_cellview()
    if not cv:
        QMessageBox.warning(None, "Error", "No active layout.")
        return

    layout = cv.layout()
    dbu = layout.dbu
    dialog = TransformDialog()

    if dialog.exec_() == QDialog.Accepted:
        values = dialog.get_values()
        dx = int(values["dx"] / dbu)
        dy = int(values["dy"] / dbu)
        cx = int(values["cx"] / dbu)
        cy = int(values["cy"] / dbu)
        mode = values["mode"]
        n = 0

        for obj in lv.object_selection:
            if obj.is_cell_inst(): continue
            shape = obj.shape

            if mode == "Translate":
                shape.transform(pya.Trans(dx, dy))

            elif mode == "Rotate":
                tf = pya.ICplxTrans(1.0, values["angle"], False, cx, cy)
                shape.transform(tf)

            elif mode == "Scale":
                tf = pya.ICplxTrans(values["scale"], 0, False, cx, cy)
                shape.transform(tf)

            n += 1

        QMessageBox.information(None, "Done", f"{n} shapes transformed.")

# 执行宏
def main():
    transform_selected()
