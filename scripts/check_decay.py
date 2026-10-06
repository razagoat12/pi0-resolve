"""Visual check of the π⁰ → γγ decay kinematics.

Writes figures/decay_checks.png:
  (a) photon opening angle vs π⁰ energy, with the θ_min = 2·arcsin(m/E) curve
  (b) photon energy asymmetry at 2 GeV, which should be flat on [0, β]
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np

from pi0resolve.config import load_config
from pi0resolve.constants import PI0_MASS
from pi0resolve.decay import decay_pi0
from pi0resolve.kinematics import four_momentum, isotropic_directions, opening_angle

N_EVENTS = 1_000_000
OUTPUT = Path(__file__).resolve().parents[1] / "figures" / "decay_checks.png"


def main():
    cfg = load_config()
    rng = np.random.default_rng(cfg["seed"])
    e_min, e_max = cfg["pi0"]["energy_min_gev"], cfg["pi0"]["energy_max_gev"]

    # (a) opening angle across the D-03 energy range
    energy = rng.uniform(e_min, e_max, N_EVENTS)
    pi0 = four_momentum(energy, isotropic_directions(N_EVENTS, rng), PI0_MASS)
    gamma1, gamma2 = decay_pi0(pi0, rng)
    angle = opening_angle(gamma1, gamma2)

    # (b) energy asymmetry at a single energy
    e_fixed = 2.0
    pi0_fixed = four_momentum(np.full(N_EVENTS, e_fixed), isotropic_directions(N_EVENTS, rng), PI0_MASS)
    g1, g2 = decay_pi0(pi0_fixed, rng)
    asymmetry = np.abs(g1[:, 0] - g2[:, 0]) / e_fixed
    beta = np.sqrt(1.0 - (PI0_MASS / e_fixed) ** 2)

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(12, 4.6), constrained_layout=True)

    *_, image = ax_a.hist2d(energy, np.degrees(angle), bins=(90, 120),
                            range=((e_min, e_max), (0.0, 60.0)), cmap="viridis", norm=LogNorm())
    fig.colorbar(image, ax=ax_a, label="decays per bin")
    e_curve = np.linspace(e_min, e_max, 400)
    ax_a.plot(e_curve, np.degrees(2.0 * np.arcsin(PI0_MASS / e_curve)),
              color="#4CC9F0", lw=2, label=r"$\theta_{\min} = 2\arcsin(m_{\pi^0}/E)$")
    ax_a.set(xlabel=r"$\pi^0$ energy $E$ (GeV)", ylabel="photon opening angle (degrees)",
             title="(a) Opening angle never falls below $\\theta_{\\min}$")
    ax_a.legend(loc="upper right")

    ax_b.hist(asymmetry, bins=50, range=(0.0, beta), color="#F72585", alpha=0.85)
    ax_b.axhline(N_EVENTS / 50, color="#4CC9F0", lw=2, ls="--",
                 label=f"flat expectation on [0, $\\beta$], $\\beta$ = {beta:.4f}")
    ax_b.set(xlabel=r"energy asymmetry $|E_1 - E_2| / E$", ylabel="events per bin",
             title=f"(b) Asymmetry is flat (E = {e_fixed:.0f} GeV)")
    ax_b.legend(loc="lower left")

    fig.suptitle(rf"$\pi^0 \to \gamma\gamma$ kinematics check · {N_EVENTS:,} decays · seed {cfg['seed']}")
    OUTPUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUTPUT, dpi=150)
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
