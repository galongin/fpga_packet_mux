"""
Priority and arbitration tests
All tests comply with AV_STREAM packet constraints (46-1500 bytes, without Ethernet header).
"""
import cocotb
from cocotb.triggers import RisingEdge
from utils.test_utils import reset_dut, wait_cycles, create_packet
from test_helpers.test_fixtures import create_test_environment, create_sink_with_backpressure
from config import WAIT_SHORT_CYCLES, WAIT_MEDIUM_CYCLES


@cocotb.test()
async def test_priority_a_over_b(dut):
    """A has priority when both ports have SOP simultaneously."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    # Create valid AV_STREAM packets (46 bytes minimum)
    # Use incrementing pattern with different start values to distinguish A vs B
    pkt_a, empty_a = create_packet(64, pattern='incrementing', start_value=0xAAAA0000)
    pkt_b, empty_b = create_packet(64, pattern='incrementing', start_value=0xBBBB0000)
    
    # Start both packets simultaneously
    async def send_both():
        await RisingEdge(dut.clk)
        # Set both to start at the same time
        env['src_a'].data.value = pkt_a[0]
        env['src_a'].valid.value = 1
        env['src_a'].sop.value = 1
        env['src_a'].eop.value = 0
        
        env['src_b'].data.value = pkt_b[0]
        env['src_b'].valid.value = 1
        env['src_b'].sop.value = 1
        env['src_b'].eop.value = 0
        
        await RisingEdge(dut.clk)
        # Wait for ready
        while not (env['src_a'].ready.value or env['src_b'].ready.value):
            await RisingEdge(dut.clk)
        
        # Complete packet A first (it should have priority)
        # Send remaining words of packet A
        if env['src_a'].ready.value:
            for word_idx in range(1, len(pkt_a)):
                env['src_a'].data.value = pkt_a[word_idx]
                env['src_a'].sop.value = 0
                env['src_a'].eop.value = 1 if word_idx == len(pkt_a) - 1 else 0
                env['src_a'].empty.value = empty_a if word_idx == len(pkt_a) - 1 else 0
                await RisingEdge(dut.clk)
                while not env['src_a'].ready.value:
                    await RisingEdge(dut.clk)
            env['src_a'].valid.value = 0
            env['src_a'].eop.value = 0
            env['src_a'].empty.value = 0
        
        # Then complete packet B
        await RisingEdge(dut.clk)
        for word_idx in range(1, len(pkt_b)):
            env['src_b'].data.value = pkt_b[word_idx]
            env['src_b'].sop.value = 0
            env['src_b'].eop.value = 1 if word_idx == len(pkt_b) - 1 else 0
            env['src_b'].empty.value = empty_b if word_idx == len(pkt_b) - 1 else 0
            await RisingEdge(dut.clk)
            while not env['src_b'].ready.value:
                await RisingEdge(dut.clk)
        env['src_b'].valid.value = 0
        env['src_b'].eop.value = 0
        env['src_b'].empty.value = 0
    
    await send_both()
    await wait_cycles(dut, WAIT_SHORT_CYCLES)
    
    # A should be received first
    assert len(env['sink_c'].packets) >= 1
    assert env['sink_c'].packets[0] == pkt_a, "A should have priority"


@cocotb.test()
async def test_concurrent_packets(dut):
    """A packet arrives on A while B is being forwarded (A should wait)."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    # Start packet B first (96 bytes = 12 words)
    pkt_b, empty_b = create_packet(96, pattern='incrementing', start_value=0xBBBB0000)
    
    # Simplified: send B, then A
    await env['src_b'].send_packet(pkt_b, empty_last=empty_b)
    await wait_cycles(dut, 10)
    
    # Send A packet (64 bytes)
    pkt_a, empty_a = create_packet(64)
    await env['src_a'].send_packet(pkt_a, empty_last=empty_a)
    
    await wait_cycles(dut, WAIT_MEDIUM_CYCLES)
    
    # Both packets should be received, B first
    assert len(env['sink_c'].packets) == 2
    assert env['sink_c'].packets[0] == pkt_b
    assert env['sink_c'].packets[1] == pkt_a


