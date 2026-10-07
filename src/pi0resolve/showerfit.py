"""Shower fit: explain all block energies with K photon showers (D-21).

Each shower has the fixed average shape of D-17 (no fluctuations), so it is
described by three numbers: energy E and shower-centre position (u, v). The
fit adjusts these 3K numbers so the predicted blocks match the measured ones,
minimising

    χ² = Σ_blocks ((measured - predicted) / σ)²

Block uncertainty (D-21): σ² = noise² + s² · e + (f · e)², from the predicted
energy e (not the measured one, which would bias energies low): electronic noise, the stochastic resolution term s (6.3 %/√E), and a
term f for shower-shape fluctuations. Blocks read as zero (below threshold)
only count if the prediction rises above the threshold.

Because overlapping showers are modelled together, the energy shared between
two close photons is attributed correctly instead of dragging their positions
toward each other (the problem found in D-19 and D-20). Energy leaking off the
array is part of the model, so fitted energies are total photon energies.

Minimisation: Levenberg–Marquardt, run for all events at once with NumPy.
Parameters are arrays (N, 3K) ordered [E1, u1, v1, E2, u2, v2, ...].
"""

import numpy as np

from .detector import block_fractions, shower_shape

MIN_ENERGY = 1e-3               # GeV
MAX_ENERGY_FACTOR = 3.0         # a shower may not exceed 3× the energy measured in the whole array
# Shower centres may sit at most `position_margin_cm` beyond the array edge.
# Unlimited, about 1 fit in 5 ran away (a large shower far off the face can
# imitate the faint tail of a real one); limited to the face itself, showers
# truly beyond the edge were pulled onto it and passed the fiducial cut,
# biasing separations low (see D-21).


