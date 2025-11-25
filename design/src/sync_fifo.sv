module sync_fifo #(
    parameter DATA_W      = packet_mux_pkg::DATA_W, // 64
    parameter DEPTH       = 512, // Store ~4KB (Multiple MTUs)
    parameter EMP_W       = packet_mux_pkg::EMPTY_W, // 3
    parameter N_LATENCY   = 3    // Safety margin for backpressure propagation delay
)(
    input  logic clk,
    input  logic rst_n,

    // Write Interface
    input  logic [DATA_W-1:0] w_data,
    input  logic              w_valid,
    input  logic              w_sop,
    input  logic              w_eop,
    input  logic [EMP_W-1:0]  w_empty,
    input  logic              w_error,
    output logic              w_ready,

    // Read Interface
    output logic [DATA_W-1:0] r_data,
    output logic              r_valid,
    output logic              r_sop,
    output logic              r_eop,
    output logic [EMP_W-1:0]  r_empty,
    output logic              r_error,
    input  logic              r_ready
);
    
    // Payload width calculation
    localparam PAYLOAD_W = DATA_W + 1 + 1 + EMP_W + 1; 
    
    // Check constraint: Depth must be greater than latency margin
`ifndef SYNTHESIS
    initial begin
        if (DEPTH <= N_LATENCY) $fatal(1, "FIFO Depth must be greater than N_LATENCY for Almost Full logic to work.");
    end
`endif

    // FIFO Memory and Pointers
    logic [PAYLOAD_W-1:0] mem [0:DEPTH-1];
    logic [$clog2(DEPTH)-1:0] w_ptr, r_ptr;
    logic [$clog2(DEPTH):0]   count;

    // Pack Write Signals
    logic [PAYLOAD_W-1:0] w_payload;
    assign w_payload = {w_data, w_sop, w_eop, w_empty, w_error};

    // --- Write and Count Logic ---
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            w_ptr <= '0;
            count <= '0;
        end else begin
            // Write Pointer Update
            if (w_valid && w_ready) begin
                mem[w_ptr] <= w_payload;
                w_ptr <= w_ptr + 1'b1;
            end
            
            // Count Update 
            if ((w_valid && w_ready) && !(r_valid && r_ready))
                count <= count + 1'b1;
            else if (!(w_valid && w_ready) && (r_valid && r_ready))
                count <= count - 1'b1;
        end
    end

    // --- Read Logic ---
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            r_ptr <= '0;
        end else begin
            if (r_valid && r_ready) begin
                r_ptr <= r_ptr + 1'b1;
            end
        end
    end

    // --- Output Assignments ---
    logic [PAYLOAD_W-1:0] r_payload_out;
    assign r_payload_out = mem[r_ptr];
    
    assign {r_data, r_sop, r_eop, r_empty, r_error} = r_payload_out;
    
    // Output Valid (Data is available if count > 0)
    assign r_valid = (count != 0);

    // --- Almost Full Logic  ---
    // The FIFO stops accepting data when its remaining capacity equals or 
    // is less than the backpressure latency (N_LATENCY).
    localparam ALMOST_FULL_THRESHOLD = DEPTH - N_LATENCY;

    assign w_ready = (count < ALMOST_FULL_THRESHOLD); 
    // If count reaches (DEPTH - 3), w_ready goes low, giving the writer 3 cycles
    // to stop before the FIFO would overflow.

endmodule
