"""Checks for the Phase 3 dataset, features and fit baseline (D-22)."""

import numpy as np
import pytest

from pi0resolve.config import load_config
from pi0resolve.dataset import ClusterSample, build_dataset, seed_windows
from pi0resolve.ml.features import raw_features, shape_features
from pi0resolve.reconstruction import Clusters, fiducial, find_clusters
from pi0resolve.showerfit import merged_score, predicted_blocks

SEED = 1618
CFG = load_config()
THRESHOLD = 0.03


@pytest.fixture(scope="module")
def dataset():
    return build_dataset(150_000, np.random.default_rng(SEED), CFG)


# --- windows and features ---------------------------------------------------------

def test_seed_window_is_centred_and_zero_padded():
    blocks = np.zeros((2, 4, 4))
    blocks[0, 1, 2] = 1.0                     # inner seed at (iv=1, iu=2)
    blocks[0, 1, 3] = 0.2
    blocks[1, 0, 0] = 0.8                     # corner seed
    blocks[1, 0, 1] = 0.1
    window = seed_windows(blocks, find_clusters(blocks, CFG))
    assert window[0, 1, 1] == 1.0 and window[0, 1, 2] == 0.2
    assert window[1, 1, 1] == 0.8 and window[1, 1, 2] == 0.1
    assert np.all(window[1, 0, :] == 0) and np.all(window[1, :, 0] == 0)   # outside the array


def test_shape_features_by_hand():
    single = np.zeros((1, 3, 3))
    single[0, 1, 1] = 1.0
    f = shape_features(single, np.array([1.0]), THRESHOLD)[0]
    assert np.allclose(f, [1.0, 0.0, 0.0, 0.0, 1, 0.0])

    pair = np.zeros((1, 3, 3))
    pair[0, 1, 1], pair[0, 1, 2] = 0.6, 0.4    # split along u only
    f = shape_features(pair, np.array([np.e]), THRESHOLD)[0]
    variance_u = 0.6 * 0.4 ** 2 + 0.4 * 0.6 ** 2            # about the weighted mean
    assert np.isclose(f[0], 0.6) and np.isclose(f[1], 0.4 / 0.6)
    assert np.isclose(f[2], np.sqrt(variance_u))
    assert np.isclose(f[3], 1.0)                            # all spread along one axis
    assert f[4] == 2 and np.isclose(f[5], 1.0)


def test_raw_features_are_normalised_window_plus_log_energy():
    window = np.random.default_rng(SEED).uniform(0, 1, (5, 3, 3))
    energy = np.full(5, 2.0)
    x = raw_features(window, energy)
    assert x.shape == (5, 10)
    assert np.allclose(x[:, :9].sum(axis=1), 1.0)
    assert np.allclose(x[:, 9], np.log(2.0))


# --- dataset --------------------------------------------------------------------

def test_dataset_classes_and_selection(dataset):
    assert set(np.unique(dataset.label)) == {0, 1}
    assert dataset.label.sum() > 1_000 and (dataset.label == 0).sum() > 1_000
    assert np.all(fiducial(dataset.position, CFG))
    assert np.all(dataset.true_separation[dataset.label == 0] == 0)
    assert np.all(dataset.true_separation[dataset.label == 1] > 0)
    # Single cluster, so the 3x3 window holds exactly the cluster energy
    assert np.allclose(dataset.window.sum(axis=(1, 2)), dataset.energy)


def test_photons_are_energy_matched_to_merged_pi0s(dataset):
    merged = np.sort(dataset.true_energy[dataset.label == 1])
    photons = dataset.true_energy[dataset.label == 0]
    # Every photon copies the energy of some merged π⁰ (matched by construction)
    index = np.clip(np.searchsorted(merged, photons), 0, len(merged) - 1)
    assert np.allclose(merged[index], photons)


def test_sample_save_load_roundtrip(dataset, tmp_path):
    part = dataset.subset(np.arange(len(dataset)) < 100)
    part.save(tmp_path / "s.npz")
    back = ClusterSample.load(tmp_path / "s.npz")
    assert np.array_equal(back.window, part.window) and np.array_equal(back.label, part.label)


# --- fit baseline ---------------------------------------------------------------------

def score_ideal(showers):
    """Δχ² for noise-free blocks predicted from (N, 6) two-shower parameters."""
    blocks = predicted_blocks(showers, CFG).reshape(-1, 4, 4)
    clusters = find_clusters(blocks, CFG)
    lead = np.argmax(clusters.energy, axis=1)
    rows = np.arange(len(lead))
    return merged_score(blocks, clusters.energy[rows, lead], clusters.position[rows, lead], CFG)[0]


def test_merged_score_flags_a_pattern_one_shower_cannot_make():
    """Showers in diagonally neighbouring blocks: no single shower lights up
    two diagonal blocks without their two common neighbours."""
    single = [2.0, 3.0, -4.0, 1e-3, 15.0, 15.0]                   # second "shower" negligible
    diagonal = [1.2, -3.0, -4.0, 0.8, 4.0, 3.0]                   # 9.9 cm apart, diagonal blocks
    delta = score_ideal(np.array([single, diagonal]))
    assert delta[0] < 1.0
    assert delta[1] > 50.0


@pytest.mark.parametrize("pair", [
    [1.2, 2.0, -4.0, 0.8, 7.0, -4.0],     # both inside one block (u = 0..10)
    [1.2, -3.0, -4.0, 0.8, 4.0, -4.0],    # 7 cm apart, either side of one block boundary
])
def test_information_limit_pairs_look_like_one_shower(pair):
    """D-21 / Q4: a pair inside one block, or split across a single boundary,
    gives almost the same block energies as one shower, so even an ideal,
    noise-free fit barely prefers two showers."""
    assert score_ideal(np.array([pair]))[0] < 10.0
