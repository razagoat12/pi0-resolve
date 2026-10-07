"""Phase 2 calibration study (D-18, D-19).

1. Position (W0): scan the log-weighting parameter on simulated π⁰ pairs and
   choose the W0 at which reconstructed photon separations match the true
   separations (median ratio = 1). The π⁰ mass is never used to choose W0.
   Single-photon position error is recorded too: it prefers a larger W0, but
   that W0 pulls the two showers of a pair toward each other (see D-19).
2. Position (D-20): median true shower coordinate against reconstructed
   coordinate for single photons over the whole face, written to
   configs/position_calibration.csv; it undoes the pull toward block centres.
3. Energy: measure the median cluster energy for single photons of known
   energy, selected by corrected position like the analysis, and write
   configs/energy_calibration.csv, which reconstruction inverts.

Outputs: studies/phase2/results/{w0_scan.csv, calibration.png}
"""

import copy
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from pi0resolve.config import load_config, repo_path
from pi0resolve.decay import decay_pi0
from pi0resolve.detector import array_response, shower_centres
from pi0resolve.generator import array_axis, generate_pi0s
from pi0resolve.reconstruction import _calibration_table, correct_position, find_clusters, fiducial, two_cluster_mass
from pi0resolve.transport import event_status, face_axes, transport_photons

N_PAIRS = 400_000
N_PHOTONS = 400_000
MATERIAL, FRACTION = "carbon", 0.02
ENERGY_RANGE = (0.05, 6.0)       # GeV, wider than any π⁰ photon in D-03
W0_GRID = np.round(np.arange(2.0, 6.01, 0.25), 2)
CALIBRATION_BINS = np.arange(0.05, 6.0001, 0.10)
MIN_EFFICIENCY = 0.95             # fraction of photons that must form a cluster
POSITION_BINS = np.arange(-20.0, 20.0001, 0.25)   # cm, reconstructed coordinate
RESULTS = Path(__file__).resolve().parent / "results"


def with_w0(cfg, w0):
    trial = copy.deepcopy(cfg)
    trial["reconstruction"]["log_weight_w0"] = float(w0)
    return trial


def single_photons(n, rng, cfg):
    """Photons aimed from the target centre at uniform points over the whole face.

    The analysis selects clusters by their *reconstructed* position, so photons
    that truly land near the edge but are reconstructed inside the fiducial
    region (and leak energy) must be in the calibration sample too.
    """
    g = cfg["geometry"]
    half = 0.5 * g["blocks_per_side"] * g["block_size_cm"]
    uv = rng.uniform(-half, half, (n, 2))
    energy = rng.uniform(*ENERGY_RANGE, n)
    e_u, e_v = face_axes(cfg)
    points = g["distance_cm"] * array_axis(cfg) + uv[:, :1] * e_u + uv[:, 1:] * e_v
    direction = points / np.linalg.norm(points, axis=1)[:, None]
    p4 = np.column_stack((energy, energy[:, None] * direction))
    return transport_photons(p4, np.zeros((n, 3)), rng, cfg, MATERIAL, FRACTION)


def leading_cluster(blocks, cfg):
    clusters = find_clusters(blocks, cfg)
    lead = np.argmax(clusters.energy, axis=1)
    rows = np.arange(len(lead))
    return clusters.energy[rows, lead], clusters.position[rows, lead]


def scan_w0(cfg, rng):
    """Median reco/true photon separation in π⁰ pairs, and single-photon position RMS."""
    sample = generate_pi0s(N_PAIRS, rng, cfg, MATERIAL, FRACTION, "flat")
    gammas = decay_pi0(sample.p4, rng)
    pair_hits = [transport_photons(g, sample.vertex, rng, cfg, MATERIAL, FRACTION) for g in gammas]
    _, accepted = event_status(sample.is_dalitz, pair_hits)
    pair_blocks = array_response(pair_hits, rng, cfg)
    true_sep = np.linalg.norm(shower_centres(pair_hits[0], cfg) - shower_centres(pair_hits[1], cfg), axis=1)

    photon_hits = single_photons(N_PHOTONS, rng, cfg)
    photon_blocks = array_response([photon_hits], rng, cfg)
    photon_truth = shower_centres(photon_hits, cfg)
    usable = photon_hits.on_array & ~photon_hits.converted

    ratio, rms = [], []
    for w0 in W0_GRID:
        trial = with_w0(cfg, w0)
        clusters = find_clusters(pair_blocks, trial)
        _, selected = two_cluster_mass(clusters, trial, calibrate=False)
        order = np.argsort(-clusters.energy, axis=1)[:, :2]
        position = clusters.position[np.arange(len(order))[:, None], order]
        reco_sep = np.linalg.norm(position[:, 0] - position[:, 1], axis=1)
        ok = selected & accepted
        ratio.append(np.median(reco_sep[ok] / true_sep[ok]))

        energy, position = leading_cluster(photon_blocks, trial)
        good = usable & (energy > 0) & fiducial(position, trial)
        rms.append(np.sqrt(np.mean(np.sum((position[good] - photon_truth[good]) ** 2, axis=1))))
    ratio, rms = np.array(ratio), np.array(rms)
    # Separation ratio falls as W0 grows: interpolate where it crosses 1
    chosen = float(np.interp(1.0, ratio[::-1], W0_GRID[::-1]))
    return ratio, rms, round(chosen * 4) / 4      # round to the 0.25 grid


