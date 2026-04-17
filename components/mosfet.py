# -*- coding: utf-8 -*-
"""
MOSFET component based on the FET pad/fanout layout style.

Compared with components/fet.py, this implementation keeps:
- source/drain fanout structure similar to FET
- a single bottom-gate electrode
- a single top-gate electrode
- MOSFET-specific layer placement and a simplified GUI-facing API
"""

import os
import sys
from datetime import datetime

print("[mosfet.py] bootstrap: starting module import", flush=True)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

_db = None
try:
    import klayout.db as _db
except ImportError as e:
    if "tlcore" in str(e) or "klayout" in str(e).lower():
        print("Error: klayout may not support this Python version.")
        print("Use either KLayout macro runtime, or a Python environment with `pip install klayout`.")
    raise

try:
    import pya
except ImportError:
    pya = _db
    sys.modules["pya"] = _db

from config import LAYER_DEFINITIONS, PROCESS_CONFIG, get_gds_path
from utils.fanout_utils import draw_pad, draw_trapezoidal_fanout
from utils.geometry import GeometryUtils
from utils.mark_utils import MarkUtils


_GF_CACHE = None
_GF_IMPORT_ATTEMPTED = False


def _get_gdsfactory():
    global _GF_CACHE, _GF_IMPORT_ATTEMPTED
    if _GF_IMPORT_ATTEMPTED:
        return _GF_CACHE
    _GF_IMPORT_ATTEMPTED = True
    try:
        import gdsfactory as gf
        _GF_CACHE = gf
    except Exception:
        _GF_CACHE = None
    return _GF_CACHE


