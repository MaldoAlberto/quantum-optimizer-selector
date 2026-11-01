"""4 Toffolis sharing qubits on 4 qubits: lots to cancel. Same demo as the optimizer skill."""
from qiskit import QuantumCircuit


def build() -> QuantumCircuit:
    qc = QuantumCircuit(4)
    qc.h(3)
    qc.ccx(0, 1, 2)
    qc.ccx(1, 2, 3)
    qc.ccx(0, 1, 2)
    qc.cx(2, 3)
    qc.ccx(0, 1, 2)
    return qc