def position_calibration(cfg, rng):
    """Median true shower coordinate in bins of reconstructed coordinate (u and v pooled).

    Returns the table and the same table built separately for soft (< 0.7 GeV)
    and hard (> 2 GeV) photons, to check whether one table can serve all energies.
    """
    hits = single_photons(N_PHOTONS, rng, cfg)
    blocks = array_response([hits], rng, cfg)
    energy, position = leading_cluster(blocks, cfg)
    ok = hits.on_array & ~hits.converted & (energy > 0)
    reco = position[ok].ravel()
    true = shower_centres(hits, cfg)[ok].ravel()
    photon_energy = np.repeat(hits.energy[ok], 2)
    centres = 0.5 * (POSITION_BINS[1:] + POSITION_BINS[:-1])

    def table(mask):
        index = np.digitize(reco[mask], POSITION_BINS) - 1
        return np.array([np.median(true[mask][index == i]) if np.any(index == i) else np.nan
                         for i in range(len(centres))])

    median_true = table(np.ones_like(reco, dtype=bool))
    filled = ~np.isnan(median_true)
    soft, hard = table(photon_energy < 0.7), table(photon_energy > 2.0)
    return np.column_stack((centres[filled], median_true[filled])), centres, soft, hard


def energy_calibration(cfg, rng):
    hits = single_photons(N_PHOTONS, rng, cfg)
    blocks = array_response([hits], rng, cfg)
    energy, position = leading_cluster(blocks, cfg)
    position = correct_position(position, cfg)      # same order as the analysis: positions first
    usable = hits.on_array & ~hits.converted
    ok = usable & (energy > 0) & fiducial(position, cfg)
    centres = 0.5 * (CALIBRATION_BINS[1:] + CALIBRATION_BINS[:-1])
    n_bins = len(centres)

    # Near the 100 MeV seed threshold only upward fluctuations form a cluster,
    # so the median there is biased high and cannot be inverted. Keep bins
    # where at least MIN_EFFICIENCY of photons aimed well inside the array form one.
    aimed_inside = usable & fiducial(shower_centres(hits, cfg), cfg)
    all_index = np.digitize(hits.energy, CALIBRATION_BINS) - 1
    in_range = (all_index >= 0) & (all_index < n_bins)
    found = np.bincount(all_index[aimed_inside & in_range & (energy > 0)], minlength=n_bins)[:n_bins]
    total = np.bincount(all_index[aimed_inside & in_range], minlength=n_bins)[:n_bins]
    efficiency = found / np.maximum(total, 1)

    true_e, reco_e = hits.energy[ok], energy[ok]
    index = np.digitize(true_e, CALIBRATION_BINS) - 1
    counts = np.bincount(index[(index >= 0) & (index < n_bins)], minlength=n_bins)[:n_bins]
    median_reco = np.array([np.median(reco_e[index == i]) if counts[i] else np.nan for i in range(n_bins)])
    filled = (counts >= 200) & (efficiency >= MIN_EFFICIENCY)
    first = np.argmax(filled)      # lowest usable bin
    print(f"calibration starts at {centres[first]:.2f} GeV (cluster efficiency {efficiency[first]:.1%})")
    table = np.column_stack((centres[filled], median_reco[filled]))
    if np.any(np.diff(table[:, 1]) <= 0):
        raise RuntimeError("energy response is not monotonic; cannot invert it")
    return table


