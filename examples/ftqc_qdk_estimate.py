"""FTQC verificado: estimacion de recursos de un circuito Qiskit con el estimador de Microsoft QDK
(qsharp), local y sin cuenta. Comprueba que los resultados son coherentes."""
from qiskit import QuantumCircuit
from qiskit.circuit.library import QFTGate
from qsharp.estimator import EstimatorParams
from qsharp.interop.qiskit import ResourceEstimatorBackend

n = 8
qc = QuantumCircuit(n)
qc.append(QFTGate(n), range(n))
qc = qc.decompose(reps=2)

params = EstimatorParams()
params.error_budget = 0.001
result = ResourceEstimatorBackend().run(qc, params=params).result()
phys = result["physicalCounts"]
logical = result["logicalQubit"]
print(f"qubits fisicos={phys['physicalQubits']} runtime={phys['runtime']} ns "
      f"distancia={logical['codeDistance']} qubits logicos={result['physicalCountsFormatted']['algorithmicLogicalQubits']}")
assert phys["physicalQubits"] > n, "debe necesitar mas qubits fisicos que logicos"
assert logical["codeDistance"] >= 3
print("ALL TESTS PASSED")
