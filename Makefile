VENV           := $(PWD)/venv
COCOTB_CONFIG  := $(VENV)/bin/cocotb-config
COCOTB_MAKE    := $(shell [ -x "$(COCOTB_CONFIG)" ] && $(COCOTB_CONFIG) --makefiles 2>/dev/null)

# Cocotb configuration variables 
TOPLEVEL_LANG = verilog
VERILOG_SOURCES := $(shell sed 's|$$ROOT_DIR|$(PWD)|g' $(PWD)/design/design.vfile)  
export VERILOG_SOURCES

TOPLEVEL = packet_mux_top
COCOTB_TEST_MODULES = packet_mux_tb
export COCOTB_TEST_MODULES

PYTHONPATH := $(PWD)/verif/tb:$(PYTHONPATH)
export PYTHONPATH

SIM = verilator
EXTRA_ARGS += -sv --trace --trace-structs


# Only include if cocotb-config is present
ifneq ($(COCOTB_MAKE),)
include $(COCOTB_MAKE)/Makefile.sim
else
$(warning cocotb-config not found. Run 'make install' first.)
endif

.PHONY: install install_verilator waves waves-clean

# Run a specific test with waveform dumping
# Usage: make waves TEST=test_basic.test_single_beat_packet
waves:
	@if [ -z "$(TEST)" ]; then \
		echo "Usage: make waves TEST=test_basic.test_single_beat_packet"; \
		exit 1; \
	fi
	@echo "Cleaning build to ensure trace support is enabled..."
	rm -rf sim_build
	@echo "Running test $(TEST) with waveform dumping..."
	$(MAKE) sim COCOTB_TEST_FILTER=$(TEST) SIM_ARGS="--trace --trace-file sim_build/dump.vcd"
	@echo ""
	@echo "Looking for VCD files..."	
	@if [ -f sim_build/dump.vcd ]; then \
		echo "Waveform file: sim_build/dump.vcd"; \
		echo "View with: gtkwave sim_build/dump.vcd"; \
	else \
		echo "Warning: No VCD file found."; \
		echo "Note: Make sure trace is enabled (--trace in EXTRA_ARGS)"; \
	fi

waves-clean:
	rm -f sim_build/*.vcd

install:
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install cocotb cocotb-bus

install_verilator:
	@echo "=== Installing Verilator 5.036 ==="
	sudo apt update
	sudo apt install -y git help2man perl python3 make g++ flex bison \
	                   libfl2 libfl-dev zlib1g-dev numactl \
	                   libgoogle-perftools-dev gtkwave
	@if [ ! -d verilator ]; then git clone https://github.com/verilator/verilator.git; fi
	cd verilator && \
		git fetch --all && \
		git checkout v5.036 && \
		autoconf && \
		./configure --prefix=/usr/local && \
		make -j$$(nproc) && \
		sudo make install
	@echo "=== Verilator installation complete ==="
	@echo "Version installed:"
	@verilator --version

