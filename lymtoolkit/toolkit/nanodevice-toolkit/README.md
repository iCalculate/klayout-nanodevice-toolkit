# NanoDevice Toolkit Library

This is a standalone KLayout library for NanoDevice GUI tools and NanoDevice FET structures.

The GUI also includes a component-based **HEMT Device** generator. It supports
single-finger `S-G-D` and symmetric double-finger `S-G-D-G-S` layouts with
independent controls for gate length/width, source and drain access spacing,
ohmic dimensions, mesa margins, optional gate dielectric, and compact outer
gate/source/drain metal fields.

For a single-finger device, gate pads are placed on both the left and right;
source and drain occupy the upper and lower fields. Their internal landing and
fanout are one complete trapezoid ending at a separate, solid rectangular outer
pad. The combined internal-pad/fanout trapezoid can be solid or hollow with a
configurable conductive frame width. Hollowing applies only to the
single-finger source/drain or the double-finger sources. Single-finger gates
use symmetric solid triangles on both sides; the common double-finger gate uses
a solid trapezoid whose inner edge covers the two-finger manifold.

HEMT alignment marks can be disabled, placed at the four device corners, or
placed at four corners plus the four side midpoints. Cross, box-frame, and
diamond marks are supported with adjustable size, line width, and independent
X/Y margins. Marks are written to the alignment-mark layer (`3/0`).

The active Mesa is centred on the requested device origin and sized from the
effective contact stack plus X/Y Mesa margins. Every gate finger extends past
both Mesa edges. `Gate Pad Edge = 0` tracks `Outer Metal Depth` automatically,
while a non-zero value overrides it. `Gate Control Margin` limits the effective
vertical contact edge so it remains narrower than the gate coverage.

`Mesa Width = 0` keeps the automatic contact-based Mesa width. A non-zero
value sets the centred Mesa width explicitly and may be smaller than `Gate
Width`, allowing the etched Mesa to define the effective channel width.
Changing `Mesa Width` does not pull the double-finger drain fanout into the
active core: the centre drain remains narrow until it clears the gate/Mesa
region. Upper and lower source structures remain mirror-symmetric about the
device centreline.

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
