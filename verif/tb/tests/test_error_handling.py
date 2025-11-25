"""
Error handling tests
All tests comply with AV_STREAM packet constraints (46-1500 bytes, without Ethernet header).
"""
import cocotb
from utils.test_utils import wait_cycles, create_packet
from test_helpers.test_fixtures import setup_test_with_idle_port, assert_single_packet_received
from config import WAIT_SHORT_CYCLES, WAIT_MEDIUM_CYCLES


@cocotb.test()
async def test_error_flag_propagation(dut):
    """Error flag on input propagates to output."""
    env = await setup_test_with_idle_port(dut, 'b')
    
    pkt_a, empty_a = create_packet(64)
    await env['src_a'].send_packet(pkt_a, empty_last=empty_a, error=True)
    
    await wait_cycles(dut, WAIT_SHORT_CYCLES)
    
    assert_single_packet_received(env['sink_c'], pkt_a)
    
    # Check error flag was propagated
    metadata = env['sink_c'].get_last_packet_metadata()
    assert metadata is not None
    assert metadata['error'] == 1, "Error flag should be propagated"


@cocotb.test()
async def test_error_on_port_a(dut):
    """Test error flag on port A."""
    env = await setup_test_with_idle_port(dut, 'b')
    
    pkt_a, empty_a = create_packet(64)
    await env['src_a'].send_packet(pkt_a, empty_last=empty_a, error=True)
    
    await wait_cycles(dut, WAIT_SHORT_CYCLES)
    
    assert_single_packet_received(env['sink_c'], pkt_a)
    metadata = env['sink_c'].get_last_packet_metadata()
    assert metadata is not None
    assert metadata['error'] == 1


@cocotb.test()
async def test_error_on_port_b(dut):
    """Test error flag on port B."""
    env = await setup_test_with_idle_port(dut, 'a')
    
    pkt_b, empty_b = create_packet(64)
    await env['src_b'].send_packet(pkt_b, empty_last=empty_b, error=True)
    
    await wait_cycles(dut, WAIT_SHORT_CYCLES)
    
    assert_single_packet_received(env['sink_c'], pkt_b)
    metadata = env['sink_c'].get_last_packet_metadata()
    assert metadata is not None
    assert metadata['error'] == 1


@cocotb.test()
async def test_error_with_empty_bytes(dut):
    """Test error flag with empty bytes."""
    env = await setup_test_with_idle_port(dut, 'b')
    
    # Create 67-byte packet (46 + 21 bytes + 3 empty bytes)
    pkt_a, _ = create_packet(67)
    await env['src_a'].send_packet(pkt_a, empty_last=3, error=True)
    
    await wait_cycles(dut, WAIT_SHORT_CYCLES)
    
    assert_single_packet_received(env['sink_c'], pkt_a)
    metadata = env['sink_c'].get_last_packet_metadata()
    assert metadata is not None
    assert metadata['error'] == 1
    assert metadata['empty'] == 3


@cocotb.test()
async def test_no_error_flag(dut):
    """Test normal operation without error flag."""
    env = await setup_test_with_idle_port(dut, 'b')
    
    # Create valid AV_STREAM packet (46 bytes minimum)
    pkt_a, empty_a = create_packet(64)
    await env['src_a'].send_packet(pkt_a, empty_last=empty_a, error=False)
    
    await wait_cycles(dut, WAIT_SHORT_CYCLES)
    
    assert_single_packet_received(env['sink_c'], pkt_a)
    metadata = env['sink_c'].get_last_packet_metadata()
    assert metadata is not None
    assert metadata['error'] == 0, "Error flag should be 0 for normal packet"


@cocotb.test()
async def test_error_on_alternating_packets(dut):
    """Test error flag on alternating packets from different ports."""
    from test_helpers.test_fixtures import create_test_environment
    from utils.test_utils import reset_dut
    
    env = create_test_environment(dut)
    await reset_dut(dut)
    cocotb.start_soon(env['sink_c'].run())
    
    pkt_a, empty_a = create_packet(64)
    pkt_b, empty_b = create_packet(64)
    
    await env['src_a'].send_packet(pkt_a, empty_last=empty_a, error=True)
    await wait_cycles(dut, 5)
    await env['src_b'].send_packet(pkt_b, error=False)
    await wait_cycles(dut, 5)
    await env['src_a'].send_packet(pkt_a, error=False)
    
    await wait_cycles(dut, WAIT_MEDIUM_CYCLES)
    
    assert len(env['sink_c'].packets) == 3
    # Check error flags
    assert env['sink_c']._packet_metadata[0]['error'] == 1
    assert env['sink_c']._packet_metadata[1]['error'] == 0
    assert env['sink_c']._packet_metadata[2]['error'] == 0

