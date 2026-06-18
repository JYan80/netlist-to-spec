// selftest/clean.v -- readable spec for check_readability self-check
module clean_spec (
    input  wire clk, rstn, sel, count_en,
    input  wire [3:0] d_load,
    output reg  [3:0] acc
);
    wire [3:0] acc_next = acc + 4'b1;

    always @(posedge clk or negedge rstn) begin
        if (!rstn)       acc <= 4'b0;
        else if (sel)    acc <= d_load;
        else if (count_en) acc <= acc_next;
        else             acc <= acc;
    end
endmodule
