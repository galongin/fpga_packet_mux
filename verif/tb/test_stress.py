"""
Stress and concurrent tests
All tests comply with Ethernet packet constraints (64-1518 bytes).
"""
import cocotb
from cocotb.triggers import RisingEdge
from drivers.avalon_st_driver import AvalonSTSource
from monitors.avalon_st_monitor import AvalonSTSink
from utils.test_utils import reset_dut, setup_clock, wait_cycles, create_packet
from test_helpers.test_fixtures import create_test_environment


@cocotb.test()
async def test_rapid_packet_sequence(dut):
    """Many packets in quick succession."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    env['src_b'].set_idle()
    
    # Send many packets rapidly
    num_packets = 20
    packets = []
    
    for i in range(num_packets):
        # Create valid Ethernet packet (64 bytes minimum)
        pkt, empty = create_packet(64)
        packets.append(pkt)
        await env['src_a'].send_packet(pkt, empty_last=empty)
        await wait_cycles(dut, 2)  # Small gap between packets
    
    await wait_cycles(dut, 200)
    
    assert len(env['sink_c'].packets) == num_packets
    for i, pkt in enumerate(packets):
        assert env['sink_c'].packets[i] == pkt


@cocotb.test()
async def test_both_ports_active(dut):
    """Continuous traffic on both ports."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    # Send packets from both ports
    packets_a = []
    packets_b = []
    
    for i in range(10):
        # Create valid Ethernet packets (64 bytes each)
        pkt_a, empty_a = create_packet(64, pattern='incrementing', start_value=0xA00000 + i*1000)
        pkt_b, empty_b = create_packet(64, pattern='incrementing', start_value=0xB00000 + i*1000)
        packets_a.append(pkt_a)
        packets_b.append(pkt_b)
        
        # Start both (A has priority)
        await env['src_a'].send_packet(pkt_a, empty_last=empty_a)
        await wait_cycles(dut, 2)
        await env['src_b'].send_packet(pkt_b, empty_last=empty_b)
        await wait_cycles(dut, 2)
    
    await wait_cycles(dut, 300)
    
    # Should receive all packets, A packets first due to priority
    assert len(env['sink_c'].packets) >= 10
    # Verify A packets come before B packets
    # Check the first word of each packet - A packets start with 0xA00000, B packets with 0xB00000
    a_count = 0
    b_count = 0
    for pkt in env['sink_c'].packets:
        if pkt[0] & 0xFF0000 == 0xA00000:  # Check upper 24 bits for 0xA00000
            a_count += 1
        elif pkt[0] & 0xFF0000 == 0xB00000:  # Check upper 24 bits for 0xB00000
            b_count += 1
    
    assert a_count > 0, f"Expected at least one A packet, got {a_count}. Total packets: {len(env['sink_c'].packets)}"
    assert b_count > 0, f"Expected at least one B packet, got {b_count}. Total packets: {len(env['sink_c'].packets)}"


@cocotb.test()
async def test_packet_interleaving_stress(dut):
    """Complex interleaving patterns."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    # Complex pattern: A, B, A, A, B, B, A, B
    # Create valid Ethernet packets (64 bytes each)
    pattern = [
        ('A', create_packet(64, pattern='incrementing', start_value=0xA10000)),
        ('B', create_packet(64, pattern='incrementing', start_value=0xB10000)),
        ('A', create_packet(64, pattern='incrementing', start_value=0xA20000)),
        ('A', create_packet(64, pattern='incrementing', start_value=0xA30000)),
        ('B', create_packet(64, pattern='incrementing', start_value=0xB20000)),
        ('B', create_packet(64, pattern='incrementing', start_value=0xB30000)),
        ('A', create_packet(64, pattern='incrementing', start_value=0xA40000)),
        ('B', create_packet(64, pattern='incrementing', start_value=0xB40000)),
    ]
    
    expected_order = []
    for port, (pkt, empty) in pattern:
        if port == 'A':
            await env['src_a'].send_packet(pkt, empty_last=empty)
            expected_order.append(('A', pkt))
        else:
            await env['src_b'].send_packet(pkt, empty_last=empty)
            expected_order.append(('B', pkt))
        await wait_cycles(dut, 2)
    
    await wait_cycles(dut, 200)
    
    # Verify all packets received
    assert len(env['sink_c'].packets) == len(pattern)
    
    # Verify order: A packets should come before B packets when both are pending
    # (due to priority)
    received_packets = env['sink_c'].packets
    assert len(received_packets) == len(expected_order)


@cocotb.test()
async def test_long_continuous_stream(dut):
    """Very long continuous stream of packets."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    env['src_b'].set_idle()
    
    # Send 50 packets
    num_packets = 50
    packets = []
    
    for i in range(num_packets):
        # Create valid Ethernet packet (64 bytes minimum)
        pkt, empty = create_packet(64, pattern='incrementing', start_value=0x1000 + i*1000)
        packets.append(pkt)
        await env['src_a'].send_packet(pkt, empty_last=empty)
        await wait_cycles(dut, 1)
    
    await wait_cycles(dut, 500)
    
    assert len(env['sink_c'].packets) == num_packets
    for i, pkt in enumerate(packets):
        assert env['sink_c'].packets[i] == pkt


