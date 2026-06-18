// selftest/dirty.v -- deliberately unreadable spec for check_readability self-check
module dirty_spec (
    input  wire clk, rstn, sel, COUNT0,
    input  wire X1234_ZN,
    output reg  q
);
    always @(posedge clk or negedge rstn) begin
        if (!rstn) q <= 1'b0;
        else q <= ~(X1234_ZN & sel & COUNT0);   // raw NAND3 in D-input
    end
endmodule
