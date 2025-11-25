"""
Common test fixtures and setup functions
"""
import cocotb
from cocotb.clock import Clock
from drivers.avalon_st_driver import AvalonSTSource
from monitors.avalon_st_monitor import AvalonSTSink
from utils.test_utils import reset_dut, setup_clock


def create_test_environment(dut):
    """
    Create a standard test environment with clock, drivers, and monitor.
    
    Args:
        dut: Device under test
    
    Returns:
        Dictionary with 'clock', 'src_a', 'src_b', 'sink_c'
    """
    # Setup clock
    clock = setup_clock(dut)
    cocotb.start_soon(clock)
    
    # Create drivers
    src_a = AvalonSTSource(
        clk   = dut.clk,
        data  = dut.porta_data,
        valid = dut.porta_valid,
        sop   = dut.porta_sop,
        eop   = dut.porta_eop,
        empty = dut.porta_empty,
        error = dut.porta_error,
        ready = dut.porta_ready,
    )
    
    src_b = AvalonSTSource(
        clk   = dut.clk,
        data  = dut.portb_data,
        valid = dut.portb_valid,
        sop   = dut.portb_sop,
        eop   = dut.portb_eop,
        empty = dut.portb_empty,
        error = dut.portb_error,
        ready = dut.portb_ready,
    )
    
    # Create monitor
    sink_c = AvalonSTSink(
        clk   = dut.clk,
        data  = dut.portc_data,
        valid = dut.portc_valid,
        sop   = dut.portc_sop,
        eop   = dut.portc_eop,
        empty = dut.portc_empty,
        error = dut.portc_error,
        ready = dut.portc_ready,
    )
    
    return {
        'clock': clock,
        'src_a': src_a,
        'src_b': src_b,
        'sink_c': sink_c
    }

