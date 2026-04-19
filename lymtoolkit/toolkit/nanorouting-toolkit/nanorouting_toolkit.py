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
    QFormLayout,
    QGraphicsScene,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(QLabel(title))
        self.table = QTableWidget(0, len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.horizontalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setMinimumHeight(72)
        self.table.setMaximumHeight(108)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(4)
        add_btn = QPushButton("Add")
        remove_btn = QPushButton("Remove")
        clear_btn = QPushButton("Clear")
        self.pick_btn = QPushButton("Pick")
        add_btn.clicked.connect(self.add_row)
        remove_btn.clicked.connect(self.remove_selected_row)
        clear_btn.clicked.connect(self.clear_rows)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addWidget(self.pick_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

    def add_row(self, values=None):
        row = self.table.rowCount()
        self.table.insertRow(row)
        values = values or [0.0] * self.table.columnCount()
        for column, value in enumerate(values):
            item = QTableWidgetItem(f"{float(value):.3f}")
            self.table.setItem(row, column, item)

    def remove_selected_row(self):
        indexes = self.table.selectionModel().selectedRows()
        for index in reversed(indexes):
            self.table.removeRow(index.row())

    def clear_rows(self):
        self.table.setRowCount(0)

    def set_pick_handler(self, handler):
        self.pick_btn.clicked.connect(handler)

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
            self.add_row(point)
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

    def draw_error(self, message, starts=None, ends=None, obstacles=None):
        scene = self.scene()
        scene.clear()
        starts = starts or []
        ends = ends or []
        obstacles = obstacles or []
        self._draw_common(scene, starts, ends, obstacles)
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
        for point in starts:
            sp = self._scene_point(point)
            scene.addRect(sp.x() - 3.0, sp.y() - 3.0, 6.0, 6.0, start_pen, marker_brush)
        for point in ends:
            sp = self._scene_point(point)
            scene.addRect(sp.x() - 3.0, sp.y() - 3.0, 6.0, 6.0, end_pen, marker_brush)

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
        self.resize(1180, 780)
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        left_widget = QWidget()
        left_widget.setMaximumWidth(360)
        left_panel = QVBoxLayout(left_widget)
        left_panel.setContentsMargins(0, 0, 0, 0)
        left_panel.setSpacing(8)
        root.addWidget(left_widget, 0)

        mode_box = QGroupBox("Routing")
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
        self.starts_table.set_pick_handler(lambda: self._load_selection("starts"))
        self.ends_table.set_pick_handler(lambda: self._load_selection("ends"))
        self.waypoints_table.set_pick_handler(lambda: self._load_selection("waypoints"))
        self.obstacles_table.set_pick_handler(lambda: self._load_selection("obstacles"))
        left_panel.addWidget(self.starts_table, 1)
        left_panel.addWidget(self.ends_table, 1)
        left_panel.addWidget(self.waypoints_table, 1)
        left_panel.addWidget(self.obstacles_table, 1)
        compact_actions = QHBoxLayout()
        compact_actions.setContentsMargins(0, 0, 0, 0)
        compact_actions.setSpacing(6)
        self.swap_btn = QPushButton("Swap Starts / Ends")
        self.swap_btn.clicked.connect(self._swap_points)
        compact_actions.addWidget(self.swap_btn)
        compact_actions.addStretch(1)
        self.preview_markers_check = QCheckBox("Show start/end markers in layout preview")
        self.preview_markers_check.setChecked(True)
        compact_actions.addWidget(self.preview_markers_check)
        left_panel.addLayout(compact_actions)

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
        self.preview_btn = QPushButton("Refresh Preview")
        self.preview_layout_btn = QPushButton("Preview In Layout")
        self.clear_preview_btn = QPushButton("Clear Layout Preview")
        self.insert_btn = QPushButton("Insert")
        self.preview_btn.clicked.connect(self._refresh_preview)
        self.preview_layout_btn.clicked.connect(self._preview_in_layout)
        self.clear_preview_btn.clicked.connect(self._clear_layout_preview)
        self.insert_btn.clicked.connect(self._insert_routes)
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

    def _swap_points(self):
        starts = self.starts_table.points()
        ends = self.ends_table.points()
        self.starts_table.set_points(ends)
        self.ends_table.set_points(starts)
        self._refresh_preview()

    def _selected_objects(self):
        view = pya.LayoutView.current()
        if view is None or not view.has_object_selection():
            return []
        return list(view.each_object_selected())

    def _selected_boxes(self):
        boxes = []
        for obj in self._selected_objects():
            shape = obj.shape
            if shape is None or shape.is_null():
                continue
            box = shape.dbbox()
            try:
                trans = obj.dtrans() if callable(getattr(obj, "dtrans", None)) else obj.dtrans
                box = box.transformed(trans)
            except Exception:
                pass
            boxes.append(box)
        return boxes

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
                return
            self.preview.draw_routes(results, values["starts"], values["ends"], values["obstacles"])
            self.status_label.setText(f"Preview ready: {len(results)} route(s)")
        except Exception as exc:
            try:
                values = self._values()
            except Exception:
                values = {"starts": [], "ends": [], "obstacles": []}
            if not values.get("starts") and not values.get("ends") and not values.get("waypoints") and not values.get("obstacles"):
                self.preview.scene().clear()
                self.status_label.setText("")
                return
            self.preview.draw_error(str(exc), values.get("starts", []), values.get("ends", []), values.get("obstacles", []))
            self.status_label.setText(f"Preview blocked: {exc}")

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
