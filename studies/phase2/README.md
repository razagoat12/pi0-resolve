# Phase 2: reconstruction and feasibility

Rebuilds π⁰s from the simulated block energies and measures how well this works (research question Q1). Reconstruction code lives in `src/pi0resolve/reconstruction.py`; this folder holds the studies that tune it and test it.

| Script | What it does | Outputs |
|---|---|---|
| `calibrate.py` | Chooses W₀ for unbiased photon separations in π⁰ pairs; measures the energy response of single photons | `results/w0_scan.csv`, `results/calibration.png`, `configs/energy_calibration.csv` |
| `mass_peak.py` | Full chain → two-cluster mass; peak before/after calibration; peak, width and efficiency vs π⁰ energy | `results/mass_peak.png`, `results/mass_vs_energy.csv` |

Run from the repository root, calibration first:

```bash
python studies/phase2/calibrate.py
python studies/phase2/mass_peak.py
```

Methods and their history are recorded in `docs/decisions.md` (D-18, D-19).

## Status

- ✅ Clustering, log-weighted positions, fiducial cut, depth-aware mass
- ✅ Calibration: W₀ = 3.25 and energy response
- ✅ π⁰ peak at 131.6 MeV (−2.5 %), σ = 22 MeV, toy spectrum
- ⚠️ **Open:** peak drifts from 124 MeV (1.25 GeV π⁰s) to 152 MeV (4.75 GeV π⁰s) because photon separations are biased by position within the block grid
- ⬜ Geometry scans: distance L and angle θ
- ⬜ Target comparison (Q2) with reconstructed events
