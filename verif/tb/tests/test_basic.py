"""
Basic functionality tests
All tests comply with AV_STREAM packet constraints:
- Packet size: 46-1500 bytes (AV_STREAM data without Ethernet header)
- Note: Full Ethernet frame (with header) is 64-1518 bytes, but AV_STREAM data is 46-1500 bytes
- AV_STREAM_RDY has 1-cycle delay
"""
import cocotb
from utils.test_utils import wait_cycles, create_packet
from test_helpers.test_fixtures import setup_test_with_idle_port, assert_single_packet_received
from config import WAIT_SHORT_CYCLES, WAIT_MEDIUM_CYCLES


@cocotb.test()
async def test_single_packet_from_a(dut):
    """Send a single packet on A, expect same packet on C."""
    env = await setup_test_with_idle_port(dut, 'b')
    
    # Create valid AV_STREAM packet (46 bytes minimum)
    pkt_a, empty_a = create_packet(64)
    await env['src_a'].send_packet(pkt_a, empty_last=empty_a)
    
    # wait for packet to propagate through DUT
    await wait_cycles(dut, WAIT_SHORT_CYCLES)
    
    assert_single_packet_received(env['sink_c'], pkt_a, "packet A")


@cocotb.test()
async def test_single_packet_from_b(dut):
    """Send a single packet on B, expect same packet on C."""
    env = await setup_test_with_idle_port(dut, 'a')
    
    # Create valid AV_STREAM packet (96 bytes = 12 words)
    pkt_b, empty_b = create_packet(96, pattern='alternating')
    await env['src_b'].send_packet(pkt_b, empty_last=empty_b)
    
    await wait_cycles(dut, WAIT_MEDIUM_CYCLES)
    
    assert_single_packet_received(env['sink_c'], pkt_b, "packet B")


@cocotb.test()
async def test_minimum_size_packet(dut):
    """Test minimum AV_STREAM packet size (46 bytes)."""
    env = await setup_test_with_idle_port(dut, 'b')
    
    # Minimum AV_STREAM packet: 46 bytes
    pkt_a, empty_a = create_packet(46)
    await env['src_a'].send_packet(pkt_a, empty_last=empty_a)
    
    await wait_cycles(dut, WAIT_SHORT_CYCLES)
    
    assert_single_packet_received(env['sink_c'], pkt_a)
    assert len(pkt_a) >= 6, "Minimum packet should be at least 6 words (46 bytes)"


@cocotb.test()
async def test_empty_bytes(dut):
    """Test packet with non-zero empty field on last beat (valid Ethernet size)."""
    env = await setup_test_with_idle_port(dut, 'b')
    
    # Create a 67-byte packet (8 words + 3 empty bytes in last word)
    # This is valid: 46 bytes minimum, and empty field is used correctly
    pkt_a, _ = create_packet(67)
    await env['src_a'].send_packet(pkt_a, empty_last=3)  # 3 empty bytes
    await wait_cycles(dut, WAIT_SHORT_CYCLES)
    
    assert_single_packet_received(env['sink_c'], pkt_a)
    # Check that empty field was preserved
    metadata = env['sink_c'].get_last_packet_metadata()
    assert metadata is not None
    assert metadata['empty'] == 3


@cocotb.test()
async def test_maximum_size_packet(dut):
    """Test maximum AV_STREAM packet size (1500 bytes)."""
    env = await setup_test_with_idle_port(dut, 'b')
    
    # Maximum AV_STREAM packet: 1500 bytes = 187 words + 4 empty bytes
    pkt_a, empty_a = create_packet(1500)
    await env['src_a'].send_packet(pkt_a, empty_last=empty_a)
    
    await wait_cycles(dut, 400)  # Large packet needs more time
    
    assert_single_packet_received(env['sink_c'], pkt_a)
    assert len(env['sink_c'].packets[0]) == len(pkt_a)
    # Verify empty field for maximum packet
    metadata = env['sink_c'].get_last_packet_metadata()
    assert metadata is not None
    assert metadata['empty'] == empty_a, f"Expected empty={empty_a}, got {metadata['empty']}"


@cocotb.test()
async def test_medium_size_packet(dut):
    """Test medium-sized Ethernet packet (256 bytes)."""
    env = await setup_test_with_idle_port(dut, 'b')
    
    # Medium packet: 256 bytes = 32 words
    pkt_a, empty_a = create_packet(256)
    await env['src_a'].send_packet(pkt_a, empty_last=empty_a)
    
    await wait_cycles(dut, 80)  # Medium packet needs more time
    
    assert_single_packet_received(env['sink_c'], pkt_a)
    assert len(pkt_a) == 32, "256-byte packet should be exactly 32 words"


@cocotb.test()
async def test_data_integrity(dut):
    """Verify data doesn't get corrupted with valid Ethernet packet sizes."""
    env = await setup_test_with_idle_port(dut, 'b')
    
    # Test with various data patterns and valid packet sizes
    test_cases = [
        (46, 'all_ones'),      # Minimum size, all ones
        (64, 'all_zeros'),     # Small size, all zeros
        (128, 'alternating'),  # Medium size, alternating pattern
        (256, 'incrementing'), # Larger size, incrementing pattern
    ]
    
    for num_bytes, pattern in test_cases:
        env['sink_c'].clear()
        pkt, empty = create_packet(num_bytes, pattern=pattern)
        await env['src_a'].send_packet(pkt, empty_last=empty)
        await wait_cycles(dut, num_bytes // 8 + 20)  # Wait based on packet size
        
        assert_single_packet_received(env['sink_c'], pkt, f"packet ({num_bytes} bytes, {pattern})")


@cocotb.test()
async def test_empty_field_preservation(dut):
    """Test that empty field is correctly passed through (valid Ethernet sizes)."""
    env = await setup_test_with_idle_port(dut, 'b')
    
    # Test different empty values with valid packet sizes
    # Create packets of size 46+empty_val bytes to test each empty value
    for empty_val in [0, 1, 2, 3, 4, 5, 6, 7]:
        env['sink_c'].clear()
        # Create packet with specific empty value (46 + empty_val bytes)
        pkt, _ = create_packet(46 + empty_val)
        await env['src_a'].send_packet(pkt, empty_last=empty_val)
        await wait_cycles(dut, WAIT_SHORT_CYCLES)
        
        assert_single_packet_received(env['sink_c'], pkt)
        metadata = env['sink_c'].get_last_packet_metadata()
        assert metadata is not None
        assert metadata['empty'] == empty_val, (
            f"Empty field mismatch: expected {empty_val}, got {metadata['empty']}"
        )

