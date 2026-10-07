"""Checks for reconstruction (D-08, D-18)."""

import copy

import numpy as np
import pytest

from pi0resolve.config import load_config
from pi0resolve.constants import PI0_MASS
from pi0resolve.decay import decay_pi0
from pi0resolve.detector import array_response, shower_centres
from pi0resolve.generator import generate_pi0s
from pi0resolve.reconstruction import (
    block_centres,
    find_clusters,
    find_seeds,
    fiducial,
    pair_mass,
    two_cluster_mass,
    window_matrix,
)
from pi0resolve.transport import event_status, transport_photons

SEED = 99
CFG = load_config()


def grid(entries):
    """One event's 4x4 block energies from {(iv, iu): GeV}."""
    b = np.zeros((1, 4, 4))
    for (iv, iu), e in entries.items():
        b[0, iv, iu] = e
    return b


# --- geometry helpers -----------------------------------------------------------

def test_block_centres_and_windows():
    centres = block_centres(CFG)
    assert np.allclose(centres[0], [-15, -15]) and np.allclose(centres[3], [15, -15])
    assert np.allclose(centres[4], [-15, -5])          # b = iv * 4 + iu
    window = window_matrix(CFG)
    assert window[0].sum() == 4                         # corner seed: 2x2 inside the array
    assert window[5].sum() == 9                         # inner seed: full 3x3
    assert window[1].sum() == 6                         # edge seed: 2x3
    assert np.array_equal(window, window.T)


# --- seeds -----------------------------------------------------------------------

def test_single_peak_gives_one_seed():
    seeds = find_seeds(grid({(1, 2): 1.0, (1, 1): 0.3, (2, 2): 0.2}), CFG)
    assert seeds.sum() == 1 and seeds[0, 1, 2]


def test_neighbouring_peaks_give_one_seed():
    """The lower of two adjacent maxima is not a local maximum: a merged cluster."""
    seeds = find_seeds(grid({(2, 1): 2.36, (2, 2): 1.91}), CFG)
    assert seeds.sum() == 1 and seeds[0, 2, 1]


def test_diagonal_neighbours_also_merge():
    seeds = find_seeds(grid({(1, 1): 1.0, (2, 2): 0.8}), CFG)
    assert seeds.sum() == 1


def test_separated_peaks_give_two_seeds():
    seeds = find_seeds(grid({(0, 0): 0.5, (3, 3): 0.7}), CFG)
    assert seeds.sum() == 2


def test_seed_threshold():
    assert find_seeds(grid({(1, 1): 0.099}), CFG).sum() == 0
    assert find_seeds(grid({(1, 1): 0.101}), CFG).sum() == 1


# --- clusters ----------------------------------------------------------------------

def test_isolated_cluster_collects_its_window():
    blocks = grid({(1, 1): 1.0, (1, 2): 0.2, (2, 1): 0.1, (0, 0): 0.05})
    c = find_clusters(blocks, CFG)
    assert c.count[0] == 1
    assert np.isclose(c.energy[0].max(), 1.35)


def test_shared_block_is_split_by_seed_energy_without_double_counting():
    """Seeds at iu = 0 and iu = 2 both reach the block at iu = 1."""
    blocks = grid({(1, 0): 0.6, (1, 1): 0.1, (1, 2): 0.3})
    c = find_clusters(blocks, CFG)
    assert c.count[0] == 2
    energies = np.sort(c.energy[0][c.energy[0] > 0])
    assert np.isclose(energies.sum(), 1.0)                       # nothing counted twice
    assert np.allclose(energies, [0.3 + 0.1 * 0.3 / 0.9, 0.6 + 0.1 * 0.6 / 0.9])


# --- positions -----------------------------------------------------------------------

def test_symmetric_cluster_sits_at_block_centre():
    blocks = grid({(1, 1): 1.0, (1, 0): 0.1, (1, 2): 0.1, (0, 1): 0.1, (2, 1): 0.1})
    for log_weighting in (True, False):
        c = find_clusters(blocks, CFG, log_weighting)
        assert np.allclose(c.position[0][c.energy[0] > 0][0], [-5.0, -5.0])


