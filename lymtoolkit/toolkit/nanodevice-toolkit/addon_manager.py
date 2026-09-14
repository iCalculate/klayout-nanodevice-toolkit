"""Discovery and installation support for NanoDevice Toolkit add-ons."""

import hashlib
import importlib.util
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import types
import zipfile
from dataclasses import dataclass

from addon_api import AddonSpec, ToolSpec, TOOLKIT_ADDON_API_VERSION


MANIFEST_NAME = "nanodevice-addon.json"


@dataclass
class AddonRecord:
    addon_id: str
    name: str
    version: str
    source: str
    status: str
    message: str = ""
    addon: AddonSpec = None


def user_addon_dir():
    return os.path.join(os.path.expanduser("~"), "KLayout", "nanodevice-addons")


def development_paths_file():
    return os.path.join(user_addon_dir(), "addon_paths.json")


def read_development_paths():
    path = development_paths_file()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return []
    return [os.path.abspath(item) for item in payload.get("paths", []) if isinstance(item, str)]


def add_development_path(path):
    path = os.path.abspath(path)
    paths = read_development_paths()
    if path not in paths:
        paths.append(path)
    os.makedirs(user_addon_dir(), exist_ok=True)
    with open(development_paths_file(), "w", encoding="utf-8") as handle:
        json.dump({"paths": paths}, handle, indent=2, ensure_ascii=False)
    return paths


def _addon_directories(search_root):
    if not os.path.isdir(search_root):
        return []
    if os.path.isfile(os.path.join(search_root, MANIFEST_NAME)):
        return [search_root]
    result = []
    for name in sorted(os.listdir(search_root)):
        candidate = os.path.join(search_root, name)
        if os.path.isdir(candidate) and os.path.isfile(os.path.join(candidate, MANIFEST_NAME)):
            result.append(candidate)
    return result


def _parse_entrypoint(addon_dir, text):
    module_name, separator, callable_name = str(text or "").partition(":")
    if not separator or not module_name or not callable_name:
        raise ValueError("entrypoint must use 'module.py:callable' syntax")
    module_path = os.path.abspath(os.path.join(addon_dir, module_name))
    if os.path.commonpath([os.path.abspath(addon_dir), module_path]) != os.path.abspath(addon_dir):
        raise ValueError("entrypoint escapes the add-on directory")
    if not os.path.isfile(module_path):
        raise ValueError("entrypoint module does not exist: {}".format(module_name))
    return module_path, callable_name


def load_addon(addon_dir):
    """Load one manifest and return an AddonRecord; errors are isolated."""

    source = os.path.abspath(addon_dir)
    manifest_path = os.path.join(source, MANIFEST_NAME)
    try:
        with open(manifest_path, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        required = ("schema_version", "addon_id", "name", "version", "author", "toolkit_api_version", "entrypoint")
        missing = [key for key in required if key not in manifest]
        if missing:
            raise ValueError("missing manifest fields: {}".format(", ".join(missing)))
        if int(manifest["schema_version"]) != 1:
            raise ValueError("unsupported manifest schema_version")
        if not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$", str(manifest["addon_id"])):
            raise ValueError("addon_id contains unsafe characters")
        if int(manifest["toolkit_api_version"]) != TOOLKIT_ADDON_API_VERSION:
            raise ValueError(
                "requires toolkit API {}, available API is {}".format(
                    manifest["toolkit_api_version"], TOOLKIT_ADDON_API_VERSION
                )
            )
        resources = manifest.get("resources", [])
        if not isinstance(resources, list) or not all(isinstance(item, str) for item in resources):
            raise ValueError("manifest resources must be a list of relative paths")
        for relative in resources:
            resource_path = os.path.abspath(os.path.join(source, relative))
            if os.path.commonpath([source, resource_path]) != source:
                raise ValueError("resource escapes the add-on directory: {}".format(relative))
            if not os.path.exists(resource_path):
                raise ValueError("declared resource does not exist: {}".format(relative))
        module_path, callable_name = _parse_entrypoint(source, manifest["entrypoint"])
        digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:12]
        package_id = "nanodevice_external_addon_{}".format(digest)
        module_id = package_id + ".entrypoint"
        for loaded_name in list(sys.modules):
            if loaded_name == package_id or loaded_name.startswith(package_id + "."):
                del sys.modules[loaded_name]
        package = types.ModuleType(package_id)
        package.__path__ = [source]
        package.__package__ = package_id
        sys.modules[package_id] = package
        spec = importlib.util.spec_from_file_location(module_id, module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("unable to create module loader")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_id] = module
        sys.path.insert(0, source)
        try:
            spec.loader.exec_module(module)
        finally:
            if sys.path and sys.path[0] == source:
                sys.path.pop(0)
        factory = getattr(module, callable_name, None)
        if not callable(factory):
            raise ValueError("entrypoint callable was not found")
        addon = factory()
        if not isinstance(addon, AddonSpec):
            raise TypeError("entrypoint must return addon_api.AddonSpec")
        if addon.addon_id != manifest["addon_id"] or addon.version != manifest["version"]:
            raise ValueError("manifest and AddonSpec identity/version do not match")
        if int(addon.toolkit_api_version) != TOOLKIT_ADDON_API_VERSION:
            raise ValueError("Add-on object has an incompatible API version")
        seen = set()
        for tool in addon.tools:
            if not isinstance(tool, ToolSpec):
                raise TypeError("all add-on tools must be ToolSpec instances")
            if tool.key in seen:
                raise ValueError("duplicate tool key inside add-on: {}".format(tool.key))
            if not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$", str(tool.key)):
                raise ValueError("tool key contains unsafe characters: {}".format(tool.key))
            seen.add(tool.key)
            tool.addon_id = addon.addon_id
            tool.addon_version = addon.version
            documentation_path = str(getattr(tool, "documentation_path", "") or "")
            if documentation_path and not os.path.isabs(documentation_path):
                documentation_path = os.path.abspath(os.path.join(source, documentation_path))
                if os.path.commonpath([source, documentation_path]) != source:
                    raise ValueError("documentation escapes the add-on directory: {}".format(tool.key))
                tool.documentation_path = documentation_path
            if documentation_path and not os.path.isfile(documentation_path):
                raise ValueError("documentation does not exist for tool: {}".format(tool.key))
        return AddonRecord(addon.addon_id, addon.name, addon.version, source, "loaded", addon=addon)
    except Exception as exc:
        return AddonRecord("", os.path.basename(source), "", source, "error", str(exc))


