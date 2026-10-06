"""Response of the 4 × 4 lead-glass array (D-06, D-07, D-17).

For each photon that reaches the array unconverted:
  1. its measured energy is smeared with σ_E/E = c + s/√E;
  2. the shower centre is shifted sideways for oblique incidence;
  3. the energy is shared between blocks by a two-Gaussian lateral profile,
     whose widths fluctuate photon by photon.
Then, per block, a fixed gain error is applied, electronic noise is added,
and blocks below threshold are set to zero.

Block energies are (N, n, n) arrays indexed [event, iv, iu] in GeV, with
iu = 0 at u = -half-width (the beam side) and iv = 0 at v = -half-width.
Blocks are treated as contiguous (no gaps or wrapping).
"""

from dataclasses import dataclass

import numpy as np
from scipy.special import ndtr  # standard normal CDF Φ

# Photon showers peak at t_max = ln(E/E_c) + 0.5 radiation lengths, and the
# longitudinal profile is a gamma distribution with b ≈ 0.5 (PDG), whose mean
# lies 1/b = 2 X0 beyond the maximum.
PHOTON_TMAX_OFFSET = 0.5
GAMMA_PROFILE_B = 0.5


@dataclass
class ShowerShape:
    core_fraction: float
    core_sigma_cm: float
    halo_sigma_cm: float


def shower_shape(cfg):
    """Two-Gaussian lateral profile fixed by the PDG containment numbers.

    Treating the narrow core as entirely inside 1 R_M, the halo (fraction h,
    width k·R_M) alone sets the energy outside radius r:
        h · exp(-r² / (2 k² R_M²)) = 1 - containment(r)
    Writing this at r = 1 R_M and r = 3.5 R_M gives two equations for h and k.
    """
    s = cfg["shower"]
    r_m = s["moliere_radius_cm"]
    outside_1 = 1.0 - s["containment_1rm"]
    outside_35 = 1.0 - s["containment_3p5rm"]
    k2 = (3.5**2 - 1.0) / (2.0 * np.log(outside_1 / outside_35))
    halo = outside_1 * np.exp(1.0 / (2.0 * k2))
    return ShowerShape(1.0 - halo, s["core_sigma_rm"] * r_m, np.sqrt(k2) * r_m)


def shower_depth_cm(energy, cfg):
    """Depth of the shower's energy centre: X0 · (ln(E/E_c) + 0.5 + 1/b)."""
    s = cfg["shower"]
    t_max = np.log(np.maximum(energy, 1e-9) / s["critical_energy_gev"]) + PHOTON_TMAX_OFFSET
    return s["glass_x0_cm"] * np.maximum(t_max + 1.0 / GAMMA_PROFILE_B, 0.0)


def shower_centres(hits, cfg):
    """Entry point shifted along the photon direction to the shower's energy centre."""
    depth = shower_depth_cm(hits.energy, cfg)
    with np.errstate(divide="ignore", invalid="ignore"):
        slope = hits.direction[:, :2] / hits.direction[:, 2:]
    return hits.position + depth[:, None] * slope


def measured_energy(energy, rng, cfg):
    """Smear energies with σ_E/E = constant + stochastic / √E (BL4S, D-07)."""
    d = cfg["detector"]
    relative = d["resolution_constant"] + d["resolution_stochastic"] / np.sqrt(np.maximum(energy, 1e-12))
    return np.maximum(energy * (1.0 + relative * rng.standard_normal(len(energy))), 0.0)


def shape_variations(n, rng, cfg):
    """Per-photon width scale (log-normal) and core fraction (clipped Gaussian)."""
    s = cfg["shower"]
    scale = np.exp(s["width_fluctuation"] * rng.standard_normal(n))
    core = np.clip(shower_shape(cfg).core_fraction
                   + s["core_fraction_fluctuation"] * rng.standard_normal(n), 0.0, 1.0)
    return scale, core


def block_fractions(centre, width_scale, core_fraction, cfg):
    """Fraction of each photon's energy in each block, (N, n, n).

    A Gaussian of width σ centred at u0 puts Φ((b - u0)/σ) - Φ((a - u0)/σ)
    of its energy between a and b; in 2D the u and v factors multiply.
    Energy beyond the outer edges is lost (lateral leakage).
    """
    g = cfg["geometry"]
    n_blocks, size = g["blocks_per_side"], g["block_size_cm"]
    edges = (np.arange(n_blocks + 1) - 0.5 * n_blocks) * size
    shape = shower_shape(cfg)

    def strip(coordinate, sigma):
        cdf = ndtr((edges[None, :] - coordinate[:, None]) / sigma[:, None])
        return np.diff(cdf, axis=1)

    total = 0.0
    for fraction, sigma in ((core_fraction, shape.core_sigma_cm * width_scale),
                            (1.0 - core_fraction, shape.halo_sigma_cm * width_scale)):
        in_u, in_v = strip(centre[:, 0], sigma), strip(centre[:, 1], sigma)
        total = total + fraction[:, None, None] * in_v[:, :, None] * in_u[:, None, :]
    return total


def shower_deposits(photons, rng, cfg):
    """True energy deposited in each block by all photons of each event, (N, n, n)."""
    n_blocks = cfg["geometry"]["blocks_per_side"]
    deposits = np.zeros((len(photons[0].energy), n_blocks, n_blocks))
    for hits in photons:
        depositing = hits.on_array & ~hits.converted
        energy = np.where(depositing, measured_energy(hits.energy, rng, cfg), 0.0)
        scale, core = shape_variations(len(energy), rng, cfg)
        centre = np.where(depositing[:, None], shower_centres(hits, cfg), 0.0)
        deposits += energy[:, None, None] * block_fractions(centre, scale, core, cfg)
    return deposits


def make_gains(rng, cfg):
    """Fixed per-block gain errors, drawn once per detector configuration (D-07)."""
    n_blocks = cfg["geometry"]["blocks_per_side"]
    return 1.0 + cfg["detector"]["gain_error"] * rng.standard_normal((n_blocks, n_blocks))


def readout(deposits, rng, cfg, gains=None):
    """Apply gains, add electronic noise, and zero blocks below threshold."""
    d = cfg["detector"]
    gains = np.ones(deposits.shape[1:]) if gains is None else gains
    signal = deposits * gains + d["noise_gev"] * rng.standard_normal(deposits.shape)
    return np.where(signal >= d["threshold_noise_sigmas"] * d["noise_gev"], signal, 0.0)


def array_response(photons, rng, cfg, gains=None):
    """Block energies (N, n, n) seen by the array for a list of PhotonHits."""
    return readout(shower_deposits(photons, rng, cfg), rng, cfg, gains)
