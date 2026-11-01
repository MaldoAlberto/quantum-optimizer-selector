"""QEM verificado: ZNE de Mitiq sobre un circuito Qiskit con ruido depolarizante en Aer.
Comprueba que el valor mitigado queda mas cerca del ideal que el valor con ruido."""
import numpy as np
from mitiq import zne
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import SparsePauliOp, Statevector
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

qc = QuantumCircuit(2)
for _ in range(10):  # identidad logica repetida: el ideal de <ZZ> es 1
    qc.h(0); qc.cx(0, 1); qc.cx(0, 1); qc.h(0)
OBS = SparsePauliOp("ZZ")
ideal = Statevector(qc).expectation_value(OBS).real

noise = NoiseModel()
noise.add_all_qubit_quantum_error(depolarizing_error(0.01, 2), ["cx"])
sim = AerSimulator(noise_model=noise, seed_simulator=7)

def execute(circ: QuantumCircuit) -> float:
    c = transpile(circ, basis_gates=["cx", "rz", "sx", "x", "h"], optimization_level=0)
    c.save_density_matrix()
    rho = sim.run(c).result().data()["density_matrix"]
    return float(np.real(rho.expectation_value(OBS)))

noisy = execute(qc)
mitigated = zne.execute_with_zne(qc, execute, factory=zne.inference.RichardsonFactory([1, 2, 3]),
                                 scale_noise=zne.scaling.fold_gates_at_random)
print(f"ideal={ideal:.4f} ruidoso={noisy:.4f} mitigado={mitigated:.4f}")
assert abs(mitigated - ideal) < abs(noisy - ideal), "ZNE no mejoro el resultado"
print("ALL TESTS PASSED")
