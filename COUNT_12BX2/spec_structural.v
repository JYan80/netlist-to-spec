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
  wire X1661_CO;
  wire X1661_SUM;
  wire X1889_ZN;
  wire X1890_Z;
  wire X1891_CO;
  wire X1892_CO;
  wire X212_6_ZN;
  wire X214_21_ZN;
  wire X2492_CO;
  wire X24_263_CO;
  wire X2503_Z;
  wire X2504_Z;
  wire X2505_Z;
  wire X2506_Z;
  wire X25_263_CO;
  wire X26_263_CO;
  wire X27_263_CO;
  wire X28_263_CO;
  wire X29_85_CO;
  wire X29_85_SUM;
  wire X30_263_CO;
  wire X30_6_ZN;
  wire X31_263_CO;
  wire X32_263_CO;
  wire X3342_ZN;
  wire X3382_Z;
  wire X3383_CO;
  wire X3384_Z;
  wire X3385_ZN;
  wire X33_263_CO;
  wire X3484_ZN;
  wire X3510_ZN;
  wire X36_263_CO;
  wire X38_85_CO;
  wire X38_85_SUM;
  wire X409_73_ZN;
  wire X420_ZN;
  wire X421_73_ZN;
  wire X421_Z;
  wire X422_73_ZN;
  wire X431_73_ZN;
  wire X432_73_ZN;
  wire X452_73_ZN;
  wire X461_73_ZN;
  wire X467_73_ZN;
  wire X46_344_CO;
  wire X47_344_CO;
  wire X4_6_ZN;
  wire X568_189_ZN;
  wire X569_189_ZN;
  wire X593_189_ZN;
  wire X59_5_ZN;
  wire X605_189_ZN;
  wire X622_5_ZN;
  wire X623_5_ZN;
  wire X624_185_ZN;
  wire X625_5_ZN;
  wire X630_103_Z;
  wire X630_189_ZN;
  wire X632_207_ZN;
  wire X633_207_ZN;
  wire X634_207_ZN;
  wire X636_64_ZN;
  wire X649_290_ZN;
  wire X661_189_ZN;
  wire X684_189_ZN;
  wire X688_189_ZN;
  wire X703_103_Z;
  wire X72_330_CO;
  wire X72_330_SUM;
  wire X72_6_ZN;
  wire X744_64_ZN;
  wire X745_64_ZN;
  wire X746_5_ZN;
  wire X747_5_ZN;
  wire X748_5_ZN;
  wire X751_5_ZN;
  wire X8258_ZN;
  wire X8259_ZN;
  wire X8261_ZN;
  wire X8267_ZN;
  wire X8269_ZN;
  wire X8270_ZN;
  wire X8271_ZN;
  wire X8274_ZN;
  wire X8275_ZN;
  wire X8276_ZN;
  wire X8277_ZN;
  wire X8278_ZN;
  wire X8279_ZN;
  wire X8280_ZN;
  wire X8294_Z;
  wire X8330_CO;
  wire X8330_SUM;
  wire X8340_CO;
  wire X8340_SUM;
  wire X8341_CO;
  wire X8341_SUM;
  wire X8342_CO;
  wire X8342_SUM;
  wire X8343_CO;
  wire X8343_SUM;
  wire X8344_CO;
  wire X8344_SUM;
  wire X8346_CO;
  wire X8346_SUM;
  wire X8347_ZN;
  wire X8348_ZN;
  wire X8349_ZN;
  wire X8350_ZN;
  wire X8351_ZN;
  wire X8352_ZN;
  wire X8353_ZN;
  wire X8354_ZN;
  wire X8355_ZN;
  wire X8397_ZN;
  wire X8403_ZN;
  wire X8405_ZN;
  wire X8409_ZN;
  wire X8411_ZN;
  wire X8418_ZN;
  wire X8419_ZN;
  wire X8500_ZN;
  wire X8510_ZN;
  wire X8511_ZN;
  wire X8514_ZN;
  wire X8515_ZN;
  wire X8517_ZN;
  wire X8519_ZN;
  wire X8522_ZN;
  wire X8526_ZN;
  wire X8527_ZN;
  wire X8531_ZN;
  wire X8543_ZN;
  wire X8549_ZN;
  wire X8557_ZN;
  wire X8559_ZN;
  wire X8613_Z;
  wire X8614_Z;
  wire X8615_Z;
  wire X8616_Z;
  wire X8617_Z;
  wire X8618_Z;
  wire X8619_Z;
  wire X8620_Z;
  wire X8621_Z;
  wire X8622_Z;
  wire X8623_Z;
  wire X8624_Z;
  wire X8625_CO;
  wire X8626_CO;
  wire X8627_CO;
  wire X8628_CO;
  wire X8629_CO;
  wire X8630_CO;
  wire X8631_CO;
  wire X8632_CO;
  wire X8633_CO;
  wire X8634_CO;
  wire X8635_CO;
  wire X8636_CO;
  wire X8637_CO;
  wire X8638_CO;
  wire X8640_ZN;
  wire X8641_ZN;
  wire X8644_ZN;
  wire X8645_ZN;
  wire X8646_ZN;
  wire X8647_ZN;
  wire X8648_ZN;
  wire X8655_ZN;
  wire X911_5_ZN;

  // Sequential state registers
  reg X0_1625_Q;
  reg X0_1626_Q;
  reg X0_1715_Q;
  reg X1712_Q;
  reg X1713_Q;
  reg X1795_Q;
  reg X1796_Q;
  reg X1797_Q;
  reg X1798_Q;
  reg X1801_Q;
  reg X1802_Q;
  reg X1803_Q;
  reg X1804_Q;
  reg X1805_Q;
  reg X1806_Q;
  reg X1849_Q;
  reg X351_44_Q;
  reg X430_309_Q;
  reg X57_10_Q;
  reg X63_1886_Q;

  // MI1_QT output registers
  reg mi1_qt0_r, mi1_qt1_r;
  assign MI1_QT[0] = mi1_qt0_r;
  assign MI1_QT[1] = mi1_qt1_r;

  // Combinational logic
  assign X4_6_ZN = ~(SET2&MI44_Q[2]);
  assign MI1_SUM[9] = (X8330_SUM&CTRL0)|(X748_5_ZN&X746_5_ZN);
  assign X24_263_CO = (MI1_SUM[8]&X28_263_CO)|(MI1_SUM[8]&X63_1886_Q)|(X28_263_CO&X63_1886_Q);
  assign X25_263_CO = (X0_1625_Q&X72_330_CO)|(X0_1625_Q&X0_1626_Q)|(X72_330_CO&X0_1626_Q);
  assign X26_263_CO = (X57_10_Q&X3383_CO)|(X57_10_Q&X63_1886_Q)|(X3383_CO&X63_1886_Q);
  assign X27_263_CO = (MI1_SUM[2]&X630_103_Z)|(MI1_SUM[2]&X0_1625_Q)|(X630_103_Z&X0_1625_Q);
  assign X28_263_CO = (MI1_SUM[7]&X32_263_CO)|(MI1_SUM[7]&X1712_Q)|(X32_263_CO&X1712_Q);
  assign X29_85_CO  = X72_330_SUM & X3484_ZN;
  assign X29_85_SUM = X72_330_SUM ^ X3484_ZN;
  assign X30_6_ZN = ~(HOLD1[2]&X0_1626_Q);
  assign X30_263_CO = (X1796_Q&X8636_CO)|(X1796_Q&X0_1715_Q)|(X8636_CO&X0_1715_Q);
  assign X31_263_CO = (MI1_SUM[8]&X8625_CO)|(MI1_SUM[8]&X57_10_Q)|(X8625_CO&X57_10_Q);
  assign X32_263_CO = (MI1_SUM[6]&X2492_CO)|(MI1_SUM[6]&X430_309_Q)|(X2492_CO&X430_309_Q);
  assign X33_263_CO = (MI1_SUM[11]&X8633_CO)|(MI1_SUM[11]&X1806_Q)|(X8633_CO&X1806_Q);
  assign X36_263_CO = (MI1_SUM[6]&X8638_CO)|(MI1_SUM[6]&X1713_Q)|(X8638_CO&X1713_Q);
  assign X38_85_CO  = X8341_CO & X59_5_ZN;
  assign X38_85_SUM = X8341_CO ^ X59_5_ZN;
  assign X46_344_CO = (X1795_Q&X26_263_CO)|(X1795_Q&X1798_Q)|(X26_263_CO&X1798_Q);
  assign X47_344_CO = (MI1_SUM[10]&X1892_CO)|(MI1_SUM[10]&X1849_Q)|(X1892_CO&X1849_Q);
  assign X59_5_ZN = ~X8350_ZN;
  assign X72_6_ZN = ~(HOLD1[2]&X1802_Q);
  assign X72_330_CO  = X1805_Q & MI1_QT[0];
  assign X72_330_SUM = X1805_Q ^ MI1_QT[0];
  assign X154_21_ZN = ~((X8616_Z|CTRL1)&(X8619_Z|CTRL2));
  assign MI1_SUM[2] = (X8343_SUM&CTRL0)|(X747_5_ZN&X746_5_ZN);
  assign MI1_SUM[6] = (X1661_SUM&CTRL0)|(X625_5_ZN&X746_5_ZN);
  assign X212_6_ZN = ~(SET1&MI44_Q[1]);
  assign X214_21_ZN = ~((X8617_Z|CTRL1)&(X8618_Z|CTRL2));
  assign X409_73_ZN = ~((COUNT3N|X154_21_ZN)&X8279_ZN&X30_6_ZN);
  assign MI1_SUM[10] = (X8340_SUM&CTRL0)|(X1033_5_ZN&X746_5_ZN);
  assign X420_ZN = ~((X421_Z|CTRL1)&(X3382_Z|CTRL2));
  assign X421_Z = X8625_CO^X57_10_Q^MI1_SUM[8];
  assign X421_73_ZN = ~((COUNT1N|X214_21_ZN)&X605_189_ZN&X636_64_ZN);
  assign X422_73_ZN = ~((COUNT1N|X420_ZN)&X8275_ZN&X8526_ZN);
  assign X431_73_ZN = ~((COUNT3N|X214_21_ZN)&X630_189_ZN&X744_64_ZN);
  assign X432_73_ZN = ~((COUNT1N|X8397_ZN)&X8271_ZN&X8500_ZN);
  assign X452_73_ZN = ~((COUNT3N|X1889_ZN)&X8280_ZN&X72_6_ZN);
  assign X461_73_ZN = ~((COUNT3N|X8403_ZN)&X8276_ZN&X8519_ZN);
  assign X467_73_ZN = ~((COUNT1N|X154_21_ZN)&X8259_ZN&X745_64_ZN);
  assign X568_189_ZN = ~((HOLD0[1]&X57_10_Q)|(X59_5_ZN&COUNT0));
  assign X569_189_ZN = ~((X911_5_ZN&COUNT2)|(MI44_Q[2]&SET4));
  assign X593_189_ZN = ~((X625_5_ZN&COUNT2)|(MI44_Q[1]&SET4));
  assign X605_189_ZN = ~((HOLD0[2]&MI1_QT[0])|(COUNT0&X3484_ZN));
  assign X622_5_ZN = ~X8352_ZN;
  assign X623_5_ZN = ~SET0N;
  assign X624_185_ZN = ~((COUNT1N|X1889_ZN)&X661_189_ZN&X8559_ZN);
  assign X625_5_ZN = ~X8347_ZN;
  assign X630_103_Z = MI1_SUM[1]&MI1_QT[0];
  assign X630_189_ZN = ~((SET5&MI44_Q[0])|(COUNT2&X3484_ZN));
  assign X632_207_ZN = ~((COUNT3N|X8411_ZN)&X593_189_ZN&X8549_ZN);
  assign X633_207_ZN = ~((COUNT3N|X8397_ZN)&X8261_ZN&X8522_ZN);
  assign X634_207_ZN = ~((COUNT1N|X8418_ZN)&X8258_ZN&X4_6_ZN);
  assign X636_64_ZN = ~(SET2&MI44_Q[0]);
  assign X649_290_ZN = ~((COUNT3N|X420_ZN)&X569_189_ZN&X8557_ZN);
  assign X661_189_ZN = ~((HOLD0[2]&X1797_Q)|(COUNT0&X3510_ZN));
  assign X684_189_ZN = ~((X1795_Q&HOLD0[0])|(COUNT0&X748_5_ZN));
  assign X688_189_ZN = ~((X1849_Q&HOLD0[0])|(COUNT0&X1033_5_ZN));
  assign X703_103_Z = MI1_SUM[1]&X1805_Q;
  assign X744_64_ZN = ~(HOLD1[2]&X1805_Q);
  assign X745_64_ZN = ~(SET2&MI44_Q[1]);
  assign X746_5_ZN = ~CTRL0;
  assign X747_5_ZN = ~X8351_ZN;
  assign X748_5_ZN = ~X8353_ZN;
  assign X751_5_ZN = ~X8349_ZN;
  assign MI1_SUM[8] = (X38_85_SUM&CTRL0)|(X59_5_ZN&X746_5_ZN);
  assign MI1_SUM[1] = (X29_85_SUM&CTRL0)|(X3484_ZN&X746_5_ZN);
  assign X911_5_ZN = ~X3342_ZN;
  assign X1033_5_ZN = ~X8354_ZN;
  assign X1661_CO  = X8346_CO & X625_5_ZN;
  assign X1661_SUM = X8346_CO ^ X625_5_ZN;
  assign X1889_ZN = ~((X1890_Z|CTRL1)&(X8621_Z|CTRL2));
  assign X1890_Z = X1891_CO^X1796_Q^MI1_SUM[5];
  assign X1891_CO = (MI1_SUM[4]&X8637_CO)|(MI1_SUM[4]&X1797_Q)|(X8637_CO&X1797_Q);
  assign X1892_CO = (MI1_SUM[9]&X31_263_CO)|(MI1_SUM[9]&X1795_Q)|(X31_263_CO&X1795_Q);
  assign X2492_CO = (MI1_SUM[5]&X8634_CO)|(MI1_SUM[5]&X0_1715_Q)|(X8634_CO&X0_1715_Q);
  assign X2503_Z = X2492_CO^X430_309_Q^MI1_SUM[6];
  assign X2504_Z = X32_263_CO^X1712_Q^MI1_SUM[7];
  assign X2505_Z = X36_263_CO^X351_44_Q^MI1_SUM[7];
  assign X2506_Z = X8638_CO^X1713_Q^MI1_SUM[6];
  assign X3342_ZN = ~(X3383_CO^X63_1886_Q^X57_10_Q);
  assign X3382_Z = X28_263_CO^X63_1886_Q^MI1_SUM[8];
  assign X3383_CO = (X351_44_Q&X8627_CO)|(X351_44_Q&X1712_Q)|(X8627_CO&X1712_Q);
  assign X3384_Z = X24_263_CO^X1798_Q^MI1_SUM[9];
  assign X3385_ZN = ~((COUNT3N|X8405_ZN)&X8277_ZN&X8511_ZN);
  assign X3484_ZN = ~X8348_ZN;
  assign X3510_ZN = ~X8355_ZN;
  assign X8258_ZN = ~((HOLD0[2]&X1804_Q)|(COUNT0&X622_5_ZN));
  assign X8259_ZN = ~((HOLD0[2]&X0_1625_Q)|(COUNT0&X747_5_ZN));
  assign X8261_ZN = ~((X751_5_ZN&COUNT2)|(MI44_Q[0]&SET4));
  assign X8267_ZN = ~((HOLD1[0]&X1806_Q)|(MI44_Q[2]&SET3));
  assign X8269_ZN = ~((X1801_Q&HOLD0[0])|(COUNT0&X8631_CO));
  assign X8270_ZN = ~((HOLD0[1]&X1713_Q)|(X625_5_ZN&COUNT0));
  assign X8271_ZN = ~((HOLD0[1]&X1796_Q)|(X751_5_ZN&COUNT0));
  assign X8274_ZN = ~((HOLD1[0]&MI1_QT[1])|(MI44_Q[1]&SET3));
  assign X8275_ZN = ~((HOLD0[1]&X351_44_Q)|(X911_5_ZN&COUNT0));
  assign X8276_ZN = ~((HOLD1[0]&X1798_Q)|(MI44_Q[0]&SET3));
  assign X8277_ZN = ~((X59_5_ZN&COUNT2)|(MI44_Q[3]&SET4));
  assign X8278_ZN = ~((MI44_Q[2]&SET5)|(X622_5_ZN&COUNT2));
  assign X8279_ZN = ~((MI44_Q[1]&SET5)|(X747_5_ZN&COUNT2));
  assign X8280_ZN = ~((MI44_Q[3]&SET5)|(X3510_ZN&COUNT2));
  assign X8294_Z = X8631_CO^X8340_CO;
  assign X8330_CO  = X38_85_CO  & X748_5_ZN;
  assign X8330_SUM = X38_85_CO  ^ X748_5_ZN;
  assign X8340_CO  = X8330_CO   & X1033_5_ZN;
  assign X8340_SUM = X8330_CO   ^ X1033_5_ZN;
  assign X8341_CO  = X1661_CO   & X911_5_ZN;
  assign X8341_SUM = X1661_CO   ^ X911_5_ZN;
  assign X8343_CO  = X29_85_CO  & X747_5_ZN;
  assign X8343_SUM = X29_85_CO  ^ X747_5_ZN;
  assign X8342_CO  = X8343_CO   & X622_5_ZN;
  assign X8342_SUM = X8343_CO   ^ X622_5_ZN;
  assign X8344_CO  = X8342_CO   & X3510_ZN;
  assign X8344_SUM = X8342_CO   ^ X3510_ZN;
  assign X8346_CO  = X8344_CO   & X751_5_ZN;
  assign X8346_SUM = X8344_CO   ^ X751_5_ZN;
  assign X8347_ZN = ~(X8627_CO^X1712_Q^X351_44_Q);
  assign X8348_ZN = ~(X72_330_CO^X0_1626_Q^X0_1625_Q);
  assign X8349_ZN = ~(X30_263_CO^X430_309_Q^X1713_Q);
  assign X8350_ZN = ~(X26_263_CO^X1798_Q^X1795_Q);
  assign X8351_ZN = ~(X25_263_CO^X1803_Q^X1804_Q);
  assign X8352_ZN = ~(X8629_CO^X1802_Q^X1797_Q);
  assign X8353_ZN = ~(X46_344_CO^MI1_QT[1]^X1849_Q);
  assign X8354_ZN = ~(X8632_CO^X1806_Q^X1801_Q);
  assign X8355_ZN = ~(X8636_CO^X0_1715_Q^X1796_Q);
  assign X8397_ZN = ~((X2506_Z|CTRL1)&(X2503_Z|CTRL2));
  assign X8403_ZN = ~((X8613_Z|CTRL1)&(X8615_Z|CTRL2));
  assign X8405_ZN = ~((X8614_Z|CTRL1)&(X3384_Z|CTRL2));
  assign X8409_ZN = ~((X8630_CO|CTRL1)&(X33_263_CO|CTRL2));
  assign X8411_ZN = ~((X2505_Z|CTRL1)&(X2504_Z|CTRL2));
  assign X8418_ZN = ~((X8620_Z|CTRL1)&(X8623_Z|CTRL2));
  assign X8419_ZN = ~((X8622_Z|CTRL1)&(X8624_Z|CTRL2));
  assign X8500_ZN = ~(X623_5_ZN&MI44_Q[0]);
  assign X8510_ZN = ~(HOLD1[2]&X1803_Q);
  assign X8511_ZN = ~(HOLD1[1]&X63_1886_Q);
  assign X8514_ZN = ~(X8631_CO&COUNT2);
  assign X8515_ZN = ~(SET1&MI44_Q[2]);
  assign X8517_ZN = ~(X623_5_ZN&MI44_Q[3]);
  assign X8519_ZN = ~(X748_5_ZN&COUNT2);
  assign X8522_ZN = ~(HOLD1[1]&X0_1715_Q);
  assign X8526_ZN = ~(X623_5_ZN&MI44_Q[2]);
  assign X8527_ZN = ~(X623_5_ZN&MI44_Q[1]);
  assign X8531_ZN = ~(SET1&MI44_Q[0]);
  assign X8543_ZN = ~(X1033_5_ZN&COUNT2);
  assign X8549_ZN = ~(HOLD1[1]&X430_309_Q);
  assign X8557_ZN = ~(HOLD1[1]&X1712_Q);
  assign X8559_ZN = ~(SET2&MI44_Q[3]);
  assign MI1_SUM[5] = (X8346_SUM&CTRL0)|(X751_5_ZN&X746_5_ZN);
  assign MI1_SUM[3] = (X8342_SUM&CTRL0)|(X622_5_ZN&X746_5_ZN);
  assign MI1_SUM[4] = (X8344_SUM&CTRL0)|(X3510_ZN&X746_5_ZN);
  assign MI1_SUM[7] = (X8341_SUM&CTRL0)|(X911_5_ZN&X746_5_ZN);
  assign MI1_SUM[11] = (X8294_Z&CTRL0)|(X8631_CO&X746_5_ZN);
  assign X8613_Z = X1892_CO^X1849_Q^MI1_SUM[10];
  assign X8614_Z = X31_263_CO^X1795_Q^MI1_SUM[9];
  assign X8615_Z = X8635_CO^MI1_QT[1]^MI1_SUM[10];
  assign X8616_Z = X27_263_CO^X1804_Q^MI1_SUM[3];
  assign X8617_Z = X630_103_Z^X0_1625_Q^MI1_SUM[2];
  assign X8618_Z = X703_103_Z^X0_1626_Q^MI1_SUM[2];
  assign X8619_Z = X8626_CO^X1803_Q^MI1_SUM[3];
  assign X8620_Z = X8637_CO^X1797_Q^MI1_SUM[4];
  assign X8621_Z = X8634_CO^X0_1715_Q^MI1_SUM[5];
  assign X8622_Z = X47_344_CO^X1801_Q^MI1_SUM[11];
  assign X8623_Z = X8628_CO^X1802_Q^MI1_SUM[4];
  assign X8624_Z = X8633_CO^X1806_Q^MI1_SUM[11];
  assign X8625_CO = (MI1_SUM[7]&X36_263_CO)|(MI1_SUM[7]&X351_44_Q)|(X36_263_CO&X351_44_Q);
  assign X8626_CO = (MI1_SUM[2]&X703_103_Z)|(MI1_SUM[2]&X0_1626_Q)|(X703_103_Z&X0_1626_Q);
  assign X8627_CO = (X1713_Q&X30_263_CO)|(X1713_Q&X430_309_Q)|(X30_263_CO&X430_309_Q);
  assign X8628_CO = (MI1_SUM[3]&X8626_CO)|(MI1_SUM[3]&X1803_Q)|(X8626_CO&X1803_Q);
  assign X8629_CO = (X1804_Q&X25_263_CO)|(X1804_Q&X1803_Q)|(X25_263_CO&X1803_Q);
  assign X8630_CO = (MI1_SUM[11]&X47_344_CO)|(MI1_SUM[11]&X1801_Q)|(X47_344_CO&X1801_Q);
  assign X8631_CO = (X1801_Q&X8632_CO)|(X1801_Q&X1806_Q)|(X8632_CO&X1806_Q);
  assign X8632_CO = (X1849_Q&X46_344_CO)|(X1849_Q&MI1_QT[1])|(X46_344_CO&MI1_QT[1]);
  assign X8633_CO = (MI1_SUM[10]&X8635_CO)|(MI1_SUM[10]&MI1_QT[1])|(X8635_CO&MI1_QT[1]);
  assign X8634_CO = (MI1_SUM[4]&X8628_CO)|(MI1_SUM[4]&X1802_Q)|(X8628_CO&X1802_Q);
  assign X8635_CO = (MI1_SUM[9]&X24_263_CO)|(MI1_SUM[9]&X1798_Q)|(X24_263_CO&X1798_Q);
  assign X8636_CO = (X1797_Q&X8629_CO)|(X1797_Q&X1802_Q)|(X8629_CO&X1802_Q);
  assign X8637_CO = (MI1_SUM[3]&X27_263_CO)|(MI1_SUM[3]&X1804_Q)|(X27_263_CO&X1804_Q);
  assign X8638_CO = (MI1_SUM[5]&X1891_CO)|(MI1_SUM[5]&X1796_Q)|(X1891_CO&X1796_Q);
  assign X8640_ZN = ~((COUNT1N|X8419_ZN)&X688_189_ZN&X212_6_ZN);
  assign X8641_ZN = ~((COUNT1N|X8405_ZN)&X568_189_ZN&X8517_ZN);
  assign X8644_ZN = ~((COUNT1N|X8403_ZN)&X684_189_ZN&X8531_ZN);
  assign X8645_ZN = ~((COUNT3N|X8419_ZN)&X8274_ZN&X8543_ZN);
  assign X8646_ZN = ~((COUNT1N|X8411_ZN)&X8270_ZN&X8527_ZN);
  assign X8647_ZN = ~((COUNT1N|X8409_ZN)&X8269_ZN&X8515_ZN);
  assign X8648_ZN = ~((COUNT3N|X8409_ZN)&X8267_ZN&X8514_ZN);
  assign X8655_ZN = ~((COUNT3N|X8418_ZN)&X8278_ZN&X8510_ZN);

  // CLK_A, RST_MAIN, SEL_A
  always @(posedge X1026_138_ZN or negedge X3_323_Z) begin
    if (!X3_323_Z) begin
      X0_1625_Q <= 1'b0;
      X0_1626_Q <= 1'b0;
      mi1_qt0_r <= 1'b0;
      X1805_Q <= 1'b0;
      X1806_Q <= 1'b0;
    end else begin
      X0_1625_Q <= X8710_Z ? X0_1626_Q : X467_73_ZN;
      X0_1626_Q <= X8710_Z ? X1804_Q : X409_73_ZN;
      mi1_qt0_r <= X8710_Z ? X0_1625_Q : X421_73_ZN;
      X1805_Q <= X8710_Z ? X1806_Q : X431_73_ZN;
      X1806_Q <= X8710_Z ? DT[0] : X8648_ZN;
    end
  end

  // CLK_B, RST_MAIN, SEL_A
  always @(posedge X1027_138_ZN or negedge X3_323_Z) begin
    if (!X3_323_Z) begin
      X1801_Q <= 1'b0;
      X1802_Q <= 1'b0;
      X1803_Q <= 1'b0;
      X1804_Q <= 1'b0;
      X1849_Q <= 1'b0;
    end else begin
      X1801_Q <= X8710_Z ? X1805_Q : X8647_ZN;
      X1802_Q <= X8710_Z ? X1797_Q : X452_73_ZN;
      X1803_Q <= X8710_Z ? X1802_Q : X8655_ZN;
      X1804_Q <= X8710_Z ? X1803_Q : X634_207_ZN;
      X1849_Q <= X8710_Z ? X1801_Q : X8640_ZN;
    end
  end

  // CLK_B, RST_AUX, SEL_A
  always @(posedge X1027_138_ZN or negedge X1676_Z) begin
    if (!X1676_Z) begin
      mi1_qt1_r <= 1'b0;
    end else begin
      mi1_qt1_r <= X8710_Z ? X1849_Q : X8645_ZN;
    end
  end

  // CLK_B, RST_MAIN, SEL_B
  always @(posedge X1027_138_ZN or negedge X3_323_Z) begin
    if (!X3_323_Z) begin
      X0_1715_Q <= 1'b0;
      X1712_Q <= 1'b0;
      X1713_Q <= 1'b0;
      X1796_Q <= 1'b0;
      X1797_Q <= 1'b0;
      X351_44_Q <= 1'b0;
      X430_309_Q <= 1'b0;
      X57_10_Q <= 1'b0;
      X63_1886_Q <= 1'b0;
    end else begin
      X0_1715_Q <= X412_46_Z ? X1713_Q : X633_207_ZN;
      X1712_Q <= X412_46_Z ? X351_44_Q : X649_290_ZN;
      X1713_Q <= X412_46_Z ? X430_309_Q : X8646_ZN;
      X1796_Q <= X412_46_Z ? X0_1715_Q : X432_73_ZN;
      X1797_Q <= X412_46_Z ? X1796_Q : X624_185_ZN;
      X351_44_Q <= X412_46_Z ? X63_1886_Q : X422_73_ZN;
      X430_309_Q <= X412_46_Z ? X1712_Q : X632_207_ZN;
      X57_10_Q <= X412_46_Z ? X1795_Q : X8641_ZN;
      X63_1886_Q <= X412_46_Z ? X57_10_Q : X3385_ZN;
    end
  end

  // CLK_B, RST_AUX, SEL_B
  always @(posedge X1027_138_ZN or negedge X1676_Z) begin
    if (!X1676_Z) begin
      X1795_Q <= 1'b0;
      X1798_Q <= 1'b0;
    end else begin
      X1795_Q <= X412_46_Z ? X1798_Q : X8644_ZN;
      X1798_Q <= X412_46_Z ? DT[1] : X461_73_ZN;
    end
  end

endmodule