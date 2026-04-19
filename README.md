# KLayout Nanodevice Toolkit

<p align="center">
  <a href="docs/README_CN.md"><strong>中文文档</strong></a>
  ·
  <a href="docs/README_EN.md"><strong>English Mirror</strong></a>
</p>

<p align="center">
  <img src="lymtoolkit/assets/logo.ico" alt="KLayout Nanodevice Toolkit logo" width="120" />
</p>

<p align="center">
  <strong>A Python-first toolkit for generating semiconductor device layouts, parameter sweeps, grayscale patterns, and KLayout macros from one workspace.</strong>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" alt="Python 3.11+" /></a>
  <a href="https://www.klayout.de/"><img src="https://img.shields.io/badge/KLayout-0.27%2B-2E8B57" alt="KLayout 0.27+" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-F4B400" alt="MIT License" /></a>
</p>

## Why This Repo

This project brings together several layout workflows that are usually scattered across scripts, macros, and one-off experiments:

- Parametric device generation for MOSFET, FET, Hall bar, TLM, meander, and electrode structures
- Array and parameter-scan generation with export to `output/`
- GUI-based layout configuration through `gui_interface.py`
- KLayout macro and PDK tooling under `lymtoolkit/`
- Grayscale and image-based pattern generation for nanofabrication workflows

If you want one place to prototype, generate, and iterate on device layouts in Python while still supporting KLayout-native workflows, this repo is the working surface.

## At A Glance

| Workflow | Entry Point | What It Does |
| --- | --- | --- |
| Python scripting | `main.py`, `layout_generator.py` | Build device arrays and save GDS layouts programmatically |
| Desktop GUI | `gui_interface.py` | Configure array size, scan parameters, device options, and output path |
| KLayout macros | `lymtoolkit/install_lymtoolkit.bat` | Install toolkit macros into KLayout for interactive use |
| PDK tooling | `lymtoolkit/PDK/` | Keep technology files, layers, examples, and registration macros together |
| Grayscale patterns | `components/greyscale/` | Generate grayscale lithography assets and image-derived structures |

## Visual Preview

<p align="center">
  <img src="lymtoolkit/assets/singleFET.png" alt="Single FET example" width="31%" />
  <img src="lymtoolkit/assets/arrayFET.png" alt="FET array example" width="31%" />
  <img src="lymtoolkit/assets/arrayTLM.png" alt="TLM array example" width="31%" />
</p>

## Quick Start

### 1. Create the environment

```bash
conda env create -f environment.yml
conda activate klayout-nanodevice-toolkit
pip install -r requirements.txt
```

The checked-in `environment.yml` already targets `python=3.11`, so the old Python-version workaround is no longer needed.

### 2. Sanity-check the install

```bash
python --version
python -c "import gdsfactory; print('gdsfactory ready')"
python -c "import klayout.db as kdb; print('klayout python api ready')"
```

### 3. Run a workflow

Programmatic generation:

```bash
python main.py
```

Standalone GUI:

```bash
python gui_interface.py
```

KLayout macro setup on Windows:

```bash
.\lymtoolkit\install_lymtoolkit.bat
```

## Example

```python
from layout_generator import LayoutGenerator

gen = LayoutGenerator()
gen.set_array_config(rows=3, cols=3, spacing_x=100, spacing_y=100)
gen.set_scan_config(
    channel_width_range=[2.0, 4.0, 6.0],
    channel_length_range=[10.0, 20.0, 30.0],
    gate_overlap_range=[1.0, 2.0, 3.0],
    scan_type="grid",
)
gen.generate_layout()
gen.save_layout("device_array.gds")
```

Generated GDS files are written to `output/`, and grayscale image outputs are written to `output/grayscaleImg/`.

## Repository Map

```text
KLayout_Nanodevice_Toolkit/
|-- components/                 Parametric device modules and grayscale generators
|-- docs/                       Supporting docs and language-specific entry pages
|-- lymtoolkit/                 KLayout macros, install scripts, toolkit integration, and PDK assets
|-- output/                     Generated layouts and image outputs
|-- utils/                      Geometry, fanout, labels, marks, QR, and helper utilities
|-- config.py                   Process, layer, font, and output-path configuration
|-- gui_interface.py            Desktop GUI for layout configuration
|-- layout_generator.py         Core array and sweep generation logic
|-- main.py                     Simple entry script and example launcher
|-- environment.yml             Conda environment definition
`-- requirements.txt            Pip dependencies
```

## Core Modules

### Device generators

- `components/mosfet.py`: dual-gate MOSFET layout generation
- `components/fet.py`: FET-focused parametric structures
- `components/hallbar.py`: Hall bar generators
- `components/tlm.py`: transfer-length-method structures
- `components/electrode.py`: electrode and pad geometries
- `components/meander.py`: meander-style routing or structures
- `components/resolution.py`: resolution-test patterns

### Utility layer

- `utils/geometry.py`: geometry primitives and shape operations
- `utils/fanout_utils.py`: fanout routing and pad-array helpers
- `utils/mark_utils.py`: alignment and registration marks
- `utils/text_utils.py`: layout text generation and placement
- `utils/QRcode_utils.py`: QR code generation for layout embedding
- `utils/alignment_utils.py`: overlay and alignment helpers

### KLayout integration

- `lymtoolkit/toolkit/nanodevice-toolkit/`: toolkit-facing KLayout macros and library registration
- `lymtoolkit/toolkit/nanodevice-pcell/`: PCell-oriented macro modules
- `lymtoolkit/PDK/`: technology definition, layer map, examples, and registration macro

## Recommended Reading

- [Chinese documentation](docs/README_CN.md)
- [Environment setup notes](docs/ENV_SETUP.md)
- [Quick start notes](docs/QUICK_START.md)
- [KLayout toolkit notes](lymtoolkit/README.md)

## Known Boundaries

- The current top-level generator centers on the MOSFET-style array workflow in `layout_generator.py`
- Some folders contain experimental or lab-specific templates alongside production utilities
- KLayout GUI loading requires a working KLayout environment; pure Python execution can still generate files offline

## License

MIT. See [LICENSE](LICENSE).
