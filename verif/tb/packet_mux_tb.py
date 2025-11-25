"""
Main testbench file - imports all test modules
This file is kept for backward compatibility and imports all test modules.
"""
# Import all test modules to register tests with cocotb
# Using star imports to bring test functions into this module's namespace
# so cocotb can discover them when it loads this module
from test_basic import *
from test_priority import *
from test_backpressure import *
from test_error_handling import *
from test_edge_cases import *
from test_stress import *
