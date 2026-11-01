"""Hardware profiles: native gates, connectivity, assumed error rates and the objective to score.

Add a profile with one entry in HARDWARE. Error rates are typical approximate values used to
estimate success probability, not data from a specific chip: cite a source in the PR if you
change them.
"""

from dataclasses import dataclass

from qiskit.transpiler import CouplingMap


@dataclass(frozen=True)
class Hardware:
    basis: tuple            # native gates
    coupling: object        # CouplingMap, or None for all-to-all
    gate_2q: str            # name of the native two-qubit gate in `basis`
    err_2q: float | None    # assumed error per 2q gate (None for logical FTQC)
    err_1q: float | None
    objective: str          # "esp" (maximize) or "t_count" (minimize)
    example: str            # commercial example, for humans


def heavy_hex_10() -> CouplingMap:
    """Connected 10-qubit patch of IBM's heavy-hex lattice (keeps the unitary check cheap)."""
    full = CouplingMap.from_heavy_hex(3)
    keep, frontier = [0], [0]
    while len(keep) < 10:
        q = frontier.pop(0)
        for n in sorted(full.neighbors(q)):
            if n not in keep and len(keep) < 10:
                keep.append(n)
                frontier.append(n)
    return full.reduce(keep)


HARDWARE = {
    "sc_heavyhex": Hardware(("cz", "rz", "sx", "x"), heavy_hex_10(), "cz", 3e-3, 2.5e-4, "esp", "IBM Heron"),
    "sc_grid": Hardware(("cz", "rz", "sx", "x"), CouplingMap.from_grid(3, 3), "cz", 3e-3, 5e-4, "esp", "Google Willow"),
    "trapped_ion": Hardware(("rxx", "rx", "ry", "rz"), None, "rxx", 1e-3, 3e-5, "esp", "Quantinuum, IonQ"),
    "neutral_atom": Hardware(("cz", "rz", "sx", "x"), None, "cz", 5e-3, 1e-3, "esp", "QuEra, Pasqal (no atom-move cost)"),
    "ftqc_logical": Hardware(("cx", "rz", "sx", "x"), None, "cx", None, None, "t_count", "surface-code logical layer"),
}
