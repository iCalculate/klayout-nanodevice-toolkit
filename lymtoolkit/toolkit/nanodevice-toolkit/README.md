# NanoDevice Toolkit Library

This is a standalone KLayout library for NanoDevice GUI tools and NanoDevice FET structures.

Included PCell:
- `NanoDeviceFETPCell`

Default layers:
- Channel: `14/0`
- Source/Drain: `16/0`
- Gate: `18/0`

Install:
1. Run `lymtoolkit\install_lymtoolkit.bat`
2. Restart KLayout
3. Open the `Libraries` panel
4. Use `NanoDeviceToolkitLib -> NanoDeviceFETPCell`
5. Or open the GUI tool from `Tools -> NanoDevice -> NanoDevice GUI`

GUI highlights:
- Extensible toolkit-style architecture
- Symbolic preview before insertion
- Separate `Preview`, `Insert`, and `Symbols` actions
- Parameter symbols included for future schematic/annotation diagrams

Main adjustable parameters:
- Comb region size
- Finger width / spacing / count
- Channel length
- Top/bottom bus width
- Source and drain pad size / left-stacked placement
- Source and drain lead width
- Gate cover mode: `global` or `channel_only`
- Gate enclosure grow/shrink
- Gate pad size / position
- Gate lead width
