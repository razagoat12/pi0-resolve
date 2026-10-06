"""Photon transport from the production point to the array face (D-16).

Each photon flies in a straight line through three materials:
target (to its exit face) → air → veto paddle (directly in front of the array).
It converts to an e⁺e⁻ pair with probability

    P = 1 - exp(-(7/9) · Σ x_i / X0_i)

the high-energy limit of pair production. At a few hundred MeV the true
probability is somewhat lower, so this slightly overestimates losses for
soft photons (stated as a limitation in D-16).

Coordinates as in the generator: z along the beam, target centred at the
origin, array face centred at L·n with n = (sin θ, 0, cos θ) facing the target.
Positions on the array face use the axes u = R·x̂, v = R·ŷ, where R carries
ẑ onto n (the same rotation as kinematics.rotate_from_z).
"""

from dataclasses import dataclass

import numpy as np

from .generator import array_axis
from .kinematics import rotate_from_z

PAIR_FACTOR = 7.0 / 9.0  # mean free path for pair production = (9/7) X0


@dataclass
class PhotonHits:
    energy: np.ndarray          # (N,) GeV
    on_array: np.ndarray        # (N,) bool: straight line reaches the array face
    position: np.ndarray        # (N, 2) cm on the face (u, v); NaN if it never reaches the plane
    direction: np.ndarray       # (N, 3) unit direction in face axes (u, v, n), for shower incidence
    path_target_cm: np.ndarray  # (N,)
    path_air_cm: np.ndarray     # (N,) only meaningful where on_array
    path_veto_cm: np.ndarray    # (N,) only meaningful where on_array
    converted: np.ndarray       # (N,) bool: converted to e⁺e⁻ before the array


def transport_photons(p4, vertex, rng, cfg, material, thickness_fraction):
    """Trace photons (N, 4) from production points (N, 3) to the array face."""
    g, tr = cfg["geometry"], cfg["transport"]
    target = cfg["targets"]["materials"][material]
    thickness = thickness_fraction * target["lambda_i_cm"]

    direction = p4[:, 1:] / np.linalg.norm(p4[:, 1:], axis=1)[:, None]
    n_axis = array_axis(cfg)
    e_u, e_v = face_axes(cfg)

    path_target = target_exit_distance(
        vertex, direction,
        half_sizes=(0.5 * cfg["targets"]["transverse_size_cm"],) * 2 + (0.5 * thickness,),
    )

    # Straight line to the plane of the array face
    toward = direction @ n_axis
    centre = g["distance_cm"] * n_axis
    reaches_plane = toward > 0.0
    distance = np.full(len(p4), np.nan)
    distance[reaches_plane] = ((centre - vertex[reaches_plane]) @ n_axis) / toward[reaches_plane]
    offset = vertex + distance[:, None] * direction - centre
    position = np.column_stack((offset @ e_u, offset @ e_v))

    half = 0.5 * g["blocks_per_side"] * g["block_size_cm"]
    with np.errstate(invalid="ignore"):
        on_array = reaches_plane & np.all(np.abs(position) <= half, axis=1)

    # Material along the path (air and veto only matter for photons that reach the array)
    path_veto = np.where(on_array, tr["veto_thickness_cm"] / np.where(toward > 0, toward, 1.0), 0.0)
    path_air = np.where(on_array, distance - path_target - path_veto, 0.0)
    radiation_lengths = (path_target / target["x0_cm"]
                         + path_air / tr["air_x0_cm"]
                         + path_veto / tr["veto_x0_cm"])
    converted = rng.random(len(p4)) < -np.expm1(-PAIR_FACTOR * radiation_lengths)

    local_direction = np.column_stack((direction @ e_u, direction @ e_v, toward))
    return PhotonHits(p4[:, 0], on_array, position, local_direction,
                      path_target, path_air, path_veto, converted)


def event_status(is_dalitz, photons):
    """Combine per-photon results into per-event flags.

    vetoed: a Dalitz decay (D-13), or any photon that converted and still
            reaches the array, since its e⁺e⁻ pair fires the veto (D-16).
    accepted: not vetoed, and every photon reaches the array unconverted.
    A converted photon that misses the array is simply lost.
    """
    vetoed = np.array(is_dalitz, dtype=bool)
    complete = np.ones_like(vetoed)
    for hits in photons:
        vetoed = vetoed | (hits.converted & hits.on_array)
        complete = complete & hits.on_array & ~hits.converted
    return vetoed, complete & ~vetoed


def target_exit_distance(vertex, direction, half_sizes):
    """Distance along `direction` from inside a centred box to its surface.

    For each axis the photon reaches the wall it is heading toward at
    (±h - x) / d; the exit is the nearest of the three walls.
    """
    half_sizes = np.asarray(half_sizes, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        wall = np.where(direction > 0, half_sizes, -half_sizes)
        steps = np.where(direction != 0, (wall - vertex) / direction, np.inf)
    return np.maximum(steps.min(axis=1), 0.0)


def face_axes(cfg):
    """Unit vectors (u, v) spanning the array face."""
    n_axis = array_axis(cfg)
    e_u = rotate_from_z(np.array([[1.0, 0.0, 0.0]]), n_axis)[0]
    e_v = rotate_from_z(np.array([[0.0, 1.0, 0.0]]), n_axis)[0]
    return e_u, e_v
