"""Checks for photon transport (D-16)."""

import numpy as np
import pytest

from pi0resolve.config import load_config
from pi0resolve.generator import array_axis
from pi0resolve.transport import (
    PhotonHits,
    event_status,
    face_axes,
    target_exit_distance,
    transport_photons,
)

SEED = 4242
# Written out independently of transport.PAIR_FACTOR, so a wrong constant there is caught
SEVEN_NINTHS = 7.0 / 9.0
CFG = load_config()
L = CFG["geometry"]["distance_cm"]
HALF = 0.5 * CFG["geometry"]["blocks_per_side"] * CFG["geometry"]["block_size_cm"]


def photons_toward(points, vertex=(0.0, 0.0, 0.0), energy=1.0):
    """Photons from `vertex` aimed at 3D `points`, as (N, 4) four-vectors."""
    vertex = np.broadcast_to(np.asarray(vertex, dtype=float), np.shape(points))
    d = points - vertex
    d = d / np.linalg.norm(d, axis=1)[:, None]
    return np.column_stack((np.full(len(d), energy), energy * d)), np.array(vertex)


def face_point(u, v):
    e_u, e_v = face_axes(CFG)
    return L * array_axis(CFG) + u * e_u + v * e_v


def transport(p4, vertex, material="copper", fraction=0.05, seed=SEED):
    return transport_photons(p4, vertex, np.random.default_rng(seed), CFG, material, fraction)


# --- target geometry ---------------------------------------------------------------

def test_exit_distance_through_each_wall():
    half = (2.5, 2.5, 0.5)
    vertex = np.zeros((4, 3))
    direction = np.array([[0, 0, 1], [1, 0, 0], [0, -1, 0], [0, 0, -1]], dtype=float)
    assert np.allclose(target_exit_distance(vertex, direction, half), [0.5, 2.5, 2.5, 0.5])


def test_exit_distance_at_an_angle_and_from_the_back_face():
    half = (2.5, 2.5, 0.5)
    tilted = np.array([[np.sin(0.3), 0.0, np.cos(0.3)]])
    assert np.isclose(target_exit_distance(np.zeros((1, 3)), tilted, half)[0], 0.5 / np.cos(0.3))
    assert target_exit_distance(np.array([[0.0, 0.0, 0.5]]), tilted, half)[0] == 0.0


def test_exit_through_side_when_nearer():
    """Near the side wall, a wide-angle photon leaves through the side."""
    vertex = np.array([[2.4, 0.0, -0.5]])
    direction = np.array([[np.sin(0.5), 0.0, np.cos(0.5)]])
    assert np.isclose(target_exit_distance(vertex, direction, (2.5, 2.5, 0.5))[0], 0.1 / np.sin(0.5))


# --- array geometry ----------------------------------------------------------------

def test_photon_lands_where_aimed():
    targets = np.array([face_point(u, v) for u, v in [(0, 0), (12.3, -7.0), (-19.9, 19.9)]])
    hits = transport(*photons_toward(targets))
    assert np.all(hits.on_array)
    assert np.allclose(hits.position, [[0, 0], [12.3, -7.0], [-19.9, 19.9]], atol=1e-9)


def test_photon_off_the_face_or_backward_misses():
    p4_off, v = photons_toward(np.array([face_point(HALF + 0.1, 0.0)]))
    p4_back = np.array([[1.0, 0.0, 0.0, -1.0]])
    assert not transport(p4_off, v).on_array[0]
    back = transport(p4_back, np.zeros((1, 3)))
    assert not back.on_array[0] and np.all(np.isnan(back.position[0]))


def test_path_lengths_add_up_to_flight_distance():
    rng = np.random.default_rng(SEED)
    points = np.array([face_point(u, v) for u, v in rng.uniform(-HALF, HALF, (200, 2))])
    vertex = np.column_stack((rng.normal(0, 0.5, 200), rng.normal(0, 0.5, 200), rng.uniform(-0.38, 0.38, 200)))
    hits = transport(*photons_toward(points, vertex))
    flight = np.linalg.norm(points - vertex, axis=1)
    total = hits.path_target_cm + hits.path_air_cm + hits.path_veto_cm
    assert np.all(hits.on_array)
    assert np.allclose(total, flight, rtol=1e-12)


def test_veto_path_grows_with_incidence_angle():
    hits = transport(*photons_toward(np.array([face_point(0, 0), face_point(19.0, 19.0)])))
    w = CFG["transport"]["veto_thickness_cm"]
    assert np.isclose(hits.path_veto_cm[0], w)
    assert np.isclose(hits.path_veto_cm[1], w / hits.direction[1, 2])
    assert hits.path_veto_cm[1] > w


# --- conversion -----------------------------------------------------------------

@pytest.mark.parametrize("material", ["carbon", "copper", "tin"])
def test_conversion_rate_matches_material_budget(material):
    """Photons from the target centre to the array centre convert at
    1 - exp(-(7/9) Σ x/X0), within 5 sigma."""
    n = 400_000
    points = np.tile(face_point(0, 0), (n, 1))
    hits = transport(*photons_toward(points), material=material, fraction=0.05)

    t = 0.05 * CFG["targets"]["materials"][material]["lambda_i_cm"]
    x0 = CFG["targets"]["materials"][material]["x0_cm"]
    cos_theta = np.cos(CFG["geometry"]["angle_rad"])
    w = CFG["transport"]["veto_thickness_cm"]
    x_target = 0.5 * t / cos_theta
    budget = x_target / x0 + (L - x_target - w) / CFG["transport"]["air_x0_cm"] + w / CFG["transport"]["veto_x0_cm"]
    expected = 1.0 - np.exp(-SEVEN_NINTHS * budget)

    sigma = np.sqrt(expected * (1 - expected) / n)
    assert abs(hits.converted.mean() - expected) < 5 * sigma


def test_heavier_targets_convert_more_at_equal_interaction_length():
    points = np.tile(face_point(0, 0), (200_000, 1))
    rates = {m: transport(*photons_toward(points), material=m).converted.mean()
             for m in ("carbon", "copper", "tin")}
    assert rates["carbon"] < rates["copper"] < rates["tin"]


# --- event-level rules ------------------------------------------------------------

def make_hits(on_array, converted):
    n = len(on_array)
    z = np.zeros(n)
    return PhotonHits(z, np.array(on_array), np.zeros((n, 2)), np.zeros((n, 3)), z, z, z, np.array(converted))


def test_event_status_truth_table():
    #            event:   0      1      2      3      4      5
    dalitz =             [False, False, False, False, True,  False]
    g1 = make_hits(on_array=[True, True, True, False, True, True],
                   converted=[False, True, False, True, False, False])
    g2 = make_hits(on_array=[True, True, False, True, True, True],
                   converted=[False, False, False, False, False, True])
    vetoed, accepted = event_status(dalitz, [g1, g2])
    # 0 clean · 1 converted γ hits array → veto · 2 γ2 misses → not accepted, not vetoed
    # 3 converted γ1 misses array → lost, not vetoed · 4 Dalitz → veto · 5 converted γ2 hits → veto
    assert list(vetoed) == [False, True, False, False, True, True]
    assert list(accepted) == [True, False, False, False, False, False]


def test_same_seed_is_reproducible():
    points = np.tile(face_point(3.0, -4.0), (1_000, 1))
    a = transport(*photons_toward(points), seed=9)
    b = transport(*photons_toward(points), seed=9)
    assert np.array_equal(a.converted, b.converted)
