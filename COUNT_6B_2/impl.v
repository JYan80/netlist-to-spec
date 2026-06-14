//-----------------------------------------------------------------------------
// Library Name: HCQ_2404150_SUB_DG_SCH
// Cell Name: COUNT_6B_2
// View Name: netlist
//-----------------------------------------------------------------------------
module COUNT_6B_2(CI, DT, MI2_Q, RST, X19_GS, X19_VS, X61_35_Z, X398_46_Z, 
    X595_149_Z);
    input CI;
    input [3:0] DT;
    output [5:0] MI2_Q;
    input RST;
    input X19_GS;
    input X19_VS;
    input X61_35_Z;
    input X398_46_Z;
    input X595_149_Z;

    wire [3:0] DT;
    wire [5:0] MI2_Q;

    SC_NAND2_70_40 X38_6 ( .A1(MI2_Q[0]), .A2(CI), .GS(X19_GS), .VS(X19_VS), .ZN(X38_6_ZN));
    SC_AOI12_E100_70 X247_39 ( .A(X1205_119_ZN), .B1(X38_6_ZN), .B2(X845_5_ZN), .GS(X19_GS),
         .VS(X19_VS), .ZN(X247_39_ZN));
    SC_MFC_140_80 X284_10 ( .CDN(RST), .CP(X61_35_Z), .D0(X247_39_ZN), .D1(DT[1]),
         .GS(X19_GS), .Q(MI2_Q[1]), .S(X398_46_Z), .VS(X19_VS));
    SC_MFC_140_80 X286_10 ( .CDN(RST), .CP(X61_35_Z), .D0(X498_101_Z), .D1(DT[3]),
         .GS(X19_GS), .Q(MI2_Q[2]), .S(X595_149_Z), .VS(X19_VS));
    SC_AOI12_E100_70 X289_39 ( .A(X1204_119_ZN), .B1(X3469_ZN), .B2(X836_64_ZN),
         .GS(X19_GS), .VS(X19_VS), .ZN(X289_39_ZN));
    SC_MFC_140_80 X295_10 ( .CDN(RST), .CP(X61_35_Z), .D0(X484_101_Z), .D1(MI2_Q[1]),
         .GS(X19_GS), .Q(MI2_Q[0]), .S(X398_46_Z), .VS(X19_VS));
    SC_MFC_140_80 X382_44 ( .CDN(RST), .CP(X61_35_Z), .D0(X477_67_ZN), .D1(DT[2]),
         .GS(X19_GS), .Q(MI2_Q[5]), .S(X398_46_Z), .VS(X19_VS));
    SC_MFC_140_80 X393_51 ( .CDN(RST), .CP(X61_35_Z), .D0(X803_Z), .D1(DT[0]), .GS(X19_GS),
         .Q(MI2_Q[4]), .S(X398_46_Z), .VS(X19_VS));
    SC_XNOR2_E120_E70 X477_67 ( .A1(MI2_Q[5]), .A2(X655_64_ZN), .GS(X19_GS), .VS(X19_VS),
         .ZN(X477_67_ZN));
    SC_OA12_140_80 X484_101 ( .A(X38_6_ZN), .B1(MI2_Q[0]), .B2(CI), .GS(X19_GS),
         .VS(X19_VS), .Z(X484_101_Z));
    SC_OA12_140_80 X498_101 ( .A(X836_64_ZN), .B1(X1205_119_ZN), .B2(MI2_Q[2]), .GS(X19_GS),
         .VS(X19_VS), .Z(X498_101_Z));
    SC_NAND2_70_40 X655_64 ( .A1(MI2_Q[4]), .A2(X1204_119_ZN), .GS(X19_GS), .VS(X19_VS),
         .ZN(X655_64_ZN));
    SC_OA12_140_80 X803 ( .A(X655_64_ZN), .B1(MI2_Q[4]), .B2(X1204_119_ZN), .GS(X19_GS),
         .VS(X19_VS), .Z(X803_Z));
    SC_NAND2_70_40 X836_64 ( .A1(X1205_119_ZN), .A2(MI2_Q[2]), .GS(X19_GS), .VS(X19_VS),
         .ZN(X836_64_ZN));
    SC_INV_140_60 X845_5 ( .A(MI2_Q[1]), .GS(X19_GS), .VS(X19_VS), .ZN(X845_5_ZN));
    SC_NOR2_100_30 X1204_119 ( .A1(X3469_ZN), .A2(X836_64_ZN), .GS(X19_GS), .VS(X19_VS),
         .ZN(X1204_119_ZN));
    SC_NOR2_100_30 X1205_119 ( .A1(X38_6_ZN), .A2(X845_5_ZN), .GS(X19_GS), .VS(X19_VS),
         .ZN(X1205_119_ZN));
    SC_INV_140_60 X3469 ( .A(MI2_Q[3]), .GS(X19_GS), .VS(X19_VS), .ZN(X3469_ZN));
    SC_MFC_140_80 X8368 ( .CDN(RST), .CP(X61_35_Z), .D0(X289_39_ZN), .D1(MI2_Q[4]),
         .GS(X19_GS), .Q(MI2_Q[3]), .S(X398_46_Z), .VS(X19_VS));
endmodule  // COUNT_6B_2
