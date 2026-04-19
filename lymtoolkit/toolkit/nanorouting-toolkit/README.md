# NanoRouting Toolkit

Install:
1. Run `lymtoolkit\install_lymtoolkit.bat`
2. Restart KLayout
3. Open `Tools -> NanoRouting -> NanoRouting GUI`
4. Or click the `NanoRouting` toolbar button

Included:
- `NanoRoutingLib -> NanoRoutingPathPCell`
- `NanoRoutingLib -> NanoRoutingBundlePCell`
- Interactive NanoRouting GUI with preview

Viewport interaction:
- Select shapes in KLayout, then use `Use Selection -> Starts/Ends/Obstacles`
- Selected shape centers become route points
- Selected shape bounding boxes become obstacle regions

Preview:
- Dialog preview updates from current parameters
- `Preview In Layout` writes a temporary `__NANOROUTING_PREVIEW__` cell into the current layout
- `Insert` commits the routing into the active cell
