"""6-qubit quantum Fourier transform: small-angle controlled rotations, all-to-all interaction."""
from qiskit import QuantumCircuit
from qiskit.circuit.library import QFTGate


def build() -> QuantumCircuit:
    qc = QuantumCircuit(6)
    qc.append(QFTGate(6), range(6))
    return qc
