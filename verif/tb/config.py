"""
Test configuration parameters
"""
# Clock configuration
CLOCK_PERIOD_NS = 6.4  # 156.25 MHz

# Reset configuration
RESET_CYCLES = 5
RESET_DEASSERT_DELAY = 2

# Timeout configuration
PACKET_TIMEOUT_CYCLES = 1000
TEST_TIMEOUT_CYCLES = 10000

# Ethernet packet constraints
# Note: AV_STREAM data is Ethernet payload WITHOUT header/preamble
# Full Ethernet frame (with header): 64-1518 bytes
# AV_STREAM data (without header): 46-1500 bytes
# Data width: 64 bits = 8 bytes per clock cycle
BYTES_PER_WORD = 8
MIN_PACKET_BYTES = 46   # Minimum AV_STREAM data size (Ethernet payload without header)
MAX_PACKET_BYTES = 1500 # Maximum AV_STREAM data size (Ethernet payload without header)
MIN_PACKET_WORDS = MIN_PACKET_BYTES // BYTES_PER_WORD  # 6 words minimum
MAX_PACKET_WORDS = MAX_PACKET_BYTES // BYTES_PER_WORD  # 187 words (full)
MAX_PACKET_LAST_EMPTY = MAX_PACKET_BYTES % BYTES_PER_WORD  # 4 bytes in last word

# Ready signal delay (AV_STREAM_RDY has 1 cycle delay)
READY_DELAY_CYCLES = 1

# Common wait cycles for tests
WAIT_SHORT_CYCLES = 40   # Typical wait for single packet propagation
WAIT_MEDIUM_CYCLES = 60  # Wait for packets through FIFO or longer paths
WAIT_LONG_CYCLES = 200   # Wait for multiple packets or stress tests

# Test data patterns
TEST_DATA_PATTERNS = {
    'simple': [0x1122334455667788, 0xDEADBEEFCAFEBABE],
    'alternating': [0x0102030405060708, 0xA5A5A5A5A5A5A5A5, 0xFFFFFFFF00000000],
    'all_ones': [0xFFFFFFFFFFFFFFFF],
    'all_zeros': [0x0000000000000000],
    'incrementing': list(range(0x1000, 0x1008)),
}
