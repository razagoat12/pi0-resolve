"""Reconstruction: block energies → clusters → photon candidates → π⁰ mass (D-08, D-18).

Steps, all vectorised over events:
  1. Seeds: blocks above the seed threshold whose energy exceeds all 8 neighbours.
  2. Clusters: the 3 × 3 window around each seed. A block inside two windows is
     split between them in proportion to the two seed energies, so no energy
     is counted twice.
  3. Position: logarithmic weights w = max(0, W0 + ln(e_block / E_cluster))
     (Awes et al. 1992), which reduce the pull toward block centres (S-curve)
     that plain energy weighting suffers from. Plain weighting is kept for comparison.
  4. Corrections (studies/phase2/calibrate.py): positions through
     configs/position_calibration.csv (D-20), then energies through
     configs/energy_calibration.csv (D-19).
  5. Mass: m² = 2 E1 E2 (1 - cos θ12), with each photon's direction taken from
     the target centre to its shower centre at depth L + D(E) behind the face.

Blocks are indexed [event, iv, iu] as in detector.py and flattened to
b = iv * n + iu where convenient. Up to n² cluster slots per event, one per
possible seed block; unused slots have energy 0.
"""

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from .config import repo_path
from .detector import shower_depth_cm


@dataclass
class Clusters:
    energy: np.ndarray    # (N, S) GeV, 0 for empty slots; S = n² slots, one per possible seed
    position: np.ndarray  # (N, S, 2) cm on the face (u, v), NaN for empty slots

    @property
    def count(self):
        return np.count_nonzero(self.energy > 0, axis=1)


def block_centres(cfg):
    """(n², 2) face coordinates (u, v) of each block centre, in flattened order."""
    g = cfg["geometry"]
    n, size = g["blocks_per_side"], g["block_size_cm"]
    c = (np.arange(n) - 0.5 * (n - 1)) * size
    v, u = np.meshgrid(c, c, indexing="ij")
    return np.column_stack((u.ravel(), v.ravel()))


