import json
import math
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import pya
from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QBrush, QFont, QFontDatabase, QFontMetricsF, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGraphicsScene,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

def _discover_root_dir():
    current = os.path.abspath(os.path.dirname(__file__))
    candidates = [
        current,
        os.path.abspath(os.path.join(current, "..")),
        os.path.abspath(os.path.join(current, "..", "..")),
        os.path.abspath(os.path.join(current, "..", "..", "..")),
    ]
    for candidate in candidates:
        if (
            os.path.exists(os.path.join(candidate, "config.py"))
            and os.path.isdir(os.path.join(candidate, "utils"))
            and os.path.isdir(os.path.join(candidate, "components"))
        ):
            return candidate
    return os.path.abspath(os.path.join(current, "..", "..", ".."))


ROOT_DIR = _discover_root_dir()
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

TEXT_POLYGON_SCRIPT = os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    "generate_gdsfactory_text_polygons.py",
)

from config import DEFAULT_DBU, LAYER_DEFINITIONS
from utils.deplof_font import _glyph as DEPLOF_GLYPH, _indent as DEPLOF_INDENT, _width as DEPLOF_WIDTH
def _discover_layer_map_path():
    candidates = [
        os.path.join(ROOT_DIR, "lymtoolkit", "pdk", "layers", "layer_map.lyp"),
        os.path.join(ROOT_DIR, "pdk", "layers", "layer_map.lyp"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return candidates[0]


LAYER_MAP_PATH = _discover_layer_map_path()
PREVIEW_TEXT_KEY = "labels"
PREVIEW_LAYER_KEY_ALIASES = {
    "text": "labels",
    "sd": "source_drain",
    "active": "channel",
    "contacts": "source_drain",
    "pads": "source_drain",
    "electrodes": "source_drain",
    "gate": "top_gate",
}
PREVIEW_LAYER_IDS = {
    "bottom_gate": [LAYER_DEFINITIONS["bottom_gate"]["id"]],
    "bottom_dielectric": [LAYER_DEFINITIONS["bottom_dielectric"]["id"]],
    "channel": [LAYER_DEFINITIONS["channel"]["id"]],
    "source_drain": [LAYER_DEFINITIONS["source_drain"]["id"], LAYER_DEFINITIONS["pads"]["id"], LAYER_DEFINITIONS["routing"]["id"]],
    "top_dielectric": [LAYER_DEFINITIONS["top_dielectric"]["id"]],
    "top_gate": [LAYER_DEFINITIONS["top_gate"]["id"]],
    "alignment_marks": [LAYER_DEFINITIONS["alignment_marks"]["id"], LAYER_DEFINITIONS["alignment_layer1"]["id"], LAYER_DEFINITIONS["alignment_layer2"]["id"]],
    "labels": [LAYER_DEFINITIONS["labels"]["id"]],
}
DIRECT_PREVIEW_TOOL_KEYS = {"gdsfactory_text", "nanodevice_fet", "mosfet_component", "hall_component", "tlm_component", "sense_latch_array", "write_read_array"}
_FONT_FAMILY_CACHE = {}


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
    preview_layers: list
    insert_params_builder: callable = None
    insert_handler: callable = None


class PreviewView(QGraphicsView):
    def __init__(self):
        scene = QGraphicsScene()
        super().__init__(scene)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.TextAntialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setMinimumSize(420, 320)
        self.setStyleSheet("background: #111;")
        self._layer_visibility = {"channel": True, "sd": True, "gate": True}
        self._preview_bounds = QRectF(-100.0, -100.0, 200.0, 200.0)
        self._base_grid_px = 28.0
        self._has_fitted_once = False
        self._last_tool_key = None

    def set_layer_visibility(self, layer_key, visible):
        self._layer_visibility[layer_key] = visible

    def wheelEvent(self, event):
        if event.angleDelta().y() == 0:
            super().wheelEvent(event)
            return
        factor = 1.18 if event.angleDelta().y() > 0 else 1.0 / 1.18
        self.scale(factor, factor)

    def drawBackground(self, painter, rect):
        painter.fillRect(rect, QColor("#111111"))

        grid_step = self._grid_step_scene()
        if grid_step <= 0:
            return

        minor_pen = QPen(QColor(255, 255, 255, 18), 0)
        major_pen = QPen(QColor(255, 255, 255, 38), 0)

        left = int(rect.left() // grid_step) - 1
        right = int(rect.right() // grid_step) + 1
        top = int(rect.top() // grid_step) - 1
        bottom = int(rect.bottom() // grid_step) + 1

        for ix in range(left, right + 1):
            x = ix * grid_step
            painter.setPen(major_pen if ix % 5 == 0 else minor_pen)
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))

        for iy in range(top, bottom + 1):
            y = iy * grid_step
            painter.setPen(major_pen if iy % 5 == 0 else minor_pen)
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)
        self._draw_scale_bar(painter)

    def draw_tool_preview(self, tool_spec, values, preserve_view=True):
        scene = self.scene()
        saved_transform = self.transform()
        saved_center = self.mapToScene(self.viewport().rect().center())
        tool_changed = tool_spec.key != self._last_tool_key
        scene.clear()
        try:
            if tool_spec.key in DIRECT_PREVIEW_TOOL_KEYS:
                tool_spec.preview_renderer(scene, values, self._layer_visibility)
            else:
                _draw_generated_preview(scene, tool_spec, values, self._layer_visibility)
        except Exception as exc:
            self._draw_preview_error(scene, str(exc))
        item_bounds = scene.itemsBoundingRect()
        if item_bounds.isNull():
            item_bounds = QRectF(-50.0, -50.0, 100.0, 100.0)
        self._preview_bounds = item_bounds.adjusted(-20.0, -20.0, 20.0, 20.0)
        scene.setSceneRect(self._preview_bounds)
        if preserve_view and self._has_fitted_once and not tool_changed:
            self.setTransform(saved_transform)
            self.centerOn(saved_center)
            self._last_tool_key = tool_spec.key
            return
        self.resetTransform()
        self.fitInView(self._preview_bounds, Qt.KeepAspectRatio)
        self._has_fitted_once = True
        self._last_tool_key = tool_spec.key

    def _draw_preview_error(self, scene, message):
        text_item = scene.addText("Preview unavailable")
        text_item.setDefaultTextColor(QColor("#ff8c69"))
        text_item.setPos(-70.0, -10.0)
        detail = scene.addText(message[:240])
        detail.setDefaultTextColor(QColor("#d9d9d9"))
        detail.setPos(-110.0, 18.0)

    def _grid_step_scene(self):
        scale = abs(self.transform().m11()) or 1.0
        target_scene = self._base_grid_px / scale
        decade = 1.0
        while target_scene > decade * 10.0:
            decade *= 10.0
        while target_scene < decade:
            decade /= 10.0
        for factor in (1.0, 2.0, 5.0, 10.0):
            step = decade * factor
            if step >= target_scene:
                return step
        return decade * 10.0

    def _draw_scale_bar(self, painter):
        viewport_rect = self.viewport().rect()
        margin = 18
        max_px = 120.0
        scale = abs(self.transform().m11()) or 1.0
        max_scene = max_px / scale

        bar_um = _nice_length(max_scene * 0.65)
        bar_px = bar_um * scale
        if bar_px < 24.0:
            return

        x2 = viewport_rect.left() + margin + bar_px
        x1 = viewport_rect.left() + margin
        y = viewport_rect.bottom() - margin

        painter.resetTransform()
        painter.setPen(QPen(QColor("#f2f2f2"), 1.0))
        painter.drawLine(int(x1), int(y), int(x2), int(y))
        painter.drawLine(int(x1), int(y - 5), int(x1), int(y + 5))
        painter.drawLine(int(x2), int(y - 5), int(x2), int(y + 5))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(QRectF(x1, y - 18, bar_px + 6.0, 14.0), Qt.AlignLeft | Qt.AlignVCenter, f"{_format_length(bar_um)}")


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
        self.scroll.setFixedWidth(285)
        self.form_host = QWidget()
        self.form_host.setFixedWidth(265)
        self.form_layout = QVBoxLayout()
        self.form_host.setLayout(self.form_layout)
        self.scroll.setWidget(self.form_host)

        self.preview = PreviewView()
        self.preview_label = QLabel("Generated preview")
        self.layer_checks = {}
        self.layer_layout = QHBoxLayout()
        self.layer_layout.setContentsMargins(0, 0, 0, 0)
        self.layer_layout.setSpacing(10)

        self.preview_btn = QPushButton("Preview")
        self.preview_btn.clicked.connect(self._refit_preview)
        self.insert_btn = QPushButton("Insert")
        self.insert_btn.clicked.connect(self._insert_tool)
        self.import_btn = QPushButton("Import Config")
        self.import_btn.clicked.connect(self._import_config)
        self.export_btn = QPushButton("Export Config")
        self.export_btn.clicked.connect(self._export_config)
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
        split.addWidget(self.scroll, 0)

        right = QVBoxLayout()
        right.addWidget(self.preview_label)
        layer_row = QHBoxLayout()
        layer_row.addWidget(QLabel("Layers"))
        layer_row.addLayout(self.layer_layout, 1)
        layer_row.addStretch(1)
        right.addLayout(layer_row)
        right.addWidget(self.preview, 1)
        split.addLayout(right, 1)
        main.addLayout(split, 1)

        btns = QHBoxLayout()
        btns.addWidget(self.symbol_btn)
        btns.addWidget(self.import_btn)
        btns.addWidget(self.export_btn)
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
        self.control_labels = {}
        self._clear_layout(self.form_layout)
        tool = self._current_tool()
        self.preview._has_fitted_once = False

        groups = {}
        for param in tool.params:
            groups.setdefault(param.group, []).append(param)

        for group_name, params in groups.items():
            box = QGroupBox(group_name)
            form = QFormLayout()
            for param in params:
                control = self._make_control(param)
                self.controls[param.key] = control
                label = QLabel(f"{param.label} [{param.symbol}]")
                if param.tooltip:
                    label.setToolTip(param.tooltip)
                self.control_labels[param.key] = label
                form.addRow(label, control)
            box.setLayout(form)
            self.form_layout.addWidget(box)

        self.form_layout.addStretch(1)
        self._update_layer_controls(tool)
        self._apply_dynamic_param_state()
        self._refresh_preview()

    def _make_control(self, param):
        if param.kind == "font_path":
            holder = QWidget()
            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(6)
            text = QLineEdit()
            text.setText(str(param.default))
            text.textChanged.connect(self._refresh_preview)
            if param.tooltip:
                text.setToolTip(param.tooltip)
            button = QPushButton("Open")
            button.setFixedWidth(58)
            button.clicked.connect(lambda _=False, field=text: self._browse_font_path(field))
            layout.addWidget(text, 1)
            layout.addWidget(button, 0)
            holder.setLayout(layout)
            holder._line_edit = text
            return holder

        if param.kind == "string":
            text = QLineEdit()
            text.setText(str(param.default))
            text.textChanged.connect(self._on_param_control_changed)
            if param.tooltip:
                text.setToolTip(param.tooltip)
            return text

        if param.kind == "layer_choice":
            combo = QComboBox()
            for title, value in self._available_layers(param.default):
                combo.addItem(title, value)
            default_index = 0
            for idx in range(combo.count()):
                if combo.itemData(idx) == param.default:
                    default_index = idx
                    break
            combo.setCurrentIndex(default_index)
            combo.currentIndexChanged.connect(self._on_param_control_changed)
            if param.tooltip:
                combo.setToolTip(param.tooltip)
            return combo

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
            combo.currentIndexChanged.connect(self._on_param_control_changed)
            if param.tooltip:
                combo.setToolTip(param.tooltip)
            return combo

        if param.kind == "int":
            spin = QSpinBox()
            spin.setRange(int(param.minimum), int(param.maximum))
            spin.setSingleStep(1)
            spin.setValue(int(param.default))
            spin.setKeyboardTracking(False)
            if param.tooltip:
                spin.setToolTip(param.tooltip)
            spin.editingFinished.connect(self._on_param_control_changed)
            spin.valueChanged.connect(self._on_param_control_changed)
            return spin

        spin = QDoubleSpinBox()
        spin.setDecimals(param.decimals)
        spin.setRange(param.minimum, param.maximum)
        spin.setSingleStep(0.5)
        spin.setValue(float(param.default))
        spin.setKeyboardTracking(False)
        if param.suffix:
            spin.setSuffix(param.suffix)
        if param.tooltip:
            spin.setToolTip(param.tooltip)
        spin.editingFinished.connect(self._on_param_control_changed)
        spin.valueChanged.connect(self._on_param_control_changed)
        return spin

    def _on_param_control_changed(self, *_args):
        self._apply_dynamic_param_state()
        self._refresh_preview()

    def _values(self):
        values = {}
        for param in self._current_tool().params:
            control = self.controls[param.key]
            if param.kind == "font_path":
                values[param.key] = control._line_edit.text()
            elif param.kind == "string":
                values[param.key] = control.text()
            elif param.kind == "layer_choice":
                values[param.key] = control.currentData()
            elif param.kind == "choice":
                values[param.key] = control.currentData()
            else:
                values[param.key] = control.value()
        return self._normalize_tool_values(self._current_tool(), values)

    def _raw_values(self):
        values = {}
        for param in self._current_tool().params:
            control = self.controls[param.key]
            if param.kind == "font_path":
                values[param.key] = control._line_edit.text()
            elif param.kind == "string":
                values[param.key] = control.text()
            elif param.kind == "layer_choice":
                values[param.key] = control.currentData()
            elif param.kind == "choice":
                values[param.key] = control.currentData()
            else:
                values[param.key] = control.value()
        return values

    def _normalize_tool_values(self, tool, values):
        normalized = dict(values)
        if tool.key in ("sense_latch_array", "write_read_array"):
            mode = str(normalized.get("array_shape_mode", "square") or "square").lower()
            if mode == "square":
                size = int(normalized.get("array_size", 1))
                normalized["rows"] = size
                normalized["cols"] = size
            else:
                normalized["array_size"] = int(max(normalized.get("rows", 1), normalized.get("cols", 1)))
        return normalized

    def _apply_dynamic_param_state(self):
        tool = self._current_tool()
        if tool.key not in ("sense_latch_array", "write_read_array"):
            return

        raw_values = self._raw_values()
        mode = str(raw_values.get("array_shape_mode", "square") or "square").lower()
        draw_top_dielectric = bool(raw_values.get("draw_top_dielectric", False))
        sense_fet_structure = str(raw_values.get("sense_fet_structure", "plain") or "plain").lower()

        array_size_control = self.controls.get("array_size")
        rows_control = self.controls.get("rows")
        cols_control = self.controls.get("cols")
        dielectric_margin_control = self.controls.get("contact_overlap_margin")

        if array_size_control is not None:
            array_size_control.setEnabled(mode == "square")
        if rows_control is not None:
            rows_control.setEnabled(mode != "square")
        if cols_control is not None:
            cols_control.setEnabled(mode != "square")
        if dielectric_margin_control is not None:
            dielectric_margin_control.setEnabled(draw_top_dielectric)

        if tool.key == "sense_latch_array":
            interdigit_keys = (
                "sense_interdigit_finger_width",
                "sense_interdigit_finger_spacing",
                "sense_interdigit_tip_gap",
            )
            show_interdigit = sense_fet_structure == "interdigitated"
            for key in interdigit_keys:
                control = self.controls.get(key)
                label = self.control_labels.get(key)
                if control is not None:
                    control.setVisible(show_interdigit)
                if label is not None:
                    label.setVisible(show_interdigit)

    def _set_control_value(self, param, value):
        control = self.controls.get(param.key)
        if control is None or value is None:
            return

        if param.kind == "font_path":
            control._line_edit.setText(str(value))
            return

        if param.kind == "string":
            control.setText(str(value))
            return

        if param.kind in ("choice", "layer_choice"):
            for idx in range(control.count()):
                if control.itemData(idx) == value:
                    control.setCurrentIndex(idx)
                    return
            return

        if param.kind == "int":
            try:
                control.setValue(int(value))
            except Exception:
                return
            return

        try:
            control.setValue(float(value))
        except Exception:
            return

    def _browse_font_path(self, field):
        current = field.text().strip()
        start_dir = _default_font_directory()
        if current and os.path.exists(current):
            start_dir = os.path.dirname(current)
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select TrueType Font",
            start_dir,
            "Font Files (*.ttf *.otf *.ttc);;All Files (*)",
        )
        if file_path:
            field.setText(file_path)

    def _config_payload(self):
        tool = self._current_tool()
        return {
            "format": "nanodevice-toolkit-config",
            "version": 1,
            "tool_key": tool.key,
            "tool_title": tool.title,
            "values": self._serialize_values(self._values()),
        }

    def _serialize_values(self, values):
        serialized = {}
        for key, value in values.items():
            if isinstance(value, tuple):
                serialized[key] = list(value)
            else:
                serialized[key] = value
        return serialized

    def _deserialize_values(self, tool, values):
        deserialized = {}
        params_by_key = {param.key: param for param in tool.params}
        for key, value in values.items():
            param = params_by_key.get(key)
            if param is None:
                continue
            if param.kind == "layer_choice" and isinstance(value, (list, tuple)) and len(value) == 2:
                deserialized[key] = (int(value[0]), int(value[1]))
            else:
                deserialized[key] = value
        return deserialized

    def _export_config(self):
        tool = self._current_tool()
        default_name = f"{tool.key}_config.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Config",
            default_name,
            "JSON Files (*.json);;All Files (*)",
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as handle:
                json.dump(self._config_payload(), handle, indent=2, ensure_ascii=False)
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))
            return

        QMessageBox.information(self, "Export Complete", f"Config saved to:\n{file_path}")

    def _import_config(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Config",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception as exc:
            QMessageBox.critical(self, "Import Failed", str(exc))
            return

        tool_key = payload.get("tool_key")
        if tool_key not in self.tool_specs:
            QMessageBox.critical(self, "Import Failed", f"Unsupported tool_key: {tool_key}")
            return

        tool_index = self.tool_select.findData(tool_key)
        if tool_index < 0:
            QMessageBox.critical(self, "Import Failed", f"Tool not found in GUI: {tool_key}")
            return

        self.tool_select.setCurrentIndex(tool_index)
        tool = self._current_tool()
        values = self._deserialize_values(tool, payload.get("values", {}))
        for param in tool.params:
            if param.key in values:
                self._set_control_value(param, values[param.key])
        self._refresh_preview()

    def _refresh_preview(self):
        tool = self._current_tool()
        for key, visible in self._layer_visibility().items():
            self.preview.set_layer_visibility(key, visible)
        self.preview.draw_tool_preview(tool, self._values(), preserve_view=True)

    def _refit_preview(self):
        tool = self._current_tool()
        for key, visible in self._layer_visibility().items():
            self.preview.set_layer_visibility(key, visible)
        self.preview.draw_tool_preview(tool, self._values(), preserve_view=False)

    def _update_layer_controls(self, tool):
        while self.layer_layout.count():
            item = self.layer_layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)
        self.layer_checks = {}
        for key, label in tool.preview_layers:
            checkbox = QCheckBox(label)
            checkbox.setChecked(True)
            checkbox.toggled.connect(self._refresh_preview)
            self.layer_layout.addWidget(checkbox)
            self.layer_checks[key] = checkbox
        self.layer_layout.addStretch(1)

    def _layer_visibility(self):
        return {key: checkbox.isChecked() for key, checkbox in self.layer_checks.items()}

    def _available_layers(self, default_value):
        layers = []
        seen = set()
        lv = pya.LayoutView.current()
        if lv is not None:
            cv = lv.active_cellview()
            if cv is not None and cv.layout() is not None:
                layout = cv.layout()
                infos = []
                if hasattr(layout, "layer_infos"):
                    try:
                        infos = list(layout.layer_infos())
                    except Exception:
                        infos = []
                if not infos and hasattr(layout, "layer_indices"):
                    try:
                        infos = [layout.get_info(idx) for idx in layout.layer_indices()]
                    except Exception:
                        infos = []
                if not infos and hasattr(layout, "layers"):
                    try:
                        infos = [layout.get_info(idx) for idx in range(layout.layers())]
                    except Exception:
                        infos = []
                for info in infos:
                    if info is None:
                        continue
                    value = (int(info.layer), int(info.datatype))
                    if value in seen:
                        continue
                    seen.add(value)
                    label = f"{info.layer}/{info.datatype}"
                    if getattr(info, "name", ""):
                        label += f" {info.name}"
                    layers.append((label, value))

        if default_value not in seen:
            layer, datatype = default_value
            layers.insert(0, (f"{layer}/{datatype}", default_value))
        return layers

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

        try:
            if tool.insert_handler is not None:
                tool.insert_handler(layout, top_cell, params)
            else:
                if tool.insert_params_builder is not None:
                    params.update(tool.insert_params_builder(params))
                pcell_variant = layout.create_cell(tool.pcell_name, tool.library_name, params)
                if pcell_variant is None:
                    raise RuntimeError("PCell variant creation returned None.")
                top_cell.insert(pya.CellInstArray(pcell_variant.cell_index(), pya.Trans()))
            lv.add_missing_layers()
            lv.zoom_fit()
        except Exception as exc:
            QMessageBox.critical(self, "Insert Failed", str(exc))


