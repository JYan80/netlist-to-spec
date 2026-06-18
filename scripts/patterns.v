// patterns.v -- yosys extract patterns for arithmetic and comparison operators
// Usage: extract -map scripts/patterns.v [design]

// ============================================================
// Adder building blocks
// ============================================================

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

// XOR3: Z = A^B^C  -- sum bit of full adder, also used in XNOR3 chain
(* extract_pattern *)
module xor3_cell (input A, B, C, output Z);
    assign Z = A ^ B ^ C;
endmodule

// XNOR3: ZN = ~(A^B^C)
(* extract_pattern *)
module xnor3_cell (input A, B, C, output ZN);
    assign ZN = ~(A ^ B ^ C);
endmodule

// ============================================================
// Incrementer building blocks
// ============================================================

// Conditional incrementer bit: SUM = A ^ CI, CO = A & CI
(* extract_pattern *)
module incr_bit (input A, CI, output SUM, CO);
    assign SUM = A ^ CI;
    assign CO  = A & CI;
endmodule

// ============================================================
// Comparator / carry-compare patterns
// The "second carry chain" in COUNT_12BX2 computes carries of
// (MI1_SUM + opA) and (MI1_SUM + opB) — these are carry-compare
// chains; recognise them as carry_cell patterns over SUM+operand pairs.
// ============================================================

// Carry-compare seed: CO = S & Q  (half-adder CO with S=MI1_SUM[k], Q=opX[k])
(* extract_pattern *)
module carry_cmp_seed (input S, Q, output CO);
    assign CO = S & Q;
endmodule

// Carry-compare propagate: CO = CARRY(S, Q, CI)
(* extract_pattern *)
module carry_cmp_prop (input S, Q, CI, output CO);
    assign CO = (S & Q) | (S & CI) | (Q & CI);
endmodule

// XOR carry-check: XOR of carry-in, operand bit, and SUM bit
// Zero means carry propagates cleanly through this bit position.
(* extract_pattern *)
module carry_xor_check (input CI, Q, S, output Z);
    assign Z = CI ^ Q ^ S;
endmodule

// ============================================================
// 2:1 MUX (common in D-input selection)
// ============================================================
(* extract_pattern *)
module mux2 (input S, D0, D1, output Y);
    assign Y = S ? D1 : D0;
endmodule
