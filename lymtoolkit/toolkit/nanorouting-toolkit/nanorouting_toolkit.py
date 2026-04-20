import json
import os
import sys

import pya
from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QBrush, QFont, QPainter, QPainterPath, QPen, QPolygonF
from PyQt5.QtWidgets import (
    QAbstractItemView,
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
    QHeaderView,
    QSizePolicy,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
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
            and os.path.isdir(os.path.join(candidate, "utils"))
        ):
            return candidate
    return os.path.abspath(os.path.join(current, "..", "..", ".."))


ROOT_DIR = _discover_root_dir()
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config import LAYER_DEFINITIONS
from components.routing import Routing
from utils.geometry import GeometryUtils
from utils.routing_utils import RouteOverlapError


def _point_key(point):
    return (round(float(point[0]), 6), round(float(point[1]), 6))


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


class PointTableWidget(QWidget):
    def __init__(self, title, columns):
        super().__init__()
        self._change_handler = None
        self._expand_handler = None
        self._row_height_hint = 18
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(2)
        self.toggle_btn = QToolButton()
        self.toggle_btn.setText("▼")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(True)
        self.toggle_btn.clicked.connect(self._toggle_collapsed)
        self.title_label = QLabel(title)
        header_row.addWidget(self.toggle_btn, 0)
        header_row.addWidget(self.title_label, 1)
        layout.addLayout(header_row)

        self.content_widget = QWidget()
        self.content_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(2)
        self.table = QTableWidget(0, len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.horizontalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setDefaultSectionSize(self._row_height_hint)
        self.table.verticalHeader().setMinimumSectionSize(self._row_height_hint)
        self.table.verticalHeader().setMaximumSectionSize(self._row_height_hint)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        content_layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(2)
        add_btn = QPushButton("Add")
        remove_btn = QPushButton("Remove")
        clear_btn = QPushButton("Clear")
        self.reverse_btn = QPushButton("Reverse")
        self.pick_btn = QPushButton("Pick")
        self._button_row_buttons = [add_btn, remove_btn, clear_btn, self.reverse_btn, self.pick_btn]
        for button in self._button_row_buttons:
            button.setFixedHeight(22)
        add_btn.clicked.connect(self.add_row)
        remove_btn.clicked.connect(self.remove_selected_row)
        clear_btn.clicked.connect(self.clear_rows)
        self.reverse_btn.clicked.connect(self.reverse_rows)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addWidget(self.reverse_btn)
        btn_row.addWidget(self.pick_btn)
        btn_row.addStretch(1)
        content_layout.addLayout(btn_row)
        layout.addWidget(self.content_widget)

    def add_row(self, values=None):
        row = self.table.rowCount()
        self.table.insertRow(row)
        values = values or [0.0] * self.table.columnCount()
        for column, value in enumerate(values):
            item = QTableWidgetItem(f"{float(value):.3f}")
            self.table.setItem(row, column, item)
        self._notify_changed()

    def remove_selected_row(self):
        indexes = self.table.selectionModel().selectedRows()
        for index in reversed(indexes):
            self.table.removeRow(index.row())
        self._notify_changed()

    def clear_rows(self):
        self.table.setRowCount(0)
        self._notify_changed()

    def reverse_rows(self):
        rows = self.points()
        self.set_points(list(reversed(rows)))
        self._notify_changed()

    def set_pick_handler(self, handler):
        self.pick_btn.clicked.connect(handler)

    def set_change_handler(self, handler):
        self._change_handler = handler

    def set_expand_handler(self, handler):
        self._expand_handler = handler

    def _notify_changed(self):
        if self._change_handler is not None:
            self._change_handler()

    def _toggle_collapsed(self):
        expanded = self.toggle_btn.isChecked()
        self.toggle_btn.setText("▼" if expanded else "▶")
        self.content_widget.setVisible(expanded)
        if self._expand_handler is not None:
            self._expand_handler()

    def set_expanded(self, expanded):
        self.toggle_btn.setChecked(expanded)
        self._toggle_collapsed()

    def is_expanded(self):
        return self.toggle_btn.isChecked()

    def set_table_height(self, height):
        height = max(int(height), 42)
        self.table.setMinimumHeight(height)
        self.table.setMaximumHeight(height)

    def header_height(self):
        return max(self.toggle_btn.sizeHint().height(), self.title_label.sizeHint().height())

    def button_row_height(self):
        return max(button.height() for button in self._button_row_buttons)

    def minimum_table_height(self):
        return self._row_height_hint * 2 + 6

    def points(self):
        points = []
        for row in range(self.table.rowCount()):
            values = []
            for column in range(self.table.columnCount()):
                item = self.table.item(row, column)
                text = item.text().strip() if item is not None else ""
                if not text:
                    raise ValueError(f"Row {row + 1} has an empty value.")
                values.append(float(text))
            points.append(tuple(values))
        return points

    def set_points(self, points):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for point in points:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for column, value in enumerate(point):
                item = QTableWidgetItem(f"{float(value):.3f}")
                self.table.setItem(row, column, item)
        self.table.blockSignals(False)


class RectTableWidget(PointTableWidget):
    def rects(self):
        rects = []
        for x1, y1, x2, y2 in self.points():
            rects.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2})
        return rects

    def set_rects(self, rects):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for rect in rects:
            self.add_row([rect["x1"], rect["y1"], rect["x2"], rect["y2"]])
        self.table.blockSignals(False)


