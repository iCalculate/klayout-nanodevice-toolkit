import os
import sys

import pya


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
    return candidates[-1]


ROOT_DIR = _discover_root_dir()
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from components.mosfet import MOSFET
from config import DEFAULT_DBU


MARK_CHOICES = [
    ["double_square", "double_square"],
    ["square", "square"],
    ["diamond", "diamond"],
    ["triangle", "triangle"],
    ["cross", "cross"],
    ["circle", "circle"],
    ["L_shape", "L_shape"],
    ["T_shape", "T_shape"],
    ["sq_missing", "sq_missing"],
    ["cross_tri", "cross_tri"],
]

CHAMFER_CHOICES = [["none", "none"], ["straight", "straight"], ["round", "round"]]


class MOSFETPCell(pya.PCellDeclarationHelper):
    """Editable PCell facade for the component-based MOSFET generator."""

    def __init__(self):
        super(MOSFETPCell, self).__init__()

        self.param("cell_name", self.TypeString, "Cell name", default="MOSFET_Device")
        self.param("x", self.TypeDouble, "Center X (um)", default=0.0)
        self.param("y", self.TypeDouble, "Center Y (um)", default=0.0)
        self.param("channel_width", self.TypeDouble, "Channel width (um)", default=20.0)
        self.param("channel_length", self.TypeDouble, "Channel length (um)", default=5.0)
        self.param("gate_overlap", self.TypeDouble, "Gate overlap (um)", default=2.0)
        self.param(
            "channel_type",
            self.TypeString,
            "Channel type",
            default="n",
            choices=[["p", "p"], ["n", "n"]],
        )
        self.param("outer_pad_size", self.TypeDouble, "Outer pad size (um)", default=60.0)
        self.param("chamfer_size", self.TypeDouble, "Chamfer size (um)", default=10.0)
        self.param("channel_extension_ratio", self.TypeDouble, "Channel extension ratio", default=4.0)
        self.param("dielectric_extension_ratio", self.TypeDouble, "Dielectric extension ratio", default=1.0)
        self.param("dielectric_margin", self.TypeDouble, "Dielectric margin (um)", default=25.0)

        self.param("device_label", self.TypeString, "Device label", default="D1")
        self.param("label_size", self.TypeDouble, "Label size (um)", default=20.0)
        self.param("label_offset_x", self.TypeDouble, "Label offset X (um)", default=-6.0)
        self.param("label_offset_y", self.TypeDouble, "Label offset Y (um)", default=-13.0)

        self.param("mark_type_1", self.TypeString, "Mark 1", default="sq_missing", choices=MARK_CHOICES)
        self.param("mark_type_2", self.TypeString, "Mark 2", default="L_shape", choices=MARK_CHOICES)
        self.param("mark_type_3", self.TypeString, "Mark 3", default="L_shape", choices=MARK_CHOICES)
        self.param("mark_type_4", self.TypeString, "Mark 4", default="L_shape", choices=MARK_CHOICES)
        self.param("mark_rotation_1", self.TypeInt, "Mark rotation 1", default=0)
        self.param("mark_rotation_2", self.TypeInt, "Mark rotation 2", default=0)
        self.param("mark_rotation_3", self.TypeInt, "Mark rotation 3", default=2)
        self.param("mark_rotation_4", self.TypeInt, "Mark rotation 4", default=3)
        self.param("mark_size", self.TypeDouble, "Mark size (um)", default=20.0)
        self.param("mark_width", self.TypeDouble, "Mark width (um)", default=5.0)
        self.param("device_region_margin_x", self.TypeDouble, "Device region margin X (um)", default=0.0)
        self.param("device_region_margin_y", self.TypeDouble, "Device region margin Y (um)", default=0.0)

        self.param("source_drain_inner_width_ratio", self.TypeDouble, "Source/drain inner width ratio", default=1.2)
        self.param("source_drain_outer_offset_x", self.TypeDouble, "Source/drain outer offset X (um)", default=50.0)
        self.param("source_drain_outer_offset_y", self.TypeDouble, "Source/drain outer offset Y (um)", default=0.0)
        self.param(
            "source_drain_inner_chamfer",
            self.TypeString,
            "Source/drain inner chamfer",
            default="none",
            choices=CHAMFER_CHOICES,
        )
        self.param(
            "source_drain_outer_chamfer",
            self.TypeString,
            "Source/drain outer chamfer",
            default="straight",
            choices=CHAMFER_CHOICES,
        )

        self.param("bottom_gate_inner_width_ratio", self.TypeDouble, "Bottom-gate inner width ratio", default=1.5)
        self.param("bottom_gate_outer_offset_x", self.TypeDouble, "Bottom-gate outer offset X (um)", default=0.0)
        self.param("bottom_gate_outer_offset_y", self.TypeDouble, "Bottom-gate outer offset Y (um)", default=-55.0)
        self.param(
            "bottom_gate_inner_chamfer",
            self.TypeString,
            "Bottom-gate inner chamfer",
            default="none",
            choices=CHAMFER_CHOICES,
        )
        self.param(
            "bottom_gate_outer_chamfer",
            self.TypeString,
            "Bottom-gate outer chamfer",
            default="straight",
            choices=CHAMFER_CHOICES,
        )

        self.param("top_gate_inner_width_ratio", self.TypeDouble, "Top-gate inner width ratio", default=1.5)
        self.param("top_gate_outer_offset_x", self.TypeDouble, "Top-gate outer offset X (um)", default=0.0)
        self.param("top_gate_outer_offset_y", self.TypeDouble, "Top-gate outer offset Y (um)", default=55.0)
        self.param(
            "top_gate_inner_chamfer",
            self.TypeString,
            "Top-gate inner chamfer",
            default="none",
            choices=CHAMFER_CHOICES,
        )
        self.param(
            "top_gate_outer_chamfer",
            self.TypeString,
            "Top-gate outer chamfer",
            default="straight",
            choices=CHAMFER_CHOICES,
        )

        self.param("fanout_enabled", self.TypeBoolean, "Enable fanout", default=True)
        self.param(
            "fanout_direction",
            self.TypeString,
            "Fanout direction",
            default="horizontal",
            choices=[["horizontal", "horizontal"], ["vertical", "vertical"]],
        )
        self.param("enable_bottom_gate", self.TypeBoolean, "Enable bottom gate", default=True)
        self.param("enable_top_gate", self.TypeBoolean, "Enable top gate", default=True)
        self.param("enable_source_drain", self.TypeBoolean, "Enable source/drain", default=True)
        self.param("show_device_labels", self.TypeBoolean, "Show device label", default=True)
        self.param("show_parameter_labels", self.TypeBoolean, "Show parameter label", default=False)
        self.param("show_alignment_marks", self.TypeBoolean, "Show alignment marks", default=True)

    def display_text_impl(self):
        label = self.cell_name.strip() or "MOSFET_Device"
        return "{}({}MOS, W={}, L={})".format(
            label,
            str(self.channel_type).upper(),
            self.channel_width,
            self.channel_length,
        )

    @staticmethod
    def _clamp(value, minimum, maximum):
        return min(max(value, minimum), maximum)

    def coerce_parameters_impl(self):
        self.x = self._clamp(self.x, -5000.0, 5000.0)
        self.y = self._clamp(self.y, -5000.0, 5000.0)
        self.channel_width = self._clamp(self.channel_width, 0.1, 1000.0)
        self.channel_length = self._clamp(self.channel_length, 0.1, 1000.0)
        self.gate_overlap = self._clamp(self.gate_overlap, 0.1, 500.0)
        self.outer_pad_size = self._clamp(self.outer_pad_size, 1.0, 5000.0)
        self.chamfer_size = self._clamp(self.chamfer_size, 0.0, 1000.0)
        self.channel_extension_ratio = self._clamp(self.channel_extension_ratio, 0.1, 20.0)
        self.dielectric_extension_ratio = self._clamp(self.dielectric_extension_ratio, 0.1, 20.0)
        self.dielectric_margin = self._clamp(self.dielectric_margin, 0.0, 500.0)
        self.label_size = self._clamp(self.label_size, 1.0, 200.0)
        self.label_offset_x = self._clamp(self.label_offset_x, -5000.0, 5000.0)
        self.label_offset_y = self._clamp(self.label_offset_y, -5000.0, 5000.0)
        self.mark_rotation_1 = int(self._clamp(self.mark_rotation_1, 0, 3))
        self.mark_rotation_2 = int(self._clamp(self.mark_rotation_2, 0, 3))
        self.mark_rotation_3 = int(self._clamp(self.mark_rotation_3, 0, 3))
        self.mark_rotation_4 = int(self._clamp(self.mark_rotation_4, 0, 3))
        self.mark_size = self._clamp(self.mark_size, 1.0, 500.0)
        self.mark_width = self._clamp(self.mark_width, 0.1, 100.0)
        self.device_region_margin_x = self._clamp(self.device_region_margin_x, 0.0, 1000.0)
        self.device_region_margin_y = self._clamp(self.device_region_margin_y, 0.0, 1000.0)
        self.source_drain_inner_width_ratio = self._clamp(self.source_drain_inner_width_ratio, 0.1, 20.0)
        self.source_drain_outer_offset_x = self._clamp(self.source_drain_outer_offset_x, -5000.0, 5000.0)
        self.source_drain_outer_offset_y = self._clamp(self.source_drain_outer_offset_y, -5000.0, 5000.0)
        self.bottom_gate_inner_width_ratio = self._clamp(self.bottom_gate_inner_width_ratio, 0.1, 20.0)
        self.bottom_gate_outer_offset_x = self._clamp(self.bottom_gate_outer_offset_x, -5000.0, 5000.0)
        self.bottom_gate_outer_offset_y = self._clamp(self.bottom_gate_outer_offset_y, -5000.0, 5000.0)
        self.top_gate_inner_width_ratio = self._clamp(self.top_gate_inner_width_ratio, 0.1, 20.0)
        self.top_gate_outer_offset_x = self._clamp(self.top_gate_outer_offset_x, -5000.0, 5000.0)
        self.top_gate_outer_offset_y = self._clamp(self.top_gate_outer_offset_y, -5000.0, 5000.0)

    def _parameter_values(self):
        names = [
            "x",
            "y",
            "channel_width",
            "channel_length",
            "gate_overlap",
            "channel_type",
            "outer_pad_size",
            "chamfer_size",
            "channel_extension_ratio",
            "dielectric_extension_ratio",
            "dielectric_margin",
            "device_label",
            "label_size",
            "label_offset_x",
            "label_offset_y",
            "mark_type_1",
            "mark_type_2",
            "mark_type_3",
            "mark_type_4",
            "mark_rotation_1",
            "mark_rotation_2",
            "mark_rotation_3",
            "mark_rotation_4",
            "mark_size",
            "mark_width",
            "device_region_margin_x",
            "device_region_margin_y",
            "source_drain_inner_width_ratio",
            "source_drain_outer_offset_x",
            "source_drain_outer_offset_y",
            "source_drain_inner_chamfer",
            "source_drain_outer_chamfer",
            "bottom_gate_inner_width_ratio",
            "bottom_gate_outer_offset_x",
            "bottom_gate_outer_offset_y",
            "bottom_gate_inner_chamfer",
            "bottom_gate_outer_chamfer",
            "top_gate_inner_width_ratio",
            "top_gate_outer_offset_x",
            "top_gate_outer_offset_y",
            "top_gate_inner_chamfer",
            "top_gate_outer_chamfer",
            "fanout_enabled",
            "fanout_direction",
            "enable_bottom_gate",
            "enable_top_gate",
            "enable_source_drain",
            "show_device_labels",
            "show_parameter_labels",
            "show_alignment_marks",
        ]
        return {name: getattr(self, name) for name in names}

    def _insert_scaled(self, shapes, shape, scale):
        if abs(scale - 1.0) < 1e-12:
            shapes.insert(shape)
        else:
            shapes.insert(shape.transformed(pya.ICplxTrans(scale, 0.0, False, 0, 0)))

    def produce_impl(self):
        device = MOSFET(**self._parameter_values())
        device.generate()

        scale = float(DEFAULT_DBU) / float(self.layout.dbu)
        layer_map = {
            name: self.layout.layer(layer_id, 0)
            for name, layer_id in device.get_layer_ids().items()
        }
        for name, generated_shapes in device.shapes.items():
            target_shapes = self.cell.shapes(layer_map[name])
            for shape in generated_shapes:
                self._insert_scaled(target_shapes, shape, scale)
        for name, generated_shapes in device.get_all_shapes().items():
            target_shapes = self.cell.shapes(layer_map[name])
            for shape in generated_shapes:
                self._insert_scaled(target_shapes, shape, scale)
