# Packet Mux Design

A SystemVerilog packet multiplexer design with priority-based arbitration, implementing Avalon-ST (Avalon Streaming) interfaces. 
The design multiplexes packets from two input ports (high priority Port A and low priority Port B) to a single output port (Port C).

## Features

- **Priority-based arbitration**: Port A has higher priority than Port B
- **Avalon-ST interface**: Full support for Avalon Streaming protocol
- **Skid buffers**: Handles backpressure with minimal latency on Port A
- **Deep FIFO buffering**: Port B uses a 512-deep FIFO for buffering
- **Comprehensive test suite**: Cocotb-based verification with multiple test scenarios

## Prerequisites

- Python 3.10 or later
- Make
- GCC/G++ compiler
- Verilator 5.036 (for simulation)
- GTKWave (optional, for waveform viewing)

## Installation

### 1. Run Installation Script

First, run the installation script to set up system dependencies and the Python environment:

```bash
./install.sh
```

This will:
- Install system packages (build-essential, python3-dev, python3-virtualenv, make, gcc)
- Set `ROOT_DIR` environment variable
- Create a Python virtual environment in `venv/` (if it doesn't exist)
- Install `cocotb` and `cocotb-bus` in the virtual environment
- Activate the virtual environment

**Note**: This script requires sudo privileges for installing system packages.

### 2. Install Verilator (if not already installed)

Install Verilator 5.036:

```bash
make install_verilator
```

**Note**: This requires sudo privileges and will install Verilator system-wide.

### 3. Set Environment Variables (Optional)

The `install.sh` script automatically sets `ROOT_DIR`. If you need to set it manually in a new terminal session:

```bash
export ROOT_DIR=$PWD
```

## Usage

### Running Tests

#### Run All Tests

```bash
make sim
```

#### Run a Specific Test Module

```bash
make sim COCOTB_TEST_FILTER=test_basic
```

#### Run a Specific Test Function

```bash
make sim COCOTB_TEST_FILTER=test_basic.test_single_beat_packet
```

### Generating Waveforms

To run a test with waveform dumping:

```bash
make waves TEST=test_basic.test_single_beat_packet
```

This will:
- Clean the build directory
- Run the specified test with VCD tracing enabled
- Display the location of the generated waveform file

View the waveform with GTKWave:

```bash
gtkwave sim_build/dump.vcd
```

### Cleaning

Clean waveform files:

```bash
make waves-clean
```

Clean build directory:

```bash
rm -rf sim_build
```

## Test Suite

The verification suite includes the following test modules:

- **test_basic.py**: Basic functionality tests (single packets, multiple packets)
- **test_priority.py**: Priority arbitration tests
- **test_backpressure.py**: Backpressure handling tests
- **test_stress.py**: Stress tests (high frequency, alternating ports)
- **test_edge_cases.py**: Edge case scenarios
- **test_error_handling.py**: Error signal handling tests

## Project Structure

```
packet_mux2/
├── design/
│   ├── src/
│   │   ├── packet_mux_top.sv    # Top-level module
│   │   ├── packet_mux_pkg.sv    # Package definitions
│   │   ├── arbiter.sv           # Priority arbiter
│   │   ├── skid_buffer.sv       # Skid buffer implementation
│   │   └── sync_fifo.sv         # Synchronous FIFO
│   └── design.vfile             # Source file list
├── verif/
│   └── tb/
│       ├── test_basic.py
│       ├── test_priority.py
│       ├── test_backpressure.py
│       ├── test_stress.py
│       ├── test_edge_cases.py
│       ├── test_error_handling.py
│       ├── drivers/              # Avalon-ST drivers
│       ├── monitors/             # Avalon-ST monitors
│       ├── utils/                # Test utilities
│       └── test_helpers/         # Test fixtures
├── Makefile                      # Build and test automation
├── source.me                     # Environment setup script
└── README.md                     # This file
```

## Design Overview

The packet mux consists of:

1. **Port A Path**: High-priority input with skid buffer for minimal latency
2. **Port B Path**: Low-priority input with skid buffer + 512-deep FIFO
3. **Arbiter**: Priority-based multiplexer that selects between Port A and Port B
4. **Output Port C**: Single output stream

### Interface

All ports use Avalon-ST interface with:
- `data`: 64-bit data bus
- `valid`: Data valid signal
- `ready`: Backpressure signal
- `sop`: Start of packet
- `eop`: End of packet
- `empty`: Empty bytes in last beat (3 bits)
- `error`: Error indicator

## Make Targets

| Target | Description |
|--------|-------------|
| `install_verilator` | Install Verilator 5.036 simulator |
| `sim` | Run all tests |
| `waves` | Run a specific test with waveform dumping |
| `waves-clean` | Remove waveform files |

## Troubleshooting

### "cocotb-config not found" Warning

If you see this warning, run:
```bash
make install
```

### "Couldn't find makefile for simulator: verilator"

This indicates Verilator is not installed or not in PATH. Install it with:
```bash
make install_verilator
```

### ModuleNotFoundError: No module named 'cocotb_tools'
make sure to activate virtualenv 
```bash
source venv/bin/activate
```




