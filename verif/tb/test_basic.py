"""
Basic functionality tests
All tests comply with Ethernet packet constraints:
- Packet size: 64-1518 bytes (8-190 words with empty field)
- No preamble/SFD in data stream
- AV_STREAM_RDY has 1-cycle delay
"""
import cocotb
from cocotb.triggers import RisingEdge
from drivers.avalon_st_driver import AvalonSTSource
from monitors.avalon_st_monitor import AvalonSTSink
from utils.test_utils import reset_dut, setup_clock, wait_cycles, create_packet
from test_helpers.test_fixtures import create_test_environment


@cocotb.test()
async def test_single_packet_from_a(dut):
    """Send a single packet on A, expect same packet on C."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    # Keep B idle in this test
    env['src_b'].set_idle()
    
    # Create valid Ethernet packet (64 bytes minimum = 8 words)
    pkt_a, empty_a = create_packet(64)
    await env['src_a'].send_packet(pkt_a, empty_last=empty_a)
    
    # wait for packet to propagate through DUT
    await wait_cycles(dut, 40)
    
    assert len(env['sink_c'].packets) == 1, f"Expected 1 packet, got {len(env['sink_c'].packets)}"
    assert env['sink_c'].packets[0] == pkt_a, (
        f"Packet mismatch: expected {pkt_a}, got {env['sink_c'].packets[0]}"
    )


@cocotb.test()
async def test_single_packet_from_b(dut):
    """Send a single packet on B, expect same packet on C."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    # Keep A idle
    env['src_a'].set_idle()
    
    # Create valid Ethernet packet (96 bytes = 12 words)
    pkt_b, empty_b = create_packet(96, pattern='alternating')
    await env['src_b'].send_packet(pkt_b, empty_last=empty_b)
    
    await wait_cycles(dut, 60)
    
    assert len(env['sink_c'].packets) == 1, f"Expected 1 packet, got {len(env['sink_c'].packets)}"
    assert env['sink_c'].packets[0] == pkt_b, (
        f"Packet mismatch: expected {pkt_b}, got {env['sink_c'].packets[0]}"
    )


@cocotb.test()
async def test_minimum_size_packet(dut):
    """Test minimum Ethernet packet size (64 bytes = 8 words)."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    env['src_b'].set_idle()
    
    # Minimum Ethernet packet: 64 bytes = exactly 8 words
    pkt_a, empty_a = create_packet(64)
    await env['src_a'].send_packet(pkt_a, empty_last=empty_a)
    
    await wait_cycles(dut, 40)
    
    assert len(env['sink_c'].packets) == 1, f"Expected 1 packet, got {len(env['sink_c'].packets)}"
    assert env['sink_c'].packets[0] == pkt_a
    assert len(pkt_a) == 8, "Minimum packet should be exactly 8 words (64 bytes)"


@cocotb.test()
async def test_empty_bytes(dut):
    """Test packet with non-zero empty field on last beat (valid Ethernet size)."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    env['src_b'].set_idle()
    
    # Create a 67-byte packet (8 words + 3 empty bytes in last word)
    # This is valid: 64 bytes minimum, and empty field is used correctly
    pkt_a, _ = create_packet(67)
    await env['src_a'].send_packet(pkt_a, empty_last=3)  # 3 empty bytes
    await wait_cycles(dut, 40)
    
    assert len(env['sink_c'].packets) == 1
    assert env['sink_c'].packets[0] == pkt_a
    # Check that empty field was preserved
    metadata = env['sink_c'].get_last_packet_metadata()
    assert metadata is not None
    assert metadata['empty'] == 3


@cocotb.test()
async def test_maximum_size_packet(dut):
    """Test maximum Ethernet packet size (1518 bytes)."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    env['src_b'].set_idle()
    
    # Maximum Ethernet packet: 1518 bytes = 189 words + 6 empty bytes
    pkt_a, empty_a = create_packet(1518)
    await env['src_a'].send_packet(pkt_a, empty_last=empty_a)
    
    await wait_cycles(dut, 400)
    
    assert len(env['sink_c'].packets) == 1
    assert len(env['sink_c'].packets[0]) == len(pkt_a)
    assert env['sink_c'].packets[0] == pkt_a
    # Verify empty field for maximum packet
    metadata = env['sink_c'].get_last_packet_metadata()
    assert metadata is not None
    assert metadata['empty'] == empty_a, f"Expected empty={empty_a}, got {metadata['empty']}"


@cocotb.test()
async def test_medium_size_packet(dut):
    """Test medium-sized Ethernet packet (256 bytes)."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    env['src_b'].set_idle()
    
    # Medium packet: 256 bytes = 32 words
    pkt_a, empty_a = create_packet(256)
    await env['src_a'].send_packet(pkt_a, empty_last=empty_a)
    
    await wait_cycles(dut, 80)
    
    assert len(env['sink_c'].packets) == 1
    assert env['sink_c'].packets[0] == pkt_a
    assert len(pkt_a) == 32, "256-byte packet should be exactly 32 words"


@cocotb.test()
async def test_data_integrity(dut):
    """Verify data doesn't get corrupted with valid Ethernet packet sizes."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    env['src_b'].set_idle()
    
    # Test with various data patterns and valid packet sizes
    test_cases = [
        (64, 'all_ones'),      # Minimum size, all ones
        (64, 'all_zeros'),      # Minimum size, all zeros
        (128, 'alternating'),  # Medium size, alternating pattern
        (256, 'incrementing'), # Larger size, incrementing pattern
    ]
    
    for num_bytes, pattern in test_cases:
        env['sink_c'].clear()
        pkt, empty = create_packet(num_bytes, pattern=pattern)
        await env['src_a'].send_packet(pkt, empty_last=empty)
        await wait_cycles(dut, num_bytes // 8 + 20)  # Wait based on packet size
        
        assert len(env['sink_c'].packets) == 1
        assert env['sink_c'].packets[0] == pkt, (
            f"Data corruption: expected {pkt[:5]}..., got {env['sink_c'].packets[0][:5]}..."
        )


@cocotb.test()
async def test_empty_field_preservation(dut):
    """Test that empty field is correctly passed through (valid Ethernet sizes)."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    env['src_b'].set_idle()
    
    # Test different empty values with valid packet sizes
    # Create packets of size 64+empty_val bytes to test each empty value
    for empty_val in [0, 1, 2, 3, 4, 5, 6, 7]:
        env['sink_c'].clear()
        # Create packet with specific empty value (64 + empty_val bytes)
        pkt, _ = create_packet(64 + empty_val)
        await env['src_a'].send_packet(pkt, empty_last=empty_val)
        await wait_cycles(dut, 40)
        
        assert len(env['sink_c'].packets) == 1
        metadata = env['sink_c'].get_last_packet_metadata()
        assert metadata is not None
        assert metadata['empty'] == empty_val, (
            f"Empty field mismatch: expected {empty_val}, got {metadata['empty']}"
        )

