# NanoDevice Add-on API v1

NanoDevice add-ons contribute parameterized tools to the existing NanoDevice
dialog without editing `nanodevice_toolkit.py`. Add-ons are ordinary Python
code and run in the KLayout process, so install only code you trust.

## Package layout

```text
my-device/
|-- nanodevice-addon.json
|-- addon.py
|-- README.md
|-- docs/
|   `-- modes/
|       `-- one-local-document-per-device-mode.md
`-- optional_resources/
```

The manifest is intentionally small:

```json
{
  "schema_version": 1,
  "addon_id": "org.example.my_device",
  "name": "My Device",
  "version": "0.1.0",
  "author": "Example Lab",
  "toolkit_api_version": 1,
  "entrypoint": "addon.py:create_addon"
}
```

`addon_id` and every tool key must contain only letters, digits, `.`, `_`, or
`-`. The entry point must return `addon_api.AddonSpec`; each tool is described
by a `ToolSpec` and a list of `ParameterSpec` values.

```python
from addon_api import AddonSpec, ParameterSpec, ToolSpec


def insert(layout, top_cell, values):
    # Create a child cell and insert it into top_cell.
    ...


def create_addon():
    tool = ToolSpec(
        key="example_device",
        title="Example Device",
        library_name="",
        pcell_name="",
        preview_renderer=lambda *_args, **_kwargs: None,
        params=[
            ParameterSpec("width", "Width", "W", "Geometry", 10.0,
                          minimum=0.1, maximum=1000.0, suffix=" um")
        ],
        preview_layers=[("device", "Device")],
        layer_ids={"device": [70]},
        insert_handler=insert,
    )
    return AddonSpec("org.example.my_device", "My Device", "0.1.0",
                     "Example Lab", [tool])
```

The preview uses the same insertion callback as the final layout. This keeps
preview and GDS geometry identical. Optional `validator(values)` and
`summary_renderer(values)` callbacks add blocking design checks, warnings, and
calculated information to the dialog. `ParameterSpec.visible_if` and
`enabled_if` accept dictionaries such as `{"shape": "circle"}` or
`{"pattern": ["grid", "hex"]}`.

## Installation and discovery

Open **Tools → NanoDevice → NanoDevice GUI**, then select **Add-ons**:

- **Install ZIP** validates and copies a packaged add-on to
  `%USERPROFILE%\KLayout\nanodevice-addons`.
- The manager shows that exact installation folder followed by every discovered
  add-on's name, version, functions, load status, and source path.
- **Add Development Directory** registers a source directory without copying
  it, which is useful while developing an add-on.
- **Reload** rescans installed and development add-ons without
  restarting KLayout.

Optional `ToolSpec` presentation fields:

- `icon_path`: an absolute path to a local PNG or SVG. The icon is shown in
  the Function picker; unavailable files fall back to the built-in schematic.
- `preview_policy`: `"live"` by default, or `"manual"` for expensive devices.
  A manual tool is marked Preparing after parameter changes and is generated
  only when the user clicks **Regenerate**.

Generated add-on previews are colored from each declared `layer_ids` entry and
the active LabPDK `.lyp` map. Add-ons should declare real process layer IDs
instead of relying on abstract preview-key fallbacks.

Device add-ons are not bundled or copied by `install_lymtoolkit.bat`. Keep each
device implementation in its own project and distribute it as one ZIP. The ZIP
installer copies the complete package, including Markdown and local image
resources, into `%USERPROFILE%\KLayout\nanodevice-addons\<addon-id>`. A broken
or incompatible add-on is listed as an error but does not prevent core
NanoDevice tools from loading.

Every user-selectable device/structure mode should have a dedicated local
Markdown page. Use relative image links so documentation remains complete and
offline after ZIP installation. The root README should index those pages and
map every GUI parameter group to the part of the generated structure it controls.

Configuration exports use format version 2 and include the add-on ID, add-on
version, and API version. Version 1 configurations for built-in tools remain
accepted.
# Configuration migration

`ToolSpec.config_migrator` is an optional API-v1 callback receiving a copy of
imported JSON values and returning migrated values before GUI controls are set.
Use it for renamed choices and explicit legacy defaults. It must not mutate
the input. Exceptions are reported as import errors. Core tools can omit it.