def _load_layer_styles():
    styles = {}
    if not os.path.exists(LAYER_MAP_PATH):
        return styles
    try:
        root = ET.parse(LAYER_MAP_PATH).getroot()
    except Exception:
        return styles

    for props in root.findall(".//properties"):
        source = (props.findtext("source") or "").strip()
        if "/" not in source:
            continue
        try:
            layer_id = int(source.split("/", 1)[0])
        except ValueError:
            continue
        styles[layer_id] = {
            "name": (props.findtext("name") or f"{layer_id}/0").strip(),
            "frame": QColor((props.findtext("frame-color") or "#dddddd").strip()),
            "fill": QColor((props.findtext("fill-color") or "#dddddd").strip()),
        }
    return styles


LAYER_STYLES = _load_layer_styles()


def _preview_style_for_key(layer_key):
    layer_key = PREVIEW_LAYER_KEY_ALIASES.get(layer_key, layer_key)
    layer_ids = PREVIEW_LAYER_IDS.get(layer_key, [])
    for layer_id in layer_ids:
        style = LAYER_STYLES.get(layer_id)
        if style:
            fill = QColor(style["fill"])
            fill.setAlpha(92)
            return QPen(style["frame"], 0), QBrush(fill)

    layer_def = LAYER_DEFINITIONS.get(layer_key)
    color = QColor("#d9d9d9")
    if layer_def is not None:
        color = QColor(f"#{layer_def['color']:06X}")
    fill = QColor(color)
    fill.setAlpha(92)
    return QPen(color, 0), QBrush(fill)


def _preview_style_for_layer_id(layer_id, fallback_key=None):
    style = LAYER_STYLES.get(int(layer_id))
    if style:
        fill = QColor(style["fill"])
        fill.setAlpha(92)
        return QPen(style["frame"], 0), QBrush(fill)
    if fallback_key is not None:
        return _preview_style_for_key(fallback_key)
    color = QColor("#d9d9d9")
    fill = QColor(color)
    fill.setAlpha(92)
    return QPen(color, 0), QBrush(fill)


def _iter_cells_recursive(layout, cell, seen=None):
    seen = seen or set()
    if cell is None or cell.cell_index() in seen:
        return
    seen.add(cell.cell_index())
    yield cell
    for inst in cell.each_inst():
        try:
            child_index = inst.cell_index if isinstance(inst.cell_index, int) else inst.cell_index()
            child = layout.cell(child_index)
        except Exception:
            child = None
        if child is not None:
            yield from _iter_cells_recursive(layout, child, seen)


def _shape_to_paths(shape, dbu):
    if shape.is_box():
        box = shape.box
        return [_boxes_to_path([_xy_box(box.left * dbu, -box.top * dbu, box.right * dbu, -box.bottom * dbu)])]
    if shape.is_path():
        return _polygon_to_paths(shape.path.polygon(), dbu)
    if shape.is_polygon():
        return _polygon_to_paths(shape.polygon, dbu)
    if shape.is_text():
        return _text_shape_to_paths(shape, dbu)
    box = shape.bbox()
    if box is None:
        return []
    return [_boxes_to_path([_xy_box(box.left * dbu, -box.top * dbu, box.right * dbu, -box.bottom * dbu)])]


def _polygon_to_paths(polygon, dbu):
    path = QPainterPath()
    hull = [point for point in polygon.each_point_hull()]
    if not hull:
        return []
    _append_points_to_path(path, hull, dbu)
    for hole_index in range(polygon.holes()):
        hole_points = [point for point in polygon.each_point_hole(hole_index)]
        if hole_points:
            _append_points_to_path(path, hole_points, dbu)
    return [path]


def _append_points_to_path(path, points, dbu):
    first = points[0]
    path.moveTo(first.x * dbu, -first.y * dbu)
    for point in points[1:]:
        path.lineTo(point.x * dbu, -point.y * dbu)
    path.closeSubpath()


def _text_shape_to_paths(shape, dbu):
    try:
        text = shape.text
        text_string = text.string
        trans = text.trans
        x = trans.disp.x * dbu
        y = -trans.disp.y * dbu
    except Exception:
        box = shape.bbox()
        if box is None:
            return []
        return [_boxes_to_path([_xy_box(box.left * dbu, -box.top * dbu, box.right * dbu, -box.bottom * dbu)])]

    text_path = QPainterPath()
    font = QFont("Segoe UI", 8)
    text_path.addText(0.0, 0.0, font, text_string)
    bounds = text_path.boundingRect()
    return [text_path.translated(x - bounds.left(), y - bounds.bottom())]


def _geometry_to_paths(geometry, dbu=DEFAULT_DBU):
    if geometry is None:
        return []
    if isinstance(geometry, pya.Box):
        return [_boxes_to_path([_xy_box(geometry.left * dbu, -geometry.top * dbu, geometry.right * dbu, -geometry.bottom * dbu)])]
    if isinstance(geometry, pya.Polygon):
        return _polygon_to_paths(geometry, dbu)
    if isinstance(geometry, pya.Path):
        return _polygon_to_paths(geometry.polygon(), dbu)
    if isinstance(geometry, pya.Region):
        paths = []
        for polygon in geometry.each():
            paths.extend(_polygon_to_paths(polygon, dbu))
        return paths
    if isinstance(geometry, pya.Text):
        text_path = QPainterPath()
        font = QFont("Segoe UI", 8)
        text_path.addText(0.0, 0.0, font, geometry.string)
        bounds = text_path.boundingRect()
        return [text_path.translated(geometry.x * dbu - bounds.left(), -geometry.y * dbu - bounds.bottom())]
    if hasattr(geometry, "bbox"):
        box = geometry.bbox()
        if box is not None:
            return [_boxes_to_path([_xy_box(box.left * dbu, -box.top * dbu, box.right * dbu, -box.bottom * dbu)])]
    return []


def _build_preview_layout(tool_spec, values):
    layout = pya.Layout()
    layout.dbu = DEFAULT_DBU
    top_cell = layout.create_cell("__NANODEVICE_PREVIEW_TOP__")
    params = dict(values)
    if tool_spec.insert_handler is not None:
        tool_spec.insert_handler(layout, top_cell, params)
    else:
        if tool_spec.insert_params_builder is not None:
            params.update(tool_spec.insert_params_builder(params))
        pcell_variant = layout.create_cell(tool_spec.pcell_name, tool_spec.library_name, params)
        if pcell_variant is None:
            raise RuntimeError("Preview PCell variant creation returned None.")
        top_cell.insert(pya.CellInstArray(pcell_variant.cell_index(), pya.Trans()))
    try:
        top_cell.flatten(-1, True)
    except Exception:
        pass
    return layout, top_cell


def _preview_layer_ids_for_tool_key(tool_spec, values, raw_key):
    layer_key = PREVIEW_LAYER_KEY_ALIASES.get(raw_key, raw_key)
    layer_ids = list(PREVIEW_LAYER_IDS.get(layer_key, []))

    if tool_spec.key == "mosfet_component":
        channel_type = str(values.get("channel_type", "p")).lower()
        if raw_key == "channel":
            layer_ids = [13 if channel_type.startswith("n") else 14]
        elif raw_key == "source_drain":
            layer_ids = [15 if channel_type.startswith("n") else 16]
        elif raw_key in ("labels", "alignment_marks"):
            layer_ids = [LAYER_DEFINITIONS["alignment_layer1"]["id"]]

    if raw_key in ("labels", "text") and "layer_spec" in values and isinstance(values["layer_spec"], tuple):
        layer_ids = [int(values["layer_spec"][0])]
    elif raw_key == "source_drain" and "sd_layer_spec" in values and isinstance(values["sd_layer_spec"], tuple):
        layer_ids = [int(values["sd_layer_spec"][0])]
    elif raw_key == "top_gate" and "gate_layer_spec" in values and isinstance(values["gate_layer_spec"], tuple):
        layer_ids = [int(values["gate_layer_spec"][0])]

    return layer_key, layer_ids


def _draw_generated_preview(scene, tool_spec, values, visible_layers=None):
    layout, top_cell = _build_preview_layout(tool_spec, values)
    visible_layers = visible_layers or {}
    dbu = layout.dbu

    for raw_key, _label in tool_spec.preview_layers:
        layer_key, layer_ids = _preview_layer_ids_for_tool_key(tool_spec, values, raw_key)
        if not visible_layers.get(raw_key, True):
            continue
        pen, brush = _preview_style_for_key(layer_key)
        for layer_id in layer_ids:
            layer_index = layout.layer(layer_id, 0)
            for cell in _iter_cells_recursive(layout, top_cell):
                shapes = cell.shapes(layer_index)
                for shape in shapes.each():
                    for path in _shape_to_paths(shape, dbu):
                        _draw_path(scene, path, pen, brush)


def _rectf_from_box(box):
    x1, y1, x2, y2 = box
    return QRectF(x1, y1, x2 - x1, y2 - y1)


def _draw_path(scene, path, pen, brush=None):
    scene.addPath(path, pen, brush or QBrush(Qt.NoBrush))


def _center_box(cx, cy, width, height):
    return (cx - width / 2.0, cy - height / 2.0, cx + width / 2.0, cy + height / 2.0)


def _xy_box(x1, y1, x2, y2):
    return (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))


def _grow_box(box, grow_x, grow_y):
    return (box[0] - grow_x, box[1] - grow_y, box[2] + grow_x, box[3] + grow_y)


def _rect_center(box):
    return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)


def _intersect_boxes(a, b):
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    if x2 <= x1 or y2 <= y1:
        return None
    return (x1, y1, x2, y2)


def _vertical_gap_boxes(channel_box, finger_boxes):
    left, bottom, right, top = channel_box
    gaps = []
    cursor = left
    for box in sorted(finger_boxes, key=lambda item: item[0]):
        if box[0] > cursor:
            gaps.append((cursor, bottom, box[0], top))
        cursor = max(cursor, box[2])
    if cursor < right:
        gaps.append((cursor, bottom, right, top))
    return [gap for gap in gaps if gap[2] - gap[0] > 1e-9]


def _horizontal_gap_boxes(channel_box, finger_boxes):
    left, bottom, right, top = channel_box
    gaps = []
    cursor = bottom
    for box in sorted(finger_boxes, key=lambda item: item[1]):
        if box[1] > cursor:
            gaps.append((left, cursor, right, box[1]))
        cursor = max(cursor, box[3])
    if cursor < top:
        gaps.append((left, cursor, right, top))
    return [gap for gap in gaps if gap[3] - gap[1] > 1e-9]


def _anchor_on_rect(rect_box, target):
    cx = (rect_box[0] + rect_box[2]) / 2.0
    cy = (rect_box[1] + rect_box[3]) / 2.0
    half_w = max((rect_box[2] - rect_box[0]) / 2.0, 1e-6)
    half_h = max((rect_box[3] - rect_box[1]) / 2.0, 1e-6)
    dx = target[0] - cx
    dy = target[1] - cy
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return (cx + half_w, cy)
    scale = 1.0 / max(abs(dx) / half_w, abs(dy) / half_h)
    return (cx + dx * scale, cy + dy * scale)


def _edge_aligned_lead_box(start_um, end_um, width_um):
    start_x, start_y = start_um
    end_x, end_y = end_um
    if abs(start_x - end_x) >= abs(start_y - end_y):
        y_mid = (start_y + end_y) / 2.0
        return _xy_box(start_x, y_mid - width_um / 2.0, end_x, y_mid + width_um / 2.0)
    x_mid = (start_x + end_x) / 2.0
    return _xy_box(x_mid - width_um / 2.0, start_y, x_mid + width_um / 2.0, end_y)


def _route_polyline_boxes(points, width):
    boxes = []
    for idx in range(len(points) - 1):
        if points[idx] == points[idx + 1]:
            continue
        boxes.append(_edge_aligned_lead_box(points[idx], points[idx + 1], width))
    for point in points[1:-1]:
        boxes.append(_center_box(point[0], point[1], width, width))
    return boxes


def _build_gate_route_boxes(geometry, route_start, values):
    pad_center = geometry["gate_pad_center"]
    active_box = geometry["active_box"]
    width = values["gate_lead_width"]
    clearance = max(values["bus_width"], values["gate_lead_width"], values["finger_far_extension"], 0.5)

    if geometry["orientation"] == "vertical":
        route_x = min(pad_center[0], active_box[2] + clearance)
        return _route_polyline_boxes([route_start, (route_x, route_start[1]), (route_x, pad_center[1]), pad_center], width)

    route_y = min(pad_center[1], active_box[3] + clearance)
    return _route_polyline_boxes([route_start, (route_start[0], route_y), (pad_center[0], route_y), pad_center], width)


def _left_pad_to_hbus_leads(pad_box, bus_left_x, bus_center_y, width, pitch):
    pad_center = _rect_center(pad_box)
    pad_mid_y = (pad_box[1] + pad_box[3]) / 2.0
    route_x = min(pad_center[0], bus_left_x - pitch - width / 2.0)
    return _route_polyline_boxes([(bus_left_x, bus_center_y), (route_x, bus_center_y), (route_x, pad_mid_y), pad_center], width)


def _bottom_pad_to_vbus_leads(pad_box, bus_center_x, bus_bottom_y, width, pitch):
    pad_center = _rect_center(pad_box)
    route_y = min(pad_center[1], bus_bottom_y - pitch - width / 2.0)
    return _route_polyline_boxes([(bus_center_x, bus_bottom_y), (bus_center_x, route_y), (pad_center[0], route_y), pad_center], width)


