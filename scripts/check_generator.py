"""Visual check of the π⁰ generator.

Writes figures/generator_checks.png:
  (a) toy energy spectrum (physics mode) vs flat mode
  (b) π⁰ polar angle from the beam, with the array's angular range and the
      HARP forward-data limit
  (c) production depth in 5 % λ_I targets of carbon, copper and tin
and prints the fraction of physics-mode π⁰s whose direction hits the array.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from pi0resolve.config import load_config
from pi0resolve.generator import generate_pi0s
from pi0resolve.transport import transport_photons

N_EVENTS = 1_000_000
HARP_FORWARD_LIMIT_RAD = 0.25
OUTPUT = Path(__file__).resolve().parents[1] / "figures" / "generator_checks.png"


def main():
    cfg = load_config()
    rng = np.random.default_rng(cfg["seed"])
    physics = generate_pi0s(N_EVENTS, rng, cfg, "carbon", 0.05, "physics")
    flat = generate_pi0s(N_EVENTS, rng, cfg, "carbon", 0.05, "flat")

    direction = physics.p4[:, 1:] / np.linalg.norm(physics.p4[:, 1:], axis=1)[:, None]
    polar = np.degrees(np.arccos(direction[:, 2]))
    # Only the direction and production point matter for "does it point at the array"
    hits = transport_photons(physics.p4, physics.vertex, rng, cfg, "carbon", 0.05).on_array
    print(f"physics-mode π⁰s pointing at the array: {hits.mean():.3%}")

    g = cfg["geometry"]
    half_width = np.degrees(np.arctan(0.5 * g["blocks_per_side"] * g["block_size_cm"] / g["distance_cm"]))
    centre = np.degrees(g["angle_rad"])

    fig, (ax_a, ax_b, ax_c) = plt.subplots(1, 3, figsize=(16, 4.6), constrained_layout=True)

    bins = np.linspace(cfg["pi0"]["energy_min_gev"], cfg["pi0"]["energy_max_gev"], 46)
    ax_a.hist(physics.p4[:, 0], bins=bins, histtype="step", lw=2, color="#7B61FF", label="physics (toy)")
    ax_a.hist(flat.p4[:, 0], bins=bins, histtype="step", lw=2, color="#F72585", label="flat (classifier)")
    ax_a.set(xlabel=r"$\pi^0$ energy (GeV)", ylabel="π⁰ per bin", yscale="log",
             title="(a) Energy: toy spectrum vs flat")
    ax_a.legend()

    ax_b.hist(polar, bins=np.linspace(0, 60, 121), color="#7B61FF", alpha=0.8, label="all π⁰")
    ax_b.hist(polar[hits], bins=np.linspace(0, 60, 121), color="#FFB703", label="pointing at array")
    ax_b.axvspan(centre - half_width, centre + half_width, color="#4CC9F0", alpha=0.15,
                 label=f"array range {centre - half_width:.1f}°–{centre + half_width:.1f}°")
    ax_b.axvline(np.degrees(HARP_FORWARD_LIMIT_RAD), color="#F72585", ls="--",
                 label=f"HARP forward limit ({np.degrees(HARP_FORWARD_LIMIT_RAD):.1f}°)")
    ax_b.set(xlabel="π⁰ angle from beam (degrees)", ylabel="π⁰ per bin", yscale="log",
             title=f"(b) Angle · {hits.mean():.2%} point at the array")
    ax_b.legend(fontsize=8)

    for material, colour in (("carbon", "#4CC9F0"), ("copper", "#F76B15"), ("tin", "#7B61FF")):
        sample = generate_pi0s(200_000, rng, cfg, material, 0.05, "physics")
        thickness = 0.05 * cfg["targets"]["materials"][material]["lambda_i_cm"]
        depth = sample.vertex[:, 2] + 0.5 * thickness
        ax_c.hist(depth, bins=50, histtype="step", lw=2, color=colour,
                  label=f"{material}: t = {thickness:.2f} cm")
    ax_c.set(xlabel="production depth in target (cm)", ylabel="π⁰ per bin",
             title="(c) Depth, 5 % λ_I targets (near-flat)")
    ax_c.legend()

    fig.suptitle(rf"$\pi^0$ generator check · {N_EVENTS:,} π⁰ · seed {cfg['seed']}")
    OUTPUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUTPUT, dpi=150)
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
