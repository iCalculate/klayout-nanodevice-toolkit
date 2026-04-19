# lymtoolkit

`lymtoolkit/` contains the KLayout-facing resources for this project: toolkit macros, PDK files, installer scripts, and now a backed-up user setup.

## Structure

```text
lymtoolkit/
  toolkit/
    nanodevice-toolkit/       # NanoDevice GUI toolkit and NanoDeviceToolkitLib
    nanodevice-pcell/         # NanoDeviceLib PCells
  PDK/                        # LabPDK technology files
  klayout_setup/              # Backed-up KLayout user configuration
  assets/                     # Icons and supporting images
  install_lymtoolkit.bat      # Install toolkit into KLayout salt
  install_pdk.bat             # Install LabPDK into KLayout tech
  install_klayout_setup.bat   # Restore saved KLayout user setup
  README.md
```

## Installers

- `install_lymtoolkit.bat`
  Installs the toolkit GUI, libraries, runtime modules, and bundled PDK runtime files into `%USERPROFILE%\KLayout\salt\nanodevice-toolkit`.

- `install_pdk.bat`
  Installs `PDK/` into `%USERPROFILE%\KLayout\tech\LabPDK` as a standalone technology bundle.

- `install_klayout_setup.bat`
  Restores `klayout_setup/klayoutrc` into `%USERPROFILE%\KLayout\klayoutrc` and makes a backup of the existing config if one is present.

## KLayout Setup Backup

The backed-up `klayoutrc` includes:

- Theme and color palette settings
- Custom key bindings and shortcuts
- Toolbar, panel, and window layout
- Editing defaults such as grids, rulers, text, and snapping
- Technology and macro path preferences
