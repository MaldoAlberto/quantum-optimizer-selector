# quantum-optimizer-selector

**Which optimizer should the AI pick?** An open benchmark for AI-guided quantum circuit optimization.

> Status: **proposal + working pilot**. Contributions welcome.

AI coding assistants now write quantum programs. The hard part is not writing the circuit: it is
compiling it well for a given machine. Qiskit, TKET and PyZX each win in different places, and
no single one wins everywhere. This project asks one question:

**Can an AI look at a circuit and a target machine, and pick the optimization pipeline that wins,
without trying them all?**

We measure it openly, with verified results, so the community can improve on it.

## What the pilot found

4 circuits × 5 hardware profiles × 4 pipelines = 80 compilations, every one checked for unitary
equivalence.

- On NISQ hardware no pipeline always wins: TKET + Qiskit L3 had the best estimated success
  probability in 10 of 16 cases, Qiskit L3 in 5.
- For fault-tolerant (FTQC) targets PyZX cut T count by up to 44%, yet on NISQ hardware it added
  54–139% more two-qubit gates.
- On heavy-hex superconducting chips, 38% of two-qubit gates were routing SWAPs.
- Verification is not optional: a format-conversion bug made a wrong circuit "win" until the
  equivalence check caught it.

Current leaderboard (`results/leaderboard.md`):

| Selector | Oracle hits | Mean ESP regret (pp) | Mean T regret |
| --- | --- | --- | --- |
| `always_qiskit_L3` | 6/20 | 0.52 | 6.0 |
| `rules_v0` | 14/20 | 0.95 | 0.0 |
| `rules_v1` | 18/20 | 0.02 | 0.0 |

`rules_v1` was written after looking at these same 20 cases, so its score is optimistic. That is
exactly why we need more circuits from contributors: held-out cases are what make a selector
score mean something.

## How it works

```
circuit + hardware ──► selector (the AI) ──► picks one pipeline
                                   │
every pipeline ──► compile ──► verify equivalence ──► metrics ──► oracle = best verified
                                                                       │
                                     regret = oracle score − score of the selector's pick
```

| Piece | Folder | What you can add |
| --- | --- | --- |
| Circuits | `bench/circuits/` | one `.py` with `build()` or one `.qasm` |
| Hardware profiles | `bench/hardware.py` | native gates, connectivity, error rates, objective |
| Pipelines | `bench/pipelines.py` | any optimizer: BQSKit, VOQC, AI transpiler passes, your own |
| Selectors (AI track) | `bench/selectors.py` | rules, a trained model, or an LLM through any API or MCP |

Scoring: hardware with error rates are scored by estimated success probability
ESP = (1 − e₂)^n₂ × (1 − e₁)^n₁; logical FTQC targets by T count.

## Quick start

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements-bench.txt
.venv/bin/python -m bench.run          # writes results/runs.csv and results/leaderboard.md
```

Runs locally in a few minutes. No cloud account, no API key.

## Also in this repo

- `skills/quantum-circuit-optimizer/`: the same method as an Agent Skill (`SKILL.md`), usable by
  Claude Code and other agents that read skills.
- `mcp_server/`: an MCP server (`optimize_circuit`, `demo_circuit`) so any MCP client can call the
  optimizer with verification built in.
- `agent.py`: a provider-independent agent (any OpenAI-compatible endpoint, Ollama by default) that
  writes and verifies QEM, QEC and FTQC code.

## Roadmap

1. More circuits, especially held-out ones nobody tuned a selector on.
2. Sampling-based verification so circuits above 10 qubits can join.
3. Real noise models and QEM (Mitiq ZNE) instead of assumed error rates.
4. FTQC: rotation synthesis and the QDK resource estimator, scored in physical qubits and runtime.
5. An LLM selector baseline (local model through MCP) on the leaderboard.
6. Several transpiler seeds per run, reported with variance.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Every result must pass the equivalence check; a pipeline
that changes the circuit is discarded, not scored.

## Known limits of the pilot

Small circuits (≤ 8 qubits), simulated hardware with assumed error rates, no atom-movement cost
for neutral atoms, one transpiler seed. The numbers show the method works, not which hardware is
best.

## License

Apache-2.0. The agent's optional QEM examples use Mitiq (GPL-3.0); the benchmark does not import it.