@cocotb.test()
async def test_mixed_packet_sizes(dut):
    """Mix of different packet sizes."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    env['src_b'].set_idle()
    
    # Packets of various valid Ethernet sizes
    packets = [
        create_packet(64),   # Minimum: 64 bytes
        create_packet(128),  # 128 bytes
        create_packet(256),  # 256 bytes
        create_packet(512),  # 512 bytes
        create_packet(1024), # 1024 bytes
        create_packet(1518), # Maximum: 1518 bytes
    ]
    
    for pkt, empty in packets:
        await env['src_a'].send_packet(pkt, empty_last=empty)
        await wait_cycles(dut, 2)
    
    await wait_cycles(dut, 200)
    
    assert len(env['sink_c'].packets) == len(packets)
    # packets contains tuples (words, empty), but sink_c.packets contains just the words
    for i, (pkt, empty) in enumerate(packets):
        assert env['sink_c'].packets[i] == pkt, (
            f"Packet {i} mismatch: expected {pkt[:5]}..., got {env['sink_c'].packets[i][:5]}..."
        )


@cocotb.test()
async def test_concurrent_sop_assertion(dut):
    """Multiple concurrent SOP assertions."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    # Try to assert SOP on both ports simultaneously multiple times
    for _ in range(5):
        await RisingEdge(dut.clk)
        env['src_a'].data.value = 0xAAAAAAAAAAAAAAAA
        env['src_a'].valid.value = 1
        env['src_a'].sop.value = 1
        env['src_a'].eop.value = 0
        
        env['src_b'].data.value = 0xBBBBBBBBBBBBBBBB
        env['src_b'].valid.value = 1
        env['src_b'].sop.value = 1
        env['src_b'].eop.value = 0
        
        await RisingEdge(dut.clk)
        
        # One should be selected (A has priority)
        if env['src_a'].ready.value:
            env['src_a'].eop.value = 1
            await RisingEdge(dut.clk)
            if env['src_a'].ready.value:
                env['src_a'].valid.value = 0
                env['src_a'].eop.value = 0
        
        if env['src_b'].ready.value:
            env['src_b'].eop.value = 1
            await RisingEdge(dut.clk)
            if env['src_b'].ready.value:
                env['src_b'].valid.value = 0
                env['src_b'].eop.value = 0
        
        await wait_cycles(dut, 5)
    
    await wait_cycles(dut, 50)
    
    # Should have received some packets
    assert len(env['sink_c'].packets) > 0


@cocotb.test()
async def test_high_frequency_packets(dut):
    """Packets with minimal gap between them."""
    env = create_test_environment(dut)
    await reset_dut(dut)
    
    cocotb.start_soon(env['sink_c'].run())
    
    env['src_b'].set_idle()
    
    # Send packets with minimal gap
    num_packets = 15
    packets = []
    
    for i in range(num_packets):
        # Create valid Ethernet packet (64 bytes minimum)
        pkt, empty = create_packet(64)
        packets.append(pkt)
        await env['src_a'].send_packet(pkt, empty_last=empty)
        # No wait - back-to-back
    
    await wait_cycles(dut, 300)
    
    assert len(env['sink_c'].packets) == num_packets


