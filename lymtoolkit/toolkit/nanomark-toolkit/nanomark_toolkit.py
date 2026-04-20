import json
import os
import sys
from dataclasses import dataclass
import xml.etree.ElementTree as ET

import pya
from PyQt5.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt5.QtGui import QColor, QBrush, QFont, QPainter, QPainterPath, QPen
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
            and os.path.isdir(os.path.join(candidate, "components"))
        ):
            return candidate
    return os.path.abspath(os.path.join(current, "..", "..", ".."))


ROOT_DIR = _discover_root_dir()
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config import DEFAULT_DBU
from components.markarray import build_general_mark_array_layout, build_writefield_mark_layout


def _discover_layer_map_path():
    candidates = [
        os.path.join(ROOT_DIR, "lymtoolkit", "PDK", "layers", "layer_map.lyp"),
        os.path.join(ROOT_DIR, "lymtoolkit", "pdk", "layers", "layer_map.lyp"),
        os.path.join(ROOT_DIR, "pdk", "layers", "layer_map.lyp"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return candidates[0]


LAYER_MAP_PATH = _discover_layer_map_path()


@dataclass
class ParameterSpec:
    key: str
    label: str
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
    params: list
    preview_layers: list
    generator: callable
    layer_mapping: dict


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
FALLBACK_LAYER_COLORS = {
    "mechanical": QColor("#6c7a89"),
    "active": QColor("#4ea8de"),
    "mark": QColor("#f7b32b"),
    "mark_frame": QColor("#90be6d"),
    "caliper": QColor("#f94144"),
    "auto_align": QColor("#43aa8b"),
    "manual_align": QColor("#577590"),
}


def _preview_style(layer_tuple, fallback_key=None):
    style = LAYER_STYLES.get(int(layer_tuple[0]))
    if style:
        fill = QColor(style["fill"])
        fill.setAlpha(88)
        return QPen(style["frame"], 0), QBrush(fill)
    color = FALLBACK_LAYER_COLORS.get(fallback_key or "", QColor("#d9d9d9"))
    fill = QColor(color)
    fill.setAlpha(88)
    return QPen(color, 0), QBrush(fill)


def _append_points_to_path(path, points, dbu):
    first = points[0]
    path.moveTo(first.x * dbu, -first.y * dbu)
    for point in points[1:]:
        path.lineTo(point.x * dbu, -point.y * dbu)
    path.closeSubpath()


def _polygon_to_paths(polygon, dbu):
    path = QPainterPath()
    hull = [point for point in polygon.each_point_hull()]
    if not hull:
        return []
    _append_points_to_path(path, hull, dbu)
    for hole_index in range(polygon.holes()):
        hole = [point for point in polygon.each_point_hole(hole_index)]
        if hole:
            _append_points_to_path(path, hole, dbu)
    return [path]


def _shape_to_paths(shape, dbu):
    if shape.is_box():
        box = shape.box
        path = QPainterPath()
        path.addRect(
            box.left * dbu,
            -box.top * dbu,
            (box.right - box.left) * dbu,
            (box.top - box.bottom) * dbu,
        )
        return [path]
    if shape.is_polygon():
        return _polygon_to_paths(shape.polygon, dbu)
    if shape.is_path():
        return _polygon_to_paths(shape.path.polygon(), dbu)
    if shape.is_text():
        text = shape.text
        text_path = QPainterPath()
        font = QFont("Segoe UI", 8)
        text_path.addText(0.0, 0.0, font, text.string)
        bounds = text_path.boundingRect()
        x = text.trans.disp.x * dbu
        y = -text.trans.disp.y * dbu
        return [text_path.translated(x - bounds.left(), y - bounds.bottom())]
    box = shape.bbox()
    if box is None:
        return []
    path = QPainterPath()
    path.addRect(
        box.left * dbu,
        -box.top * dbu,
        (box.right - box.left) * dbu,
        (box.top - box.bottom) * dbu,
    )
    return [path]


def _shape_copy_to_target(shape, shape_collection):
    if shape.is_box():
        shape_collection.insert(shape.box)
    elif shape.is_polygon():
        shape_collection.insert(shape.polygon)
    elif shape.is_path():
        shape_collection.insert(shape.path)
    elif shape.is_text():
        shape_collection.insert(shape.text)


def _serialize_values(values):
    serialized = {}
    for key, value in values.items():
        if isinstance(value, tuple):
            serialized[key] = list(value)
        else:
            serialized[key] = value
    return serialized


def _draw_layout_preview(scene, layout, top_cell, visible_layer_keys, tool_spec):
    dbu = layout.dbu
    for preview_key, _label in tool_spec.preview_layers:
        if not visible_layer_keys.get(preview_key, True):
            continue
        param_key = tool_spec.layer_mapping.get(preview_key)
        if not param_key:
            continue
        layer_tuple = tool_spec._current_values[param_key]
        layer_index = layout.find_layer(int(layer_tuple[0]), int(layer_tuple[1]))
        if layer_index < 0:
            continue
        pen, brush = _preview_style(layer_tuple, preview_key)
        for shape in top_cell.shapes(layer_index).each():
            for path in _shape_to_paths(shape, dbu):
                scene.addPath(path, pen, brush)


def _insert_layout_into_active_cell(target_layout, target_cell, source_layout, source_top):
    for layer_index in source_layout.layer_indices():
        info = source_layout.get_info(layer_index)
        dest_layer = target_layout.layer(int(info.layer), int(info.datatype))
        dest_shapes = target_cell.shapes(dest_layer)
        for shape in source_top.shapes(layer_index).each():
            _shape_copy_to_target(shape, dest_shapes)


def _mark_array_values(values):
    return {
        "sample_width": values["sample_width"],
        "sample_height": values["sample_height"],
        "active_width": values["active_width"],
        "active_height": values["active_height"],
        "mark_width": values["mark_width"],
        "mark_size": values["mark_size"],
        "mark_pitch_x": values["mark_pitch_x"],
        "mark_pitch_y": values["mark_pitch_y"],
        "mark_type": values["mark_type"],
        "label_interval": values["label_interval"],
        "boundary_line_width": values["boundary_line_width"],
        "layer_mechanical": values["layer_mechanical"],
        "layer_active": values["layer_active"],
        "layer_mark": values["layer_mark"],
        "label_offset": (values["label_offset_x"], values["label_offset_y"]),
        "label_size": values["label_size"],
        "user_name": values["user_name"],
        "info_text_size": values["info_text_size"],
        "info_text_offset": (values["info_text_offset_x"], values["info_text_offset_y"]),
        "name": values["name"],
    }


def _writefield_values(values):
    frame_width = values["frame_width"]
    if frame_width <= 0.0:
        frame_width = None
    return {
        "sample_width": values["sample_width"],
        "sample_height": values["sample_height"],
        "active_width": values["active_width"],
        "active_height": values["active_height"],
        "writefield_size": values["writefield_size"],
        "mark_main_size": values["mark_main_size"],
        "mark_main_width": values["mark_main_width"],
        "mark_small_size": values["mark_small_size"],
        "mark_small_width": values["mark_small_width"],
        "mark_small_dist": values["mark_small_dist"],
        "l_marker_length": values["l_marker_length"],
        "l_marker_width": values["l_marker_width"],
        "boundary_line_width": values["boundary_line_width"],
        "mark_offset_from_corner": (values["mark_offset_x"], values["mark_offset_y"]),
        "global_mark_offset": values["global_mark_offset"],
        "global_mark_main_size": values["global_mark_main_size"],
        "global_mark_main_width": values["global_mark_main_width"],
        "global_mark_small_size": values["global_mark_small_size"],
        "global_mark_small_width": values["global_mark_small_width"],
        "global_mark_small_dist": values["global_mark_small_dist"],
        "label_size": values["label_size"],
        "label_offset": (values["label_offset_x"], values["label_offset_y"]),
        "enable_caliper": values["enable_caliper"],
        "caliper_width": values["caliper_width"],
        "caliper_top_right_pitch": values["caliper_top_right_pitch"],
        "caliper_top_right_num_side": values["caliper_top_right_num_side"],
        "caliper_top_right_tick_length": values["caliper_top_right_tick_length"],
        "caliper_top_right_center_length": values["caliper_top_right_center_length"],
        "caliper_bottom_left_pitch": values["caliper_bottom_left_pitch"],
        "caliper_bottom_left_num_side": values["caliper_bottom_left_num_side"],
        "caliper_bottom_left_tick_length": values["caliper_bottom_left_tick_length"],
        "caliper_bottom_left_center_length": values["caliper_bottom_left_center_length"],
        "layer_mechanical": values["layer_mechanical"],
        "layer_active": values["layer_active"],
        "layer_mark": values["layer_mark"],
        "layer_mark_frame": values["layer_mark_frame"],
        "layer_caliper": values["layer_caliper"],
        "layer_auto_align": values["layer_auto_align"],
        "layer_manual_align": values["layer_manual_align"],
        "frame_width": frame_width,
        "user_name": values["user_name"],
        "info_text_size": values["info_text_size"],
        "info_text_offset": (values["info_text_offset_x"], values["info_text_offset_y"]),
        "info_text_line_width": values["info_text_line_width"],
        "enable_alignment_layers": values["enable_alignment_layers"],
    }


def _generate_mark_array(values):
    return build_general_mark_array_layout(**_mark_array_values(values))


def _generate_writefield_array(values):
    return build_writefield_mark_layout(**_writefield_values(values))


class PreviewView(QGraphicsView):
    def __init__(self):
        scene = QGraphicsScene()
        super().__init__(scene)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setMinimumSize(520, 380)
        self.setStyleSheet("background: #111;")
        self._bounds = QRectF(-100.0, -100.0, 200.0, 200.0)
        self._has_fitted_once = False
        self._last_tool_key = None

    def wheelEvent(self, event):
        factor = 1.18 if event.angleDelta().y() > 0 else 1.0 / 1.18
        self.scale(factor, factor)

    def drawBackground(self, painter, rect):
        painter.fillRect(rect, QColor("#111111"))
        step = self._grid_step()
        minor_pen = QPen(QColor(255, 255, 255, 18), 0)
        major_pen = QPen(QColor(255, 255, 255, 38), 0)
        left = int(rect.left() // step) - 1
        right = int(rect.right() // step) + 1
        top = int(rect.top() // step) - 1
        bottom = int(rect.bottom() // step) + 1
        for ix in range(left, right + 1):
            painter.setPen(major_pen if ix % 5 == 0 else minor_pen)
            x = ix * step
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
        for iy in range(top, bottom + 1):
            painter.setPen(major_pen if iy % 5 == 0 else minor_pen)
            y = iy * step
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))

    def drawForeground(self, painter, rect):
        del rect
        self._draw_scale_bar(painter)

    def _grid_step(self):
        scale = abs(self.transform().m11()) or 1.0
        target = 28.0 / scale
        decade = 1.0
        while target > decade * 10.0:
            decade *= 10.0
        while target < decade:
            decade /= 10.0
        for factor in (1.0, 2.0, 5.0, 10.0):
            step = decade * factor
            if step >= target:
                return step
        return decade * 10.0

    def _draw_scale_bar(self, painter):
        viewport_rect = self.viewport().rect()
        margin = 18
        max_px = 120.0
        scale = abs(self.transform().m11()) or 1.0
        bar_um = _nice_length((max_px / scale) * 0.65)
        bar_px = bar_um * scale
        if bar_px < 24.0:
            return
        x1 = viewport_rect.left() + margin
        x2 = x1 + bar_px
        y = viewport_rect.bottom() - margin
        painter.resetTransform()
        painter.setPen(QPen(QColor("#f2f2f2"), 1.0))
        painter.drawLine(int(x1), int(y), int(x2), int(y))
        painter.drawLine(int(x1), int(y - 5), int(x1), int(y + 5))
        painter.drawLine(int(x2), int(y - 5), int(x2), int(y + 5))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(
            QRectF(x1, y - 18, bar_px + 8.0, 14.0),
            Qt.AlignLeft | Qt.AlignVCenter,
            _format_length(bar_um),
        )

    def draw_mark_preview(self, tool_spec, values, visible_layers, preserve_view=True):
        scene = self.scene()
        saved_transform = self.transform()
        saved_center = self.mapToScene(self.viewport().rect().center())
        tool_changed = tool_spec.key != self._last_tool_key
        scene.clear()
        try:
            layout, top_cell = tool_spec.generator(values)
            tool_spec._current_values = values
            _draw_layout_preview(scene, layout, top_cell, visible_layers, tool_spec)
        except Exception as exc:
            self._draw_preview_error(scene, str(exc))
        bounds = scene.itemsBoundingRect()
        if bounds.isNull():
            bounds = QRectF(-50.0, -50.0, 100.0, 100.0)
        self._bounds = bounds.adjusted(-20.0, -20.0, 20.0, 20.0)
        scene.setSceneRect(self._bounds)
        if preserve_view and self._has_fitted_once and not tool_changed:
            self.setTransform(saved_transform)
            self.centerOn(saved_center)
            self._last_tool_key = tool_spec.key
            return
        self.resetTransform()
        self.fitInView(self._bounds, Qt.KeepAspectRatio)
        self._has_fitted_once = True
        self._last_tool_key = tool_spec.key

    def _draw_preview_error(self, scene, message):
        title = scene.addText("Preview unavailable")
        title.setDefaultTextColor(QColor("#ff8c69"))
        title.setPos(-70.0, -10.0)
        detail = scene.addText(message[:260])
        detail.setDefaultTextColor(QColor("#d9d9d9"))
        detail.setPos(-120.0, 18.0)


class NanoMarkDialog(QDialog):
    def __init__(self, tool_specs, parent=None):
        super().__init__(parent)
        self.tool_specs = {spec.key: spec for spec in tool_specs}
        self.controls = {}
        self.layer_checks = {}

        self.setWindowTitle("NanoMark Toolkit")
        self.setMinimumSize(1000, 700)

        self.tool_select = QComboBox()
        for spec in tool_specs:
            self.tool_select.addItem(spec.title, spec.key)
        self.tool_select.currentIndexChanged.connect(self._rebuild_form)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFixedWidth(320)
        self.form_host = QWidget()
        self.form_layout = QVBoxLayout()
        self.form_host.setLayout(self.form_layout)
        self.scroll.setWidget(self.form_host)

        self.preview = PreviewView()
        self.preview_label = QLabel("Generated preview")
        self.layer_row = QHBoxLayout()
        self.layer_row.setContentsMargins(0, 0, 0, 0)
        self.layer_row.setSpacing(10)
        self.status_label = QLabel("Ready")

        self.preview_btn = QPushButton("Preview")
        self.preview_btn.clicked.connect(self._refit_preview)
        self.insert_btn = QPushButton("Insert")
        self.insert_btn.clicked.connect(self._insert_tool)
        self.import_btn = QPushButton("Import Config")
        self.import_btn.clicked.connect(self._import_config)
        self.export_btn = QPushButton("Export Config")
        self.export_btn.clicked.connect(self._export_config)
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.reject)

        self._build_ui()
        self._rebuild_form()

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
        layer_container = QHBoxLayout()
        layer_container.addWidget(QLabel("Layers"))
        layer_container.addLayout(self.layer_row, 1)
        right.addLayout(layer_container)
        right.addWidget(self.preview, 1)
        right.addWidget(self.status_label)
        split.addLayout(right, 1)
        main.addLayout(split, 1)

        btns = QHBoxLayout()
        btns.addWidget(self.import_btn)
        btns.addWidget(self.export_btn)
        btns.addStretch(1)
        btns.addWidget(self.preview_btn)
        btns.addWidget(self.insert_btn)
        btns.addWidget(self.close_btn)
        main.addLayout(btns)
        self.setLayout(main)

    def _current_tool(self):
        return self.tool_specs[self.tool_select.currentData()]

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)

    def _rebuild_form(self):
        self.controls = {}
        self._clear_layout(self.form_layout)
        self.preview._has_fitted_once = False
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
                form.addRow(param.label, control)
            box.setLayout(form)
            self.form_layout.addWidget(box)

        self.form_layout.addStretch(1)
        self._update_layer_controls(tool)
        QTimer.singleShot(0, self._refresh_preview)

    def _make_control(self, param):
        if param.kind == "string":
            control = QLineEdit()
            control.setText(str(param.default))
            control.textChanged.connect(self._refresh_preview)
            if param.tooltip:
                control.setToolTip(param.tooltip)
            return control

        if param.kind == "choice":
            control = QComboBox()
            for title, value in param.choices:
                control.addItem(title, value)
            default_index = 0
            for index, (_title, value) in enumerate(param.choices):
                if value == param.default:
                    default_index = index
                    break
            control.setCurrentIndex(default_index)
            control.currentIndexChanged.connect(self._refresh_preview)
            if param.tooltip:
                control.setToolTip(param.tooltip)
            return control

        if param.kind == "bool":
            control = QCheckBox()
            control.setChecked(bool(param.default))
            control.toggled.connect(self._refresh_preview)
            if param.tooltip:
                control.setToolTip(param.tooltip)
            return control

        if param.kind == "layer_choice":
            control = QComboBox()
            for title, value in self._available_layers(param.default):
                control.addItem(title, value)
            default_index = 0
            for idx in range(control.count()):
                if control.itemData(idx) == param.default:
                    default_index = idx
                    break
            control.setCurrentIndex(default_index)
            control.currentIndexChanged.connect(self._refresh_preview)
            if param.tooltip:
                control.setToolTip(param.tooltip)
            return control

        if param.kind == "int":
            control = QSpinBox()
            control.setRange(int(param.minimum), int(param.maximum))
            control.setValue(int(param.default))
            control.setKeyboardTracking(False)
            control.valueChanged.connect(self._refresh_preview)
            if param.tooltip:
                control.setToolTip(param.tooltip)
            return control

        control = QDoubleSpinBox()
        control.setDecimals(param.decimals)
        control.setRange(param.minimum, param.maximum)
        control.setValue(float(param.default))
        control.setKeyboardTracking(False)
        if param.suffix:
            control.setSuffix(param.suffix)
        control.valueChanged.connect(self._refresh_preview)
        if param.tooltip:
            control.setToolTip(param.tooltip)
        return control

    def _available_layers(self, default_value):
        layers = []
        seen = set()
        lv = pya.LayoutView.current()
        if lv is not None:
            cv = lv.active_cellview()
            if cv is not None and cv.layout() is not None:
                layout = cv.layout()
                try:
                    infos = list(layout.layer_infos())
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
            layers.insert(0, (f"{default_value[0]}/{default_value[1]}", default_value))
        return layers

    def _values(self):
        values = {}
        for param in self._current_tool().params:
            control = self.controls[param.key]
            if param.kind == "string":
                values[param.key] = control.text()
            elif param.kind in ("choice", "layer_choice"):
                values[param.key] = control.currentData()
            elif param.kind == "bool":
                values[param.key] = control.isChecked()
            else:
                values[param.key] = control.value()
        return values

    def _set_control_value(self, param, value):
        control = self.controls.get(param.key)
        if control is None or value is None:
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
        if param.kind == "bool":
            control.setChecked(bool(value))
            return
        if param.kind == "int":
            control.setValue(int(value))
            return
        control.setValue(float(value))

    def _layer_visibility(self):
        return {key: checkbox.isChecked() for key, checkbox in self.layer_checks.items()}

    def _update_layer_controls(self, tool):
        while self.layer_row.count():
            item = self.layer_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.layer_checks = {}
        for key, label in tool.preview_layers:
            checkbox = QCheckBox(label)
            checkbox.setChecked(True)
            checkbox.toggled.connect(self._refresh_preview)
            self.layer_row.addWidget(checkbox)
            self.layer_checks[key] = checkbox
        self.layer_row.addStretch(1)

    def _config_payload(self):
        tool = self._current_tool()
        return {
            "format": "nanomark-toolkit-config",
            "version": 1,
            "tool_key": tool.key,
            "tool_title": tool.title,
            "values": _serialize_values(self._values()),
        }

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
            "Export NanoMark Config",
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
        self.status_label.setText(f"Config exported: {file_path}")

    def _import_config(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import NanoMark Config",
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
        self.status_label.setText(f"Config imported: {file_path}")
        self._refresh_preview()

    def _refresh_preview(self):
        tool = self._current_tool()
        try:
            self.preview.draw_mark_preview(tool, self._values(), self._layer_visibility(), preserve_view=True)
            self.status_label.setText("Preview updated")
        except Exception as exc:
            self.status_label.setText(f"Preview failed: {exc}")

    def _refit_preview(self):
        tool = self._current_tool()
        try:
            self.preview.draw_mark_preview(tool, self._values(), self._layer_visibility(), preserve_view=False)
            self.status_label.setText("Preview refit")
        except Exception as exc:
            self.status_label.setText(f"Preview failed: {exc}")

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
        try:
            source_layout, source_top = tool.generator(self._values())
            _insert_layout_into_active_cell(cv.layout(), cv.cell, source_layout, source_top)
            lv.add_missing_layers()
            lv.zoom_fit()
            self.status_label.setText(f"{tool.title} inserted into active cell")
        except Exception as exc:
            QMessageBox.critical(self, "Insert Failed", str(exc))


MARK_ARRAY_TOOL = ToolSpec(
    key="mark_array",
    title="General Mark Array",
    generator=_generate_mark_array,
    preview_layers=[
        ("mechanical", "Mechanical"),
        ("active", "Active"),
        ("mark", "Mark / Label"),
    ],
    layer_mapping={
        "mechanical": "layer_mechanical",
        "active": "layer_active",
        "mark": "layer_mark",
    },
    params=[
        ParameterSpec("sample_width", "Sample Width", "Layout", 10000.0, minimum=1.0, maximum=100000.0, suffix=" um"),
        ParameterSpec("sample_height", "Sample Height", "Layout", 10000.0, minimum=1.0, maximum=100000.0, suffix=" um"),
        ParameterSpec("active_width", "Active Width", "Layout", 8000.0, minimum=1.0, maximum=100000.0, suffix=" um"),
        ParameterSpec("active_height", "Active Height", "Layout", 8000.0, minimum=1.0, maximum=100000.0, suffix=" um"),
        ParameterSpec("boundary_line_width", "Boundary Line Width", "Layout", 10.0, minimum=0.01, maximum=10000.0, suffix=" um"),
        ParameterSpec("mark_type", "Mark Type", "Mark", "cross", kind="choice", choices=[("cross", "cross"), ("bonecross", "bonecross"), ("chessboard", "chessboard")]),
        ParameterSpec("mark_size", "Mark Size", "Mark", 52.0, minimum=0.01, maximum=10000.0, suffix=" um"),
        ParameterSpec("mark_width", "Mark Width", "Mark", 10.0, minimum=0.01, maximum=10000.0, suffix=" um"),
        ParameterSpec("mark_pitch_x", "Pitch X", "Array", 500.0, minimum=0.01, maximum=100000.0, suffix=" um"),
        ParameterSpec("mark_pitch_y", "Pitch Y", "Array", 504.0, minimum=0.01, maximum=100000.0, suffix=" um"),
        ParameterSpec("label_interval", "Label Interval", "Array", 4, kind="int", minimum=1, maximum=1000),
        ParameterSpec("label_size", "Label Size", "Label", 40.0, minimum=0.01, maximum=10000.0, suffix=" um"),
        ParameterSpec("label_offset_x", "Label Offset X", "Label", 50.0, minimum=-100000.0, maximum=100000.0, suffix=" um"),
        ParameterSpec("label_offset_y", "Label Offset Y", "Label", 20.0, minimum=-100000.0, maximum=100000.0, suffix=" um"),
        ParameterSpec("user_name", "User Name", "Info", "GEMsLab UserName", kind="string"),
        ParameterSpec("info_text_size", "Info Text Size", "Info", 60.0, minimum=0.01, maximum=10000.0, suffix=" um"),
        ParameterSpec("info_text_offset_x", "Info Offset X", "Info", 20.0, minimum=-100000.0, maximum=100000.0, suffix=" um"),
        ParameterSpec("info_text_offset_y", "Info Offset Y", "Info", 250.0, minimum=-100000.0, maximum=100000.0, suffix=" um"),
        ParameterSpec("name", "Cell Name", "Output", "mark_array_sample", kind="string"),
        ParameterSpec("layer_mechanical", "Mechanical Layer", "Layers", (1, 0), kind="layer_choice"),
        ParameterSpec("layer_active", "Active Layer", "Layers", (2, 0), kind="layer_choice"),
        ParameterSpec("layer_mark", "Mark Layer", "Layers", (3, 0), kind="layer_choice"),
    ],
)


WRITEFIELD_TOOL = ToolSpec(
    key="writefield_mark",
    title="EBL Writefield Mark",
    generator=_generate_writefield_array,
    preview_layers=[
        ("mechanical", "Mechanical"),
        ("active", "Active"),
        ("mark", "Mark"),
        ("mark_frame", "Frame"),
        ("caliper", "Caliper"),
        ("auto_align", "Auto Align"),
        ("manual_align", "Manual Align"),
    ],
    layer_mapping={
        "mechanical": "layer_mechanical",
        "active": "layer_active",
        "mark": "layer_mark",
        "mark_frame": "layer_mark_frame",
        "caliper": "layer_caliper",
        "auto_align": "layer_auto_align",
        "manual_align": "layer_manual_align",
    },
    params=[
        ParameterSpec("sample_width", "Sample Width", "Layout", 10000.0, minimum=1.0, maximum=100000.0, suffix=" um"),
        ParameterSpec("sample_height", "Sample Height", "Layout", 10000.0, minimum=1.0, maximum=100000.0, suffix=" um"),
        ParameterSpec("active_width", "Active Width", "Layout", 7000.0, minimum=1.0, maximum=100000.0, suffix=" um"),
        ParameterSpec("active_height", "Active Height", "Layout", 7000.0, minimum=1.0, maximum=100000.0, suffix=" um"),
        ParameterSpec("writefield_size", "Writefield Size", "Layout", 1000.0, minimum=1.0, maximum=100000.0, suffix=" um"),
        ParameterSpec("mark_main_size", "Main Mark Size", "Center Mark", 80.0, minimum=0.01, maximum=10000.0, suffix=" um"),
        ParameterSpec("mark_main_width", "Main Mark Width", "Center Mark", 10.0, minimum=0.01, maximum=10000.0, suffix=" um"),
        ParameterSpec("mark_small_size", "Small Mark Size", "Center Mark", 15.0, minimum=0.01, maximum=10000.0, suffix=" um"),
        ParameterSpec("mark_small_width", "Small Mark Width", "Center Mark", 2.0, minimum=0.01, maximum=10000.0, suffix=" um"),
        ParameterSpec("mark_small_dist", "Small Mark Distance", "Center Mark", 50.0, minimum=0.01, maximum=10000.0, suffix=" um"),
        ParameterSpec("l_marker_length", "L Marker Length", "Center Mark", 100.0, minimum=0.01, maximum=10000.0, suffix=" um"),
        ParameterSpec("l_marker_width", "L Marker Width", "Center Mark", 5.0, minimum=0.01, maximum=10000.0, suffix=" um"),
        ParameterSpec("frame_width", "Frame Width", "Center Mark", 0.0, minimum=0.0, maximum=10000.0, suffix=" um", tooltip="Set 0 to use automatic frame width."),
        ParameterSpec("boundary_line_width", "Boundary Line Width", "Boundary", 10.0, minimum=0.01, maximum=10000.0, suffix=" um"),
        ParameterSpec("mark_offset_x", "Corner Offset X", "Boundary", 100.0, minimum=-100000.0, maximum=100000.0, suffix=" um"),
        ParameterSpec("mark_offset_y", "Corner Offset Y", "Boundary", 100.0, minimum=-100000.0, maximum=100000.0, suffix=" um"),
        ParameterSpec("global_mark_offset", "Global Mark Offset", "Global Mark", 200.0, minimum=0.0, maximum=100000.0, suffix=" um"),
        ParameterSpec("global_mark_main_size", "Global Main Size", "Global Mark", 400.0, minimum=0.01, maximum=10000.0, suffix=" um"),
        ParameterSpec("global_mark_main_width", "Global Main Width", "Global Mark", 10.0, minimum=0.01, maximum=10000.0, suffix=" um"),
        ParameterSpec("global_mark_small_size", "Global Small Size", "Global Mark", 50.0, minimum=0.01, maximum=10000.0, suffix=" um"),
        ParameterSpec("global_mark_small_width", "Global Small Width", "Global Mark", 4.0, minimum=0.01, maximum=10000.0, suffix=" um"),
        ParameterSpec("global_mark_small_dist", "Global Small Distance", "Global Mark", 175.0, minimum=0.01, maximum=10000.0, suffix=" um"),
        ParameterSpec("label_size", "Field Label Size", "Labels", 15.0, minimum=0.01, maximum=10000.0, suffix=" um"),
        ParameterSpec("label_offset_x", "Field Label Offset X", "Labels", -70.0, minimum=-100000.0, maximum=100000.0, suffix=" um"),
        ParameterSpec("label_offset_y", "Field Label Offset Y", "Labels", -75.0, minimum=-100000.0, maximum=100000.0, suffix=" um"),
        ParameterSpec("user_name", "User Name", "Info", "GEMsLab UserName", kind="string"),
        ParameterSpec("info_text_size", "Info Text Size", "Info", 50.0, minimum=0.01, maximum=10000.0, suffix=" um"),
        ParameterSpec("info_text_offset_x", "Info Offset X", "Info", -100.0, minimum=-100000.0, maximum=100000.0, suffix=" um"),
        ParameterSpec("info_text_offset_y", "Info Offset Y", "Info", -95.0, minimum=-100000.0, maximum=100000.0, suffix=" um"),
        ParameterSpec("info_text_line_width", "Info Text Line Width", "Info", 0.0, minimum=-1000.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("enable_caliper", "Enable Caliper", "Caliper", True, kind="bool"),
        ParameterSpec("caliper_width", "Caliper Width", "Caliper", 2.0, minimum=0.01, maximum=1000.0, suffix=" um"),
        ParameterSpec("caliper_top_right_pitch", "Top/Right Pitch", "Top/Right Caliper", 5.0, minimum=0.01, maximum=1000.0, suffix=" um"),
        ParameterSpec("caliper_top_right_num_side", "Top/Right Tick Count", "Top/Right Caliper", 10, kind="int", minimum=0, maximum=1000),
        ParameterSpec("caliper_top_right_tick_length", "Top/Right Tick Length", "Top/Right Caliper", 10.0, minimum=0.01, maximum=1000.0, suffix=" um"),
        ParameterSpec("caliper_top_right_center_length", "Top/Right Center Length", "Top/Right Caliper", 20.0, minimum=0.01, maximum=1000.0, suffix=" um"),
        ParameterSpec("caliper_bottom_left_pitch", "Bottom/Left Pitch", "Bottom/Left Caliper", 5.1, minimum=0.01, maximum=1000.0, suffix=" um"),
        ParameterSpec("caliper_bottom_left_num_side", "Bottom/Left Tick Count", "Bottom/Left Caliper", 10, kind="int", minimum=0, maximum=1000),
        ParameterSpec("caliper_bottom_left_tick_length", "Bottom/Left Tick Length", "Bottom/Left Caliper", 10.0, minimum=0.01, maximum=1000.0, suffix=" um"),
        ParameterSpec("caliper_bottom_left_center_length", "Bottom/Left Center Length", "Bottom/Left Caliper", 20.0, minimum=0.01, maximum=1000.0, suffix=" um"),
        ParameterSpec("enable_alignment_layers", "Enable Alignment Layers", "Alignment", True, kind="bool"),
        ParameterSpec("layer_mechanical", "Mechanical Layer", "Layers", (1, 0), kind="layer_choice"),
        ParameterSpec("layer_active", "Active Layer", "Layers", (2, 0), kind="layer_choice"),
        ParameterSpec("layer_mark", "Mark Layer", "Layers", (3, 0), kind="layer_choice"),
        ParameterSpec("layer_mark_frame", "Frame Layer", "Layers", (4, 0), kind="layer_choice"),
        ParameterSpec("layer_caliper", "Caliper Layer", "Layers", (5, 0), kind="layer_choice"),
        ParameterSpec("layer_auto_align", "Auto Align Layer", "Layers", (61, 0), kind="layer_choice"),
        ParameterSpec("layer_manual_align", "Manual Align Layer", "Layers", (63, 0), kind="layer_choice"),
    ],
)


_dialog_ref = None


def launch_nanomark_dialog():
    global _dialog_ref
    if _dialog_ref is None:
        _dialog_ref = NanoMarkDialog([WRITEFIELD_TOOL, MARK_ARRAY_TOOL])
    _dialog_ref.show()
    _dialog_ref.raise_()
    _dialog_ref.activateWindow()
