"""Four-vector helpers.

Conventions (D-12): energies and momenta in GeV, natural units (c = 1).
A four-vector array has shape (N, 4) with columns [E, px, py, pz];
a three-vector array has shape (N, 3).
"""

import numpy as np


def isotropic_directions(n, rng):
    """Return `n` unit vectors uniformly distributed over the sphere.

    Uniform on the sphere means cos(theta) uniform in [-1, 1] and phi uniform
    in [0, 2*pi). Drawing theta itself uniformly would crowd points at the poles.
    """
    cos_theta = rng.uniform(-1.0, 1.0, n)
    phi = rng.uniform(0.0, 2.0 * np.pi, n)
    sin_theta = np.sqrt(1.0 - cos_theta**2)
    return np.column_stack((sin_theta * np.cos(phi), sin_theta * np.sin(phi), cos_theta))


def rotate_from_z(vectors, axis):
    """Rotate three-vectors (N, 3) so that the z-axis is carried onto `axis`.

    Builds a right-handed basis (u, v, axis) and maps (x, y, z) to
    x*u + y*v + z*axis. Lengths and angles between vectors are preserved.
    """
    axis = np.asarray(axis, dtype=float)
    axis = axis / np.linalg.norm(axis)
    helper = np.array([0.0, 1.0, 0.0]) if abs(axis[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(helper, axis)
    u /= np.linalg.norm(u)
    v = np.cross(axis, u)
    return vectors[:, :1] * u + vectors[:, 1:2] * v + vectors[:, 2:] * axis


def four_momentum(energy, direction, mass):
    """Build four-vectors from energy (N,), unit direction (N, 3) and mass.

    |p| = sqrt(E^2 - m^2), so E must be at least m.
    """
    energy = np.asarray(energy, dtype=float)
    p = np.sqrt(np.maximum(energy**2 - mass**2, 0.0))
    return np.column_stack((energy, p[:, None] * direction))


def boost(p4, beta):
    """Lorentz-boost four-vectors `p4` (N, 4) by velocity vectors `beta` (N, 3).

    A particle at rest in the original frame ends up moving with velocity beta.
    With gamma = 1 / sqrt(1 - beta^2):

        E' = gamma * (E + beta . p)
        p' = p + (gamma^2 / (gamma + 1) * (beta . p) + gamma * E) * beta

    The textbook form has (gamma - 1) / beta^2 in place of gamma^2 / (gamma + 1).
    The two are equal, but this form never divides by beta^2, so beta = 0
    (no boost) is handled without special cases.
    """
    energy = p4[:, 0]
    p = p4[:, 1:]
    beta2 = np.sum(beta**2, axis=1)
    gamma = 1.0 / np.sqrt(1.0 - beta2)
    beta_dot_p = np.sum(beta * p, axis=1)

    energy_new = gamma * (energy + beta_dot_p)
    coeff = gamma**2 / (gamma + 1.0) * beta_dot_p + gamma * energy
    p_new = p + coeff[:, None] * beta
    return np.column_stack((energy_new, p_new))


def invariant_mass(p4a, p4b):
    """Invariant mass of two four-vectors: m^2 = (Ea + Eb)^2 - |pa + pb|^2."""
    total = p4a + p4b
    m2 = total[:, 0] ** 2 - np.sum(total[:, 1:] ** 2, axis=1)
    return np.sqrt(np.maximum(m2, 0.0))


def opening_angle(p4a, p4b):
    """Angle between the momenta of two four-vectors, in rad.

    Uses atan2(|a x b|, a . b), which stays accurate at small angles where
    arccos(a . b / |a||b|) loses precision.
    """
    a = p4a[:, 1:]
    b = p4b[:, 1:]
    cross = np.linalg.norm(np.cross(a, b), axis=1)
    dot = np.sum(a * b, axis=1)
    return np.arctan2(cross, dot)
