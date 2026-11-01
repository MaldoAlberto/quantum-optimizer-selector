# Fault-tolerant resource estimation (FTQC)

Libraries: qsharp 1.31 (Microsoft QDK resource estimator; accepts Qiskit circuits, local, free),
qualtran 0.7 (Google; bloqs, T/Toffoli counts, logical resource estimates).

Verification (mandatory):
- Report logical qubits, T or Toffoli count, code distance, physical qubits and runtime, with the
  assumptions used (error budget, qubit model, QEC scheme).
- Sanity asserts: physical qubits > logical qubits, code distance >= 3, counts grow with problem size
  (estimate at least two sizes).
- When both tools apply, cross-check logical counts between qsharp and qualtran and explain gaps.

Pitfalls:
- `qsharp.estimator.EstimatorParams` prints a DeprecationWarning pointing to `qdk.qre`; it still
  works in 1.31. Prefer it unless the user asks for the new API.

Verified example (examples/ftqc_qdk_estimate.py):
