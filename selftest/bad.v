// selftest bad: bit 0 of q intentionally flipped on load
module selftest_bad (
    input  wire       clk,
    input  wire       rst,
    input  wire       en,
    input  wire [3:0] d,
    output reg  [3:0] q
);
    always @(posedge clk) begin
        if (rst)    q <= 4'b0;
        else if (en) q <= {d[3:1], ~d[0]};  // bit 0 intentionally wrong
    end
endmodule
