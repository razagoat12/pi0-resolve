"""The default config must match the decision log (docs/decisions.md)."""

import numpy as np

from pi0resolve.config import load_config


def test_default_config_matches_decisions():
    cfg = load_config()

    beam = cfg["beam"]  # D-01, D-15
    assert beam == {"particle": "proton", "momentum_gev": 8.0, "spot_sigma_cm": 0.5}

    pi0 = cfg["pi0"]  # D-03: 0.5-5 GeV in 0.25 GeV bins = 18 bins
    n_bins = (pi0["energy_max_gev"] - pi0["energy_min_gev"]) / pi0["energy_bin_gev"]
    assert np.isclose(n_bins, 18)

    targets = cfg["targets"]  # D-04
    assert set(targets["materials"]) == {"carbon", "copper", "tin"}
    assert targets["thickness_fractions_lambda_i"] == [0.02, 0.05]

    geometry = cfg["geometry"]  # D-05
    assert geometry["distance_cm"] == 150.0
    assert np.isclose(geometry["angle_rad"], np.radians(12.0), atol=1e-4)

    assert cfg["clustering"]["seed_threshold_gev"] == 0.100  # D-08

    rec = cfg["reconstruction"]  # D-18, D-19
    assert rec["log_weight_w0"] == 3.25
    assert rec["fiducial_margin_cm"] == 5.0