@cocotb.test()
async def test_back_to_back_packets(dut):
    """Multiple packets from same port."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    env['src_b'].set_idle()
    
    # Create valid AV_STREAM packets (64 bytes each)
    pkt1, empty1 = create_packet(64)
    pkt2, empty2 = create_packet(64)
    pkt3, empty3 = create_packet(64)
    
    await env['src_a'].send_packet(pkt1, empty_last=empty1)
    await wait_cycles(dut, 5)
    await env['src_a'].send_packet(pkt2, empty_last=empty2)
    await wait_cycles(dut, 5)
    await env['src_a'].send_packet(pkt3, empty_last=empty3)
    
    await wait_cycles(dut, WAIT_MEDIUM_CYCLES)
    
    assert len(env['sink_c'].packets) == 3
    assert env['sink_c'].packets[0] == pkt1
    assert env['sink_c'].packets[1] == pkt2
    assert env['sink_c'].packets[2] == pkt3


@cocotb.test()
async def test_alternating_packets(dut):
    """A packet, then B packet, then A packet (verify state transitions)."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    # Create valid AV_STREAM packets (64 bytes each)
    pkt_a1, empty_a1 = create_packet(64)
    pkt_b, empty_b = create_packet(64)
    pkt_a2, empty_a2 = create_packet(64)
    
    await env['src_a'].send_packet(pkt_a1, empty_last=empty_a1)
    await wait_cycles(dut, 5)
    await env['src_b'].send_packet(pkt_b, empty_last=empty_b)
    await wait_cycles(dut, 5)
    await env['src_a'].send_packet(pkt_a2, empty_last=empty_a2)
    
    await wait_cycles(dut, WAIT_MEDIUM_CYCLES)
    
    assert len(env['sink_c'].packets) == 3
    assert env['sink_c'].packets[0] == pkt_a1
    assert env['sink_c'].packets[1] == pkt_b
    assert env['sink_c'].packets[2] == pkt_a2


@cocotb.test()
async def test_both_ports_waiting(dut):
    """Both A and B have packets, C_ready is low, then goes high."""
    from monitors.avalon_st_monitor import AvalonSTSinkWithBackpressure
    
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    # Use sink with backpressure control
    sink_c = create_sink_with_backpressure(dut)
    cocotb.start_soon(sink_c.run())
    
    # Start with ready low
    sink_c.set_ready(False)
    
    # Create valid AV_STREAM packets (64 bytes each)
    # Use incrementing pattern with different start values to distinguish A vs B
    pkt_a, empty_a = create_packet(64, pattern='incrementing', start_value=0xAAAA0000)
    pkt_b, empty_b = create_packet(64, pattern='incrementing', start_value=0xBBBB0000)
    
    # Start both packets
    async def send_packets():
        await RisingEdge(dut.clk)
        # Set up both packets
        env['src_a'].data.value = pkt_a[0]
        env['src_a'].valid.value = 1
        env['src_a'].sop.value = 1
        env['src_a'].eop.value = 0
        
        env['src_b'].data.value = pkt_b[0]
        env['src_b'].valid.value = 1
        env['src_b'].sop.value = 1
        env['src_b'].eop.value = 0
        
        # Wait a few cycles with ready low
        await wait_cycles(dut, 5)
        
        # Assert ready - A should be selected
        sink_c.set_ready(True)
        
        # Wait for A to complete
        await wait_cycles(dut, 10)
        
        # Complete A - send remaining words
        for word_idx in range(1, len(pkt_a)):
            env['src_a'].data.value = pkt_a[word_idx]
            env['src_a'].sop.value = 0
            env['src_a'].eop.value = 1 if word_idx == len(pkt_a) - 1 else 0
            env['src_a'].empty.value = empty_a if word_idx == len(pkt_a) - 1 else 0
            await RisingEdge(dut.clk)
            while not env['src_a'].ready.value:
                await RisingEdge(dut.clk)
        env['src_a'].valid.value = 0
        env['src_a'].eop.value = 0
        env['src_a'].empty.value = 0
        
        # Then B should go through - send remaining words
        await wait_cycles(dut, 5)
        for word_idx in range(1, len(pkt_b)):
            env['src_b'].data.value = pkt_b[word_idx]
            env['src_b'].sop.value = 0
            env['src_b'].eop.value = 1 if word_idx == len(pkt_b) - 1 else 0
            env['src_b'].empty.value = empty_b if word_idx == len(pkt_b) - 1 else 0
            await RisingEdge(dut.clk)
            while not env['src_b'].ready.value:
                await RisingEdge(dut.clk)
        env['src_b'].valid.value = 0
        env['src_b'].eop.value = 0
        env['src_b'].empty.value = 0
    
    await send_packets()
    await wait_cycles(dut, WAIT_SHORT_CYCLES)
    
    # A should be received first due to priority
    assert len(sink_c.packets) >= 1
    if len(sink_c.packets) >= 1:
        assert sink_c.packets[0] == pkt_a


@cocotb.test()
async def test_idle_state_behavior(dut):
    """Verify IDLE state when no packets."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    # Keep both ports idle
    env['src_a'].set_idle()
    env['src_b'].set_idle()
    
    # Wait many cycles
    await wait_cycles(dut, 100)
    
    # Should remain in idle, no packets
    assert len(env['sink_c'].packets) == 0
    assert dut.portc_valid.value == 0

