"""Compare quantum circuit optimizers on one circuit and verify each result.

Runs Qiskit (optimization_level=3), TKET (FullPeepholeOptimise) and PyZX (full_reduce +
extract) on the same circuit, translates every result to one basis (cx, rz, sx, x) so the
counts are comparable, checks unitary equivalence against the input, and prints a table.

Usage:
    python optimize.py circuit.qasm [--metric 2q|t|depth] [--json out.json]
    python optimize.py --demo qft5
    python optimize.py --demo toffoli_chain

Metrics:
    2q     two-qubit gate count (cx). Main cost on NISQ hardware and for QEM.
    t      non-Clifford rotations (rz angle not a multiple of pi/2). T-count proxy for FTQC.
    depth  circuit depth.
"""

import argparse
import json
import math
import sys
import time

import pyzx as zx
from pytket import OpType
from pytket.passes import AutoRebase, FullPeepholeOptimise, RemoveRedundancies
from pytket.qasm import circuit_from_qasm_str, circuit_to_qasm_str
from qiskit import QuantumCircuit, qasm2, transpile
from qiskit.circuit.library import QFTGate
from qiskit.quantum_info import Operator

BASIS = ["cx", "rz", "sx", "x"]
ZX_BASIS = ["cx", "rz", "h"]  # gates PyZX's QASM parser reads reliably
MAX_EQUIV_QUBITS = 12  # dense unitary check is 4^n memory


def demo(name: str) -> QuantumCircuit:
    if name == "qft5":
        qc = QuantumCircuit(5)
        qc.append(QFTGate(5), range(5))
        return qc
    if name == "toffoli_chain":  # Clifford+T heavy: 3 Toffolis share qubits, lots to cancel
        qc = QuantumCircuit(4)
        qc.h(3)
        qc.ccx(0, 1, 2)
        qc.ccx(1, 2, 3)
        qc.ccx(0, 1, 2)
        qc.cx(2, 3)
        qc.ccx(0, 1, 2)
        return qc
    raise SystemExit(f"Unknown demo {name!r}: use qft5 or toffoli_chain")


def to_basis(qc: QuantumCircuit) -> QuantumCircuit:
    """Basis translation only, no optimization, so every tool is counted the same way."""
    return transpile(qc, basis_gates=BASIS, optimization_level=0)


def metrics(qc: QuantumCircuit) -> dict:
    ops = qc.count_ops()
    non_clifford = sum(
        1 for inst in qc.data
        if inst.operation.name == "rz"
        and not math.isclose((float(inst.operation.params[0]) / (math.pi / 2)) % 1, 0, abs_tol=1e-9)
        and not math.isclose((float(inst.operation.params[0]) / (math.pi / 2)) % 1, 1, abs_tol=1e-9)
    )
    return {"2q": ops.get("cx", 0), "t": non_clifford, "depth": qc.depth(), "gates": sum(ops.values())}


def run_qiskit(qc: QuantumCircuit) -> QuantumCircuit:
    return transpile(qc, basis_gates=BASIS, optimization_level=3, seed_transpiler=7)


def run_tket(qc: QuantumCircuit) -> QuantumCircuit:
    # One register: TKET sorts qubits by register name, which would permute multi-register circuits
    flat = QuantumCircuit(qc.num_qubits)
    flat.compose(to_basis(qc), qubits=range(qc.num_qubits), inplace=True)
    circ = circuit_from_qasm_str(qasm2.dumps(flat))
    FullPeepholeOptimise(allow_swaps=False).apply(circ)  # implicit swaps would permute qubits
    AutoRebase({OpType.CX, OpType.Rz, OpType.SX, OpType.X}).apply(circ)  # rebase inside tket, not after
    RemoveRedundancies().apply(circ)
    return to_basis(QuantumCircuit.from_qasm_str(circuit_to_qasm_str(circ)))


def run_pyzx(qc: QuantumCircuit) -> QuantumCircuit:
    src = transpile(qc, basis_gates=ZX_BASIS, optimization_level=0)
    g = zx.Circuit.from_qasm(qasm2.dumps(src)).to_graph()
    zx.full_reduce(g)
    out = zx.basic_optimization(zx.extract_circuit(g.copy()).to_basic_gates())
    return to_basis(QuantumCircuit.from_qasm_str(out.to_qasm()))


def equivalent(a: QuantumCircuit, b: QuantumCircuit) -> str:
    if a.num_qubits > MAX_EQUIV_QUBITS:
        return "skipped"
    # from_circuit undoes the output permutation Qiskit L3 records when it elides final swaps
    return "yes" if Operator(a).equiv(Operator.from_circuit(b)) else "NO"


def compare(qc: QuantumCircuit, metric: str = "2q"):
    """Run every optimizer on qc. Returns (rows, best_row or None, best_circuit or None)."""
    qc = qc.copy()
    qc.remove_final_measurements()
    base = to_basis(qc)
    rows = [{"tool": "input", **metrics(base), "equiv": "-", "seconds": 0.0}]
    circuits = {}
    for tool, fn in [("qiskit-L3", run_qiskit), ("tket", run_tket), ("pyzx", run_pyzx)]:
        t0 = time.perf_counter()
        try:
            out = fn(qc)
        except Exception as e:  # one tool failing must not hide the others
            rows.append({"tool": tool, "error": f"{type(e).__name__}: {e}"[:120]})
            continue
        circuits[tool] = out
        rows.append({"tool": tool, **metrics(out), "equiv": equivalent(base, out),
                     "seconds": round(time.perf_counter() - t0, 2)})
    valid = [r for r in rows[1:] if r.get("equiv") in ("yes", "skipped")]
    if not valid:
        return rows, None, None
    best = min(valid, key=lambda r: (r[metric], r["2q"], r["depth"]))
    return rows, best, circuits[best["tool"]]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("qasm", nargs="?", help="OpenQASM 2 file")
    p.add_argument("--demo", choices=["qft5", "toffoli_chain"])
    p.add_argument("--metric", default="2q", choices=["2q", "t", "depth"])
    p.add_argument("--json", help="write results to this file")
    args = p.parse_args()
    if bool(args.qasm) == bool(args.demo):
        p.error("give a QASM file or --demo, not both")

    qc = demo(args.demo) if args.demo else QuantumCircuit.from_qasm_file(args.qasm)
    rows, best, _ = compare(qc, args.metric)

    print(f"{'tool':<10} {'2q':>5} {'t':>5} {'depth':>6} {'gates':>6} {'equiv':>7} {'s':>6}")
    for r in rows:
        if "error" in r:
            print(f"{r['tool']:<10} error: {r['error']}")
        else:
            print(f"{r['tool']:<10} {r['2q']:>5} {r['t']:>5} {r['depth']:>6} {r['gates']:>6} "
                  f"{r['equiv']:>7} {r['seconds']:>6}")

    if best is None:
        print("No optimizer produced a verified circuit.")
        return 1
    gain = rows[0][args.metric] - best[args.metric]
    print(f"\nBest for {args.metric}: {best['tool']} "
          f"({rows[0][args.metric]} -> {best[args.metric]}, -{gain})")

    if args.json:
        with open(args.json, "w") as f:
            json.dump({"metric": args.metric, "best": best["tool"], "rows": rows}, f, indent=2)
    if any(r.get("equiv") == "NO" for r in rows):
        print("WARNING: at least one optimizer changed the circuit's unitary; its result was discarded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
