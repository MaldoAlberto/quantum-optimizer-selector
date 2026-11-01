# What each optimizer does and when it wins

## Qiskit transpiler, `optimization_level=3`
- Rewrites: gate cancellation (commutation analysis), 1-qubit gate resynthesis, 2-qubit block
  resynthesis (KAK / Weyl decomposition), removal of final swaps (recorded as a layout permutation).
- Wins: two-qubit gate count on general circuits. Benchmark: arXiv 2409.08844.
- Use `seed_transpiler` for reproducible results; level 3 is stochastic in layout and routing.

## TKET, `FullPeepholeOptimise`
- Rewrites: Clifford simplification, phase-gadget synthesis, 2-qubit block resynthesis, peephole rules.
- Wins: two-qubit depth, especially with more connected hardware. arXiv 2409.08844, arXiv 2003.10611.
- `allow_swaps=True` can save more gates but permutes the output qubits.

## PyZX, `full_reduce` + `extract_circuit`
- Rewrites: turns the circuit into a ZX diagram, applies local complementation and pivoting, fuses
  phases (phase teleportation), then extracts a circuit.
- Wins: T count on Clifford+T circuits. Often increases CX count: extraction is not CX-optimal.
- With TODD it reaches up to 47% fewer 2-qubit gates than the Clifford approach (arXiv 2311.08881).

## Not included, worth knowing
- BQSKit: numerical resynthesis by instantiation (arXiv 2206.07885). Slow, strong on small blocks.
- VOQC: formally verified optimizer (arXiv 1912.02250).
- IBM AI transpiler passes (`qiskit-ibm-transpiler`): reinforcement-learning routing and synthesis.
  Pulls IBM cloud dependencies; see the dependency pitfall in SKILL.md.
