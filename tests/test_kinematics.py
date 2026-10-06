"""Checks for the four-vector helpers."""

import numpy as np

from pi0resolve.kinematics import (
    boost,
    four_momentum,
    invariant_mass,
    isotropic_directions,
    opening_angle,
    rotate_from_z,
)

SEED = 2026


def random_betas(n, rng, max_speed=0.99):
    return isotropic_directions(n, rng) * rng.uniform(0.0, max_speed, n)[:, None]


def mass_squared(p4):
    return p4[:, 0] ** 2 - np.sum(p4[:, 1:] ** 2, axis=1)


def test_isotropic_directions():
    n = 200_000
    d = isotropic_directions(n, np.random.default_rng(SEED))
    assert np.allclose(np.linalg.norm(d, axis=1), 1.0, atol=1e-12)
    # Each component averages to 0 and <n_z^2> = 1/3 (5-sigma tolerances)
    assert np.all(np.abs(d.mean(axis=0)) < 5.0 / np.sqrt(3.0 * n))
    assert abs(np.mean(d[:, 2] ** 2) - 1.0 / 3.0) < 5.0 * np.sqrt(4.0 / 45.0 / n)


def test_rotate_from_z_carries_z_onto_axis_and_preserves_geometry():
    rng = np.random.default_rng(SEED)
    for axis in (np.array([0.0, 0.0, 1.0]), np.array([0.0, 1.0, 0.0]),
                 isotropic_directions(1, rng)[0]):
        assert np.allclose(rotate_from_z(np.array([[0.0, 0.0, 1.0]]), axis)[0], axis)
        vectors = isotropic_directions(500, rng) * rng.uniform(0.1, 3.0, 500)[:, None]
        rotated = rotate_from_z(vectors, axis)
        assert np.allclose(np.linalg.norm(rotated, axis=1), np.linalg.norm(vectors, axis=1))
        assert np.allclose(rotated[:-1] @ rotated[1:].T, vectors[:-1] @ vectors[1:].T)


def test_four_momentum_has_requested_mass():
    rng = np.random.default_rng(SEED)
    mass = 0.938
    energy = rng.uniform(mass, 10.0, 1_000)
    p4 = four_momentum(energy, isotropic_directions(1_000, rng), mass)
    assert np.allclose(mass_squared(p4), mass**2, atol=1e-12)


def test_boost_of_particle_at_rest():
    """A particle at rest, boosted by β, has E = γm and p = γmβ."""
    rng = np.random.default_rng(SEED)
    n, mass = 1_000, 0.135
    beta = random_betas(n, rng)
    gamma = 1.0 / np.sqrt(1.0 - np.sum(beta**2, axis=1))
    at_rest = np.column_stack((np.full(n, mass), np.zeros((n, 3))))
    moved = boost(at_rest, beta)
    assert np.allclose(moved[:, 0], gamma * mass)
    assert np.allclose(moved[:, 1:], (gamma * mass)[:, None] * beta)


def test_boost_preserves_mass_and_inverts():
    rng = np.random.default_rng(SEED)
    n, mass = 1_000, 0.5
    p4 = four_momentum(rng.uniform(mass, 5.0, n), isotropic_directions(n, rng), mass)
    beta = random_betas(n, rng)
    boosted = boost(p4, beta)
    assert np.allclose(mass_squared(boosted), mass**2, rtol=1e-9)
    assert np.allclose(boost(boosted, -beta), p4, rtol=1e-9, atol=1e-12)


def test_zero_boost_changes_nothing():
    rng = np.random.default_rng(SEED)
    p4 = four_momentum(rng.uniform(1.0, 5.0, 100), isotropic_directions(100, rng), 0.135)
    assert np.allclose(boost(p4, np.zeros((100, 3))), p4)


def test_invariant_mass_of_back_to_back_photons():
    gamma1 = np.array([[1.0, 0.0, 0.0, 1.0]])
    gamma2 = np.array([[1.0, 0.0, 0.0, -1.0]])
    assert np.allclose(invariant_mass(gamma1, gamma2), 2.0)


def test_opening_angle_is_accurate_at_small_angles():
    """atan2 keeps tiny angles accurate; arccos would lose most digits here."""
    tiny = 1e-7
    a = np.array([[1.0, 0.0, 0.0, 1.0]])
    b = np.array([[1.0, np.sin(tiny), 0.0, np.cos(tiny)]])
    assert np.isclose(opening_angle(a, b)[0], tiny, rtol=1e-9)
