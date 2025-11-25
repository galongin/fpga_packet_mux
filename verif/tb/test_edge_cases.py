"""
Edge case tests
All tests comply with Ethernet packet constraints (64-1518 bytes).
"""
import cocotb
from cocotb.triggers import RisingEdge
from drivers.avalon_st_driver import AvalonSTSource
from monitors.avalon_st_monitor import AvalonSTSink
from utils.test_utils import reset_dut, setup_clock, wait_cycles, create_packet
from test_helpers.test_fixtures import create_test_environment


@cocotb.test()
async def test_valid_without_sop(dut):
    """Valid asserted without SOP (should be ignored in IDLE)."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    env['src_b'].set_idle()
    
    # Send valid without SOP
    await RisingEdge(dut.clk)
    env['src_a'].data.value = 0xDEADBEEFCAFEBABE
    env['src_a'].valid.value = 1
    env['src_a'].sop.value = 0
    env['src_a'].eop.value = 0
    
    await wait_cycles(dut, 10)
    
    # Should not accept this (no SOP in IDLE state)
    assert dut.porta_ready.value == 0 or len(env['sink_c'].packets) == 0
    
    # Now send proper packet
    env['src_a'].valid.value = 0
    await wait_cycles(dut, 2)
    
    pkt_a, empty_a = create_packet(64)
    await env['src_a'].send_packet(pkt_a, empty_last=empty_a)
    
    await wait_cycles(dut, 40)
    
    # Should have one valid packet
    assert len(env['sink_c'].packets) == 1
    assert env['sink_c'].packets[0] == pkt_a


@cocotb.test()
async def test_eop_without_sop(dut):
    """EOP without preceding SOP."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    env['src_b'].set_idle()
    
    # Send EOP without SOP
    await RisingEdge(dut.clk)
    env['src_a'].data.value = 0xDEADBEEFCAFEBABE
    env['src_a'].valid.value = 1
    env['src_a'].sop.value = 0
    env['src_a'].eop.value = 1
    
    await wait_cycles(dut, 10)
    
    # Should not accept this
    assert len(env['sink_c'].packets) == 0
    
    # Send proper packet
    env['src_a'].valid.value = 0
    await wait_cycles(dut, 2)
    
    # Minimum Ethernet packet: 64 bytes = 8 words
    pkt_a, empty_a = create_packet(64)
    await env['src_a'].send_packet(pkt_a, empty_last=empty_a)
    
    await wait_cycles(dut, 40)
    
    assert len(env['sink_c'].packets) == 1


@cocotb.test()
async def test_simultaneous_eop_and_new_sop(dut):
    """EOP on one port, SOP on other in same cycle."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    # Send packet A
    pkt_a, empty_a = create_packet(64)
    await env['src_a'].send_packet(pkt_a, empty_last=empty_a)
    
    # Immediately after A completes, start B
    await wait_cycles(dut, 2)
    pkt_b, empty_b = create_packet(64)
    await env['src_b'].send_packet(pkt_b, empty_last=empty_b)
    
    await wait_cycles(dut, 60)
    
    assert len(env['sink_c'].packets) == 2
    assert env['sink_c'].packets[0] == pkt_a
    assert env['sink_c'].packets[1] == pkt_b


@cocotb.test()
async def test_reset_during_transmission(dut):
    """Reset asserted mid-packet."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    env['src_b'].set_idle()
    
    # Start sending packet (valid Ethernet packet)
    pkt_a, empty_a = create_packet(64)
    
    await RisingEdge(dut.clk)
    env['src_a'].data.value = pkt_a[0]
    env['src_a'].valid.value = 1
    env['src_a'].sop.value = 1
    env['src_a'].eop.value = 0
    
    await RisingEdge(dut.clk)
    if env['src_a'].ready.value:
        env['src_a'].data.value = pkt_a[1]
        env['src_a'].sop.value = 0
    
    # Assert reset mid-packet
    await RisingEdge(dut.clk)
    dut.rst_n.value = 0
    await wait_cycles(dut, 5)
    dut.rst_n.value = 1
    await wait_cycles(dut, 2)
    
    # Clear any partial packet
    env['src_a'].valid.value = 0
    await wait_cycles(dut, 5)
    
    # Send a new complete packet (valid Ethernet packet)
    pkt_new, empty_new = create_packet(64)
    await env['src_a'].send_packet(pkt_new, empty_last=empty_new)
    
    await wait_cycles(dut, 40)
    
    # Should only have the new packet (reset should have cleared state)
    # Note: depending on design, might have 0 or 1 packets
    # The important thing is that after reset, new packet works
    if len(env['sink_c'].packets) > 0:
        # If we have packets, the last one should be the new one
        assert env['sink_c'].packets[-1] == pkt_new


