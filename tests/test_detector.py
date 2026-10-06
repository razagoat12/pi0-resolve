"""Checks for the lead-glass array response (D-06, D-07, D-17)."""

import copy

import numpy as np
import pytest
from scipy.special import ndtr

from pi0resolve.config import load_config
from pi0resolve.detector import (
    array_response,
    block_fractions,
    make_gains,
    measured_energy,
    readout,
    shape_variations,
    shower_centres,
    shower_deposits,
    shower_depth_cm,
    shower_shape,
)
from pi0resolve.transport import PhotonHits

SEED = 777
CFG = load_config()


def config(**changes):
    """Copy of the default config with dotted keys changed, e.g. detector__noise_gev=0."""
    cfg = copy.deepcopy(CFG)
    for key, value in changes.items():
        section, name = key.split("__")
        cfg[section][name] = value
    return cfg


IDEAL = config(shower__width_fluctuation=0.0, shower__core_fraction_fluctuation=0.0,
               detector__resolution_stochastic=0.0, detector__resolution_constant=0.0)


def photons(energy, u, v, direction=(0.0, 0.0, 1.0), on_array=True, converted=False):
    """PhotonHits for N photons at face positions (u, v)."""
    u = np.atleast_1d(np.asarray(u, dtype=float))
    n = len(u)
    d = np.tile(np.asarray(direction, dtype=float) / np.linalg.norm(direction), (n, 1))
    z = np.zeros(n)
    return PhotonHits(np.full(n, float(energy)), np.full(n, on_array), np.column_stack((u, np.broadcast_to(v, n))),
                      d, z, z, z, np.full(n, converted))


def containment(shape, r):
    """Fraction of a two-Gaussian shower within radius r (2D Gaussian: 1 - exp(-r²/2σ²))."""
    inside = lambda sigma: 1.0 - np.exp(-r**2 / (2 * sigma**2))
    return shape.core_fraction * inside(shape.core_sigma_cm) + (1 - shape.core_fraction) * inside(shape.halo_sigma_cm)


# --- shower shape and depth -------------------------------------------------------

def test_shower_shape_reproduces_pdg_containment():
    """PDG: 90 % of the energy within 1 R_M, 99 % within 3.5 R_M."""
    shape = shower_shape(CFG)
    r_m = 2.6
    assert abs(containment(shape, r_m) - 0.90) < 0.005   # core treated as fully inside 1 R_M
    assert abs(containment(shape, 3.5 * r_m) - 0.99) < 1e-6
    assert np.isclose(shape.core_sigma_cm, 0.3 * r_m)
    assert shape.halo_sigma_cm > r_m > shape.core_sigma_cm


def test_shower_depth_matches_pdg_formula():
    """1 GeV photon in SF57: X0 · (ln(1 / 0.012) + 0.5 + 2) = 10.73 cm."""
    assert np.isclose(shower_depth_cm(np.array([1.0]), CFG)[0], 1.55 * (np.log(1 / 0.012) + 2.5))
    assert np.isclose(shower_depth_cm(np.array([1.0]), CFG)[0], 10.73, atol=0.01)
    assert shower_depth_cm(np.array([4.0]), CFG)[0] > shower_depth_cm(np.array([1.0]), CFG)[0]


def test_oblique_photon_shower_shifts_along_its_direction():
    alpha = np.radians(8.0)
    hits = photons(1.0, 5.0, -3.0, direction=(np.sin(alpha), 0.0, np.cos(alpha)))
    centre = shower_centres(hits, CFG)[0]
    assert np.isclose(centre[0], 5.0 + 10.73 * np.tan(alpha), atol=0.01)
    assert np.isclose(centre[1], -3.0)
    head_on = shower_centres(photons(1.0, 5.0, -3.0), CFG)[0]
    assert np.allclose(head_on, [5.0, -3.0])


# --- sharing between blocks ------------------------------------------------------

def test_block_fractions_match_hand_calculation():
    """Photon at the centre of block (iv=2, iu=2): u and v each span [0, 10] cm."""
    shape = shower_shape(CFG)
    f = block_fractions(np.array([[5.0, 5.0]]), np.ones(1), np.array([shape.core_fraction]), CFG)[0]
    one_d = lambda s: ndtr(5.0 / s) - ndtr(-5.0 / s)
    expected = shape.core_fraction * one_d(shape.core_sigma_cm) ** 2 + (1 - shape.core_fraction) * one_d(shape.halo_sigma_cm) ** 2
    assert np.isclose(f[2, 2], expected)
    assert f[2, 2] == f.max()


@pytest.mark.parametrize("u, v, iv, iu", [(15.0, -15.0, 0, 3), (-15.0, 5.0, 2, 0), (-5.0, 15.0, 3, 1)])
def test_photon_lands_in_the_right_block(u, v, iv, iu):
    """Blocks are indexed [iv, iu], counting from the -u (beam side) and -v edges."""
    deposits = shower_deposits([photons(1.0, u, v)], np.random.default_rng(SEED), IDEAL)[0]
    assert np.unravel_index(deposits.argmax(), deposits.shape) == (iv, iu)


