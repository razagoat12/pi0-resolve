"""Phase 3: single photon vs merged π⁰ classifiers (Q3, Q4; D-10, D-22).

Methods, all scored on the same held-out test set:
  - width cut            (baseline, no training)
  - shower-fit Δχ²       (baseline, no training: one vs two showers, D-22)
  - logistic regression  (shape features and raw window)
  - boosted trees        (shape features and raw window)
  - neural network (MLP) (shape features and raw window)
Split 60 / 20 / 20 (train / validation / test). Model settings are chosen on
the validation set only; the test set is used once, for the numbers reported.

Sanity checks (D-09): a classifier given only the cluster energy, or only
the true entry position, should be close to AUC 0.5.

Usage:  python studies/phase3/train.py [--n-pi0 1500000]
Outputs: studies/phase3/results/{metrics.csv, auc_vs_energy.csv, classifiers.png}
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from pi0resolve.config import load_config, repo_path
from pi0resolve.dataset import ClusterSample, build_dataset
from pi0resolve.ml.features import raw_features, shape_features, width_score
from pi0resolve.showerfit import merged_score

RESULTS = Path(__file__).resolve().parent / "results"
ENERGY_EDGES = np.arange(0.5, 5.0001, 0.5)        # GeV, for per-bin AUC
MIN_PER_CLASS = 50                                # per bin, to report an AUC
OVERLAP_CM = 20.0                                 # true photon separation below which a merged π⁰ is an overlap


def split(n, rng):
    order = rng.permutation(n)
    a, b = int(0.6 * n), int(0.8 * n)
    return order[:a], order[a:b], order[b:]


def candidates():
    """Model families with a small grid of settings each (chosen on validation)."""
    return {
        "logistic regression": [make_pipeline(StandardScaler(), LogisticRegression(C=c, max_iter=2000))
                                for c in (0.1, 1.0, 10.0)],
        "boosted trees": [HistGradientBoostingClassifier(learning_rate=lr, max_iter=300, random_state=0)
                          for lr in (0.05, 0.1, 0.2)],
        "neural network": [make_pipeline(StandardScaler(), MLPClassifier(hidden_layer_sizes=h, early_stopping=True,
                                                                         max_iter=300, random_state=0))
                           for h in ((32,), (32, 32), (64, 64))],
    }


def photon_efficiency_at_rejection(label, score, rejection=0.90):
    """Fraction of photons kept when the cut rejects `rejection` of merged π⁰s (high score = π⁰)."""
    cut = np.quantile(score[label == 1], 1.0 - rejection)
    return np.mean(score[label == 0] < cut)


def auc_by_energy(label, score, energy):
    out = []
    for lo, hi in zip(ENERGY_EDGES[:-1], ENERGY_EDGES[1:]):
        k = (energy >= lo) & (energy < hi)
        enough = min(np.sum(label[k] == 1), np.sum(label[k] == 0)) >= MIN_PER_CLASS
        out.append(roc_auc_score(label[k], score[k]) if enough else np.nan)
    return np.array(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-pi0", type=int, default=1_500_000)
    args = parser.parse_args()

    cfg = load_config()
    rng = np.random.default_rng(cfg["seed"])
    RESULTS.mkdir(parents=True, exist_ok=True)
    cache = repo_path(f"data/phase3/dataset_{args.n_pi0}_{cfg['seed']}.npz")
    if cache.exists():
        data = ClusterSample.load(cache)
    else:
        data = build_dataset(args.n_pi0, rng, cfg)
        cache.parent.mkdir(parents=True, exist_ok=True)
        data.save(cache)
    print(f"dataset: {len(data):,} clusters ({data.label.sum():,} merged π⁰, {(data.label == 0).sum():,} photons)")

    threshold = cfg["detector"]["threshold_noise_sigmas"] * cfg["detector"]["noise_gev"]
    flat = data.blocks.reshape(len(data), -1)
    inputs = {"shape": shape_features(data.window, data.energy, threshold),
              "raw": raw_features(data.window, data.energy),
              # all 16 blocks: can see a second photon that leaked away from the window
              "array": np.column_stack((flat / flat.sum(axis=1)[:, None], np.log(data.energy)))}
    train, valid, test = split(len(data), rng)
    y = data.label

    scores, chosen = {}, {}
    scores["width cut"] = width_score(data.window[test], data.energy[test], threshold)
    scores["shower-fit Δχ²"], _, _ = merged_score(data.blocks[test], data.energy[test], data.position[test], cfg)

    for family, models in candidates().items():
        for input_name, x in inputs.items():
            if input_name == "array" and family == "logistic regression":
                continue
            best_auc, best = -1.0, None
            for model in models:
                model.fit(x[train], y[train])
                auc = roc_auc_score(y[valid], model.predict_proba(x[valid])[:, 1])
                if auc > best_auc:
                    best_auc, best = auc, model
            name = f"{family} ({input_name})"
            scores[name] = best.predict_proba(x[test])[:, 1]
            chosen[name] = f"validation AUC {best_auc:.4f}: {best}"
            print(f"trained {name}")

    # Sanity checks: energy only, true position only (boosted trees, D-09)
    sanity = {}
    for name, x in (("cluster energy only", np.log(data.energy)[:, None]),
                    ("true entry position only", data.true_position),
                    ("raw window WITHOUT energy (should stay high)", inputs["raw"][:, :-1])):
        model = HistGradientBoostingClassifier(random_state=0).fit(x[train], y[train])
        sanity[name] = roc_auc_score(y[test], model.predict_proba(x[test])[:, 1])

    # Metrics
    y_test, e_test = y[test], data.true_energy[test]
    # Overlap: photons less than two blocks apart. Lost: the second photon is far
    # away and formed no cluster (mostly leaked off the array edge, D-21).
    overlap = (data.true_separation[test] < OVERLAP_CM) & (y_test == 1)
    lost_soft = (data.true_separation[test] >= OVERLAP_CM) & (y_test == 1)
    rows, per_energy = [], {}
    print(f"\n{'method':34s} {'AUC':>6s} {'γ eff @90% π⁰ rej':>18s} {'AUC overlap':>12s} {'AUC lost γ':>11s}")
    for name, score in scores.items():
        auc = roc_auc_score(y_test, score)
        eff = photon_efficiency_at_rejection(y_test, score)
        photons = y_test == 0
        auc_overlap = roc_auc_score(y_test[overlap | photons], score[overlap | photons])
        auc_soft = roc_auc_score(y_test[lost_soft | photons], score[lost_soft | photons])
        rows.append((name, auc, eff, auc_overlap, auc_soft))
        per_energy[name] = auc_by_energy(y_test, score, e_test)
        print(f"{name:34s} {auc:6.4f} {eff:18.3f} {auc_overlap:12.4f} {auc_soft:14.4f}")
    print("\nsanity checks (first two should be near 0.5):")
    for name, auc in sanity.items():
        print(f"  {name}: AUC {auc:.4f}")
    print(f"test set: {overlap.sum():,} overlapping π⁰, {lost_soft.sum():,} π⁰ whose second photon was lost, "
          f"{(y_test == 0).sum():,} photons")
    for name, text in chosen.items():
        print(f"  chosen {name}: {text}")

    with open(RESULTS / "metrics.csv", "w", encoding="utf-8") as f:
        f.write("method,auc,photon_efficiency_at_90pc_pi0_rejection,auc_overlap,auc_second_photon_lost\n")
        for r in rows:
            f.write(f"{r[0]},{r[1]:.5f},{r[2]:.5f},{r[3]:.5f},{r[4]:.5f}\n")
        for name, auc in sanity.items():
            f.write(f"sanity: {name},{auc:.5f},,,\n")
    centres = 0.5 * (ENERGY_EDGES[1:] + ENERGY_EDGES[:-1])
    np.savetxt(RESULTS / "auc_vs_energy.csv", np.column_stack([centres] + list(per_energy.values())),
               delimiter=",", comments="", fmt="%.5f", header="energy_gev," + ",".join(per_energy), encoding="utf-8")

    # Figure
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(15, 5.4), constrained_layout=True)
    colours = plt.cm.tab10(np.linspace(0, 1, len(scores)))
    for (name, score), colour in zip(scores.items(), colours):
        fpr, tpr, _ = roc_curve(y_test, score)
        ax_a.plot(1 - fpr, tpr, color=colour, lw=1.6, label=f"{name} ({roc_auc_score(y_test, score):.3f})")
        ax_b.plot(centres, per_energy[name], "o-", color=colour, lw=1.3, ms=4, label=name)
    ax_a.set(xlabel="photon efficiency (photons kept)", ylabel="π⁰ rejection (merged π⁰ removed)",
             title="(a) ROC curves on the test set (AUC)")
    ax_a.legend(fontsize=7, loc="lower left")
    ax_b.axhline(0.5, color="#8A97B4", ls=":", lw=1)
    ax_b.set(xlabel=r"$\pi^0$ / photon energy (GeV)", ylabel="AUC", ylim=(0.45, 1.01),
             title="(b) Separation vs energy (Q4)")
    ax_b.legend(fontsize=7, loc="lower right")
    fig.suptitle(f"Phase 3 · single photon vs merged π⁰ · {len(test):,} test clusters · seed {cfg['seed']}")
    fig.savefig(RESULTS / "classifiers.png", dpi=150)
    print(f"wrote {RESULTS / 'classifiers.png'}")


if __name__ == "__main__":
    main()
