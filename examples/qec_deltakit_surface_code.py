"""QEC verificado: memoria Z de código de superficie rotado con Deltakit + Stim + PyMatching.
Comprueba que la tasa de error lógico (LEP) baja al subir la distancia bajo el umbral."""
# Deltakit debe importarse ANTES que pymatching: al reves, deltakit_stim falla con
# "RuntimeError: Caught an unknown exception!" al construir el circuito.
from deltakit.explorer.codes import RotatedPlanarCode, css_code_memory_circuit
from deltakit.explorer.qpu import QPU, SD6Noise
from deltakit.circuit.gates import PauliBasis
import numpy as np
import pymatching
import stim

P, SHOTS = 0.002, 20_000
lep = {}
for d in (3, 5):
    code = RotatedPlanarCode(width=d, height=d)
    circuit = css_code_memory_circuit(code, num_rounds=d, logical_basis=PauliBasis.Z)
    noisy = QPU(circuit.qubits, noise_model=SD6Noise(p=P)).compile_and_add_noise_to_circuit(circuit)
    # deltakit devuelve un circuito de deltakit_stim; se pasa por texto al stim normal que usa pymatching
    stim_circuit = stim.Circuit(str(noisy.as_stim_circuit()))
    matcher = pymatching.Matching.from_detector_error_model(stim_circuit.detector_error_model(decompose_errors=True))
    dets, obs = stim_circuit.compile_detector_sampler(seed=1).sample(SHOTS, separate_observables=True)
    fails = np.sum(np.any(matcher.decode_batch(dets) != obs, axis=1))
    lep[d] = fails / SHOTS
    print(f"d={d}: qubits={stim_circuit.num_qubits} LEP={lep[d]:.4f} ({fails}/{SHOTS})")

assert lep[5] < lep[3], f"LEP no baja con la distancia: {lep}"
print(f"Lambda (LEP3/LEP5) = {lep[3] / max(lep[5], 1 / SHOTS):.1f}")
print("ALL TESTS PASSED")
