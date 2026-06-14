// patterns.v -- yosys extract patterns for half-adder and full-adder/carry
// Usage: extract -map scripts/patterns.v [design]

// Half-adder: SUM = A^B, CO = A&B
(* extract_pattern *)
module half_adder (input A, B, output SUM, CO);
    assign SUM = A ^ B;
    assign CO  = A & B;
endmodule

// Full-adder: SUM = A^B^CI, CO = majority(A,B,CI)
(* extract_pattern *)
module full_adder (input A, B, CI, output SUM, CO);
    assign SUM = A ^ B ^ CI;
    assign CO  = (A & B) | (A & CI) | (B & CI);
endmodule

// Carry-only cell: CO = (A&B)|(A&CI)|(B&CI)  -- matches SC_CARRY_140_80
(* extract_pattern *)
module carry_cell (input A, B, CI, output CO);
    assign CO = (A & B) | (A & CI) | (B & CI);
endmodule

// XOR3: Z = A^B^C
(* extract_pattern *)
module xor3_cell (input A, B, C, output Z);
    assign Z = A ^ B ^ C;
endmodule

// XNOR3: ZN = ~(A^B^C)
(* extract_pattern *)
module xnor3_cell (input A, B, C, output ZN);
    assign ZN = ~(A ^ B ^ C);
endmodule
