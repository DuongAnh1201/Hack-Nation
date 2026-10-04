"""Sun, sky and blackbody spectra. Wavelengths in micrometres, intensities per micrometre.

Assumptions (also listed in docs/physics-bench.md):

* Sun: ASTM G173-03 AM1.5 global tilt spectrum (~1000 W/m^2), normal incidence.
* Sky: zenith transmittance t(lambda) from a simple analytic clear-sky model
  (below), angular dependence eps_atm = 1 - t^(1/cos theta) as in Raman et al. 2014,
  sky at ambient temperature. Override with a two-column CSV
  (wavelength_um, transmittance) via the LAB_ATM_TRANSMITTANCE_CSV env var.
"""

import functools
import os
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).parent / "data"

H = 6.62607015e-34  # J s
C = 2.99792458e8  # m / s
KB = 1.380649e-23  # J / K


@functools.lru_cache(maxsize=1)
def _am15_table():
    rows = np.loadtxt(DATA_DIR / "astmg173_global.csv", delimiter=",", comments="#")
    lam_um = rows[:, 0] / 1000.0
    irr_per_um = rows[:, 1] * 1000.0  # W/m^2/nm -> W/m^2/um
    return lam_um, irr_per_um


def am15_global(lam_um):
    """AM1.5 global spectral irradiance in W m^-2 um^-1 (zero outside 0.28-4 um)."""
    lam, irr = _am15_table()
    return np.interp(lam_um, lam, irr, left=0.0, right=0.0)


def planck_radiance(temp_k, lam_um):
    """Blackbody spectral radiance in W m^-2 sr^-1 um^-1."""
    lam_m = np.asarray(lam_um) * 1e-6
    x = H * C / (lam_m * KB * temp_k)
    return (2 * H * C**2 / lam_m**5) / np.expm1(x) * 1e-6


def _logistic(x):
    return 1.0 / (1.0 + np.exp(-x))


def _analytic_zenith_transmittance(lam_um):
    """Simplified clear, moderately humid mid-latitude sky.

    * 8-13 um window, peak transmittance 0.85, smooth edges.
    * Ozone absorption dip at 9.6 um (transmittance down to ~0.34 at the centre).
    * Partial 3.4-4.1 um window (0.6).
    * Opaque elsewhere in the thermal infrared (H2O and CO2 bands).
    """
    lam = np.asarray(lam_um, dtype=float)
    window = 0.85 * _logistic((lam - 8.0) / 0.15) * _logistic((13.0 - lam) / 0.3)
    window *= 1.0 - 0.6 * np.exp(-(((lam - 9.6) / 0.2) ** 2))
    mwir = 0.6 * _logistic((lam - 3.4) / 0.05) * _logistic((4.1 - lam) / 0.05)
    return np.clip(window + mwir, 0.0, 1.0)


@functools.lru_cache(maxsize=1)
def _csv_transmittance():
    path = os.environ.get("LAB_ATM_TRANSMITTANCE_CSV")
    if not path:
        return None
    rows = np.loadtxt(path, delimiter=",", comments="#")
    return rows[:, 0], rows[:, 1]


def zenith_transmittance(lam_um):
    table = _csv_transmittance()
    if table is not None:
        return np.interp(lam_um, table[0], table[1], left=0.0, right=0.0)
    return _analytic_zenith_transmittance(lam_um)


def atmosphere_model_name():
    path = os.environ.get("LAB_ATM_TRANSMITTANCE_CSV")
    return f"csv:{path}" if path else "analytic-clear-sky-v1"