def window_matrix(cfg):
    """W[s, b] = 1 if block b lies in the window around seed block s."""
    g = cfg["geometry"]
    n, size = g["blocks_per_side"], g["block_size_cm"]
    reach = (cfg["clustering"]["window_blocks"] // 2) * size
    centres = block_centres(cfg)
    offset = np.abs(centres[:, None, :] - centres[None, :, :])
    return np.all(offset <= reach + 1e-9, axis=2).astype(float)


def find_seeds(blocks, cfg):
    """Boolean (N, n, n): above the seed threshold and higher than all 8 neighbours."""
    padded = np.pad(blocks, ((0, 0), (1, 1), (1, 1)), constant_values=-np.inf)
    n = blocks.shape[1]
    is_peak = blocks >= cfg["clustering"]["seed_threshold_gev"]
    for dv in (-1, 0, 1):
        for du in (-1, 0, 1):
            if dv == 0 and du == 0:
                continue
            neighbour = padded[:, 1 + dv:1 + dv + n, 1 + du:1 + du + n]
            is_peak &= blocks > neighbour
    return is_peak


def find_clusters(blocks, cfg, log_weighting=True):
    """Clusters for every event: energies (N, S) and positions (N, S, 2)."""
    n_events = len(blocks)
    energy_flat = blocks.reshape(n_events, -1)
    seeds = find_seeds(blocks, cfg).reshape(n_events, -1)
    seed_energy = np.where(seeds, energy_flat, 0.0)

    window = window_matrix(cfg)
    claim = seed_energy @ window                       # (N, B): total seed energy claiming each block
    with np.errstate(divide="ignore", invalid="ignore"):
        per_claim = np.where(claim > 0, energy_flat / claim, 0.0)

    centres = block_centres(cfg)
    w0 = cfg["reconstruction"]["log_weight_w0"]
    cluster_energy = np.zeros_like(seed_energy)
    position = np.full(seed_energy.shape + (2,), np.nan)
    for s in np.flatnonzero(seeds.any(axis=0)):
        present = seeds[:, s]
        share = seed_energy[present, s, None] * window[s] * per_claim[present]   # (M, B) energy given to seed s
        total = share.sum(axis=1)
        if log_weighting:
            with np.errstate(divide="ignore"):
                weight = np.maximum(0.0, w0 + np.log(share / total[:, None]))
        else:
            weight = share
        position[present, s] = (weight @ centres) / weight.sum(axis=1)[:, None]
        cluster_energy[present, s] = total
    return Clusters(cluster_energy, position)


@lru_cache(maxsize=8)
def _calibration_table(path):
    table = np.loadtxt(repo_path(path), delimiter=",", skiprows=1)
    return table[:, 0], table[:, 1]


def correct_position(position, cfg):
    """Undo the pull toward block centres (S-curve and edge effects; D-20).

    The table gives, for each reconstructed coordinate, the median true shower
    coordinate of simulated single photons. Applied to u and v separately.
    With no table configured, positions are returned unchanged.
    """
    path = cfg["reconstruction"].get("position_calibration")
    if not path:
        return position
    reco, true = _calibration_table(path)
    return np.interp(position, reco, true)


def correct_energy(energy, cfg):
    """Invert the measured energy response (D-19).

    The calibration table gives the median cluster energy for photons of known
    true energy. Reading that curve backwards maps a cluster energy to the
    true energy that typically produces it. Outside the table, the end ratios
    are used. With no table configured, energies are returned unchanged.
    """
    path = cfg["reconstruction"].get("energy_calibration")
    if not path:
        return energy
    true_e, reco_e = _calibration_table(path)
    corrected = np.interp(energy, reco_e, true_e)
    low, high = energy < reco_e[0], energy > reco_e[-1]
    corrected = np.where(low, energy * true_e[0] / reco_e[0], corrected)
    corrected = np.where(high, energy * true_e[-1] / reco_e[-1], corrected)
    return np.where(energy > 0, corrected, 0.0)


def fiducial(position, cfg):
    """True where a reconstructed centre lies at least the margin inside the array edge."""
    g = cfg["geometry"]
    limit = 0.5 * g["blocks_per_side"] * g["block_size_cm"] - cfg["reconstruction"]["fiducial_margin_cm"]
    with np.errstate(invalid="ignore"):
        return np.all(np.abs(position) <= limit, axis=-1)


def shower_points(position, energy, cfg):
    """3D shower centres in face axes (u, v, n): n = L + depth(E), measured from the target centre."""
    depth = shower_depth_cm(energy, cfg)
    return np.concatenate((position, (cfg["geometry"]["distance_cm"] + depth)[..., None]), axis=-1)


def pair_mass(energy1, position1, energy2, position2, cfg):
    """Invariant mass of two photon candidates seen from the target centre."""
    a = shower_points(position1, energy1, cfg)
    b = shower_points(position2, energy2, cfg)
    cos_theta = np.sum(a * b, axis=-1) / (np.linalg.norm(a, axis=-1) * np.linalg.norm(b, axis=-1))
    return np.sqrt(np.maximum(2.0 * energy1 * energy2 * (1.0 - cos_theta), 0.0))


def leading_pair(clusters, cfg, calibrate=True, correct_positions=None):
    """Energies (N, 2) and positions (N, 2, 2) of the two most energetic clusters.

    Positions are corrected first (D-20), so the fiducial cut and the shower
    depth see corrected values; then energies are calibrated (D-19).
    `correct_positions` defaults to `calibrate`.
    """
    correct_positions = calibrate if correct_positions is None else correct_positions
    order = np.argsort(-clusters.energy, axis=1)[:, :2]
    rows = np.arange(len(order))[:, None]
    energy = clusters.energy[rows, order]
    position = clusters.position[rows, order]
    if correct_positions:
        position = correct_position(position, cfg)
    if calibrate:
        energy = correct_energy(energy, cfg)
    return energy, position


def two_cluster_mass(clusters, cfg, calibrate=True, correct_positions=None):
    """Mass for events with exactly two clusters, both fiducial; NaN otherwise.

    Returns (mass (N,), selected (N,) bool).
    """
    energy, position = leading_pair(clusters, cfg, calibrate, correct_positions)
    selected = (clusters.count == 2) & np.all(fiducial(position, cfg), axis=1)
    mass = np.full(len(energy), np.nan)
    mass[selected] = pair_mass(energy[selected, 0], position[selected, 0],
                               energy[selected, 1], position[selected, 1], cfg)
    return mass, selected
