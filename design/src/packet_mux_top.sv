`timescale 1ns/1ps

import packet_mux_pkg::*;

module packet_mux_top #(
    parameter DATA_W  = packet_mux_pkg::DATA_W, // 64
    parameter EMP_W  = packet_mux_pkg::EMPTY_W // 3
)(
    input  logic        clk,
    input  logic        rst_n,

    // --- PORT A (High Priority) ---
    input  logic [DATA_W-1:0] porta_data,
    input  logic              porta_valid,
    input  logic              porta_sop,
    input  logic              porta_eop,
    input  logic [EMP_W-1:0]  porta_empty,
    input  logic              porta_error,
    output logic              porta_ready,

    // --- PORT B (Low Priority) ---
    input  logic [DATA_W-1:0] portb_data,
    input  logic              portb_valid,
    input  logic              portb_sop,
    input  logic              portb_eop,
    input  logic [EMP_W-1:0]  portb_empty,
    input  logic              portb_error,
    output logic              portb_ready,

    // --- PORT C (Output) ---
    output logic [DATA_W-1:0] portc_data,
    output logic              portc_valid,
    output logic              portc_sop,
    output logic              portc_eop,
    output logic [EMP_W-1:0]  portc_empty,
    output logic              portc_error,
    input  logic              portc_ready
);

    // Internal Signals (After Buffers, entering Mux)
    logic [DATA_W-1:0] a_data_int, b_data_int;
    logic        a_valid_int, b_valid_int;
    logic        a_sop_int, b_sop_int;
    logic        a_eop_int, b_eop_int;
    logic [EMP_W-1:0]  a_empty_int, b_empty_int;
    logic        a_error_int, b_error_int;
    logic        a_ready_int, b_ready_int;

    // Port B FIFO Connection Signals
    logic [DATA_W-1:0] b_fifo_in_data;
    logic        b_fifo_in_valid, b_fifo_in_sop, b_fifo_in_eop, b_fifo_in_error;
    logic [EMP_W-1:0]  b_fifo_in_empty;
    logic        b_fifo_in_ready;

    // ------------------------------------------------------------
    // 1. PORT A PATH (Latency Critical)
    // ------------------------------------------------------------
    skid_buffer #(DATA_W, EMP_W) u_skid_a (
        .clk     (clk), 
        .rst_n   (rst_n),

        // External Inputs
        .s_data  (porta_data), 
        .s_valid (porta_valid), 
        .s_sop   (porta_sop), 
        .s_eop   (porta_eop), 
        .s_empty (porta_empty), 
        .s_error (porta_error),
        .s_ready (porta_ready),

        // To arbiter (port A)
        .m_data  (a_data_int), 
        .m_valid (a_valid_int), 
        .m_sop   (a_sop_int),
        .m_eop   (a_eop_int), 
        .m_empty (a_empty_int), 
        .m_error (a_error_int),
        .m_ready (a_ready_int)
    );

    // ------------------------------------------------------------
    // 2. PORT B PATH (Buffered)
    // ------------------------------------------------------------
    // Step 1: Skid Buffer (Handles Latency 1 from Port B)
    skid_buffer #(DATA_W, EMP_W) u_skid_b (
        .clk     (clk), 
        .rst_n   (rst_n),

        // External Inputs
        .s_data  (portb_data), 
        .s_valid (portb_valid), 
        .s_sop   (portb_sop),
        .s_eop   (portb_eop), 
        .s_empty (portb_empty), 
        .s_error (portb_error),
        .s_ready (portb_ready),

        // To FIFO
        .m_data  (b_fifo_in_data), 
        .m_valid (b_fifo_in_valid), 
        .m_sop   (b_fifo_in_sop),
        .m_eop   (b_fifo_in_eop), 
        .m_empty (b_fifo_in_empty), 
        .m_error (b_fifo_in_error),
        .m_ready (b_fifo_in_ready)
    );

    // Step 2: Deep FIFO (Uses N_LATENCY=3 for Almost Full)
    sync_fifo #(
        .DATA_W(DATA_W), 
        .DEPTH(512), 
        .EMP_W(EMP_W), 
        .N_LATENCY(3)
    ) u_fifo_b (
        .clk     (clk), 
        .rst_n   (rst_n),

        // From Skid Buffer
        .w_data  (b_fifo_in_data), 
        .w_valid (b_fifo_in_valid), 
        .w_sop   (b_fifo_in_sop),
        .w_eop   (b_fifo_in_eop), 
        .w_empty (b_fifo_in_empty), 
        .w_error (b_fifo_in_error),
        .w_ready (b_fifo_in_ready),

        // To arbiter (port B)
        .r_data  (b_data_int), 
        .r_valid (b_valid_int), 
        .r_sop   (b_sop_int),
        .r_eop   (b_eop_int), 
        .r_empty (b_empty_int), 
        .r_error (b_error_int),
        .r_ready (b_ready_int)
    );

    // ------------------------------------------------------------
    // 3. ARBITER 
    // ------------------------------------------------------------
    
    arbiter #(DATA_W, EMP_W) u_arbiter (
        .clk     (clk),
        .rst_n   (rst_n),    
        // Port A 
        .a_data  (a_data_int),
        .a_valid (a_valid_int),
        .a_sop   (a_sop_int),
        .a_eop   (a_eop_int),
        .a_empty (a_empty_int),
        .a_error (a_error_int),
        .a_ready (a_ready_int),

        // Port B
        .b_data  (b_data_int),
        .b_valid (b_valid_int),
        .b_sop   (b_sop_int),
        .b_eop   (b_eop_int),
        .b_empty (b_empty_int),
        .b_error (b_error_int),
        .b_ready (b_ready_int),

        // Port C
        .c_data  (portc_data),
        .c_valid (portc_valid),
        .c_sop   (portc_sop),
        .c_eop   (portc_eop),
        .c_empty (portc_empty),
        .c_error (portc_error),
        .c_ready (portc_ready)
    );

endmodule
