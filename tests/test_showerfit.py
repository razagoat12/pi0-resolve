"""Checks for the two-shower fit (D-21)."""

import copy

import numpy as np

from pi0resolve.config import load_config
from pi0resolve.decay import decay_pi0
from pi0resolve.detector import array_response, block_fractions, shower_centres, shower_shape
from pi0resolve.generator import generate_pi0s
from pi0resolve.reconstruction import Clusters, find_clusters, fiducial
from pi0resolve.showerfit import block_sigma, fit_pairs, fit_showers, predicted_blocks
from pi0resolve.transport import event_status, transport_photons

SEED = 2718
CFG = load_config()


def random_showers(n, k, rng, spread=12.0):
    columns = []
    for _ in range(k):
        columns += [rng.uniform(0.4, 3.0, n), rng.uniform(-spread, spread, n), rng.uniform(-spread, spread, n)]
    return np.column_stack(columns)


def test_prediction_is_energy_times_average_shape():
    params = np.array([[1.7, 4.2, -6.3]])
    shape = shower_shape(CFG)
    expected = 1.7 * block_fractions(params[:, 1:], np.ones(1), np.array([shape.core_fraction]), CFG)
    assert np.allclose(predicted_blocks(params, CFG), expected.reshape(1, -1))


def test_two_showers_add():
    a, b = np.array([[1.0, -8.0, 3.0]]), np.array([[0.6, 9.0, -4.0]])
    both = predicted_blocks(np.hstack((a, b)), CFG)
    assert np.allclose(both, predicted_blocks(a, CFG) + predicted_blocks(b, CFG))


def test_block_sigma_terms():
    """σ² = noise² + s²·e + (f·e)²: noise only at zero energy."""
    assert np.isclose(block_sigma(np.array([0.0]), CFG)[0], 0.010)
    e = 1.0
    expected = np.sqrt(0.010**2 + 0.063**2 * e + (0.05 * e) ** 2)
    assert np.isclose(block_sigma(np.array([e]), CFG)[0], expected)


def test_single_shower_recovered_exactly_from_ideal_blocks():
    """Blocks made by the model itself, start 1 cm and 20 % off: the fit must return the truth."""
    rng = np.random.default_rng(SEED)
    truth = random_showers(2_000, 1, rng)
    blocks = predicted_blocks(truth, CFG).reshape(-1, 4, 4)
    start = truth + np.column_stack((0.2 * truth[:, 0], rng.normal(0, 1, (2_000, 2))))
    fitted, chi2 = fit_showers(blocks, start, CFG)
    error = np.abs(fitted - truth)
    assert np.mean(np.all(error < [1e-3, 1e-2, 1e-2], axis=1)) > 0.97


def test_two_showers_recovered_from_ideal_blocks():
    rng = np.random.default_rng(SEED)
    truth = random_showers(2_000, 2, rng)
    far_apart = np.linalg.norm(truth[:, 1:3] - truth[:, 4:6], axis=1) > 12.0
    truth = truth[far_apart]
    blocks = predicted_blocks(truth, CFG).reshape(-1, 4, 4)
    start = truth + np.column_stack((0.2 * truth[:, 0], rng.normal(0, 1, (len(truth), 2)),
                                     -0.2 * truth[:, 3], rng.normal(0, 1, (len(truth), 2))))
    fitted, _ = fit_showers(blocks, start, CFG)
    swapped = fitted[:, [3, 4, 5, 0, 1, 2]]
    error = np.minimum(np.abs(fitted - truth).max(axis=1), np.abs(swapped - truth).max(axis=1))
    assert np.mean(error < 1e-2) > 0.85


def test_fit_never_worsens_the_start():
    rng = np.random.default_rng(SEED)
    truth = random_showers(500, 2, rng)
    blocks = predicted_blocks(truth, CFG).reshape(-1, 4, 4) + rng.normal(0, 0.01, (500, 4, 4))
    blocks = np.where(blocks > 0.03, blocks, 0.0)
    start = truth + rng.normal(0, 1.5, truth.shape) * [0, 1, 1, 0, 1, 1]
    from pi0resolve.showerfit import _residuals
    start_chi2 = np.sum(_residuals(start, blocks.reshape(500, -1), 0.03, CFG) ** 2, axis=1)
    _, chi2 = fit_showers(blocks, start, CFG)
    assert np.all(chi2 <= start_chi2 + 1e-9)


def test_limits_are_respected():
    rng = np.random.default_rng(SEED)
    truth = random_showers(500, 2, rng, spread=19.0)
    blocks = predicted_blocks(truth, CFG).reshape(-1, 4, 4)
    fitted, _ = fit_showers(blocks, truth * [1, 1.6, 1.6, 1, 1.6, 1.6], CFG)
    limit = 20.0 + CFG["showerfit"]["position_margin_cm"]
    assert np.all(np.abs(fitted[:, [1, 2, 4, 5]]) <= limit + 1e-9)
    assert np.all(fitted[:, [0, 3]] <= 3.0 * blocks.reshape(500, -1).sum(axis=1)[:, None] + 1e-9)


def test_fit_is_deterministic():
    rng = np.random.default_rng(SEED)
    truth = random_showers(200, 2, rng)
    blocks = predicted_blocks(truth, CFG).reshape(-1, 4, 4)
    a, _ = fit_showers(blocks, truth * 1.05, CFG)
    b, _ = fit_showers(blocks, truth * 1.05, CFG)
    assert np.array_equal(a, b)


def test_fit_is_unbiased_where_position_information_exists():
    """π⁰ pairs above 2.5 GeV whose photons truly lie inside the fiducial region:
    fitted separations and energies within 2 % of the truth (D-21). Photons near
    the array edge are the documented limitation and are excluded here."""
    rng = np.random.default_rng(SEED)
    sample = generate_pi0s(300_000, rng, CFG, "carbon", 0.02, "flat")
    gammas = decay_pi0(sample.p4, rng)
    hits = [transport_photons(g, sample.vertex, rng, CFG, "carbon", 0.02) for g in gammas]
    _, accepted = event_status(sample.is_dalitz, hits)
    blocks = array_response(hits, rng, CFG)
    clusters = find_clusters(blocks, CFG)
    truth = [shower_centres(h, CFG) for h in hits]
    use = (clusters.count == 2) & accepted & (sample.p4[:, 0] > 2.5) & fiducial(truth[0], CFG) & fiducial(truth[1], CFG)

    params, _ = fit_pairs(Clusters(clusters.energy[use], clusters.position[use]), blocks[use], CFG)
    fitted_sep = np.linalg.norm(params[:, 1:3] - params[:, 4:6], axis=1)
    true_sep = np.linalg.norm(truth[0][use] - truth[1][use], axis=1)
    true_energy = hits[0].energy[use] + hits[1].energy[use]
    assert use.sum() > 1_000
    assert abs(np.median(fitted_sep / true_sep) - 1.0) < 0.02
    assert abs(np.median((params[:, 0] + params[:, 3]) / true_energy) - 1.0) < 0.02
