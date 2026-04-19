# KLayout Setup Backup

This folder stores a project-backed copy of the user's KLayout configuration.

Files:
- `klayoutrc`: backed-up KLayout user setup copied from the provided reference file.

Imported categories:
- Theme and color palette
- Custom key bindings and shortcuts
- Window, panel, and toolbar layout
- Editing defaults such as grids, rulers, text, and snapping
- Technology and macro path preferences

Installer:
- Run `lymtoolkit/install_klayout_setup.bat` to copy this setup into `%USERPROFILE%\KLayout\klayoutrc`
- The installer also creates `%USERPROFILE%\KLayout\klayoutrc.before_nanodevice_backup` if an existing config is present
