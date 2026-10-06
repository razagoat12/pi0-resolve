"""Visual check of photon transport.

Writes figures/transport_checks.png:
  (a) where accepted photons land on the array face (physics mode, carbon 5 % λ_I)
  (b) geometric acceptance vs π⁰ energy (flat mode): both photons / at least one on the array
  (c) π⁰ lost to photon conversion, for every target and thickness (D-04)
and prints the conversion-loss table.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from pi0resolve.config import load_config
from pi0resolve.decay import decay_pi0
from pi0resolve.generator import generate_pi0s
from pi0resolve.transport import event_status, transport_photons

N_EVENTS = 1_000_000
OUTPUT = Path(__file__).resolve().parents[1] / "figures" / "transport_checks.png"


def simulate(n, rng, cfg, material, fraction, mode):
    sample = generate_pi0s(n, rng, cfg, material, fraction, mode)
    gamma1, gamma2 = decay_pi0(sample.p4, rng)
    hits = [transport_photons(g, sample.vertex, rng, cfg, material, fraction) for g in (gamma1, gamma2)]
    return sample, hits


def main():
    cfg = load_config()
    rng = np.random.default_rng(cfg["seed"])
    g = cfg["geometry"]
    half = 0.5 * g["blocks_per_side"] * g["block_size_cm"]

    fig, (ax_a, ax_b, ax_c) = plt.subplots(1, 3, figsize=(16, 4.8), constrained_layout=True)

    # (a) hit map
    sample, hits = simulate(N_EVENTS, rng, cfg, "carbon", 0.05, "physics")
    _, accepted = event_status(sample.is_dalitz, hits)
    positions = np.vstack([h.position[accepted] for h in hits])
    *_, image = ax_a.hist2d(positions[:, 0], positions[:, 1], bins=80, range=((-half, half),) * 2, cmap="viridis")
    fig.colorbar(image, ax=ax_a, label="photons per bin")
    for edge in np.linspace(-half, half, g["blocks_per_side"] + 1):
        ax_a.axhline(edge, color="white", lw=0.6, alpha=0.6)
        ax_a.axvline(edge, color="white", lw=0.6, alpha=0.6)
    ax_a.set(xlabel="u (cm), toward larger angles", ylabel="v (cm)", aspect="equal",
             title=f"(a) Photon hits, accepted π⁰ ({accepted.mean():.2%} of all)")

    # (b) acceptance vs energy, flat mode
    sample, hits = simulate(N_EVENTS, rng, cfg, "carbon", 0.02, "flat")
    energy = sample.p4[:, 0]
    both = hits[0].on_array & hits[1].on_array
    one = hits[0].on_array | hits[1].on_array
    edges = np.arange(cfg["pi0"]["energy_min_gev"], cfg["pi0"]["energy_max_gev"] + 1e-9, cfg["pi0"]["energy_bin_gev"])
    centres = 0.5 * (edges[1:] + edges[:-1])
    index = np.digitize(energy, edges) - 1
    for flag, label, colour in ((both, "both photons", "#F72585"), (one, "at least one", "#4CC9F0")):
        frac = np.array([flag[index == i].mean() for i in range(len(centres))])
        ax_b.plot(centres, frac, "o-", color=colour, label=label)
    ax_b.set(xlabel=r"$\pi^0$ energy (GeV)", ylabel="fraction reaching the array", ylim=(0, 1.05),
             title="(b) Geometric acceptance (π⁰ aimed at the array)")
    ax_b.legend()

    # (c) conversion losses for every target configuration
    labels, lost = [], []
    print(f"{'target':8s} {'thickness':>9s}  π⁰ lost to conversion (both photons on array)")
    for material in cfg["targets"]["materials"]:
        for fraction in cfg["targets"]["thickness_fractions_lambda_i"]:
            sample, hits = simulate(400_000, rng, cfg, material, fraction, "flat")
            geometric = hits[0].on_array & hits[1].on_array & ~sample.is_dalitz
            converted = (hits[0].converted | hits[1].converted)[geometric]
            labels.append(f"{material}\n{fraction:.0%} λ_I")
            lost.append(converted.mean())
            print(f"{material:8s} {fraction:>8.0%}   {converted.mean():6.1%}")
    colours = ["#4CC9F0", "#4CC9F0", "#F76B15", "#F76B15", "#7B61FF", "#7B61FF"]
    bars = ax_c.bar(labels, np.array(lost) * 100, color=colours)
    for bar, value in zip(bars, lost):
        ax_c.text(bar.get_x() + bar.get_width() / 2, value * 100 + 0.5, f"{value:.1%}", ha="center", fontsize=9)
    ax_c.set(ylabel="π⁰ lost to conversion (%)", title="(c) Target + air + veto conversion losses")

    fig.suptitle(rf"Photon transport check · L = {g['distance_cm']:.0f} cm, θ = {np.degrees(g['angle_rad']):.0f}° · seed {cfg['seed']}")
    OUTPUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUTPUT, dpi=150)
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
