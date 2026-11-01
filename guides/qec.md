# Quantum error correction (QEC)

Libraries: deltakit 0.10 (Riverlane; codes, noise models, QPU compilation, analysis),
stim 1.16, pymatching 2.4, ldpc 2.4 (BP+OSD for qLDPC codes).
Use only Deltakit's local open-source parts; never call deltakit.explorer.Client (cloud).

Verification (mandatory):
- Memory experiment at distances d = 3, 5 (add 7 if time allows) with rounds = d, same physical noise.
- Decode with pymatching from the detector error model; compute logical error probability (LEP).
- Below threshold, assert LEP decreases with distance; report Lambda = LEP(d) / LEP(d+2).
- Use >= 10_000 shots and a fixed sampler seed; state the noise model and p.

Pitfalls:
- IMPORT ORDER: import deltakit modules BEFORE pymatching/stim. Importing pymatching first makes
  css_code_memory_circuit fail with "RuntimeError: Caught an unknown exception!".
- Deltakit returns a deltakit_stim circuit; convert with `stim.Circuit(str(c.as_stim_circuit()))`
  before giving it to pymatching.
- SD6Noise(p) is circuit-level depolarising noise; its threshold is well below 1%, so use p <= 0.003.

Verified example (examples/qec_deltakit_surface_code.py):
