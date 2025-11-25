"""
Avalon-ST Sink Monitor
Monitors and collects packets from the output port.
"""
import cocotb
from cocotb.triggers import RisingEdge


class AvalonSTSink:
    """
    Simple Avalon-ST monitor for the output port C.
    Collects packets as lists of data words.
    """
    def __init__(self, clk, data, valid, sop, eop, empty, error, ready):
        self.clk   = clk
        self.data  = data
        self.valid = valid
        self.sop   = sop
        self.eop   = eop
        self.empty = empty
        self.error = error
        self.ready = ready

        self.packets = []   # list[list[int]]
        self._cur_pkt = []
        self._in_pkt  = False
        self._packet_metadata = []  # Store metadata for each packet

    async def run(self, always_ready=True):
        """
        Monitor task that collects packets.
        
        Args:
            always_ready: If True, always assert ready. If False, ready is controlled externally.
        """
        if always_ready:
            self.ready.value = 1

        while True:
            await RisingEdge(self.clk)
            if self.valid.value and self.ready.value:
                d = int(self.data.value)
                empty_val = int(self.empty.value)
                error_val = int(self.error.value)

                if self.sop.value:
                    # start of new packet
                    self._cur_pkt = []
                    self._in_pkt  = True

                if self._in_pkt:
                    self._cur_pkt.append(d)

                if self.eop.value:
                    # end of packet
                    if self._in_pkt:
                        self.packets.append(self._cur_pkt.copy())
                        self._packet_metadata.append({
                            'empty': empty_val,
                            'error': error_val
                        })
                    self._cur_pkt = []
                    self._in_pkt  = False

    def clear(self):
        """Clear collected packets."""
        self.packets = []
        self._packet_metadata = []
        self._cur_pkt = []
        self._in_pkt = False

    def get_packet_count(self):
        """Get number of packets collected."""
        return len(self.packets)

    def get_last_packet_metadata(self):
        """Get metadata for the last packet."""
        if self._packet_metadata:
            return self._packet_metadata[-1]
        return None


class AvalonSTSinkWithBackpressure:
    """
    Avalon-ST monitor with controllable ready signal for backpressure testing.
    """
    def __init__(self, clk, data, valid, sop, eop, empty, error, ready):
        self.clk   = clk
        self.data  = data
        self.valid = valid
        self.sop   = sop
        self.eop   = eop
        self.empty = empty
        self.error = error
        self.ready = ready

        self.packets = []
        self._cur_pkt = []
        self._in_pkt  = False
        self._ready_state = True
        self._last_data = None  # Track last collected data to avoid duplicates
        self._last_valid_ready = False  # Track previous valid&&ready state

    async def run(self, ready_pattern=None):
        """
        Monitor task with controllable ready.
        
        Args:
            ready_pattern: List of (cycles, state) tuples for ready control.
                          If None, ready is always asserted.
                          Pattern repeats if it completes.
        """
        if ready_pattern is None:
            self.ready.value = 1
            self._ready_state = True
            while True:
                await RisingEdge(self.clk)
                if self.valid.value and self.ready.value:
                    d = int(self.data.value)

                    if self.sop.value:
                        self._cur_pkt = []
                        self._in_pkt  = True

                    if self._in_pkt:
                        self._cur_pkt.append(d)

                    if self.eop.value:
                        if self._in_pkt:
                            self.packets.append(self._cur_pkt.copy())
                        self._cur_pkt = []
                        self._in_pkt  = False
        else:
            # Pattern-based ready control
            pattern_idx = 0
            cycles_in_pattern = 0
            
            if ready_pattern:
                cycles, state = ready_pattern[0]
                self.ready.value = int(state)
                self._ready_state = bool(state)

            while True:
                await RisingEdge(self.clk)
                cycles_in_pattern += 1
                
                # Update ready based on pattern
                if pattern_idx < len(ready_pattern):
                    cycles, state = ready_pattern[pattern_idx]
                    if cycles_in_pattern >= cycles:
                        # Move to next pattern segment
                        pattern_idx += 1
                        cycles_in_pattern = 0
                        if pattern_idx < len(ready_pattern):
                            cycles, state = ready_pattern[pattern_idx]
                            self.ready.value = int(state)
                            self._ready_state = bool(state)
                        else:
                            # Pattern complete, repeat from beginning
                            pattern_idx = 0
                            if ready_pattern:
                                cycles, state = ready_pattern[0]
                                self.ready.value = int(state)
                                self._ready_state = bool(state)

                # Collect packet data
                # Track transfers to avoid collecting duplicates when same data is held for multiple cycles
                current_valid_ready = (self.valid.value and self.ready.value)
                
                if current_valid_ready:
                    d = int(self.data.value)
                    
                    # Handle SOP - start new packet
                    if self.sop.value:
                        self._cur_pkt = []
                        self._in_pkt  = True
                        # Reset last_data on new packet
                        self._last_data = None
                        self._last_valid_ready = False  # Force collection on first word
                    
                    # Only collect if:
                    # 1. Rising edge of valid&&ready (new transfer after backpressure), OR
                    # 2. Data changed from last collected (new word)
                    # This prevents duplicate collection when same data is held for multiple cycles,
                    # but allows collection when ready goes high after backpressure
                    is_rising_edge = not self._last_valid_ready
                    data_changed = (self._last_data is not None and d != self._last_data)
                    is_new_data = (self._last_data is None or d != self._last_data)
                    
                    # Collect on rising edge (even if same data) OR when data changes
                    if (is_rising_edge or data_changed) and self._in_pkt:
                        self._last_data = d
                        self._cur_pkt.append(d)
                    
                    self._last_valid_ready = True

                    # Handle EOP - end packet
                    if self.eop.value and self._in_pkt:
                        self.packets.append(self._cur_pkt.copy())
                        self._cur_pkt = []
                        self._in_pkt  = False
                        # Reset last_data after packet ends
                        self._last_data = None
                else:
                    # Reset tracking when not in transfer (backpressure)
                    self._last_valid_ready = False
                    # Keep last_data to detect if same data appears again after backpressure

    def set_ready(self, value):
        """Set ready signal value."""
        self.ready.value = int(value)
        self._ready_state = bool(value)

    def get_packet_count(self):
        """Get number of packets collected."""
        return len(self.packets)

    def clear(self):
        """Clear collected packets."""
        self.packets = []
        self._cur_pkt = []
        self._in_pkt = False
        self._last_data = None
        self._last_valid_ready = False

