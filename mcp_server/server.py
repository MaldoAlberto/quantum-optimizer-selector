"""Quantum algorithms MCP server: verified circuit optimization for any MCP client.

Exposes the quantum-circuit-optimizer skill as MCP tools, so Claude, Cursor, VS Code, or a local
LLM host can call it. Every result is checked for unitary equivalence before it is returned.

Run (stdio):
    ~/quantum-agent/.venv/bin/python ~/quantum-agent/mcp_server/server.py
"""

import logging
import sys
from pathlib import Path
from typing import Literal

from mcp.server.mcpserver import MCPServer
from qiskit import QuantumCircuit, qasm2

SKILL = Path(__file__).resolve().parent.parent / "skills" / "quantum-circuit-optimizer"
sys.path.insert(0, str(SKILL / "scripts"))
import optimize  # noqa: E402  (the skill's script, shared with the CLI and the agent)

logging.getLogger("qiskit").setLevel(logging.WARNING)  # transpiler logs every pass at INFO
MAX_QUBITS = 20  # keeps a single call under a few seconds on a laptop

server = MCPServer(
    name="quantum-algorithms",
    log_level="WARNING",
    version="0.1.0",
    instructions=(
        "Tools for optimizing quantum circuits with Qiskit, TKET and PyZX. Pick the metric from "
        "the user's goal: '2q' for NISQ hardware and error mitigation, 't' for fault-tolerant "
        "resource estimation, 'depth' for short-coherence or QEC syndrome circuits. Only report "
        "results whose 'equiv' is 'yes' (or 'skipped' above 12 qubits, then say it was not verified)."
    ),
)


@server.tool()
def optimize_circuit(qasm: str, metric: Literal["2q", "t", "depth"] = "2q") -> dict:
    """Optimize an OpenQASM 2 circuit with Qiskit (level 3), TKET and PyZX, verify each result is
    unitarily equivalent to the input, and return a comparison table plus the best circuit.

    Args:
        qasm: The circuit in OpenQASM 2. Final measurements are removed before optimizing.
        metric: What to minimize: "2q" (CX count), "t" (non-Clifford rotations, T-count proxy)
            or "depth".
    """
    qc = QuantumCircuit.from_qasm_str(qasm)
    if qc.num_qubits > MAX_QUBITS:
        return {"error": f"{qc.num_qubits} qubits; this server accepts at most {MAX_QUBITS}."}
    rows, best, circuit = optimize.compare(qc, metric)
    result = {"metric": metric, "rows": rows}
    if best is None:
        result["error"] = "No optimizer produced a verified circuit."
        return result
    before, after = rows[0][metric], best[metric]
    result.update(
        best_tool=best["tool"],
        improvement=f"{metric}: {before} -> {after} ({(before - after) / before:.0%} less)" if before else "n/a",
        best_qasm=qasm2.dumps(circuit),
    )
    return result


@server.tool()
def demo_circuit(name: Literal["qft5", "toffoli_chain"]) -> str:
    """Return a demo circuit as OpenQASM 2: "qft5" (5-qubit QFT, small-angle rotations) or
    "toffoli_chain" (4 qubits, Clifford+T heavy). Useful to try optimize_circuit."""
    return qasm2.dumps(optimize.to_basis(optimize.demo(name)))


@server.resource("skill://quantum-circuit-optimizer")
def skill_guide() -> str:
    """The full optimization workflow: metric choice, verification rules, pitfalls, next steps."""
    return (SKILL / "SKILL.md").read_text()


if __name__ == "__main__":
    server.run()
