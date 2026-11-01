# Leaderboard: selector regret

Regret = how much worse the selector's pick is than the best verified pipeline (oracle).
ESP regret in percentage points of success probability; T regret in T gates. Lower is better.

| Selector | Oracle hits | Mean ESP regret (pp) | Mean T regret | Worst case |
| --- | --- | --- | --- | --- |
| `always_qiskit_L3` | 6/20 | 0.52 | 6.0 | adder3 on neutral_atom: picked qiskit_L3, best tket+qiskit_L3 |
| `rules_v0` | 14/20 | 0.95 | 0.0 | qft6 on neutral_atom: picked tket+qiskit_L3, best qiskit_L3 |
| `rules_v1` | 18/20 | 0.02 | 0.0 | toffoli_chain on sc_heavyhex: picked tket+qiskit_L3, best qiskit_L3 |
