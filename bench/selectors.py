"""Selectors: the AI track. A selector looks at a circuit and a hardware profile BEFORE anything is
compiled and picks one pipeline. It is scored by regret: how much worse its pick is than the best
pipeline found by trying all of them (the oracle).

Add a selector with one function decorated with @selector("name"). It may be rules, a trained
model, or an LLM called through any API or MCP client. It must not run the pipelines itself.
Inputs:
    features: dict with num_qubits, depth, num_2q, num_ccx and counts, the gate counts after
        unrolling to ccx, cx, cp, rzz, u (so a QFT shows up as cp gates, an adder as ccx)
    hw_name, hw: the hardware profile (see hardware.py)
Output: a pipeline name from pipelines.PIPELINES.
"""

SELECTORS = {}


def selector(name):
    def register(fn):
        SELECTORS[name] = fn
        return fn
    return register


@selector("always_qiskit_L3")
def always_l3(features, hw_name, hw):
    """What most people do: one compiler, strongest preset."""
    return "qiskit_L3"


@selector("rules_v0")
def rules_v0(features, hw_name, hw):
    """The quantum-circuit-optimizer skill's rule: T count -> PyZX, otherwise TKET then Qiskit."""
    if hw.objective == "t_count":
        return "pyzx+qiskit_L3"
    return "tket+qiskit_L3"


@selector("rules_v1")
def rules_v1(features, hw_name, hw):
    """rules_v0 plus one finding of the pilot: small-angle rotation circuits (QFT-like, no Toffolis)
    do better with Qiskit L3's block resynthesis on NISQ hardware."""
    if hw.objective == "t_count":
        return "pyzx+qiskit_L3"
    if features["num_ccx"] == 0 and features["counts"].get("cp", 0) > 0:
        return "qiskit_L3"
    return "tket+qiskit_L3"
