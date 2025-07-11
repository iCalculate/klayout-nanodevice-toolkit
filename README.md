# KLayout Semiconductor Device Layout Generator

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![KLayout](https://img.shields.io/badge/KLayout-0.28+-green.svg)](https://www.klayout.de/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Overview

**KLayout Semiconductor Device Layout Generator** is a modular, extensible Python toolkit designed for rapid and professional semiconductor device layout generation within [KLayout](https://www.klayout.de/). This project streamlines the creation of MOSFET arrays, parameter sweeps, and complex device structures, integrating advanced features such as alignment marks, text annotations, and flexible fanout routing. It is suitable for both academic research and industrial prototyping.

---

## Features

- **Modular Architecture**: Clean separation of device components, utilities, and configuration for easy maintenance and extension.
- **Comprehensive Device Support**: Dual-gate MOSFETs, custom electrode shapes, and parameterized device arrays.
- **Flexible Parameter Sweep Engine**: Supports grid, random, and user-defined parameter scanning for systematic or statistical studies.
- **Advanced Fanout and Marking System**: Multiple routing styles and professional alignment/measurement marks.
- **Seamless KLayout GUI Integration**: Native interface for real-time layout preview and interactive design.
- **Multi-language Text Annotation**: Built-in utilities for device labeling and documentation.
- **Process-aware Configuration**: Centralized layer and process parameter management for design rule compliance.

---

## Table of Contents

- [Project Structure](#project-structure)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Examples](#usage-examples)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)

---

## Project Structure

```
klayout-nanodevice-toolkit/
├── main.py                # Main entry point
├── layout_generator.py    # Core layout engine
├── gui_interface.py       # KLayout GUI integration
├── components/            # Device modules (MOSFET, electrodes)
├── utils/                 # Geometry, text, mark, fanout utilities
├── config.py              # Layer and process config
└── README.md
```

---

## Installation

1. **Requirements**
   - [KLayout](https://www.klayout.de/) >= 0.28
   - Python >= 3.7

2. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/klayout-nanodevice-toolkit.git
   cd klayout-nanodevice-toolkit
   ```

3. **(Optional) Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install dependencies**
   > Most dependencies are standard Python libraries. If you use extra packages, list them here or in `requirements.txt`.

---

## Quick Start

**Run the main program:**
```python
exec(open('main.py').read())
```

**Create a device array:**
```python
from layout_generator import LayoutGenerator

generator = LayoutGenerator()
generator.set_array_config(rows=3, cols=3, spacing_x=100, spacing_y=100)
generator.set_scan_config(channel_width_range=[3,5,7], channel_length_range=[10,20,30], scan_type='grid')
generator.generate_layout()
generator.save_layout("device_array.gds")
generator.load_to_gui()
```

---

## Usage Examples

**Custom Device Creation**
```python
from components.mosfet import MOSFET

device = MOSFET(
    x=0, y=0,
    channel_width=5.0,
    channel_length=20.0,
    gate_overlap=2.0,
    device_label="Custom_Device",
    fanout_enabled=True
)
device.generate()
```

**Launch the KLayout GUI Interface**
```python
from gui_interface import show_mosfet_layout_gui
show_mosfet_layout_gui()
```

---

## Configuration

All global settings, layer definitions, and process parameters are managed in `config.py`. This includes:

- **Layer Definitions**: Assign layer IDs, names, and colors for each process step.
- **Process Parameters**: Set minimum feature size, spacing, overlap, and database units.
- **Extensibility**: Easily add new device types or routing styles by extending the `components/` and `utils/` modules.

For advanced configuration and extension, please refer to the [detailed documentation](docs/README.md).

---

## Troubleshooting

- **ImportError**: Ensure your Python path and module names are correct.
- **Layer Conflicts**: Check for duplicate or conflicting layer IDs in `config.py`.
- **GUI Issues**: Make sure your KLayout version is >= 0.28.
- **Parameter Errors**: Validate parameter ranges and types in your scripts.

If you encounter issues, please check the [FAQ](docs/README.md#faq) or open an issue.

---

## Contributing

Contributions are welcome! Please read our [contributing guidelines](CONTRIBUTING.md) and submit pull requests or issues to help improve this project.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Acknowledgements

- Built on top of the excellent [KLayout](https://www.klayout.de/) platform.
- Inspired by open-source EDA and device design communities.

---

> For more advanced usage, development guides, and API reference, please see [docs/README.md](docs/README.md). 