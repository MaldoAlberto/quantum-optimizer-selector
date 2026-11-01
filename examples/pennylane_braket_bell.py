"""Multi-framework verificado: el mismo estado de Bell en PennyLane (default.qubit) y en el
simulador local de Amazon Braket (gratis, sin cuenta de AWS)."""
import numpy as np
import pennylane as qml
from braket.circuits import Circuit
from braket.devices import LocalSimulator

dev = qml.device("default.qubit", wires=2)

@qml.qnode(dev)
def bell():
    qml.Hadamard(0); qml.CNOT([0, 1])
    return qml.probs(wires=[0, 1])

p_pl = np.array(bell())
p_bk = LocalSimulator().run(Circuit().h(0).cnot(0, 1).probability(), shots=0).result().values[0]
print("PennyLane:", np.round(p_pl, 3), " Braket:", np.round(p_bk, 3))
assert np.allclose(p_pl, [0.5, 0, 0, 0.5]) and np.allclose(p_bk, p_pl)
print("ALL TESTS PASSED")
