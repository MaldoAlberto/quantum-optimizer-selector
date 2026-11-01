# Quantum error mitigation (QEM)

Libraries: mitiq 1.1 (ZNE, PEC, CDR, DDD; GPL-3.0), qiskit_aer noise models,
pennylane `qml.transforms.mitigate_with_zne`.

Verification (mandatory):
- Simulate the circuit with an explicit noise model (e.g. `depolarizing_error` on "cx").
- Compute the ideal value noiselessly (`Statevector`), the raw noisy value, and the mitigated value.
- Assert `abs(mitigated - ideal) < abs(noisy - ideal)`. Report all three numbers.
- Mitigated values can overshoot physical bounds (e.g. <ZZ> > 1); say so when it happens.

Pitfalls:
- Mitiq's executor must return a float expectation value; use `save_density_matrix()` for exact
  noisy expectation values instead of shot noise.
- Mitiq imports cirq's QASM parser; `ply` must be installed (it is).

Verified example (examples/qem_mitiq_zne.py):
