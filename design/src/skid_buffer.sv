`timescale 1ns/1ps

import packet_mux_pkg::*;

module skid_buffer #(
    parameter DATA_W = packet_mux_pkg::DATA_W, // 64
    parameter EMP_W  = packet_mux_pkg::EMPTY_W // 3
)(
    input  logic              clk,
    input  logic              rst_n,

    // Slave (input) Interface – one cycle latency
    input  logic [DATA_W-1:0] s_data,
    input  logic              s_valid,
    input  logic              s_sop,
    input  logic              s_eop,
    input  logic [EMP_W-1:0]  s_empty,
    input  logic              s_error,
    output logic              s_ready,

    // Master (output) Interface – zero latency
    output logic [DATA_W-1:0] m_data,
    output logic              m_valid,
    output logic              m_sop,
    output logic              m_eop,
    output logic [EMP_W-1:0]  m_empty,
    output logic              m_error,
    input  logic              m_ready
);

    // Internal buffer 
    logic [DATA_W-1:0] buf_data;    
    logic              buf_sop;
    logic              buf_eop;
    logic [EMP_W-1:0]  buf_empty;
    logic              buf_error;

    // Control signal indicating buffer holds valid data
    logic use_buffer;

    // Handshake: upstream beat accepted
    logic accept_in;

    // Ready generation
    assign s_ready   = m_ready || !use_buffer;
    assign accept_in = s_valid && s_ready;

    // Buffer FSM
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            use_buffer <= 1'b0;
            buf_data   <= '0;
            buf_sop    <= '0;
            buf_eop    <= '0;
            buf_empty  <= '0;
            buf_error  <= '0;
        end else begin
            if (use_buffer) begin
                // Buffer is full
                if (m_ready) begin
                    if (accept_in) begin
                        // Drain + refill same cycle
                        use_buffer <= 1'b1;
                        buf_data   <= s_data;
                        buf_sop    <= s_sop;
                        buf_eop    <= s_eop;
                        buf_empty  <= s_empty;
                        buf_error  <= s_error;
                    end else begin
                        // Drain only
                        use_buffer <= 1'b0;
                    end
                end
                // else downstream stalled → hold buffer
            end else begin
                // Buffer empty
                if (!m_ready && accept_in) begin
                    // Store into buffer
                    use_buffer <= 1'b1;
                    buf_data   <= s_data;
                    buf_sop    <= s_sop;
                    buf_eop    <= s_eop;
                    buf_empty  <= s_empty;
                    buf_error  <= s_error;
                end
                // else pass-through only
            end
        end
    end

    // Output mux
    always_comb begin
        if (use_buffer) begin
            m_data  = buf_data;
            m_valid = 1'b1;
            m_sop   = buf_sop;
            m_eop   = buf_eop;
            m_empty = buf_empty;
            m_error = buf_error;
        end else begin
            m_data  = s_data;
            m_valid = s_valid;
            m_sop   = s_sop;
            m_eop   = s_eop;
            m_empty = s_empty;
            m_error = s_error;
        end
    end

endmodule
