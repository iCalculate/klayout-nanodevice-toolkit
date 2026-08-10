"""KLayout batch smoke test for the NanoDevice HEMT integration."""

import importlib.util
import os
import sys

import pya


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

toolkit_path = os.path.join(
    ROOT,
    "lymtoolkit",
    "toolkit",
    "nanodevice-toolkit",
    "nanodevice_toolkit.py",
)
spec = importlib.util.spec_from_file_location("nanodevice_toolkit_smoke", toolkit_path)
toolkit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(toolkit)

values = {param.key: param.default for param in toolkit.HEMT_COMPONENT_TOOL.params}
values["hollow_fanout"] = True
values["mark_mode"] = "corners_and_sides"
layout = pya.Layout()
layout.dbu = 0.001
top = layout.create_cell("TOP")
toolkit._insert_hemt_component(layout, top, values)

if not list(top.each_inst()):
    raise RuntimeError("HEMT insertion did not create a child cell instance")
if layout.cells() != 2:
    raise RuntimeError("Expected TOP and one HEMT device cell")

output_path = os.path.join(ROOT, "output", "hemt_klayout_smoke.gds")
layout.write(output_path)
print("HEMT KLayout smoke test passed: {} cells".format(layout.cells()))
