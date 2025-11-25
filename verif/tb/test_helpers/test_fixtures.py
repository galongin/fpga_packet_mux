"""
Common test fixtures and setup functions
"""
import cocotb
from cocotb.clock import Clock
from drivers.avalon_st_driver import AvalonSTSource, AvalonSTQueuedSource
from monitors.avalon_st_monitor import AvalonSTSink, AvalonSTSinkWithBackpressure
from utils.test_utils import reset_dut, setup_clock, wait_cycles


def _get_port_a_signals(dut):
    """Get signal dictionary for port A."""
    return {
        'clk': dut.clk,
        'data': dut.porta_data,
        'valid': dut.porta_valid,
        'sop': dut.porta_sop,
        'eop': dut.porta_eop,
        'empty': dut.porta_empty,
        'error': dut.porta_error,
        'ready': dut.porta_ready,
    }


def _get_port_b_signals(dut):
    """Get signal dictionary for port B."""
    return {
        'clk': dut.clk,
        'data': dut.portb_data,
        'valid': dut.portb_valid,
        'sop': dut.portb_sop,
        'eop': dut.portb_eop,
        'empty': dut.portb_empty,
        'error': dut.portb_error,
        'ready': dut.portb_ready,
    }


def _get_port_c_signals(dut):
    """Get signal dictionary for port C."""
    return {
        'clk': dut.clk,
        'data': dut.portc_data,
        'valid': dut.portc_valid,
        'sop': dut.portc_sop,
        'eop': dut.portc_eop,
        'empty': dut.portc_empty,
        'error': dut.portc_error,
        'ready': dut.portc_ready,
    }


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
    src_a = AvalonSTSource(**_get_port_a_signals(dut))
    src_b = AvalonSTSource(**_get_port_b_signals(dut))
    
    # Create monitor
    sink_c = AvalonSTSink(**_get_port_c_signals(dut))
    
    return {
        'clock': clock,
        'src_a': src_a,
        'src_b': src_b,
        'sink_c': sink_c
    }


def create_sink_with_backpressure(dut):
    """
    Create an Avalon-ST sink monitor with backpressure control for port C.
    
    Args:
        dut: Device under test
    
    Returns:
        AvalonSTSinkWithBackpressure instance
    """
    return AvalonSTSinkWithBackpressure(**_get_port_c_signals(dut))


def create_queued_source_a(dut):
    """
    Create an Avalon-ST queued source driver for port A.
    
    Args:
        dut: Device under test
    
    Returns:
        AvalonSTQueuedSource instance for port A
    """
    return AvalonSTQueuedSource(**_get_port_a_signals(dut))


def create_queued_source_b(dut):
    """
    Create an Avalon-ST queued source driver for port B.
    
    Args:
        dut: Device under test
    
    Returns:
        AvalonSTQueuedSource instance for port B
    """
    return AvalonSTQueuedSource(**_get_port_b_signals(dut))


async def setup_test_with_idle_port(dut, idle_port='b'):
    """
    Common test setup: create environment, reset, start sink, and set one port idle.
    
    Args:
        dut: Device under test
        idle_port: Which port to set idle ('a' or 'b', default 'b')
    
    Returns:
        Dictionary with test environment (same as create_test_environment)
    """
    env = create_test_environment(dut)
    await reset_dut(dut)
    cocotb.start_soon(env['sink_c'].run())
    
    if idle_port.lower() == 'a':
        env['src_a'].set_idle()
    else:
        env['src_b'].set_idle()
    
    return env


def assert_single_packet_received(sink, expected_packet, packet_name="packet"):
    """
    Assert that exactly one packet was received and it matches the expected packet.
    
    Args:
        sink: Avalon-ST sink monitor (with packets list)
        expected_packet: Expected packet data (list of words)
        packet_name: Name for error messages (default: "packet")
    
    Raises:
        AssertionError: If packet count or data doesn't match
    """
    assert len(sink.packets) == 1, (
        f"Expected 1 {packet_name}, got {len(sink.packets)}"
    )
    assert sink.packets[0] == expected_packet, (
        f"{packet_name} mismatch: expected {expected_packet}, got {sink.packets[0]}"
    )