def main():
    cfg = load_config()
    rng = np.random.default_rng(cfg["seed"])
    RESULTS.mkdir(parents=True, exist_ok=True)

    ratio, rms, chosen = scan_w0(cfg, rng)
    np.savetxt(RESULTS / "w0_scan.csv", np.column_stack((W0_GRID, ratio, rms)), delimiter=",",
               header="w0,pair_separation_ratio,single_photon_rms_cm", comments="", fmt="%.4f")
    configured = cfg["reconstruction"]["log_weight_w0"]
    print(f"W0 for unbiased pair separation: {chosen} (configured: {configured})")
    print(f"single-photon RMS would be smallest at W0 = {W0_GRID[np.argmin(rms)]} — not used, it biases pairs")
    if chosen != configured:
        print("WARNING: set reconstruction.log_weight_w0 in configs/default.yaml to the value above and rerun")

    position_table, centres, soft, hard = position_calibration(cfg, rng)
    position_out = repo_path("configs/position_calibration.csv")   # written for study; used only if enabled
    np.savetxt(position_out, position_table, delimiter=",",
               header="reconstructed_coordinate_cm,median_true_coordinate_cm", comments="", fmt="%.4f")
    _calibration_table.cache_clear()
    both = ~np.isnan(soft) & ~np.isnan(hard) & (np.abs(centres) <= 15.0)
    print(f"wrote {position_out} ({len(position_table)} points); soft vs hard photon tables differ by "
          f"{np.sqrt(np.mean((soft[both] - hard[both]) ** 2)):.2f} cm RMS inside the fiducial region")

    table = energy_calibration(cfg, rng)
    out = repo_path(cfg["reconstruction"]["energy_calibration"])
    np.savetxt(out, table, delimiter=",", header="true_energy_gev,median_cluster_energy_gev",
               comments="", fmt="%.6f")
    print(f"wrote {out} ({len(table)} points); response at 0.5 / 1 / 4 GeV: "
          + " / ".join(f"{np.interp(e, table[:, 0], table[:, 1]) / e:.3f}" for e in (0.5, 1.0, 4.0)))

    fig, (ax_a, ax_b, ax_d, ax_c) = plt.subplots(1, 4, figsize=(22, 4.6), constrained_layout=True)
    ax_d.plot(position_table[:, 0], position_table[:, 1], color="#F72585", lw=2, label="all photons")
    ax_d.plot(centres, soft, color="#4CC9F0", lw=1, alpha=0.8, label="< 0.7 GeV")
    ax_d.plot(centres, hard, color="#7B61FF", lw=1, alpha=0.8, label="> 2 GeV")
    ax_d.plot([-20, 20], [-20, 20], color="#FFB703", lw=1, ls="--", label="no correction")
    ax_d.set(xlabel="reconstructed coordinate (cm)", ylabel="median true coordinate (cm)",
             title="(c) Position correction (S-curve inverse)", xlim=(-20, 20), ylim=(-20, 20))
    ax_d.legend(fontsize=8)
    ax_a.plot(W0_GRID, ratio, "o-", color="#F72585")
    ax_a.axhline(1.0, color="#FFB703", lw=1)
    ax_a.axvline(configured, color="#4CC9F0", ls="--", label=f"chosen W₀ = {configured}")
    ax_a.set(xlabel="log-weighting W₀", ylabel="reconstructed / true separation (median)",
             title="(a) π⁰ pairs: W₀ sets the separation bias")
    ax_a.legend()
    ax_b.plot(W0_GRID, rms, "o-", color="#7B61FF")
    ax_b.axvline(configured, color="#4CC9F0", ls="--", label=f"chosen W₀ = {configured}")
    ax_b.axvline(W0_GRID[np.argmin(rms)], color="#8A97B4", ls=":", label="single-photon optimum (biases pairs)")
    ax_b.set(xlabel="log-weighting W₀", ylabel="single-photon position error, RMS (cm)",
             title="(b) Single photons prefer larger W₀")
    ax_b.legend()
    ax_c.plot(table[:, 0], table[:, 1] / table[:, 0], "o", ms=3, color="#4CC9F0")
    ax_c.axhline(1.0, color="#FFB703", lw=1)
    ax_c.set(xlabel="true photon energy (GeV)", ylabel="median cluster energy / true energy",
             title="(d) Energy response (inverted by the calibration)", ylim=(0.8, 1.05))
    fig.savefig(RESULTS / "calibration.png", dpi=150)
    print(f"wrote {RESULTS / 'calibration.png'}")


if __name__ == "__main__":
    main()
