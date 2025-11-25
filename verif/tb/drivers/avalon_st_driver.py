"""
Avalon-ST Source Driver (BFM)
Drives data/valid/sop/eop/empty/error and honors ready signal.
"""
import cocotb
from cocotb.triggers import RisingEdge


class AvalonSTSource:
    """
    Simple Avalon-ST source driver:
    drives data/valid/sop/eop/empty/error and honors ready.
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

    async def send_packet(self, words, empty_last=0, error=False):
        """
        Send a packet with the given data words.
        
        Args:
            words: List of data words to send
            empty_last: Empty field value for the last beat
            error: Error flag value for the packet
        
        Note: AV_STREAM_RDY has 1 cycle delay, so ready signal responds
        one cycle after valid/data are asserted.
        """
        # idle defaults
        self.valid.value = 0
        self.sop.value   = 0
        self.eop.value   = 0
        self.empty.value = 0
        self.error.value = 0

        await RisingEdge(self.clk)

        n = len(words)
        for i, w in enumerate(words):
            self.data.value  = w
            self.empty.value = empty_last if i == n - 1 else 0
            self.error.value = int(error)
            self.sop.value   = int(i == 0)
            self.eop.value   = int(i == n - 1)
            self.valid.value = 1

            # Wait for ready signal (accounts for 1-cycle delay in AV_STREAM_RDY)
            # When ready goes high, the transfer happens on that cycle
            while True:
                await RisingEdge(self.clk)
                if self.ready.value:
                    break

        # return to idle
        self.valid.value = 0
        self.sop.value   = 0
        self.eop.value   = 0
        self.empty.value = 0
        self.error.value = 0
        await RisingEdge(self.clk)

    async def send_packet_with_backpressure(self, words, empty_last=0, error=False, 
                                           ready_control=None):
        """
        Send a packet with external ready control (for testing backpressure).
        
        Args:
            words: List of data words to send
            empty_last: Empty field value for the last beat
            error: Error flag value for the packet
            ready_control: Coroutine that controls ready signal
        """
        # idle defaults
        self.valid.value = 0
        self.sop.value   = 0
        self.eop.value   = 0
        self.empty.value = 0
        self.error.value = 0

        await RisingEdge(self.clk)

        n = len(words)
        for i, w in enumerate(words):
            self.data.value  = w
            self.empty.value = empty_last if i == n - 1 else 0
            self.error.value = int(error)
            self.sop.value   = int(i == 0)
            self.eop.value   = int(i == n - 1)
            self.valid.value = 1

            # wait until DUT is ready and a transfer happens
            while True:
                await RisingEdge(self.clk)
                if self.ready.value:
                    break

        # return to idle
        self.valid.value = 0
        self.sop.value   = 0
        self.eop.value   = 0
        self.empty.value = 0
        self.error.value = 0
        await RisingEdge(self.clk)

    def set_idle(self):
        """Set driver to idle state."""
        self.valid.value = 0
        self.sop.value   = 0
        self.eop.value   = 0
        self.empty.value = 0
        self.error.value = 0


class AvalonSTQueuedSource:
    """
    Avalon-ST source driver with packet queue.
    Can queue multiple packets and send them as ready allows.
    Non-blocking - packets are queued and sent in background.
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
        
        self.packet_queue = []  # Queue of (words, empty_last, error) tuples
        self.current_packet = None
        self.current_word_idx = 0
        self._running = False

    async def queue_packet(self, words, empty_last=0, error=False):
        """
        Queue a packet to be sent. Non-blocking.
        
        Args:
            words: List of data words to send
            empty_last: Empty field value for the last beat
            error: Error flag value for the packet
        """
        self.packet_queue.append((words, empty_last, error))
        
        # Start the send task if not already running
        if not self._running:
            self._running = True
            import cocotb
            cocotb.start_soon(self._send_task())

    async def _send_task(self):
        """Background task that sends queued packets."""
        # Initialize to idle
        self.valid.value = 0
        self.sop.value   = 0
        self.eop.value   = 0
        self.empty.value = 0
        self.error.value = 0
        
        await RisingEdge(self.clk)
        
        while True:
            # Get next packet if we don't have one
            if self.current_packet is None:
                if not self.packet_queue:
                    # No packets, go idle
                    self.valid.value = 0
                    self.sop.value   = 0
                    self.eop.value   = 0
                    self.empty.value = 0
                    self.error.value = 0
                    await RisingEdge(self.clk)
                    continue
                
                # Get next packet from queue
                words, empty_last, error = self.packet_queue.pop(0)
                self.current_packet = (words, empty_last, error)
                self.current_word_idx = 0
            
            # Send current word
            words, empty_last, error = self.current_packet
            n = len(words)
            i = self.current_word_idx
            
            self.data.value  = words[i]
            self.empty.value = empty_last if i == n - 1 else 0
            self.error.value = int(error)
            self.sop.value   = int(i == 0)
            self.eop.value   = int(i == n - 1)
            self.valid.value = 1
            
            # Wait for ready
            await RisingEdge(self.clk)
            while not self.ready.value:
                await RisingEdge(self.clk)
            
            # Move to next word
            self.current_word_idx += 1
            
            # Check if packet is complete
            if self.current_word_idx >= n:
                # Packet complete, return to idle
                self.valid.value = 0
                self.sop.value   = 0
                self.eop.value   = 0
                self.empty.value = 0
                self.error.value = 0
                self.current_packet = None
                self.current_word_idx = 0
                await RisingEdge(self.clk)

    def get_queue_size(self):
        """Get number of packets in queue."""
        queue_size = len(self.packet_queue)
        if self.current_packet is not None:
            queue_size += 1
        return queue_size

    def clear_queue(self):
        """Clear all queued packets."""
        self.packet_queue = []
        self.current_packet = None
        self.current_word_idx = 0

    def set_idle(self):
        """Set driver to idle state (stops sending but keeps queue)."""
        self.valid.value = 0
        self.sop.value   = 0
        self.eop.value   = 0
        self.empty.value = 0
        self.error.value = 0