class MOSFET:
    """MOSFET geometry builder for the lymtoolkit GUI."""

    def __init__(
        self,
        x=0.0,
        y=0.0,
        channel_width=5.0,
        channel_length=20.0,
        gate_overlap=2.0,
        device_label="D1",
        device_id=1,
        fanout_enabled=True,
        fanout_direction="horizontal",
        enable_bottom_gate=True,
        enable_top_gate=True,
        enable_source_drain=True,
        show_device_labels=True,
        show_parameter_labels=True,
        show_alignment_marks=True,
        **kwargs,
    ):
        self.x = float(x)
        self.y = float(y)
        self.channel_width = float(channel_width)
        self.channel_length = float(channel_length)
        self.gate_overlap = float(gate_overlap)
        self.channel_type = str(kwargs.get("channel_type", "p")).lower()
        self.device_label = device_label
        self.device_id = device_id

        self.fanout_enabled = fanout_enabled
        self.fanout_direction = fanout_direction
        self.enable_bottom_gate = enable_bottom_gate
        self.enable_top_gate = enable_top_gate
        self.enable_source_drain = enable_source_drain
        self.show_device_labels = show_device_labels
        self.show_parameter_labels = show_parameter_labels
        self.show_alignment_marks = show_alignment_marks

        # Geometry defaults aligned with the FET implementation style.
        self.outer_pad_size = kwargs.get("outer_pad_size", 80.0)
        self.chamfer_size = kwargs.get("chamfer_size", 10.0)

        self.channel_extension_ratio = kwargs.get("channel_extension_ratio", 3.0)
        self.dielectric_extension_ratio = kwargs.get("dielectric_extension_ratio", 2.0)
        self.dielectric_margin = kwargs.get("dielectric_margin", 2.0 * self.gate_overlap)

        self.source_drain_inner_width_ratio = kwargs.get("source_drain_inner_width_ratio", 1.2)
        self.source_drain_outer_offset_x = kwargs.get("source_drain_outer_offset_x", 110.0)
        self.source_drain_outer_offset_y = kwargs.get("source_drain_outer_offset_y", 0.0)
        self.source_drain_inner_chamfer = kwargs.get("source_drain_inner_chamfer", "none")
        self.source_drain_outer_chamfer = kwargs.get("source_drain_outer_chamfer", "straight")

        self.bottom_gate_inner_width_ratio = kwargs.get("bottom_gate_inner_width_ratio", 1.5)
        self.bottom_gate_outer_offset_x = kwargs.get("bottom_gate_outer_offset_x", 0.0)
        self.bottom_gate_outer_offset_y = kwargs.get("bottom_gate_outer_offset_y", -100.0)
        self.bottom_gate_inner_chamfer = kwargs.get("bottom_gate_inner_chamfer", "none")
        self.bottom_gate_outer_chamfer = kwargs.get("bottom_gate_outer_chamfer", "straight")

        self.top_gate_inner_width_ratio = kwargs.get("top_gate_inner_width_ratio", 1.2)
        self.top_gate_outer_offset_x = kwargs.get("top_gate_outer_offset_x", 0.0)
        self.top_gate_outer_offset_y = kwargs.get("top_gate_outer_offset_y", 100.0)
        self.top_gate_inner_chamfer = kwargs.get("top_gate_inner_chamfer", "none")
        self.top_gate_outer_chamfer = kwargs.get("top_gate_outer_chamfer", "straight")

        self.mark_size = kwargs.get("mark_size", 8.0)
        self.mark_margin_x = kwargs.get("mark_margin_x", 30.0)
        self.mark_margin_y = kwargs.get("mark_margin_y", 30.0)
        self.device_region_margin_x = kwargs.get("device_region_margin_x", 20.0)
        self.device_region_margin_y = kwargs.get("device_region_margin_y", 20.0)
        self.mark_width = kwargs.get("mark_width", max(self.mark_size * 0.12, 0.5))
        self.mark_types = [
            kwargs.get("mark_type_1", "double_square"),
            kwargs.get("mark_type_2", "L_shape"),
            kwargs.get("mark_type_3", "L_shape"),
            kwargs.get("mark_type_4", "L_shape"),
        ]
        self.mark_rotations = [
            int(kwargs.get("mark_rotation_1", 0)),
            int(kwargs.get("mark_rotation_2", 0)),
            int(kwargs.get("mark_rotation_3", 180)),
            int(kwargs.get("mark_rotation_4", 270)),
        ]
        self.label_font = kwargs.get("label_font", "C:/Windows/Fonts/OCRAEXT.TTF")
        self.label_size = kwargs.get("label_size", 14.0)
        self.label_anchor = kwargs.get("label_anchor", "left_bottom")
        self.label_offset_x = kwargs.get("label_offset_x", 0.0)
        self.label_offset_y = kwargs.get("label_offset_y", 0.0)

        self.shapes = {
            "channel": [],
            "bottom_dielectric": [],
            "top_dielectric": [],
            "device_label": [],
            "parameter_labels": [],
            "alignment_marks": [],
        }
        self._component_shapes = {
            "bottom_gate": [],
            "source": [],
            "drain": [],
            "top_gate": [],
        }

    def _box_um(self, x_um, y_um, w_um, h_um, center=True):
        return GeometryUtils.create_rectangle(x_um, y_um, w_um, h_um, center=center)

    @staticmethod
    def _log_info(message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        reset = "\033[0m"
        bright_cyan = "\033[96m"
        bright_yellow = "\033[93m"
        bright_magenta = "\033[95m"
        bright_white = "\033[97m"
        print(
            f"{bright_cyan}{timestamp}{reset} | "
            f"{bright_yellow}INFO{reset}     | "
            f"{bright_magenta}components/mosfet.py{reset} - "
            f"{bright_white}{message}{reset}",
            flush=True,
        )

    def _channel_layer_id(self):
        return 13 if self.channel_type.startswith("n") else 14

    def _contact_layer_id(self):
        return 15 if self.channel_type.startswith("n") else 16

    def get_layer_ids(self):
        return {
            "channel": self._channel_layer_id(),
            "bottom_dielectric": 12,
            "top_dielectric": LAYER_DEFINITIONS["top_dielectric"]["id"],
            "bottom_gate": LAYER_DEFINITIONS["bottom_gate"]["id"],
            "source": self._contact_layer_id(),
            "drain": self._contact_layer_id(),
            "top_gate": LAYER_DEFINITIONS["top_gate"]["id"],
            "device_label": LAYER_DEFINITIONS["alignment_layer1"]["id"],
            "parameter_labels": LAYER_DEFINITIONS["alignment_layer1"]["id"],
            "alignment_marks": LAYER_DEFINITIONS["alignment_layer1"]["id"],
        }

    def _single_gate_inner_length(self):
        return self.channel_length + 2.0 * self.gate_overlap

    def _single_gate_inner_width(self, width_ratio):
        return self.channel_width * width_ratio

    def _append_sd_shapes(self, name, inner_center, outer_center):
        self._log_info(f"Building {name} inner pad at {inner_center} and outer pad at {outer_center}")
        inner_pad = draw_pad(
            center=inner_center,
            length=self.channel_length,
            width=self.channel_width * self.source_drain_inner_width_ratio,
            chamfer_size=0 if self.source_drain_inner_chamfer == "none" else self.chamfer_size,
            chamfer_type=self.source_drain_inner_chamfer,
        )
        self._component_shapes[name].append(inner_pad.polygon)

        if not self.fanout_enabled:
            return

        outer_pad = draw_pad(
            center=outer_center,
            length=self.outer_pad_size,
            width=self.outer_pad_size,
            chamfer_size=0 if self.source_drain_outer_chamfer == "none" else self.chamfer_size,
            chamfer_type=self.source_drain_outer_chamfer,
        )
        self._component_shapes[name].append(outer_pad.polygon)
        self._component_shapes[name].append(draw_trapezoidal_fanout(inner_pad, outer_pad))

    def _append_single_gate(self, layer_name, outer_offset_x, outer_offset_y, width_ratio, inner_chamfer, outer_chamfer):
        self._log_info(
            f"Building {layer_name} with inner width ratio={width_ratio}, outer offset=({outer_offset_x}, {outer_offset_y})"
        )
        inner_pad = draw_pad(
            center=(self.x, self.y),
            length=self._single_gate_inner_length(),
            width=self._single_gate_inner_width(width_ratio),
            chamfer_size=0 if inner_chamfer == "none" else self.chamfer_size,
            chamfer_type=inner_chamfer,
        )
        self._component_shapes[layer_name].append(inner_pad.polygon)

        if not self.fanout_enabled:
            return

        outer_pad = draw_pad(
            center=(self.x + outer_offset_x, self.y + outer_offset_y),
            length=self.outer_pad_size,
            width=self.outer_pad_size,
            chamfer_size=0 if outer_chamfer == "none" else self.chamfer_size,
            chamfer_type=outer_chamfer,
        )
        self._component_shapes[layer_name].append(outer_pad.polygon)
        self._component_shapes[layer_name].append(draw_trapezoidal_fanout(inner_pad, outer_pad))

    def _append_text_shape(self, text, x, y):
        if not text:
            return []
        text = str(text)
        self._log_info(f"Generating label text '{text}' at ({x}, {y})")

        gf = _get_gdsfactory()
        if gf is not None:
            try:
                self._log_info(f"Using gdsfactory text for '{text}'")
                text_component = gf.components.text(
                    text=text,
                    size=self.label_size,
                    justify="left",
                    layer=(self.get_layer_ids()["device_label"], 0),
                )
                bbox = text_component.bbox
                offset_x = x - float(bbox[0][0])
                offset_y = y - float(bbox[0][1])
                polygons = []
                for polygon in text_component.get_polygons():
                    points = [pya.Point(int(px + offset_x), int(py + offset_y)) for px, py in polygon]
                    if len(points) >= 3:
                        polygons.append(pya.Polygon(points))
                if polygons:
                    self._log_info(f"gdsfactory text generated {len(polygons)} polygons for '{text}'")
                    return polygons
            except Exception:
                self._log_info(f"gdsfactory text failed for '{text}', falling back to KLayout text generator")

        try:
            self._log_info(f"Using KLayout text generator for '{text}'")
            generator = pya.TextGenerator.default_generator()
            mag = float(self.label_size) / max(generator.dheight(), 1e-9)
            region = generator.text(text, PROCESS_CONFIG["dbu"], mag, False, 0.0, 0.0, 0.0).merged()
            bbox = region.bbox()
            dx = int(round(x / PROCESS_CONFIG["dbu"] - bbox.left))
            dy = int(round(y / PROCESS_CONFIG["dbu"] - bbox.bottom))
            self._log_info(f"KLayout text generator succeeded for '{text}'")
            return [region.moved(dx, dy)]
        except Exception:
            self._log_info(f"KLayout text generator failed for '{text}', falling back to raw pya.Text")
            return [pya.Text(text, int(x * 1000), int(y * 1000))]

    def _double_square_mark(self, cx, cy, size):
        ring = max(self.mark_width, size * 0.12)
        gap = max(ring, size * 0.10)
        outer = pya.Region(self._box_um(cx, cy, size, size, center=True))
        outer_void = pya.Region(self._box_um(cx, cy, max(size - 2.0 * ring, ring), max(size - 2.0 * ring, ring), center=True))
        outer_frame = outer - outer_void

        inner_size = max(size - 2.0 * (ring + gap), 2.0 * ring)
        inner = pya.Region(self._box_um(cx, cy, inner_size, inner_size, center=True))
        inner_void = pya.Region(self._box_um(cx, cy, max(inner_size - 2.0 * ring, ring), max(inner_size - 2.0 * ring, ring), center=True))
        inner_frame = inner - inner_void
        return outer_frame + inner_frame

    def _shape_bbox(self, shape):
        if isinstance(shape, pya.Box):
            return shape
        if hasattr(shape, "bbox"):
            return shape.bbox()
        return None

    def _compute_active_bbox(self):
        self._log_info("Computing active bounding box")
        boxes = []
        for key in ("channel", "bottom_dielectric", "top_dielectric"):
            for shape in self.shapes.get(key, []):
                box = self._shape_bbox(shape)
                if box is not None:
                    boxes.append(box)
        for shapes in self._component_shapes.values():
            for shape in shapes:
                box = self._shape_bbox(shape)
                if box is not None:
                    boxes.append(box)
        if not boxes:
            return None
        left = min(box.left for box in boxes)
        bottom = min(box.bottom for box in boxes)
        right = max(box.right for box in boxes)
        top = max(box.top for box in boxes)
        self._log_info(
            f"Active bounding box = ({left / 1000.0}, {bottom / 1000.0}) to ({right / 1000.0}, {top / 1000.0}) um"
        )
        return pya.Box(left, bottom, right, top)

    def _create_alignment_mark_shapes(self, region_bbox):
        self._log_info(
            "Generating alignment marks for region "
            f"({region_bbox.left / 1000.0}, {region_bbox.bottom / 1000.0}) to ({region_bbox.right / 1000.0}, {region_bbox.top / 1000.0}) um"
        )
        shapes = []
        left_um = region_bbox.left / 1000.0
        right_um = region_bbox.right / 1000.0
        top_um = region_bbox.top / 1000.0
        bottom_um = region_bbox.bottom / 1000.0
        center_positions = [
            (left_um + self.mark_size / 2.0, top_um - self.mark_size / 2.0),
            (right_um - self.mark_size / 2.0, top_um - self.mark_size / 2.0),
            (left_um + self.mark_size / 2.0, bottom_um + self.mark_size / 2.0),
            (right_um - self.mark_size / 2.0, bottom_um + self.mark_size / 2.0),
        ]
        corner_positions = [
            (left_um, top_um),
            (right_um, top_um),
            (left_um, bottom_um),
            (right_um, bottom_um),
        ]
        for idx in range(4):
            mark_type = self.mark_types[idx] if idx < len(self.mark_types) else "square"
            rotation_deg = self.mark_rotations[idx] if idx < len(self.mark_rotations) else 0
            rotation = (rotation_deg // 90) % 4
            cx, cy = center_positions[idx]
            px, py = corner_positions[idx]
            self._log_info(
                f"Creating mark {idx + 1}: type={mark_type}, rotation_deg={rotation_deg}, center=({cx}, {cy}), corner=({px}, {py})"
            )
            if mark_type == "cross":
                mark = MarkUtils.cross(cx, cy, self.mark_size, self.mark_width)
            elif mark_type == "square":
                mark = MarkUtils.square(cx, cy, self.mark_size)
            elif mark_type == "circle":
                mark = MarkUtils.circle(cx, cy, self.mark_size)
            elif mark_type == "diamond":
                mark = MarkUtils.diamond(cx, cy, self.mark_size)
            elif mark_type == "triangle":
                mark = MarkUtils.triangle(cx, cy, self.mark_size, "up")
            elif mark_type in ("double_square", "chessy"):
                mark = self._double_square_mark(cx, cy, self.mark_size)
            elif mark_type == "L_shape":
                mark = MarkUtils.l_shape(px, py, self.mark_size, ratio=self.mark_width / max(self.mark_size, 1e-6), arm_ratio=0.6)
            elif mark_type == "T_shape":
                mark = MarkUtils.t_shape(cx, cy, self.mark_size, ratio=self.mark_width / max(self.mark_size, 1e-6), arm_ratio=0.6)
            elif mark_type == "sq_missing":
                mark = MarkUtils.sq_missing(cx, cy, self.mark_size, missing=(2, 4))
            elif mark_type == "cross_tri":
                mark = MarkUtils.cross_tri(cx, cy, self.mark_size, ratio=max(self.mark_width / max(self.mark_size, 1e-6), 0.1), triangle_leg_ratio=0.3)
            else:
                mark = MarkUtils.square(cx, cy, self.mark_size)
            if hasattr(mark, "rotate"):
                mark = mark.rotate(rotation)
                mark_shapes = mark.get_shapes()
            else:
                mark_shapes = mark
            if isinstance(mark_shapes, list):
                shapes.extend(mark_shapes)
            else:
                shapes.append(mark_shapes)
        return shapes

    def generate(self):
        self._log_info(
            f"Starting MOSFET.generate with channel_type={self.channel_type}, x={self.x}, y={self.y}, "
            f"W={self.channel_width}, L={self.channel_length}, gate_overlap={self.gate_overlap}"
        )
        x, y = self.x, self.y
        ch_w = self.channel_width
        ch_l = self.channel_length

        self._log_info("Generating channel geometry")
        self.shapes["channel"] = [
            self._box_um(x, y, ch_l * self.channel_extension_ratio, ch_w, center=True)
        ]

        diel_w = max(ch_l * self.dielectric_extension_ratio, ch_l + self.dielectric_margin)
        diel_h = max(ch_w * self.dielectric_extension_ratio, ch_w + self.dielectric_margin)
        self._log_info(f"Generating dielectric geometry with size=({diel_w}, {diel_h})")
        self.shapes["bottom_dielectric"] = [self._box_um(x, y, diel_w, diel_h, center=True)]
        self.shapes["top_dielectric"] = [self._box_um(x, y, diel_w, diel_h, center=True)]

        self._component_shapes = {
            "bottom_gate": [],
            "source": [],
            "drain": [],
            "top_gate": [],
        }

        if self.enable_bottom_gate:
            self._append_single_gate(
                "bottom_gate",
                self.bottom_gate_outer_offset_x,
                self.bottom_gate_outer_offset_y,
                self.bottom_gate_inner_width_ratio,
                self.bottom_gate_inner_chamfer,
                self.bottom_gate_outer_chamfer,
            )

        if self.enable_source_drain:
            self._log_info(f"Generating source/drain with fanout_direction={self.fanout_direction}")
            if self.fanout_direction == "vertical":
                source_outer = (
                    x - ch_l,
                    y + self.source_drain_outer_offset_y + self.source_drain_outer_offset_x * 0.25,
                )
                drain_outer = (
                    x + ch_l,
                    y + self.source_drain_outer_offset_y + self.source_drain_outer_offset_x * 0.25,
                )
            else:
                source_outer = (
                    x - ch_l / 2.0 - self.source_drain_outer_offset_x,
                    y + self.source_drain_outer_offset_y,
                )
                drain_outer = (
                    x + ch_l / 2.0 + self.source_drain_outer_offset_x,
                    y + self.source_drain_outer_offset_y,
                )

            self._append_sd_shapes("source", (x - ch_l, y), source_outer)
            self._append_sd_shapes("drain", (x + ch_l, y), drain_outer)

        if self.enable_top_gate:
            self._append_single_gate(
                "top_gate",
                self.top_gate_outer_offset_x,
                self.top_gate_outer_offset_y,
                self.top_gate_inner_width_ratio,
                self.top_gate_inner_chamfer,
                self.top_gate_outer_chamfer,
            )

        active_bbox = self._compute_active_bbox()
        if active_bbox is None:
            half_channel_l = ch_l * self.channel_extension_ratio / 2.0
            half_channel_w = ch_w / 2.0
            active_bbox = pya.Box(
                int((x - half_channel_l) * 1000),
                int((y - half_channel_w) * 1000),
                int((x + half_channel_l) * 1000),
                int((y + half_channel_w) * 1000),
            )
        else:
            half_channel_l = (active_bbox.right - active_bbox.left) / 2000.0
            half_channel_w = (active_bbox.top - active_bbox.bottom) / 2000.0

        region_bbox = pya.Box(
            active_bbox.left - int(self.device_region_margin_x * 1000),
            active_bbox.bottom - int(self.device_region_margin_y * 1000),
            active_bbox.right + int(self.device_region_margin_x * 1000),
            active_bbox.top + int(self.device_region_margin_y * 1000),
        )
        self._log_info(
            "Device region from corner marks = "
            f"({region_bbox.left / 1000.0}, {region_bbox.bottom / 1000.0}) to ({region_bbox.right / 1000.0}, {region_bbox.top / 1000.0}) um"
        )

        if self.show_device_labels:
            self.shapes["device_label"] = self._append_text_shape(
                self.device_label,
                region_bbox.left / 1000.0 + self.mark_size + 4.0 + self.label_offset_x,
                region_bbox.top / 1000.0 - self.mark_size - 2.0 + self.label_offset_y,
            )
        else:
            self.shapes["device_label"] = []

        if self.show_parameter_labels:
            param_text = f"{self.channel_type.upper()} W={self.channel_width:g} L={self.channel_length:g}"
            self.shapes["parameter_labels"] = self._append_text_shape(
                param_text,
                region_bbox.left / 1000.0 + self.mark_size + 4.0,
                region_bbox.bottom / 1000.0 + self.mark_size + 4.0,
            )
        else:
            self.shapes["parameter_labels"] = []

        if self.show_alignment_marks:
            self.shapes["alignment_marks"] = self._create_alignment_mark_shapes(region_bbox)
        else:
            self.shapes["alignment_marks"] = []
        self._log_info("MOSFET.generate completed")

    def get_all_shapes(self):
        return dict(self._component_shapes)

    def get_device_info(self):
        return {
            "device_id": self.device_id,
            "channel_width": self.channel_width,
            "channel_length": self.channel_length,
            "gate_overlap": self.gate_overlap,
            "channel_type": self.channel_type,
            "device_label": self.device_label,
        }


def _write_test_layout(filename="mosfet_test.gds", device_params=None):
    MOSFET._log_info(f"Starting test layout generation for file '{filename}'")
    layout = pya.Layout()
    layout.dbu = PROCESS_CONFIG["dbu"]
    MOSFET._log_info(f"Created layout with dbu={layout.dbu}")
    top_cell = layout.create_cell("TOP")
    device_cell = layout.create_cell("MOSFET_TEST")
    MOSFET._log_info("Created TOP and MOSFET_TEST cells")

    device_params = dict(device_params or {})
    MOSFET._log_info(f"Instantiating MOSFET with test parameters: {device_params}")
    device = MOSFET(**device_params)
    device.generate()

    layer_map = {name: layout.layer(layer_id, 0) for name, layer_id in device.get_layer_ids().items()}
    MOSFET._log_info(f"Resolved layer map: {device.get_layer_ids()}")

    for name, shapes in device.shapes.items():
        MOSFET._log_info(f"Inserting {len(shapes)} shapes for primary bucket '{name}'")
        for shape in shapes:
            device_cell.shapes(layer_map[name]).insert(shape)
    for name, shapes in device.get_all_shapes().items():
        MOSFET._log_info(f"Inserting {len(shapes)} shapes for component bucket '{name}'")
        for shape in shapes:
            device_cell.shapes(layer_map[name]).insert(shape)

    top_cell.insert(pya.CellInstArray(device_cell.cell_index(), pya.Trans()))
    MOSFET._log_info("Inserted MOSFET_TEST into TOP")
    output_path = get_gds_path(filename)
    MOSFET._log_info(f"Writing layout to '{output_path}'")
    layout.write(output_path)
    MOSFET._log_info(f"Finished writing layout to '{output_path}'")
    return output_path


if __name__ == "__main__":
    # Example parameter set for standalone MOSFET test generation.
    # All dimensions are in micrometers unless noted otherwise.
    test_params = {
        # Placement
        "x": 0.0,                     # Device center X
        "y": 0.0,                     # Device center Y

        # Device type / core geometry
        "channel_type": "n",          # "p" -> P-channel layers, "n" -> N-channel layers
        "channel_width": 20.0,         # Channel width
        "channel_length": 5.0,       # Channel contact-to-contact half-structure scale used by this MOSFET builder
        "gate_overlap": 2.0,          # Gate overlap / extra gate enclosure around channel

        # Labels / identifiers
        "device_label": "NMOS_01",    # Main device label text
        "device_id": 1,               # Optional numeric ID

        # Switches
        "fanout_enabled": True,       # True -> add outer pads and fanout polygons
        "fanout_direction": "horizontal",  # "horizontal" or "vertical" source/drain fanout style
        "enable_bottom_gate": True,   # Enable bottom-gate electrode
        "enable_top_gate": True,      # Enable top-gate electrode
        "enable_source_drain": True,  # Enable source/drain electrodes
        "show_device_labels": True,   # Draw device label
        "show_parameter_labels": True,  # Draw parameter label
        "show_alignment_marks": True,   # Draw corner marks

        # Generic pad / chamfer settings
        "outer_pad_size": 80.0,       # Outer pad square size
        "chamfer_size": 10.0,         # Chamfer size used when chamfer is enabled

        # Channel / dielectric envelope
        "channel_extension_ratio": 3.0,   # Drawn channel length = channel_length * this ratio
        "dielectric_extension_ratio": 2.0,  # Drawn dielectric width/height scale factor
        "dielectric_margin": 4.0,     # Minimum dielectric extra margin around channel

        # Source / drain geometry
        "source_drain_inner_width_ratio": 1.2,  # Inner S/D width relative to channel width
        "source_drain_outer_offset_x": 110.0,   # Outer S/D pad X offset
        "source_drain_outer_offset_y": 0.0,     # Outer S/D pad Y offset; default 0 keeps horizontal alignment
        "source_drain_inner_chamfer": "none",   # "none" / "straight" / "round"
        "source_drain_outer_chamfer": "straight",

        # Bottom-gate geometry
        "bottom_gate_inner_width_ratio": 1.5,   # Bottom-gate inner width relative to channel width
        "bottom_gate_outer_offset_x": 0.0,      # Bottom-gate outer pad X offset
        "bottom_gate_outer_offset_y": -100.0,   # Bottom-gate outer pad Y offset
        "bottom_gate_inner_chamfer": "none",
        "bottom_gate_outer_chamfer": "straight",

        # Top-gate geometry
        "top_gate_inner_width_ratio": 1.2,      # Top-gate inner width relative to channel width
        "top_gate_outer_offset_x": 0.0,         # Top-gate outer pad X offset
        "top_gate_outer_offset_y": 100.0,       # Top-gate outer pad Y offset
        "top_gate_inner_chamfer": "none",
        "top_gate_outer_chamfer": "straight",

        # Device region / marks
        "device_region_margin_x": 10.0,         # Horizontal clearance from active device to mark-defined region
        "device_region_margin_y": 10.0,         # Vertical clearance from active device to mark-defined region
        "mark_size": 20.0,                      # Corner mark size
        "mark_width": 3,                      # Line width for line-based marks
        "mark_type_1": "sq_missing",                # Top-left mark
        "mark_type_2": "L_shape",               # Top-right mark
        "mark_type_3": "L_shape",               # Bottom-left mark
        "mark_type_4": "L_shape",               # Bottom-right mark
        "mark_rotation_1": 0,                   # Chessy rotation
        "mark_rotation_2": 0,                 # L opens outward at top-right
        "mark_rotation_3": 180,                  # L opens outward at bottom-left
        "mark_rotation_4": 270,                   # L opens outward at bottom-right

        # Label rendering
        "label_font": "C:/Windows/Fonts/OCRAEXT.TTF",  # Font path used by the project
        "label_size": 14.0,                    # Reserved for future polygon text rendering
        "label_anchor": "left_bottom",         # Reserved label anchor setting
        "label_offset_x": 0.0,                 # Manual label X offset
        "label_offset_y": 0.0,                 # Manual label Y offset
    }

    output_path = _write_test_layout(device_params=test_params)
    print(f"MOSFET test layout written to: {output_path}")