class RoutingPreviewView(QGraphicsView):
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
        painter.drawText(QRectF(x1, y - 18, bar_px + 8.0, 14.0), Qt.AlignLeft | Qt.AlignVCenter, _format_length(bar_um))

    def _scene_point(self, point):
        return QPointF(float(point[0]), -float(point[1]))

    def _scene_rect(self, rect):
        x1 = min(rect["x1"], rect["x2"])
        x2 = max(rect["x1"], rect["x2"])
        y1 = min(rect["y1"], rect["y2"])
        y2 = max(rect["y1"], rect["y2"])
        return QRectF(x1, -y2, x2 - x1, y2 - y1)

    def _polygon_from_shape(self, shape):
        polygon = shape.polygon() if hasattr(shape, "polygon") else shape
        points = []
        if hasattr(polygon, "each_point_hull"):
            for point in polygon.each_point_hull():
                points.append(
                    QPointF(
                        float(point.x) / GeometryUtils.UNIT_SCALE,
                        -float(point.y) / GeometryUtils.UNIT_SCALE,
                    )
                )
        return QPolygonF(points)

    def draw_error(self, message, starts=None, ends=None, obstacles=None, route_results=None):
        scene = self.scene()
        scene.clear()
        starts = starts or []
        ends = ends or []
        obstacles = obstacles or []
        self._draw_common(scene, starts, ends, obstacles)
        if route_results:
            fill_brush = QBrush(QColor(247, 201, 72, 55))
            edge_pen = QPen(QColor(255, 219, 99), 0)
            center_pen = QPen(QColor("#f7c948"), 0)
            for result in route_results:
                for shape in result.shapes:
                    polygon = self._polygon_from_shape(shape)
                    if not polygon.isEmpty():
                        scene.addPolygon(polygon, edge_pen, fill_brush)
                center_path = QPainterPath()
                if result.points:
                    center_path.moveTo(self._scene_point(result.points[0]))
                    for point in result.points[1:]:
                        center_path.lineTo(self._scene_point(point))
                    scene.addPath(center_path, center_pen)
        text_item = scene.addText("Routing blocked")
        text_item.setDefaultTextColor(QColor("#ff8c69"))
        text_item.setPos(-80.0, -15.0)
        detail = scene.addText(message[:300])
        detail.setDefaultTextColor(QColor("#f3f3f3"))
        detail.setPos(-140.0, 12.0)
        self._finalize(scene)

    def _draw_common(self, scene, starts, ends, obstacles):
        obstacle_pen = QPen(QColor("#ff7f50"), 0)
        obstacle_brush = QBrush(QColor(255, 127, 80, 45))
        for rect in obstacles:
            scene.addRect(self._scene_rect(rect), obstacle_pen, obstacle_brush)

        start_pen = QPen(QColor("#57cc99"), 0)
        end_pen = QPen(QColor("#4ea8de"), 0)
        marker_brush = QBrush(Qt.NoBrush)
        for index, point in enumerate(starts, start=1):
            sp = self._scene_point(point)
            scene.addRect(sp.x() - 3.0, sp.y() - 3.0, 6.0, 6.0, start_pen, marker_brush)
            label = scene.addText(str(index))
            label.setDefaultTextColor(QColor("#57cc99"))
            label.setFont(QFont("Segoe UI", 8, QFont.Bold))
            label.setPos(sp.x() + 5.0, sp.y() - 16.0)
        for index, point in enumerate(ends, start=1):
            sp = self._scene_point(point)
            scene.addRect(sp.x() - 3.0, sp.y() - 3.0, 6.0, 6.0, end_pen, marker_brush)
            label = scene.addText(str(index))
            label.setDefaultTextColor(QColor("#4ea8de"))
            label.setFont(QFont("Segoe UI", 8, QFont.Bold))
            label.setPos(sp.x() + 5.0, sp.y() + 2.0)

    def _finalize(self, scene):
        bounds = scene.itemsBoundingRect()
        if bounds.isNull():
            bounds = QRectF(-50.0, -50.0, 100.0, 100.0)
        self._bounds = bounds.adjusted(-20.0, -20.0, 20.0, 20.0)
        scene.setSceneRect(self._bounds)
        self.resetTransform()
        self.fitInView(self._bounds, Qt.KeepAspectRatio)

    def draw_routes(self, route_results, starts, ends, obstacles):
        scene = self.scene()
        scene.clear()
        self._draw_common(scene, starts, ends, obstacles)

        fill_brush = QBrush(QColor(247, 201, 72, 90))
        edge_pen = QPen(QColor(255, 219, 99), 0)
        center_pen = QPen(QColor("#f7c948"), 0)

        for result in route_results:
            for shape in result.shapes:
                polygon = self._polygon_from_shape(shape)
                if not polygon.isEmpty():
                    scene.addPolygon(polygon, edge_pen, fill_brush)

            center_path = QPainterPath()
            if result.points:
                center_path.moveTo(self._scene_point(result.points[0]))
                for point in result.points[1:]:
                    center_path.lineTo(self._scene_point(point))
                scene.addPath(center_path, center_pen)

        self._finalize(scene)


