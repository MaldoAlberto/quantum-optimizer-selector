"""3-bit CDKM ripple-carry adder (8 qubits, several registers): Toffoli heavy, rich in T gates."""
from qiskit import QuantumCircuit
from qiskit.circuit.library import CDKMRippleCarryAdder


def build() -> QuantumCircuit:
    return CDKMRippleCarryAdder(3, kind="full").decompose()
