# lymtoolkit

`lymtoolkit/` contains the KLayout-facing part of the NanoDevice toolkit. It is the package that gets copied into a user's KLayout environment and provides GUI macros, toolbar buttons, PCell libraries, PDK files, icons, and optional KLayout user setup.

This README is for installing, using, and maintaining the KLayout `.lym` toolkit files. The repository-root README describes the Python package more broadly.

## What Is Included

```text
lymtoolkit/
  toolkit/
    nanodevice-toolkit/       # Unified NanoDevice GUI and NanoDeviceToolkitLib
    nanodevice-pcell/         # Classic NanoDeviceLib PCells
    nanomark-toolkit/         # NanoMark GUI for writefield marks and arrays
    nanorouting-toolkit/      # NanoRouting GUI, selection import, and PCells
  PDK/                        # LabPDK KLayout technology bundle
  klayout_setup/              # Optional backed-up KLayout user configuration
  assets/                     # Toolbar icons and supporting preview images
  install_lymtoolkit.bat      # Install GUI/toolkit files into KLayout salt
  install_pdk.bat             # Install LabPDK into KLayout tech
  install_klayout_setup.bat   # Restore saved KLayout preferences
  README.md
```

The main installed modules are:

- `NanoDevice`: device-oriented layout tools, FET structures, text, QR code, fanout, mark, MOSFET, Hall, TLM, sense/latch array, and write/read array workflows.
- `NanoMark`: EBL writefield marks, general mark arrays, custom global mark grids, and text pattern arrays.
- `NanoRouting`: single-route and route-bundle generation with waypoints, obstacles, layout preview, and active-cell insertion.
- `LabPDK`: a lightweight KLayout technology with standard lab layer numbers, colors, and `dbu = 0.001`.

## Requirements

- Windows with KLayout installed.
- A normal KLayout user folder at `%USERPROFILE%\KLayout`.
- The repository should remain in its normal structure, because the installer copies `config.py`, `utils/`, `components/`, `lymtoolkit/toolkit/`, `lymtoolkit/assets/`, and `lymtoolkit/PDK/`.
- Close KLayout before reinstalling if the target folder is locked.

Some tools use optional Python dependencies at runtime, depending on the selected function. For example, the gdsfactory text helper may call an external Python interpreter with `gdsfactory` installed. If needed, set `NANODEVICE_EXTERNAL_PYTHON` to the Python executable that has the required packages.

## Recommended Installation

Run the main toolkit installer:

```bat
lymtoolkit\install_lymtoolkit.bat
```

It installs to:

```text
%USERPROFILE%\KLayout\salt\nanodevice-toolkit
```

The installer copies:

- GUI macros, toolbar scripts, and PCell library registration files.
- `config.py`, `utils/`, and `components/` runtime code.
- `assets/` icons and preview images.
- A bundled copy of `PDK/` under the installed toolkit folder.

After installation, restart KLayout.

## Optional PDK Installation

Run this if you want LabPDK available as a standalone KLayout technology:

```bat
lymtoolkit\install_pdk.bat
```

It installs to:

```text
%USERPROFILE%\KLayout\tech\LabPDK
```

Use this when you want `LabPDK` to appear in KLayout's technology list for new layouts or layout properties. The main toolkit installer already bundles a runtime copy of the PDK for toolkit use, but the standalone PDK install is cleaner for manual layout work.

## Optional KLayout Setup Restore

Run this only if you want to restore the saved KLayout UI setup:

```bat
lymtoolkit\install_klayout_setup.bat
```

It copies:

```text
lymtoolkit\klayout_setup\klayoutrc
```

to:

```text
%USERPROFILE%\KLayout\klayoutrc
```

If an existing `klayoutrc` is present, the installer backs it up as:

```text
%USERPROFILE%\KLayout\klayoutrc.before_nanodevice_backup
```

This setup restore can change theme colors, panels, shortcuts, editor defaults, macro paths, and technology preferences. Use it deliberately if you already have a customized KLayout environment.

## KLayout Entry Points

After installing and restarting KLayout, use the menu and toolbar entries:

- `Tools -> NanoDevice -> NanoDevice GUI`
- `Tools -> NanoMark -> NanoMark GUI`
- `Tools -> NanoRouting -> NanoRouting GUI`

The installed PCell libraries can also be used from KLayout's `Libraries` panel:

- `NanoDeviceLib`
- `NanoDeviceToolkitLib`
- `NanoRoutingLib`

## NanoDevice Toolkit

`toolkit/nanodevice-toolkit/` provides the main NanoDevice GUI and newer PCell library.

Typical workflow:

1. Open or create a layout in KLayout.
2. Launch `Tools -> NanoDevice -> NanoDevice GUI`.
3. Choose a function from the function selector.
4. Adjust parameters in the left panel.
5. Use `Preview` to refit the preview canvas.
6. Use `Insert` to place the generated geometry into the active cell.
7. Use `Import Config` / `Export Config` to reuse parameter sets.

Included GUI functions include:

