// wrapper_template.v -- port-mapping wrapper for gate-level top module
// Instantiates the gate-level impl and re-exposes ports using spec port names.
// Used when gate port names differ from spec port names.
// For COUNT_12BX2, port names already match, so wrapper is a thin pass-through.

module COUNT_12BX2_wrapper (
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
    COUNT_12BX2 u_impl (
        .COUNT0       (COUNT0),
        .COUNT1N      (COUNT1N),
        .COUNT2       (COUNT2),
        .COUNT3N      (COUNT3N),
        .CTRL0        (CTRL0),
        .CTRL1        (CTRL1),
        .CTRL2        (CTRL2),
        .DT           (DT),
        .HOLD0        (HOLD0),
        .HOLD1        (HOLD1),
        .MI1_QT       (MI1_QT),
        .MI1_SUM      (MI1_SUM),
        .MI44_Q       (MI44_Q),
        .SET0N        (SET0N),
        .SET1         (SET1),
        .SET2         (SET2),
        .SET3         (SET3),
        .SET4         (SET4),
        .SET5         (SET5),
        .X3_323_Z     (X3_323_Z),
        .X19_GS       (X19_GS),
        .X19_VS       (X19_VS),
        .X412_46_Z    (X412_46_Z),
        .X1026_138_ZN (X1026_138_ZN),
        .X1027_138_ZN (X1027_138_ZN),
        .X1676_Z      (X1676_Z),
        .X8710_Z      (X8710_Z)
    );
endmodule
