import json
import os
import sys
import zipfile

import pytest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLKIT = os.path.join(ROOT, "lymtoolkit", "toolkit", "nanodevice-toolkit")
if TOOLKIT not in sys.path:
    sys.path.insert(0, TOOLKIT)

import addon_manager as addon_manager_module  # noqa: E402
from addon_manager import (  # noqa: E402
    MANIFEST_NAME,
    discover_addons,
    install_addon_zip,
    load_addon,
)


@pytest.fixture(autouse=True)
def _isolate_real_user_addons(tmp_path, monkeypatch):
    """Unit discovery must not consume the developer's registered add-ons."""
    monkeypatch.setattr(addon_manager_module, "read_development_paths", lambda: [])
    monkeypatch.setattr(addon_manager_module, "user_addon_dir", lambda: str(tmp_path / "user-addons"))


def _write_minimal_addon(path, addon_id="example.addon", api=1, tool_key="example_tool"):
    path.mkdir(parents=True)
    manifest = {
        "schema_version": 1,
        "addon_id": addon_id,
        "name": "Example",
        "version": "1.0.0",
        "author": "Tests",
        "toolkit_api_version": api,
        "entrypoint": "addon.py:create_addon",
    }
    (path / MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    (path / "addon.py").write_text(
        "from addon_api import AddonSpec, ToolSpec\n"
        "def create_addon():\n"
        "    tool=ToolSpec(%r, 'Example tool', '', '', lambda *a: None, [], [], insert_handler=lambda *a: None)\n"
        "    return AddonSpec(%r, 'Example', '1.0.0', 'Tests', [tool])\n" % (tool_key, addon_id),
        encoding="utf-8",
    )


def test_load_and_discover_addon(tmp_path):
    addon = tmp_path / "addons" / "example"
    _write_minimal_addon(addon)
    record = load_addon(str(addon))
    assert record.status == "loaded"
    assert record.version == "1.0.0"
    tools, records = discover_addons(str(tmp_path), extra_paths=[str(addon)])
    assert [tool.key for tool in tools] == ["example_tool"]
    assert records[0].addon_id == "example.addon"


def test_bad_api_is_isolated(tmp_path):
    addon = tmp_path / "bad"
    _write_minimal_addon(addon, api=99)
    record = load_addon(str(addon))
    assert record.status == "error"
    assert "requires toolkit API" in record.message


def test_unsafe_addon_id_is_rejected(tmp_path):
    addon = tmp_path / "unsafe"
    _write_minimal_addon(addon)
    manifest_path = addon / MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["addon_id"] = "../escape"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    record = load_addon(str(addon))
    assert record.status == "error"
    assert "unsafe characters" in record.message


def test_duplicate_ids_are_disabled(tmp_path):
    first = tmp_path / "one"
    second = tmp_path / "two"
    _write_minimal_addon(first, addon_id="same", tool_key="one")
    _write_minimal_addon(second, addon_id="same", tool_key="two")
    tools, records = discover_addons(str(tmp_path / "empty"), extra_paths=[str(first), str(second)])
    assert len(tools) == 1
    assert sorted(record.status for record in records) == ["disabled", "loaded"]


def test_zip_install_and_path_traversal_rejection(tmp_path):
    source = tmp_path / "source"
    _write_minimal_addon(source)
    good_zip = tmp_path / "good.zip"
    with zipfile.ZipFile(good_zip, "w") as archive:
        for filename in (MANIFEST_NAME, "addon.py"):
            archive.write(source / filename, "package/" + filename)
    installed = install_addon_zip(str(good_zip), destination=str(tmp_path / "installed"))
    assert os.path.isfile(os.path.join(installed, MANIFEST_NAME))

    bad_zip = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad_zip, "w") as archive:
        archive.writestr("../escape.py", "bad")
        archive.writestr(MANIFEST_NAME, "{}")
    with pytest.raises(ValueError, match="unsafe ZIP path"):
        install_addon_zip(str(bad_zip), destination=str(tmp_path / "bad-install"))


def test_zip_install_uses_user_addon_folder_by_default(tmp_path, monkeypatch):
    source = tmp_path / "source"
    _write_minimal_addon(source)
    archive_path = tmp_path / "addon.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for filename in (MANIFEST_NAME, "addon.py"):
            archive.write(source / filename, filename)

    default_folder = tmp_path / "user-addons"
    monkeypatch.setattr(addon_manager_module, "user_addon_dir", lambda: str(default_folder))
    installed = install_addon_zip(str(archive_path))

    assert installed == str(default_folder / "example.addon")
    assert os.path.isfile(os.path.join(installed, MANIFEST_NAME))


def test_declared_documentation_is_required_and_installed(tmp_path):
    source = tmp_path / "documented"
    _write_minimal_addon(source, addon_id="documented.addon")
    manifest_path = source / MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["resources"] = ["README.md", "docs/modes"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert load_addon(str(source)).status == "error"
    (source / "README.md").write_text("# Documentation", encoding="utf-8")
    (source / "docs" / "modes").mkdir(parents=True)
    (source / "docs" / "modes" / "mode.md").write_text("# Mode", encoding="utf-8")
    archive_path = tmp_path / "documented.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for path in source.rglob("*"):
            if path.is_file():
                archive.write(path, "package/" + path.relative_to(source).as_posix())
    installed = install_addon_zip(str(archive_path), destination=str(tmp_path / "installed"))
    assert os.path.isfile(os.path.join(installed, "README.md"))
    assert os.path.isfile(os.path.join(installed, "docs", "modes", "mode.md"))


def test_tool_html_documentation_is_resolved_inside_addon(tmp_path):
    source = tmp_path / "html-manual"
    _write_minimal_addon(source)
    addon_path = source / "addon.py"
    code = addon_path.read_text(encoding="utf-8")
    code = code.replace(
        "    return AddonSpec",
        "    tool.documentation_path='docs/manual.html'\n    return AddonSpec",
    )
    addon_path.write_text(code, encoding="utf-8")
    (source / "docs").mkdir()
    manual = source / "docs" / "manual.html"
    manual.write_text("<!doctype html><title>Manual</title>", encoding="utf-8")
    record = load_addon(str(source))
    assert record.status == "loaded"
    assert record.addon.tools[0].documentation_path == str(manual.resolve())


def test_repository_addons_are_not_implicitly_discovered(tmp_path):
    bundled = tmp_path / "addons" / "should_stay_external"
    _write_minimal_addon(bundled)
    tools, records = discover_addons(str(tmp_path), extra_paths=[])
    assert tools == [] and records == []
