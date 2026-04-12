import os
from dataclasses import dataclass

import pya
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QBrush, QPen
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGraphicsScene,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


@dataclass
class ParameterSpec:
    key: str
    label: str
    symbol: str
    group: str
    default: object
    kind: str = "float"
    minimum: float = -1e6
    maximum: float = 1e6
    decimals: int = 3
    choices: list = None
    suffix: str = ""
    tooltip: str = ""


@dataclass
class ToolSpec:
    key: str
    title: str
    library_name: str
    pcell_name: str
    preview_renderer: callable
    params: list


class PreviewView(QGraphicsView):
    def __init__(self):
        scene = QGraphicsScene()
        super().__init__(scene)
        self.setRenderHint(self.renderHints())
        self.setMinimumSize(420, 320)
        self.setStyleSheet("background: #111;")

    def draw_tool_preview(self, tool_spec, values):
        scene = self.scene()
        scene.clear()
        tool_spec.preview_renderer(scene, values)
        scene.setSceneRect(scene.itemsBoundingRect().adjusted(-12, -12, 12, 12))
        self.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)


class SymbolDialog(QDialog):
    def __init__(self, tool_spec, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{tool_spec.title} Symbols")
        self.setMinimumSize(420, 360)

        text = QTextEdit()
        text.setReadOnly(True)
        lines = []
        for param in tool_spec.params:
            symbol = param.symbol or "-"
            lines.append(f"{symbol}: {param.label} ({param.key})")
        text.setPlainText("\n".join(lines))

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Parameter symbols for documentation / schematic annotations:"))
        layout.addWidget(text)
        self.setLayout(layout)


class ToolkitDialog(QDialog):
    def __init__(self, tool_specs, parent=None):
        super().__init__(parent)
        self.tool_specs = {spec.key: spec for spec in tool_specs}
        self.controls = {}
        self.current_tool_key = tool_specs[0].key

        self.setWindowTitle("NanoDevice Toolkit")
        self.setMinimumSize(980, 680)

        self.tool_select = QComboBox()
        for spec in tool_specs:
            self.tool_select.addItem(spec.title, spec.key)
        self.tool_select.currentIndexChanged.connect(self._rebuild_param_form)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.form_host = QWidget()
        self.form_layout = QVBoxLayout()
        self.form_host.setLayout(self.form_layout)
        self.scroll.setWidget(self.form_host)

        self.preview = PreviewView()
        self.preview_label = QLabel("Symbolic preview")

        self.preview_btn = QPushButton("Preview")
        self.preview_btn.clicked.connect(self._refresh_preview)
        self.insert_btn = QPushButton("Insert")
        self.insert_btn.clicked.connect(self._insert_tool)
        self.symbol_btn = QPushButton("Symbols")
        self.symbol_btn.clicked.connect(self._show_symbols)
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.reject)

        self._build_ui()
        self._rebuild_param_form()

    def _build_ui(self):
        main = QVBoxLayout()

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Function"))
        top_row.addWidget(self.tool_select, 1)
        main.addLayout(top_row)

        split = QHBoxLayout()
        split.addWidget(self.scroll, 1)

        right = QVBoxLayout()
        right.addWidget(self.preview_label)
        right.addWidget(self.preview, 1)
        split.addLayout(right, 1)
        main.addLayout(split, 1)

        btns = QHBoxLayout()
        btns.addWidget(self.symbol_btn)
        btns.addStretch(1)
        btns.addWidget(self.preview_btn)
        btns.addWidget(self.insert_btn)
        btns.addWidget(self.close_btn)
        main.addLayout(btns)
        self.setLayout(main)

    def _current_tool(self):
        key = self.tool_select.currentData()
        return self.tool_specs[key]

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)

    def _rebuild_param_form(self):
        self.controls = {}
        self._clear_layout(self.form_layout)
        tool = self._current_tool()

        groups = {}
        for param in tool.params:
            groups.setdefault(param.group, []).append(param)

        for group_name, params in groups.items():
            box = QGroupBox(group_name)
            form = QFormLayout()
            for param in params:
                control = self._make_control(param)
                self.controls[param.key] = control
                label = f"{param.label} [{param.symbol}]"
                form.addRow(label, control)
            box.setLayout(form)
            self.form_layout.addWidget(box)

        self.form_layout.addStretch(1)
        self._refresh_preview()

    def _make_control(self, param):
        if param.kind == "choice":
            combo = QComboBox()
            for title, value in param.choices:
                combo.addItem(title, value)
            default_index = 0
            for idx, (_, value) in enumerate(param.choices):
                if value == param.default:
                    default_index = idx
                    break
            combo.setCurrentIndex(default_index)
            combo.currentIndexChanged.connect(self._refresh_preview)
            if param.tooltip:
                combo.setToolTip(param.tooltip)
            return combo

        spin = QDoubleSpinBox()
        spin.setDecimals(param.decimals)
        spin.setRange(param.minimum, param.maximum)
        spin.setSingleStep(0.5)
        spin.setValue(float(param.default))
        if param.suffix:
            spin.setSuffix(param.suffix)
        if param.tooltip:
            spin.setToolTip(param.tooltip)
        spin.valueChanged.connect(self._refresh_preview)
        return spin

    def _values(self):
        values = {}
        for param in self._current_tool().params:
            control = self.controls[param.key]
            if param.kind == "choice":
                values[param.key] = control.currentData()
            else:
                values[param.key] = control.value()
        return values

    def _refresh_preview(self):
        tool = self._current_tool()
        self.preview.draw_tool_preview(tool, self._values())

    def _show_symbols(self):
        dlg = SymbolDialog(self._current_tool(), self)
        dlg.exec_()

    def _insert_tool(self):
        lv = pya.LayoutView.current()
        if lv is None:
            QMessageBox.warning(self, "No View", "Open a layout first.")
            return

        cv = lv.active_cellview()
        if cv is None or cv.layout() is None or cv.cell is None:
            QMessageBox.warning(self, "No Active Cell", "Open or create a layout cell first.")
            return

        tool = self._current_tool()
        layout = cv.layout()
        top_cell = cv.cell
        params = dict(self._values())
        params["channel_layer"] = pya.LayerInfo(14, 0)
        params["sd_layer"] = pya.LayerInfo(16, 0)
        params["gate_layer"] = pya.LayerInfo(18, 0)

        try:
            pcell_variant = layout.create_cell(tool.pcell_name, tool.library_name, params)
            if pcell_variant is None:
                raise RuntimeError("PCell variant creation returned None.")
            top_cell.insert(pya.CellInstArray(pcell_variant.cell_index(), pya.Trans()))
            lv.add_missing_layers()
            lv.zoom_fit()
        except Exception as exc:
            QMessageBox.critical(self, "Insert Failed", str(exc))


