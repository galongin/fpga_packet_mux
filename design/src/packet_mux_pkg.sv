package packet_mux_pkg;

    // Data width for AVST interface. 
    // Since Altera 10G Ethernet design uses a 156.25MHz clock, we can assume 64 data bits.
    parameter int DATA_W  = 64;
    
    // Empty width assume up to 8 empty Bytes - 3 bits. 
    parameter int EMPTY_W = $clog2(DATA_W/8); 

endpackage : packet_mux_pkg

