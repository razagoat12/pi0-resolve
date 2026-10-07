# Phase 2: reconstruction and feasibility

Rebuilds π⁰s from the simulated block energies and measures how well this works (research question Q1). Reconstruction code lives in `src/pi0resolve/reconstruction.py`; this folder holds the studies that tune it and test it.

| Script | What it does | Outputs |
|---|---|---|
| `calibrate.py` | Chooses W₀ for unbiased photon separations in π⁰ pairs; measures the energy response of single photons | `results/w0_scan.csv`, `results/calibration.png`, `configs/energy_calibration.csv` |
| `mass_peak.py` | Full chain → two-cluster mass with log weighting and with the two-shower fit; peak, width and efficiency vs π⁰ energy | `results/mass_peak.png`, `results/mass_vs_energy.csv` |

Run from the repository root, calibration first:

```bash
python studies/phase2/calibrate.py
python studies/phase2/mass_peak.py
```

Methods and their history are recorded in `docs/decisions.md` (D-18 to D-21).

## Status

- ✅ Clustering, log-weighted positions, fiducial cut, depth-aware mass (D-18)
- ✅ Calibration: W₀ = 3.25 and energy response (D-19)
- ✅ Single-photon position correction tried and disabled (D-20)
- ✅ Two-shower fit, validated where position information exists (D-21)
- ⚠️ **Limitation:** the peak depends on π⁰ energy because every resolved π⁰ has a photon in an edge block, where the position within the block cannot be measured (D-21)
- ⬜ Geometry scans: distance L and angle θ
- ⬜ Target comparison (Q2) with reconstructed events
