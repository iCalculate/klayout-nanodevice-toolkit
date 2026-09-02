"""KLayout batch smoke test for the editable MOSFET PCell."""

import importlib.util
import os
import sys

import pya


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

pcell_path = os.path.join(
    ROOT,
    "lymtoolkit",
    "toolkit",
    "nanodevice-toolkit",
    "mosfet_pcell.py",
)
spec = importlib.util.spec_from_file_location("mosfet_pcell_smoke", pcell_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class MOSFETSmokeLibrary(pya.Library):
    def __init__(self):
        super(MOSFETSmokeLibrary, self).__init__()
        self.layout().register_pcell("MOSFETPCell", module.MOSFETPCell())
        self.register("MOSFETSmokeLibrary")


library = MOSFETSmokeLibrary()
layout = pya.Layout()
layout.dbu = 0.001

variant = layout.create_cell(
    "MOSFETPCell",
    "MOSFETSmokeLibrary",
    {
        "cell_name": "MOSFET_Device",
        "channel_width": 20.0,
        "channel_length": 5.0,
        "show_parameter_labels": True,
    },
)
if variant is None or not variant.is_pcell_variant():
    raise RuntimeError("MOSFETPCell did not create a PCell variant")

top = layout.create_cell("TOP")
instance = top.insert(pya.CellInstArray(variant.cell_index(), pya.Trans()))
if not instance.is_pcell():
    raise RuntimeError("Inserted MOSFET instance is not recognized as a PCell")

updated = instance.change_pcell_parameter("channel_width", 35.0)
if updated is not None:
    instance = updated
if abs(float(instance.pcell_parameter("channel_width")) - 35.0) > 1e-9:
    raise RuntimeError("MOSFET PCell parameter update did not persist")

required_layers = (11, 12, 13, 15, 17, 18)
for layer_number in required_layers:
    if instance.cell.shapes(layout.layer(layer_number, 0)).is_empty():
        raise RuntimeError("Expected MOSFET geometry on layer {}/0".format(layer_number))

# The GUI and the PCell must expose the same parameter names so an Insert can
# pass the form values directly to Layout.create_cell.
toolkit_path = os.path.join(
    ROOT,
    "lymtoolkit",
    "toolkit",
    "nanodevice-toolkit",
    "nanodevice_toolkit.py",
)
toolkit_spec = importlib.util.spec_from_file_location("nanodevice_toolkit_mosfet_smoke", toolkit_path)
toolkit = importlib.util.module_from_spec(toolkit_spec)
toolkit_spec.loader.exec_module(toolkit)
gui_parameter_names = [parameter.key for parameter in toolkit.MOSFET_PCELL_TOOL.params]
declaration = library.layout().pcell_declaration("MOSFETPCell")
pcell_parameter_names = [parameter.name for parameter in declaration.get_parameters()]
if gui_parameter_names != pcell_parameter_names:
    raise RuntimeError(
        "GUI/PCell MOSFET parameters differ: GUI={} PCell={}".format(
            gui_parameter_names,
            pcell_parameter_names,
        )
    )
if toolkit.MOSFET_COMPONENT_TOOL.insert_handler is not toolkit._insert_mosfet_component:
    raise RuntimeError("Original MOSFET GUI entry no longer uses static insertion")
if toolkit.MOSFET_PCELL_TOOL.insert_handler is not None:
    raise RuntimeError("MOSFET PCell GUI entry unexpectedly uses static insertion")
if toolkit.MOSFET_PCELL_TOOL.pcell_name != "MOSFETPCell":
    raise RuntimeError("MOSFET PCell GUI entry is not connected to MOSFETPCell")

static_values = {parameter.key: parameter.default for parameter in toolkit.MOSFET_COMPONENT_TOOL.params}
static_layout = pya.Layout()
static_layout.dbu = 0.001
static_top = static_layout.create_cell("STATIC_TOP")
toolkit._insert_mosfet_component(static_layout, static_top, static_values)
static_instances = list(static_top.each_inst())
if len(static_instances) != 1 or static_instances[0].is_pcell():
    raise RuntimeError("Original MOSFET entry did not create one static cell instance")

# The legacy generator emits geometry at 1 nm DBU. Verify that the wrapper
# rescales it when the PCell's owning layout uses a different DBU.
scaled_layout = pya.Layout()
scaled_layout.dbu = 0.002
scaled_layout.register_pcell("MOSFETPCell", module.MOSFETPCell())
scaled_variant = scaled_layout.create_cell(
    "MOSFETPCell",
    {
        "fanout_enabled": False,
        "enable_bottom_gate": False,
        "enable_top_gate": False,
        "enable_source_drain": False,
        "show_device_labels": False,
        "show_parameter_labels": False,
        "show_alignment_marks": False,
    },
)
channel_bbox = scaled_variant.bbox_per_layer(scaled_layout.layer(13, 0))
if abs(channel_bbox.width() * scaled_layout.dbu - 20.0) > 1e-9:
    raise RuntimeError("MOSFET PCell DBU scaling produced the wrong channel width")

print("MOSFET PCell smoke test passed")