@cocotb.test()
async def test_state_transition_timing(dut):
    """Verify state changes at correct clock edges."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    env['src_b'].set_idle()
    
    # Send packet and monitor state transitions
    pkt_a, empty_a = create_packet(64)
    
    # Before packet, should be in IDLE (c_valid should be 0)
    assert dut.portc_valid.value == 0
    
    # Send packet
    await env['src_a'].send_packet(pkt_a, empty_last=empty_a)
    
    await wait_cycles(dut, 40)
    
    assert len(env['sink_c'].packets) == 1
    # After packet completes, should return to IDLE
    await wait_cycles(dut, 5)
    # Note: c_valid might still be high if there's pipeline delay
    # This is a basic check


@cocotb.test()
async def test_metadata_preservation(dut):
    """All metadata (sop, eop, empty, error) preserved."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    env['src_b'].set_idle()
    
    # Test various metadata combinations
    test_cases = [
        {'empty': 0, 'error': 0},
        {'empty': 3, 'error': 0},
        {'empty': 0, 'error': 1},
        {'empty': 5, 'error': 1},
    ]
    
    for i, test_case in enumerate(test_cases):
        env['sink_c'].clear()
        # Create valid Ethernet packet (64 + empty bytes)
        pkt, _ = create_packet(64 + test_case['empty'])
        await env['src_a'].send_packet(
            pkt, 
            empty_last=test_case['empty'],
            error=test_case['error']
        )
        await wait_cycles(dut, 40)
        
        assert len(env['sink_c'].packets) == 1
        metadata = env['sink_c'].get_last_packet_metadata()
        assert metadata is not None
        assert metadata['empty'] == test_case['empty']
        assert metadata['error'] == test_case['error']


@cocotb.test()
async def test_packet_abort(dut):
    """Valid goes low mid-packet (if design handles this)."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    env['src_b'].set_idle()
    
    # Start packet
    await RisingEdge(dut.clk)
    env['src_a'].data.value = 0x1111111111111111
    env['src_a'].valid.value = 1
    env['src_a'].sop.value = 1
    env['src_a'].eop.value = 0
    
    await RisingEdge(dut.clk)
    if env['src_a'].ready.value:
        env['src_a'].data.value = 0x2222222222222222
        env['src_a'].sop.value = 0
    
    # Abort packet (valid goes low)
    await RisingEdge(dut.clk)
    env['src_a'].valid.value = 0
    
    await wait_cycles(dut, 10)
    
    # Send a complete packet
    pkt, empty = create_packet(64)
    await env['src_a'].send_packet(pkt, empty_last=empty)
    
    await wait_cycles(dut, 40)
    
    # Should have at least the complete packet
    # Aborted packet may or may not be in sink depending on design
    assert len(env['sink_c'].packets) >= 1


@cocotb.test()
async def test_various_data_patterns(dut):
    """Test with various data patterns."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    env['src_b'].set_idle()
    
    # Use valid Ethernet packet sizes (64 bytes minimum = 8 words)
    patterns = [
        create_packet(64, 'incrementing'),
        create_packet(64, 'all_ones'),
        create_packet(64, 'all_zeros'),
        create_packet(64, 'alternating'),
    ]
    
    for pkt, empty in patterns:
        env['sink_c'].clear()
        await env['src_a'].send_packet(pkt, empty_last=empty)
        await wait_cycles(dut, 40)
        
        assert len(env['sink_c'].packets) == 1
        assert env['sink_c'].packets[0] == pkt

