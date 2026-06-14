module COUNT_6B_2_spec (
    input wire CI,
    input wire [3:0] DT,
    output reg [5:0] MI2_Q,
    input wire RST,
    input wire X19_GS,
    input wire X19_VS,
    input wire X61_35_Z, // 时钟
    input wire X398_46_Z, // 主选择控制
    input wire X595_149_Z // 位 2 专用选择控制
);

    wire [5:0] count_next = MI2_Q + CI;

    always @(posedge X61_35_Z or negedge RST) begin
        if (!RST) begin
            MI2_Q <= 6'b0;
        end else begin
            // 使用拼接运算符将 6 位值整体赋值
            // 分为三段处理：高 3 位 [5:3]、第 2 位 [2]、低 2 位 [1:0]
            MI2_Q <= {
                (X398_46_Z  ? {DT[2], DT[0], MI2_Q[4]} : count_next[5:3]),
                (X595_149_Z ? DT[3]                    : count_next[2]),
                (X398_46_Z  ? {DT[1], MI2_Q[1]}        : count_next[1:0])
            };
        end
    end

endmodule