def _auto_slot_count(values):
    span = values["channel_width"] if values["finger_orientation"] == 0 else values["channel_height"]
    usable = max(span, values["finger_width"])
    pitch = values["finger_width"] + values["finger_spacing"]
    count = int((usable + values["finger_spacing"]) // pitch)
    return max(count, 2)


def _draw_box(scene, box, pen, brush=None):
    x1, y1, x2, y2 = box
    scene.addRect(x1, y1, x2 - x1, y2 - y1, pen, brush or QBrush(Qt.NoBrush))


def _center_box(cx, cy, width, height):
    return (cx - width / 2.0, cy - height / 2.0, cx + width / 2.0, cy + height / 2.0)


def render_interdigitated_fet(scene, values):
    pen_channel = QPen(QColor("#f4d35e"))
    pen_sd = QPen(QColor("#d7263d"))
    pen_gate = QPen(QColor("#1b998b"))
    pen_outline = QPen(QColor("#aaaaaa"))
    brush_channel = QBrush(QColor(244, 211, 94, 70))
    brush_sd = QBrush(QColor(215, 38, 61, 90))
    brush_gate = QBrush(QColor(27, 153, 139, 90))

    cx = values["device_cx"]
    cy = values["device_cy"]
    channel = _center_box(cx, cy, values["channel_width"], values["channel_height"])
    _draw_box(scene, channel, pen_channel, brush_channel)

    slots = _auto_slot_count(values)
    fw = values["finger_width"]
    fs = values["finger_spacing"]
    ext = values["finger_extension"]
    far_ext = values["finger_far_extension"]
    busw = values["bus_width"]

    if values["finger_orientation"] == 0:
        left, bottom, right, top = channel
        width = slots * fw + (slots - 1) * fs
        x0 = cx - width / 2.0
        pitch = fw + fs
        top_finger_top = top + ext
        top_finger_bottom = bottom - far_ext
        bottom_finger_bottom = bottom - ext
        bottom_finger_top = top + far_ext
        active_left = left
        active_right = right
        _draw_box(scene, _center_box((active_left + active_right) / 2.0, top_finger_top + busw / 2.0, active_right - active_left, busw), pen_sd, brush_sd)
        _draw_box(scene, _center_box((active_left + active_right) / 2.0, bottom_finger_bottom - busw / 2.0, active_right - active_left, busw), pen_sd, brush_sd)

        for i in range(slots):
            x_left = x0 + i * pitch
            if i % 2 == 0:
                _draw_box(scene, (x_left, top_finger_bottom, x_left + fw, top_finger_top), pen_sd, brush_sd)
            else:
                _draw_box(scene, (x_left, bottom_finger_bottom, x_left + fw, bottom_finger_top), pen_sd, brush_sd)

        if values["gate_mode"] == 0:
            gate = (
                channel[0] - values["gate_margin_x"],
                channel[1] - values["gate_margin_y"],
                channel[2] + values["gate_margin_x"],
                channel[3] + values["gate_margin_y"],
            )
            _draw_box(scene, gate, pen_gate, brush_gate)
        else:
            gap_boxes = []
            cursor = x0
            for i in range(slots):
                x_left = x0 + i * pitch
                if x_left > cursor:
                    gap_boxes.append((cursor, bottom, x_left, top))
                cursor = x_left + fw
            if cursor < x0 + width:
                gap_boxes.append((cursor, bottom, x0 + width, top))
            for gap in gap_boxes:
                _draw_box(scene, gap, pen_gate, brush_gate)
            bridge_h = max(min(fs, values["channel_height"] / 3.0), 0.2)
            for idx in range(len(gap_boxes) - 1):
                lg = gap_boxes[idx]
                rg = gap_boxes[idx + 1]
                if idx % 2 == 0:
                    bridge = (lg[2], top - bridge_h, rg[0], top)
                else:
                    bridge = (lg[2], bottom, rg[0], bottom + bridge_h)
                _draw_box(scene, bridge, pen_gate, brush_gate)
    else:
        left, bottom, right, top = channel
        height = slots * fw + (slots - 1) * fs
        y0 = cy - height / 2.0
        pitch = fw + fs
        right_finger_right = right + ext
        right_finger_left = left - far_ext
        left_finger_left = left - ext
        left_finger_right = right + far_ext
        active_bottom = bottom
        active_top = top
        _draw_box(scene, _center_box(left_finger_left - busw / 2.0, (active_bottom + active_top) / 2.0, busw, active_top - active_bottom), pen_sd, brush_sd)
        _draw_box(scene, _center_box(right_finger_right + busw / 2.0, (active_bottom + active_top) / 2.0, busw, active_top - active_bottom), pen_sd, brush_sd)

        for i in range(slots):
            y_bottom = y0 + i * pitch
            if i % 2 == 0:
                _draw_box(scene, (left_finger_left, y_bottom, left_finger_right, y_bottom + fw), pen_sd, brush_sd)
            else:
                _draw_box(scene, (right_finger_left, y_bottom, right_finger_right, y_bottom + fw), pen_sd, brush_sd)

        if values["gate_mode"] == 0:
            gate = (
                channel[0] - values["gate_margin_x"],
                channel[1] - values["gate_margin_y"],
                channel[2] + values["gate_margin_x"],
                channel[3] + values["gate_margin_y"],
            )
            _draw_box(scene, gate, pen_gate, brush_gate)
        else:
            gap_boxes = []
            cursor = y0
            for i in range(slots):
                y_bottom = y0 + i * pitch
                if y_bottom > cursor:
                    gap_boxes.append((left, cursor, right, y_bottom))
                cursor = y_bottom + fw
            if cursor < y0 + height:
                gap_boxes.append((left, cursor, right, y0 + height))
            for gap in gap_boxes:
                _draw_box(scene, gap, pen_gate, brush_gate)
            bridge_w = max(min(fs, values["channel_width"] / 3.0), 0.2)
            for idx in range(len(gap_boxes) - 1):
                lg = gap_boxes[idx]
                ug = gap_boxes[idx + 1]
                if idx % 2 == 0:
                    bridge = (right - bridge_w, lg[3], right, ug[1])
                else:
                    bridge = (left, lg[3], left + bridge_w, ug[1])
                _draw_box(scene, bridge, pen_gate, brush_gate)

    scene.addText("Channel").setPos(channel[0], channel[1] - 10)
    scene.addText("S/D").setPos(channel[0], channel[3] + 8)
    scene.addText("Gate").setPos(channel[2] + 6, channel[1])


INTERDIGITATED_FET_TOOL = ToolSpec(
    key="interdigitated_fet",
    title="Interdigitated FET",
    library_name="InterdigitatedFETLib",
    pcell_name="InterdigitatedFETPCell",
    preview_renderer=render_interdigitated_fet,
    params=[
        ParameterSpec("device_cx", "Center X", "Cx", "Placement", 0.0, suffix=" um"),
        ParameterSpec("device_cy", "Center Y", "Cy", "Placement", 0.0, suffix=" um"),
        ParameterSpec(
            "finger_orientation",
            "Orientation",
            "Dir",
            "Channel",
            0,
            kind="choice",
            choices=[("vertical", 0), ("horizontal", 1)],
            tooltip="Direction of the inner interdigitated electrodes.",
        ),
        ParameterSpec("channel_width", "Channel Width", "Wch", "Channel", 30.0, minimum=0.1, suffix=" um"),
        ParameterSpec("channel_height", "Channel Height", "Hch", "Channel", 18.0, minimum=0.1, suffix=" um"),
        ParameterSpec("finger_width", "Finger Width", "Wf", "Finger", 2.0, minimum=0.01, suffix=" um"),
        ParameterSpec("finger_spacing", "Finger Spacing", "Sf", "Finger", 2.0, minimum=0.0, suffix=" um"),
        ParameterSpec("finger_extension", "Bus-side Extension", "Lf,b", "Finger", 8.0, minimum=0.0, suffix=" um"),
        ParameterSpec("finger_far_extension", "Far-side Extension", "Lf,f", "Finger", 0.0, minimum=0.0, suffix=" um"),
        ParameterSpec("bus_width", "Bus Width", "Wbus", "Finger", 6.0, minimum=0.01, suffix=" um"),
        ParameterSpec("sd_lead_length", "Lead Length", "Llead", "Source / Drain", 10.0, minimum=0.0, suffix=" um"),
        ParameterSpec("sd_pad_width", "Pad Width", "Wpad", "Source / Drain", 18.0, minimum=0.1, suffix=" um"),
        ParameterSpec("sd_pad_height", "Pad Height", "Hpad", "Source / Drain", 14.0, minimum=0.1, suffix=" um"),
        ParameterSpec("sd_pad_gap", "Pad-to-Pad Gap", "Gpad", "Source / Drain", 12.0, minimum=0.0, suffix=" um"),
        ParameterSpec(
            "gate_mode",
            "Gate Mode",
            "Gmode",
            "Gate",
            0,
            kind="choice",
            choices=[("global", 0), ("channel_only", 1)],
            tooltip="global = same size as channel before resize, channel_only = serpentine inter-finger region.",
        ),
        ParameterSpec("gate_margin_x", "Resize X", "dGx", "Gate", 0.0, suffix=" um"),
        ParameterSpec("gate_margin_y", "Resize Y", "dGy", "Gate", 0.0, suffix=" um"),
        ParameterSpec("gate_lead_width", "Lead Width", "Wglead", "Gate", 8.0, minimum=0.01, suffix=" um"),
        ParameterSpec("gate_pad_width", "Pad Width", "Wgpad", "Gate", 18.0, minimum=0.1, suffix=" um"),
        ParameterSpec("gate_pad_height", "Pad Height", "Hgpad", "Gate", 14.0, minimum=0.1, suffix=" um"),
        ParameterSpec("gate_pad_gap", "Pad Gap", "Ggpad", "Gate", 10.0, minimum=0.0, suffix=" um"),
    ],
)


def launch_toolkit_dialog():
    dlg = ToolkitDialog([INTERDIGITATED_FET_TOOL])
    dlg.exec_()
