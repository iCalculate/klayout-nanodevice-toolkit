# KLayout Setup Backup

This folder stores the project-backed KLayout user configuration.

## Files

- `klayoutrc`: project copy of the KLayout configuration used for installation and backup.

## What is tracked here

The repository copy keeps the KLayout setup that should be reproducible across machines:

- theme and color palette
- custom key bindings and shortcut unbindings
- window, panel, and toolbar layout
- editing defaults such as grids, rulers, text, and snapping
- technology and macro path preferences

When syncing shortcut updates into this folder, the main source of truth is the `<key-bindings>` section inside the user's current `%USERPROFILE%\\KLayout\\klayoutrc`.

## Shortcut Configuration

### Active shortcut bindings

The following shortcuts are explicitly bound in the current tracked setup:

| Shortcut | Action | KLayout config key |
| --- | --- | --- |
| `B` | Switch to Box mode | `edit_menu.mode_menu.box` |
| `M` | Switch to Move mode | `edit_menu.mode_menu.move` |
| `R` | Switch to Ruler mode | `edit_menu.mode_menu.ruler` |
| `S` | Switch to Select mode | `edit_menu.mode_menu.select` |
| `P` | Switch to Polygon mode | `edit_menu.mode_menu.polygon` |
| `W` | Switch to Path mode | `edit_menu.mode_menu.path` |
| `Space` | Rotate selected object clockwise | `edit_menu.selection_menu.sel_rot_cw` |
| `F` | Zoom to selected shapes | `zoom_menu.zoom_fit_sel` |
| `L` | Show layer panel | `view_menu.show_layer_panel` |
| `1` | Select default grid 1 | `view_menu.default_grid.default_grid_1` |
| `2` | Select default grid 2 | `view_menu.default_grid.default_grid_2` |
| `3` | Select default grid 3 | `view_menu.default_grid.default_grid_3` |
| `4` | Select default grid 4 | `view_menu.default_grid.default_grid_4` |
| `5` | Select default grid 5 | `view_menu.default_grid.default_grid_5` |
| `Ctrl+M` | Move selection to typed coordinates | `edit_menu.selection_menu.sel_move_to` |
| `Ctrl+Shift+A` | Create array from selection | `edit_menu.selection_menu.make_array` |
| `Shift+L` | Change layer of selection | `edit_menu.selection_menu.change_layer` |
| `Shift+M` | Move current selection | `edit_menu.selection_menu.sel_move` |
| `Shift+S` | Scale selection | `edit_menu.selection_menu.sel_scale` |
| `Ctrl+A` | Align selection | `edit_menu.selection_menu.align` |
| `Ctrl+Shift+M` | Boolean union on selection | `edit_menu.selection_menu.union` |
| `Ctrl+D` | Distribute selection | `edit_menu.selection_menu.distribute` |
| `Ctrl+S` | Save layout | `file_menu.save` |
| `Ctrl+Shift+S` | Save layout as | `file_menu.save_as` |
| `Alt+S` | Select current cell | `zoom_menu.select_current_cell` |

### Explicitly disabled shortcuts

Entries set to `none` are intentionally disabled instead of simply left unassigned:

| Action | KLayout config key | Value |
| --- | --- | --- |
| Select next item | `@secrets.select_next_item` | `none` |
| Add next item to selection | `@secrets.select_next_item_add` | `none` |
| Max hierarchy level 1 shortcut | `zoom_menu.max_hier_1` | `none` |
| Ascend hierarchy | `zoom_menu.ascend` | `none` |
| Descend hierarchy | `zoom_menu.descend` | `none` |

### Explicitly cleared bindings

Entries set to `''` are kept in the config as intentionally blank to avoid conflicts with custom bindings or to reserve those actions for menu access only.

Key examples from the current customization:

- `edit_menu.layout_menu.lay_move` is cleared, so `Shift+M` is now dedicated to `edit_menu.selection_menu.sel_move`.
- `edit_menu.selection_menu.make_cell` is cleared.
- `edit_menu.layer_menu.edit_layer` is cleared.
- `@secrets.via` is cleared.
- multiple default file, edit, zoom, tools, macro, and panel actions are kept explicitly unbound.

## Current sync delta

Compared with the previous project copy, this update brings in the following shortcut changes from the live user config:

- added `Shift+L` for `change_layer`
- added `Shift+S` for `sel_scale`
- added `Ctrl+S` for `save`
- added `Ctrl+Shift+S` for `save_as`
- added `Alt+S` for `select_current_cell`
- added `Shift+M` for `sel_move`
- added `Ctrl+Shift+M` for `union`
- changed `distribute` from `Ctrl+Shift+D` to `Ctrl+D`
- added `Ctrl+A` for `align`
- changed `zoom_menu.ascend` from cleared to `none`
- changed `zoom_menu.descend` from cleared to `none`
- cleared `edit_menu.layout_menu.lay_move`, so it no longer occupies `Shift+M`
- synced newly present empty entries such as `edit_menu.mode_menu.Align`, `edit_menu.select_menu.pi_enable_15`, `gdsfactory`, and toolkit macro menu items

## Install

- Run `lymtoolkit/install_klayout_setup.bat` to copy this setup into `%USERPROFILE%\\KLayout\\klayoutrc`.
- The installer also creates `%USERPROFILE%\\KLayout\\klayoutrc.before_nanodevice_backup` if an existing config is present.
