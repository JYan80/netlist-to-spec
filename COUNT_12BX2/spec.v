// COUNT_12BX2_spec.v  Behavioral RTL spec, formally equivalent to impl.v
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

  // Clock / reset / select aliases
  wire CLK_A    = X1026_138_ZN;
  wire CLK_B    = X1027_138_ZN;
  wire RST_MAIN = X3_323_Z;
  wire RST_AUX  = X1676_Z;
  wire SEL_A    = X8710_Z;
  wire SEL_B    = X412_46_Z;

  // State registers (11-bit A accumulator + 11-bit B accumulator)
  reg a0; reg a1; reg a2; reg a3; reg a4; reg a5;
  reg a6; reg a7; reg a8; reg a9; reg a10;
  reg b0; reg b1; reg b2; reg b3; reg b4; reg b5;
  reg b6; reg b7; reg b8; reg b9; reg b10;

  assign MI1_QT[0] = a0;
  assign MI1_QT[1] = b9;

  // Word-level arithmetic
  wire [10:0] opA         = {a10, a9, a8, a7, a6, a5, a4, a3, a2, a1, a0};
  wire [10:0] opB         = {b10, b9, b8, b7, b6, b5, b4, b3, b2, b1, b0};
  wire [11:0] sum_ext     = {1'b0, opA} + {1'b0, opB} + {11'b0, CTRL0};
  wire [11:0] raw_sum_ext = {1'b0, opA} + {1'b0, opB};
  assign MI1_SUM = sum_ext[11:1];

  // Carry-compare chains (opA+opB running carry vs MI1_SUM at each bit)
  wire X630_103_Z = MI1_SUM[1] & MI1_QT[0];
  wire X703_103_Z = MI1_SUM[1] & b0;
  wire X27_263_CO  = (MI1_SUM[2] & X630_103_Z) | (MI1_SUM[2] & a1)      | (X630_103_Z & a1);
  wire X8626_CO    = (MI1_SUM[2] & X703_103_Z) | (MI1_SUM[2] & b1)      | (X703_103_Z & b1);
  wire X8637_CO    = (MI1_SUM[3] & X27_263_CO) | (MI1_SUM[3] & b2)      | (X27_263_CO & b2);
  wire X8628_CO    = (MI1_SUM[3] & X8626_CO)   | (MI1_SUM[3] & a2)      | (X8626_CO & a2);
  wire X1891_CO    = (MI1_SUM[4] & X8637_CO)   | (MI1_SUM[4] & b3)      | (X8637_CO & b3);
  wire X8634_CO    = (MI1_SUM[4] & X8628_CO)   | (MI1_SUM[4] & a3)      | (X8628_CO & a3);
  wire X8638_CO    = (MI1_SUM[5] & X1891_CO)   | (MI1_SUM[5] & b4)      | (X1891_CO & b4);
  wire X2492_CO    = (MI1_SUM[5] & X8634_CO)   | (MI1_SUM[5] & a4)      | (X8634_CO & a4);
  wire X36_263_CO  = (MI1_SUM[6] & X8638_CO)   | (MI1_SUM[6] & b5)      | (X8638_CO & b5);
  wire X32_263_CO  = (MI1_SUM[6] & X2492_CO)   | (MI1_SUM[6] & a5)      | (X2492_CO & a5);
  wire X8625_CO    = (MI1_SUM[7] & X36_263_CO) | (MI1_SUM[7] & b6)      | (X36_263_CO & b6);
  wire X28_263_CO  = (MI1_SUM[7] & X32_263_CO) | (MI1_SUM[7] & a6)      | (X32_263_CO & a6);
  wire X31_263_CO  = (MI1_SUM[8] & X8625_CO)   | (MI1_SUM[8] & a7)      | (X8625_CO & a7);
  wire X24_263_CO  = (MI1_SUM[8] & X28_263_CO) | (MI1_SUM[8] & b7)      | (X28_263_CO & b7);
  wire X1892_CO    = (MI1_SUM[9] & X31_263_CO) | (MI1_SUM[9] & b8)      | (X31_263_CO & b8);
  wire X8635_CO    = (MI1_SUM[9] & X24_263_CO) | (MI1_SUM[9] & a8)      | (X24_263_CO & a8);
  wire X47_344_CO  = (MI1_SUM[10] & X1892_CO)  | (MI1_SUM[10] & a9)     | (X1892_CO & a9);
  wire X8633_CO    = (MI1_SUM[10] & X8635_CO)  | (MI1_SUM[10] & MI1_QT[1]) | (X8635_CO & MI1_QT[1]);

  // neq_N: 1 when carry-compare at SUM[N] shows mismatch (suppresses update)
  wire neq_2   = ~(((X630_103_Z ^ a1  ^ MI1_SUM[2]) | CTRL1) & ((X703_103_Z ^ b1        ^ MI1_SUM[2])  | CTRL2));
  wire neq_3   = ~(((X27_263_CO  ^ b2  ^ MI1_SUM[3]) | CTRL1) & ((X8626_CO   ^ a2        ^ MI1_SUM[3])  | CTRL2));
  wire neq_4   = ~(((X8637_CO   ^ b3  ^ MI1_SUM[4]) | CTRL1) & ((X8628_CO   ^ a3        ^ MI1_SUM[4])  | CTRL2));
  wire neq_5   = ~(((X1891_CO   ^ b4  ^ MI1_SUM[5]) | CTRL1) & ((X8634_CO   ^ a4        ^ MI1_SUM[5])  | CTRL2));
  wire neq_6   = ~(((X8638_CO   ^ b5  ^ MI1_SUM[6]) | CTRL1) & ((X2492_CO   ^ a5        ^ MI1_SUM[6])  | CTRL2));
  wire neq_7   = ~(((X36_263_CO ^ b6  ^ MI1_SUM[7]) | CTRL1) & ((X32_263_CO ^ a6        ^ MI1_SUM[7])  | CTRL2));
  wire neq_8   = ~(((X8625_CO   ^ a7  ^ MI1_SUM[8]) | CTRL1) & ((X28_263_CO ^ b7        ^ MI1_SUM[8])  | CTRL2));
  wire neq_9   = ~(((X31_263_CO ^ b8  ^ MI1_SUM[9]) | CTRL1) & ((X24_263_CO ^ a8        ^ MI1_SUM[9])  | CTRL2));
  wire neq_10  = ~(((X1892_CO   ^ a9  ^ MI1_SUM[10])| CTRL1) & ((X8635_CO   ^ MI1_QT[1] ^ MI1_SUM[10]) | CTRL2));
  wire neq_11  = ~(((X47_344_CO ^ a10 ^ MI1_SUM[11])| CTRL1) & ((X8633_CO   ^ b10       ^ MI1_SUM[11]) | CTRL2));
  wire neq_c11 = ~((((MI1_SUM[11]&X47_344_CO)|(MI1_SUM[11]&a10)|(X47_344_CO&a10))|CTRL1) &
                   (((MI1_SUM[11]&X8633_CO)  |(MI1_SUM[11]&b10)|(X8633_CO&b10))  |CTRL2));

  // G1: CLK_A, RST_MAIN, SEL_A
  always @(posedge CLK_A or negedge RST_MAIN) begin
    if (!RST_MAIN) begin
      a0 <= 1'b0; b0  <= 1'b0;
      a1 <= 1'b0; b1  <= 1'b0;
      b10 <= 1'b0;
    end else begin
      a0  <= SEL_A ? a1    : (~((COUNT1N|neq_2)  &(~((HOLD0[2]&MI1_QT[0])|(COUNT0&raw_sum_ext[1])))&(~(SET2&MI44_Q[0]))));
      b0  <= SEL_A ? b10   : (~((COUNT3N|neq_2)  &(~((SET5&MI44_Q[0])|(COUNT2&raw_sum_ext[1])))    &(~(HOLD1[2]&b0))));
      a1  <= SEL_A ? b1    : (~((COUNT1N|neq_3)  &(~((HOLD0[2]&a1)|(COUNT0&raw_sum_ext[2])))       &(~(SET2&MI44_Q[1]))));
      b1  <= SEL_A ? b2    : (~((COUNT3N|neq_3)  &(~((MI44_Q[1]&SET5)|(raw_sum_ext[2]&COUNT2)))    &(~(HOLD1[2]&b1))));
      b10 <= SEL_A ? DT[0] : (~((COUNT3N|neq_c11)&(~((HOLD1[0]&b10)|(MI44_Q[2]&SET3)))            &(~(raw_sum_ext[11]&COUNT2))));
    end
  end

  // G2: CLK_B, RST_MAIN, SEL_A
  always @(posedge CLK_B or negedge RST_MAIN) begin
    if (!RST_MAIN) begin
      a2 <= 1'b0; b2  <= 1'b0;
      a3 <= 1'b0; a9  <= 1'b0; a10 <= 1'b0;
    end else begin
      a2  <= SEL_A ? a3    : (~((COUNT3N|neq_4)  &(~((MI44_Q[2]&SET5)|(raw_sum_ext[3]&COUNT2)))    &(~(HOLD1[2]&a2))));
      b2  <= SEL_A ? a2    : (~((COUNT1N|neq_4)  &(~((HOLD0[2]&b2)|(COUNT0&raw_sum_ext[3])))       &(~(SET2&MI44_Q[2]))));
      a3  <= SEL_A ? b3    : (~((COUNT3N|neq_5)  &(~((MI44_Q[3]&SET5)|(raw_sum_ext[4]&COUNT2)))    &(~(HOLD1[2]&a3))));
      a9  <= SEL_A ? a10   : (~((COUNT1N|neq_11) &(~((a9&HOLD0[0])|(COUNT0&raw_sum_ext[10])))      &(~(SET1&MI44_Q[1]))));
      a10 <= SEL_A ? b0    : (~((COUNT1N|neq_c11)&(~((a10&HOLD0[0])|(COUNT0&raw_sum_ext[11])))     &(~(SET1&MI44_Q[2]))));
    end
  end

  // G3: CLK_B, RST_AUX, SEL_A
  always @(posedge CLK_B or negedge RST_AUX) begin
    if (!RST_AUX) begin
      b9 <= 1'b0;
    end else begin
      b9 <= SEL_A ? a9 : (~((COUNT3N|neq_11)&(~((HOLD1[0]&MI1_QT[1])|(MI44_Q[1]&SET3)))&(~(raw_sum_ext[10]&COUNT2))));
    end
  end

  // G4: CLK_B, RST_MAIN, SEL_B
  always @(posedge CLK_B or negedge RST_MAIN) begin
    if (!RST_MAIN) begin
      b3 <= 1'b0; b4 <= 1'b0; a4 <= 1'b0;
      b5 <= 1'b0; a5 <= 1'b0;
      b6 <= 1'b0; a6 <= 1'b0;
      a7 <= 1'b0; b7 <= 1'b0;
    end else begin
      b3  <= SEL_B ? b4   : (~((COUNT1N|neq_5) &(~((HOLD0[2]&b3)|(COUNT0&raw_sum_ext[4])))      &(~(SET2&MI44_Q[3]))));
      b4  <= SEL_B ? a4   : (~((COUNT1N|neq_6) &(~((HOLD0[1]&b4)|(raw_sum_ext[5]&COUNT0)))      &(~(~SET0N&MI44_Q[0]))));
      a4  <= SEL_B ? b5   : (~((COUNT3N|neq_6) &(~((raw_sum_ext[5]&COUNT2)|(MI44_Q[0]&SET4)))   &(~(HOLD1[1]&a4))));
      b5  <= SEL_B ? a5   : (~((COUNT1N|neq_7) &(~((HOLD0[1]&b5)|(raw_sum_ext[6]&COUNT0)))      &(~(~SET0N&MI44_Q[1]))));
      a5  <= SEL_B ? a6   : (~((COUNT3N|neq_7) &(~((raw_sum_ext[6]&COUNT2)|(MI44_Q[1]&SET4)))   &(~(HOLD1[1]&a5))));
      b6  <= SEL_B ? b7   : (~((COUNT1N|neq_8) &(~((HOLD0[1]&b6)|(raw_sum_ext[7]&COUNT0)))      &(~(~SET0N&MI44_Q[2]))));
      a6  <= SEL_B ? b6   : (~((COUNT3N|neq_8) &(~((raw_sum_ext[7]&COUNT2)|(MI44_Q[2]&SET4)))   &(~(HOLD1[1]&a6))));
      a7  <= SEL_B ? b8   : (~((COUNT1N|neq_9) &(~((HOLD0[1]&a7)|(raw_sum_ext[8]&COUNT0)))      &(~(~SET0N&MI44_Q[3]))));
      b7  <= SEL_B ? a7   : (~((COUNT3N|neq_9) &(~((raw_sum_ext[8]&COUNT2)|(MI44_Q[3]&SET4)))   &(~(HOLD1[1]&b7))));
    end
  end

  // G5: CLK_B, RST_AUX, SEL_B
  always @(posedge CLK_B or negedge RST_AUX) begin
    if (!RST_AUX) begin
      b8 <= 1'b0; a8 <= 1'b0;
    end else begin
      b8 <= SEL_B ? a8    : (~((COUNT1N|neq_10)&(~((b8&HOLD0[0])|(COUNT0&raw_sum_ext[9])))      &(~(SET1&MI44_Q[0]))));
      a8 <= SEL_B ? DT[1] : (~((COUNT3N|neq_10)&(~((HOLD1[0]&a8)|(MI44_Q[0]&SET3)))            &(~(raw_sum_ext[9]&COUNT2))));
    end
  end

endmodule
