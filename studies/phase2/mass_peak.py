"""Phase 2 mass-peak study (Q1): log weighting vs two-shower fit.

Full chain: generator → decay → transport → detector → reconstruction.
  (a) two-cluster invariant mass, physics-mode π⁰s (toy spectrum):
      raw, calibrated log weighting (D-19), two-shower fit (D-21)
  (b) peak position and width vs π⁰ energy (flat mode), both methods
  (c) selection efficiency vs π⁰ energy: accepted → two clusters → both fiducial
Peak position and width come from an iterative Gaussian fit to the core
(±1.5σ), which ignores the non-Gaussian tails.

The remaining energy dependence of the peak is a documented limitation
(D-21): every resolved π⁰ in a 4 × 4 array has a photon in an edge block,
where the position within the block cannot be measured.

Outputs: studies/phase2/results/{mass_peak.png, mass_vs_energy.csv}
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

from pi0resolve.config import load_config
from pi0resolve.constants import PI0_MASS
from pi0resolve.decay import decay_pi0
from pi0resolve.detector import array_response
from pi0resolve.generator import generate_pi0s
from pi0resolve.reconstruction import find_clusters, two_cluster_mass
from pi0resolve.showerfit import fitted_pair_mass
from pi0resolve.transport import event_status, transport_photons

MATERIAL, FRACTION = "carbon", 0.02
N_PHYSICS = 2_000_000
N_FLAT = 1_500_000
RESULTS = Path(__file__).resolve().parent / "results"
METHODS = (("log weighting", "#F72585"), ("two-shower fit", "#4CC9F0"))


def run_chain(n, rng, cfg, mode):
    sample = generate_pi0s(n, rng, cfg, MATERIAL, FRACTION, mode)
    gammas = decay_pi0(sample.p4, rng)
    hits = [transport_photons(g, sample.vertex, rng, cfg, MATERIAL, FRACTION) for g in gammas]
    _, accepted = event_status(sample.is_dalitz, hits)
    blocks = array_response(hits, rng, cfg)
    return sample.p4[:, 0], accepted, find_clusters(blocks, cfg), blocks


def masses(clusters, blocks, cfg):
    """{method: (mass, selected)} for both reconstruction methods."""
    return {"log weighting": two_cluster_mass(clusters, cfg),
            "two-shower fit": fitted_pair_mass(clusters, blocks, cfg)}


def gaussian(x, amplitude, mean, sigma):
    return amplitude * np.exp(-0.5 * ((x - mean) / sigma) ** 2)


def fit_peak(mass, iterations=5):
    """Iterative Gaussian fit to the core: refit within ±1.5σ of the last result."""
    mean, sigma = np.median(mass), np.subtract(*np.percentile(mass, [75, 25])) / 1.349
    for _ in range(iterations):
        window = mass[np.abs(mass - mean) < 1.5 * sigma]
        counts, edges = np.histogram(window, bins=40)
        centres = 0.5 * (edges[1:] + edges[:-1])
        (_, mean, sigma), cov = curve_fit(gaussian, centres, counts, p0=(counts.max(), mean, sigma))
        sigma = abs(sigma)
    return mean, sigma, np.sqrt(cov[1, 1])


def main():
    cfg = load_config()
    rng = np.random.default_rng(cfg["seed"])
    RESULTS.mkdir(parents=True, exist_ok=True)
    fig, (ax_a, ax_b, ax_c) = plt.subplots(1, 3, figsize=(18, 4.9), constrained_layout=True)

    # (a) physics mode
    energy, accepted, clusters, blocks = run_chain(N_PHYSICS, rng, cfg, "physics")
    results = masses(clusters, blocks, cfg)
    raw, raw_selected = two_cluster_mass(clusters, cfg, calibrate=False)
    bins = np.linspace(0.0, 0.30, 121)
    print(f"physics mode: {N_PHYSICS:,} π⁰ generated")
    curves = [("raw (uncalibrated)", "#8A97B4", raw, raw_selected)]
    curves += [(name, colour, *results[name]) for name, colour in METHODS]
    for label, colour, mass, selected in curves:
        m = mass[selected & accepted]
        mean, sigma, error = fit_peak(m)
        ax_a.hist(m, bins=bins, histtype="step", lw=2, color=colour,
                  label=f"{label}: {mean * 1000:.1f} ± {error * 1000:.1f} MeV, σ {sigma * 1000:.1f}")
        print(f"  {label:20s}: peak {mean * 1000:.1f} ± {error * 1000:.1f} MeV "
              f"({(mean / PI0_MASS - 1) * 100:+.1f} %), σ = {sigma * 1000:.1f} MeV, {len(m):,} events")
    ax_a.axvline(PI0_MASS, color="#FFB703", ls="--", label="π⁰ mass 135.0 MeV")
    ax_a.set(xlabel=r"two-photon mass $m_{\gamma\gamma}$ (GeV)", ylabel="events per bin",
             title="(a) Reconstructed π⁰ peak (toy spectrum, C 2 % λ_I)")
    ax_a.legend(fontsize=8)

    # (b), (c) flat mode, per energy bin
    energy, accepted, clusters, blocks = run_chain(N_FLAT, rng, cfg, "flat")
    results = masses(clusters, blocks, cfg)
    edges = np.arange(cfg["pi0"]["energy_min_gev"], cfg["pi0"]["energy_max_gev"] + 1e-9, 0.5)
    centres = 0.5 * (edges[1:] + edges[:-1])
    header = ["energy_gev", "accepted", "two_clusters"]
    table = [centres,
             [accepted[(energy >= lo) & (energy < hi)].mean() for lo, hi in zip(edges[:-1], edges[1:])],
             [np.mean(accepted[(energy >= lo) & (energy < hi)] & (clusters.count[(energy >= lo) & (energy < hi)] == 2))
              for lo, hi in zip(edges[:-1], edges[1:])]]
    print("per energy bin, peak / sigma in MeV:")
    for (name, colour), offset in zip(METHODS, (-0.06, 0.06)):
        mass, selected = results[name]
        peak, width, efficiency = [], [], []
        for lo, hi in zip(edges[:-1], edges[1:]):
            in_bin = (energy >= lo) & (energy < hi)
            good = in_bin & accepted & selected
            efficiency.append(good.sum() / max(in_bin.sum(), 1))
            mean, sigma = (fit_peak(mass[good])[:2] if good.sum() >= 300 else (np.nan, np.nan))
            peak.append(mean)
            width.append(sigma)
        peak, width = np.array(peak), np.array(width)
        ax_b.errorbar(centres + offset, peak * 1000, yerr=width * 1000, fmt="o", color=colour, capsize=3,
                      label=f"{name} (peak ± σ)")
        ax_c.plot(centres, efficiency, "o-", color=colour, label=f"… both fiducial ({name})")
        key = name.replace(" ", "_").replace("-", "_")
        header += [f"selected_{key}", f"peak_gev_{key}", f"sigma_gev_{key}"]
        table += [efficiency, peak, width]
        print(f"  {name}: " + "  ".join(f"{c:.2f}:{p * 1000:5.1f}/{w * 1000:4.1f}" for c, p, w in zip(centres, peak, width)))
    np.savetxt(RESULTS / "mass_vs_energy.csv", np.column_stack(table), delimiter=",", comments="",
               fmt="%.5f", header=",".join(header))

    ax_b.axhline(PI0_MASS * 1000, color="#FFB703", ls="--", label="π⁰ mass")
    ax_b.set(xlabel=r"$\pi^0$ energy (GeV)", ylabel="reconstructed mass (MeV)", ylim=(60, 210),
             title="(b) Peak vs energy: edge-block limitation (D-21)")
    ax_b.legend(fontsize=8)
    ax_c.plot(centres, table[1], "o-", color="#8A97B4", label="both photons accepted")
    ax_c.plot(centres, table[2], "o-", color="#7B61FF", label="… and exactly two clusters")
    ax_c.set(xlabel=r"$\pi^0$ energy (GeV)", ylabel="fraction of generated π⁰",
             title="(c) Where π⁰s are lost (flat mode)", ylim=(0, None))
    ax_c.legend(fontsize=8)

    fig.suptitle(f"Phase 2 · π⁰ mass reconstruction · L = {cfg['geometry']['distance_cm']:.0f} cm, "
                 f"θ = {np.degrees(cfg['geometry']['angle_rad']):.0f}°, W₀ = {cfg['reconstruction']['log_weight_w0']}"
                 f" · seed {cfg['seed']}")
    fig.savefig(RESULTS / "mass_peak.png", dpi=150)
    print(f"wrote {RESULTS / 'mass_peak.png'}")


if __name__ == "__main__":
    main()
