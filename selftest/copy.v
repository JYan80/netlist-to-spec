// selftest copy: identical logic to gold, different module name
module selftest_copy (
    input  wire       clk,
    input  wire       rst,
    input  wire       en,
    input  wire [3:0] d,
    output reg  [3:0] q
);
    always @(posedge clk) begin
        if (rst)    q <= 4'b0;
        else if (en) q <= d;
    end
endmodule