def _auto_slot_count(values):
    span = values["channel_width"] if values["finger_orientation"] == 0 else values["channel_height"]
    usable = max(span, values["finger_width"])
    pitch = values["finger_width"] + values["finger_spacing"]
    count = int((usable + values["finger_spacing"]) // pitch)
    return max(count, 2)


def _build_preview_geometry(values):
    cx = values["device_cx"]
    cy = values["device_cy"]
    channel = _center_box(cx, cy, values["channel_width"], values["channel_height"])
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
        sd_boxes = [
            _center_box((active_left + active_right) / 2.0, top_finger_top + busw / 2.0, active_right - active_left, busw),
            _center_box((active_left + active_right) / 2.0, bottom_finger_bottom - busw / 2.0, active_right - active_left, busw),
        ]

        for i in range(slots):
            x_left = x0 + i * pitch
            if i % 2 == 0:
                sd_boxes.append((x_left, top_finger_bottom, x_left + fw, top_finger_top))
            else:
                sd_boxes.append((x_left, bottom_finger_bottom, x_left + fw, bottom_finger_top))

        top_bus_top = top_finger_top + busw
        bottom_bus_bottom = bottom_finger_bottom - busw
        pad_stack_height = 2 * values["sd_pad_height"] + values["sd_pad_gap"]
        source_pad_bottom = cy - pad_stack_height / 2.0
        drain_pad_bottom = source_pad_bottom + values["sd_pad_height"] + values["sd_pad_gap"]
        pad_right = active_left - values["sd_lead_length"]
        source_pad_box = _xy_box(pad_right - values["sd_pad_width"], source_pad_bottom, pad_right, source_pad_bottom + values["sd_pad_height"])
        drain_pad_box = _xy_box(pad_right - values["sd_pad_width"], drain_pad_bottom, pad_right, drain_pad_bottom + values["sd_pad_height"])
        gate_pad_center = (active_right + values["gate_pad_gap"] + values["gate_pad_width"] / 2.0, cy)
        gate_pad_box = _center_box(gate_pad_center[0], gate_pad_center[1], values["gate_pad_width"], values["gate_pad_height"])
        sd_boxes.extend([source_pad_box, drain_pad_box])
        lead_boxes = []
        lead_boxes.extend(_left_pad_to_hbus_leads(source_pad_box, active_left, bottom_bus_bottom + busw / 2.0, busw, pitch))
        lead_boxes.extend(_left_pad_to_hbus_leads(drain_pad_box, active_left, top_bus_top - busw / 2.0, busw, pitch))
        active_box = _xy_box(active_left, min(bottom_finger_bottom, bottom_bus_bottom), active_right, max(top_finger_top, top_bus_top))
        finger_boxes = sd_boxes[2:-2]
        orientation = "vertical"
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
        sd_boxes = [
            _center_box(left_finger_left - busw / 2.0, (active_bottom + active_top) / 2.0, busw, active_top - active_bottom),
            _center_box(right_finger_right + busw / 2.0, (active_bottom + active_top) / 2.0, busw, active_top - active_bottom),
        ]

        for i in range(slots):
            y_bottom = y0 + i * pitch
            if i % 2 == 0:
                sd_boxes.append((left_finger_left, y_bottom, left_finger_right, y_bottom + fw))
            else:
                sd_boxes.append((right_finger_left, y_bottom, right_finger_right, y_bottom + fw))

        left_bus_left = left_finger_left - busw
        right_bus_right = right_finger_right + busw
        pad_stack_width = 2 * values["sd_pad_width"] + values["sd_pad_gap"]
        source_pad_left = cx - pad_stack_width / 2.0
        drain_pad_left = source_pad_left + values["sd_pad_width"] + values["sd_pad_gap"]
        pad_top = active_bottom - values["sd_lead_length"]
        source_pad_box = _xy_box(source_pad_left, pad_top - values["sd_pad_height"], source_pad_left + values["sd_pad_width"], pad_top)
        drain_pad_box = _xy_box(drain_pad_left, pad_top - values["sd_pad_height"], drain_pad_left + values["sd_pad_width"], pad_top)
        gate_pad_center = (cx, active_top + values["gate_pad_gap"] + values["gate_pad_height"] / 2.0)
        gate_pad_box = _center_box(gate_pad_center[0], gate_pad_center[1], values["gate_pad_width"], values["gate_pad_height"])
        sd_boxes.extend([source_pad_box, drain_pad_box])
        lead_boxes = []
        lead_boxes.extend(_bottom_pad_to_vbus_leads(source_pad_box, left_bus_left + busw / 2.0, active_bottom, busw, pitch))
        lead_boxes.extend(_bottom_pad_to_vbus_leads(drain_pad_box, right_bus_right - busw / 2.0, active_bottom, busw, pitch))
        active_box = _xy_box(min(left_finger_left, left_bus_left), active_bottom, max(right_finger_right, right_bus_right), active_top)
        finger_boxes = sd_boxes[2:-2]
        orientation = "horizontal"

    geometry = {
        "orientation": orientation,
        "active_box": active_box,
        "gate_pad_box": gate_pad_box,
        "gate_pad_center": gate_pad_center,
        "channel_box": channel,
    }

    gate_boxes = []
    if values["gate_mode"] == 0:
        grown = _grow_box(channel, values["gate_margin_x"], values["gate_margin_y"])
        gate_boxes.append(grown)
        route_start = _rect_center(grown)
    else:
        clipped_fingers = [_intersect_boxes(box, channel) for box in finger_boxes]
        clipped_fingers = [box for box in clipped_fingers if box is not None]
        if values["finger_orientation"] == 0:
            gap_boxes = _vertical_gap_boxes(channel, clipped_fingers)
            gate_boxes.extend(gap_boxes)
            bridge_h = max(min(fs, values["channel_height"] / 3.0), 0.2)
            for idx in range(len(gap_boxes) - 1):
                lg = gap_boxes[idx]
                rg = gap_boxes[idx + 1]
                if idx % 2 == 0:
                    gate_boxes.append(_xy_box(lg[2], channel[3] - bridge_h, rg[0], channel[3]))
                else:
                    gate_boxes.append(_xy_box(lg[2], channel[1], rg[0], channel[1] + bridge_h))
            if gap_boxes:
                attach_gap = max(gap_boxes, key=lambda box: box[2])
                route_start = _rect_center(attach_gap)
            else:
                route_start = _rect_center(channel)
        else:
            gap_boxes = _horizontal_gap_boxes(channel, clipped_fingers)
            gate_boxes.extend(gap_boxes)
            bridge_w = max(min(fs, values["channel_width"] / 3.0), 0.2)
            for idx in range(len(gap_boxes) - 1):
                lg = gap_boxes[idx]
                ug = gap_boxes[idx + 1]
                if idx % 2 == 0:
                    gate_boxes.append(_xy_box(channel[2] - bridge_w, lg[3], channel[2], ug[1]))
                else:
                    gate_boxes.append(_xy_box(channel[0], lg[3], channel[0] + bridge_w, ug[1]))
            if gap_boxes:
                attach_gap = max(gap_boxes, key=lambda box: box[3])
                route_start = _rect_center(attach_gap)
            else:
                route_start = _rect_center(channel)
        if values["gate_margin_x"] != 0.0 or values["gate_margin_y"] != 0.0:
            gate_boxes = [_grow_box(box, values["gate_margin_x"], values["gate_margin_y"]) for box in gate_boxes]

    gate_boxes.append(gate_pad_box)
    gate_boxes.extend(_build_gate_route_boxes(geometry, route_start, values))

    return {
        "channel": [channel],
        "sd": sd_boxes + lead_boxes,
        "gate": gate_boxes,
        "labels": {
            "channel": [{"text": "Channel", "center": _rect_center(channel), "box": channel}],
            "sd": [
                {"text": "S", "center": _rect_center(source_pad_box), "box": source_pad_box},
                {"text": "D", "center": _rect_center(drain_pad_box), "box": drain_pad_box},
            ],
            "gate": [{"text": "G", "center": _rect_center(gate_pad_box), "box": gate_pad_box}],
        },
        "bounds": [channel, active_box, gate_pad_box],
    }


def _boxes_to_path(boxes):
    path = QPainterPath()
    for box in boxes:
        rect_path = QPainterPath()
        rect_path.addRect(_rectf_from_box(box))
        path = rect_path if path.isEmpty() else path.united(rect_path)
    return path


def _add_label(scene, text, center, color, box, font_size=8):
    item = scene.addSimpleText(text)
    font = QFont("Segoe UI", font_size)
    font.setStyleStrategy(QFont.PreferAntialias)
    item.setFont(font)
    item.setBrush(QBrush(color))
    bounds = item.boundingRect()
    x = center[0] - bounds.width() / 2.0
    y = center[1] - bounds.height() / 2.0
    if box is not None:
        x = min(max(x, box[0]), box[2] - bounds.width())
        y = min(max(y, box[1]), box[3] - bounds.height())
    item.setPos(x, y)


def _nice_length(value):
    if value <= 0:
        return 1.0
    decade = 1.0
    while value > decade * 10.0:
        decade *= 10.0
    while value < decade:
        decade /= 10.0
    for factor in (1.0, 2.0, 5.0, 10.0):
        candidate = decade * factor
        if candidate >= value:
            return candidate
    return decade * 10.0


def _format_length(value_um):
    if value_um >= 1000.0:
        return f"{value_um / 1000.0:.2f} mm"
    if value_um >= 100.0:
        return f"{value_um:.0f} um"
    if value_um >= 10.0:
        return f"{value_um:.1f} um"
    return f"{value_um:.2f} um"


def render_nanodevice_fet(scene, values, visible_layers=None):
    visible_layers = visible_layers or {"channel": True, "sd": True, "gate": True}
    geometry = _build_preview_geometry(values)

    pen_channel = QPen(QColor("#f4d35e"), 0)
    pen_sd = QPen(QColor("#ff5a6e"), 0)
    pen_gate = QPen(QColor("#2bd5c4"), 0)
    brush_channel = QBrush(QColor(244, 211, 94, 70))
    brush_sd = QBrush(QColor(215, 38, 61, 95))
    brush_gate = QBrush(QColor(27, 153, 139, 95))
    pad_label_color = QColor("#f5f5f5")
    channel_label_color = QColor(255, 255, 255, 150)

    layer_specs = {
        "channel": (pen_channel, brush_channel),
        "sd": (pen_sd, brush_sd),
        "gate": (pen_gate, brush_gate),
    }

    for layer_key in ("channel", "sd", "gate"):
        if not visible_layers.get(layer_key, True):
            continue
        path = _boxes_to_path(geometry[layer_key])
        pen, brush = layer_specs[layer_key]
        _draw_path(scene, path, pen, brush)
        for label_spec in geometry["labels"][layer_key]:
            _add_label(
                scene,
                label_spec["text"],
                label_spec["center"],
                channel_label_color if layer_key == "channel" else pad_label_color,
                label_spec["box"],
                font_size=7 if layer_key == "channel" else 8,
            )


def _default_font_directory():
    windir = os.environ.get("WINDIR", "C:/Windows")
    return os.path.join(windir, "Fonts")


def _font_family_from_path(font_path):
    path = os.path.normpath(str(font_path or "").strip())
    if path in _FONT_FAMILY_CACHE:
        return _FONT_FAMILY_CACHE[path]

    family = "Segoe UI"
    if path and os.path.exists(path):
        font_id = QFontDatabase.addApplicationFont(path)
        if font_id >= 0:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                family = families[0]

    _FONT_FAMILY_CACHE[path] = family
    return family


def _build_truetype_text_path(values):
    text = values.get("text", "") or "Text"
    size_um = max(float(values.get("size_um", 10.0)), 0.1)
    x = float(values.get("x", 0.0))
    y = float(values.get("y", 0.0))
    anchor = str(values.get("anchor", "center") or "center")
    font_path = str(values.get("font_path", os.path.join(_default_font_directory(), "arial.ttf")))
    spacing_um = max(float(values.get("spacing_um", 0.0)), 0.0)

    font = QFont(_font_family_from_path(font_path))
    font.setStyleStrategy(QFont.PreferAntialias)
    font.setPointSizeF(max(size_um * 0.55, 1.0))
    metrics = QFontMetricsF(font)
    spacing_px = spacing_um * 0.55

    path = QPainterPath()
    cursor_x = 0.0
    for char in text:
        char_path = QPainterPath()
        char_path.addText(0.0, 0.0, font, char)
        char_bounds = char_path.boundingRect()
        path.addPath(char_path.translated(cursor_x - char_bounds.left(), 0.0))
        cursor_x += metrics.horizontalAdvance(char) + spacing_px

    bounds = path.boundingRect()
    anchor_x, anchor_y = _anchor_offset(bounds, anchor)
    return path.translated(x - anchor_x, y - anchor_y)


def _build_deplof_text_path(values):
    text = values.get("text", "") or "Text"
    size_um = max(float(values.get("size_um", 10.0)), 0.1)
    x = float(values.get("x", 0.0))
    y = float(values.get("y", 0.0))
    anchor = str(values.get("anchor", "center") or "center")
    justify = str(values.get("justify", "left") or "left").lower()
    scaling = size_um / 1000.0

    path = QPainterPath()
    line_paths = []
    yoffset = 0.0
    for line in text.split("\n"):
        line_path = QPainterPath()
        xoffset = 0.0
        for char in line:
            ascii_val = ord(char)
            if char == " ":
                xoffset += 500.0 * scaling
                continue
            if ascii_val not in DEPLOF_GLYPH:
                continue
            for poly in DEPLOF_GLYPH[ascii_val]:
                if not poly:
                    continue
                poly_path = QPainterPath()
                first_x, first_y = poly[0]
                poly_path.moveTo(first_x * scaling + xoffset, -(first_y * scaling + yoffset))
                for px, py in poly[1:]:
                    poly_path.lineTo(px * scaling + xoffset, -(py * scaling + yoffset))
                poly_path.closeSubpath()
                line_path.addPath(poly_path)
            xoffset += (DEPLOF_WIDTH[ascii_val] + DEPLOF_INDENT[ascii_val]) * scaling

        bounds = line_path.boundingRect()
        if justify == "center":
            line_path = line_path.translated(-bounds.center().x(), 0.0)
        elif justify == "right":
            line_path = line_path.translated(-bounds.right(), 0.0)
        line_paths.append(line_path)
        yoffset += 1500.0 * scaling

    for line_path in line_paths:
        path.addPath(line_path)

    bounds = path.boundingRect()
    anchor_x, anchor_y = _anchor_offset(bounds, anchor)
    return path.translated(x - anchor_x, y - anchor_y)


def _build_text_path(values):
    engine = str(values.get("font_engine", "truetype") or "truetype").lower()
    if engine == "deplof":
        return _build_deplof_text_path(values)
    return _build_truetype_text_path(values)


def _truetype_text_shapes(values, dbu=DEFAULT_DBU):
    path = _build_text_path(values)
    shapes = []
    for polygon in path.toFillPolygons():
        points = [pya.Point(int(round(point.x() / dbu)), int(round(-point.y() / dbu))) for point in polygon]
        if len(points) >= 2 and points[0] == points[-1]:
            points = points[:-1]
        if len(points) >= 3:
            shapes.append(pya.Polygon(points))
    return shapes


def render_gdsfactory_text(scene, values, visible_layers=None):
    visible_layers = visible_layers or {"labels": True}
    if not visible_layers.get("labels", visible_layers.get("text", True)):
        return

    pen = QPen(QColor("#6cc0ff"), 0)
    brush = QBrush(QColor(108, 192, 255, 70))
    _draw_path(scene, _build_text_path(values), pen, brush)


def _anchor_offset(bounds, anchor):
    anchor = anchor or "center"
    center_x = bounds.center().x()
    center_y = bounds.center().y()
    mapping = {
        "left_top": (bounds.left(), bounds.top()),
        "center_top": (center_x, bounds.top()),
        "right_top": (bounds.right(), bounds.top()),
        "left_center": (bounds.left(), center_y),
        "center": (center_x, center_y),
        "right_center": (bounds.right(), center_y),
        "left_bottom": (bounds.left(), bounds.bottom()),
        "center_bottom": (center_x, bounds.bottom()),
        "right_bottom": (bounds.right(), bounds.bottom()),
    }
    anchor_x, anchor_y = mapping.get(anchor, (center_x, center_y))
    return anchor_x, anchor_y


def _render_text_path(scene, text, values, color, family="Segoe UI", weight=QFont.Normal):
    text = text or "Text"
    size_um = max(float(values.get("size_um", values.get("size", 20.0))), 0.5)
    x = float(values.get("x", 0.0))
    y = float(values.get("y", 0.0))
    anchor = values.get("anchor", "center")

    font = QFont(family)
    font.setStyleStrategy(QFont.PreferAntialias)
    font.setWeight(weight)
    font.setPointSizeF(max(size_um * 0.55, 1.0))

    path = QPainterPath()
    path.addText(0.0, 0.0, font, text)
    bounds = path.boundingRect()
    anchor_x, anchor_y = _anchor_offset(bounds, anchor)
    translated = path.translated(x - anchor_x, y - anchor_y)
    _draw_path(scene, translated, QPen(color, 0), QBrush(QColor(color.red(), color.green(), color.blue(), 85)))


def render_nanodevice_text(scene, values, visible_layers=None):
    visible_layers = visible_layers or {"text": True}
    if not visible_layers.get("text", True):
        return
    _render_text_path(scene, values.get("text", "Hello KLayout"), values, QColor("#ffd166"), family="Consolas")


def render_digital_text(scene, values, visible_layers=None):
    visible_layers = visible_layers or {"text": True}
    if not visible_layers.get("text", True):
        return
    local_values = dict(values)
    local_values["size_um"] = max(values.get("size", 10.0), 1.0) * 1.4
    _render_text_path(
        scene,
        values.get("text", "NANO DEVICE"),
        local_values,
        QColor("#ef476f"),
        family="Bahnschrift",
        weight=QFont.Bold,
    )


def render_qrcode(scene, values, visible_layers=None):
    visible_layers = visible_layers or {"qr": True}
    if not visible_layers.get("qr", True):
        return

    text = values.get("text", "") or "QR"
    box_size = max(float(values.get("box_size", 3.0)), 0.2)
    border = max(int(values.get("border", 4)), 0)
    version = max(int(values.get("version", 2)), 1)
    try:
        import qrcode

        qr = qrcode.QRCode(
            version=version,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=1,
            border=border,
        )
        qr.add_data(text)
        qr.make(fit=True)
        matrix = qr.get_matrix()
    except Exception:
        side = version * 4 + 17 + 2 * border
        matrix = [[(row + col) % 2 == 0 for col in range(side)] for row in range(side)]

    rows = len(matrix)
    cols = len(matrix[0]) if rows else 0
    width = cols * box_size
    height = rows * box_size
    x0 = -width / 2.0
    y0 = -height / 2.0
    pen = QPen(QColor("#f5f5f5"), 0)
    brush = QBrush(QColor(245, 245, 245, 220))
    for row_idx, row in enumerate(matrix):
        for col_idx, value in enumerate(row):
            if not value:
                continue
            rect = QRectF(x0 + col_idx * box_size, y0 + row_idx * box_size, box_size, box_size)
            scene.addRect(rect, pen, brush)

    outline_pen = QPen(QColor("#8ecae6"), 0)
    scene.addRect(QRectF(x0, y0, width, height), outline_pen)


def _pick_edge(cx, cy, tx, ty):
    dx = tx - cx
    dy = ty - cy
    if abs(dx) >= abs(dy):
        return "R" if dx >= 0 else "L"
    return "U" if dy >= 0 else "D"


def _edge_center(box, edge):
    cx, cy = _rect_center(box)
    if edge == "L":
        return (box[0], cy)
    if edge == "R":
        return (box[2], cy)
    if edge == "U":
        return (cx, box[3])
    return (cx, box[1])


def _polyline_path(points, width):
    path = QPainterPath()
    if len(points) < 2:
        return path
    rect_path = QPainterPath()
    for box in _route_polyline_boxes(points, width):
        rect_path.addRect(_rectf_from_box(box))
    return rect_path


def render_fanout(scene, values, visible_layers=None):
    visible_layers = visible_layers or {"pads": True, "lead": True}
    inner_pad = _center_box(
        values["inner_center_x"],
        values["inner_center_y"],
        values["inner_length"],
        values["inner_width"],
    )
    outer_pad = _center_box(
        values["outer_center_x"],
        values["outer_center_y"],
        values["outer_length"],
        values["outer_width"],
    )

    if visible_layers.get("pads", True):
        pad_pen = QPen(QColor("#ffb703"), 0)
        pad_brush = QBrush(QColor(255, 183, 3, 90))
        _draw_path(scene, _boxes_to_path([inner_pad, outer_pad]), pad_pen, pad_brush)
        _add_label(scene, "Inner", _rect_center(inner_pad), QColor("#f5f5f5"), inner_pad, font_size=8)
        _add_label(scene, "Outer", _rect_center(outer_pad), QColor("#f5f5f5"), outer_pad, font_size=8)

    if not visible_layers.get("lead", True):
        return

    inner_edge = values.get("inner_edge") or _pick_edge(
        values["inner_center_x"],
        values["inner_center_y"],
        values["outer_center_x"],
        values["outer_center_y"],
    )
    outer_edge = values.get("outer_edge") or _pick_edge(
        values["outer_center_x"],
        values["outer_center_y"],
        values["inner_center_x"],
        values["inner_center_y"],
    )
    start = _edge_center(inner_pad, inner_edge)
    end = _edge_center(outer_pad, outer_edge)

    fanout_type = values["fanout_type"]
    lead_pen = QPen(QColor("#219ebc"), 0)
    lead_brush = QBrush(QColor(33, 158, 188, 95))

    if fanout_type == 0:
        polygon = QPainterPath()
        polygon.moveTo(start[0], start[1] - values["lead_line_width"] / 2.0)
        polygon.lineTo(start[0], start[1] + values["lead_line_width"] / 2.0)
        polygon.lineTo(end[0], end[1] + max(values["outer_width"], values["lead_line_width"]) / 2.0)
        polygon.lineTo(end[0], end[1] - max(values["outer_width"], values["lead_line_width"]) / 2.0)
        polygon.closeSubpath()
        _draw_path(scene, polygon, lead_pen, lead_brush)
        return

    mid = (end[0], start[1]) if abs(end[0] - start[0]) >= abs(end[1] - start[1]) else (start[0], end[1])
    route = _polyline_path([start, mid, end], max(values["lead_line_width"], 0.2))
    _draw_path(scene, route, lead_pen, lead_brush)


def _rotate_points(points, angle_deg, center):
    angle = math.radians(angle_deg)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    cx, cy = center
    rotated = []
    for x, y in points:
        dx = x - cx
        dy = y - cy
        rotated.append((cx + dx * cos_a - dy * sin_a, cy + dx * sin_a + dy * cos_a))
    return rotated


def _polygon_path(points):
    if not points:
        return QPainterPath()
    path = QPainterPath()
    path.moveTo(points[0][0], points[0][1])
    for x, y in points[1:]:
        path.lineTo(x, y)
    path.closeSubpath()
    return path


def render_mark(scene, values, visible_layers=None):
    visible_layers = visible_layers or {"mark": True}
    if not visible_layers.get("mark", True):
        return

    x = values["x"]
    y = values["y"]
    size = max(values["size"], 0.2)
    width = max(values["width"], 0.1)
    shape = values["shape"]
    rotation = values["rotation"]
    half = size / 2.0
    color = QColor("#90be6d")
    pen = QPen(color, 0)
    brush = QBrush(QColor(color.red(), color.green(), color.blue(), 90))
    path = QPainterPath()

    if shape in ("cross", "cross_pos", "cross_neg", "semi_cross"):
        horiz = _center_box(x, y, size, width)
        vert = _center_box(x, y, width, size)
        path = _boxes_to_path([horiz, vert])
    elif shape in ("square", "sq_missing", "sq_missing_border", "sq_missing_rotborder", "sq_missing_diff_rotborder"):
        path.addRect(_rectf_from_box(_center_box(x, y, size, size)))
    elif shape == "circle":
        path.addEllipse(QRectF(x - half, y - half, size, size))
    elif shape == "diamond":
        path = _polygon_path([(x, y + half), (x + half, y), (x, y - half), (x - half, y)])
    elif shape in ("triangle_up", "triangle_down"):
        direction = -1 if shape == "triangle_up" else 1
        path = _polygon_path([(x, y + direction * half), (x + half, y - direction * half), (x - half, y - direction * half)])
    elif shape in ("L", "l_shape"):
        path = _boxes_to_path([
            _xy_box(x - half, y - half, x - half + width, y + half),
            _xy_box(x - half, y - half, x + half, y - half + width),
        ])
    elif shape in ("T", "t_shape"):
        path = _boxes_to_path([
            _xy_box(x - width / 2.0, y - half, x + width / 2.0, y + half),
            _xy_box(x - half, y + half - width, x + half, y + half),
        ])
    elif shape == "regular_polygon":
        sides = max(int(values["parameter1"]), 3)
        points = []
        for idx in range(sides):
            angle = 2.0 * math.pi * idx / sides - math.pi / 2.0
            points.append((x + half * math.cos(angle), y + half * math.sin(angle)))
        path = _polygon_path(points)
    else:
        path.addRect(_rectf_from_box(_center_box(x, y, size, size)))

    if abs(rotation) > 1e-9:
        center = path.boundingRect().center()
        transform = pya.ICplxTrans(1.0, rotation, False, 0.0, 0.0)
        rotated_points = _rotate_points(
            [(path.boundingRect().left(), path.boundingRect().top())],
            rotation,
            (center.x(), center.y()),
        )
        _ = transform
        path = _polygon_path(_rotate_points(
            [(pt.x(), pt.y()) for pt in [path.boundingRect().topLeft(), path.boundingRect().topRight(), path.boundingRect().bottomRight(), path.boundingRect().bottomLeft()]],
            rotation,
            (center.x(), center.y()),
        )) if shape in ("square", "sq_missing", "sq_missing_border", "sq_missing_rotborder", "sq_missing_diff_rotborder") else path

    _draw_path(scene, path, pen, brush)
    if shape not in ("cross", "square", "circle", "diamond", "triangle_up", "triangle_down", "L", "T"):
        _add_label(scene, shape, (x, y - half - 8.0), QColor("#f5f5f5"), None, font_size=7)


def _legacy_interdigitated_geometry(values):
    cx = values["device_cx"]
    cy = values["device_cy"]
    active = _center_box(cx, cy, values["active_width"], values["active_height"])
    left, bottom, right, top = active
    side_span = max((values["active_width"] - values["channel_gap"]) / 2.0, 0.2)
    bus_width = min(values["sd_bus_width"], side_span)

    source_bus_x2 = left + bus_width
    drain_bus_x1 = right - bus_width
    source_bus = _xy_box(left, bottom, source_bus_x2, top)
    drain_bus = _xy_box(drain_bus_x1, bottom, right, top)

    source_finger_x1 = source_bus_x2
    source_finger_x2 = max(source_finger_x1, cx - values["channel_gap"] / 2.0)
    drain_finger_x1 = min(drain_bus_x1, cx + values["channel_gap"] / 2.0)
    drain_finger_x2 = drain_bus_x1

    pitch = values["finger_width"] + values["finger_spacing"]
    max_fit = max(1, int(math.floor((values["active_height"] + values["finger_spacing"]) / max(pitch, 1e-9))))
    finger_count = min(int(values["finger_count"]), max_fit)
    used_height = finger_count * values["finger_width"] + max(0, finger_count - 1) * values["finger_spacing"]
    y0 = cy - used_height / 2.0
    sd_boxes = [source_bus, drain_bus]
    for index in range(finger_count):
        y1 = y0 + index * pitch
        y2 = y1 + values["finger_width"]
        if index % 2 == 0:
            sd_boxes.append(_xy_box(source_finger_x1, y1, source_finger_x2, y2))
        else:
            sd_boxes.append(_xy_box(drain_finger_x1, y1, drain_finger_x2, y2))

    source_pad = _center_box(values["source_pad_cx"], values["source_pad_cy"], values["source_pad_width"], values["source_pad_height"])
    drain_pad = _center_box(values["drain_pad_cx"], values["drain_pad_cy"], values["drain_pad_width"], values["drain_pad_height"])
    gate_pad = _center_box(values["gate_pad_cx"], values["gate_pad_cy"], values["gate_pad_width"], values["gate_pad_height"])

    if values["gate_mode"] == 0:
        gate = _center_box(
            cx + values["gate_x_offset"],
            cy + values["gate_y_offset"],
            max(values["active_width"] + 2.0 * values["gate_enclosure_x"], 0.2),
            max(values["active_height"] + 2.0 * values["gate_enclosure_y"], 0.2),
        )
    else:
        gate = _center_box(
            cx + values["gate_x_offset"],
            cy + values["gate_y_offset"],
            max(values["channel_gap"] + 2.0 * values["gate_enclosure_x"], 0.2),
            max(values["active_height"] + 2.0 * values["gate_enclosure_y"], 0.2),
        )

    source_route = _polyline_path([_edge_center(source_bus, "L"), _edge_center(source_pad, "R")], values["outer_bus_width"])
    drain_route = _polyline_path([_edge_center(drain_bus, "R"), _edge_center(drain_pad, "L")], values["outer_bus_width"])
    gate_route = _polyline_path([_edge_center(gate, "U"), _edge_center(gate_pad, "D")], values["gate_lead_width"])

    return {
        "active": [active],
        "sd": sd_boxes + [source_pad, drain_pad],
        "gate": [gate, gate_pad],
        "sd_route": source_route.united(drain_route),
        "gate_route": gate_route,
        "labels": [
            ("Active", _rect_center(active), active),
            ("S", _rect_center(source_pad), source_pad),
            ("D", _rect_center(drain_pad), drain_pad),
            ("G", _rect_center(gate_pad), gate_pad),
        ],
    }


def render_nanodevice_classic_fet(scene, values, visible_layers=None):
    visible_layers = visible_layers or {"active": True, "sd": True, "gate": True}
    geometry = _legacy_interdigitated_geometry(values)

    if visible_layers.get("active", True):
        _draw_path(scene, _boxes_to_path(geometry["active"]), QPen(QColor("#f4d35e"), 0), QBrush(QColor(244, 211, 94, 70)))
    if visible_layers.get("sd", True):
        sd_path = _boxes_to_path(geometry["sd"]).united(geometry["sd_route"])
        _draw_path(scene, sd_path, QPen(QColor("#ee6c4d"), 0), QBrush(QColor(238, 108, 77, 95)))
    if visible_layers.get("gate", True):
        gate_path = _boxes_to_path(geometry["gate"]).united(geometry["gate_route"])
        _draw_path(scene, gate_path, QPen(QColor("#2a9d8f"), 0), QBrush(QColor(42, 157, 143, 95)))

    for label, center, box in geometry["labels"]:
        _add_label(scene, label, center, QColor("#f5f5f5"), box, font_size=8)


def _nanodevice_fet_insert_params(_values):
    return {
        "channel_layer": pya.LayerInfo(14, 0),
        "sd_layer": pya.LayerInfo(16, 0),
        "gate_layer": pya.LayerInfo(18, 0),
    }


def _gdsfactory_text_insert_params(values):
    layer, datatype = values["layer_spec"]
    return {
        "layer": pya.LayerInfo(int(layer), int(datatype)),
    }


def _text_backend_mode(values):
    return str(values.get("backend", "auto") or "auto").strip().lower()


def _build_klayout_text_region(text, size_um, center_x, center_y, dbu=0.001):
    text_region = _preview_text_region(text, max(size_um, 0.1))
    bbox = text_region.bbox()
    src_center_x = (bbox.left + bbox.right) * 0.001 / 2.0
    src_center_y = (bbox.bottom + bbox.top) * 0.001 / 2.0
    dx = int(round((center_x - src_center_x) / dbu))
    dy = int(round((center_y - src_center_y) / dbu))
    return text_region.moved(dx, dy)


def _insert_gdsfactory_text(layout, top_cell, values):
    layer, datatype = values["layer_spec"]
    layer_index = layout.layer(int(layer), int(datatype))
    for shape in _truetype_text_shapes(values):
        top_cell.shapes(layer_index).insert(shape)


def _layer_insert_params(param_key):
    def builder(values):
        layer, datatype = values[param_key]
        return {
            param_key.replace("_spec", ""): pya.LayerInfo(int(layer), int(datatype)),
        }

    return builder


def _nanodevice_classic_fet_insert_params(values):
    sd_layer, sd_datatype = values["sd_layer_spec"]
    gate_layer, gate_datatype = values["gate_layer_spec"]
    return {
        "sd_layer": pya.LayerInfo(int(sd_layer), int(sd_datatype)),
        "gate_layer": pya.LayerInfo(int(gate_layer), int(gate_datatype)),
    }


def _preview_text_region(text, size_um):
    generator = pya.TextGenerator.default_generator()
    mag = float(size_um) / max(generator.dheight(), 1e-9)
    return generator.text(text, 0.001, mag, False, 0.0, 0.0, 0.0).merged()


def _external_python_candidates():
    candidates = []
    env_python = os.environ.get("NANODEVICE_EXTERNAL_PYTHON")
    if env_python:
        candidates.append([env_python])

    conda_python = shutil.which("python")
    if conda_python:
        candidates.append([conda_python])

    py_launcher = shutil.which("py")
    if py_launcher:
        candidates.append([py_launcher, "-3"])
    return candidates


def _run_external_text_polygon_script(text, size_um, justify="left"):
    if not os.path.exists(TEXT_POLYGON_SCRIPT):
        raise RuntimeError(f"Text polygon generator not found: {TEXT_POLYGON_SCRIPT}")

    errors = []
    for candidate in _external_python_candidates():
        if not candidate:
            continue
        try:
            completed = subprocess.run(
                [*candidate, TEXT_POLYGON_SCRIPT, text, str(float(size_um)), justify],
                capture_output=True,
                text=True,
                check=True,
            )
            return json.loads(completed.stdout)
        except Exception as exc:
            errors.append(f"{' '.join(candidate)}: {exc}")

    raise RuntimeError(
        "Unable to run external gdsfactory text generator. "
        "Set NANODEVICE_EXTERNAL_PYTHON or install gdsfactory in an external Python environment. "
        "You can also install it into the local pydeps folder beside generate_gdsfactory_text_polygons.py.\n"
        + "\n".join(errors)
    )


def _text_payload_to_paths(payload, center_x, center_y):
    bbox = payload.get("bbox") or [[0.0, 0.0], [0.0, 0.0]]
    min_x = float(bbox[0][0])
    min_y = float(bbox[0][1])
    max_x = float(bbox[1][0])
    max_y = float(bbox[1][1])
    bbox_center_x = (min_x + max_x) / 2.0
    bbox_center_y = (min_y + max_y) / 2.0
    dx = float(center_x) - bbox_center_x
    dy = float(center_y) - bbox_center_y

    paths = []
    for polygon in payload.get("polygons", []):
        if len(polygon) < 3:
            continue
        path = QPainterPath()
        first_x, first_y = polygon[0]
        path.moveTo(float(first_x) + dx, -(float(first_y) + dy))
        for px, py in polygon[1:]:
            path.lineTo(float(px) + dx, -(float(py) + dy))
        path.closeSubpath()
        paths.append(path)
    return paths


def _text_payload_to_region(payload, center_x, center_y):
    bbox = payload.get("bbox") or [[0.0, 0.0], [0.0, 0.0]]
    min_x = float(bbox[0][0])
    min_y = float(bbox[0][1])
    max_x = float(bbox[1][0])
    max_y = float(bbox[1][1])
    bbox_center_x = (min_x + max_x) / 2.0
    bbox_center_y = (min_y + max_y) / 2.0
    dx = float(center_x) - bbox_center_x
    dy = float(center_y) - bbox_center_y

    region = pya.Region()
    for polygon in payload.get("polygons", []):
        points = [pya.Point(int(round((float(px) + dx) * 1000.0)), int(round((float(py) + dy) * 1000.0))) for px, py in polygon]
        if len(points) >= 3:
            region.insert(pya.Polygon(points))
    return region


NANODEVICE_FET_TOOL = ToolSpec(
    key="nanodevice_fet",
    title="Interdigitated FET",
    library_name="NanoDeviceToolkitLib",
    pcell_name="NanoDeviceFETPCell",
    preview_renderer=render_nanodevice_fet,
    preview_layers=[("channel", "Channel"), ("source_drain", "Source / Drain"), ("top_gate", "Gate")],
    insert_params_builder=_nanodevice_fet_insert_params,
    params=[
        ParameterSpec("device_cx", "Center X", "Cx", "Placement", 0.0, minimum=-1000.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("device_cy", "Center Y", "Cy", "Placement", 0.0, minimum=-1000.0, maximum=1000.0, suffix=" um"),
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
        ParameterSpec("channel_width", "Channel Width", "Wch", "Channel", 50.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("channel_height", "Channel Height", "Hch", "Channel", 50.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("finger_width", "Finger Width", "Wf", "Finger", 2.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("finger_spacing", "Finger Spacing", "Sf", "Finger", 2.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("finger_extension", "Bus-side Extension", "Lf,b", "Finger", 8.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("finger_far_extension", "Far-side Extension", "Lf,f", "Finger", 4.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("bus_width", "Bus Width", "Wbus", "Finger", 8.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("sd_lead_length", "Lead Length", "Llead", "Source / Drain", 10.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("sd_pad_width", "Pad Width", "Wpad", "Source / Drain", 50.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("sd_pad_height", "Pad Height", "Hpad", "Source / Drain", 50.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("sd_pad_gap", "Pad-to-Pad Gap", "Gpad", "Source / Drain", 15.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec(
            "gate_mode",
            "Gate Mode",
            "Gmode",
            "Gate",
            1,
            kind="choice",
            choices=[("global", 0), ("channel_only", 1)],
            tooltip="global = same size as channel before resize, channel_only = serpentine inter-finger region.",
        ),
        ParameterSpec("gate_margin_x", "Resize X", "dGx", "Gate", 0.5, minimum=-1000.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("gate_margin_y", "Resize Y", "dGy", "Gate", 0.5, minimum=-1000.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("gate_lead_width", "Lead Width", "Wglead", "Gate", 20.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("gate_pad_width", "Pad Width", "Wgpad", "Gate", 50.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("gate_pad_height", "Pad Height", "Hgpad", "Gate", 50.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("gate_pad_gap", "Pad Gap", "Ggpad", "Gate", 15.0, minimum=0.1, maximum=1000.0, suffix=" um"),
    ],
)


GDSFACTORY_TEXT_TOOL = ToolSpec(
    key="gdsfactory_text",
    title="KLayout Text",
    library_name="",
    pcell_name="",
    preview_renderer=render_gdsfactory_text,
    preview_layers=[("labels", "Text")],
    insert_handler=_insert_gdsfactory_text,
    params=[
        ParameterSpec("text", "Text", "Txt", "Content", "ABC123", kind="string", tooltip="Text rendered from the specified TrueType font."),
        ParameterSpec("x", "Anchor X", "X", "Placement", 0.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("y", "Anchor Y", "Y", "Placement", 0.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("font_engine", "Font Engine", "FE", "Style", "truetype", kind="choice", choices=[("truetype", "truetype"), ("deplof_polygon", "deplof")], tooltip="truetype uses a selected TTF/OTF font. deplof_polygon reproduces the vendored gdsfactory DEPLOF polygon font."),
        ParameterSpec("size_um", "Font Size", "H", "Style", 20.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("font_path", "Font Path", "Font", "Style", os.path.join(_default_font_directory(), "OCRAEXT.TTF"), kind="font_path", tooltip="Path to the TrueType font used for polygon generation."),
        ParameterSpec("spacing_um", "Char Spacing", "Sp", "Style", 0.0, minimum=0.0, maximum=100.0, suffix=" um"),
        ParameterSpec("justify", "Justify", "J", "Style", "left", kind="choice", choices=[("left", "left"), ("center", "center"), ("right", "right")]),
        ParameterSpec(
            "anchor",
            "Anchor",
            "Anc",
            "Placement",
            "center",
            kind="choice",
            choices=[
                ("left_top", "left_top"),
                ("center_top", "center_top"),
                ("right_top", "right_top"),
                ("left_center", "left_center"),
                ("center", "center"),
                ("right_center", "right_center"),
                ("left_bottom", "left_bottom"),
                ("center_bottom", "center_bottom"),
                ("right_bottom", "right_bottom"),
            ],
        ),
        ParameterSpec("layer_spec", "Layer", "L", "Layer", (10, 0), kind="layer_choice"),
    ],
)


NANODEVICE_TEXT_TOOL = ToolSpec(
    key="nanodevice_text",
    title="NanoDevice Text",
    library_name="NanoDeviceLib",
    pcell_name="TextPCell",
    preview_renderer=render_nanodevice_text,
    preview_layers=[("labels", "Text")],
    insert_params_builder=_layer_insert_params("layer_spec"),
    params=[
        ParameterSpec("text", "Text", "Txt", "Content", "Hello KLayout", kind="string"),
        ParameterSpec("x", "Anchor X", "X", "Placement", 0.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("y", "Anchor Y", "Y", "Placement", 0.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("size_um", "Font Size", "H", "Style", 10.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("font_path", "Font Path", "Font", "Style", os.path.join(_default_font_directory(), "OCRAEXT.TTF"), kind="font_path"),
        ParameterSpec("spacing_um", "Char Spacing", "Sp", "Style", 0.0, minimum=0.0, maximum=100.0, suffix=" um"),
        ParameterSpec(
            "anchor",
            "Anchor",
            "Anc",
            "Placement",
            "center",
            kind="choice",
            choices=[
                ("left_top", "left_top"),
                ("center_top", "center_top"),
                ("right_top", "right_top"),
                ("left_center", "left_center"),
                ("center", "center"),
                ("right_center", "right_center"),
                ("left_bottom", "left_bottom"),
                ("center_bottom", "center_bottom"),
                ("right_bottom", "right_bottom"),
            ],
        ),
        ParameterSpec("layer_spec", "Layer", "L", "Layer", (10, 0), kind="layer_choice"),
    ],
)


QRCODE_TOOL = ToolSpec(
    key="qrcode",
    title="QRCode",
    library_name="NanoDeviceLib",
    pcell_name="QRCodePCell",
    preview_renderer=render_qrcode,
    preview_layers=[("qr", "QR")],
    insert_params_builder=_layer_insert_params("layer_spec"),
    params=[
        ParameterSpec("text", "QR Content", "Txt", "Content", "https://github.com/iCalculate/klayout-nanodevice-toolkit", kind="string"),
        ParameterSpec("box_size", "Box Size", "B", "Geometry", 3.0, minimum=0.1, maximum=100.0, suffix=" um"),
        ParameterSpec("version", "Version", "V", "Geometry", 2, kind="int", minimum=1, maximum=40),
        ParameterSpec("border", "Border", "Bd", "Geometry", 4, kind="int", minimum=0, maximum=20),
        ParameterSpec("layer_spec", "Layer", "L", "Layer", (10, 0), kind="layer_choice"),
    ],
)


FANOUT_TOOL = ToolSpec(
    key="fanout",
    title="Fanout",
    library_name="NanoDeviceLib",
    pcell_name="FanoutPCell",
    preview_renderer=render_fanout,
    preview_layers=[("pads", "Pads"), ("lead", "Lead")],
    insert_params_builder=_layer_insert_params("layer_spec"),
    params=[
        ParameterSpec("inner_center_x", "Inner Center X", "Xin", "Inner Pad", 0.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("inner_center_y", "Inner Center Y", "Yin", "Inner Pad", 0.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("inner_length", "Inner Length", "Lin", "Inner Pad", 8.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("inner_width", "Inner Width", "Win", "Inner Pad", 4.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("inner_chamfer_size", "Inner Chamfer", "Cin", "Inner Pad", 0.0, minimum=0.0, maximum=200.0, suffix=" um"),
        ParameterSpec("inner_chamfer_type", "Inner Chamfer Type", "Tin", "Inner Pad", 0, kind="choice", choices=[("none", 0), ("straight", 1), ("round", 2)]),
        ParameterSpec("inner_corner_pts", "Inner Corner Pts", "Pin", "Inner Pad", 4, kind="int", minimum=2, maximum=64),
        ParameterSpec("outer_center_x", "Outer Center X", "Xout", "Outer Pad", 50.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("outer_center_y", "Outer Center Y", "Yout", "Outer Pad", -30.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("outer_length", "Outer Length", "Lout", "Outer Pad", 20.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("outer_width", "Outer Width", "Wout", "Outer Pad", 20.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("outer_chamfer_size", "Outer Chamfer", "Cout", "Outer Pad", 4.0, minimum=0.0, maximum=200.0, suffix=" um"),
        ParameterSpec("outer_chamfer_type", "Outer Chamfer Type", "Tout", "Outer Pad", 1, kind="choice", choices=[("none", 0), ("straight", 1), ("round", 2)]),
        ParameterSpec("outer_corner_pts", "Outer Corner Pts", "Pout", "Outer Pad", 4, kind="int", minimum=2, maximum=64),
        ParameterSpec("fanout_type", "Fanout Type", "Type", "Lead", 0, kind="choice", choices=[("trapezoidal", 0), ("lead_right_angle", 1), ("lead_straight_chamfer", 2), ("lead_round_chamfer", 3)]),
        ParameterSpec("lead_line_width", "Lead Width", "Wlead", "Lead", 3.0, minimum=0.1, maximum=500.0, suffix=" um"),
        ParameterSpec("lead_corner_type", "Lead Corner", "Clead", "Lead", 0, kind="choice", choices=[("right_angle", 0), ("straight_chamfer", 1), ("round_chamfer", 2)]),
        ParameterSpec("lead_chamfer_size", "Lead Chamfer", "Slead", "Lead", 10.0, minimum=0.0, maximum=500.0, suffix=" um"),
        ParameterSpec("inner_edge", "Inner Edge", "Ein", "Lead", "", kind="choice", choices=[("(auto)", ""), ("U", "U"), ("D", "D"), ("L", "L"), ("R", "R")]),
        ParameterSpec("outer_edge", "Outer Edge", "Eout", "Lead", "", kind="choice", choices=[("(auto)", ""), ("U", "U"), ("D", "D"), ("L", "L"), ("R", "R")]),
        ParameterSpec("layer_spec", "Layer", "L", "Layer", (8, 0), kind="layer_choice"),
    ],
)


DIGITAL_TOOL = ToolSpec(
    key="digital",
    title="Digital Text",
    library_name="NanoDeviceLib",
    pcell_name="DigitalPCell",
    preview_renderer=render_digital_text,
    preview_layers=[("labels", "Text")],
    insert_params_builder=_layer_insert_params("layer_spec"),
    params=[
        ParameterSpec("text", "Text", "Txt", "Content", "NANO DEVICE", kind="string"),
        ParameterSpec("x", "Center X", "Cx", "Placement", 0.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("y", "Center Y", "Cy", "Placement", 0.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("size", "Size", "S", "Style", 10.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("stroke_width", "Stroke Width", "W", "Style", 5.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("spacing", "Char Spacing", "Sp", "Style", 17.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("layer_spec", "Layer", "L", "Layer", (10, 0), kind="layer_choice"),
    ],
)


MARK_TOOL = ToolSpec(
    key="mark",
    title="Mark",
    library_name="NanoDeviceLib",
    pcell_name="MarkPCell",
    preview_renderer=render_mark,
    preview_layers=[("mark", "Mark")],
    insert_params_builder=_layer_insert_params("layer_spec"),
    params=[
        ParameterSpec(
            "shape",
            "Shape",
            "Sh",
            "Mark",
            "cross",
            kind="choice",
            choices=[
                ("cross", "cross"),
                ("square", "square"),
                ("circle", "circle"),
                ("diamond", "diamond"),
                ("triangle_up", "triangle_up"),
                ("triangle_down", "triangle_down"),
                ("L", "L"),
                ("T", "T"),
                ("semi_cross", "semi_cross"),
                ("cross_pos", "cross_pos"),
                ("cross_neg", "cross_neg"),
                ("l_shape", "l_shape"),
                ("t_shape", "t_shape"),
                ("sq_missing", "sq_missing"),
                ("sq_missing_border", "sq_missing_border"),
                ("cross_tri", "cross_tri"),
                ("sq_missing_rotborder", "sq_missing_rotborder"),
                ("sq_missing_diff_rotborder", "sq_missing_diff_rotborder"),
                ("regular_polygon", "regular_polygon"),
                ("chamfered_octagon", "chamfered_octagon"),
            ],
        ),
        ParameterSpec("x", "Center X", "Cx", "Placement", 0.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("y", "Center Y", "Cy", "Placement", 0.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("size", "Size", "S", "Geometry", 10.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("width", "Line Width", "W", "Geometry", 1.0, minimum=0.1, maximum=500.0, suffix=" um"),
        ParameterSpec("rotation", "Rotation", "Rot", "Geometry", 0.0, minimum=-360.0, maximum=360.0, suffix=" deg"),
        ParameterSpec("parameter1", "Parameter 1", "P1", "Advanced", 0.1, minimum=-1000.0, maximum=1000.0),
        ParameterSpec("parameter2", "Parameter 2", "P2", "Advanced", 0.0, minimum=-1000.0, maximum=1000.0),
        ParameterSpec("parameter3", "Parameter 3", "P3", "Advanced", 0.0, minimum=-1000.0, maximum=1000.0),
        ParameterSpec("layer_spec", "Layer", "L", "Layer", (10, 0), kind="layer_choice"),
    ],
)


NANODEVICE_CLASSIC_FET_TOOL = ToolSpec(
    key="nanodevice_classic_fet",
    title="Interdigitated FET (Original NanoDevice)",
    library_name="NanoDeviceLib",
    pcell_name="NanoDeviceClassicFETPCell",
    preview_renderer=render_nanodevice_classic_fet,
    preview_layers=[("channel", "Channel"), ("source_drain", "Source / Drain"), ("top_gate", "Gate")],
    insert_params_builder=_nanodevice_classic_fet_insert_params,
    params=[
        ParameterSpec("device_cx", "Center X", "Cx", "Placement", 0.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("device_cy", "Center Y", "Cy", "Placement", 0.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("active_width", "Active Width", "Wa", "Active", 80.0, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("active_height", "Active Height", "Ha", "Active", 60.0, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("channel_gap", "Channel Gap", "Gch", "Active", 4.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("finger_width", "Finger Width", "Wf", "Finger", 2.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("finger_spacing", "Finger Spacing", "Sf", "Finger", 2.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("finger_count", "Finger Count", "Nf", "Finger", 10, kind="int", minimum=1, maximum=500),
        ParameterSpec("finger_head_length", "Finger Head Length", "Lh", "Finger", 3.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("finger_head_overhang", "Head Overhang", "Oh", "Finger", 0.5, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("sd_bus_width", "Inner Bus Width", "Wbus", "Source / Drain", 8.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("outer_bus_width", "Outer Lead Width", "Wout", "Source / Drain", 12.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("source_pad_width", "Source Pad Width", "Wsp", "Source Pad", 60.0, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("source_pad_height", "Source Pad Height", "Hsp", "Source Pad", 60.0, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("source_pad_cx", "Source Pad X", "Xsp", "Source Pad", -120.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("source_pad_cy", "Source Pad Y", "Ysp", "Source Pad", 0.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("drain_pad_width", "Drain Pad Width", "Wdp", "Drain Pad", 60.0, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("drain_pad_height", "Drain Pad Height", "Hdp", "Drain Pad", 60.0, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("drain_pad_cx", "Drain Pad X", "Xdp", "Drain Pad", 120.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("drain_pad_cy", "Drain Pad Y", "Ydp", "Drain Pad", 0.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("gate_mode", "Gate Mode", "Gm", "Gate", 0, kind="choice", choices=[("global", 0), ("channel_only", 1)]),
        ParameterSpec("gate_x_offset", "Gate X Offset", "dGx", "Gate", 0.0, minimum=-1000.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("gate_y_offset", "Gate Y Offset", "dGy", "Gate", 0.0, minimum=-1000.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("gate_enclosure_x", "Gate Enclosure X", "Ex", "Gate", 0.0, minimum=-1000.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("gate_enclosure_y", "Gate Enclosure Y", "Ey", "Gate", 0.0, minimum=-1000.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("gate_lead_width", "Gate Lead Width", "Wg", "Gate", 10.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("gate_pad_width", "Gate Pad Width", "Wgp", "Gate Pad", 50.0, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("gate_pad_height", "Gate Pad Height", "Hgp", "Gate Pad", 50.0, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("gate_pad_cx", "Gate Pad X", "Xgp", "Gate Pad", 0.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("gate_pad_cy", "Gate Pad Y", "Ygp", "Gate Pad", 110.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("sd_layer_spec", "S/D Layer", "Ls", "Layer", (16, 0), kind="layer_choice"),
        ParameterSpec("gate_layer_spec", "Gate Layer", "Lg", "Layer", (18, 0), kind="layer_choice"),
    ],
)


def _next_cell_name(layout, base_name):
    existing = set()
    for i in range(layout.cells()):
        try:
            cell = layout.cell(i)
        except Exception:
            continue
        if cell is not None:
            existing.add(cell.name)
    if base_name not in existing:
        return base_name
    index = 1
    while f"{base_name}_{index}" in existing:
        index += 1
    return f"{base_name}_{index}"


def _normalize_mark_rotation_value(value, default=0):
    try:
        rotation = int(value)
    except Exception:
        rotation = int(default)
    if rotation in (0, 1, 2, 3):
        return rotation
    return int(round(rotation / 90.0)) % 4


def _insert_mosfet_component(layout, top_cell, values):
    from components.mosfet import MOSFET

    device = MOSFET(
        x=values["x"],
        y=values["y"],
        channel_width=values["channel_width"],
        channel_length=values["channel_length"],
        gate_overlap=values["gate_overlap"],
        channel_type=values["channel_type"],
        fanout_enabled=values["fanout_enabled"],
        fanout_direction=values["fanout_direction"],
        enable_bottom_gate=values["enable_bottom_gate"],
        enable_top_gate=values["enable_top_gate"],
        enable_source_drain=values["enable_source_drain"],
        show_device_labels=values["show_device_labels"],
        show_parameter_labels=values["show_parameter_labels"],
        show_alignment_marks=values["show_alignment_marks"],
        device_label=values["device_label"],
        mark_type_1=values["mark_type_1"],
        mark_type_2=values["mark_type_2"],
        mark_type_3=values["mark_type_3"],
        mark_type_4=values["mark_type_4"],
        mark_rotation_1=_normalize_mark_rotation_value(values["mark_rotation_1"], 0),
        mark_rotation_2=_normalize_mark_rotation_value(values["mark_rotation_2"], 0),
        mark_rotation_3=_normalize_mark_rotation_value(values["mark_rotation_3"], 2),
        mark_rotation_4=_normalize_mark_rotation_value(values["mark_rotation_4"], 3),
        outer_pad_size=values["outer_pad_size"],
        chamfer_size=values["chamfer_size"],
        channel_extension_ratio=values["channel_extension_ratio"],
        dielectric_extension_ratio=values["dielectric_extension_ratio"],
        dielectric_margin=values["dielectric_margin"],
        source_drain_inner_width_ratio=values["source_drain_inner_width_ratio"],
        source_drain_outer_offset_x=values["source_drain_outer_offset_x"],
        source_drain_outer_offset_y=values["source_drain_outer_offset_y"],
        source_drain_inner_chamfer=values["source_drain_inner_chamfer"],
        source_drain_outer_chamfer=values["source_drain_outer_chamfer"],
        bottom_gate_inner_width_ratio=values["bottom_gate_inner_width_ratio"],
        bottom_gate_outer_offset_x=values["bottom_gate_outer_offset_x"],
        bottom_gate_outer_offset_y=values["bottom_gate_outer_offset_y"],
        bottom_gate_inner_chamfer=values["bottom_gate_inner_chamfer"],
        bottom_gate_outer_chamfer=values["bottom_gate_outer_chamfer"],
        top_gate_inner_width_ratio=values["top_gate_inner_width_ratio"],
        top_gate_outer_offset_x=values["top_gate_outer_offset_x"],
        top_gate_outer_offset_y=values["top_gate_outer_offset_y"],
        top_gate_inner_chamfer=values["top_gate_inner_chamfer"],
        top_gate_outer_chamfer=values["top_gate_outer_chamfer"],
        device_region_margin_x=values["device_region_margin_x"],
        device_region_margin_y=values["device_region_margin_y"],
        mark_size=values["mark_size"],
        mark_width=values["mark_width"],
        label_size=values["label_size"],
        label_offset_x=values["label_offset_x"],
        label_offset_y=values["label_offset_y"],
    )
    device.generate()
    cell = layout.create_cell(_next_cell_name(layout, values["cell_name"]))

    layer_map = {name: layout.layer(layer_id, 0) for name, layer_id in device.get_layer_ids().items()}
    for name, shapes in device.shapes.items():
        for shape in shapes:
            cell.shapes(layer_map[name]).insert(shape)
    for name, shapes in device.get_all_shapes().items():
        for shape in shapes:
            cell.shapes(layer_map[name]).insert(shape)
    top_cell.insert(pya.CellInstArray(cell.cell_index(), pya.Trans()))


def _insert_fet_component(layout, top_cell, values):
    from components.fet import FET

    params = dict(values)
    x = params.pop("x")
    y = params.pop("y")
    cell_name = params.pop("cell_name")
    label_type = params.pop("label_type")
    device = FET(layout=layout, **params)
    cell = device.create_single_device(_next_cell_name(layout, cell_name), x, y, label_type=label_type)
    top_cell.insert(pya.CellInstArray(cell.cell_index(), pya.Trans()))


def _insert_hall_component(layout, top_cell, values):
    from components.hallbar import HallBar

    params = _normalize_hall_component_params(values)
    x = params.pop("x")
    y = params.pop("y")
    cell_name = params.pop("cell_name")
    label_text = params.pop("label_text")
    show_param_label = params.pop("show_param_label")
    device = HallBar(layout=layout, **params)
    cell = device.create_single_device(_next_cell_name(layout, cell_name), x, y, label_text, show_param_label)
    top_cell.insert(pya.CellInstArray(cell.cell_index(), pya.Trans()))


def _normalize_hall_component_params(values):
    params = dict(values)
    params["mark_types"] = [
        params.pop("mark_type_1", "sq_missing"),
        params.pop("mark_type_2", "L_shape"),
        params.pop("mark_type_3", "L_shape"),
        params.pop("mark_type_4", "cross"),
    ]
    params["mark_rotations"] = [
        _normalize_mark_rotation_value(params.pop("mark_rotation_1", 0), 0),
        _normalize_mark_rotation_value(params.pop("mark_rotation_2", 0), 0),
        _normalize_mark_rotation_value(params.pop("mark_rotation_3", 2), 2),
        _normalize_mark_rotation_value(params.pop("mark_rotation_4", 1), 1),
    ]
    if params.get("i_inner_width", 0.0) <= 0.0:
        params["i_inner_width"] = None
    if params.get("v_inner_length", 0.0) <= 0.0:
        params["v_inner_length"] = None
    return params


def _normalize_tlm_component_params(values):
    params = dict(values)
    if params.get("inner_pad_width") == 0:
        params["inner_pad_width"] = None
    if params.get("outer_pad_spacing") == 0:
        params["outer_pad_spacing"] = None
    if params.get("channel_length") == 0:
        params["channel_length"] = None

    params["mark_types"] = [
        params.pop("mark_type_1", "sq_missing"),
        params.pop("mark_type_2", "L_shape"),
        params.pop("mark_type_3", "L_shape"),
        params.pop("mark_type_4", "cross"),
    ]
    params["mark_rotations"] = [
        _normalize_mark_rotation_value(params.pop("mark_rotation_1", 0), 0),
        _normalize_mark_rotation_value(params.pop("mark_rotation_2", 0), 0),
        _normalize_mark_rotation_value(params.pop("mark_rotation_3", 2), 2),
        _normalize_mark_rotation_value(params.pop("mark_rotation_4", 1), 1),
    ]
    return params


def _insert_tlm_component(layout, top_cell, values):
    from components.tlm import TLM

    params = dict(values)
    x = params.pop("x")
    y = params.pop("y")
    cell_name = params.pop("cell_name")
    device = TLM(layout=layout, **params)
    cell = device.create_single_device(_next_cell_name(layout, cell_name), x, y)
    top_cell.insert(pya.CellInstArray(cell.cell_index(), pya.Trans()))


def _insert_meander_component(layout, top_cell, values):
    from components.meander import Meander

    params = dict(values)
    x = params.pop("x")
    y = params.pop("y")
    cell_name = params.pop("cell_name")
    device = Meander(layout=layout, **params)
    cell = layout.create_cell(_next_cell_name(layout, cell_name))
    device.create_serpentine_channel(cell, x, y)
    top_cell.insert(pya.CellInstArray(cell.cell_index(), pya.Trans()))


def _insert_sense_latch_array_component(layout, top_cell, values):
    from components.sense_latch_array import SenseLatchArray

    params = dict(values)
    cell_name = params.pop("cell_name")
    params.pop("array_type", None)
    device = SenseLatchArray(layout=layout, **params)
    cell = device.create_array_cell(_next_cell_name(layout, cell_name))
    top_cell.insert(pya.CellInstArray(cell.cell_index(), pya.Trans()))


def _insert_write_read_array_component(layout, top_cell, values):
    from components.write_read_array import WriteReadArray

    params = dict(values)
    cell_name = params.pop("cell_name")
    device = WriteReadArray(layout=layout, **params)
    cell = device.create_array_cell(_next_cell_name(layout, cell_name))
    top_cell.insert(pya.CellInstArray(cell.cell_index(), pya.Trans()))


def _fet_preview_geometry(values):
    x = values["x"]
    y = values["y"]
    ch_box = _center_box(x, y, values["ch_len"] * 3.0, values["ch_width"])
    bg_left = _center_box(
        x - values["gate_space"] / 2.0 - values["gate_width"] / 2.0,
        y,
        values["gate_width"],
        values["ch_width"] * values["bottom_gate_inner_width_ratio"],
    )
    bg_right = _center_box(
        x + values["gate_space"] / 2.0 + values["gate_width"] / 2.0,
        y,
        values["gate_width"],
        values["ch_width"] * values["bottom_gate_inner_width_ratio"],
    )
    sd_left = _center_box(x - values["ch_len"], y, values["ch_len"], values["ch_width"] * values["source_drain_inner_width_ratio"])
    sd_right = _center_box(x + values["ch_len"], y, values["ch_len"], values["ch_width"] * values["source_drain_inner_width_ratio"])
    tg = _center_box(
        x,
        y,
        values["ch_len"] * values["top_gate_inner_width_ratio"],
        values["ch_width"] * values["top_gate_inner_width_ratio"],
    )
    outer = [
        _center_box(x - values["bottom_gate_outer_offset_x"] - values["gate_space"] / 2.0, y + values["bottom_gate_outer_offset_y"], values["outer_pad_size"], values["outer_pad_size"]),
        _center_box(x + values["bottom_gate_outer_offset_x"] + values["gate_space"] / 2.0, y + values["bottom_gate_outer_offset_y"], values["outer_pad_size"], values["outer_pad_size"]),
        _center_box(x - values["ch_len"] / 2.0 - values["source_drain_outer_offset_x"], y + values["source_drain_outer_offset_y"], values["outer_pad_size"], values["outer_pad_size"]),
        _center_box(x + values["ch_len"] / 2.0 + values["source_drain_outer_offset_x"], y + values["source_drain_outer_offset_y"], values["outer_pad_size"], values["outer_pad_size"]),
        _center_box(x + values["top_gate_outer_offset_x"], y + values["top_gate_outer_offset_y"], values["outer_pad_size"], values["outer_pad_size"]),
    ]
    return {
        "channel": [ch_box],
        "electrodes": [bg_left, bg_right, sd_left, sd_right, tg] + outer,
    }


def render_fet_component(scene, values, visible_layers=None):
    visible_layers = visible_layers or {"channel": True, "electrodes": True}
    geometry = _fet_preview_geometry(values)
    if visible_layers.get("channel", True):
        _draw_path(scene, _boxes_to_path(geometry["channel"]), QPen(QColor("#f4d35e"), 0), QBrush(QColor(244, 211, 94, 70)))
    if visible_layers.get("electrodes", True):
        _draw_path(scene, _boxes_to_path(geometry["electrodes"]), QPen(QColor("#ee6c4d"), 0), QBrush(QColor(238, 108, 77, 90)))


def render_hall_component(scene, values, visible_layers=None):
    from components.hallbar import HallBar

    visible_layers = visible_layers or {}
    params = _normalize_hall_component_params(values)
    params.pop("cell_name", None)
    label_text = params.pop("label_text", "HallBar")
    show_param_label = params.pop("show_param_label", True)

    layout = pya.Layout()
    layout.dbu = DEFAULT_DBU
    device = HallBar(layout=layout, **params)
    cell = device.create_single_device("__HALL_PREVIEW__", params["x"], params["y"], label_text, show_param_label)
    cell.flatten(-1, True)
    layer_ids = device.get_layer_ids()

    buckets = {
        "channel": [layer_ids["channel"]],
        "source_drain": [layer_ids["source_drain"]],
        "labels": [layer_ids["labels"]],
        "alignment_marks": [layer_ids["alignment_marks"]],
        "parameter_labels": [layer_ids["parameter_labels"]],
    }

    for layer_key, layer_list in buckets.items():
        if not visible_layers.get(layer_key, True):
            continue
        style_layer_id = layer_list[0]
        pen, brush = _preview_style_for_layer_id(style_layer_id, layer_key)
        for layer_id in layer_list:
            layer_index = layout.layer(layer_id, 0)
            for shape in cell.shapes(layer_index).each():
                for path in _shape_to_paths(shape, layout.dbu):
                    _draw_path(scene, path, pen, brush)


def _tlm_positions(values):
    n = max(int(values["num_electrodes"]), 3)
    min_spacing = values["min_spacing"]
    max_spacing = values["max_spacing"]
    pad_length = values["inner_pad_length"]
    if values["distribution"] == "log" and min_spacing > 0 and max_spacing > 0:
        edge_spacings = [min_spacing * (max_spacing / min_spacing) ** (i / (n - 2)) for i in range(n - 1)]
    else:
        edge_spacings = [min_spacing + (max_spacing - min_spacing) * i / (n - 2) for i in range(n - 1)]
    spacings = [s + pad_length for s in edge_spacings]
    xs = [0.0]
    for spacing in spacings:
        xs.append(xs[-1] + spacing)
    shift = (xs[0] + xs[-1]) / 2.0
    return [value - shift for value in xs]


def render_tlm_component(scene, values, visible_layers=None):
    from components.tlm import TLM

    visible_layers = visible_layers or {}
    params = _normalize_tlm_component_params(values)
    params.pop("cell_name", None)

    layout = pya.Layout()
    layout.dbu = DEFAULT_DBU
    device = TLM(layout=layout, **params)
    cell = device.create_single_device("__TLM_PREVIEW__", params["x"], params["y"])
    layer_ids = device.get_layer_ids()

    buckets = {
        "channel": [layer_ids["channel"]],
        "source_drain": [layer_ids["source_drain"]],
        "labels": [layer_ids["labels"]],
        "alignment_marks": [layer_ids["alignment_marks"]],
        "parameter_labels": [layer_ids["parameter_labels"]],
    }

    for layer_key, layer_list in buckets.items():
        if not visible_layers.get(layer_key, True):
            continue
        style_layer_id = layer_list[0]
        pen, brush = _preview_style_for_layer_id(style_layer_id, layer_key)
        for layer_id in layer_list:
            layer_index = layout.layer(layer_id, 0)
            for preview_cell in _iter_cells_recursive(layout, cell):
                for shape in preview_cell.shapes(layer_index).each():
                    for path in _shape_to_paths(shape, layout.dbu):
                        _draw_path(scene, path, pen, brush)


def render_meander_component(scene, values, visible_layers=None):
    visible_layers = visible_layers or {"channel": True}
    if not visible_layers.get("channel", True):
        return
    x = values["x"]
    y = values["y"]
    width = values["region_width"]
    height = values["region_height"]
    line_width = max(values["line_width"], 0.2)
    spacing = max(values["line_spacing"], 0.2)
    left = x - width / 2.0 + values["margin"]
    right = x + width / 2.0 - values["margin"]
    bottom = y - height / 2.0 + values["margin"]
    top = y + height / 2.0 - values["margin"]
    step = max(line_width + spacing, line_width)
    boxes = []
    y_cursor = bottom
    direction = 1
    while y_cursor + line_width <= top:
        if direction > 0:
            boxes.append(_xy_box(left, y_cursor, right, y_cursor + line_width))
        else:
            boxes.append(_xy_box(right, y_cursor, left, y_cursor + line_width))
        next_y = y_cursor + step
        if next_y + line_width <= top:
            x_col = right - line_width if direction > 0 else left
            boxes.append(_xy_box(x_col, y_cursor + line_width, x_col + line_width, next_y))
        y_cursor = next_y
        direction *= -1
    _draw_path(scene, _boxes_to_path(boxes), QPen(QColor("#4cc9f0"), 0), QBrush(QColor(76, 201, 240, 85)))


def render_sense_latch_array(scene, values, visible_layers=None):
    from components.sense_latch_array import SenseLatchArray

    visible_layers = visible_layers or {}
    params = dict(values)
    params.pop("cell_name", None)
    params.pop("array_type", None)

    layout = pya.Layout()
    layout.dbu = DEFAULT_DBU
    device = SenseLatchArray(layout=layout, **params)
    cell = device.create_array_cell("__SENSE_LATCH_ARRAY_PREVIEW__")

    layer_specs = [
        ("channel", "channel", QPen(QColor("#7cb342"), 0), QBrush(QColor(124, 179, 66, 90))),
        ("contact", "contact", QPen(QColor("#ef6c00"), 0), QBrush(QColor(239, 108, 0, 110))),
        ("bottom_gate", "bottom_gate", QPen(QColor("#2196f3"), 0), QBrush(QColor(33, 150, 243, 95))),
        ("top_dielectric", "top_dielectric", QPen(QColor("#ab47bc"), 0), QBrush(QColor(171, 71, 188, 55))),
        ("pad", "pad", QPen(QColor("#ffb300"), 0), QBrush(QColor(255, 179, 0, 85))),
        ("note", "note", QPen(QColor("#bdbdbd"), 0), QBrush(QColor(0, 0, 0, 0))),
    ]

    for layer_key, component_layer_key, pen, brush in layer_specs:
        if not visible_layers.get(layer_key, True):
            continue
        layer_index = device.layers[component_layer_key]
        for shape in cell.shapes(layer_index).each():
            for path in _shape_to_paths(shape, layout.dbu):
                _draw_path(scene, path, pen, brush)


def render_write_read_array(scene, values, visible_layers=None):
    from components.write_read_array import WriteReadArray

    visible_layers = visible_layers or {}
    params = dict(values)
    params.pop("cell_name", None)

    layout = pya.Layout()
    layout.dbu = DEFAULT_DBU
    device = WriteReadArray(layout=layout, **params)
    cell = device.create_array_cell("__WRITE_READ_ARRAY_PREVIEW__")

    layer_specs = [
        ("channel", "channel", QPen(QColor("#7cb342"), 0), QBrush(QColor(124, 179, 66, 90))),
        ("contact", "contact", QPen(QColor("#ef6c00"), 0), QBrush(QColor(239, 108, 0, 110))),
        ("bottom_gate", "bottom_gate", QPen(QColor("#2196f3"), 0), QBrush(QColor(33, 150, 243, 95))),
        ("bottom_dielectric", "bottom_dielectric", QPen(QColor("#8e24aa"), 0), QBrush(QColor(142, 36, 170, 70))),
        ("top_dielectric", "top_dielectric", QPen(QColor("#ab47bc"), 0), QBrush(QColor(171, 71, 188, 55))),
        ("pad", "pad", QPen(QColor("#ffb300"), 0), QBrush(QColor(255, 179, 0, 85))),
        ("note", "note", QPen(QColor("#bdbdbd"), 0), QBrush(QColor(0, 0, 0, 0))),
    ]

    for layer_key, component_layer_key, pen, brush in layer_specs:
        if not visible_layers.get(layer_key, True):
            continue
        layer_index = device.layers[component_layer_key]
        for shape in cell.shapes(layer_index).each():
            for path in _shape_to_paths(shape, layout.dbu):
                _draw_path(scene, path, pen, brush)


def render_mosfet_component(scene, values, visible_layers=None):
    from components.mosfet import MOSFET

    visible_layers = visible_layers or {}
    params = dict(values)
    params.pop("cell_name", None)
    device = MOSFET(**params)
    device.generate()
    layer_ids = device.get_layer_ids()

    buckets = {
        "channel": list(device.shapes.get("channel", [])),
        "bottom_dielectric": list(device.shapes.get("bottom_dielectric", [])),
        "top_dielectric": list(device.shapes.get("top_dielectric", [])),
        "bottom_gate": list(device.get_all_shapes().get("bottom_gate", [])),
        "source_drain": list(device.get_all_shapes().get("source", [])) + list(device.get_all_shapes().get("drain", [])),
        "top_gate": list(device.get_all_shapes().get("top_gate", [])),
        "labels": list(device.shapes.get("device_label", [])),
        "parameter_labels": list(device.shapes.get("parameter_labels", [])),
        "alignment_marks": list(device.shapes.get("alignment_marks", [])),
    }

    for layer_key, shapes in buckets.items():
        if not visible_layers.get(layer_key, True):
            continue
        if layer_key == "source_drain":
            style_layer_id = layer_ids.get("source", layer_ids.get("drain"))
        elif layer_key == "labels":
            style_layer_id = layer_ids.get("device_label")
        elif layer_key == "parameter_labels":
            style_layer_id = layer_ids.get("parameter_labels")
        elif layer_key == "alignment_marks":
            style_layer_id = layer_ids.get("alignment_marks")
        else:
            style_layer_id = layer_ids.get(layer_key)
        pen, brush = _preview_style_for_layer_id(style_layer_id, layer_key)
        for shape in shapes:
            for path in _geometry_to_paths(shape):
                _draw_path(scene, path, pen, brush)


MOSFET_COMPONENT_TOOL = ToolSpec(
    key="mosfet_component",
    title="MOSFET",
    library_name="",
    pcell_name="",
    preview_renderer=render_mosfet_component,
    preview_layers=[
        ("channel", "Channel"),
        ("bottom_dielectric", "Bottom Dielectric"),
        ("top_dielectric", "Dielectric"),
        ("bottom_gate", "Bottom Gate"),
        ("source_drain", "Source / Drain"),
        ("top_gate", "Top Gate"),
        ("labels", "Labels"),
        ("parameter_labels", "Notes"),
        ("alignment_marks", "Marks"),
    ],
    insert_handler=_insert_mosfet_component,
    params=[
        ParameterSpec("cell_name", "Cell Name", "Cell", "Placement", "MOSFET_Device", kind="string"),
        ParameterSpec("x", "Center X", "Cx", "Placement", 0.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("y", "Center Y", "Cy", "Placement", 0.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("channel_width", "Channel Width", "W", "Geometry", 20.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("channel_length", "Channel Length", "L", "Geometry", 5.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("gate_overlap", "Gate Overlap", "Ov", "Geometry", 2.0, minimum=0.1, maximum=500.0, suffix=" um"),
        ParameterSpec("channel_type", "Channel Type", "Type", "Geometry", "n", kind="choice", choices=[("p", "p"), ("n", "n")]),
        ParameterSpec("outer_pad_size", "Outer Pad", "Pad", "Geometry", 60.0, minimum=1.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("chamfer_size", "Chamfer", "Cham", "Geometry", 10.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("channel_extension_ratio", "Channel Ext", "ChEx", "Geometry", 4.0, minimum=0.1, maximum=20.0),
        ParameterSpec("dielectric_extension_ratio", "Dielectric Ext", "DiEx", "Geometry", 1.0, minimum=0.1, maximum=20.0),
        ParameterSpec("dielectric_margin", "Dielectric Margin", "DiMg", "Geometry", 25.0, minimum=0.0, maximum=500.0, suffix=" um"),
        ParameterSpec("device_label", "Device Label", "Lbl", "Labels", "D1", kind="string"),
        ParameterSpec("label_size", "Label Size", "LS", "Labels", 20.0, minimum=1.0, maximum=200.0, suffix=" um"),
        ParameterSpec("label_offset_x", "Label Offset X", "LOx", "Labels", -6.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("label_offset_y", "Label Offset Y", "LOy", "Labels", -13.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("mark_type_1", "Mark 1", "M1", "Marks", "sq_missing", kind="choice", choices=[("double_square", "double_square"), ("square", "square"), ("diamond", "diamond"), ("triangle", "triangle"), ("cross", "cross"), ("circle", "circle"), ("L_shape", "L_shape"), ("T_shape", "T_shape"), ("sq_missing", "sq_missing"), ("cross_tri", "cross_tri")]),
        ParameterSpec("mark_type_2", "Mark 2", "M2", "Marks", "L_shape", kind="choice", choices=[("double_square", "double_square"), ("square", "square"), ("diamond", "diamond"), ("triangle", "triangle"), ("cross", "cross"), ("circle", "circle"), ("L_shape", "L_shape"), ("T_shape", "T_shape"), ("sq_missing", "sq_missing"), ("cross_tri", "cross_tri")]),
        ParameterSpec("mark_type_3", "Mark 3", "M3", "Marks", "L_shape", kind="choice", choices=[("double_square", "double_square"), ("square", "square"), ("diamond", "diamond"), ("triangle", "triangle"), ("cross", "cross"), ("circle", "circle"), ("L_shape", "L_shape"), ("T_shape", "T_shape"), ("sq_missing", "sq_missing"), ("cross_tri", "cross_tri")]),
        ParameterSpec("mark_type_4", "Mark 4", "M4", "Marks", "L_shape", kind="choice", choices=[("double_square", "double_square"), ("square", "square"), ("diamond", "diamond"), ("triangle", "triangle"), ("cross", "cross"), ("circle", "circle"), ("L_shape", "L_shape"), ("T_shape", "T_shape"), ("sq_missing", "sq_missing"), ("cross_tri", "cross_tri")]),
        ParameterSpec("mark_rotation_1", "Rot 1", "R1", "Marks", 0, kind="int", minimum=0, maximum=3),
        ParameterSpec("mark_rotation_2", "Rot 2", "R2", "Marks", 0, kind="int", minimum=0, maximum=3),
        ParameterSpec("mark_rotation_3", "Rot 3", "R3", "Marks", 2, kind="int", minimum=0, maximum=3),
        ParameterSpec("mark_rotation_4", "Rot 4", "R4", "Marks", 3, kind="int", minimum=0, maximum=3),
        ParameterSpec("mark_size", "Mark Size", "MS", "Marks", 20.0, minimum=1.0, maximum=500.0, suffix=" um"),
        ParameterSpec("mark_width", "Mark Width", "MW", "Marks", 5.0, minimum=0.1, maximum=100.0, suffix=" um"),
        ParameterSpec("device_region_margin_x", "Region Margin X", "RMx", "Marks", 0.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("device_region_margin_y", "Region Margin Y", "RMy", "Marks", 0.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("source_drain_inner_width_ratio", "SD Width Ratio", "SDWr", "Source / Drain", 1.2, minimum=0.1, maximum=20.0),
        ParameterSpec("source_drain_outer_offset_x", "SD Outer X", "SDOx", "Source / Drain", 50.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("source_drain_outer_offset_y", "SD Outer Y", "SDOy", "Source / Drain", 0.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("source_drain_inner_chamfer", "SD Inner Chamfer", "SDIc", "Source / Drain", "none", kind="choice", choices=[("none", "none"), ("straight", "straight"), ("round", "round")]),
        ParameterSpec("source_drain_outer_chamfer", "SD Outer Chamfer", "SDOc", "Source / Drain", "straight", kind="choice", choices=[("none", "none"), ("straight", "straight"), ("round", "round")]),
        ParameterSpec("bottom_gate_inner_width_ratio", "BG Width Ratio", "BGWr", "Bottom Gate", 1.5, minimum=0.1, maximum=20.0),
        ParameterSpec("bottom_gate_outer_offset_x", "BG Outer X", "BGOx", "Bottom Gate", 0.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("bottom_gate_outer_offset_y", "BG Outer Y", "BGOy", "Bottom Gate", -55.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("bottom_gate_inner_chamfer", "BG Inner Chamfer", "BGIc", "Bottom Gate", "none", kind="choice", choices=[("none", "none"), ("straight", "straight"), ("round", "round")]),
        ParameterSpec("bottom_gate_outer_chamfer", "BG Outer Chamfer", "BGOc", "Bottom Gate", "straight", kind="choice", choices=[("none", "none"), ("straight", "straight"), ("round", "round")]),
        ParameterSpec("top_gate_inner_width_ratio", "TG Width Ratio", "TGWr", "Top Gate", 1.5, minimum=0.1, maximum=20.0),
        ParameterSpec("top_gate_outer_offset_x", "TG Outer X", "TGOx", "Top Gate", 0.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("top_gate_outer_offset_y", "TG Outer Y", "TGOy", "Top Gate", 55.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("top_gate_inner_chamfer", "TG Inner Chamfer", "TGIc", "Top Gate", "none", kind="choice", choices=[("none", "none"), ("straight", "straight"), ("round", "round")]),
        ParameterSpec("top_gate_outer_chamfer", "TG Outer Chamfer", "TGOc", "Top Gate", "straight", kind="choice", choices=[("none", "none"), ("straight", "straight"), ("round", "round")]),
        ParameterSpec("fanout_enabled", "Enable Fanout", "Fan", "Options", 1, kind="choice", choices=[("true", True), ("false", False)]),
        ParameterSpec("fanout_direction", "Fanout Direction", "Dir", "Options", "horizontal", kind="choice", choices=[("horizontal", "horizontal"), ("vertical", "vertical")]),
        ParameterSpec("enable_bottom_gate", "Bottom Gate", "BG", "Options", 1, kind="choice", choices=[("true", True), ("false", False)]),
        ParameterSpec("enable_top_gate", "Top Gate", "TG", "Options", 1, kind="choice", choices=[("true", True), ("false", False)]),
        ParameterSpec("enable_source_drain", "Source/Drain", "SD", "Options", 1, kind="choice", choices=[("true", True), ("false", False)]),
        ParameterSpec("show_device_labels", "Show Device Label", "DL", "Options", 1, kind="choice", choices=[("true", True), ("false", False)]),
        ParameterSpec("show_parameter_labels", "Show Param Label", "PL", "Options", 0, kind="choice", choices=[("true", True), ("false", False)]),
        ParameterSpec("show_alignment_marks", "Show Marks", "Mk", "Options", 1, kind="choice", choices=[("true", True), ("false", False)]),
    ],
)


FET_COMPONENT_TOOL = ToolSpec(
    key="fet_component",
    title="FET",
    library_name="",
    pcell_name="",
    preview_renderer=render_fet_component,
    preview_layers=[
        ("bottom_gate", "Bottom Gate"),
        ("top_dielectric", "Dielectric"),
        ("channel", "Channel"),
        ("source_drain", "Source / Drain"),
        ("top_gate", "Top Gate"),
        ("labels", "Labels"),
        ("alignment_marks", "Marks"),
    ],
    insert_handler=_insert_fet_component,
    params=[
        ParameterSpec("cell_name", "Cell Name", "Cell", "Placement", "FET_Device", kind="string"),
        ParameterSpec("x", "Center X", "Cx", "Placement", 0.0, minimum=-10000.0, maximum=10000.0, suffix=" um"),
        ParameterSpec("y", "Center Y", "Cy", "Placement", 0.0, minimum=-10000.0, maximum=10000.0, suffix=" um"),
        ParameterSpec("ch_len", "Channel Length", "Lch", "Channel", 16.0, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("ch_width", "Channel Width", "Wch", "Channel", 5.0, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("gate_space", "Gate Space", "Gsp", "Channel", 20.0, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("gate_width", "Gate Width", "Wg", "Channel", 15.0, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("outer_pad_size", "Outer Pad Size", "Pad", "Pads", 100.0, minimum=1.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("bottom_gate_inner_width_ratio", "Bottom Gate Ratio", "BGR", "Pads", 1.5, minimum=0.1, maximum=10.0),
        ParameterSpec("source_drain_inner_width_ratio", "S/D Ratio", "SDR", "Pads", 1.2, minimum=0.1, maximum=10.0),
        ParameterSpec("top_gate_inner_width_ratio", "Top Gate Ratio", "TGR", "Pads", 1.2, minimum=0.1, maximum=10.0),
        ParameterSpec("bottom_gate_outer_offset_x", "Bottom Gate Offset X", "BGx", "Offsets", 50.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("bottom_gate_outer_offset_y", "Bottom Gate Offset Y", "BGy", "Offsets", -100.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("source_drain_outer_offset_x", "S/D Offset X", "SDx", "Offsets", 110.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("source_drain_outer_offset_y", "S/D Offset Y", "SDy", "Offsets", 20.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("top_gate_outer_offset_x", "Top Gate Offset X", "TGx", "Offsets", 0.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("top_gate_outer_offset_y", "Top Gate Offset Y", "TGy", "Offsets", 100.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("label_type", "Label Type", "Lbl", "Labels", "textutils", kind="choice", choices=[("textutils", "textutils"), ("digital", "digital")]),
    ],
)


HALL_COMPONENT_TOOL = ToolSpec(
    key="hall_component",
    title="Hall Bar",
    library_name="",
    pcell_name="",
    preview_renderer=render_hall_component,
    preview_layers=[("channel", "Channel"), ("source_drain", "Contacts"), ("labels", "Labels"), ("alignment_marks", "Marks"), ("parameter_labels", "Notes")],
    insert_handler=_insert_hall_component,
    params=[
        ParameterSpec("cell_name", "Cell Name", "Cell", "Placement", "HallBar_Device", kind="string"),
        ParameterSpec("x", "Center X", "Cx", "Placement", 0.0, minimum=-10000.0, maximum=10000.0, suffix=" um"),
        ParameterSpec("y", "Center Y", "Cy", "Placement", 0.0, minimum=-10000.0, maximum=10000.0, suffix=" um"),
        ParameterSpec("label_text", "Label Text", "Lbl", "Labels", "HB_D1", kind="string"),
        ParameterSpec("show_param_label", "Show Param Label", "PL", "Labels", 1, kind="choice", choices=[("true", True), ("false", False)]),
        ParameterSpec("label_size", "Label Size", "LS", "Labels", 20.0, minimum=1.0, maximum=500.0, suffix=" um"),
        ParameterSpec("label_anchor", "Label Anchor", "LA", "Labels", "left_top", kind="choice", choices=[("left_top", "left_top"), ("left_bottom", "left_bottom"), ("right_top", "right_top"), ("right_bottom", "right_bottom"), ("center", "center")]),
        ParameterSpec("label_offset_x", "Label Offset X", "LOx", "Labels", 5.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("label_offset_y", "Label Offset Y", "LOy", "Labels", -23.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("electrode_text_label", "Electrode Text", "ET", "Labels", 0, kind="choice", choices=[("true", True), ("false", False)]),
        ParameterSpec("bar_length", "Bar Length", "Lb", "Channel", 50.0, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("bar_width", "Bar Width", "Wb", "Channel", 20.0, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("v_protrude_width", "V Protrude Width", "VpW", "Channel", 5.0, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("v_protrude_length", "V Protrude Length", "VpL", "Channel", 5.0, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("dist_v", "V Distance", "Dv", "Channel", 15.5, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("device_margin_x", "Device Margin X", "DMx", "Marks", 170.0, minimum=0.0, maximum=10000.0, suffix=" um"),
        ParameterSpec("device_margin_y", "Device Margin Y", "DMy", "Marks", 140.0, minimum=0.0, maximum=10000.0, suffix=" um"),
        ParameterSpec("mark_size", "Mark Size", "MS", "Marks", 20.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("mark_width", "Mark Width", "MW", "Marks", 5.0, minimum=0.1, maximum=100.0, suffix=" um"),
        ParameterSpec("mark_type_1", "Mark 1", "M1", "Marks", "sq_missing", kind="choice", choices=[("double_square", "double_square"), ("square", "square"), ("diamond", "diamond"), ("triangle", "triangle"), ("cross", "cross"), ("circle", "circle"), ("L_shape", "L_shape"), ("T_shape", "T_shape"), ("sq_missing", "sq_missing"), ("cross_tri", "cross_tri")]),
        ParameterSpec("mark_type_2", "Mark 2", "M2", "Marks", "L_shape", kind="choice", choices=[("double_square", "double_square"), ("square", "square"), ("diamond", "diamond"), ("triangle", "triangle"), ("cross", "cross"), ("circle", "circle"), ("L_shape", "L_shape"), ("T_shape", "T_shape"), ("sq_missing", "sq_missing"), ("cross_tri", "cross_tri")]),
        ParameterSpec("mark_type_3", "Mark 3", "M3", "Marks", "L_shape", kind="choice", choices=[("double_square", "double_square"), ("square", "square"), ("diamond", "diamond"), ("triangle", "triangle"), ("cross", "cross"), ("circle", "circle"), ("L_shape", "L_shape"), ("T_shape", "T_shape"), ("sq_missing", "sq_missing"), ("cross_tri", "cross_tri")]),
        ParameterSpec("mark_type_4", "Mark 4", "M4", "Marks", "cross", kind="choice", choices=[("double_square", "double_square"), ("square", "square"), ("diamond", "diamond"), ("triangle", "triangle"), ("cross", "cross"), ("circle", "circle"), ("L_shape", "L_shape"), ("T_shape", "T_shape"), ("sq_missing", "sq_missing"), ("cross_tri", "cross_tri")]),
        ParameterSpec("mark_rotation_1", "Rot 1", "R1", "Marks", 0, kind="int", minimum=0, maximum=3),
        ParameterSpec("mark_rotation_2", "Rot 2", "R2", "Marks", 0, kind="int", minimum=0, maximum=3),
        ParameterSpec("mark_rotation_3", "Rot 3", "R3", "Marks", 2, kind="int", minimum=0, maximum=3),
        ParameterSpec("mark_rotation_4", "Rot 4", "R4", "Marks", 1, kind="int", minimum=0, maximum=3),
        ParameterSpec("i_inner_length", "I Inner Length", "IiL", "Current Contacts", 10.0, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("i_inner_width", "I Inner Width", "IiW", "Current Contacts", 0.0, minimum=0.0, maximum=5000.0, suffix=" um", tooltip="0 means auto from bar width"),
        ParameterSpec("i_outer_length", "I Pad Length", "IL", "Contacts", 80.0, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("i_outer_width", "I Pad Width", "IW", "Contacts", 80.0, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("i_outer_chamfer", "I Chamfer", "ICh", "Contacts", 10.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("i_outer_chamfer_type", "I Chamfer Type", "ICt", "Contacts", "straight", kind="choice", choices=[("none", "none"), ("straight", "straight"), ("round", "round")]),
        ParameterSpec("i_outer_offset_x", "I Offset X", "Ix", "Contacts", 110.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("i_outer_offset_y", "I Offset Y", "Iy", "Contacts", 0.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("v_inner_length", "V Inner Length", "ViL", "Voltage Contacts", 0.0, minimum=0.0, maximum=5000.0, suffix=" um", tooltip="0 means auto from protrude length"),
        ParameterSpec("v_inner_width", "V Inner Width", "ViW", "Voltage Contacts", 3.0, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("v_outer_length", "V Pad Length", "VL", "Contacts", 80.0, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("v_outer_width", "V Pad Width", "VW", "Contacts", 80.0, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("v_outer_chamfer", "V Chamfer", "VCh", "Contacts", 10.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("v_outer_chamfer_type", "V Chamfer Type", "VCt", "Contacts", "straight", kind="choice", choices=[("none", "none"), ("straight", "straight"), ("round", "round")]),
        ParameterSpec("v_outer_offset_x", "V Offset X", "Vx", "Contacts", 45.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("v_outer_offset_y", "V Offset Y", "Vy", "Contacts", 90.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
    ],
)


TLM_COMPONENT_TOOL = ToolSpec(
    key="tlm_component",
    title="TLM",
    library_name="",
    pcell_name="",
    preview_renderer=render_tlm_component,
    preview_layers=[("channel", "Channel"), ("source_drain", "Pads / Fanout"), ("labels", "Labels"), ("alignment_marks", "Marks"), ("parameter_labels", "Notes")],
    insert_handler=_insert_tlm_component,
    params=[
        ParameterSpec("cell_name", "Cell Name", "Cell", "Placement", "TLM_Device", kind="string"),
        ParameterSpec("x", "Center X", "Cx", "Placement", 0.0, minimum=-10000.0, maximum=10000.0, suffix=" um"),
        ParameterSpec("y", "Center Y", "Cy", "Placement", 0.0, minimum=-10000.0, maximum=10000.0, suffix=" um"),
        ParameterSpec("label_text", "Label Text", "Lbl", "Labels", "TLM", kind="string"),
        ParameterSpec("num_electrodes", "Electrode Count", "N", "Structure", 8, kind="int", minimum=3, maximum=100),
        ParameterSpec("min_spacing", "Min Spacing", "Smin", "Structure", 1.0, minimum=0.01, maximum=1000.0, suffix=" um"),
        ParameterSpec("max_spacing", "Max Spacing", "Smax", "Structure", 20.0, minimum=0.01, maximum=5000.0, suffix=" um"),
        ParameterSpec("distribution", "Distribution", "Dist", "Structure", "inv", kind="choice", choices=[("log", "log"), ("linear", "linear"), ("exp", "exp"), ("inv", "inv")]),
        ParameterSpec("spacing_mode", "Spacing Mode", "SM", "Structure", "centered", kind="choice", choices=[("centered", "centered"), ("left_to_right", "left_to_right")]),
        ParameterSpec("inner_pad_length", "Inner Pad Length", "Li", "Pads", 2.0, minimum=0.01, maximum=1000.0, suffix=" um"),
        ParameterSpec("inner_pad_width", "Inner Pad Width", "Wi", "Pads", 0.0, minimum=0.0, maximum=1000.0, suffix=" um", tooltip="0 means auto"),
        ParameterSpec("outer_pad_length", "Outer Pad Length", "Lo", "Pads", 60.0, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("outer_pad_width", "Outer Pad Width", "Wo", "Pads", 60.0, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("outer_pad_spacing", "Outer Pad Spacing", "Os", "Pads", 0.0, minimum=0.0, maximum=5000.0, suffix=" um", tooltip="0 means auto"),
        ParameterSpec("outer_pad_offset_y", "Outer Pad Offset Y", "Oy", "Pads", 100.0, minimum=0.1, maximum=5000.0, suffix=" um"),
        ParameterSpec("outer_pad_chamfer_size", "Pad Chamfer", "Ch", "Pads", 6.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("outer_pad_chamfer_type", "Chamfer Type", "CT", "Pads", "straight", kind="choice", choices=[("none", "none"), ("straight", "straight"), ("round", "round")]),
        ParameterSpec("channel_length", "Channel Length", "Lch", "Channel", 0.0, minimum=0.0, maximum=5000.0, suffix=" um", tooltip="0 means auto"),
        ParameterSpec("channel_width", "Channel Width", "Wch", "Channel", 10.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("device_margin_x", "Device Margin X", "DMx", "Marks", 150.0, minimum=0.0, maximum=10000.0, suffix=" um"),
        ParameterSpec("device_margin_y", "Device Margin Y", "DMy", "Marks", 140.0, minimum=0.0, maximum=10000.0, suffix=" um"),
        ParameterSpec("add_alignment_mark", "Show Marks", "AM", "Marks", 1, kind="choice", choices=[("true", True), ("false", False)]),
        ParameterSpec("mark_size", "Mark Size", "MS", "Marks", 20.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("mark_width", "Mark Width", "MW", "Marks", 2.0, minimum=0.1, maximum=100.0, suffix=" um"),
        ParameterSpec("mark_type_1", "Mark 1", "M1", "Marks", "sq_missing", kind="choice", choices=[("double_square", "double_square"), ("square", "square"), ("diamond", "diamond"), ("triangle", "triangle"), ("cross", "cross"), ("circle", "circle"), ("L_shape", "L_shape"), ("T_shape", "T_shape"), ("sq_missing", "sq_missing"), ("cross_tri", "cross_tri")]),
        ParameterSpec("mark_type_2", "Mark 2", "M2", "Marks", "L_shape", kind="choice", choices=[("double_square", "double_square"), ("square", "square"), ("diamond", "diamond"), ("triangle", "triangle"), ("cross", "cross"), ("circle", "circle"), ("L_shape", "L_shape"), ("T_shape", "T_shape"), ("sq_missing", "sq_missing"), ("cross_tri", "cross_tri")]),
        ParameterSpec("mark_type_3", "Mark 3", "M3", "Marks", "L_shape", kind="choice", choices=[("double_square", "double_square"), ("square", "square"), ("diamond", "diamond"), ("triangle", "triangle"), ("cross", "cross"), ("circle", "circle"), ("L_shape", "L_shape"), ("T_shape", "T_shape"), ("sq_missing", "sq_missing"), ("cross_tri", "cross_tri")]),
        ParameterSpec("mark_type_4", "Mark 4", "M4", "Marks", "L_shape", kind="choice", choices=[("double_square", "double_square"), ("square", "square"), ("diamond", "diamond"), ("triangle", "triangle"), ("cross", "cross"), ("circle", "circle"), ("L_shape", "L_shape"), ("T_shape", "T_shape"), ("sq_missing", "sq_missing"), ("cross_tri", "cross_tri")]),
        ParameterSpec("mark_rotation_1", "Rot 1", "R1", "Marks", 2, kind="int", minimum=0, maximum=3),
        ParameterSpec("mark_rotation_2", "Rot 2", "R2", "Marks", 0, kind="int", minimum=0, maximum=3),
        ParameterSpec("mark_rotation_3", "Rot 3", "R3", "Marks", 2, kind="int", minimum=0, maximum=3),
        ParameterSpec("mark_rotation_4", "Rot 4", "R4", "Marks", 3, kind="int", minimum=0, maximum=3),
        ParameterSpec("label_size", "Label Size", "LS", "Labels", 20.0, minimum=1.0, maximum=500.0, suffix=" um"),
        ParameterSpec("label_offset_x", "Label Offset X", "LOx", "Labels", 30.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("label_offset_y", "Label Offset Y", "LOy", "Labels", -10.0, minimum=-5000.0, maximum=5000.0, suffix=" um"),
    ],
)


MEANDER_COMPONENT_TOOL = ToolSpec(
    key="meander_component",
    title="Meander",
    library_name="",
    pcell_name="",
    preview_renderer=render_meander_component,
    preview_layers=[("channel", "Channel")],
    insert_handler=_insert_meander_component,
    params=[
        ParameterSpec("cell_name", "Cell Name", "Cell", "Placement", "Meander_Device", kind="string"),
        ParameterSpec("x", "Center X", "Cx", "Placement", 0.0, minimum=-10000.0, maximum=10000.0, suffix=" um"),
        ParameterSpec("y", "Center Y", "Cy", "Placement", 0.0, minimum=-10000.0, maximum=10000.0, suffix=" um"),
        ParameterSpec("region_width", "Region Width", "W", "Region", 200.0, minimum=1.0, maximum=10000.0, suffix=" um"),
        ParameterSpec("region_height", "Region Height", "H", "Region", 100.0, minimum=1.0, maximum=10000.0, suffix=" um"),
        ParameterSpec("line_width", "Line Width", "Wl", "Pattern", 5.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("line_spacing", "Line Spacing", "Sl", "Pattern", 10.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("direction", "Direction", "Dir", "Pattern", "horizontal", kind="choice", choices=[("horizontal", "horizontal"), ("vertical", "vertical")]),
        ParameterSpec("margin", "Margin", "Mg", "Pattern", 0.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("curve_type", "Curve Type", "Cv", "Pattern", "serpentine", kind="choice", choices=[("serpentine", "serpentine"), ("peano", "peano"), ("hilbert", "hilbert"), ("gosper", "gosper"), ("moore", "moore")]),
    ],
)


SENSE_LATCH_ARRAY_TOOL = ToolSpec(
    key="sense_latch_array",
    title="Sense / Latch Array",
    library_name="",
    pcell_name="",
    preview_renderer=render_sense_latch_array,
    preview_layers=[
        ("channel", "Channel"),
        ("contact", "N/P Contact"),
        ("bottom_gate", "Bottom Gate"),
        ("top_dielectric", "Top Dielectric"),
        ("pad", "Breakout Pads"),
        ("note", "Pixel Outline"),
    ],
    insert_handler=_insert_sense_latch_array_component,
    params=[
        ParameterSpec("cell_name", "Cell Name", "Cell", "Placement", "Sense_Latch_Array", kind="string"),
        ParameterSpec("origin_mode", "Origin Mode", "Org", "Placement", "center", kind="choice", choices=[("center", "center"), ("lower_left", "lower_left")]),
        ParameterSpec("offset_x", "Offset X", "Ox", "Placement", 0.0, minimum=-100000.0, maximum=100000.0, suffix=" um"),
        ParameterSpec("offset_y", "Offset Y", "Oy", "Placement", 0.0, minimum=-100000.0, maximum=100000.0, suffix=" um"),
        ParameterSpec("array_shape_mode", "Array Mode", "Am", "Array", "square", kind="choice", choices=[("square", "square"), ("rectangular", "rectangular")]),
        ParameterSpec("array_size", "Array Size", "N", "Array", 3, kind="int", minimum=1, maximum=512),
        ParameterSpec("rows", "Rows", "R", "Array", 3, kind="int", minimum=1, maximum=512),
        ParameterSpec("cols", "Cols", "C", "Array", 3, kind="int", minimum=1, maximum=512),
        ParameterSpec("pixel_size", "Pixel Size", "P", "Array", 50.0, minimum=2.0, maximum=10000.0, suffix=" um"),
        ParameterSpec("stack_base", "Stack Base", "Stk", "Process", 11, kind="choice", choices=[("11", 11), ("21", 21)]),
        ParameterSpec("channel_type", "Channel Type", "Type", "Process", "n", kind="choice", choices=[("n", "n"), ("p", "p")]),
        ParameterSpec("edge_margin", "Edge Margin", "Em", "Layout", 2.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("trail_edge_margin", "Trail Edge Margin", "Tem", "Layout", 2.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("contact_tail_margin", "Trail End Margin", "Ttm", "Layout", 0.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("channel_margin", "Channel Margin", "Cm", "Layout", 2.0, minimum=0.0, maximum=1000.0, suffix=" um", tooltip="Shrinks channel height inside each FET window."),
        ParameterSpec("channel_edge_gap", "Channel Edge Gap", "Ceg", "Layout", 2.0, minimum=0.0, maximum=1000.0, suffix=" um", tooltip="Keeps channel away from the pixel left/right edge so adjacent pixels do not short."),
        ParameterSpec("contact_overlap_margin", "Dielectric Margin", "Dom", "Layout", 2.0, minimum=0.0, maximum=1000.0, suffix=" um", tooltip="Only affects the top dielectric outline when Top Dielectric is enabled."),
        ParameterSpec("contact_spine_width", "Trail Width", "Tw", "Contacts", 4.0, minimum=2.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("fet_gap", "FET Gap", "Gap", "Contacts", 12.0, minimum=2.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("shared_contact_height", "Shared Contact Height", "Sch", "Contacts", 12.0, minimum=2.0, maximum=1000.0, suffix=" um", tooltip="Minimum vertical size of the shared middle contact between sens and latch."),
        ParameterSpec("outer_contact_min_length", "Outer Contact Min", "Ocm", "Contacts", 2.0, minimum=2.0, maximum=1000.0, suffix=" um", tooltip="Minimum allowed left/right outer-contact length after centering the full two-FET assembly."),
        ParameterSpec("sense_fet_structure", "Sense FET Structure", "Sfs", "Sens FET", "plain", kind="choice", choices=[("plain", "plain"), ("interdigitated", "interdigitated")], tooltip="Choose the sense transistor contact style: the current plain block or an interdigitated finger electrode."),
        ParameterSpec("sens_width", "Sens Width", "Ws", "Sens FET", 30.0, minimum=2.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("sens_length", "Sens Length", "Ls", "Sens FET", 10.0, minimum=2.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("sens_channel_overlap", "Sens Channel Overlap", "Sco", "Sens FET", 2.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("sens_pad_overhang", "Sens Pad Overhang", "Spo", "Sens FET", 2.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("sense_interdigit_finger_width", "Inner Finger Width", "Wf", "Sens FET", 2.0, minimum=0.1, maximum=1000.0, suffix=" um", tooltip="Width of each interdigit inner electrode stripe."),
        ParameterSpec("sense_interdigit_finger_spacing", "Inner Finger Spacing", "Sf", "Sens FET", 1.0, minimum=0.0, maximum=1000.0, suffix=" um", tooltip="Spacing between adjacent interdigit inner electrode stripes."),
        ParameterSpec("sense_interdigit_tip_gap", "Tip Gap", "Tg", "Sens FET", 1.5, minimum=0.1, maximum=1000.0, suffix=" um", tooltip="Gap from one side's finger tip to the opposite main electrode body."),
        ParameterSpec("latch_width", "Latch Width", "Wl", "Latch FET", 30.0, minimum=2.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("latch_length", "Latch Length", "Ll", "Latch FET", 5.0, minimum=2.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("latch_channel_overlap", "Latch Channel Overlap", "Lco", "Latch FET", 2.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("latch_pad_overhang", "Latch Pad Overhang", "Lpo", "Latch FET", 2.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("gate_line_width", "Gate Trail Width", "Gtw", "Gate", 4.0, minimum=2.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("gate_extension", "Gate Extension", "Gex", "Gate", 2.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("gate_length_overhang", "Gate Length Overhang", "Glo", "Gate", 2.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("gate_width_overhang", "Gate Width Overhang", "Gwo", "Gate", 2.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("gate_gap", "Gate Gap", "Gg", "Gate", 2.0, minimum=0.0, maximum=1000.0, suffix=" um", tooltip="Minimum vertical separation budget between the upper and lower gate routing zones."),
        ParameterSpec("draw_channel", "Draw Channel", "Ch", "Options", 1, kind="choice", choices=[("true", True), ("false", False)]),
        ParameterSpec("draw_top_dielectric", "Top Dielectric", "Td", "Options", 0, kind="choice", choices=[("true", True), ("false", False)]),
        ParameterSpec("draw_array_pads", "Array Pads", "Pad", "Options", 1, kind="choice", choices=[("true", True), ("false", False)]),
        ParameterSpec("note_text_enabled", "Note Text", "Txt", "Options", 1, kind="choice", choices=[("true", True), ("false", False)]),
        ParameterSpec("array_pad_size", "Pad Size", "Ps", "Fanout", 20.0, minimum=2.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("array_pad_overlap", "Pad Overlap", "Po", "Fanout", 4.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("gate_pad_offset", "Gate Pad Offset", "Gpo", "Fanout", 18.0, minimum=0.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("contact_pad_offset", "Contact Pad Offset", "Cpo", "Fanout", 18.0, minimum=0.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("gate_pad_pitch", "Gate Pad Pitch", "Gpp", "Fanout", 26.0, minimum=0.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("pad_connection_style", "Pad Connection", "Pcs", "Fanout", "line", kind="choice", choices=[("line", "line"), ("block", "block")]),
        ParameterSpec("show_pixel_outline", "Show Pixel Outline", "Out", "Debug", 0, kind="choice", choices=[("true", True), ("false", False)]),
        ParameterSpec("pixel_outline_layer", "Outline Layer", "Ol", "Debug", 6, kind="int", minimum=0, maximum=1000),
    ],
)


WRITE_READ_ARRAY_TOOL = ToolSpec(
    key="write_read_array",
    title="Write / Read Array",
    library_name="",
    pcell_name="",
    preview_renderer=render_write_read_array,
    preview_layers=[
        ("channel", "Channel"),
        ("contact", "N/P Contact"),
        ("bottom_gate", "Bottom Gate"),
        ("bottom_dielectric", "Bottom Dielectric"),
        ("top_dielectric", "Top Dielectric"),
        ("pad", "Breakout Pads"),
        ("note", "Notes"),
    ],
    insert_handler=_insert_write_read_array_component,
    params=[
        ParameterSpec("cell_name", "Cell Name", "Cell", "Placement", "Write_Read_Array", kind="string"),
        ParameterSpec("origin_mode", "Origin Mode", "Org", "Placement", "center", kind="choice", choices=[("center", "center"), ("lower_left", "lower_left")]),
        ParameterSpec("offset_x", "Offset X", "Ox", "Placement", 0.0, minimum=-100000.0, maximum=100000.0, suffix=" um"),
        ParameterSpec("offset_y", "Offset Y", "Oy", "Placement", 0.0, minimum=-100000.0, maximum=100000.0, suffix=" um"),
        ParameterSpec("array_shape_mode", "Array Mode", "Am", "Array", "square", kind="choice", choices=[("square", "square"), ("rectangular", "rectangular")]),
        ParameterSpec("array_size", "Array Size", "N", "Array", 3, kind="int", minimum=1, maximum=512),
        ParameterSpec("rows", "Rows", "R", "Array", 3, kind="int", minimum=1, maximum=512),
        ParameterSpec("cols", "Cols", "C", "Array", 3, kind="int", minimum=1, maximum=512),
        ParameterSpec("pixel_size", "Pixel Size", "P", "Array", 72.0, minimum=2.0, maximum=10000.0, suffix=" um"),
        ParameterSpec("stack_base", "Stack Base", "Stk", "Process", 11, kind="choice", choices=[("11", 11), ("21", 21)]),
        ParameterSpec("channel_type", "Channel Type", "Type", "Process", "n", kind="choice", choices=[("n", "n"), ("p", "p")]),
        ParameterSpec("edge_margin", "Edge Margin", "Em", "Layout", 2.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("trail_edge_margin", "Trail Edge Margin", "Tem", "Layout", 2.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("contact_tail_margin", "Trail End Margin", "Ttm", "Layout", 0.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("channel_margin", "Channel Margin", "Cm", "Layout", 2.0, minimum=0.0, maximum=1000.0, suffix=" um", tooltip="Shrinks channel geometry where applicable."),
        ParameterSpec("channel_edge_gap", "Channel Edge Gap", "Ceg", "Layout", 2.0, minimum=0.0, maximum=1000.0, suffix=" um", tooltip="Keeps channel away from pixel left/right edges."),
        ParameterSpec("contact_overlap_margin", "Dielectric Margin", "Dom", "Layout", 2.0, minimum=0.0, maximum=1000.0, suffix=" um", tooltip="Only affects dielectric outline when Top Dielectric is enabled."),
        ParameterSpec("contact_spine_width", "Trail Width", "Tw", "Routing", 4.0, minimum=2.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("gate_line_width", "Gate Trail Width", "Gtw", "Routing", 4.0, minimum=2.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("fet_gap", "FET Gap", "Gap", "Routing", 8.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("shared_contact_height", "Shared Height", "Sch", "Routing", 12.0, minimum=2.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("outer_contact_min_length", "Outer Contact Min", "Ocm", "Routing", 2.0, minimum=2.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("write_width", "Write Width", "Ww", "Write FET", 16.0, minimum=2.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("write_length", "Write Length", "Lw", "Write FET", 10.0, minimum=2.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("write_channel_overlap", "Write Channel Overlap", "Wco", "Write FET", 2.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("write_pad_overhang", "Write Pad Overhang", "Wpo", "Write FET", 2.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("write_left_contact_length", "Write Left Contact", "Wlc", "Write FET", 8.0, minimum=2.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("write_right_contact_length", "Write Right Contact", "Wrc", "Write FET", 8.0, minimum=2.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("read_width", "Read Width", "Wr", "Read FET", 14.0, minimum=2.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("read_length", "Read Length", "Lr", "Read FET", 18.0, minimum=2.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("read_channel_overlap", "Read Channel Overlap", "Rco", "Read FET", 2.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("read_pad_overhang", "Read Pad Overhang", "Rpo", "Read FET", 2.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("read_contact_length", "Read Contact Length", "Rcl", "Read FET", 10.0, minimum=2.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("gate_extension", "Gate Extension", "Gex", "Gate", 2.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("gate_length_overhang", "Gate Length Overhang", "Glo", "Gate", 2.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("gate_width_overhang", "Gate Width Overhang", "Gwo", "Gate", 2.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("gate_gap", "Gate Gap", "Gg", "Gate", 2.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("coupling_gate_pad_size", "Coupling Via Pad", "Cgp", "Coupling", 6.0, minimum=2.0, maximum=1000.0, suffix=" um", tooltip="Base size used for bottom-gate coupling features and the read bottom stub."),
        ParameterSpec("coupling_via_size", "Dielectric Via Size", "Cvs", "Coupling", 4.0, minimum=1.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("read_gate_bridge_width", "Read Gate Bridge", "Rgb", "Coupling", 4.0, minimum=1.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("rwl_up_extension", "RWL Up Extension", "Rue", "Coupling", 6.0, minimum=0.0, maximum=1000.0, suffix=" um", tooltip="How far the RWL bottom-gate trail rises upward into the pixel."),
        ParameterSpec("read_bottom_overlap_height", "Read Bottom Overlap", "Rbo", "Coupling", 4.0, minimum=0.0, maximum=1000.0, suffix=" um", tooltip="Overlap height between the read bottom contact and the upward RWL gate stub."),
        ParameterSpec("write_coupling_via_inset", "Write Via Inset", "Wvi", "Coupling", 2.0, minimum=0.0, maximum=1000.0, suffix=" um", tooltip="Keeps the write-side coupling via inside the contact-only overlap region, away from the channel."),
        ParameterSpec("draw_channel", "Draw Channel", "Ch", "Options", 1, kind="choice", choices=[("true", True), ("false", False)]),
        ParameterSpec("draw_top_dielectric", "Top Dielectric", "Td", "Options", 0, kind="choice", choices=[("true", True), ("false", False)]),
        ParameterSpec("draw_array_pads", "Array Pads", "Pad", "Options", 1, kind="choice", choices=[("true", True), ("false", False)]),
        ParameterSpec("note_text_enabled", "Note Text", "Txt", "Options", 1, kind="choice", choices=[("true", True), ("false", False)]),
        ParameterSpec("array_pad_size", "Pad Size", "Ps", "Fanout", 20.0, minimum=2.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("array_pad_overlap", "Pad Overlap", "Po", "Fanout", 4.0, minimum=0.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("gate_pad_offset", "Gate Pad Offset", "Gpo", "Fanout", 18.0, minimum=0.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("contact_pad_offset", "Contact Pad Offset", "Cpo", "Fanout", 18.0, minimum=0.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("gate_pad_pitch", "Gate Pad Pitch", "Gpp", "Fanout", 26.0, minimum=0.0, maximum=5000.0, suffix=" um"),
        ParameterSpec("pad_connection_style", "Pad Connection", "Pcs", "Fanout", "line", kind="choice", choices=[("line", "line"), ("block", "block")]),
        ParameterSpec("show_pixel_outline", "Show Pixel Outline", "Out", "Debug", 0, kind="choice", choices=[("true", True), ("false", False)]),
        ParameterSpec("pixel_outline_layer", "Outline Layer", "Ol", "Debug", 6, kind="int", minimum=0, maximum=1000),
    ],
)


def launch_toolkit_dialog():
    dlg = ToolkitDialog(
        [
            NANODEVICE_FET_TOOL,
            GDSFACTORY_TEXT_TOOL,
            MOSFET_COMPONENT_TOOL,
            HALL_COMPONENT_TOOL,
            TLM_COMPONENT_TOOL,
            SENSE_LATCH_ARRAY_TOOL,
            WRITE_READ_ARRAY_TOOL,
        ]
    )
    dlg.exec_()
