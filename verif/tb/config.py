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
# Data width: 64 bits = 8 bytes per clock cycle
BYTES_PER_WORD = 8
MIN_PACKET_BYTES = 64   # Minimum Ethernet frame size (without preamble/SFD)
MAX_PACKET_BYTES = 1518 # Maximum Ethernet frame size (without preamble/SFD)
MIN_PACKET_WORDS = MIN_PACKET_BYTES // BYTES_PER_WORD  # 8 words minimum
MAX_PACKET_WORDS = MAX_PACKET_BYTES // BYTES_PER_WORD  # 189 words (full)
MAX_PACKET_LAST_EMPTY = MAX_PACKET_BYTES % BYTES_PER_WORD  # 6 bytes in last word

# Ready signal delay (AV_STREAM_RDY has 1 cycle delay)
READY_DELAY_CYCLES = 1

# Test data patterns
TEST_DATA_PATTERNS = {
    'simple': [0x1122334455667788, 0xDEADBEEFCAFEBABE],
    'alternating': [0x0102030405060708, 0xA5A5A5A5A5A5A5A5, 0xFFFFFFFF00000000],
    'all_ones': [0xFFFFFFFFFFFFFFFF],
    'all_zeros': [0x0000000000000000],
    'incrementing': list(range(0x1000, 0x1008)),
}
