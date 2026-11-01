"""Optimization pipelines: each one takes a logical circuit and returns it compiled to the hardware.

Add a pipeline with one function decorated with @pipeline("name"). It receives the circuit and a
Hardware profile and must return a circuit in hw.basis that respects hw.coupling. If you route
yourself, set the circuit's layout so verification can undo the qubit permutation (Qiskit's
transpile does this for you).
"""

import sys
from pathlib import Path

from qiskit import QuantumCircuit, transpile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "quantum-circuit-optimizer" / "scripts"))
import optimize  # noqa: E402  logical optimizers shared with the skill and the MCP server

SEED = 7
PIPELINES = {}


def pipeline(name):
    def register(fn):
        PIPELINES[name] = fn
        return fn
    return register


def _qiskit(qc, hw, level):
    return transpile(qc, basis_gates=list(hw.basis), coupling_map=hw.coupling,
                     optimization_level=level, seed_transpiler=SEED)


@pipeline("qiskit_L1")
def qiskit_l1(qc: QuantumCircuit, hw) -> QuantumCircuit:
    """Baseline: Qiskit with light optimization."""
    return _qiskit(qc, hw, 1)


@pipeline("qiskit_L3")
def qiskit_l3(qc: QuantumCircuit, hw) -> QuantumCircuit:
    """Qiskit's strongest preset."""
    return _qiskit(qc, hw, 3)


@pipeline("tket+qiskit_L3")
def tket_then_qiskit(qc: QuantumCircuit, hw) -> QuantumCircuit:
    """TKET FullPeepholeOptimise on the logical circuit, then Qiskit L3 for mapping."""
    return _qiskit(optimize.run_tket(qc), hw, 3)


@pipeline("pyzx+qiskit_L3")
def pyzx_then_qiskit(qc: QuantumCircuit, hw) -> QuantumCircuit:
    """PyZX full_reduce on the logical circuit, then Qiskit L3 for mapping."""
    return _qiskit(optimize.run_pyzx(qc), hw, 3)