- NanoDevice FET
- gdsfactory/KLayout text
- MOSFET component
- Hall component
- TLM component
- Sense / Latch Array
- Write / Read Array

The GUI uses live preview layers and can insert either registered PCell variants or directly generated Python component layouts, depending on the selected tool.

## Classic NanoDevice PCells

`toolkit/nanodevice-pcell/` contains smaller PCell wrappers for the classic library:

- `TextPCell`
- `QRCodePCell`
- `DigitalPCell`
- `FanoutPCell`
- `MarkPCell`
- `NanoDeviceClassicFETPCell`

These are useful when you want parameterized cells directly from KLayout's `Libraries` panel rather than using the larger GUI dialogs.

## NanoMark Toolkit

`toolkit/nanomark-toolkit/` provides mark generation workflows for lithography alignment and writefield planning.

Included tools:

- EBL Writefield Mark
- Custom Global Mark Grid
- Text Pattern Array
- General Mark Array

Features:

- Live PyQt preview with pan and zoom.
- Layer visibility toggles.
- KLayout `.lyp` color loading for preview styling.
- JSON import/export for repeatable mark layouts.
- Direct insertion of generated geometry into the active KLayout cell.

## NanoRouting Toolkit

`toolkit/nanorouting-toolkit/` provides interactive routing for single paths and bundles.

Included library cells:

- `NanoRoutingPathPCell`
- `NanoRoutingBundlePCell`

GUI features:

- Single-route and bundle-route modes.
- Manhattan and diagonal route options.
- Waypoints, obstacle rectangles, clearance, width, and spacing controls.
- Live preview in the dialog.
- `Preview In Layout`, which writes temporary geometry into a dedicated `__NANOROUTING_PREVIEW__` cell.
- `Clear Preview`, which clears only that preview cell.
- `Insert`, which writes final route geometry into the active cell.
- `Use Selection` helpers that can read selected KLayout shapes as starts, ends, waypoints, or obstacles.

Selection import behavior:

- Selected shape centers are used for route points.
- Selected shape bounding boxes are used for obstacle regions.

## LabPDK

`PDK/` contains the `LabPDK` technology definition.

Important settings:

- Technology name: `LabPDK`
- Database unit: `0.001` microns, so 1 database unit is 1 nm
- Layer display: `PDK/layers/layer_map.lyp`

Common layer ranges:

| Range | Purpose |
| --- | --- |
| `1-10` | Mark system, chip boundary, active region, alignment marks, calipers |
| `11-20` | Device stack 1 |
| `21-29` | Device stack 2 |
| `31-40` | Interconnect metal and via layers |
| `41-42` | Bonding pads and probe contacts |
| `61, 63` | EBL automatic/manual alignment |

See `PDK/README.md` for more detailed technology notes.

## Configuration Files

The toolkit relies on runtime files copied from the repository root:

- `config.py`: layer definitions, default database unit, and shared constants.
- `utils/`: geometry, text, QR code, mark, fanout, routing, and helper utilities.
- `components/`: higher-level layout generators used by the GUI tools.

When changing layer definitions or component behavior, reinstall with:

```bat
lymtoolkit\install_lymtoolkit.bat
```

Then restart KLayout so the updated macro code is reloaded.

## Updating an Existing Installation

Recommended update procedure:

1. Close KLayout.
2. Pull or copy the updated repository files.
3. Run `lymtoolkit\install_lymtoolkit.bat`.
4. Optionally run `lymtoolkit\install_pdk.bat` if `PDK/` changed.
5. Restart KLayout.

The main installer removes the old salt installation before copying the new files. This avoids stale macro files, but it also means any manual edits inside `%USERPROFILE%\KLayout\salt\nanodevice-toolkit` will be lost. Make source edits in the repository, not in the installed copy.

## Troubleshooting

If toolbar buttons or menu entries do not appear:

- Restart KLayout after installation.
- Confirm the installed folder exists at `%USERPROFILE%\KLayout\salt\nanodevice-toolkit`.
- Check KLayout's macro log for import errors.

If a GUI opens but insertion fails:

- Make sure a layout and active cell are open.
- Confirm the target layers exist or let KLayout add missing layers.
- Check whether the selected function needs optional Python packages.

If gdsfactory text generation fails:

- Install `gdsfactory` into an external Python environment.
- Set `NANODEVICE_EXTERNAL_PYTHON` to that Python executable.
- Restart KLayout and try again.

If reinstall fails:

- Close KLayout.
- Check that `%USERPROFILE%\KLayout\salt\nanodevice-toolkit` is not locked.
- Run the installer again from a normal command prompt.

## Maintenance Notes

- Keep `.lym` toolbar/register files small; put substantial Python logic in `.py` files.
- Use repository-relative root discovery in macro scripts because KLayout may launch them from a different working directory.
- Prefer shared code in `utils/` and `components/` over duplicating geometry logic inside macros.
- Add English comments around KLayout lifecycle hooks, unit conversion, layer mapping, and external-process calls.
- Avoid editing generated or installed `__pycache__` folders.
