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
- [Dependencies](#dependencies)
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

## Installation & Setup

### Prerequisites

1. **System Requirements**
   - [KLayout](https://www.klayout.de/) >= 0.28
   - Python >= 3.7
   - Git (for cloning the repository)

2. **Operating System Support**
   - Windows 10/11
   - macOS 10.14+
   - Linux (Ubuntu 18.04+, CentOS 7+)

### Installation

#### Prerequisites
- **KLayout** >= 0.28 ([Download](https://www.klayout.de/))
- **Python** >= 3.7
- **Git** (for cloning)

#### Quick Setup
```bash
# 1. Clone repository
git clone https://github.com/yourusername/klayout-nanodevice-toolkit.git
cd klayout-nanodevice-toolkit

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

#### Configure KLayout
1. **Launch KLayout**
2. **Add project to Python path**: Tools → Manage Packages → Add Path
3. **Navigate to your project directory** and click "OK"

#### Verify Installation
In KLayout Python Console (Tools → Python Console):
```python
# Test imports
import pya
from layout_generator import LayoutGenerator
print("✅ Installation successful!")
```

### Dependencies

#### Required
- **freetype-py** >= 2.3.0 - Text rendering for layout labels
- **pya** - KLayout Python API (included with KLayout)
- **klayout.db** - KLayout database module (included with KLayout)

#### Optional
- **numpy** >= 1.21.0 - Numerical operations
- **pandas** >= 1.3.0 - Data analysis
- **matplotlib** >= 3.4.0 - Plotting and visualization

#### Development
- **pytest** >= 6.0.0 - Testing framework
- **black** >= 21.0.0 - Code formatting
- **flake8** >= 3.9.0 - Code linting

### Troubleshooting

**Common Issues:**

1. **ImportError: No module named 'pya'**
   - Solution: Run code within KLayout's Python environment, not standalone Python

2. **ModuleNotFoundError: No module named 'layout_generator'**
   - Solution: Add project directory to KLayout's Python path (Tools → Manage Packages)

3. **AttributeError: 'Layout' object has no attribute '...'**
   - Solution: Update KLayout to version 0.28 or higher

4. **ImportError: No module named 'freetype'**
   - Solution: Run `pip install -r requirements.txt`

### Development Setup

For contributors:
```bash
pip install -r requirements.txt
pip install black flake8 pytest
```

---

## Quick Start

### First Time Setup
1. **Complete the installation** (see [Installation & Setup](#installation--setup) above)
2. **Launch KLayout**
3. **Open Python Console** (Tools → Python Console)

### Basic Usage

**Option 1: Run the Interactive Main Program**
```python
# In KLayout Python Console
exec(open('main.py').read())
```
This will show an interactive menu where you can choose different operations.

**Option 2: Create a Simple Device Array**
```python
# In KLayout Python Console
from layout_generator import LayoutGenerator

# Create generator
generator = LayoutGenerator()

# Configure array
generator.set_array_config(
    rows=3, 
    cols=3, 
    spacing_x=100, 
    spacing_y=100
)

# Configure parameter scan
generator.set_scan_config(
    channel_width_range=[3, 5, 7], 
    channel_length_range=[10, 20, 30], 
    scan_type='grid'
)

# Generate and save
generator.generate_layout()
generator.save_layout("my_device_array.gds")
generator.load_to_gui()  # View in KLayout
```

**Option 3: Launch the GUI Interface**
```python
# In KLayout Python Console
from gui_interface import show_mosfet_layout_gui
show_mosfet_layout_gui()
```

### Quick Examples

**Create a Single Device**
```python
from components.mosfet import MOSFET

device = MOSFET(
    x=0, y=0,
    channel_width=5.0,
    channel_length=20.0,
    gate_overlap=2.0,
    device_label="Test_Device"
)
device.generate()
```

**Create a Parameter Sweep Array**
```python
from layout_generator import LayoutGenerator

generator = LayoutGenerator()
generator.set_array_config(rows=5, cols=5, spacing_x=80, spacing_y=80)
generator.set_scan_config(
    channel_width_range=[2, 3, 4, 5, 6],
    channel_length_range=[5, 10, 15, 20, 25],
    scan_type='custom'
)
generator.generate_layout()
generator.save_layout("parameter_sweep.gds")
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