`timescale 1ns/1ps

import packet_mux_pkg::*;

module arbiter #(
    parameter DATA_W  = packet_mux_pkg::DATA_W,
    parameter EMPTY_W = packet_mux_pkg::EMPTY_W
)(
    input  logic                clk,
    input  logic                rst_n,

    // Port A input
    input  logic [DATA_W-1:0]   a_data,
    input  logic                a_valid,
    input  logic                a_sop,
    input  logic                a_eop,
    input  logic [EMPTY_W-1:0]  a_empty,
    input  logic                a_error,
    output logic                a_ready,

    // Port B input
    input  logic [DATA_W-1:0]   b_data,
    input  logic                b_valid,
    input  logic                b_sop,
    input  logic                b_eop,
    input  logic [EMPTY_W-1:0]  b_empty,
    input  logic                b_error,
    output logic                b_ready,

    // Port C output
    output logic [DATA_W-1:0]   c_data,
    output logic                c_valid,
    output logic                c_sop,
    output logic                c_eop,
    output logic [EMPTY_W-1:0]  c_empty,
    output logic                c_error,
    input  logic                c_ready
);

    // FSM: which port currently has the grant / is being forwarded
    typedef enum logic [1:0] {
        ST_IDLE      = 2'b00,
        ST_FORWARD_A = 2'b01,
        ST_FORWARD_B = 2'b10
    } pm_state_t;

    pm_state_t current_state, next_state;        

    // Combinational next-state and output logic
    always_comb begin
        // defaults
        next_state   = current_state;

        c_data  = {DATA_W{1'b0}};
        c_valid = 1'b0;
        c_sop   = 1'b0;
        c_eop   = 1'b0;
        c_empty = {EMPTY_W{1'b0}};
        c_error = 1'b0;

        a_ready = 1'b0;
        b_ready = 1'b0;

        case (current_state)
            ST_IDLE: begin
                
                // Strict priority: A > B
                if (a_valid) begin
                    c_data  = a_data;
                    c_valid = a_valid;
                    c_sop   = a_sop;
                    c_eop   = a_eop;
                    c_empty = a_empty;
                    c_error = a_error;
                    a_ready = c_ready;

                    if (a_sop && !a_eop) begin                         
                        next_state = ST_FORWARD_A;
                    end
                end
                // Forward B
                else if (b_valid) begin                    
                    c_data  = b_data;
                    c_valid = b_valid;
                    c_sop   = b_sop;
                    c_eop   = b_eop;
                    c_empty = b_empty;
                    c_error = b_error;
                    b_ready  = c_ready;                   

                    if (b_sop && !b_eop) begin                        
                        next_state = ST_FORWARD_B;
                    end
                end                
            end

            ST_FORWARD_A: begin
                // Continue forwarding packet from A
                c_data      = a_data;
                c_valid     = a_valid;
                c_sop       = a_sop;   
                c_eop       = a_eop;
                c_empty     = a_empty;
                c_error     = a_error;

                a_ready = c_ready;
                b_ready = 1'b0;

                // Packet completes when we accept EOP
                if (c_ready && a_valid && a_eop) begin
                    next_state = ST_IDLE;
                end
            end

            ST_FORWARD_B: begin
                // Continue forwarding packet from B
                c_data      = b_data;
                c_valid     = b_valid;
                c_sop       = b_sop;
                c_eop       = b_eop;
                c_empty     = b_empty;
                c_error     = b_error;

                b_ready = c_ready;
                a_ready = 1'b0;

                if (c_ready && b_valid && b_eop) begin
                    next_state = ST_IDLE;
                end
            end
            default: begin
                next_state = ST_IDLE;
            end
        endcase
    end

    // Sequential state register
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            current_state <= ST_IDLE;
        end else begin
            current_state <= next_state;
        end
    end

endmodule