class NanoRoutingDialog(QDialog):
    PREVIEW_CELL_NAME = "__NANOROUTING_PREVIEW__"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NanoRouting")
        self.setMinimumHeight(520)
        self.resize(1180, 640)
        self._last_debug_payload = None
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        left_widget = QWidget()
        self.left_widget = left_widget
        left_widget.setMaximumWidth(252)
        left_panel = QVBoxLayout(left_widget)
        self.left_panel = left_panel
        left_panel.setContentsMargins(0, 0, 0, 0)
        left_panel.setSpacing(4)
        root.addWidget(left_widget, 0)

        mode_box = QGroupBox("Routing")
        self.mode_box = mode_box
        mode_form = QFormLayout(mode_box)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["single", "bundle"])
        self.route_mode_combo = QComboBox()
        self.route_mode_combo.addItems(["manhattan", "diagonal"])
        self.extension_combo = QComboBox()
        self.extension_combo.addItems(["flush", "half_width"])
        self.layer_combo = QComboBox()
        self.layer_combo.addItems(sorted(LAYER_DEFINITIONS.keys()))
        self.layer_combo.setCurrentText("routing")
        for widget in (self.mode_combo, self.route_mode_combo, self.extension_combo, self.layer_combo):
            widget.currentIndexChanged.connect(self._refresh_preview)
        mode_form.addRow("Mode", self.mode_combo)
        mode_form.addRow("Route mode", self.route_mode_combo)
        mode_form.addRow("Extension", self.extension_combo)
        mode_form.addRow("Layer", self.layer_combo)
        left_panel.addWidget(mode_box)

        param_box = QGroupBox("Parameters")
        self.param_box = param_box
        param_form = QFormLayout(param_box)
        self.line_width_spin = self._double_spin(2.0, 0.1, 1000.0, 3)
        self.min_line_width_spin = self._double_spin(2.0, 0.1, 1000.0, 3)
        self.bundle_spacing_spin = self._double_spin(6.0, 0.1, 1000.0, 3)
        self.clearance_spin = self._double_spin(2.0, 0.0, 1000.0, 3)
        for widget in (self.line_width_spin, self.min_line_width_spin, self.bundle_spacing_spin, self.clearance_spin):
            widget.valueChanged.connect(self._refresh_preview)
        param_form.addRow("Line width", self.line_width_spin)
        param_form.addRow("Min line width", self.min_line_width_spin)
        param_form.addRow("Bundle spacing", self.bundle_spacing_spin)
        param_form.addRow("Clearance", self.clearance_spin)
        left_panel.addWidget(param_box)

        self.starts_table = PointTableWidget("Start points", ["", ""])
        self.ends_table = PointTableWidget("End points", ["", ""])
        self.waypoints_table = PointTableWidget("Waypoints", ["", ""])
        self.obstacles_table = RectTableWidget("Obstacle rectangles", ["", "", "", ""])
        for table_widget in (self.starts_table, self.ends_table, self.waypoints_table, self.obstacles_table):
            table_widget.table.itemChanged.connect(self._refresh_preview)
            table_widget.set_change_handler(self._refresh_preview)
            table_widget.set_expand_handler(self._update_table_heights)
        self.starts_table.set_pick_handler(lambda: self._load_selection("starts"))
        self.ends_table.set_pick_handler(lambda: self._load_selection("ends"))
        self.waypoints_table.set_pick_handler(lambda: self._load_selection("waypoints"))
        self.obstacles_table.set_pick_handler(lambda: self._load_selection("obstacles"))
        self.starts_table.set_expanded(True)
        self.ends_table.set_expanded(True)
        self.waypoints_table.set_expanded(False)
        self.obstacles_table.set_expanded(False)
        left_panel.addWidget(self.starts_table)
        left_panel.addWidget(self.ends_table)
        left_panel.addWidget(self.waypoints_table)
        left_panel.addWidget(self.obstacles_table)
        self.compact_actions_widget = QWidget()
        compact_actions = QHBoxLayout(self.compact_actions_widget)
        compact_actions.setContentsMargins(0, 0, 0, 0)
        compact_actions.setSpacing(4)
        self.preview_markers_check = QCheckBox("Show start/end markers in layout preview")
        self.preview_markers_check.setChecked(True)
        compact_actions.addStretch(1)
        compact_actions.addWidget(self.preview_markers_check)
        left_panel.addWidget(self.compact_actions_widget)

        self.distribute_widget = QWidget()
        distribute_row = QHBoxLayout(self.distribute_widget)
        distribute_row.setContentsMargins(0, 0, 0, 0)
        distribute_row.setSpacing(4)
        self.distribute_x_btn = QPushButton("Distribute X")
        self.distribute_y_btn = QPushButton("Distribute Y")
        self.distribute_x_btn.setFixedHeight(24)
        self.distribute_y_btn.setFixedHeight(24)
        self.distribute_x_btn.clicked.connect(lambda: self._distribute_selected_objects("x"))
        self.distribute_y_btn.clicked.connect(lambda: self._distribute_selected_objects("y"))
        distribute_row.addWidget(self.distribute_x_btn)
        distribute_row.addWidget(self.distribute_y_btn)
        left_panel.addWidget(self.distribute_widget)
        left_panel.addStretch(1)
        self._table_widgets = [
            self.starts_table,
            self.ends_table,
            self.waypoints_table,
            self.obstacles_table,
        ]
        self._update_table_heights()

        right_panel = QVBoxLayout()
        right_panel.setSpacing(8)
        root.addLayout(right_panel, 1)
        right_panel.addWidget(QLabel("Preview"))
        self.preview = RoutingPreviewView()
        right_panel.addWidget(self.preview, 1)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #d7d7d7;")
        right_panel.addWidget(self.status_label)

        action_row = QHBoxLayout()
        self.import_btn = QPushButton("Import Config")
        self.export_btn = QPushButton("Export Config")
        self.export_debug_btn = QPushButton("Export Debug JSON")
        self.preview_btn = QPushButton("Refresh Preview")
        self.preview_layout_btn = QPushButton("Preview In Layout")
        self.clear_preview_btn = QPushButton("Clear Layout Preview")
        self.insert_btn = QPushButton("Insert")
        self.import_btn.clicked.connect(self._import_config)
        self.export_btn.clicked.connect(self._export_config)
        self.export_debug_btn.clicked.connect(self._export_debug_json)
        self.preview_btn.clicked.connect(self._refresh_preview)
        self.preview_layout_btn.clicked.connect(self._preview_in_layout)
        self.clear_preview_btn.clicked.connect(self._clear_layout_preview)
        self.insert_btn.clicked.connect(self._insert_routes)
        action_row.addWidget(self.import_btn)
        action_row.addWidget(self.export_btn)
        action_row.addWidget(self.export_debug_btn)
        action_row.addWidget(self.preview_btn)
        action_row.addWidget(self.preview_layout_btn)
        action_row.addWidget(self.clear_preview_btn)
        action_row.addWidget(self.insert_btn)
        right_panel.addLayout(action_row)

    def _double_spin(self, value, minimum, maximum, decimals):
        spin = QDoubleSpinBox()
        spin.setDecimals(decimals)
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        return spin

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_table_heights()

    def _update_table_heights(self):
        expanded_tables = [widget for widget in getattr(self, "_table_widgets", []) if widget.is_expanded()]
        if not expanded_tables or not hasattr(self, "left_widget"):
            return
        layout_spacing = self.left_panel.spacing() if hasattr(self, "left_panel") else 4
        fixed_height = 0
        fixed_height += self.mode_box.sizeHint().height()
        fixed_height += self.param_box.sizeHint().height()
        fixed_height += self.compact_actions_widget.sizeHint().height()
        fixed_height += self.distribute_widget.sizeHint().height()
        fixed_height += layout_spacing * (2 + len(self._table_widgets))
        for widget in self._table_widgets:
            fixed_height += widget.header_height()
            if widget.is_expanded():
                fixed_height += widget.button_row_height() + 2

        available_height = max(self.left_widget.height() - fixed_height, 0)
        per_table_height = max(
            min(widget.minimum_table_height() for widget in expanded_tables),
            int(available_height / max(len(expanded_tables), 1)),
        )
        for widget in self._table_widgets:
            if widget.is_expanded():
                widget.set_table_height(per_table_height)

    def _selected_objects(self):
        view = pya.LayoutView.current()
        if view is None:
            return []
        objects = []

        def add_objects(iterator):
            for obj in iterator:
                objects.append(obj)

        if view.has_object_selection():
            add_objects(view.each_object_selected())
        if hasattr(view, "has_transient_object_selection") and view.has_transient_object_selection():
            add_objects(view.each_object_selected_transient())
        if not objects and hasattr(view, "object_selection"):
            try:
                add_objects(view.object_selection)
            except Exception:
                pass
        return objects

    def _selected_shape_entries(self):
        entries = []
        seen = set()
        for obj in self._selected_objects():
            shape = getattr(obj, "shape", None)
            if shape is None or shape.is_null():
                continue
            box = shape.dbbox()
            try:
                trans = obj.dtrans() if callable(getattr(obj, "dtrans", None)) else obj.dtrans
                box = box.transformed(trans)
            except Exception:
                pass
            key = (
                round(float(box.left), 6),
                round(float(box.bottom), 6),
                round(float(box.right), 6),
                round(float(box.top), 6),
            )
            if key in seen:
                continue
            seen.add(key)
            entries.append({"obj": obj, "shape": shape, "box": box})
        return entries

    def _selected_boxes(self):
        boxes = []
        for entry in self._selected_shape_entries():
            boxes.append(entry["box"])
        return boxes

    def _move_shape_by(self, shape, dx_um, dy_um):
        dx_dbu = int(round(dx_um * GeometryUtils.UNIT_SCALE))
        dy_dbu = int(round(dy_um * GeometryUtils.UNIT_SCALE))
        if dx_dbu == 0 and dy_dbu == 0:
            return
        try:
            shape.transform(pya.Trans(dx_dbu, dy_dbu))
        except Exception:
            shape.transform(pya.ICplxTrans(1.0, 0.0, False, dx_dbu, dy_dbu))

    def _distribute_selected_objects(self, axis):
        entries = self._selected_shape_entries()
        if len(entries) < 3:
            QMessageBox.information(self, "NanoRouting", "Select at least 3 objects to distribute.")
            return

        center_getter = (lambda entry: float(entry["box"].center().x)) if axis == "x" else (lambda entry: float(entry["box"].center().y))
        ordered = sorted(entries, key=center_getter)
        first_center = center_getter(ordered[0])
        last_center = center_getter(ordered[-1])
        step = (last_center - first_center) / float(len(ordered) - 1)

        moved_count = 0
        for index, entry in enumerate(ordered[1:-1], start=1):
            target_center = first_center + index * step
            current_center = center_getter(entry)
            delta = target_center - current_center
            if abs(delta) < 1e-9:
                continue
            if axis == "x":
                self._move_shape_by(entry["shape"], delta, 0.0)
            else:
                self._move_shape_by(entry["shape"], 0.0, delta)
            moved_count += 1

        if moved_count == 0:
            self.status_label.setText("Selected objects already evenly distributed")
        else:
            self.status_label.setText(f"Distributed {moved_count} selected object(s) along {axis.upper()}")

    def _load_selection(self, target):
        boxes = self._selected_boxes()
        if not boxes:
            QMessageBox.information(self, "NanoRouting", "No selected layout objects found.")
            return

        if target in {"starts", "ends", "waypoints"}:
            centers = sorted(
                ((float(box.center().x), float(box.center().y)) for box in boxes),
                key=lambda item: (item[0], item[1]),
            )
            if target == "starts":
                self.starts_table.set_points(centers)
            elif target == "waypoints":
                self.waypoints_table.set_points(centers)
            else:
                self.ends_table.set_points(centers)
        else:
            rects = sorted(
                (
                    {
                        "x1": float(box.left),
                        "y1": float(box.bottom),
                        "x2": float(box.right),
                        "y2": float(box.top),
                    }
                    for box in boxes
                ),
                key=lambda item: (item["x1"], item["y1"], item["x2"], item["y2"]),
            )
            self.obstacles_table.set_rects(rects)
        self._refresh_preview()

    def _values(self):
        return {
            "mode": self.mode_combo.currentText(),
            "route_mode": self.route_mode_combo.currentText(),
            "extension_type": self.extension_combo.currentText(),
            "layer_name": self.layer_combo.currentText(),
            "line_width": self.line_width_spin.value(),
            "min_line_width": self.min_line_width_spin.value(),
            "bundle_spacing": self.bundle_spacing_spin.value(),
            "clearance": self.clearance_spin.value(),
            "starts": self.starts_table.points(),
            "ends": self.ends_table.points(),
            "waypoints": self.waypoints_table.points(),
            "obstacles": self.obstacles_table.rects(),
        }

    def _set_values(self, values):
        self.mode_combo.setCurrentText(values.get("mode", self.mode_combo.currentText()))
        self.route_mode_combo.setCurrentText(values.get("route_mode", self.route_mode_combo.currentText()))
        self.extension_combo.setCurrentText(values.get("extension_type", self.extension_combo.currentText()))
        self.layer_combo.setCurrentText(values.get("layer_name", self.layer_combo.currentText()))
        self.line_width_spin.setValue(float(values.get("line_width", self.line_width_spin.value())))
        self.min_line_width_spin.setValue(float(values.get("min_line_width", self.min_line_width_spin.value())))
        self.bundle_spacing_spin.setValue(float(values.get("bundle_spacing", self.bundle_spacing_spin.value())))
        self.clearance_spin.setValue(float(values.get("clearance", self.clearance_spin.value())))
        self.starts_table.set_points(values.get("starts", []))
        self.ends_table.set_points(values.get("ends", []))
        self.waypoints_table.set_points(values.get("waypoints", []))
        self.obstacles_table.set_rects(values.get("obstacles", []))

    def _export_config(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export NanoRouting Config",
            "nanorouting_config.json",
            "JSON Files (*.json)",
        )
        if not path:
            return
        try:
            values = self._values()
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(values, handle, indent=2)
            self.status_label.setText(f"Config exported: {path}")
        except Exception as exc:
            QMessageBox.warning(self, "NanoRouting", f"Failed to export config:\n{exc}")

    def _import_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import NanoRouting Config",
            "",
            "JSON Files (*.json)",
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                values = json.load(handle)
            self._set_values(values)
            self._refresh_preview()
            self.status_label.setText(f"Config imported: {path}")
        except Exception as exc:
            QMessageBox.warning(self, "NanoRouting", f"Failed to import config:\n{exc}")

    def _serialize_route_results(self, route_results):
        serialized = []
        for result in route_results or []:
            serialized.append(
                {
                    "points": [[float(point[0]), float(point[1])] for point in result.points],
                    "width": float(result.width),
                    "begin_extension": float(result.begin_extension),
                    "end_extension": float(result.end_extension),
                }
            )
        return serialized

    def _update_debug_payload(self, values, status, route_results=None, error=None):
        payload = {
            "values": values,
            "status": status,
            "routes": self._serialize_route_results(route_results),
        }
        if error is not None:
            payload["error"] = error
        self._last_debug_payload = payload

    def _export_debug_json(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export NanoRouting Debug JSON",
            "nanorouting_debug.json",
            "JSON Files (*.json)",
        )
        if not path:
            return
        try:
            if self._last_debug_payload is None:
                try:
                    values = self._values()
                except Exception:
                    values = {}
                self._update_debug_payload(values, "idle", route_results=[], error=None)
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(self._last_debug_payload, handle, indent=2)
            self.status_label.setText(f"Debug JSON exported: {path}")
        except Exception as exc:
            QMessageBox.warning(self, "NanoRouting", f"Failed to export debug JSON:\n{exc}")

    def _validate_values(self, values):
        starts = values["starts"]
        ends = values["ends"]
        waypoints = values["waypoints"]
        obstacles = values["obstacles"]

        if values["mode"] == "single":
            if len(starts) != 1 or len(ends) != 1:
                raise ValueError("Single mode requires exactly one start point and one end point.")
        else:
            if not starts or not ends:
                raise ValueError("Bundle mode requires at least one start point and one end point.")
            if len(starts) != len(ends):
                raise ValueError("Bundle mode requires the same number of start and end points.")

        grouped = [("start", starts), ("end", ends), ("waypoint", waypoints)]
        seen = {}
        for group_name, points in grouped:
            for index, point in enumerate(points, start=1):
                key = _point_key(point)
                if key in seen:
                    prev_group, prev_index = seen[key]
                    raise ValueError(f"Duplicate point detected between {prev_group} #{prev_index} and {group_name} #{index}.")
                seen[key] = (group_name, index)

        for group_name, points in grouped:
            for index, point in enumerate(points, start=1):
                for obstacle_index, rect in enumerate(obstacles, start=1):
                    x1 = min(rect["x1"], rect["x2"])
                    x2 = max(rect["x1"], rect["x2"])
                    y1 = min(rect["y1"], rect["y2"])
                    y2 = max(rect["y1"], rect["y2"])
                    if x1 <= point[0] <= x2 and y1 <= point[1] <= y2:
                        raise ValueError(f"{group_name.capitalize()} point #{index} is inside obstacle #{obstacle_index}.")

        for index, rect in enumerate(obstacles, start=1):
            if abs(rect["x2"] - rect["x1"]) < 1e-9 or abs(rect["y2"] - rect["y1"]) < 1e-9:
                raise ValueError(f"Obstacle #{index} has zero width or height.")

    def _build_results(self):
        values = self._values()
        self._validate_values(values)
        routing = Routing(layer_name=values["layer_name"])
        if values["mode"] == "single":
            result = routing.route(
                start=values["starts"][0],
                end=values["ends"][0],
                waypoints=values["waypoints"],
                line_width=values["line_width"],
                route_mode=values["route_mode"],
                avoid_regions=values["obstacles"],
                clearance=values["clearance"],
                extension_type=values["extension_type"],
            )
            return [result], values

        widths = [values["line_width"] for _ in values["starts"]]
        results = routing.route_parallel(
            start_points=values["starts"],
            end_points=values["ends"],
            shared_waypoints=values["waypoints"],
            line_width=widths,
            min_line_width=values["min_line_width"],
            bundle_spacing=values["bundle_spacing"],
            route_mode=values["route_mode"],
            avoid_regions=values["obstacles"],
            clearance=values["clearance"],
            extension_type=values["extension_type"],
        )
        return list(results), values

    def _refresh_preview(self):
        try:
            results, values = self._build_results()
            if not values["starts"] and not values["ends"] and not values["waypoints"] and not values["obstacles"]:
                self.preview.scene().clear()
                self.status_label.setText("")
                self._update_debug_payload(values, "idle", route_results=[])
                return
            self.preview.draw_routes(results, values["starts"], values["ends"], values["obstacles"])
            self.status_label.setText(f"Preview ready: {len(results)} route(s)")
            self._update_debug_payload(values, "ok", route_results=results)
        except RouteOverlapError as exc:
            try:
                values = self._values()
            except Exception:
                values = {"starts": [], "ends": [], "waypoints": [], "obstacles": []}
            self.preview.draw_error(
                str(exc),
                values.get("starts", []),
                values.get("ends", []),
                values.get("obstacles", []),
                route_results=getattr(exc, "results", None),
            )
            self.status_label.setText(f"Preview blocked: {exc}")
            self._update_debug_payload(
                values,
                "blocked",
                route_results=getattr(exc, "results", None),
                error={"type": exc.__class__.__name__, "message": str(exc)},
            )
        except Exception as exc:
            try:
                values = self._values()
            except Exception:
                values = {"starts": [], "ends": [], "obstacles": []}
            if not values.get("starts") and not values.get("ends") and not values.get("waypoints") and not values.get("obstacles"):
                self.preview.scene().clear()
                self.status_label.setText("")
                self._update_debug_payload(values, "idle", route_results=[])
                return
            self.preview.draw_error(str(exc), values.get("starts", []), values.get("ends", []), values.get("obstacles", []))
            self.status_label.setText(f"Preview blocked: {exc}")
            self._update_debug_payload(
                values,
                "blocked",
                route_results=[],
                error={"type": exc.__class__.__name__, "message": str(exc)},
            )

    def _current_layout_context(self):
        view = pya.LayoutView.current()
        if view is None:
            raise RuntimeError("No active KLayout LayoutView.")
        cv = view.active_cellview()
        if cv is None or cv.cell is None:
            raise RuntimeError("No active cell view.")
        return view, cv.layout(), cv.cell

    def _ensure_preview_cell(self, layout, top_cell):
        preview_cell = layout.create_cell(self.PREVIEW_CELL_NAME)
        try:
            preview_cell.clear()
        except Exception:
            pass

        has_instance = False
        try:
            for inst in top_cell.each_inst():
                inst_cell_index = inst.cell_index() if callable(getattr(inst, "cell_index", None)) else inst.cell_index
                if inst_cell_index == preview_cell.cell_index():
                    has_instance = True
                    break
        except Exception:
            pass

        if not has_instance:
            top_cell.insert(pya.CellInstArray(preview_cell.cell_index(), pya.Trans()))
        return preview_cell

    def _draw_markers_and_obstacles(self, routing, cell, values):
        if self.preview_markers_check.isChecked():
            for point in values["starts"] + values["ends"]:
                routing.insert_box_marker(cell, point, size=max(values["line_width"] * 2.0, 4.0))
        for rect in values["obstacles"]:
            routing.insert_obstacle_box(
                cell,
                center=((rect["x1"] + rect["x2"]) / 2.0, (rect["y1"] + rect["y2"]) / 2.0),
                width=abs(rect["x2"] - rect["x1"]),
                height=abs(rect["y2"] - rect["y1"]),
            )

    def _error_anchor(self, values):
        coords = list(values.get("starts", [])) + list(values.get("ends", [])) + list(values.get("waypoints", []))
        for rect in values.get("obstacles", []):
            coords.append(((rect["x1"] + rect["x2"]) / 2.0, (rect["y1"] + rect["y2"]) / 2.0))
        if not coords:
            return (0.0, 0.0)
        return (min(point[0] for point in coords), max(point[1] for point in coords) + 20.0)

    def _show_layout_error(self, layout, top_cell, values, message):
        routing = Routing(layout=layout, layer_name=values["layer_name"] if "layer_name" in values else "routing")
        preview_cell = self._ensure_preview_cell(layout, top_cell)
        self._draw_markers_and_obstacles(routing, preview_cell, values)
        anchor = self._error_anchor(values)
        routing.insert_note_text(preview_cell, f"NanoRouting error: {message}", anchor[0], anchor[1])

    def _preview_in_layout(self):
        try:
            results, values = self._build_results()
            view, layout, top_cell = self._current_layout_context()
            routing = Routing(layout=layout, layer_name=values["layer_name"])
            preview_cell = self._ensure_preview_cell(layout, top_cell)
            self._draw_markers_and_obstacles(routing, preview_cell, values)
            if values["mode"] == "single":
                routing.insert_route(
                    preview_cell,
                    start=values["starts"][0],
                    end=values["ends"][0],
                    waypoints=values["waypoints"],
                    line_width=values["line_width"],
                    route_mode=values["route_mode"],
                    avoid_regions=values["obstacles"],
                    clearance=values["clearance"],
                    extension_type=values["extension_type"],
                )
            else:
                widths = [values["line_width"] for _ in values["starts"]]
                routing.insert_parallel_routes(
                    preview_cell,
                    start_points=values["starts"],
                    end_points=values["ends"],
                    shared_waypoints=values["waypoints"],
                    line_width=widths,
                    min_line_width=values["min_line_width"],
                    bundle_spacing=values["bundle_spacing"],
                    route_mode=values["route_mode"],
                    avoid_regions=values["obstacles"],
                    clearance=values["clearance"],
                    extension_type=values["extension_type"],
                )
            view.add_missing_layers()
            view.zoom_fit()
            self.status_label.setText(f"Layout preview updated: {len(results)} route(s)")
        except Exception as exc:
            try:
                values = self._values()
                _view, layout, top_cell = self._current_layout_context()
                self._show_layout_error(layout, top_cell, values, str(exc))
            except Exception:
                pass
            QMessageBox.critical(self, "Preview Failed", str(exc))

    def _clear_layout_preview(self):
        try:
            _view, layout, _top_cell = self._current_layout_context()
            preview_cell = layout.create_cell(self.PREVIEW_CELL_NAME)
            preview_cell.clear()
            self.status_label.setText("Layout preview cleared")
        except Exception as exc:
            QMessageBox.critical(self, "Clear Preview Failed", str(exc))

    def _insert_routes(self):
        try:
            _results, values = self._build_results()
            view, layout, top_cell = self._current_layout_context()
            routing = Routing(layout=layout, layer_name=values["layer_name"])
            if values["mode"] == "single":
                routing.insert_route(
                    top_cell,
                    start=values["starts"][0],
                    end=values["ends"][0],
                    waypoints=values["waypoints"],
                    line_width=values["line_width"],
                    route_mode=values["route_mode"],
                    avoid_regions=values["obstacles"],
                    clearance=values["clearance"],
                    extension_type=values["extension_type"],
                )
            else:
                widths = [values["line_width"] for _ in values["starts"]]
                routing.insert_parallel_routes(
                    top_cell,
                    start_points=values["starts"],
                    end_points=values["ends"],
                    shared_waypoints=values["waypoints"],
                    line_width=widths,
                    min_line_width=values["min_line_width"],
                    bundle_spacing=values["bundle_spacing"],
                    route_mode=values["route_mode"],
                    avoid_regions=values["obstacles"],
                    clearance=values["clearance"],
                    extension_type=values["extension_type"],
                )
            view.add_missing_layers()
            self.status_label.setText("Routes inserted into active cell")
        except Exception as exc:
            try:
                values = self._values()
                _view, layout, top_cell = self._current_layout_context()
                self._show_layout_error(layout, top_cell, values, str(exc))
            except Exception:
                pass
            QMessageBox.critical(self, "Insert Failed", str(exc))


_dialog_ref = None


def launch_nanorouting_dialog():
    global _dialog_ref
    if _dialog_ref is None:
        _dialog_ref = NanoRoutingDialog()
    _dialog_ref.show()
    _dialog_ref.raise_()
    _dialog_ref.activateWindow()