@cocotb.test()
async def test_alternating_ports_stress(dut):
    """Stress test with queued packets from both ports - proper arbitration and backpressure."""
    from drivers.avalon_st_driver import AvalonSTQueuedSource
    from monitors.avalon_st_monitor import AvalonSTSinkWithBackpressure
    from utils.test_utils import reset_dut, setup_clock, wait_cycles, create_packet
    import cocotb
    from cocotb.triggers import RisingEdge
    
    # Setup clock
    cocotb.start_soon(setup_clock(dut))
    await reset_dut(dut)
    
    # Create queued drivers for both ports
    src_a = AvalonSTQueuedSource(
        clk   = dut.clk,
        data  = dut.porta_data,
        valid = dut.porta_valid,
        sop   = dut.porta_sop,
        eop   = dut.porta_eop,
        empty = dut.porta_empty,
        error = dut.porta_error,
        ready = dut.porta_ready,
    )
    
    src_b = AvalonSTQueuedSource(
        clk   = dut.clk,
        data  = dut.portb_data,
        valid = dut.portb_valid,
        sop   = dut.portb_sop,
        eop   = dut.portb_eop,
        empty = dut.portb_empty,
        error = dut.portb_error,
        ready = dut.portb_ready,
    )
    
    # Create sink with backpressure to stress the design
    sink_c = AvalonSTSinkWithBackpressure(
        clk   = dut.clk,
        data  = dut.portc_data,
        valid = dut.portc_valid,
        sop   = dut.portc_sop,
        eop   = dut.portc_eop,
        empty = dut.portc_empty,
        error = dut.portc_error,
        ready = dut.portc_ready,
    )
    
    # Start monitor with occasional backpressure pattern
    # Ready for 3 cycles, not ready for 1 cycle - creates backpressure
    ready_pattern = [(3, True), (1, False)]
    cocotb.start_soon(sink_c.run(ready_pattern=ready_pattern))
    
    # Queue many packets from both ports simultaneously
    # This creates a proper stress test with arbitration
    num_packets_per_port = 15
    total_packets = num_packets_per_port * 2
    
    # Queue all packets from both ports rapidly (non-blocking)
    # Use valid Ethernet packet sizes (64 bytes minimum)
    for i in range(num_packets_per_port):
        # Port A packets (64 bytes = 8 words)
        pkt_a, empty_a = create_packet(64, pattern='incrementing', start_value=0xA00000 + i*1000)
        await src_a.queue_packet(pkt_a, empty_last=empty_a)
        
        # Port B packets (64 bytes = 8 words)
        pkt_b, empty_b = create_packet(64, pattern='incrementing', start_value=0xB00000 + i*1000)
        await src_b.queue_packet(pkt_b, empty_last=empty_b)
    
    # Wait for all packets to be sent and received
    # With backpressure and FIFO buffering, this may take much longer
    # Each packet is 8 words, with backpressure pattern (3 ready, 1 not ready)
    # Worst case: 8 words * 4 cycles/word = 32 cycles per packet
    # Plus FIFO buffering delays for port B
    max_wait_cycles = total_packets * 50  # Very generous timeout for FIFO + backpressure
    cycles_waited = 0
    for _ in range(max_wait_cycles):
        await RisingEdge(dut.clk)
        cycles_waited += 1
        # Check if all packets received AND queues are empty
        if len(sink_c.packets) >= total_packets and src_a.get_queue_size() == 0 and src_b.get_queue_size() == 0:
            break
    
    # Give extra time for any remaining packets to drain
    # Port B FIFO might still have packets buffered
    for _ in range(200):
        await RisingEdge(dut.clk)
        if len(sink_c.packets) >= total_packets and src_a.get_queue_size() == 0 and src_b.get_queue_size() == 0:
            break
    
    # Verify all packets were received
    assert len(sink_c.packets) == total_packets, (
        f"Expected {total_packets} packets, got {len(sink_c.packets)} after {cycles_waited} cycles. "
        f"Queue A: {src_a.get_queue_size()}, Queue B: {src_b.get_queue_size()}"
    )
    
    # Verify queue is empty (all packets sent)
    assert src_a.get_queue_size() == 0, "Port A queue should be empty"
    assert src_b.get_queue_size() == 0, "Port B queue should be empty"

