"""Validation checks for π⁰ → γγ (docs/decisions.md, README "Validation")."""

import numpy as np
import pytest
from scipy import stats

from pi0resolve.constants import PI0_BR_DALITZ, PI0_BR_GAMMA_GAMMA, PI0_MASS
from pi0resolve.decay import decay_pi0, is_dalitz
from pi0resolve.kinematics import (
    four_momentum,
    invariant_mass,
    isotropic_directions,
    opening_angle,
)

SEED = 12345
ENERGIES = [0.5, 1.0, 2.0, 5.0]  # GeV, spanning the D-03 range


def decayed(energy, n, seed=SEED):
    """π⁰s of one energy, flying in random directions, and their decay photons."""
    rng = np.random.default_rng(seed)
    pi0 = four_momentum(np.full(n, energy), isotropic_directions(n, rng), PI0_MASS)
    gamma1, gamma2 = decay_pi0(pi0, rng)
    return pi0, gamma1, gamma2


@pytest.mark.parametrize("energy", [PI0_MASS] + ENERGIES)
def test_photons_are_massless(energy):
    _, gamma1, gamma2 = decayed(energy, 10_000)
    for gamma in (gamma1, gamma2):
        m2 = gamma[:, 0] ** 2 - np.sum(gamma[:, 1:] ** 2, axis=1)
        assert np.allclose(m2, 0.0, atol=1e-12)


@pytest.mark.parametrize("energy", [PI0_MASS] + ENERGIES)
def test_four_momentum_is_conserved(energy):
    pi0, gamma1, gamma2 = decayed(energy, 10_000)
    assert np.allclose(gamma1 + gamma2, pi0, rtol=1e-12, atol=1e-12)


@pytest.mark.parametrize("energy", [PI0_MASS] + ENERGIES)
def test_photons_rebuild_pi0_mass(energy):
    _, gamma1, gamma2 = decayed(energy, 100_000)
    assert np.allclose(invariant_mass(gamma1, gamma2), PI0_MASS, rtol=0, atol=1e-9)


@pytest.mark.parametrize("energy", ENERGIES)
def test_minimum_opening_angle(energy):
    """θ_min = 2·arcsin(m/E): never undercut, and reached by symmetric decays."""
    theta_min = 2.0 * np.arcsin(PI0_MASS / energy)
    _, gamma1, gamma2 = decayed(energy, 200_000)
    angle = opening_angle(gamma1, gamma2)
    assert np.all(angle >= theta_min * (1.0 - 1e-9))
    assert angle.min() <= theta_min * (1.0 + 1e-3)


@pytest.mark.parametrize("energy", ENERGIES)
def test_energy_asymmetry_is_flat(energy):
    """|E1 - E2| / E is uniform on [0, β] for an isotropic decay."""
    pi0, gamma1, gamma2 = decayed(energy, 100_000)
    beta = np.linalg.norm(pi0[0, 1:]) / energy
    asymmetry = np.abs(gamma1[:, 0] - gamma2[:, 0]) / energy
    assert stats.kstest(asymmetry, "uniform", args=(0.0, beta)).pvalue > 0.01


@pytest.mark.parametrize("energy", ENERGIES)
def test_photon_energy_bounds(energy):
    """Each photon carries between E(1 - β)/2 and E(1 + β)/2."""
    pi0, gamma1, gamma2 = decayed(energy, 100_000)
    beta = np.linalg.norm(pi0[0, 1:]) / energy
    for gamma in (gamma1, gamma2):
        assert np.all(gamma[:, 0] >= 0.5 * energy * (1.0 - beta) - 1e-12)
        assert np.all(gamma[:, 0] <= 0.5 * energy * (1.0 + beta) + 1e-12)


def test_pi0_at_rest_gives_back_to_back_photons():
    _, gamma1, gamma2 = decayed(PI0_MASS, 1_000)
    assert np.allclose(gamma1[:, 0], 0.5 * PI0_MASS)
    assert np.allclose(gamma2[:, 0], 0.5 * PI0_MASS)
    assert np.allclose(opening_angle(gamma1, gamma2), np.pi, atol=1e-9)


def test_branching_fractions_match_pdg():
    """γγ + Dalitz cover all but the neglected modes (~3e-5)."""
    assert 0.0 < 1.0 - (PI0_BR_GAMMA_GAMMA + PI0_BR_DALITZ) < 1e-4


def test_dalitz_fraction():
    """Tagged fraction matches the PDG branching fraction within 5 sigma."""
    n = 1_000_000
    tagged = is_dalitz(n, np.random.default_rng(SEED))
    sigma = np.sqrt(PI0_BR_DALITZ * (1.0 - PI0_BR_DALITZ) / n)
    assert tagged.dtype == bool
    assert abs(tagged.mean() - PI0_BR_DALITZ) < 5.0 * sigma


def test_same_seed_is_reproducible():
    first = decayed(2.0, 1_000, seed=7)
    second = decayed(2.0, 1_000, seed=7)
    other = decayed(2.0, 1_000, seed=8)
    for a, b in zip(first, second):
        assert np.array_equal(a, b)
    assert not np.array_equal(first[1], other[1])
