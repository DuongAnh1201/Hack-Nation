"""Refractive-index data (n, k) for the coating materials.

All data come from the refractiveindex.info database
(github.com/polyanskiy/refractiveindex.info-database), stored unmodified in
``lab/data/nk/``. Wavelengths are in micrometres everywhere in this module.

Source choice (one source per material where possible, covering 0.3-25 um):

| Material | Source file(s)                   | Native range (um) | Notes |
|----------|----------------------------------|-------------------|-------|
| SiO2     | Franta (film)                    | 0.025-125         | full range |
| Al2O3    | Franta (film)                    | 0.114-125         | full range |
| TiO2     | Franta (film)                    | 0.114-125         | full range |
| MgF2     | Franta (film)                    | 0.028-125         | full range |
| HfO2     | Franta (film)                    | 0.115-125         | control only (excluded from search) |
| Si3N4    | Luke (formula) + Kischkat (film) | 0.31-5.5, 1.54-14.3 | stitched at 1.54 um; held constant above 14.3 um |
| Ag       | Yang (template-stripped)         | 0.27-24.9         | held constant at the edges |
| Al       | Rakic Lorentz-Drude              | 0.062-248         | full range |

Outside a source's native range the nearest tabulated value is held constant
(``numpy.interp`` behaviour). That only matters for Si3N4 above 14.3 um and is
an explicit, documented assumption.
"""

import functools
from pathlib import Path

import numpy as np
import yaml

DATA_DIR = Path(__file__).parent / "data" / "nk"

# (file, lambda_min_um, lambda_max_um) segments, applied in order; later segments win.
_SOURCES = {
    "SiO2": [("SiO2_Franta.yml", None, None)],
    "Al2O3": [("Al2O3_Franta.yml", None, None)],
    "TiO2": [("TiO2_Franta.yml", None, None)],
    "MgF2": [("MgF2_Franta.yml", None, None)],
    "HfO2": [("HfO2_Franta.yml", None, None)],
    "Si3N4": [("Si3N4_Luke.yml", None, 1.54), ("Si3N4_Kischkat.yml", 1.54, None)],
    "Ag": [("Ag_Yang.yml", None, None)],
    "Al": [("Al_Rakic-LD.yml", None, None)],
}

KNOWN_MATERIALS = tuple(_SOURCES)


def _formula_1(coeffs, lam_um):
    """refractiveindex.info 'formula 1' (Sellmeier): n^2 - 1 = C0 + sum Ci l^2 / (l^2 - Cj^2)."""
    c = list(coeffs)
    n2 = 1.0 + c[0]
    for i in range(1, len(c) - 1, 2):
        n2 = n2 + c[i] * lam_um**2 / (lam_um**2 - c[i + 1] ** 2)
    return np.sqrt(n2).astype(complex)


@functools.lru_cache(maxsize=None)
def _load_file(fname):
    """Return a callable lam_um -> complex index (n + ik) for one database file."""
    doc = yaml.safe_load((DATA_DIR / fname).read_text())
    entry = doc["DATA"][0]
    kind = entry["type"]
    if kind == "tabulated nk":
        rows = np.array([[float(x) for x in line.split()] for line in entry["data"].strip().splitlines()])
        lam, n, k = rows[:, 0], rows[:, 1], rows[:, 2]
        return lambda x: np.interp(x, lam, n) + 1j * np.interp(x, lam, k)
    if kind == "formula 1":
        coeffs = [float(v) for v in str(entry["coefficients"]).split()]
        lo, hi = (float(v) for v in str(entry["wavelength_range"]).split())
        return lambda x: _formula_1(coeffs, np.clip(x, lo, hi))
    raise ValueError(f"unsupported refractiveindex.info entry type {kind!r} in {fname}")


def refractive_index(material, lam_um):
    """Complex refractive index n + ik (k >= 0 absorbing) of ``material`` at ``lam_um``."""
    if material not in _SOURCES:
        raise KeyError(f"unknown material {material!r}; known: {KNOWN_MATERIALS}")
    lam_um = np.asarray(lam_um, dtype=float)
    out = np.empty(lam_um.shape, dtype=complex)
    for fname, lo, hi in _SOURCES[material]:
        mask = np.ones(lam_um.shape, dtype=bool)
        if lo is not None:
            mask &= lam_um >= lo
        if hi is not None:
            mask &= lam_um < hi
        if mask.any():
            out[mask] = _load_file(fname)(lam_um[mask])
    return out


def material_properties(material):
    """Summary used by the agents' ``material_properties`` tool."""
    lam = np.array([0.5, 1.0, 2.0, 8.0, 9.6, 10.5, 12.0, 13.0, 20.0])
    nk = refractive_index(material, lam)
    return {
        "material": material,
        "sources": [f for f, _, _ in _SOURCES[material]],
        "samples": [
            {"wavelength_um": float(l), "n": round(float(v.real), 4), "k": round(float(v.imag), 4)}
            for l, v in zip(lam, nk)
        ],
    }
