"""Checks for the π⁰ generator (D-15)."""

import numpy as np
import pytest
from scipy import stats

from pi0resolve.config import load_config
from pi0resolve.constants import PI0_BR_DALITZ, PI0_MASS
from pi0resolve.generator import (
    aim_half_angle,
    array_axis,
    cone_directions,
    generate_pi0s,
    sample_vertices,
    toy_momenta,
)
from pi0resolve.kinematics import rotate_from_z

SEED = 31415
CFG = load_config()


def mass(p4):
    return np.sqrt(p4[:, 0] ** 2 - np.sum(p4[:, 1:] ** 2, axis=1))


@pytest.mark.parametrize("mode", ["physics", "flat"])
@pytest.mark.parametrize("material", ["carbon", "copper", "tin"])
def test_generated_pi0s_are_valid(mode, material):
    n = 50_000
    sample = generate_pi0s(n, np.random.default_rng(SEED), CFG, material, 0.05, mode)
    e_min, e_max = CFG["pi0"]["energy_min_gev"], CFG["pi0"]["energy_max_gev"]

    assert len(sample) == n
    assert np.allclose(mass(sample.p4), PI0_MASS, atol=1e-9)
    assert np.all((sample.p4[:, 0] >= e_min - 1e-12) & (sample.p4[:, 0] <= e_max + 1e-12))

    thickness = 0.05 * CFG["targets"]["materials"][material]["lambda_i_cm"]
    assert np.all(np.abs(sample.vertex[:, 2]) <= 0.5 * thickness + 1e-12)

    sigma = np.sqrt(PI0_BR_DALITZ * (1 - PI0_BR_DALITZ) / n)
    assert abs(sample.is_dalitz.mean() - PI0_BR_DALITZ) < 5 * sigma


def test_unknown_mode_is_rejected():
    with pytest.raises(ValueError):
        generate_pi0s(10, np.random.default_rng(SEED), CFG, "carbon", 0.02, "uniform")


def test_same_seed_is_reproducible():
    a = generate_pi0s(1_000, np.random.default_rng(5), CFG, "tin", 0.02)
    b = generate_pi0s(1_000, np.random.default_rng(5), CFG, "tin", 0.02)
    assert np.array_equal(a.p4, b.p4) and np.array_equal(a.vertex, b.vertex)
    assert np.array_equal(a.is_dalitz, b.is_dalitz)


# --- vertices -----------------------------------------------------------------

def test_beam_spot_is_gaussian_with_configured_width():
    n = 200_000
    v = sample_vertices(n, np.random.default_rng(SEED), 1.0, 15.32, spot_sigma_cm=0.5, half_width_cm=2.5)
    for axis in (0, 1):
        assert abs(v[:, axis].mean()) < 5 * 0.5 / np.sqrt(n)
        assert abs(v[:, axis].std() - 0.5) < 0.005


def test_depth_follows_beam_attenuation():
    """Depth s in [0, t] has CDF (1 - exp(-s/λ)) / (1 - exp(-t/λ)).

    A thick target (t = 2λ) makes the exponential shape easy to see.
    """
    lam, t = 10.0, 20.0
    v = sample_vertices(100_000, np.random.default_rng(SEED), t, lam, 0.5, 2.5)
    depth = v[:, 2] + 0.5 * t
    cdf = lambda s: np.expm1(-s / lam) / np.expm1(-t / lam)
    assert stats.kstest(depth, cdf).pvalue > 0.01


def test_vertices_stay_inside_target_face():
    """A spot much wider than the target is clipped to the face by redrawing."""
    v = sample_vertices(50_000, np.random.default_rng(SEED), 1.0, 15.32, spot_sigma_cm=3.0, half_width_cm=2.5)
    assert np.all(np.abs(v[:, :2]) <= 2.5)


# --- toy physics spectrum ---------------------------------------------------------

def test_toy_momentum_is_truncated_exponential():
    p_min, p_max, slope = 0.48, 4.998, 1.0
    p, _ = toy_momenta(100_000, np.random.default_rng(SEED), p_min, p_max, slope, 0.17)
    cdf = lambda x: np.expm1(-(x - p_min) / slope) / np.expm1(-(p_max - p_min) / slope)
    assert stats.kstest(p, cdf).pvalue > 0.01


def test_toy_transverse_momentum_shape():
    """Where p is large, the pT < p redraw almost never happens, so pT must
    follow its input shape pT·exp(-pT/T): a gamma distribution, shape 2."""
    temperature = 0.17
    p, direction = toy_momenta(200_000, np.random.default_rng(SEED), 0.48, 4.998, 1.0, temperature)
    pt = p * np.linalg.norm(direction[:, :2], axis=1)
    high = p > 3.0
    assert stats.kstest(pt[high], "gamma", args=(2.0, 0, temperature)).pvalue > 0.01
    assert np.all(pt < p)


def test_toy_directions_are_forward_and_symmetric():
    n = 100_000
    _, d = toy_momenta(n, np.random.default_rng(SEED), 0.48, 4.998, 1.0, 0.17)
    assert np.allclose(np.linalg.norm(d, axis=1), 1.0)
    assert np.all(d[:, 2] > 0.0)
    assert np.all(np.abs(d[:, :2].mean(axis=0)) < 5.0 / np.sqrt(n))


# --- flat mode: aimed at the array ----------------------------------------------

def test_cone_covers_whole_array():
    """Every corner of the array face lies inside the aiming cone."""
    g = CFG["geometry"]
    half = 0.5 * g["blocks_per_side"] * g["block_size_cm"]
    centre = g["distance_cm"] * array_axis(CFG)
    corners = [centre + rotate_from_z(np.array([[sx * half, sy * half, 0.0]]), array_axis(CFG))[0]
               for sx in (-1, 1) for sy in (-1, 1)]
    for corner in corners:
        angle = np.arccos(corner @ array_axis(CFG) / np.linalg.norm(corner))
        assert angle < aim_half_angle(CFG)


def test_cone_directions_are_uniform_in_solid_angle():
    half_angle = 0.3
    axis = array_axis(CFG)
    d = cone_directions(100_000, np.random.default_rng(SEED), axis, half_angle)
    cos_alpha = d @ axis
    assert np.all(cos_alpha >= np.cos(half_angle) - 1e-12)
    # Uniform in solid angle means cos(alpha) uniform on [cos(half_angle), 1]
    assert stats.kstest(cos_alpha, "uniform", args=(np.cos(half_angle), 1 - np.cos(half_angle))).pvalue > 0.01


def test_flat_mode_energy_is_uniform():
    sample = generate_pi0s(100_000, np.random.default_rng(SEED), CFG, "carbon", 0.02, "flat")
    e_min, e_max = CFG["pi0"]["energy_min_gev"], CFG["pi0"]["energy_max_gev"]
    assert stats.kstest(sample.p4[:, 0], "uniform", args=(e_min, e_max - e_min)).pvalue > 0.01
