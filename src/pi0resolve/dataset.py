"""Labelled single-cluster samples for the classifier (D-08, D-09, D-22).

Class 1 — merged π⁰: both photons reach the array unconverted (not vetoed),
          but reconstruction finds exactly one cluster (D-08), inside the
          fiducial region. At low energy this is usually a π⁰ whose softer
          photon is below the seed threshold; at high energy, overlapping
          photons. Both fake a single photon, so both count (D-22).
Class 0 — single photon: for every merged π⁰, one photon with the π⁰'s
          energy, from the same production point, aimed at the energy-
          weighted mean entry point of the two π⁰ photons. Energies and
          positions therefore match by construction (D-09). Same selection.

Each sample keeps the 3 × 3 block window around the cluster's seed (zero
outside the array), the full 4 × 4 array (for the shower-fit baseline), the
reconstructed cluster, and the truth needed for the analysis.
"""

from dataclasses import dataclass, fields

import numpy as np

from .decay import decay_pi0
from .detector import array_response, shower_centres
from .generator import array_axis, generate_pi0s
from .reconstruction import find_clusters, fiducial
from .transport import event_status, face_axes, transport_photons


@dataclass
class ClusterSample:
    label: np.ndarray            # (N,) 1 = merged π⁰, 0 = single photon
    window: np.ndarray           # (N, 3, 3) GeV around the seed block
    blocks: np.ndarray           # (N, n, n) GeV, whole array
    energy: np.ndarray           # (N,) raw cluster energy, GeV
    position: np.ndarray         # (N, 2) log-weighted cluster position, cm
    true_energy: np.ndarray      # (N,) π⁰ or photon energy, GeV
    true_position: np.ndarray    # (N, 2) energy-weighted mean entry point of the photons, cm
    true_separation: np.ndarray  # (N,) distance between the two shower centres, cm (0 for photons)
    soft_energy: np.ndarray      # (N,) energy of the softer π⁰ photon, GeV (0 for photons)
    vertex: np.ndarray           # (N, 3) production point, cm

    def __len__(self):
        return len(self.label)

    def subset(self, mask):
        return ClusterSample(**{f.name: getattr(self, f.name)[mask] for f in fields(self)})

    def save(self, path):
        np.savez_compressed(path, **{f.name: getattr(self, f.name) for f in fields(self)})

    @classmethod
    def load(cls, path):
        with np.load(path) as data:
            return cls(**{f.name: data[f.name] for f in fields(cls)})

    @classmethod
    def concatenate(cls, samples):
        return cls(**{f.name: np.concatenate([getattr(s, f.name) for s in samples]) for f in fields(cls)})


def seed_windows(blocks, clusters):
    """3 × 3 block energies centred on the leading cluster's seed block, zero-padded."""
    n_events, n = blocks.shape[0], blocks.shape[1]
    lead = np.argmax(clusters.energy, axis=1)
    iv, iu = np.divmod(lead, n)                      # cluster slot = flattened seed block index
    padded = np.pad(blocks, ((0, 0), (1, 1), (1, 1)))
    rows = iv[:, None, None] + np.arange(3)[None, :, None]
    cols = iu[:, None, None] + np.arange(3)[None, None, :]
    return padded[np.arange(n_events)[:, None, None], rows, cols]


def _single_cluster_selection(hits, is_dalitz, blocks, cfg):
    _, accepted = event_status(is_dalitz, hits)
    clusters = find_clusters(blocks, cfg)
    lead = np.argmax(clusters.energy, axis=1)
    rows = np.arange(len(lead))
    position = clusters.position[rows, lead]
    keep = accepted & (clusters.count == 1) & fiducial(position, cfg)
    return keep, clusters, clusters.energy[rows, lead], position


def merged_pi0_sample(n, rng, cfg, material, fraction):
    """Generate `n` flat-mode π⁰s and keep those reconstructed as one fiducial cluster."""
    pi0 = generate_pi0s(n, rng, cfg, material, fraction, "flat")
    gammas = decay_pi0(pi0.p4, rng)
    hits = [transport_photons(g, pi0.vertex, rng, cfg, material, fraction) for g in gammas]
    blocks = array_response(hits, rng, cfg)
    keep, clusters, energy, position = _single_cluster_selection(hits, pi0.is_dalitz, blocks, cfg)

    photon_energy = np.column_stack((hits[0].energy, hits[1].energy))
    entry = (photon_energy[:, :1] * hits[0].position + photon_energy[:, 1:] * hits[1].position) / photon_energy.sum(axis=1)[:, None]
    separation = np.linalg.norm(shower_centres(hits[0], cfg) - shower_centres(hits[1], cfg), axis=1)
    return ClusterSample(
        label=np.ones(keep.sum(), dtype=np.int8),
        window=seed_windows(blocks, clusters)[keep],
        blocks=blocks[keep],
        energy=energy[keep],
        position=position[keep],
        true_energy=pi0.p4[keep, 0],
        true_position=entry[keep],
        true_separation=separation[keep],
        soft_energy=photon_energy[keep].min(axis=1),
        vertex=pi0.vertex[keep],
    )


def matched_photon_sample(merged, rng, cfg, material, fraction):
    """One single photon per merged π⁰: same energy, production point and mean entry point."""
    g = cfg["geometry"]
    e_u, e_v = face_axes(cfg)
    target = (g["distance_cm"] * array_axis(cfg)
              + merged.true_position[:, :1] * e_u + merged.true_position[:, 1:] * e_v)
    direction = target - merged.vertex
    direction /= np.linalg.norm(direction, axis=1)[:, None]
    p4 = np.column_stack((merged.true_energy, merged.true_energy[:, None] * direction))

    hits = transport_photons(p4, merged.vertex, rng, cfg, material, fraction)
    blocks = array_response([hits], rng, cfg)
    keep, clusters, energy, position = _single_cluster_selection([hits], np.zeros(len(p4), dtype=bool), blocks, cfg)
    return ClusterSample(
        label=np.zeros(keep.sum(), dtype=np.int8),
        window=seed_windows(blocks, clusters)[keep],
        blocks=blocks[keep],
        energy=energy[keep],
        position=position[keep],
        true_energy=merged.true_energy[keep],
        true_position=hits.position[keep],
        true_separation=np.zeros(keep.sum()),
        soft_energy=np.zeros(keep.sum()),
        vertex=merged.vertex[keep],
    )


def build_dataset(n_pi0, rng, cfg, material="carbon", fraction=0.02):
    """Merged π⁰ clusters and their matched single photons, in one sample."""
    merged = merged_pi0_sample(n_pi0, rng, cfg, material, fraction)
    photons = matched_photon_sample(merged, rng, cfg, material, fraction)
    return ClusterSample.concatenate([merged, photons])
