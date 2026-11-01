# Contributing

Thank you for helping find out how AI should optimize quantum circuits. Every contribution is one
small file or one entry in a registry.

## Before you open a pull request

```bash
.venv/bin/python -m bench.run
```

It must end with `0 not verified`. Include the new rows of `results/leaderboard.md` in the PR
description.

## Add a circuit

One file in `bench/circuits/`:

```python
"""Grover search on 5 qubits: multi-controlled gates, deep oracle."""
from qiskit import QuantumCircuit

def build() -> QuantumCircuit:
    ...
```

or an OpenQASM 2 file. Rules: at most 10 qubits, no mid-circuit measurement, a docstring that says
why the circuit is interesting for optimization. Circuits from real applications are most welcome.

## Add a hardware profile

One entry in `HARDWARE` in `bench/hardware.py`: native gates, coupling map (or `None` for
all-to-all), the native two-qubit gate, error rates and the objective (`"esp"` or `"t_count"`).
Link the source of the error rates in the PR.

## Add a pipeline

One function in `bench/pipelines.py`:

```python
@pipeline("bqskit+qiskit_L3")
def bqskit_then_qiskit(qc, hw):
    """One line on what it does."""
    ...
    return compiled  # in hw.basis, respecting hw.coupling
```

If your pipeline routes qubits itself, keep the layout on the returned circuit so the
verification can undo the permutation. Pipelines that need a cloud account or network access go
behind an environment variable and are skipped when it is missing.

## Add a selector (the AI track)

One function in `bench/selectors.py`:

```python
@selector("my_llm_selector")
def my_llm_selector(features, hw_name, hw):
    """Model, prompt and version used."""
    return "qiskit_L3"
```

Rules:
- It sees only `features` and the hardware profile. It must not run pipelines or read `results/`.
- If it calls an LLM, say which model and version, put the prompt in the file, and make it
  deterministic (temperature 0) or report the mean over 5 runs.
- Say in the docstring which circuits you looked at while designing it. Scores on circuits you
  tuned on are reported, but marked.

## Style

- Python 3.10+, standard library plus the pinned packages in `requirements-bench.txt`.
- Comments explain why, not what.
- Spanish or English issues are both fine.
