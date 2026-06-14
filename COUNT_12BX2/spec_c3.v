// COUNT_12BX2_spec.v - Behavioral RTL spec for COUNT_12BX2
// Auto-generated from netlist using assign statements for comb logic
// and always blocks for sequential logic (FFs with async reset).

module COUNT_12BX2_spec (
    input  wire        COUNT0,
    input  wire        COUNT1N,
    input  wire        COUNT2,
    input  wire        COUNT3N,
    input  wire        CTRL0,
    input  wire        CTRL1,
    input  wire        CTRL2,
    input  wire [1:0]  DT,
    input  wire [2:0]  HOLD0,
    input  wire [2:0]  HOLD1,
    input  wire [3:0]  MI44_Q,
    input  wire        SET0N,
    input  wire        SET1,
    input  wire        SET2,
    input  wire        SET3,
    input  wire        SET4,
    input  wire        SET5,
    input  wire        X3_323_Z,
    input  wire        X19_GS,
    input  wire        X19_VS,
    input  wire        X412_46_Z,
    input  wire        X1026_138_ZN,
    input  wire        X1027_138_ZN,
    input  wire        X1676_Z,
    input  wire        X8710_Z,
    output wire [1:0]  MI1_QT,
    output wire [11:1] MI1_SUM
);

  // Intermediate combinational wires
  wire X1033_5_ZN;
  wire X154_21_ZN;
  // word-level arithmetic wires (Phase C1)
  wire [10:0] opA = {a10, a9, a8, a7, a6, a5, a4, a3, a2, a1, a0};
  wire [10:0] opB = {b10, b9, b8, b7, b6, b5, b4, b3, b2, b1, b0};
  wire [11:0] sum_ext = {1'b0, opA} + {1'b0, opB} + {11'b0, CTRL0};
  wire [11:0] raw_sum_ext = {1'b0, opA} + {1'b0, opB};
  wire X1889_ZN;
  wire X1891_CO;
  wire X1892_CO;
  wire X214_21_ZN;
  wire X2492_CO;
  wire X24_263_CO;
  wire X27_263_CO;
  wire X28_263_CO;
  wire X31_263_CO;
  wire X32_263_CO;
  wire X3484_ZN;
  wire X3510_ZN;
  wire X36_263_CO;
  wire X420_ZN;
  wire X47_344_CO;
  wire X59_5_ZN;
  wire X622_5_ZN;
  wire X623_5_ZN;
  wire X625_5_ZN;
  wire X630_103_Z;
  wire X703_103_Z;
  wire X747_5_ZN;
  wire X748_5_ZN;
  wire X751_5_ZN;
  wire X8397_ZN;
  wire X8403_ZN;
  wire X8405_ZN;
  wire X8409_ZN;
  wire X8411_ZN;
  wire X8418_ZN;
  wire X8419_ZN;
  wire X8625_CO;
  wire X8626_CO;
  wire X8628_CO;
  wire X8631_CO;
  wire X8633_CO;
  wire X8634_CO;
  wire X8635_CO;
  wire X8637_CO;
  wire X8638_CO;
  wire X911_5_ZN;

  // Sequential state registers

  // MI1_QT output registers
  reg a0, b9;
  assign MI1_QT[0] = a0;
  assign MI1_QT[1] = b9;

  // Clock / reset / select aliases

  wire CLK_A    = X1026_138_ZN;

  wire CLK_B    = X1027_138_ZN;

  wire RST_MAIN = X3_323_Z;

  wire RST_AUX  = X1676_Z;

  wire SEL_A    = X8710_Z;

  wire SEL_B    = X412_46_Z;

  // Operand accumulator state bits

  reg a0; // a0

  reg a1; // a1

  reg a10; // a10

  reg a2; // a2

  reg a3; // a3

  reg a4; // a4

  reg a5; // a5

  reg a6; // a6

  reg a7; // a7

  reg a8; // a8

  reg a9; // a9

  reg b0; // b0

  reg b1; // b1

  reg b10; // b10

  reg b2; // b2

  reg b3; // b3

  reg b4; // b4

  reg b5; // b5

  reg b6; // b6

  reg b7; // b7

  reg b8; // b8

  reg b9; // b9

  // Combinational logic
  assign MI1_SUM = sum_ext[11:1];
  assign X24_263_CO = (MI1_SUM[8]&X28_263_CO)|(MI1_SUM[8]&b7)|(X28_263_CO&b7);
  assign X27_263_CO = (MI1_SUM[2]&X630_103_Z)|(MI1_SUM[2]&a1)|(X630_103_Z&a1);
  assign X28_263_CO = (MI1_SUM[7]&X32_263_CO)|(MI1_SUM[7]&a6)|(X32_263_CO&a6);
  assign X31_263_CO = (MI1_SUM[8]&X8625_CO)|(MI1_SUM[8]&a7)|(X8625_CO&a7);
  assign X32_263_CO = (MI1_SUM[6]&X2492_CO)|(MI1_SUM[6]&a5)|(X2492_CO&a5);
  assign X36_263_CO = (MI1_SUM[6]&X8638_CO)|(MI1_SUM[6]&b5)|(X8638_CO&b5);
  assign X47_344_CO = (MI1_SUM[10]&X1892_CO)|(MI1_SUM[10]&a9)|(X1892_CO&a9);
  assign X59_5_ZN = raw_sum_ext[8];
  assign X154_21_ZN = ~(((X27_263_CO^b2^MI1_SUM[3])|CTRL1)&((X8626_CO^a2^MI1_SUM[3])|CTRL2));
  assign X214_21_ZN = ~(((X630_103_Z^a1^MI1_SUM[2])|CTRL1)&((X703_103_Z^b1^MI1_SUM[2])|CTRL2));
  assign X420_ZN = ~(((X8625_CO^a7^MI1_SUM[8])|CTRL1)&((X28_263_CO^b7^MI1_SUM[8])|CTRL2));
  assign X622_5_ZN = raw_sum_ext[3];
  assign X623_5_ZN = ~SET0N;
  assign X625_5_ZN = raw_sum_ext[6];
  assign X630_103_Z = MI1_SUM[1]&MI1_QT[0];
  assign X703_103_Z = MI1_SUM[1]&b0;
  assign X747_5_ZN = raw_sum_ext[2];
  assign X748_5_ZN = raw_sum_ext[9];
  assign X751_5_ZN = raw_sum_ext[5];
  assign X911_5_ZN = raw_sum_ext[7];
  assign X1033_5_ZN = raw_sum_ext[10];
  assign X1889_ZN = ~(((X1891_CO^b4^MI1_SUM[5])|CTRL1)&((X8634_CO^a4^MI1_SUM[5])|CTRL2));
  assign X1891_CO = (MI1_SUM[4]&X8637_CO)|(MI1_SUM[4]&b3)|(X8637_CO&b3);
  assign X1892_CO = (MI1_SUM[9]&X31_263_CO)|(MI1_SUM[9]&b8)|(X31_263_CO&b8);
  assign X2492_CO = (MI1_SUM[5]&X8634_CO)|(MI1_SUM[5]&a4)|(X8634_CO&a4);
  assign X3484_ZN = raw_sum_ext[1];
  assign X3510_ZN = raw_sum_ext[4];
  assign X8397_ZN = ~(((X8638_CO^b5^MI1_SUM[6])|CTRL1)&((X2492_CO^a5^MI1_SUM[6])|CTRL2));
  assign X8403_ZN = ~(((X1892_CO^a9^MI1_SUM[10])|CTRL1)&((X8635_CO^MI1_QT[1]^MI1_SUM[10])|CTRL2));
  assign X8405_ZN = ~(((X31_263_CO^b8^MI1_SUM[9])|CTRL1)&((X24_263_CO^a8^MI1_SUM[9])|CTRL2));
  assign X8409_ZN = ~((((MI1_SUM[11]&X47_344_CO)|(MI1_SUM[11]&a10)|(X47_344_CO&a10))|CTRL1)&(((MI1_SUM[11]&X8633_CO)|(MI1_SUM[11]&b10)|(X8633_CO&b10))|CTRL2));
  assign X8411_ZN = ~(((X36_263_CO^b6^MI1_SUM[7])|CTRL1)&((X32_263_CO^a6^MI1_SUM[7])|CTRL2));
  assign X8418_ZN = ~(((X8637_CO^b3^MI1_SUM[4])|CTRL1)&((X8628_CO^a3^MI1_SUM[4])|CTRL2));
  assign X8419_ZN = ~(((X47_344_CO^a10^MI1_SUM[11])|CTRL1)&((X8633_CO^b10^MI1_SUM[11])|CTRL2));
  assign X8625_CO = (MI1_SUM[7]&X36_263_CO)|(MI1_SUM[7]&b6)|(X36_263_CO&b6);
  assign X8626_CO = (MI1_SUM[2]&X703_103_Z)|(MI1_SUM[2]&b1)|(X703_103_Z&b1);
  assign X8628_CO = (MI1_SUM[3]&X8626_CO)|(MI1_SUM[3]&a2)|(X8626_CO&a2);
  assign X8631_CO = raw_sum_ext[11];
  assign X8633_CO = (MI1_SUM[10]&X8635_CO)|(MI1_SUM[10]&MI1_QT[1])|(X8635_CO&MI1_QT[1]);
  assign X8634_CO = (MI1_SUM[4]&X8628_CO)|(MI1_SUM[4]&a3)|(X8628_CO&a3);
  assign X8635_CO = (MI1_SUM[9]&X24_263_CO)|(MI1_SUM[9]&a8)|(X24_263_CO&a8);
  assign X8637_CO = (MI1_SUM[3]&X27_263_CO)|(MI1_SUM[3]&b2)|(X27_263_CO&b2);
  assign X8638_CO = (MI1_SUM[5]&X1891_CO)|(MI1_SUM[5]&b4)|(X1891_CO&b4);

  // CLK_A, RST_MAIN, SEL_A
  always @(posedge X1026_138_ZN or negedge X3_323_Z) begin
    if (!X3_323_Z) begin
      a1 <= 1'b0;
      b1 <= 1'b0;
      a0 <= 1'b0;
      b0 <= 1'b0;
      b10 <= 1'b0;
    end else begin
      a1 <= X8710_Z ? b1 : (~((COUNT1N|X154_21_ZN)&(~((HOLD0[2]&a1)|(COUNT0&X747_5_ZN)))&(~(SET2&MI44_Q[1]))));
      b1 <= X8710_Z ? b2 : (~((COUNT3N|X154_21_ZN)&(~((MI44_Q[1]&SET5)|(X747_5_ZN&COUNT2)))&(~(HOLD1[2]&b1))));
      a0 <= X8710_Z ? a1 : (~((COUNT1N|X214_21_ZN)&(~((HOLD0[2]&MI1_QT[0])|(COUNT0&X3484_ZN)))&(~(SET2&MI44_Q[0]))));
      b0 <= X8710_Z ? b10 : (~((COUNT3N|X214_21_ZN)&(~((SET5&MI44_Q[0])|(COUNT2&X3484_ZN)))&(~(HOLD1[2]&b0))));
      b10 <= X8710_Z ? DT[0] : (~((COUNT3N|X8409_ZN)&(~((HOLD1[0]&b10)|(MI44_Q[2]&SET3)))&(~(X8631_CO&COUNT2))));
    end
  end

  // CLK_B, RST_MAIN, SEL_A
  always @(posedge X1027_138_ZN or negedge X3_323_Z) begin
    if (!X3_323_Z) begin
      a10 <= 1'b0;
      a3 <= 1'b0;
      a2 <= 1'b0;
      b2 <= 1'b0;
      a9 <= 1'b0;
    end else begin
      a10 <= X8710_Z ? b0 : (~((COUNT1N|X8409_ZN)&(~((a10&HOLD0[0])|(COUNT0&X8631_CO)))&(~(SET1&MI44_Q[2]))));
      a3 <= X8710_Z ? b3 : (~((COUNT3N|X1889_ZN)&(~((MI44_Q[3]&SET5)|(X3510_ZN&COUNT2)))&(~(HOLD1[2]&a3))));
      a2 <= X8710_Z ? a3 : (~((COUNT3N|X8418_ZN)&(~((MI44_Q[2]&SET5)|(X622_5_ZN&COUNT2)))&(~(HOLD1[2]&a2))));
      b2 <= X8710_Z ? a2 : (~((COUNT1N|X8418_ZN)&(~((HOLD0[2]&b2)|(COUNT0&X622_5_ZN)))&(~(SET2&MI44_Q[2]))));
      a9 <= X8710_Z ? a10 : (~((COUNT1N|X8419_ZN)&(~((a9&HOLD0[0])|(COUNT0&X1033_5_ZN)))&(~(SET1&MI44_Q[1]))));
    end
  end

  // CLK_B, RST_AUX, SEL_A
  always @(posedge X1027_138_ZN or negedge X1676_Z) begin
    if (!X1676_Z) begin
      b9 <= 1'b0;
    end else begin
      b9 <= X8710_Z ? a9 : (~((COUNT3N|X8419_ZN)&(~((HOLD1[0]&MI1_QT[1])|(MI44_Q[1]&SET3)))&(~(X1033_5_ZN&COUNT2))));
    end
  end

  // CLK_B, RST_MAIN, SEL_B
  always @(posedge X1027_138_ZN or negedge X3_323_Z) begin
    if (!X3_323_Z) begin
      a4 <= 1'b0;
      a6 <= 1'b0;
      b5 <= 1'b0;
      b4 <= 1'b0;
      b3 <= 1'b0;
      b6 <= 1'b0;
      a5 <= 1'b0;
      a7 <= 1'b0;
      b7 <= 1'b0;
    end else begin
      a4 <= X412_46_Z ? b5 : (~((COUNT3N|X8397_ZN)&(~((X751_5_ZN&COUNT2)|(MI44_Q[0]&SET4)))&(~(HOLD1[1]&a4))));
      a6 <= X412_46_Z ? b6 : (~((COUNT3N|X420_ZN)&(~((X911_5_ZN&COUNT2)|(MI44_Q[2]&SET4)))&(~(HOLD1[1]&a6))));
      b5 <= X412_46_Z ? a5 : (~((COUNT1N|X8411_ZN)&(~((HOLD0[1]&b5)|(X625_5_ZN&COUNT0)))&(~(X623_5_ZN&MI44_Q[1]))));
      b4 <= X412_46_Z ? a4 : (~((COUNT1N|X8397_ZN)&(~((HOLD0[1]&b4)|(X751_5_ZN&COUNT0)))&(~(X623_5_ZN&MI44_Q[0]))));
      b3 <= X412_46_Z ? b4 : (~((COUNT1N|X1889_ZN)&(~((HOLD0[2]&b3)|(COUNT0&X3510_ZN)))&(~(SET2&MI44_Q[3]))));
      b6 <= X412_46_Z ? b7 : (~((COUNT1N|X420_ZN)&(~((HOLD0[1]&b6)|(X911_5_ZN&COUNT0)))&(~(X623_5_ZN&MI44_Q[2]))));
      a5 <= X412_46_Z ? a6 : (~((COUNT3N|X8411_ZN)&(~((X625_5_ZN&COUNT2)|(MI44_Q[1]&SET4)))&(~(HOLD1[1]&a5))));
      a7 <= X412_46_Z ? b8 : (~((COUNT1N|X8405_ZN)&(~((HOLD0[1]&a7)|(X59_5_ZN&COUNT0)))&(~(X623_5_ZN&MI44_Q[3]))));
      b7 <= X412_46_Z ? a7 : (~((COUNT3N|X8405_ZN)&(~((X59_5_ZN&COUNT2)|(MI44_Q[3]&SET4)))&(~(HOLD1[1]&b7))));
    end
  end

  // CLK_B, RST_AUX, SEL_B
  always @(posedge X1027_138_ZN or negedge X1676_Z) begin
    if (!X1676_Z) begin
      b8 <= 1'b0;
      a8 <= 1'b0;
    end else begin
      b8 <= X412_46_Z ? a8 : (~((COUNT1N|X8403_ZN)&(~((b8&HOLD0[0])|(COUNT0&X748_5_ZN)))&(~(SET1&MI44_Q[0]))));
      a8 <= X412_46_Z ? DT[1] : (~((COUNT3N|X8403_ZN)&(~((HOLD1[0]&a8)|(MI44_Q[0]&SET3)))&(~(X748_5_ZN&COUNT2))));
    end
  end

endmodule