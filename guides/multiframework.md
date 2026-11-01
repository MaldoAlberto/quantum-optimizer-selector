# PennyLane and Amazon Braket

Libraries: pennylane 0.45 (`default.qubit`), amazon-braket-sdk 1.127 (`LocalSimulator`, free).
Real Braket hardware needs an AWS account and costs money per task and shot: this agent has no
tool to submit hardware jobs. Write code for LocalSimulator only and tell the user what would
change for hardware (device ARN, shots, cost).

Verification: compare probabilities or expectation values across frameworks, or against a numpy
reference, with `np.allclose`.

Verified example (examples/pennylane_braket_bell.py):
