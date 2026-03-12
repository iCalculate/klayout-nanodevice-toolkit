# LabPDK — Lightweight research PDK for KLayout

LabPDK standardizes layer usage for device layout design in the lab. It provides a fixed global layer numbering convention, a layer display file, and a Python helper for scripts.

## Technology settings

- **Technology name:** LabPDK  
- **Database unit:** `dbu = 0.001` (1 database unit = 1 nm)  
- **Layer display:** Loaded from `layers/layer_map.lyp`

## Layer numbering convention

All layers use **datatype = 0**. Layer numbers:

| Range   | Purpose |
|--------|---------|
| **61, 63** | EBL alignment (61: auto mark scan, 63: manual mark scan) |
| **1–10**   | Mark system: chip boundary (1), active region (2), primary/complementary alignment marks (3–4), caliper (5), 6–10 reserved |
| **11–20**  | Device stack 1: bottom gate (11), bottom dielectric (12), n/p semiconductor (13–14), n/p contact metal (15–16), top dielectric (17), top gate (18), 19–20 reserved |
| **21–29**  | Device stack 2: same roles as 11–19 for stacked devices |
| **31–40**  | Interconnect: Metal1 (31), Via1 (32), Metal2 (33), Via2 (34), … Metal5 (39), Via5 (40) |
| **41–42**  | Bonding pad (41), probe test contact (42) |

See `layers/layer_table.yaml` for the full list with names and categories.

## Install

1. Copy the entire PDK folder to KLayout’s technology directory so that `technology.lyt` lies in a folder named `LabPDK`.

   **Example (Linux / macOS):**
   ```bash
   cp -r /path/to/lymtoolkit/PDK ~/.klayout/tech/LabPDK
   ```
   So the layout is:
   ```
   ~/.klayout/tech/LabPDK/
   ├── technology.lyt
   ├── layers/
   │   ├── layer_map.lyp
   │   ├── layers.py
   │   └── layer_table.yaml
   ├── macros/
   │   ├── init.py
   │   └── register_labpdk.lym
   └── README.md
   ```

   **Windows:** use `%USERPROFILE%\.klayout\tech\LabPDK\` (e.g. `C:\Users\<You>\.klayout\tech\LabPDK\`).

2. In KLayout, run the macro once to register the technology:  
   **LabPDK → Register LabPDK Technology**  
   (Or run the code in `macros/init.py` so that `register_labpdk()` is called.)

3. When creating a new layout or in **File → Layout Properties**, set technology to **LabPDK**. The layer colors and dbu will be applied.

## Using layers in Python scripts

Use the `Layers` helper so that `L.<name>` gives the layout layer index for `cell.shapes(L.<name>)`:

```python
import pya
# Add PDK layers to path if not under tech/LabPDK
# sys.path.insert(0, r"C:\Users\Admin\.klayout\tech\LabPDK\layers")
from layers.layers import Layers

layout = pya.Layout()
layout.dbu = 0.001   # 1 nm
layout.technology_name = "LabPDK"
L = Layers(layout)
cell = layout.create_cell("Top")

# Draw on specific layers
cell.shapes(L.METAL1).insert(pya.Box(0, 0, 1000, 500))
cell.shapes(L.PAD).insert(pya.Box(0, 0, 10000, 10000))
cell.shapes(L.BOTTOM_GATE).insert(pya.Box(100, 100, 2000, 800))
```

Class-level constants are `(layer, datatype)` tuples, e.g. `Layers.METAL1` → `(31, 0)`.

## Example layout script

See `examples/example_layout.py` for a small script that draws:

- **Alignment:** chip mechanical boundary (layer 1), primary alignment mark (layer 3, cross).
- **Device:** bottom gate (layer 11).
- **Interconnect:** Metal1 wire and Via1 (layers 31, 32).
- **Probe:** bonding pad (layer 41).

Run from KLayout: open Macro Development, add the `examples` folder to the path if needed, then run `example_layout.py`. You can adapt the script to insert into the current layout instead of creating a new one.

## File overview

- `technology.lyt` — Technology definition (name, dbu, layer properties file).
- `layers/layer_map.lyp` — Layer display (colors/fill by category).
- `layers/layer_table.yaml` — Structured layer list (name, layer, datatype, category, description).
- `layers/layers.py` — Python `Layers` class for script access.
- `macros/init.py` — Registers LabPDK technology.
- `macros/register_labpdk.lym` — KLayout macro that runs the registration.