def test_position_moves_toward_the_heavier_neighbour():
    blocks = grid({(1, 1): 1.0, (1, 2): 0.4})
    for log_weighting in (True, False):
        u, v = find_clusters(blocks, CFG, log_weighting).position[0][find_clusters(blocks, CFG).energy[0] > 0][0]
        assert -5.0 < u < 0.0 and np.isclose(v, -5.0)


def test_log_weights_follow_the_formula():
    """Seed share 1.0/1.4, neighbour 0.4/1.4: w = W0 + ln(share)."""
    w0 = CFG["reconstruction"]["log_weight_w0"]
    w_seed, w_side = w0 + np.log(1.0 / 1.4), w0 + np.log(0.4 / 1.4)
    expected_u = (w_seed * -5.0 + w_side * 5.0) / (w_seed + w_side)
    c = find_clusters(grid({(1, 1): 1.0, (1, 2): 0.4}), CFG)
    assert np.isclose(c.position[0][c.energy[0] > 0][0][0], expected_u)


def simulated_photons(n, rng, cfg):
    """Single 2 GeV photons from the target centre at random face positions."""
    from pi0resolve.generator import array_axis
    from pi0resolve.transport import face_axes
    uv = rng.uniform(-12.0, 12.0, (n, 2))
    e_u, e_v = face_axes(cfg)
    points = cfg["geometry"]["distance_cm"] * array_axis(cfg) + uv[:, :1] * e_u + uv[:, 1:] * e_v
    d = points / np.linalg.norm(points, axis=1)[:, None]
    p4 = np.column_stack((np.full(n, 2.0), 2.0 * d))
    return transport_photons(p4, np.zeros((n, 3)), rng, cfg, "carbon", 0.02)


def simulated_pairs(n, rng, cfg=CFG):
    """Full chain for flat-mode π⁰s: (sample, hits, accepted, blocks)."""
    sample = generate_pi0s(n, rng, cfg, "carbon", 0.02, "flat")
    gammas = decay_pi0(sample.p4, rng)
    hits = [transport_photons(g, sample.vertex, rng, cfg, "carbon", 0.02) for g in gammas]
    _, accepted = event_status(sample.is_dalitz, hits)
    return sample, hits, accepted, array_response(hits, rng, cfg)


def separation_ratio(clusters, hits, selected):
    order = np.argsort(-clusters.energy, axis=1)[:, :2]
    position = clusters.position[np.arange(len(order))[:, None], order]
    reco = np.linalg.norm(position[:, 0] - position[:, 1], axis=1)
    true = np.linalg.norm(shower_centres(hits[0], CFG) - shower_centres(hits[1], CFG), axis=1)
    return reco[selected] / true[selected]


def test_log_weighting_gives_unbiased_pair_separations():
    """What the mass relies on (D-19): at the tuned W0, photon separations in
    π⁰ pairs are unbiased, and better than with plain energy weighting."""
    _, hits, accepted, blocks = simulated_pairs(200_000, np.random.default_rng(SEED))
    stats = {}
    for log_weighting in (True, False):
        clusters = find_clusters(blocks, CFG, log_weighting)
        _, selected = two_cluster_mass(clusters, CFG)
        ratio = separation_ratio(clusters, hits, selected & accepted)
        stats[log_weighting] = (abs(np.median(ratio) - 1.0), np.subtract(*np.percentile(ratio, [75, 25])))
    assert stats[True][0] < 0.01                       # bias below 1 %
    assert stats[True][0] < stats[False][0]            # less biased than plain weighting
    assert stats[True][1] < stats[False][1]            # and less spread


