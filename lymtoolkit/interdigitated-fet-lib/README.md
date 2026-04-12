# Interdigitated FET Library

This is a standalone KLayout PCell library for generating interdigitated FET structures.

Included PCell:
- `InterdigitatedFETPCell`

Default layers:
- Channel: `14/0`
- Source/Drain: `16/0`
- Gate: `18/0`

Install:
1. Run `lymtoolkit\install_interdigitated_fet_lib.bat`
2. Restart KLayout
3. Open the `Libraries` panel
4. Use `InterdigitatedFETLib -> InterdigitatedFETPCell`
5. Or open the GUI tool from `Tools -> InterdigitatedFET -> Interdigitated FET GUI`

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
