---
name: quantum-circuit-optimizer
description: Optimizes a quantum circuit by running Qiskit, TKET and PyZX on it, verifying each result is unitarily equivalent to the input, and picking the best one for a chosen metric (two-qubit gates, T count, or depth). Use when the user asks to optimize, simplify, compress or reduce the cost of a quantum circuit, compare quantum compilers, cut CNOT or T count, or prepare a circuit for error mitigation (QEM), error correction (QEC) or fault-tolerant (FTQC) resource estimation.
license: MIT
compatibility: Python 3.10+ with qiskit 2.x, pytket 2.x and pyzx 0.10. Runs fully local; no cloud account or network needed.
metadata:
  version: "0.1"
  last-reviewed: "2026-11-01"
  tested-with: qiskit 2.6.1, pytket 2.18.5, pyzx 0.10.8
---

# Quantum circuit optimizer

Do not hand-optimize circuits. Run the established compilers, verify, and explain what each one won.

## 1. Pick the metric from the goal

| Goal | Metric | Why |
|---|---|---|
| Run on NISQ hardware, or apply QEM (ZNE, PEC) | `2q` | Two-qubit gates dominate the error; ZNE folding multiplies them |
| FTQC resource estimation, Clifford+T circuits | `t` | Each T gate needs a magic state; T count drives physical qubits and runtime |
| Short coherence time, or QEC syndrome circuits | `depth` | Idle time adds errors; syndrome rounds must be short |

If the user gives no goal, ask which one, or default to `2q` and say so.

## 2. Run the comparison

```bash
python scripts/optimize.py circuit.qasm --metric 2q --json result.json
python scripts/optimize.py --demo toffoli_chain --metric t   # try it without a circuit
```

The input is OpenQASM 2. For a Qiskit circuit in code, write it with `qiskit.qasm2.dumps(qc)` first.
The script removes final measurements, runs each tool, translates every output to the basis
`cx, rz, sx, x` so counts are comparable, and checks `Operator(input).equiv(Operator.from_circuit(output))`.

## 3. Verify before you trust a number

- Only accept rows with `equiv = yes`. A `NO` means the tool changed the circuit; report it, never use it.
- Above 12 qubits the unitary check is skipped. Then verify by sampling: run input and output on
  `AerSimulator` with the same seed and compare distributions (total variation distance < 0.02 at
  >= 20 000 shots), or compare `Statevector` on several random input states if the width allows.
- `Operator.from_circuit` is required for Qiskit output: level 3 removes final swaps and stores the
  permutation in the layout. Plain `Operator(out)` gives a false `NO`.
- For TKET, keep `FullPeepholeOptimise(allow_swaps=False)` unless the caller handles the permutation.

## 4. Report

Give the table, the winner for the chosen metric, and the trade-off. Example from the demos:

| Circuit | Best 2q | Best T | Trade-off |
|---|---|---|---|
| `qft5` | Qiskit L3: 26 -> 20 | PyZX: 30 -> 18 | PyZX cuts T by 40% but raises CX to 30 |
| `toffoli_chain` | Qiskit L3 / TKET: 25 -> 24 | PyZX: 28 -> 20 | Same pattern |

Then explain in plain words which rewrite each tool used. See [references/tools.md](references/tools.md).

## 5. Next steps by domain

- **QEM**: feed the `2q` winner to Mitiq. Fewer CX means less noise amplification per fold factor.
- **QEC**: optimize syndrome-extraction circuits for `depth`, then rebuild the Stim circuit and
  check the logical error rate did not get worse. Gate order in syndrome circuits affects hook
  errors, so a shorter circuit can still decode worse.
- **FTQC**: feed the `t` winner to the resource estimator (qsharp / qualtran) and report the change
  in physical qubits and runtime, not only in T count.

## Pitfalls

- The `t` column counts `rz` angles that are not multiples of pi/2. For exact Clifford+T circuits it
  equals the T count; for small-angle rotations (QFT) each one costs many T gates after synthesis.
- Do not install `pytket-qiskit` in an environment that also has `amazon-braket-sdk`: it pulls
  `ibm-cloud-sdk-core`, which needs `python-dateutil>=3` and breaks `botocore`. The script converts
  through QASM instead.
- PyZX reads `cx, rz, h` reliably; the script translates to that basis before calling it.
