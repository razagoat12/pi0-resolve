"""End-to-end check of Phase 1: generator → decay → transport → detector.

Writes figures/detector_checks.png:
  top row: three simulated events as the array sees them
           (single photon, resolved π⁰, merged π⁰)
  (d) energy response: summed block energy / true energy, centre vs edge
  (e) position bias: energy-weighted centroid vs true shower centre across blocks
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from pi0resolve.config import load_config
from pi0resolve.decay import decay_pi0
from pi0resolve.detector import array_response, shower_centres, shower_shape
from pi0resolve.generator import array_axis, generate_pi0s
from pi0resolve.transport import event_status, face_axes, transport_photons

OUTPUT = Path(__file__).resolve().parents[1] / "figures" / "detector_checks.png"
MATERIAL, FRACTION = "carbon", 0.02


def photons_at(points_uv, energy, rng, cfg):
    """Photons from the target centre aimed at face positions (u, v)."""
    e_u, e_v = face_axes(cfg)
    points = cfg["geometry"]["distance_cm"] * array_axis(cfg) + points_uv[:, :1] * e_u + points_uv[:, 1:] * e_v
    direction = points / np.linalg.norm(points, axis=1)[:, None]
    p4 = np.column_stack((np.full(len(points), energy), energy * direction))
    return transport_photons(p4, np.zeros_like(points), rng, cfg, MATERIAL, FRACTION)


def centroid_u(blocks, cfg):
    g = cfg["geometry"]
    centres = (np.arange(g["blocks_per_side"]) - 0.5 * (g["blocks_per_side"] - 1)) * g["block_size_cm"]
    return (blocks.sum(axis=1) * centres).sum(axis=1) / blocks.sum(axis=(1, 2))


def draw_event(ax, blocks, title, truth, cfg):
    half = 0.5 * cfg["geometry"]["blocks_per_side"] * cfg["geometry"]["block_size_cm"]
    image = ax.imshow(blocks, origin="lower", extent=(-half, half, -half, half), cmap="magma", vmin=0)
    n = blocks.shape[0]
    size = 2 * half / n
    for iv in range(n):
        for iu in range(n):
            if blocks[iv, iu] > 0:
                ax.text(-half + (iu + 0.5) * size, -half + (iv + 0.5) * size, f"{blocks[iv, iu]:.2f}",
                        ha="center", va="center", fontsize=8,
                        color="black" if blocks[iv, iu] > 0.6 * blocks.max() else "white")
    for u, v in truth:
        ax.plot(u, v, "+", color="#4CC9F0", ms=12, mew=2)
    ax.set(title=title, xlabel="u (cm)  ·  + = true shower centre", ylabel="v (cm)")
    plt.colorbar(image, ax=ax, fraction=0.046, label="GeV")


def main():
    cfg = load_config()
    rng = np.random.default_rng(cfg["seed"])

    # Full chain on flat-mode π⁰s, keeping accepted events
    sample = generate_pi0s(300_000, rng, cfg, MATERIAL, FRACTION, "flat")
    gamma1, gamma2 = decay_pi0(sample.p4, rng)
    hits = [transport_photons(g, sample.vertex, rng, cfg, MATERIAL, FRACTION) for g in (gamma1, gamma2)]
    _, accepted = event_status(sample.is_dalitz, hits)
    blocks = array_response(hits, rng, cfg)
    separation = np.linalg.norm(hits[0].position - hits[1].position, axis=1)
    energy = sample.p4[:, 0]
    centres = [shower_centres(h, cfg) for h in hits]
    # Showers centred near the edge leak most of their energy (see D-17); show typical events
    inside = np.all([np.all(np.abs(c) < 17.0, axis=1) for c in centres], axis=0)
    deposited = blocks.sum(axis=(1, 2))
    print(f"accepted π⁰: mean recorded / true energy {np.mean(deposited[accepted] / energy[accepted]):.3f}; "
          f"with both shower centres inside |u|,|v| < 10 cm: "
          f"{np.mean((deposited / energy)[accepted & np.all([np.all(np.abs(c) < 10.0, axis=1) for c in centres], axis=0)]):.3f}")

    resolved = np.flatnonzero(accepted & inside & (energy < 1.6) & (separation > 22))[0]
    merged = np.flatnonzero(accepted & inside & (energy > 4.5) & (separation < 10))[0]  # minimum is 8.1 cm at 5 GeV
    single_hits = photons_at(np.array([[-2.0, 3.5]]), 2.5, rng, cfg)
    single = array_response([single_hits], rng, cfg)[0]

    fig = plt.figure(figsize=(16, 9.5), constrained_layout=True)
    grid = fig.add_gridspec(2, 6)
    events = [
        (single, f"(a) Single photon · {single_hits.energy[0]:.1f} GeV", [shower_centres(single_hits, cfg)[0]]),
        (blocks[resolved], f"(b) Resolved π⁰ · {energy[resolved]:.2f} GeV · {separation[resolved]:.0f} cm apart",
         [centres[0][resolved], centres[1][resolved]]),
        (blocks[merged], f"(c) Merged π⁰ · {energy[merged]:.2f} GeV · {separation[merged]:.1f} cm apart",
         [centres[0][merged], centres[1][merged]]),
    ]
    for k, (b, title, truth) in enumerate(events):
        draw_event(fig.add_subplot(grid[0, 2 * k:2 * k + 2]), b, title, truth, cfg)

    # (d) energy response at the centre and near an edge
    ax_d = fig.add_subplot(grid[1, 0:3])
    for u, label, colour in ((0.0, "centre (u = 0)", "#4CC9F0"), (18.0, "edge (u = 18 cm)", "#F72585")):
        h = photons_at(np.tile([[u, 0.0]], (50_000, 1)), 1.0, rng, cfg)
        response = array_response([h], rng, cfg).sum(axis=(1, 2))[h.on_array & ~h.converted]
        ax_d.hist(response, bins=120, range=(0.5, 1.4), histtype="step", lw=2, color=colour,
                  label=f"{label}: mean {response.mean():.3f}, σ {response.std():.3f}")
    ax_d.set(xlabel="summed block energy / true energy (1 GeV photons)", ylabel="photons per bin",
             title="(d) Energy response: leakage at the edge")
    ax_d.legend()

    # (e) centroid bias across blocks
    ax_e = fig.add_subplot(grid[1, 3:6])
    true_u = np.linspace(-19.5, 19.5, 40_000)
    h = photons_at(np.column_stack((true_u, np.zeros_like(true_u))), 1.0, rng, cfg)
    ok = h.on_array & ~h.converted
    response = array_response([h], rng, cfg)
    shower_u = shower_centres(h, cfg)[:, 0]
    ax_e.plot(shower_u[ok], centroid_u(response[ok], cfg), ",", color="#7B61FF", alpha=0.3)
    ax_e.plot([-20, 20], [-20, 20], color="#FFB703", lw=1.5, label="perfect")
    ax_e.set(xlabel="true shower centre u (cm)", ylabel="energy-weighted centroid u (cm)",
             title="(e) Position bias: centroids pulled to block centres", xlim=(-20, 20), ylim=(-20, 20))
    ax_e.legend(loc="upper left")

    shape = shower_shape(cfg)
    fig.suptitle(f"Phase 1 end-to-end check · shower core {shape.core_fraction:.1%} (σ {shape.core_sigma_cm:.2f} cm), "
                 f"halo σ {shape.halo_sigma_cm:.2f} cm · seed {cfg['seed']}")
    fig.savefig(OUTPUT, dpi=150)
    print(f"accepted π⁰: {accepted.mean():.2%} of flat-mode events")
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
