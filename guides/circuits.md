# Circuits and algorithms (Qiskit 2.x)

Libraries: qiskit 2.6, qiskit_aer 0.18. Qiskit 2.x removed `execute`, `Aer` from `qiskit`, and
`qiskit.circuit.library.QFT` as a class you subclass; use `QFTGate`, `transpile` + `AerSimulator.run`.

Verification:
- <= 12 qubits: compare `Statevector(qc)` against a numpy reference computed independently
  (e.g. `np.fft.fft` for QFT, a brute-force classical answer for oracles).
- Sampling: `AerSimulator(seed_simulator=...)`, assert the expected outcome dominates with an
  explicit threshold.
- Always report resources after
  `transpile(qc, basis_gates=["cx", "rz", "sx", "x"], optimization_level=3)`.

Example: none needed; see the system prompt workflow.
