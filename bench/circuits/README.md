# Circuits

Add a circuit with ONE file here:

- `name.py` with a `build() -> QuantumCircuit` function and a one-line docstring saying what the
  circuit is and why it is interesting for optimization, or
- `name.qasm` in OpenQASM 2.

Limit: 10 qubits, so the full unitary check runs on a laptop. Larger circuits need sampling
verification first (see the roadmap in the main README).
