"""Run the benchmark: every circuit x hardware x pipeline, verified, then score every selector.

Usage (from the repo root):
    .venv/bin/python -m bench.run                 # everything
    .venv/bin/python -m bench.run --circuits qft6 adder3 --hardware sc_heavyhex

Writes results/runs.csv (one row per compilation) and results/leaderboard.md (selector regret).
"""

import argparse
import csv
import importlib.util
import logging
import sys
import time
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Operator

from bench.hardware import HARDWARE
from bench.pipelines import PIPELINES, optimize
from bench.selectors import SELECTORS

logging.getLogger("qiskit").setLevel(logging.WARNING)
ROOT = Path(__file__).resolve().parent.parent
CIRCUIT_DIR = Path(__file__).resolve().parent / "circuits"
RESULTS = ROOT / "results"
MAX_QUBITS = 10


def load_circuits() -> dict:
    out = {}
    for path in sorted(CIRCUIT_DIR.iterdir()):
        if path.suffix == ".py" and path.stem != "__init__":
            spec = importlib.util.spec_from_file_location(f"bench.circuits.{path.stem}", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            out[path.stem] = mod.build()
        elif path.suffix == ".qasm":
            out[path.stem] = QuantumCircuit.from_qasm_file(str(path))
    for name, qc in out.items():
        if qc.num_qubits > MAX_QUBITS:
            raise SystemExit(f"{name}: {qc.num_qubits} qubits > {MAX_QUBITS} (unitary check limit)")
        qc.remove_final_measurements()
    return out


def features(qc: QuantumCircuit) -> dict:
    unrolled = transpile(qc, basis_gates=["ccx", "cx", "cp", "rzz", "u"], optimization_level=0)
    counts = dict(unrolled.count_ops())
    return {
        "num_qubits": qc.num_qubits, "depth": unrolled.depth(), "counts": counts,
        "num_ccx": counts.get("ccx", 0),
        "num_2q": sum(1 for i in unrolled.data if i.operation.num_qubits == 2),
    }


def verify(original: QuantumCircuit, compiled: QuantumCircuit) -> bool:
    """Same unitary on the logical qubits, with ancillas starting and ending in |0>."""
    v = Operator(original).data
    u = Operator.from_circuit(compiled).data  # undoes initial layout and final routing permutation
    idx = np.arange(2 ** original.num_qubits)  # ancillas are the high bits, all in |0>
    block = u[np.ix_(idx, idx)]
    if not np.isclose(np.linalg.norm(block), np.linalg.norm(v)):
        return False  # amplitude leaked into ancillas
    phase = np.vdot(v.flatten(), block.flatten())
    return abs(phase) > 1e-9 and np.allclose(block, v * phase / abs(phase), atol=1e-6)


def measure(qc, out, hw, free_2q) -> dict:
    ops = out.count_ops()
    n2 = ops.get(hw.gate_2q, 0) + 3 * ops.get("swap", 0)
    n1 = sum(v for k, v in ops.items() if k not in (hw.gate_2q, "swap", "barrier", "measure"))
    t = optimize.metrics(transpile(out, basis_gates=optimize.BASIS, optimization_level=0))["t"]
    esp = (1 - hw.err_2q) ** n2 * (1 - hw.err_1q) ** n1 if hw.err_2q is not None else None
    return {
        "native_2q": n2, "depth_2q": out.depth(lambda i: i.operation.num_qubits == 2),
        "depth": out.depth(), "swap_overhead_2q": n2 - free_2q, "t_count": t,
        "esp": round(esp, 4) if esp is not None else "",
    }


def score(row, hw) -> float:
    """Higher is better, for every objective."""
    return float(row["esp"]) if hw.objective == "esp" else -float(row["t_count"])


def leaderboard(rows, circuits) -> str:
    by_case = {}
    for r in rows:
        if r["verified"]:
            by_case.setdefault((r["circuit"], r["hardware"]), {})[r["pipeline"]] = r
    lines = ["# Leaderboard: selector regret", "",
             "Regret = how much worse the selector's pick is than the best verified pipeline (oracle).",
             "ESP regret in percentage points of success probability; T regret in T gates. Lower is better.", "",
             "| Selector | Oracle hits | Mean ESP regret (pp) | Mean T regret | Worst case |",
             "| --- | --- | --- | --- | --- |"]
    feats = {name: features(qc) for name, qc in circuits.items()}
    for sname, fn in SELECTORS.items():
        hits, esp_reg, t_reg, worst = 0, [], [], (0.0, "")
        for (c, h), cands in by_case.items():
            hw = HARDWARE[h]
            pick = fn(feats[c], h, hw)
            best = max(cands.values(), key=lambda r: score(r, hw))
            if pick not in cands:
                reg = float("inf")
            else:
                reg = score(best, hw) - score(cands[pick], hw)
            hits += reg <= 1e-12
            if hw.objective == "esp":
                esp_reg.append(reg * 100)
                if reg * 100 > worst[0]:
                    worst = (reg * 100, f"{c} on {h}: picked {pick}, best {best['pipeline']}")
            else:
                t_reg.append(reg)
        lines.append(f"| `{sname}` | {hits}/{len(by_case)} | {np.mean(esp_reg):.2f} | {np.mean(t_reg):.1f} | "
                     f"{worst[1] or '-'} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--circuits", nargs="*")
    p.add_argument("--hardware", nargs="*")
    args = p.parse_args()
    circuits = {k: v for k, v in load_circuits().items() if not args.circuits or k in args.circuits}
    hardware = {k: v for k, v in HARDWARE.items() if not args.hardware or k in args.hardware}

    rows = []
    for cname, qc in circuits.items():
        for hname, hw in hardware.items():
            free_hw = hw.__class__(**{**hw.__dict__, "coupling": None})  # same gates, all-to-all
            for pname, fn in PIPELINES.items():
                t0 = time.perf_counter()
                out = fn(qc, hw)
                secs = time.perf_counter() - t0
                free_2q = fn(qc, free_hw).count_ops().get(hw.gate_2q, 0)
                r = {"circuit": cname, "hardware": hname, "pipeline": pname, "qubits": qc.num_qubits,
                     **measure(qc, out, hw, free_2q), "verified": verify(qc, out), "seconds": round(secs, 2)}
                rows.append(r)
                print(f"{cname:<14} {hname:<13} {pname:<15} 2q={r['native_2q']:>4} T={r['t_count']:>3} "
                      f"esp={r['esp']!s:>6} ok={r['verified']}")

    RESULTS.mkdir(exist_ok=True)
    with (RESULTS / "runs.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    board = leaderboard(rows, circuits)
    (RESULTS / "leaderboard.md").write_text(board)
    print("\n" + board)
    bad = [r for r in rows if not r["verified"]]
    print(f"{len(rows)} runs, {len(bad)} not verified")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
