"""Classifier inputs computed from a cluster's 3 × 3 window (D-10, D-22).

Two input sets are compared:
  - shape features: a few physics-motivated numbers describing how the
    energy is spread;
  - raw window: the nine block energies divided by the window total.
Both include log(cluster energy), because how wide a merged cluster looks
depends on energy. Energy alone cannot separate the classes: the samples
are energy-matched (D-09), which a sanity check confirms.
"""

import numpy as np

# Offsets of the 3 × 3 window blocks from the seed, in block units
_DV, _DU = np.meshgrid(np.arange(-1, 2), np.arange(-1, 2), indexing="ij")


def shape_features(window, energy, threshold):
    """(N, 6): max fraction, second/first, width, elongation, blocks above threshold, log E."""
    flat = window.reshape(len(window), -1)
    total = flat.sum(axis=1)
    ordered = np.sort(flat, axis=1)[:, ::-1]
    max_fraction = ordered[:, 0] / total
    second_ratio = ordered[:, 1] / ordered[:, 0]

    weight = window / total[:, None, None]
    mean_u = np.sum(weight * _DU, axis=(1, 2))
    mean_v = np.sum(weight * _DV, axis=(1, 2))
    var_u = np.sum(weight * (_DU - mean_u[:, None, None]) ** 2, axis=(1, 2))
    var_v = np.sum(weight * (_DV - mean_v[:, None, None]) ** 2, axis=(1, 2))
    width = np.sqrt(var_u + var_v)                               # in block units
    elongation = np.abs(var_u - var_v) / np.maximum(var_u + var_v, 1e-12)
    n_blocks = np.count_nonzero(flat >= threshold, axis=1)
    return np.column_stack((max_fraction, second_ratio, width, elongation, n_blocks, np.log(energy)))


SHAPE_FEATURE_NAMES = ("max_fraction", "second_ratio", "width", "elongation", "n_blocks", "log_energy")


def raw_features(window, energy):
    """(N, 10): the nine window energies divided by their total, plus log E."""
    flat = window.reshape(len(window), -1)
    return np.column_stack((flat / flat.sum(axis=1)[:, None], np.log(energy)))


def width_score(window, energy, threshold):
    """Baseline score: cluster width (wider ⇒ more π⁰-like)."""
    return shape_features(window, energy, threshold)[:, 2]
