# Phase 3: classifiers and ML positions

Can a model tell a single photon from a merged π⁰ using only the block energies (Q3), and where does the detector's block size make that impossible (Q4)? Plus: can ML positions help with the edge-block limitation found in Phase 2 (D-21)?

Setup decisions: `docs/decisions.md`, D-22 (dataset, inputs, baselines) and D-23 (ML positions).

| Script | What it does | Outputs |
|---|---|---|
| `train.py` | Builds the labelled dataset (cached in `data/phase3/`), trains logistic regression, boosted trees and a neural network on shape features and on the raw 3 × 3 window, and compares them with the width-cut and shower-fit Δχ² baselines | `results/metrics.csv`, `results/auc_vs_energy.csv`, `results/classifiers.png` |
| `position.py` | Compares log weighting, the two-shower fit and ML regression for single photons (error vs position) and π⁰ pairs (separation and mass vs energy, same events) | `results/position.png`, `results/position_single.csv`, `results/position_pairs.csv` |

```bash
python studies/phase3/train.py --n-pi0 1500000
python studies/phase3/position.py
```

Generated datasets are not committed; they are rebuilt from the seed in `configs/default.yaml`.

**Caveat for ML positions:** no model can recover information the blocks do not contain. Where an edge block hides a photon's position, a model can only learn the typical position under the simulation's assumptions. Phase 4 tests how much results depend on those assumptions.
