// selftest gold: 4-bit register with sync reset and load enable
module selftest_gold (
    input  wire       clk,
    input  wire       rst,    // synchronous active-high reset
    input  wire       en,
    input  wire [3:0] d,
    output reg  [3:0] q
);
    always @(posedge clk) begin
        if (rst)    q <= 4'b0;
        else if (en) q <= d;
    end
endmodule