def discover_addons(root_dir, extra_paths=None):
    """Discover user-installed and explicitly registered development add-ons."""

    # Device implementations are intentionally external to the Toolkit core.
    # A broken package is isolated so the core tools still load normally.
    roots = list(read_development_paths())
    roots.append(user_addon_dir())
    roots.extend(extra_paths or [])
    candidates = []
    seen_paths = set()
    for root in roots:
        for path in _addon_directories(root):
            norm = os.path.normcase(os.path.abspath(path))
            if norm not in seen_paths:
                seen_paths.add(norm)
                candidates.append(path)

    records = [load_addon(path) for path in candidates]
    winners = {}
    for record in records:
        if record.status != "loaded":
            continue
        previous = winners.get(record.addon_id)
        if previous is None:
            winners[record.addon_id] = record
        else:
            record.status = "disabled"
            record.message = "duplicate add-on id; already loaded from {}".format(previous.source)
    tools = []
    tool_keys = set()
    for record in records:
        if record.status != "loaded":
            continue
        for tool in record.addon.tools:
            if tool.key in tool_keys:
                record.status = "disabled"
                record.message = "duplicate global tool key: {}".format(tool.key)
                break
            tool_keys.add(tool.key)
            tools.append(tool)
    return tools, records


def _safe_zip_members(archive):
    for info in archive.infolist():
        name = info.filename.replace("\\", "/")
        parts = [part for part in name.split("/") if part not in ("", ".")]
        if name.startswith("/") or ".." in parts or (parts and ":" in parts[0]):
            raise ValueError("unsafe ZIP path: {}".format(info.filename))
        mode = (info.external_attr >> 16) & 0xFFFF
        if mode and stat.S_ISLNK(mode):
            raise ValueError("symbolic links are not allowed in add-on ZIP files")
        yield info


def install_addon_zip(zip_path, destination=None, replace=False):
    """Validate and install an add-on ZIP; return the installed directory."""

    destination = os.path.abspath(destination or user_addon_dir())
    os.makedirs(destination, exist_ok=True)
    temp_dir = tempfile.mkdtemp(prefix="nanodevice-addon-")
    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            members = list(_safe_zip_members(archive))
            archive.extractall(temp_dir, members)
        manifests = []
        for current, dirs, files in os.walk(temp_dir):
            dirs[:] = [name for name in dirs if name != "__MACOSX"]
            if MANIFEST_NAME in files:
                manifests.append(current)
        if len(manifests) != 1:
            raise ValueError("ZIP must contain exactly one {}".format(MANIFEST_NAME))
        record = load_addon(manifests[0])
        if record.status != "loaded":
            raise ValueError(record.message)
        target = os.path.join(destination, record.addon_id)
        if os.path.exists(target):
            if not replace:
                raise FileExistsError("add-on is already installed: {}".format(record.addon_id))
            shutil.rmtree(target)
        shutil.copytree(manifests[0], target)
        return target
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