def test_log_weighting_no_worse_for_single_photons():
    rng = np.random.default_rng(SEED)
    hits = simulated_photons(20_000, rng, CFG)
    blocks = array_response([hits], rng, CFG)
    truth = shower_centres(hits, CFG)
    ok = hits.on_array & ~hits.converted
    errors = {}
    for log_weighting in (True, False):
        c = find_clusters(blocks, CFG, log_weighting)
        lead = np.argmax(c.energy, axis=1)
        position = c.position[np.arange(len(lead)), lead]
        errors[log_weighting] = np.sqrt(np.nanmean(np.sum((position[ok] - truth[ok]) ** 2, axis=1)))
    assert errors[True] < errors[False]


# --- fiducial and mass -----------------------------------------------------------

def test_fiducial_margin():
    pos = np.array([[0.0, 0.0], [15.0, -15.0], [15.1, 0.0], [np.nan, np.nan]])
    assert list(fiducial(pos, CFG)) == [True, True, False, False]


def test_pair_mass_with_true_inputs_gives_pi0_mass():
    """True photon energies and true shower centres, through the geometry, give 0.135 GeV.

    Uses ideal settings (no smearing) so this tests the mass formula and the
    depth-aware geometry, not the detector.
    """
    cfg = copy.deepcopy(CFG)
    rng = np.random.default_rng(SEED)
    sample = generate_pi0s(20_000, rng, cfg, "carbon", 0.02, "flat")
    sample.vertex[:] = 0.0                               # reconstruction assumes the target centre
    g1, g2 = decay_pi0(sample.p4, rng)
    h1, h2 = (transport_photons(g, sample.vertex, rng, cfg, "carbon", 0.02) for g in (g1, g2))
    both = h1.on_array & h2.on_array
    m = pair_mass(h1.energy[both], shower_centres(h1, cfg)[both], h2.energy[both], shower_centres(h2, cfg)[both], cfg)
    assert np.allclose(m, PI0_MASS, rtol=1e-6)


def test_full_chain_mass_peak_after_calibration():
    """Calibrated peak within 2 % of the π⁰ mass; uncalibrated clearly low.
    W0 and the energy calibration are fixed from truth-level separations and
    single-photon energies, never from the π⁰ mass, so this is an independent check."""
    _, hits, accepted, blocks = simulated_pairs(200_000, np.random.default_rng(SEED))
    clusters = find_clusters(blocks, CFG)
    calibrated, selected = two_cluster_mass(clusters, CFG)
    raw, _ = two_cluster_mass(clusters, CFG, calibrate=False)
    ok = selected & accepted
    assert ok.sum() > 1_000
    assert abs(np.median(calibrated[ok]) / PI0_MASS - 1.0) < 0.02
    assert np.median(raw[ok]) < 0.95 * PI0_MASS


# --- energy calibration (D-19) -------------------------------------------------------

def test_calibration_table_is_sane():
    from pi0resolve.config import repo_path
    table = np.loadtxt(repo_path(CFG["reconstruction"]["energy_calibration"]), delimiter=",", skiprows=1)
    true_e, reco_e = table[:, 0], table[:, 1]
    assert np.all(np.diff(true_e) > 0) and np.all(np.diff(reco_e) > 0)     # invertible
    assert np.all((reco_e / true_e > 0.80) & (reco_e / true_e < 1.0))       # losses only, < 20 %
    # Starts where >= 95 % of photons form a cluster (below, the 100 MeV seed
    # threshold biases the median high); reaches the top of the π⁰ photon range
    assert true_e[0] <= 0.35 and true_e[-1] >= 5.0


def test_correct_energy_inverts_the_table():
    from pi0resolve.reconstruction import _calibration_table, correct_energy
    true_e, reco_e = _calibration_table(CFG["reconstruction"]["energy_calibration"])
    assert np.allclose(correct_energy(reco_e, CFG), true_e)
    assert correct_energy(np.array([0.0]), CFG)[0] == 0.0


def test_correct_energy_without_table_is_identity():
    cfg = copy.deepcopy(CFG)
    cfg["reconstruction"]["energy_calibration"] = None
    from pi0resolve.reconstruction import correct_energy
    e = np.array([0.3, 1.2, 4.0])
    assert np.array_equal(correct_energy(e, cfg), e)
