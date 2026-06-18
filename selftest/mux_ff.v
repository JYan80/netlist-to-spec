// selftest/mux_ff.v -- simple 2:1-mux FF for decode_modes self-check
module mux_ff (
    input  wire clk,
    input  wire rstn,   // async active-low reset
    input  wire sel,
    input  wire d0,
    input  wire d1,
    output reg  q
);
    always @(posedge clk or negedge rstn) begin
        if (!rstn) q <= 1'b0;
        else       q <= sel ? d1 : d0;
    end
endmodule