def test_energy_is_conserved_away_from_edges():
    deposits = shower_deposits([photons(2.0, 0.0, 0.0)], np.random.default_rng(SEED), IDEAL)
    assert np.isclose(deposits.sum(), 2.0, rtol=1e-5)


def test_energy_leaks_out_at_the_edge():
    shape = shower_shape(CFG)
    deposits = shower_deposits([photons(2.0, 19.0, 0.0)], np.random.default_rng(SEED), IDEAL)
    kept_u = shape.core_fraction * ndtr(1.0 / shape.core_sigma_cm) + (1 - shape.core_fraction) * ndtr(1.0 / shape.halo_sigma_cm)
    assert np.isclose(deposits.sum(), 2.0 * kept_u, rtol=1e-4)
    assert deposits.sum() < 2.0


def test_mirror_symmetry():
    rng = np.random.default_rng(SEED)
    a = shower_deposits([photons(1.0, 7.3, -2.1)], rng, IDEAL)[0]
    b = shower_deposits([photons(1.0, -7.3, 2.1)], rng, IDEAL)[0]
    assert np.allclose(a, b[::-1, ::-1])


def test_two_photons_add():
    rng = np.random.default_rng(SEED)
    both = shower_deposits([photons(1.0, -12.0, 3.0), photons(0.5, 6.0, -8.0)], rng, IDEAL)
    one = shower_deposits([photons(1.0, -12.0, 3.0)], rng, IDEAL)
    two = shower_deposits([photons(0.5, 6.0, -8.0)], rng, IDEAL)
    assert np.allclose(both, one + two)


def test_converted_or_missing_photons_deposit_nothing():
    rng = np.random.default_rng(SEED)
    assert shower_deposits([photons(1.0, 0.0, 0.0, converted=True)], rng, IDEAL).sum() == 0.0
    assert shower_deposits([photons(1.0, 0.0, 0.0, on_array=False)], rng, IDEAL).sum() == 0.0


# --- fluctuations ---------------------------------------------------------------

@pytest.mark.parametrize("energy, expected", [(1.0, 0.0002 + 0.063), (4.0, 0.0002 + 0.063 / 2)])
def test_energy_resolution(energy, expected):
    e = measured_energy(np.full(200_000, energy), np.random.default_rng(SEED), CFG)
    assert np.isclose(e.mean(), energy, rtol=1e-3)
    assert np.isclose(e.std() / energy, expected, rtol=0.01)


def test_shape_variations_have_configured_spread():
    scale, core = shape_variations(200_000, np.random.default_rng(SEED), CFG)
    assert np.isclose(np.log(scale).std(), 0.10, rtol=0.02)
    assert np.isclose(core.mean(), shower_shape(CFG).core_fraction, atol=1e-3)
    assert np.isclose(core.std(), 0.03, rtol=0.02)


def test_without_fluctuations_identical_photons_give_identical_showers():
    d = shower_deposits([photons(1.0, [3.0, 3.0], 4.0)], np.random.default_rng(SEED), IDEAL)
    assert np.allclose(d[0], d[1])
    d = shower_deposits([photons(1.0, [3.0, 3.0], 4.0)], np.random.default_rng(SEED), CFG)
    assert not np.allclose(d[0], d[1])


# --- readout: gains, noise, threshold ----------------------------------------------

def test_noise_and_threshold():
    """Empty array: noise σ = 10 MeV, so blocks pass the 30 MeV threshold with P(z > 3) = 0.135 %."""
    blocks = readout(np.zeros((200_000, 4, 4)), np.random.default_rng(SEED), CFG)
    nonzero = blocks[blocks != 0]
    assert np.isclose((blocks != 0).mean(), 1 - ndtr(3.0), rtol=0.05)
    assert np.all(nonzero >= 0.030)


def test_raw_noise_width():
    blocks = readout(np.zeros((100_000, 4, 4)), np.random.default_rng(SEED),
                     config(detector__threshold_noise_sigmas=-np.inf))
    assert np.isclose(blocks.std(), 0.010, rtol=0.01)


def test_signal_above_threshold_survives():
    deposits = np.zeros((1, 4, 4))
    deposits[0, 1, 2] = 0.5
    blocks = readout(deposits, np.random.default_rng(SEED), CFG)
    assert np.isclose(blocks[0, 1, 2], 0.5, atol=0.06)


def test_gains():
    assert np.all(make_gains(np.random.default_rng(SEED), CFG) == 1.0)    # default: 0 % gain error
    gains = make_gains(np.random.default_rng(SEED), config(detector__gain_error=0.05))
    assert gains.shape == (4, 4) and not np.allclose(gains, 1.0)
    deposits = np.full((1, 4, 4), 1.0)
    quiet = config(detector__noise_gev=0.0)
    assert np.allclose(readout(deposits, np.random.default_rng(SEED), quiet, gains)[0], gains)


def test_full_response_is_reproducible():
    hits = [photons(1.5, [-4.0, 9.0], [2.0, -6.0])]
    a = array_response(hits, np.random.default_rng(3), CFG)
    b = array_response(hits, np.random.default_rng(3), CFG)
    assert np.array_equal(a, b)
