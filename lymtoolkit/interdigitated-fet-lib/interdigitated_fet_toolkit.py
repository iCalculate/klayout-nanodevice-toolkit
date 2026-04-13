import os
from dataclasses import dataclass

import pya
from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QBrush, QFont, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
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
        scene.clear()
        tool_spec.preview_renderer(scene, values, self._layer_visibility)
        item_bounds = scene.itemsBoundingRect()
        if item_bounds.isNull():
            item_bounds = QRectF(-50.0, -50.0, 100.0, 100.0)
        self._preview_bounds = item_bounds.adjusted(-20.0, -20.0, 20.0, 20.0)
        scene.setSceneRect(self._preview_bounds)
        if preserve_view and self._has_fitted_once:
            self.setTransform(saved_transform)
            self.centerOn(saved_center)
            return
        self.resetTransform()
        self.fitInView(self._preview_bounds, Qt.KeepAspectRatio)
        self._has_fitted_once = True

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
        self.preview_label = QLabel("Symbolic preview")
        self.layer_checks = [QCheckBox(), QCheckBox(), QCheckBox()]
        for checkbox in self.layer_checks:
            checkbox.setChecked(True)
            checkbox.toggled.connect(self._refresh_preview)

        self.preview_btn = QPushButton("Preview")
        self.preview_btn.clicked.connect(self._refit_preview)
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
        split.addWidget(self.scroll, 0)

        right = QVBoxLayout()
        right.addWidget(self.preview_label)
        layer_row = QHBoxLayout()
        layer_row.addWidget(QLabel("Layers"))
        for checkbox in self.layer_checks:
            layer_row.addWidget(checkbox)
        layer_row.addStretch(1)
        right.addLayout(layer_row)
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
        self._update_layer_controls(tool)
        self._refresh_preview()

    def _make_control(self, param):
        if param.kind == "string":
            text = QLineEdit()
            text.setText(str(param.default))
            text.textChanged.connect(self._refresh_preview)
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
            combo.currentIndexChanged.connect(self._refresh_preview)
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
            combo.currentIndexChanged.connect(self._refresh_preview)
            if param.tooltip:
                combo.setToolTip(param.tooltip)
            return combo

        if param.kind == "int":
            spin = QSpinBox()
            spin.setRange(int(param.minimum), int(param.maximum))
            spin.setSingleStep(1)
            spin.setValue(int(param.default))
            if param.tooltip:
                spin.setToolTip(param.tooltip)
            spin.valueChanged.connect(self._refresh_preview)
            return spin

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
            if param.kind == "string":
                values[param.key] = control.text()
            elif param.kind == "layer_choice":
                values[param.key] = control.currentData()
            elif param.kind == "choice":
                values[param.key] = control.currentData()
            else:
                values[param.key] = control.value()
        return values

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
        for idx, checkbox in enumerate(self.layer_checks):
            if idx < len(tool.preview_layers):
                _, label = tool.preview_layers[idx]
                checkbox.setText(label)
                checkbox.setChecked(True)
                checkbox.show()
            else:
                checkbox.hide()

    def _layer_visibility(self):
        tool = self._current_tool()
        return {
            key: self.layer_checks[idx].isChecked()
            for idx, (key, _) in enumerate(tool.preview_layers)
        }

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
        if tool.insert_params_builder is not None:
            params.update(tool.insert_params_builder(params))

        try:
            pcell_variant = layout.create_cell(tool.pcell_name, tool.library_name, params)
            if pcell_variant is None:
                raise RuntimeError("PCell variant creation returned None.")
            top_cell.insert(pya.CellInstArray(pcell_variant.cell_index(), pya.Trans()))
            lv.add_missing_layers()
            lv.zoom_fit()
        except Exception as exc:
            QMessageBox.critical(self, "Insert Failed", str(exc))


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


def render_interdigitated_fet(scene, values, visible_layers=None):
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


def render_gdsfactory_text(scene, values, visible_layers=None):
    visible_layers = visible_layers or {"text": True}
    if not visible_layers.get("text", True):
        return

    text = values["text"] or "Text"
    text_region = _preview_text_region(text, max(values["size_um"], 0.1))
    bbox = text_region.bbox()
    center_x = (bbox.left + bbox.right) * 0.001 / 2.0
    center_y = -(bbox.bottom + bbox.top) * 0.001 / 2.0
    dx = values["x"] - center_x
    dy = values["y"] - center_y

    path = QPainterPath()
    path.setFillRule(Qt.OddEvenFill)
    for polygon in text_region.each():
        hull = [QPointF(point.x * 0.001 + dx, -point.y * 0.001 + dy) for point in polygon.each_point_hull()]
        if len(hull) < 3:
            continue
        path.moveTo(hull[0])
        for pt in hull[1:]:
            path.lineTo(pt)
        path.closeSubpath()
        for hole_index in range(polygon.holes()):
            hole = [QPointF(point.x * 0.001 + dx, -point.y * 0.001 + dy) for point in polygon.each_point_hole(hole_index)]
            if len(hole) < 3:
                continue
            path.moveTo(hole[0])
            for pt in hole[1:]:
                path.lineTo(pt)
            path.closeSubpath()

    pen = QPen(QColor("#6cc0ff"), 0)
    brush = QBrush(QColor(108, 192, 255, 70))
    _draw_path(scene, path, pen, brush)


def _interdigitated_insert_params(_values):
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


def _preview_text_region(text, size_um):
    generator = pya.TextGenerator.default_generator()
    mag = float(size_um) / max(generator.dheight(), 1e-9)
    return generator.text(text, 0.001, mag, False, 0.0, 0.0, 0.0).merged()


INTERDIGITATED_FET_TOOL = ToolSpec(
    key="interdigitated_fet",
    title="Interdigitated FET",
    library_name="InterdigitatedFETLib",
    pcell_name="InterdigitatedFETPCell",
    preview_renderer=render_interdigitated_fet,
    preview_layers=[("channel", "Channel"), ("sd", "S/D"), ("gate", "Gate")],
    insert_params_builder=_interdigitated_insert_params,
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
    title="Text Label",
    library_name="InterdigitatedFETLib",
    pcell_name="GdsfactoryTextPCell",
    preview_renderer=render_gdsfactory_text,
    preview_layers=[("text", "Text")],
    insert_params_builder=_gdsfactory_text_insert_params,
    params=[
        ParameterSpec("text", "Text", "Txt", "Placement", "ABC123", kind="string", tooltip="Text rendered with gdsfactory."),
        ParameterSpec("x", "Center X", "Cx", "Placement", 0.0, minimum=-1000.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("y", "Center Y", "Cy", "Placement", 0.0, minimum=-1000.0, maximum=1000.0, suffix=" um"),
        ParameterSpec("size_um", "Text Size", "Htxt", "Geometry", 20.0, minimum=0.1, maximum=1000.0, suffix=" um"),
        ParameterSpec("layer_spec", "Layer", "L", "Layer", (10, 0), kind="layer_choice"),
    ],
)


def launch_toolkit_dialog():
    dlg = ToolkitDialog([INTERDIGITATED_FET_TOOL, GDSFACTORY_TEXT_TOOL])
    dlg.exec_()
