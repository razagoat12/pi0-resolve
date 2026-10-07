"""Phase 3: ML position estimates vs log weighting and the two-shower fit (D-21, D-23).

A. Single photons over the whole face: position error vs true position, so
   the edge-block limitation can be compared across the three methods.
B. π⁰ pairs with two clusters: photon separation and π⁰ mass vs energy,
   all three methods on exactly the same events (log-weighted fiducial selection).

The ML models are gradient-boosted regressors on the 16 block energies
(divided by their total) plus log total energy. They are trained on one half
of the simulated events and tested on the other.

Caveat: no method can recover information the blocks do not contain. Where
the edge block hides a photon's position, an ML model can only learn the
typical position under the simulation's assumptions (shower shape, energy
and angle spectrum). Its gains there depend on those assumptions; Phase 4
tests that.

Usage:  python studies/phase3/position.py [--n-photons 300000] [--n-pi0 1500000]
Outputs: studies/phase3/results/{position.png, position_single.csv, position_pairs.csv}
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor

from pi0resolve.config import load_config
from pi0resolve.constants import PI0_MASS
from pi0resolve.decay import decay_pi0
from pi0resolve.detector import array_response, shower_centres
from pi0resolve.generator import array_axis, generate_pi0s
from pi0resolve.reconstruction import correct_energy, find_clusters, fiducial, leading_pair, pair_mass
from pi0resolve.showerfit import fit_pairs, fit_showers
from pi0resolve.reconstruction import Clusters
from pi0resolve.transport import event_status, face_axes, transport_photons

RESULTS = Path(__file__).resolve().parent / "results"
MATERIAL, FRACTION = "carbon", 0.02
U_EDGES = np.arange(0.0, 20.0001, 1.0)
E_EDGES = np.arange(1.0, 5.0001, 0.5)


def block_inputs(blocks):
    flat = blocks.reshape(len(blocks), -1)
    total = flat.sum(axis=1)
    return np.column_stack((flat / total[:, None], np.log(total)))


def regressor():
    return HistGradientBoostingRegressor(learning_rate=0.1, max_iter=400, random_state=0)


def halves(n, rng):
    order = rng.permutation(n)
    return order[: n // 2], order[n // 2:]


def single_photons(n, rng, cfg):
    g = cfg["geometry"]
    half = 0.5 * g["blocks_per_side"] * g["block_size_cm"]
    uv = rng.uniform(-half, half, (n, 2))
    energy = rng.uniform(0.3, 5.0, n)
    e_u, e_v = face_axes(cfg)
    points = g["distance_cm"] * array_axis(cfg) + uv[:, :1] * e_u + uv[:, 1:] * e_v
    direction = points / np.linalg.norm(points, axis=1)[:, None]
    hits = transport_photons(np.column_stack((energy, energy[:, None] * direction)), np.zeros((n, 3)),
                             rng, cfg, MATERIAL, FRACTION)
    blocks = array_response([hits], rng, cfg)
    clusters = find_clusters(blocks, cfg)
    keep = hits.on_array & ~hits.converted & (clusters.count == 1)
    lead = np.argmax(clusters.energy, axis=1)
    rows = np.arange(n)
    return (blocks[keep], clusters.energy[rows, lead][keep], clusters.position[rows, lead][keep],
            shower_centres(hits, cfg)[keep], hits.energy[keep])


def part_a(cfg, rng, n):
    blocks, energy, logw, truth, true_energy = single_photons(n, rng, cfg)
    train, test = halves(len(blocks), rng)
    x = block_inputs(blocks)
    ml = np.column_stack([regressor().fit(x[train], truth[train, k]).predict(x[test]) for k in (0, 1)])
    fitted, _ = fit_showers(blocks[test], np.column_stack((energy[test], logw[test])), cfg)
    methods = {"log weighting": logw[test], "two-shower fit": fitted[:, 1:], "ML (boosted trees)": ml}

    # Fold u and v together: distance from the array centre along each axis
    true_abs = np.abs(truth[test]).ravel()
    rows = []
    for name, estimate in methods.items():
        signed = (np.sign(truth[test]) * (estimate - truth[test])).ravel()   # + means outward
        bias = [np.median(signed[(true_abs >= lo) & (true_abs < hi)]) for lo, hi in zip(U_EDGES[:-1], U_EDGES[1:])]
        rms = np.sqrt(np.mean(np.sum((estimate - truth[test]) ** 2, axis=1)))
        inner = np.all(np.abs(truth[test]) < 15.0, axis=1)
        rms_inner = np.sqrt(np.mean(np.sum((estimate[inner] - truth[test][inner]) ** 2, axis=1)))
        rows.append((name, rms, rms_inner, np.array(bias)))
        print(f"  {name:20s}: position RMS {rms:.2f} cm (inner |u|,|v| < 15 cm: {rms_inner:.2f} cm)")
    return rows


def part_b(cfg, rng, n):
    sample = generate_pi0s(n, rng, cfg, MATERIAL, FRACTION, "flat")
    gammas = decay_pi0(sample.p4, rng)
    hits = [transport_photons(g, sample.vertex, rng, cfg, MATERIAL, FRACTION) for g in gammas]
    _, accepted = event_status(sample.is_dalitz, hits)
    blocks = array_response(hits, rng, cfg)
    clusters = find_clusters(blocks, cfg)
    energy, position = leading_pair(clusters, cfg)                 # calibrated energies, log-weighted positions
    use = accepted & (clusters.count == 2) & np.all(fiducial(position, cfg), axis=1)
    blocks, energy, position = blocks[use], energy[use], position[use]
    pi0_energy = sample.p4[use, 0]
    true_sep = np.linalg.norm(shower_centres(hits[0], cfg)[use] - shower_centres(hits[1], cfg)[use], axis=1)

    train, test = halves(use.sum(), rng)
    ml_sep = regressor().fit(block_inputs(blocks[train]), true_sep[train]).predict(block_inputs(blocks[test]))

    params, _ = fit_pairs(Clusters(clusters.energy[use][test], clusters.position[use][test]), blocks[test], cfg)
    fit_pos = np.stack((params[:, 1:3], params[:, 4:6]), axis=1)
    fit_energy = params[:, [0, 3]]

    e, p = energy[test], position[test]
    midpoint = p.mean(axis=1, keepdims=True)
    logw_sep = np.linalg.norm(p[:, 0] - p[:, 1], axis=1)
    ml_pos = midpoint + (p - midpoint) * (ml_sep / logw_sep)[:, None, None]
    estimates = {
        "log weighting": (pair_mass(e[:, 0], p[:, 0], e[:, 1], p[:, 1], cfg), logw_sep),
        "two-shower fit": (pair_mass(fit_energy[:, 0], fit_pos[:, 0], fit_energy[:, 1], fit_pos[:, 1], cfg),
                           np.linalg.norm(fit_pos[:, 0] - fit_pos[:, 1], axis=1)),
        "ML (boosted trees)": (pair_mass(e[:, 0], ml_pos[:, 0], e[:, 1], ml_pos[:, 1], cfg), ml_sep),
    }
    rows = []
    for name, (mass, sep) in estimates.items():
        peak = [np.median(mass[(pi0_energy[test] >= lo) & (pi0_energy[test] < hi)]) for lo, hi in zip(E_EDGES[:-1], E_EDGES[1:])]
        ratio = [np.median((sep / true_sep[test])[(pi0_energy[test] >= lo) & (pi0_energy[test] < hi)])
                 for lo, hi in zip(E_EDGES[:-1], E_EDGES[1:])]
        rows.append((name, np.array(peak), np.array(ratio), np.median(mass)))
        print(f"  {name:20s}: median mass {np.median(mass) * 1000:6.1f} MeV; by energy "
              + " ".join(f"{m * 1000:5.1f}" for m in peak))
    print(f"  ({len(test):,} test events, the same for all three methods)")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-photons", type=int, default=300_000)
    parser.add_argument("--n-pi0", type=int, default=1_500_000)
    args = parser.parse_args()
    cfg = load_config()
    rng = np.random.default_rng(cfg["seed"] + 3)
    RESULTS.mkdir(parents=True, exist_ok=True)

    print("A. single photons")
    rows_a = part_a(cfg, rng, args.n_photons)
    print("B. π⁰ pairs (two clusters)")
    rows_b = part_b(cfg, rng, args.n_pi0)

    u_centres = 0.5 * (U_EDGES[1:] + U_EDGES[:-1])
    e_centres = 0.5 * (E_EDGES[1:] + E_EDGES[:-1])
    np.savetxt(RESULTS / "position_single.csv", np.column_stack([u_centres] + [r[3] for r in rows_a]),
               delimiter=",", comments="", fmt="%.4f", encoding="utf-8",
               header="true_distance_from_centre_cm," + ",".join(f"outward_bias_cm_{r[0]}" for r in rows_a))
    np.savetxt(RESULTS / "position_pairs.csv",
               np.column_stack([e_centres] + [r[1] for r in rows_b] + [r[2] for r in rows_b]),
               delimiter=",", comments="", fmt="%.5f", encoding="utf-8",
               header="pi0_energy_gev," + ",".join(f"mass_gev_{r[0]}" for r in rows_b) + ","
               + ",".join(f"separation_ratio_{r[0]}" for r in rows_b))

    colours = ("#F72585", "#4CC9F0", "#7B61FF")
    fig, (ax_a, ax_b, ax_c) = plt.subplots(1, 3, figsize=(18, 4.9), constrained_layout=True)
    for (name, rms, rms_inner, bias), colour in zip(rows_a, colours):
        ax_a.plot(u_centres, bias, "o-", ms=3, color=colour, label=f"{name} (RMS {rms:.2f} cm)")
    ax_a.axhline(0, color="#8A97B4", lw=1)
    ax_a.axvspan(15, 20, color="#FFB703", alpha=0.12, label="outer half of edge block")
    ax_a.set(xlabel="true distance from array centre (cm)", ylabel="median position error, outward + (cm)",
             title="(a) Single photons: the edge-block limitation")
    ax_a.legend(fontsize=8)
    for (name, peak, ratio, _), colour in zip(rows_b, colours):
        ax_b.plot(e_centres, ratio, "o-", color=colour, label=name)
        ax_c.plot(e_centres, peak * 1000, "o-", color=colour, label=name)
    ax_b.axhline(1.0, color="#FFB703", ls="--")
    ax_b.set(xlabel=r"$\pi^0$ energy (GeV)", ylabel="reconstructed / true separation (median)",
             title="(b) π⁰ pairs: photon separation")
    ax_b.legend(fontsize=8)
    ax_c.axhline(PI0_MASS * 1000, color="#FFB703", ls="--", label="π⁰ mass")
    ax_c.set(xlabel=r"$\pi^0$ energy (GeV)", ylabel="median reconstructed mass (MeV)",
             title="(c) π⁰ pairs: mass, same events for all methods")
    ax_c.legend(fontsize=8)
    fig.suptitle(f"Phase 3 · position methods compared · seed {cfg['seed'] + 3}")
    fig.savefig(RESULTS / "position.png", dpi=150)
    print(f"wrote {RESULTS / 'position.png'}")


if __name__ == "__main__":
    main()
