import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLKIT = os.path.join(ROOT, "lymtoolkit", "toolkit", "nanodevice-toolkit")
if TOOLKIT not in sys.path:
    sys.path.insert(0, TOOLKIT)

import pya  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

import nanodevice_toolkit as gui  # noqa: E402
from addon_api import ParameterSpec, ToolSpec  # noqa: E402

_QT_APP = QApplication.instance() or QApplication([])

def _app():
    return _QT_APP


def test_generated_preview_uses_actual_lab_pdk_layer_color():
    _app()
    _pen, brush = gui._preview_style_for_layer_id(31, "heater_metal")
    assert brush.color().name().lower() == "#e08800"
    assert brush.color().name().lower() != "#d9d9d9"


def test_function_picker_accepts_external_svg_icon(tmp_path):
    _app()
    icon = tmp_path / "tool.svg"
    icon.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
        '<circle cx="16" cy="16" r="14" fill="#e08800"/></svg>',
        encoding="utf-8",
    )
    picker = gui.FunctionPicker()
    picker.addItem("External", "external.tool", str(icon))
    assert not picker._buttons[0].icon().isNull()
    assert not picker.icon().isNull()


def test_manual_tool_waits_for_regenerate(monkeypatch):
    _app()
    calls = []

    def insert(layout, top, values):
        calls.append(dict(values))
        top.shapes(layout.layer(31, 0)).insert(pya.Box(0, 0, 1000, 1000))

    tool = ToolSpec(
        key="manual.example",
        title="Manual example",
        library_name="",
        pcell_name="",
        preview_renderer=lambda *_args: None,
        params=[ParameterSpec("width", "Width", "W", "Geometry", 1.0)],
        preview_layers=[("heater_metal", "Metal")],
        insert_handler=insert,
        layer_ids={"heater_metal": [31]},
        preview_policy="manual",
    )
    monkeypatch.setattr(gui, "discover_addons", lambda _root: ([], []))
    dialog = gui.ToolkitDialog([tool])
    assert calls == []
    assert dialog.preview_btn.text() == "Regenerate"
    assert dialog.status_label.text() == "Preparing"
    assert dialog.progress_label.text() == "0%"
    dialog.controls["width"].setValue(2.0)
    assert calls == []
    dialog._refit_preview()
    assert len(calls) == 1
    assert dialog.status_label.text() == "Ready"
    assert dialog.progress_label.text() == "Ready · 100%"


def test_every_core_function_has_an_offline_html_manual(monkeypatch):
    _app()
    monkeypatch.setattr(gui, "discover_addons", lambda _root: ([], []))
    tools = [
        gui.NANODEVICE_FET_TOOL,
        gui.GDSFACTORY_TEXT_TOOL,
        gui.MOSFET_COMPONENT_TOOL,
        gui.MOSFET_PCELL_TOOL,
        gui.WOODPILE_COMPONENT_TOOL,
        gui.CROSSBAR_COMPONENT_TOOL,
        gui.HEMT_COMPONENT_TOOL,
        gui.HALL_COMPONENT_TOOL,
        gui.TLM_COMPONENT_TOOL,
        gui.SENSE_LATCH_ARRAY_TOOL,
        gui.WRITE_READ_ARRAY_TOOL,
    ]
    dialog = gui.ToolkitDialog(tools)
    for index, tool in enumerate(tools):
        dialog.tool_select.setCurrentIndex(index)
        assert dialog.manual_btn.isEnabled(), tool.key
        assert tool.documentation_path.endswith(tool.key + ".html")
        assert os.path.isfile(tool.documentation_path)
        html = open(tool.documentation_path, "r", encoding="utf-8").read()
        assert '<svg class="diagram"' in html
        assert tool.key + "-canvas.png" in html
        assert os.path.isfile(os.path.join(os.path.dirname(tool.documentation_path), "assets", tool.key + "-canvas.png"))
        assert "如何改变结构" in html
        assert 'data-lang="zh"' in html
        assert 'data-lang="en"' in html
        assert "Structural effect" in html
    manual_js = os.path.join(os.path.dirname(tools[0].documentation_path), "assets", "manual.js")
    assert os.path.isfile(manual_js)
    assert "nanodevice-manual-language" in open(manual_js, "r", encoding="utf-8").read()
