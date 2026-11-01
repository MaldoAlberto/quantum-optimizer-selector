"""QAOA MaxCut on a 6-node ring, p = 2, fixed angles: nearest-neighbour rzz layers."""
from qiskit import QuantumCircuit


def build() -> QuantumCircuit:
    qc = QuantumCircuit(6)
    qc.h(range(6))
    for gamma, beta in [(0.4, 0.7), (0.8, 0.3)]:
        for i in range(6):
            qc.rzz(2 * gamma, i, (i + 1) % 6)
        qc.rx(2 * beta, range(6))
    return qc
