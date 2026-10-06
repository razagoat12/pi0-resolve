"""Neutral-pion decay, π⁰ → γγ.

Units: GeV. Four-vectors are (N, 4) arrays [E, px, py, pz].
"""

import numpy as np

from .constants import PI0_BR_DALITZ, PI0_MASS
from .kinematics import boost, isotropic_directions


def is_dalitz(n, rng):
    """Tag which of `n` π⁰s decay via the Dalitz mode π⁰ → e⁺e⁻γ (D-13).

    Returns a boolean array, True with probability PI0_BR_DALITZ (1.17 %).
    The nearly collinear e⁺e⁻ pair fires the charged veto in front of the
    array, so tagged π⁰s are rejected downstream rather than tracked;
    their electron kinematics are never simulated.
    """
    return rng.random(n) < PI0_BR_DALITZ


def decay_pi0(p4_pi0, rng):
    """Decay π⁰s into two photons and return (gamma1, gamma2) in the lab frame.

    This is the γγ mode (98.8 %). Use `is_dalitz` to tag the 1.2 % that decay
    to e⁺e⁻γ instead.

    1. In the π⁰ rest frame the photons are back to back, each carrying half
       the π⁰ mass, along a random (isotropic) direction n:
           gamma1 = (m/2) * (1,  n)
           gamma2 = (m/2) * (1, -n)
    2. Both photons are boosted to the lab with the π⁰ velocity
           beta = p_pi0 / E_pi0

    The π⁰ has spin 0, so the rest-frame direction is isotropic. The decay
    happens at the production point: cτ ≈ 25 nm, far below anything resolvable.
    """
    n = len(p4_pi0)
    half_mass = 0.5 * PI0_MASS
    direction = isotropic_directions(n, rng)
    ones = np.ones((n, 1))

    gamma1_rest = half_mass * np.hstack((ones, direction))
    gamma2_rest = half_mass * np.hstack((ones, -direction))

    beta = p4_pi0[:, 1:] / p4_pi0[:, :1]
    return boost(gamma1_rest, beta), boost(gamma2_rest, beta)