def predicted_blocks(params, cfg):
    """Block energies (N, n²) predicted by K average-shape showers."""
    n_events, n_params = params.shape
    core = np.full(n_events, shower_shape(cfg).core_fraction)
    scale = np.ones(n_events)
    total = 0.0
    for k in range(n_params // 3):
        energy, centre = params[:, 3 * k], params[:, 3 * k + 1:3 * k + 3]
        total = total + energy[:, None] * block_fractions(centre, scale, core, cfg).reshape(n_events, -1)
    return total


def block_sigma(expected, cfg):
    """Block uncertainty for an expected block energy (GeV)."""
    d, f = cfg["detector"], cfg["showerfit"]["shape_term"]
    e = np.maximum(expected, 0.0)
    return np.sqrt(d["noise_gev"] ** 2 + d["resolution_stochastic"] ** 2 * e + (f * e) ** 2)


def _residuals(params, measured, threshold, cfg):
    """Normalised residuals. σ comes from the *predicted* energies: taking it
    from the measured ones would give blocks that fluctuated low too much
    weight and pull fitted energies down (Neyman bias)."""
    predicted = predicted_blocks(params, cfg)
    zero = measured <= 0.0
    difference = np.where(zero, -np.maximum(predicted - threshold, 0.0), measured - predicted)
    return difference / block_sigma(predicted, cfg)


def _clip(params, max_energy, half_width):
    params = params.copy()
    params[:, 0::3] = np.clip(params[:, 0::3], MIN_ENERGY, max_energy[:, None])
    params[:, 1::3] = np.clip(params[:, 1::3], -half_width, half_width)
    params[:, 2::3] = np.clip(params[:, 2::3], -half_width, half_width)
    return params


def fit_showers(blocks, start, cfg):
    """Fit K showers to block energies (N, n, n), starting from `start` (N, 3K).

    Returns (params (N, 3K), chi2 (N,)). Deterministic: no random numbers.
    """
    d = cfg["detector"]
    n_events, n_params = start.shape
    measured = blocks.reshape(n_events, -1)
    threshold = d["threshold_noise_sigmas"] * d["noise_gev"]

    max_energy = np.maximum(MAX_ENERGY_FACTOR * np.maximum(measured, 0.0).sum(axis=1), 10 * MIN_ENERGY)
    half_width = (0.5 * cfg["geometry"]["blocks_per_side"] * cfg["geometry"]["block_size_cm"]
                  + cfg["showerfit"]["position_margin_cm"])
    params = _clip(start.astype(float), max_energy, half_width)
    residual = _residuals(params, measured, threshold, cfg)
    chi2 = np.sum(residual**2, axis=1)
    damping = np.full(n_events, 1e-2)
    eye = np.eye(n_params)

    for _ in range(cfg["showerfit"]["iterations"]):
        # Jacobian of the residuals by forward differences, (N, B, P)
        steps = np.where(np.arange(n_params) % 3 == 0, 1e-4 + 1e-3 * np.abs(params), 1e-3)
        jacobian = np.empty(residual.shape + (n_params,))
        for j in range(n_params):
            shifted = params.copy()
            shifted[:, j] += steps[:, j]
            jacobian[:, :, j] = (_residuals(shifted, measured, threshold, cfg) - residual) / steps[:, j, None]

        jtj = np.einsum("nbi,nbj->nij", jacobian, jacobian)
        jtr = np.einsum("nbi,nb->ni", jacobian, residual)
        diagonal = np.einsum("nii->ni", jtj)
        system = jtj + (damping[:, None] * diagonal)[:, :, None] * eye + 1e-9 * eye
        delta = np.linalg.solve(system, -jtr[:, :, None])[:, :, 0]

        trial = _clip(params + delta, max_energy, half_width)
        trial_residual = _residuals(trial, measured, threshold, cfg)
        trial_chi2 = np.sum(trial_residual**2, axis=1)
        better = trial_chi2 < chi2
        params[better], residual[better], chi2[better] = trial[better], trial_residual[better], trial_chi2[better]
        damping = np.where(better, damping * 0.3, damping * 10.0)
    return params, chi2


def fitted_pair_mass(clusters, blocks, cfg):
    """π⁰ mass from the two-shower fit, for events with exactly two clusters.

    Selected when both fitted shower centres pass the fiducial cut. Fitted
    energies are used as they are (the model already includes leakage).
    Returns (mass (N,), selected (N,) bool), NaN where not selected.
    """
    from .reconstruction import Clusters, fiducial, pair_mass

    use = np.flatnonzero(clusters.count == 2)
    mass = np.full(len(clusters.energy), np.nan)
    selected = np.zeros(len(clusters.energy), dtype=bool)
    if len(use) == 0:
        return mass, selected
    params, _ = fit_pairs(Clusters(clusters.energy[use], clusters.position[use]), blocks[use], cfg)
    position = np.stack((params[:, 1:3], params[:, 4:6]), axis=1)
    ok = np.all(fiducial(position, cfg), axis=1)
    mass[use[ok]] = pair_mass(params[ok, 0], position[ok, 0], params[ok, 3], position[ok, 1], cfg)
    selected[use[ok]] = True
    return mass, selected


def fit_pairs(clusters, blocks, cfg):
    """Two-shower fit for every event, from several starting guesses (D-21).

    The χ² surface has local minima (a shower can settle on the wrong side of a
    block), so each event is fitted from three starts built from its two most
    energetic clusters, and the best fit is kept:
      1. log-weighted cluster positions, 2. plain energy-weighted positions,
      3. the centres of the two seed blocks;
    always with the raw cluster energies. Events with fewer than two clusters
    get NaN results. Returns (params (N, 6), chi2 (N,)).
    """
    from .reconstruction import block_centres, find_clusters

    order = np.argsort(-clusters.energy, axis=1)[:, :2]
    rows = np.arange(len(order))[:, None]
    has_two = clusters.count >= 2
    params = np.full((len(order), 6), np.nan)
    chi2 = np.full(len(order), np.nan)
    if not np.any(has_two):
        return params, chi2

    energy = clusters.energy[rows, order][has_two]
    plain = find_clusters(blocks[has_two], cfg, log_weighting=False).position
    starts = [
        clusters.position[rows, order][has_two],
        plain[np.arange(len(energy))[:, None], order[has_two]],
        block_centres(cfg)[order[has_two]],
    ]
    best_chi2 = np.full(len(energy), np.inf)
    best = np.empty((len(energy), 6))
    for position in starts:
        start = np.column_stack((energy[:, 0], position[:, 0], energy[:, 1], position[:, 1]))
        fitted, fit_chi2 = fit_showers(blocks[has_two], start, cfg)
        better = fit_chi2 < best_chi2
        best[better], best_chi2[better] = fitted[better], fit_chi2[better]
    params[has_two], chi2[has_two] = best, best_chi2
    return params, chi2


# Starting offsets (cm) for the second shower when splitting one cluster in two:
# the two showers start symmetrically about the cluster position, along u, v
# and both diagonals.
SPLIT_OFFSETS = ((3.0, 0.0), (0.0, 3.0), (2.1, 2.1), (2.1, -2.1))


def merged_score(blocks, energy, position, cfg):
    """Fit-based classifier score for single clusters (D-22).

    Δχ² = χ²(best one-shower fit) - χ²(best two-shower fit). A merged π⁰ is
    explained much better by two showers; a single photon is not. The
    two-shower fit starts from the cluster split in half, with the halves
    offset along each direction in SPLIT_OFFSETS; the best result is kept.
    Returns (delta_chi2, chi2_one, chi2_two), each (N,).
    """
    _, chi2_one = fit_showers(blocks, np.column_stack((energy, position)), cfg)
    chi2_two = np.full(len(energy), np.inf)
    for du, dv in SPLIT_OFFSETS:
        offset = np.array([du, dv])
        start = np.column_stack((0.5 * energy, position + offset, 0.5 * energy, position - offset))
        _, chi2 = fit_showers(blocks, start, cfg)
        chi2_two = np.minimum(chi2_two, chi2)
    return chi2_one - chi2_two, chi2_one, chi2_two
