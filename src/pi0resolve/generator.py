"""π⁰ generator: momenta, production points and decay-mode tags (D-15).

Coordinates: z along the beam, target centred at the origin, array centre at
L·(sin θ, 0, cos θ) in the x-z plane. Units: GeV, cm, rad.

Two sampling modes:
- "physics": π⁰ momenta from a production spectrum around the beam axis
  (toy model now, HARP-based later, D-02). For acceptance and yields (Q1, Q2).
- "flat": energy uniform in [E_min, E_max], directions uniform inside a cone
  aimed at the array. For per-energy-bin classifier samples (Q3, Q4, D-11).
  It deliberately ignores the real energy-angle spectrum.
"""

from dataclasses import dataclass

import numpy as np

from .constants import PI0_MASS
from .decay import is_dalitz
from .kinematics import four_momentum, rotate_from_z


@dataclass
class Pi0Sample:
    p4: np.ndarray         # (N, 4) π⁰ four-momenta, GeV
    vertex: np.ndarray     # (N, 3) production points, cm
    is_dalitz: np.ndarray  # (N,) True for π⁰ → e⁺e⁻γ, rejected downstream (D-13)

    def __len__(self):
        return len(self.p4)


def generate_pi0s(n, rng, cfg, material, thickness_fraction, mode="physics"):
    """Generate `n` π⁰s produced in a target of `material` (e.g. "copper")
    whose thickness is `thickness_fraction` of its interaction length."""
    pi0_cfg = cfg["pi0"]
    e_min, e_max = pi0_cfg["energy_min_gev"], pi0_cfg["energy_max_gev"]

    if mode == "physics":
        if pi0_cfg["spectrum"] != "toy":
            raise NotImplementedError("only the toy spectrum exists so far (D-02)")
        toy = pi0_cfg["toy"]
        p, direction = toy_momenta(
            n, rng,
            p_min=np.sqrt(e_min**2 - PI0_MASS**2),
            p_max=np.sqrt(e_max**2 - PI0_MASS**2),
            slope=toy["momentum_slope_gev"],
            temperature=toy["pt_temperature_gev"],
        )
        energy = np.sqrt(p**2 + PI0_MASS**2)
    elif mode == "flat":
        energy = rng.uniform(e_min, e_max, n)
        direction = cone_directions(n, rng, array_axis(cfg), aim_half_angle(cfg))
    else:
        raise ValueError(f"unknown mode {mode!r}; use 'physics' or 'flat'")

    target = cfg["targets"]["materials"][material]
    vertex = sample_vertices(
        n, rng,
        thickness_cm=thickness_fraction * target["lambda_i_cm"],
        lambda_i_cm=target["lambda_i_cm"],
        spot_sigma_cm=cfg["beam"]["spot_sigma_cm"],
    )
    return Pi0Sample(four_momentum(energy, direction, PI0_MASS), vertex, is_dalitz(n, rng))


def toy_momenta(n, rng, p_min, p_max, slope, temperature):
    """Toy production spectrum around the beam (z) axis.

    - Momentum: dN/dp ~ exp(-p / slope), truncated to [p_min, p_max].
    - Transverse momentum: dN/dpT ~ pT exp(-pT / T), redrawn until pT < p.
    - Polar angle: sin θ = pT / p (forward hemisphere); azimuth uniform.

    Returns momentum magnitudes (N,) and unit directions (N, 3).
    """
    # Inverse CDF of the truncated exponential; kept = 1 - exp(-(p_max - p_min) / slope)
    kept = -np.expm1(-(p_max - p_min) / slope)
    p = p_min - slope * np.log1p(-rng.random(n) * kept)

    pt = rng.gamma(2.0, temperature, n)
    too_large = pt >= p
    while np.any(too_large):
        pt[too_large] = rng.gamma(2.0, temperature, np.count_nonzero(too_large))
        too_large = pt >= p

    sin_theta = pt / p
    cos_theta = np.sqrt(1.0 - sin_theta**2)
    phi = rng.uniform(0.0, 2.0 * np.pi, n)
    direction = np.column_stack((sin_theta * np.cos(phi), sin_theta * np.sin(phi), cos_theta))
    return p, direction


def cone_directions(n, rng, axis, half_angle):
    """Unit vectors uniform in solid angle within `half_angle` of `axis`."""
    cos_alpha = rng.uniform(np.cos(half_angle), 1.0, n)
    sin_alpha = np.sqrt(1.0 - cos_alpha**2)
    phi = rng.uniform(0.0, 2.0 * np.pi, n)
    local = np.column_stack((sin_alpha * np.cos(phi), sin_alpha * np.sin(phi), cos_alpha))
    return rotate_from_z(local, axis)


def sample_vertices(n, rng, thickness_cm, lambda_i_cm, spot_sigma_cm):
    """Production points inside the target.

    x, y: Gaussian beam spot. z: the beam is attenuated as exp(-s / λ_I) with
    depth s, so interactions follow that law truncated to [0, t] (inverse CDF),
    then shifted so the target is centred on z = 0.
    """
    xy = rng.normal(0.0, spot_sigma_cm, (n, 2))
    # Inverse CDF; interacting = 1 - exp(-t / λ_I), the interaction probability
    interacting = -np.expm1(-thickness_cm / lambda_i_cm)
    depth = -lambda_i_cm * np.log1p(-rng.random(n) * interacting)
    return np.column_stack((xy, depth - 0.5 * thickness_cm))


def array_axis(cfg):
    """Unit vector from the target centre to the array centre."""
    theta = cfg["geometry"]["angle_rad"]
    return np.array([np.sin(theta), 0.0, np.cos(theta)])


def aim_half_angle(cfg):
    """Cone half-angle for flat mode: the array's half-diagonal plus a margin."""
    g = cfg["geometry"]
    half_diagonal = 0.5 * g["blocks_per_side"] * g["block_size_cm"] * np.sqrt(2.0)
    return np.arctan(half_diagonal / g["distance_cm"]) + cfg["pi0"]["flat"]["aim_margin_rad"]
