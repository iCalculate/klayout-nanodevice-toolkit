"""Public API for NanoDevice Toolkit add-ons.

The classes in this module deliberately contain no Qt or KLayout imports.  An
add-on can therefore declare its UI and geometry entry points without importing
the large toolkit GUI module (and without creating an import cycle).
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


TOOLKIT_ADDON_API_VERSION = 1


@dataclass
class ParameterSpec:
    """Describe one value shown in the NanoDevice parameter panel."""

    key: str
    label: str
    symbol: str
    group: str
    default: Any
    kind: str = "float"
    minimum: float = -1e6
    maximum: float = 1e6
    decimals: int = 3
    choices: Optional[list] = None
    suffix: str = ""
    tooltip: str = ""
    visible_if: Optional[Dict[str, Any]] = None
    enabled_if: Optional[Dict[str, Any]] = None
    read_only: bool = False


@dataclass
class ToolSpec:
    """Connect a GUI tool entry to preview and insertion callbacks."""

    key: str
    title: str
    library_name: str
    pcell_name: str
    preview_renderer: Callable
    params: List[ParameterSpec]
    preview_layers: list
    insert_params_builder: Optional[Callable] = None
    insert_handler: Optional[Callable] = None
    validator: Optional[Callable] = None
    summary_renderer: Optional[Callable] = None
    layer_ids: Dict[str, List[int]] = field(default_factory=dict)
    addon_id: str = "core"
    addon_version: str = ""
    config_migrator: Optional[Callable] = None
    icon_path: str = ""
    preview_policy: str = "live"
    documentation_path: str = ""


@dataclass
class AddonSpec:
    """Metadata returned by an add-on entry point."""

    addon_id: str
    name: str
    version: str
    author: str
    tools: List[ToolSpec]
    toolkit_api_version: int = TOOLKIT_ADDON_API_VERSION
    description: str = ""
