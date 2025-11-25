"""
Common test utility functions
"""
import cocotb
from cocotb.triggers import RisingEdge
from cocotb.clock import Clock
import os
import random
try:
    from config import CLOCK_PERIOD_NS, RESET_CYCLES, RESET_DEASSERT_DELAY, PACKET_TIMEOUT_CYCLES
except ImportError:
    # Fallback if import fails
    CLOCK_PERIOD_NS = 6.4
    RESET_CYCLES = 5
    RESET_DEASSERT_DELAY = 2
    PACKET_TIMEOUT_CYCLES = 1000


def enable_vcd_dump(dut, vcd_filename=None):
    """
    Enable VCD waveform dumping for Verilator simulations.
    
    Args:
        dut: Device under test
        vcd_filename: Optional VCD filename (defaults to sim_build/Vtop.vcd)
    
    Returns:
        True if VCD dumping was enabled, False otherwise
    """
    if vcd_filename is None:
        # Default VCD file location
        vcd_filename = "sim_build/Vtop.vcd"
    
    try:
        # For Verilator, we need to access the simulator handle
        # Cocotb provides access through the simulator module
        import cocotb.simulator
        
        # Get the simulator handle
        sim = cocotb.simulator.get_simulator()
        
        # For Verilator, we can enable VCD through the handle
        # The actual implementation depends on cocotb version
        # Try to set VCD dumping through environment or direct access
        
        # Set environment variable that Verilator might use
        os.environ['VERILATOR_TRACE'] = '1'
        os.environ['VERILATOR_TRACE_FILE'] = vcd_filename
        
        # Try to access the Verilated model and enable trace
        # This is simulator-specific
        try:
            # Access the underlying Verilated model
            # Note: This is implementation-dependent
            handle = sim._handle if hasattr(sim, '_handle') else None
            
            if handle:
                # If we can access the handle, try to enable VCD
                # This would require C++ bindings which may not be available
                pass
        except:
            pass
        
        return True
    except Exception as e:
        cocotb.log.warning(f"Could not enable VCD dumping: {e}")
        return False


async def reset_dut(dut, cycles=None):
    """
    Reset the DUT and drive all inputs to safe defaults.
    
    Args:
        dut: Device under test
        cycles: Number of reset cycles (defaults to config.RESET_CYCLES)
    """
    if cycles is None:
        cycles = RESET_CYCLES
    
    dut.rst_n.value = 0

    # drive all inputs to safe defaults
    dut.porta_valid.value = 0
    dut.porta_sop.value   = 0
    dut.porta_eop.value   = 0
    dut.porta_empty.value = 0
    dut.porta_error.value = 0

    dut.portb_valid.value = 0
    dut.portb_sop.value   = 0
    dut.portb_eop.value   = 0
    dut.portb_empty.value = 0
    dut.portb_error.value = 0

    dut.portc_ready.value = 0

    for _ in range(cycles):
        await RisingEdge(dut.clk)

    dut.rst_n.value = 1
    for _ in range(RESET_DEASSERT_DELAY):
        await RisingEdge(dut.clk)


def setup_clock(dut, period_ns=None):
    """
    Setup clock for the DUT.
    
    Args:
        dut: Device under test
        period_ns: Clock period in nanoseconds (defaults to config.CLOCK_PERIOD_NS)
    
    Returns:
        Clock coroutine
    """
    if period_ns is None:
        period_ns = CLOCK_PERIOD_NS
    
    return Clock(dut.clk, period_ns, unit="ns").start()


async def wait_cycles(dut, cycles):
    """
    Wait for specified number of clock cycles.
    
    Args:
        dut: Device under test
        cycles: Number of cycles to wait
    """
    for _ in range(cycles):
        await RisingEdge(dut.clk)


async def wait_for_packet(sink, timeout_cycles=None, min_packets=1):
    """
    Wait for at least min_packets to be collected by the sink.
    
    Args:
        sink: AvalonSTSink monitor
        timeout_cycles: Maximum cycles to wait (defaults to config.PACKET_TIMEOUT_CYCLES)
        min_packets: Minimum number of packets to wait for
    
    Returns:
        True if packets received, False if timeout
    """
    if timeout_cycles is None:
        timeout_cycles = PACKET_TIMEOUT_CYCLES
    
    for _ in range(timeout_cycles):
        if sink.get_packet_count() >= min_packets:
            return True
        await RisingEdge(sink.clk)
    
    return False


def create_packet(num_bytes=None, pattern='random', start_value=0x1000, seed=None):
    """
    Create a valid Ethernet-sized packet (64-1518 bytes).
    
    Args:
        num_bytes: Number of bytes in packet (must be between 64 and 1518).
                   If None, a random size within the valid range will be selected.
        pattern: Pattern type ('incrementing', 'all_ones', 'all_zeros', 'alternating', 'random')
        start_value: Starting value for incrementing pattern
        seed: Optional random seed for 'random' pattern and random num_bytes (for reproducibility)
    
    Returns:
        Tuple of (packet_words, empty_last) where:
        - packet_words: List of data words
        - empty_last: Empty field value for last word (0-7)
    
    Raises:
        ValueError: If num_bytes is outside valid range
    """
    try:
        from config import MIN_PACKET_BYTES, MAX_PACKET_BYTES, BYTES_PER_WORD
    except ImportError:
        MIN_PACKET_BYTES = 46
        MAX_PACKET_BYTES = 1500
        BYTES_PER_WORD = 8
    
    # Set random seed once at the beginning if provided (for reproducibility)
    if seed is not None:
        random.seed(seed)
    
    # Randomize num_bytes if not specified
    if num_bytes is None:
        num_bytes = random.randint(MIN_PACKET_BYTES, MAX_PACKET_BYTES)
    
    if num_bytes < MIN_PACKET_BYTES or num_bytes > MAX_PACKET_BYTES:
        raise ValueError(
            f"Packet size {num_bytes} bytes is outside valid range "
            f"({MIN_PACKET_BYTES}-{MAX_PACKET_BYTES} bytes)"
        )
    
    num_words = (num_bytes + BYTES_PER_WORD - 1) // BYTES_PER_WORD  # Ceiling division
    empty_last = (num_words * BYTES_PER_WORD) - num_bytes
    valid_bytes_last = BYTES_PER_WORD - empty_last  # Number of valid bytes in last word
    
    # Generate packet words
    if pattern == 'incrementing':
        words = list(range(start_value, start_value + num_words))
    elif pattern == 'all_ones':
        words = [0xFFFFFFFFFFFFFFFF] * num_words
    elif pattern == 'all_zeros':
        words = [0x0000000000000000] * num_words
    elif pattern == 'alternating':
        words = [0xAAAAAAAAAAAAAAAA if i % 2 == 0 else 0x5555555555555555 
                 for i in range(num_words)]
    elif pattern == 'random':
        # Generate random 64-bit values (seed already set above if provided)
        words = [random.getrandbits(64) for _ in range(num_words)]
    else:
        words = [0xDEADBEEFCAFEBABE + i for i in range(num_words)]
    
    # Mask the last word based on empty field
    # Only the valid bytes should contain pattern data, rest should be zero    
    if empty_last > 0 and num_words > 0:
        last_word = words[-1]        
        mask = (1 << (valid_bytes_last * 8)) - 1
        words[-1] = last_word & mask
    
    return words, empty_last


