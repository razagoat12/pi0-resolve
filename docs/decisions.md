# Decision log

This file records every choice that shapes the simulation, **before** results exist. Each entry gives the question, why it matters, the facts we found, and the options. The **Decision** and **Rationale** fields are filled in by the team, in our own words.

**Rules**

1. An entry is `Open` until a choice is made, `Proposed` until the whole team confirms it, then `Decided` with a date.
2. A decided entry is never edited. To change it, add a new entry that says `Supersedes D-xx` and explains why.
3. Every number used in the code must trace back to an entry here or to `configs/default.yaml`.
4. Suggestions in this file are starting points, not decisions.

**Units used everywhere:** energy and momentum in GeV (GeV/c), length in cm, angles in rad (degrees only in text).

## Index

| ID | Decision | Status |
|---|---|---|
| D-01 | Beam particle and momentum | Proposed |
| D-02 | π⁰ production model | Proposed |
| D-03 | π⁰ energy range | Proposed |
| D-04 | Target materials and thickness | Proposed |
| D-05 | Geometry: distance *L* and angle *θ* | Proposed |
| D-06 | Lead-glass properties and shower model | Proposed |
| D-07 | Detector response: resolution, noise, gains | Proposed |
| D-08 | Clustering and the definition of "merged" | Proposed |
| D-09 | Labels and energy matching | Proposed |
| D-10 | ML inputs, models, data split, metrics | Proposed |
| D-11 | Sample sizes and random seeds | Proposed |
| D-12 | Software conventions | Proposed |
| D-13 | π⁰ decay modes | Proposed |
| D-14 | Other neutral mesons and multiple π⁰s per event | Proposed |
| D-15 | Generator: sampling modes and production point | Proposed |
| D-16 | Photon transport: target size, material in the path, conversions | Proposed |
| D-17 | Detector response details | Proposed |
| D-18 | Reconstruction method and Phase 2 layout | Proposed |
| D-19 | Calibration: W₀ and energy response | Proposed |
| D-20 | Single-photon position correction (tried, disabled) | Proposed |
| D-21 | Two-shower fit, and the edge-block limitation | Proposed |
| D-22 | Phase 3 setup: dataset, inputs, baselines, scope | Proposed |
| D-23 | ML position estimates | Proposed |

---

## D-01 · Beam particle and momentum

**Status:** Proposed (2026-10-06), pending team confirmation

**Question:** Which projectile(s) and which single beam momentum do we simulate?

**Why it matters:** It sets the π⁰ energy spectrum and decides which published data we can use directly.

**Facts**
- The CERN PS test beam used by BL4S delivers 0.5–15 GeV/c. A positive beam is mostly protons and π⁺. Expect 10⁴–10⁵ particles per spill, spills of about 400 ms, and 1–3 spills per minute. *(BL4S 2026 Beams and Detectors)*
- HARP measured pion production by protons on carbon and copper at **3, 5, 8 and 12 GeV/c**, in the **T9 beamline of the CERN PS**. *(HARP, arXiv:0907.3857)*
- HARP also measured production with incoming π± beams on some targets. *(arXiv:0902.2105; check which targets and momenta)*
- Our 2026 proposal used 6 GeV/c, which HARP did **not** measure.

**Options**

| Option | For | Against |
|---|---|---|
| A. Protons only | Simplest; HARP proton data cover C and Cu | Ignores the π⁺ part of the real beam |
| B. π⁺ only | Matches a Cherenkov-tagged pion sample | Less HARP data available |
| C. Both, tagged separately | Matches the real mixed beam; enables a projectile comparison later | Doubles the work |

**Starting suggestion:** Option A at **8 GeV/c** (or 5 GeV/c), a momentum where HARP data exist, so no interpolation is needed. Keep Option C as a later extension.

**Decision:** Option A, protons only, at a fixed beam momentum of **8 GeV/c**.

**Rationale (our words):** _______________

**Decided by / date:** Proposed 2026-10-06, pending team confirmation

**Revisit if:** _______________

---

## D-02 · π⁰ production model

**Status:** Proposed (2026-10-06), pending team confirmation

**Question:** Where do the π⁰ energies and angles come from?

**Why it matters:** This is the biggest source of uncertainty in absolute yields. It doesn't change the decay physics or the detector response.

**Facts**
- HARP forward data cover 0.5 < p < 8.0 GeV/c and 0.025 < θ < 0.25 rad for p + C and p + Cu. *(arXiv:0907.3857)*
- HARP measured **charged** pions only. A standard approximation is that π⁰ production ≈ the average of π⁺ and π⁻ production (isospin symmetry). It is an approximation and must be stated as one.
- Typical transverse momentum of produced pions is a few hundred MeV/c.

**Options**

| Option | For | Against |
|---|---|---|
| A. Toy model: exponential in transverse momentum, simple longitudinal shape | Fast, transparent, good for the first working version | Not tied to data |
| B. HARP-based: π⁰ ≈ (π⁺ + π⁻)/2 from published HARP tables | Real data from the same beamline and targets | Need to read or digitise the tables; isospin approximation |
| C. Geant4 event generator | Most realistic, includes backgrounds | Steep learning curve |

**Starting suggestion:** A for Phase 1 (to get the pipeline working), B as the default for all results, C as a stretch goal.

**Decision:** Toy model (A) for Phase 1 only. All reported results use HARP-based spectra (B), with π⁰ ≈ (π⁺ + π⁻)/2 for p + C and p + Cu at 8 GeV/c. Geant4 (C) is a stretch goal.

**Rationale (our words):** _______________

**Decided by / date:** Proposed 2026-10-06, pending team confirmation

**Revisit if:** _______________

---

## D-03 · π⁰ energy range

**Status:** Proposed (2026-10-06), pending team confirmation

**Question:** Which π⁰ energies do we generate and analyse?

**Why it matters:** The range must cover all three regimes (resolved, shared blocks, same block), or Q4 can't be answered.

**Facts.** Minimum opening angle θ_min = 2·arcsin(m/E), and the minimum photon separation is d = L·θ_min (m = 0.135 GeV). The array face is 40 × 40 cm, with 10 cm blocks.

| E (GeV) | θ_min (rad) | d at L = 1.5 m |
|---|---|---|
| 0.5 | 0.547 | 82 cm, too wide for both photons to hit the array |
| 1.0 | 0.271 | 41 cm |
| 2.0 | 0.135 | 20 cm, about two blocks |
| 3.0 | 0.090 | 13.5 cm |
| 5.0 | 0.054 | 8 cm, less than one block |

**Starting suggestion:** 0.5–5 GeV in fixed bins (for example 0.25 GeV). Check that the upper end is still produced at the chosen beam momentum (D-01).

**Decision:** Generate and analyse π⁰ energies from **0.5 to 5 GeV in 0.25 GeV bins** (18 bins).

**Rationale (our words):** _______________

**Decided by / date:** Proposed 2026-10-06, pending team confirmation

**Revisit if:** _______________

---

## D-04 · Target materials and thickness

**Status:** Proposed (2026-10-06), pending team confirmation

**Question:** Which materials, and how thick?

**Why it matters:** A thick copper target converts many photons before they leave it. A yield comparison between materials would then measure photon absorption, not π⁰ production. This was the main flaw in our 2026 proposal.

**Facts** *(PDG Atomic and Nuclear Properties)*

| Material | Density | Radiation length X₀ | Interaction length λ_I |
|---|---|---|---|
| Carbon (graphite) | 2.21 g/cm³ | 19.32 cm | 38.83 cm |
| Copper | 8.96 g/cm³ | 1.436 cm | 15.32 cm |
| Tin | 7.31 g/cm³ | 1.206 cm | 22.80 cm |

**Thickness options, matched in interaction length.** "Both photons survive" assumes π⁰s are produced uniformly through the target depth and photons leave roughly along the beam.

| Material | Thickness | t (cm) | t / X₀ | Interaction prob. | Both photons survive |
|---|---|---|---|---|---|
| Carbon | 2 % λ_I | 0.78 | 0.04 | 2.0 % | 96.9 % |
| Carbon | 5 % λ_I | 1.94 | 0.10 | 4.9 % | 92.6 % |
| Carbon | 10 % λ_I | 3.88 | 0.20 | 9.5 % | 85.9 % |
| Copper | 2 % λ_I | 0.31 | 0.21 | 2.0 % | 85.1 % |
| Copper | 5 % λ_I | 0.77 | 0.53 | 4.9 % | 68.0 % |
| Copper | 10 % λ_I | 1.53 | 1.07 | 9.5 % | 48.8 % |
| Tin | 2 % λ_I | 0.46 | 0.38 | 2.0 % | 75.6 % |
| Tin | 5 % λ_I | 1.14 | 0.95 | 4.9 % | 52.4 % |

HARP used targets of 5 % λ_I, and measured carbon, copper and tin.

**Starting suggestion:** Carbon and copper at a matched λ_I fraction, with conversion **simulated and corrected for**, never ignored. Decide whether to favour rate (5 %) or low conversion (2 %).

**Decision:** Three targets (**carbon, copper and tin**), each simulated at **both 2 % and 5 % λ_I** (six configurations). Photon conversion is simulated and corrected for in every configuration.

| Target | 2 % λ_I | 5 % λ_I |
|---|---|---|
| Carbon | 0.78 cm | 1.94 cm |
| Copper | 0.31 cm | 0.77 cm |
| Tin | 0.46 cm | 1.14 cm |

**Rationale (our words):** _______________

**Decided by / date:** Proposed 2026-10-06, pending team confirmation

**Note:** At 5 % λ_I, tin loses about half of all photon pairs, so its correction is the largest. Comparing the two thicknesses shows the size of the conversion effect directly.

**Revisit if:** _______________

---

## D-05 · Geometry: distance *L* and angle *θ*

**Status:** Proposed (2026-10-06), pending team confirmation

**Question:** What default geometry, and what ranges do we scan?

**Why it matters:** *L* sets the photon separation (D-03). *θ* keeps the beam out of the array.

**Facts**
- The CERN experimental area is about 5 m × 10 m. The beam spot is about 2 cm across when focused, and grows with distance. *(BL4S 2026)*
- The array face is 40 × 40 cm. For an array centred at angle *θ* and distance *L*, the gap between the beam and the nearest array edge is roughly *L*·sin *θ* − 20 cm:

| L | θ = 10° | θ = 15° | θ = 20° |
|---|---|---|---|
| 1.0 m | −3 cm (beam hits array) | 6 cm | 14 cm |
| 1.5 m | 6 cm | 19 cm | 31 cm |
| 2.0 m | 15 cm | 32 cm | 48 cm |

- HARP forward data stop at 0.25 rad (about 14°). Larger angles need HARP's large-angle data or the toy model.
- Alternative to angling the array: deflect the beam with a dipole magnet. BL4S says CERN can install one on request.

**Starting suggestion:** Default *L* = 1.5 m, *θ* = 12–15°. Scan *L* = 0.75–3 m and *θ* = 8–25°.

**Decision:** Reference geometry ***L* = 1.5 m, *θ* = 12°** (beam clearance about 11 cm). Feasibility scans cover *L* = 0.75–3 m and *θ* = 8–25°. Configurations where the beam would hit the array are flagged, not used.

**Rationale (our words):** _______________

**Decided by / date:** Proposed 2026-10-06, pending team confirmation

**Note:** At this geometry the 40 cm array covers roughly 4°–20° from the target. HARP forward data reach 0.25 rad (about 14°) and large-angle data start at 0.35 rad (20°). The 14–20° range needs interpolation between the two data sets, and this must be stated in the paper.

**Revisit if:** _______________

---

## D-06 · Lead-glass properties and shower model

**Status:** Proposed (2026-10-06), pending team confirmation

**Question:** Which glass properties and which sideways shower profile?

**Why it matters:** The classifier's information is entirely in how energy spreads between blocks, so this model drives the Q3 and Q4 results.

**Facts**
- BL4S states the block size (10 × 10 × 37 cm) but **not the glass type**.
- Blocks of exactly this size were used in the OPAL barrel calorimeter, made of Schott **SF57** glass. SF57: X₀ ≈ 1.50–1.55 cm, Molière radius ≈ 2.6 cm. 37 cm is then about 24 X₀, so showers are fully contained in depth. *(OPAL / NA62 LAV papers; EIC Yellow Report table 11.33)*
- **This is an assumption until BL4S confirms the glass type.**
- About 90 % of a shower's energy lies within one Molière radius, about 95 % within two.

**Options for the transverse profile**

| Option | For | Against |
|---|---|---|
| A. Single Gaussian | Simplest | No tails, so it underestimates energy sharing |
| B. Two Gaussians (narrow core + wide halo) | Captures core and tails; used in the README figures (80 % core σ = 1.6 cm, 20 % halo σ = 5 cm) | Parameters need justifying |
| C. Geant4 shower library | Realistic fluctuations | Much more work |

**Starting suggestion:** B as default, tuned to R_M ≈ 2.6 cm. For robustness, run alternatives with R_M × 0.75 and R_M × 1.5. Add event-by-event fluctuations of the shower shape.

**Decision:** Option B: two Gaussians (narrow core + wide halo) tuned to SF57, R_M ≈ 2.6 cm, **with event-by-event fluctuations** of the shower shape. Robustness runs use R_M × 0.75 and R_M × 1.5. The glass type remains an assumption until BL4S confirms it.

**Rationale (our words):** _______________

**Decided by / date:** Proposed 2026-10-06, pending team confirmation

**Revisit if:** _______________

---

## D-07 · Detector response: resolution, noise, gains

**Status:** Proposed (2026-10-06), pending team confirmation

**Question:** How do we blur and distort the block energies?

**Facts**
- BL4S quotes σ_E / E = 0.02 % + 6.3 % / √E (E in GeV). *(BL4S 2026)*
- Per-block electronic noise and the gain spread between blocks are not given by BL4S.

**Starting suggestion**
- Resolution: as quoted, applied per photon.
- Noise: 10 MeV per block (scan 5–20 MeV), threshold at 3× noise.
- Gain errors: 0 % by default; robustness runs at 2 % and 5 %.

**Decision:**
- **Resolution:** σ_E / E = 0.02 % + 6.3 % / √E, as quoted by BL4S, applied per photon.
- **Noise:** 10 MeV per block by default, scanned over 5–20 MeV; block threshold at 3× noise (30 MeV by default).
- **Gain errors:** 0 % by default; robustness runs with 2 % and 5 % random block-to-block gain errors.

**Rationale (our words):** _______________

**Decided by / date:** Proposed 2026-10-06, pending team confirmation

**Revisit if:** _______________

---

## D-08 · Clustering and the definition of "merged"

**Status:** Proposed (2026-10-06), pending team confirmation

**Question:** How does reconstruction find clusters, and what counts as a merged π⁰?

**Options for "merged"**

| Option | For | Against |
|---|---|---|
| A. Reconstruction-based: both photons hit the array, but only **one** cluster is found | Matches what the detector actually sees | Depends on clustering parameters |
| B. Truth-based: true photon separation under a fixed distance (e.g. one block) | Clean, independent of the algorithm | Not what an experiment can observe |

**Starting suggestion**
- Seed: a block above a seed threshold (for example 100 MeV) whose energy exceeds all 8 neighbours.
- Cluster: the 3 × 3 blocks around the seed.
- "Merged": option A. Always store the true separation too, for plots against it.

**Decision:**
- **Seed:** a block above **100 MeV** whose energy exceeds all 8 neighbours.
- **Cluster:** the 3 × 3 blocks around the seed.
- **"Merged" (option A):** both photons hit the array but only one cluster is reconstructed. The true photon separation is stored for every event.

**Rationale (our words):** _______________

**Decided by / date:** Proposed 2026-10-06, pending team confirmation

**Note:** In π⁰ → γγ the photon energy is spread evenly from nearly 0 to nearly E_π⁰. With a 100 MeV seed, about 38 % of 0.5 GeV π⁰s and about 19 % of 1 GeV π⁰s have one photon below threshold. This is measured and reported as an energy-dependent efficiency, not hidden.

**Revisit if:** _______________

---

## D-09 · Labels and energy matching

**Status:** Proposed (2026-10-06), pending team confirmation

**Question:** How do we stop the classifier from learning "high energy = π⁰" instead of shower shape?

**Options**

| Option | For | Against |
|---|---|---|
| A. Generate single photons with energies drawn from the merged-π⁰ cluster energy spectrum | Matched by construction, simplest | Needs the π⁰ sample first |
| B. Reweight events in energy bins | Uses all events | Weights complicate training |
| C. Discard events until the spectra match | Simple | Throws away data |

Do the same for the hit position on the array (edges behave differently).

**Check:** a classifier given **only** the cluster energy should score AUC ≈ 0.5.

**Starting suggestion:** A, plus the energy-only check.

**Decision:** Option A. Single photons are generated with energies **and hit positions** drawn from the merged-π⁰ cluster distributions, so both match by construction. Required check: a classifier using only cluster energy must score AUC ≈ 0.5, and likewise one using only hit position.

**Rationale (our words):** _______________

**Decided by / date:** Proposed 2026-10-06, pending team confirmation

**Revisit if:** _______________

---

## D-10 · ML inputs, models, data split, metrics

**Status:** Proposed (2026-10-06), pending team confirmation

**Questions:** What goes into the models, which models, how do we split data, and how do we score?

**Starting suggestion**
- **Inputs:** (a) shape features: hottest-block fraction, second/first ratio, cluster width, x–y asymmetry, number of blocks above threshold; (b) raw 3 × 3 energies divided by cluster energy.
- **Models:** width cut (baseline), logistic regression, gradient-boosted trees, small MLP.
- **Split:** 60 / 20 / 20 for train / validation / test. Tune only on validation; use the test set **once**, at the end.
- **Metrics:** ROC curve, AUC, photon efficiency at 90 % π⁰ rejection, AUC per energy bin (for Q4).

**Decision:**
- **Inputs:** both, compared. (a) shape features; (b) raw 3 × 3 energies divided by cluster energy.
- **Models:** width cut (baseline) → logistic regression → gradient-boosted trees → small MLP.
- **Split:** 60 / 20 / 20 train / validation / test. Tune on validation only; the test set is used once, at the end.
- **Headline metric:** **AUC per π⁰ energy bin.** Also reported: overall ROC and AUC, and photon efficiency at 90 % π⁰ rejection.

**Rationale (our words):** _______________

**Decided by / date:** Proposed 2026-10-06, pending team confirmation

**Revisit if:** _______________

---

## D-11 · Sample sizes and random seeds

**Status:** Proposed (2026-10-06), pending team confirmation

**Starting suggestion**
- At least 10⁴ events per class per energy bin in the test set.
- Every run sets and logs its random seed in its output file.
- Figures are made only from saved, seeded runs.

**Decision:** **10⁵ events per class per energy bin in the test set.** With the 60 / 20 / 20 split that is about 18 million labelled events in total (18 bins × 2 classes × 5 × 10⁵). Every run sets and logs its random seed, and figures are made only from saved, seeded runs.

**Rationale (our words):** _______________

**Decided by / date:** Proposed 2026-10-06, pending team confirmation

**Notes**
- **Low-energy bins:** below about 2 GeV, merged π⁰s are rare at *L* = 1.5 m, so reaching 10⁵ in those bins needs a very large π⁰ generation. Bins that can't reach the target are reported with however many events exist, and with their larger uncertainties.
- **Compute:** develop with 10³ per bin. If the MLP is too slow on 10.8 million training events, train it on a documented random subsample and record that as a new entry.

---

## D-12 · Software conventions

**Status:** Proposed (2026-10-06), pending team confirmation

**Starting suggestion**
- Python ≥ 3.10, NumPy, SciPy, scikit-learn, matplotlib, pytest.
- Configs in YAML.
- Event output as `.npz` files with true values stored alongside reconstructed ones.
- Units: GeV, cm, rad.
- Every change goes through a pull request reviewed by someone other than its author.

**Decision:**
- **Stack:** Python ≥ 3.10, NumPy, SciPy, scikit-learn, matplotlib, pytest.
- **Configs:** YAML.
- **Units:** GeV, cm, rad.
- **Event files:** **.npz**, one file per configuration (target, thickness, geometry, model variant), storing true values alongside reconstructed ones.
- **Review:** every change goes through a pull request approved by **someone other than its author**.

**Rationale (our words):** _______________

**Decided by / date:** Proposed 2026-10-06, pending team confirmation

---

## D-13 · π⁰ decay modes

**Status:** Proposed (2026-10-06), pending team confirmation

**Question:** Do we simulate π⁰ decays other than γγ?

**Why it matters:** Assuming 100 % γγ overstates the number of reconstructable π⁰s.

**Facts** *(PDG)*

| Mode | Branching fraction | What the detector sees |
|---|---|---|
| π⁰ → γγ | 98.823 % | Two photon showers |
| π⁰ → e⁺e⁻γ (Dalitz) | 1.174 % | A nearly collinear e⁺e⁻ pair fires the charged veto, plus one photon |
| π⁰ → e⁺e⁻e⁺e⁻ | 0.003 % | Negligible |

**Options**

| Option | For | Against |
|---|---|---|
| A. γγ only | Simplest | Silently overstates efficiency by about 1.2 % |
| B. Tag Dalitz decays and reject them (veto) | Correct rate, no electron kinematics needed | Ignores rare Dalitz events where the pair misses the veto |
| C. Full Dalitz kinematics (Kroll–Wada) | Most complete | Much more work for a 1 % effect |

**Decision:** Option B. `decay.is_dalitz` tags 1.174 % of π⁰s as Dalitz decays; downstream modules reject them as vetoed. Double Dalitz and rarer modes are neglected.

**Rationale (our words):** _______________

**Decided by / date:** Proposed 2026-10-06, pending team confirmation

**Revisit if:** the veto turns out to be absent or inefficient in the real setup.

---

## D-14 · Other neutral mesons and multiple π⁰s per event

**Status:** Proposed (2026-10-06), pending team confirmation

**Question:** Does each simulated collision contain exactly one π⁰, or a realistic mix of several π⁰s and other neutral mesons?

**Why it matters**
- **Q1 (mass peak):** with several photons per event, wrong photon pairings form the combinatorial background under the 135 MeV peak. With one π⁰ per event, there is none.
- **Q3/Q4 (classifier):** photons from *different* particles can overlap in one cluster, making cluster shapes messier than the clean single-π⁰ case.
- Real collisions at 8 GeV/c often produce more than one π⁰, so a one-π⁰ simulation is cleaner than any experiment.

**Facts** *(PDG)*

| Meson | Mass | Decays that add photons |
|---|---|---|
| η | 547.9 MeV | γγ 39.4 %; 3π⁰ 32.6 %; π⁺π⁻π⁰ 23.0 % |
| ω | 782.7 MeV | π⁰γ 8.3 % (mostly π⁺π⁻π⁰, 89 %) |
| K⁰_S | 497.6 MeV | π⁰π⁰ 30.7 % |

- η photons separate about 4× more widely than π⁰ photons. At *L* = 1.5 m the minimum η photon separation is 83 cm at 2 GeV and 41 cm at 4 GeV, so both η photons rarely land on the 40 cm array below about 4 GeV. Usually only one does, and that looks like a single photon.
- η → γγ adds a second, smaller mass peak at 548 MeV.
- The π⁰ multiplicity and the η/π⁰ production ratio at 8 GeV/c are **not yet sourced**. Candidates: HARP charged-pion multiplicities with π⁰ ≈ (π⁺ + π⁻)/2, and published η/π⁰ ratios from proton–nucleus data.

**Options**

| Option | For | Against |
|---|---|---|
| A. One π⁰ per event, nothing else | Simplest; isolates the detector question | No combinatorial background or cross-particle overlaps; the classifier looks optimistic |
| B. Several π⁰s per event (Poisson multiplicity) plus η and ω at fixed ratios, toy kinematics | Captures background and overlaps at moderate cost | Needs sourced multiplicities and ratios; correlations between particles ignored |
| C. Full event generator (e.g. Geant4 hadronic models) | Realistic, with correlations | Steep learning curve |

**Starting suggestion:** Option A as the core classifier study (Q3/Q4 are defined per cluster). Option B as a dedicated study for Q1, and as a contamination check for Q3: measure what fraction of single clusters contain photons from more than one particle. Option C remains a stretch goal.

**Decision:**
- **Core classifier study (Q3/Q4):** Option A, one π⁰ per event.
- **Dedicated study (Q1 and a Q3 contamination check):** Option B, Poisson π⁰ multiplicity plus η and ω at fixed ratios. It measures the combinatorial background under the mass peak, and the fraction of single clusters containing photons from more than one particle.
- **Stretch goal:** Option C.
- Multiplicity and η/π⁰ ratio must be sourced before Option B runs.

**Rationale (our words):** _______________

**Decided by / date:** Proposed 2026-10-06, pending team confirmation

**Revisit if:** the contamination check shows multi-particle clusters are common enough to change the Q3 conclusions; then Option B becomes the core study.

---

## D-15 · Generator: sampling modes and production point

**Status:** Proposed (2026-10-06), pending team confirmation

**Questions:** How are π⁰s sampled for the classifier study, and where in the target are they produced?

**Why it matters:** D-11 asks for 10⁵ events per class in every energy bin. A physics spectrum falls steeply with energy, so the high-energy bins, where merging happens, fill very slowly.

**Facts** *(measured with `scripts/check_generator.py`, toy spectrum, 10⁶ π⁰, 5 % λ_I carbon)*
- 11.7 % of physics-mode π⁰s point at the array.
- Array hits in the 4.75–5 GeV bin are **62× fewer** than in the 0.5–0.75 GeV bin.
- 18 % of the π⁰s that hit the array are beyond HARP's forward limit (0.25 rad), which quantifies the gap noted in D-05.
- BL4S: a focused beam spot is "about 2 cm" across.
- The beam is attenuated as exp(−s/λ_I) with depth s, so interactions are slightly more likely near the front of the target. This is nearly uniform for 2–5 % λ_I targets.

**Decision**
- **Coordinates:** z along the beam, target centred at the origin, array centre at *L*·(sin *θ*, 0, cos *θ*).
- **Two sampling modes:**
  - `physics`: momenta from the production spectrum around the beam axis (toy now, HARP later; D-02), for Q1 and Q2.
  - `flat`: energy uniform in 0.5–5 GeV, directions uniform in solid angle inside a cone around the array axis (the array half-diagonal angle plus a 0.10 rad margin), for Q3 and Q4. This deliberately removes the real energy–angle correlation, and the paper must say so.
- **Toy spectrum (Phase 1 only):** dN/dp ∝ exp(−p / 1.0 GeV); dN/dp_T ∝ p_T exp(−p_T / 0.17 GeV), so ⟨p_T⟩ ≈ 0.34 GeV.
- **Beam spot:** Gaussian with σ = 0.5 cm in x and y ("about 2 cm" read as ±2σ).
- **Production depth:** truncated exponential with λ_I, through the full target thickness.

**Rationale (our words):** _______________

**Decided by / date:** Proposed 2026-10-06, pending team confirmation

**Revisit if:** BL4S gives the real beam-spot size; or HARP spectra replace the toy model, after which the energy-imbalance numbers above must be remeasured.

---

## D-16 · Photon transport: target size, material in the path, conversions

**Status:** Proposed (2026-10-06), pending team confirmation

**Questions:** How large is the target sideways, which materials does a photon cross on its way to the array, and what happens when a photon converts?

**Why it matters:** Any material converts photons into e⁺e⁻ pairs, not only the target. A conversion close to the array also fires the charged veto.

**Facts** *(PDG radiation lengths)*

| Material in the path | X₀ | Typical path | Conversion per photon |
|---|---|---|---|
| Air (1 atm) | 30 390 cm | about 1.5 m | about 0.4 % |
| Plastic scintillator veto (PVT) | 42.54 cm | 1 cm | about 1.8 % |

Pair-conversion probability: 1 − exp(−(7/9) Σ x/X₀). This is the high-energy limit; for photons of a few hundred MeV the true value is somewhat lower, so soft-photon losses are slightly overestimated.

**Decision**
- **Target:** 5 × 5 cm face (covers the beam spot to ±5σ). Photons may leave through the back face or a side, whichever comes first.
- **Path:** target (to its exit) → air → a **1 cm plastic veto** directly in front of the array. The path length through the veto grows as 1/cos(incidence angle).
- **Conversions:** a converted photon whose path still reaches the array **vetoes the whole event**, because its e⁺e⁻ pair fires the veto. A converted photon that misses the array is simply lost.
- **Accepted event:** not a Dalitz decay, not vetoed, and both photons reach the array unconverted.

**Results** *(scripts/check_transport.py, L = 1.5 m, θ = 12°)*
- No π⁰ below about 1.2 GeV has both photons on the array; even at 5 GeV, about 17 % of π⁰s aimed at the array are fully on it.
- About 1.6 % of physics-mode (toy) π⁰s are fully accepted; hits crowd the beam-side edge of the array.
- π⁰ lost to conversion, for π⁰s whose photons both reach the array:

| Target | 2 % λ_I | 5 % λ_I |
|---|---|---|
| Carbon | 7.5 % | 11.5 % |
| Copper | 19.0 % | 35.6 % |
| Tin | 28.2 % | 51.0 % |

  About 4.4 points of every entry come from the air and the veto; the rest matches the target-only table in D-04.

**Rationale (our words):** _______________

**Decided by / date:** Proposed 2026-10-06, pending team confirmation

**Revisit if:** BL4S confirms a different veto thickness or position, or the target size; or if soft-photon conversion matters enough to need an energy-dependent cross-section.

---

## D-17 · Detector response details

**Status:** Proposed (2026-10-06), pending team confirmation

**Questions:** What exact shower shape, fluctuation size and position effects does the detector model use? (This completes D-06 and D-07.)

**Facts** *(PDG Passage of Particles through Matter, section 33.5)*
- About 90 % of a shower's energy lies within 1 R_M and about 99 % within 3.5 R_M. Lateral profiles are "often represented as the sum of two Gaussians".
- The longitudinal profile is a gamma distribution with b ≈ 0.5. A photon shower peaks at t_max = ln(E/E_c) **+ 0.5** radiation lengths (−0.5 is for electrons).
- SF57 lead glass: X₀ ≈ 1.55 cm, E_c ≈ 12 MeV, R_M ≈ 2.6 cm *(EIC Yellow Report)*.
- Photons strike the array up to about 11° from head-on.

**Decision**
- **Shape:** two Gaussians fixed by the PDG containment numbers. Core width 0.3 R_M (assumed); the halo fraction and width are solved from the two containment conditions. The result is an 87.7 % core with σ = 0.78 cm and a 12.3 % halo with σ = 4.06 cm. It reproduces 99 % at 3.5 R_M exactly and 89.6 % at 1 R_M, because the core is treated as fully inside 1 R_M.
- **Fluctuations:** per photon, both widths are scaled log-normally with a 10 % spread, and the core fraction varies by ±3 % (Gaussian). Robustness scan: 0 % to 20 %.
- **Oblique incidence:** the shower centre is shifted along the photon direction to the energy-centroid depth X₀·(ln(E/E_c) + 0.5 + 2), about 10.7 cm at 1 GeV.
- **Energy:** σ_E/E = 0.02 % + 6.3 %/√E, applied to each photon's energy (linear sum, as quoted by BL4S).
- **Readout order:** deposits → fixed per-block gains → 10 MeV Gaussian noise → zero any block below 30 MeV. Blocks are treated as contiguous (no gaps); energy outside the 40 cm face is lost.

**Results** *(scripts/check_detector.py)*
- At the array centre, 1 GeV photons give a summed response of 0.997 ± 0.066. At u = 18 cm, 0.787: 21 % leaks off the edge.
- Accepted π⁰s (both photons enter the face unconverted) record **87.8 %** of their energy on average, but **98.7 %** when both shower centres are within 10 cm of the middle. A photon entering just inside an edge can have its shower centre outside the array. **Phase 2 needs a fiducial cut.**
- Energy-weighted centroids are strongly pulled toward block centres (the "S-curve"), so position reconstruction needs a correction. This is the position-bias problem anticipated in Q1.

**Rationale (our words):** _______________

**Decided by / date:** Proposed 2026-10-06, pending team confirmation

**Revisit if:** BL4S confirms a different glass type; or a Geant4 shower sample becomes available to replace the parameterisation.

---

## D-18 · Reconstruction method and Phase 2 layout

**Status:** Proposed (2026-10-06), pending team confirmation

**Decision**
- **Layout:** reconstruction code in `src/pi0resolve/reconstruction.py` (reused by later phases); Phase 2 studies, result tables and figures in `studies/phase2/`.
- **Clusters (completes D-08):** a seed is a block of at least 100 MeV that is higher than all 8 neighbours; the cluster is the 3 × 3 window around it. A block inside two windows is **split between the clusters in proportion to the two seed energies**, so no energy is counted twice.
- **Position:** logarithmic weighting, w = max(0, W₀ + ln(e_block / E_cluster)) (Awes et al., NIM A 311 (1992) 130), compared against plain energy weighting. The value of W₀ is set in D-19.
- **Fiducial cut:** both reconstructed cluster centres at least **5 cm** inside the array edge (the inner 30 × 30 cm).
- **Mass:** only events with exactly two clusters, both fiducial. Each photon direction runs from the target centre to the shower centre at depth L + D(E), using the D-17 depth formula. Using the front face instead would make every angle about 7 % too large.

**Rationale (our words):** _______________

**Decided by / date:** Proposed 2026-10-06, pending team confirmation

---

## D-19 · Calibration: W₀ and energy response

**Status:** Proposed (2026-10-06), pending team confirmation

**Question:** How are reconstructed positions and energies calibrated, without using the π⁰ mass we want to measure?

**What happened** *(recorded so the paper can describe the method honestly)*
1. With no calibration, the π⁰ peak sat 8 % low. A diagnosis showed cluster energies about 5 % low (the 30 MeV threshold zeroes soft halo blocks) and photon separations about 2.5 % short.
2. Tuning W₀ on *single photons* gave W₀ = 5.25, the best single-photon position (1.35 cm RMS against 1.94 at W₀ = 4). But in π⁰ *pairs* it pulled the two showers toward each other: separations 8 % short, peak 15 % low. **Tuning on single photons is the wrong target for a pair measurement.**
3. The first energy calibration used photons that truly landed inside the fiducial region. The analysis selects by *reconstructed* position, and positions are pulled inward, so photons truly near the edge (which leak energy) were missing from the calibration. Fixed by sampling the whole face and selecting by reconstructed position.
4. Near the 100 MeV seed threshold, only upward fluctuations form a cluster, so the median there is biased high (+22 % at 0.1 GeV) and cannot be inverted. The calibration therefore starts at 0.3 GeV, the first bin with at least 95 % cluster efficiency.

**Decision**
- **W₀ = 3.25:** the value at which the median reconstructed photon separation in simulated π⁰ pairs equals the true separation. It is chosen from truth-level separations, **never from the π⁰ mass.**
- **Energy calibration:** median cluster energy against true energy for simulated single photons (0.3–6 GeV, whole face, selected by reconstructed position), stored in `configs/energy_calibration.csv` and inverted by interpolation. The response is 0.93 at 0.5 GeV, 0.94 at 1 GeV and 0.97 at 4 GeV.
- Both are produced by `studies/phase2/calibrate.py`.

**Results** *(`studies/phase2/mass_peak.py`, carbon 2 % λ_I, L = 1.5 m, θ = 12°)*
- Toy-spectrum π⁰ peak: **131.6 ± 0.3 MeV** after calibration (−2.5 %), σ = 22.1 MeV; 123.0 MeV before calibration.
- **The peak depends on π⁰ energy:** 124 MeV at 1.25 GeV rising to 152 MeV at 4.75 GeV. The cause is photon separation (S-curve and edge effects): it is 9 % short at 1–1.5 GeV and 10 % long at 3.5–5 GeV. A single W₀ cancels this only on average.
- At 4.75 GeV, 16 % of π⁰s have both photons on the array, but only 1 % give two clusters: **about 94 % of accepted high-energy π⁰s merge.**

**Open question:** how to handle the energy-dependent separation bias. Resolved by D-20 (tried, failed) and D-21.

**Rationale (our words):** _______________

**Decided by / date:** Proposed 2026-10-06, pending team confirmation

---

## D-20 · Single-photon position correction (tried, disabled)

**Status:** Proposed (2026-10-07), pending team confirmation

**Question:** Can a correction table built from lone photons remove the energy-dependent separation bias found in D-19?

**What was tried:** single photons fired at known points over the whole face. For each reconstructed coordinate, the median true shower coordinate was recorded (`configs/position_calibration.csv`, made by `studies/phase2/calibrate.py`) and applied to u and v separately, before the fiducial cut.

**Result: it made π⁰ pairs worse.**

| π⁰ energy | Separation ratio, energy calibration only | With the position table |
|---|---|---|
| 1.5–2.0 GeV | 0.924 | 0.736 |
| 2.5–3.5 GeV | 1.055 | 0.825 |
| 3.5–5.0 GeV | 1.105 | 0.949 |

Selected events fell from 40 934 to 6 195.

**Why**
1. At W₀ = 3.25, reconstructed positions bunch near block centres, so the table is almost a step function. It stretches noise rather than recovering information.
2. In pairs, the dominant distortion is **the two showers interfering**: overlapping halos in shared blocks drag each position toward the other photon. Lone photons never show this.
3. Corrected positions were pushed outward past the fiducial cut, which preferentially removed widely separated pairs. That is a new selection bias.

The table built separately for soft (< 0.7 GeV) and hard (> 2 GeV) photons differed by only 0.31 cm RMS, so energy dependence was not the problem.

**Decision:** keep the code (`reconstruction.correct_position`) and the study output, but **disable** it (`position_calibration: null`). Pair interference is handled by a two-shower fit instead (D-21).

**Rationale (our words):** _______________

**Decided by / date:** Proposed 2026-10-07, pending team confirmation

---

## D-21 · Two-shower fit, and the edge-block limitation

**Status:** Proposed (2026-10-07), pending team confirmation

**Question:** Can fitting two showers of known shape to all 16 blocks remove the pair interference that biases photon separations (D-19, D-20)?

**Method** (`src/pi0resolve/showerfit.py`)
- **Model:** each photon is a shower of the fixed average shape (D-17) with an energy and a shower-centre position. Six numbers per event, chosen so the predicted blocks best match the measured ones (χ², Levenberg–Marquardt, all events at once).
- **Block uncertainty:** σ² = noise² + s²·e + (0.05·e)², with e the *predicted* block energy. Using the measured energy biased fitted energies low (Neyman bias).
- **Three starts per event:** log-weighted positions, plain-weighted positions, and seed-block centres; the lowest χ² is kept. The χ² surface has genuine local minima: on the straight path from a wrong fit to the truth, χ² rose from about 23 to 280 before falling to 0.
- **Limits:** shower energy at most 3× the energy measured in the whole array; shower centre at most 5 cm beyond the array edge. Without limits, about 1 fit in 5 ran away (a large shower far off the face can imitate the faint tail of a real one).
- **Mass:** events with exactly two clusters; both fitted centres must pass the 5 cm fiducial cut (D-18). Fitted energies are used directly (the model includes edge leakage).

**Validation** (`tests/test_showerfit.py`)
- Exact recovery from noise-free model blocks.
- Single photons above 2 GeV through the full simulation: energy ratio 1.000, position error 1.0 cm.
- π⁰ pairs above 2.5 GeV with both photons truly inside the fiducial region: separation and energy within 2 % of the truth.

**Limitation: the edge-block information limit**

A photon's position *within* a block is known only from the energy it shares with neighbouring blocks. In the outer half of an edge block, the only neighbour receives about 1 % of the energy, under the 30 MeV threshold for photons of a few GeV, so it reads zero. Any position in the block then fits equally well, and every method (fit or weighting) returns the block centre. Measured with single photons:

| True shower centre | Fitted − true position | Fitted / true energy |
|---|---|---|
| 13–14 cm | +1.0 cm | 0.99 |
| 16–17 cm | −1.5 cm | 0.98 |
| 18–19 cm | −3.4 cm | 0.93 |
| 19–20 cm | −4.5 cm | 0.70 |

**Every resolved π⁰ in a 4 × 4 array has at least one photon in an edge block.** Two photons form two clusters only if their seed blocks are not neighbours, and in a row of four, every non-neighbouring pair includes an edge block. Requiring both photons in the inner 2 × 2 blocks leaves zero events.

**Consequence:** the reconstructed π⁰ mass depends on π⁰ energy for both methods (`studies/phase2/mass_peak.py`):

| π⁰ energy | Log weighting: mass (separation ratio) | Two-shower fit: mass (separation ratio) |
|---|---|---|
| 1.5–2.0 GeV | 122 MeV (0.92) | 112 MeV (0.90) |
| 2.5–3.5 GeV | 143 MeV (1.06) | 127 MeV (0.97) |
| 3.5–5.0 GeV | 148 MeV (1.10) | 130 MeV (0.98) |
| All energies | 135 MeV (1.00) | 124 MeV (0.95) |

Gaussian core fits from the full study (`results/mass_vs_energy.csv`):
- **Log weighting:** 124 → 152 MeV from 1.25 to 4.75 GeV, σ 20–28 MeV.
- **Two-shower fit:** 117 → 132 MeV, σ 14–20 MeV.
- **Toy spectrum overall:** log weighting 131.6 MeV (σ 22.1, 19 396 events); fit 123.3 MeV (σ 19.3, 9 342 events). The fit keeps fewer events because fitted edge photons fail the fiducial cut more often.

Log weighting is right on average because opposite errors cancel. The fit has the smaller energy dependence (spread 18 MeV against 26 MeV) but sits low, because edge photons fall back toward block centres.

**Decision:** keep both methods and report the energy-dependent peak as a **detector limitation**, not a correctable bias. A pair-level correction from simulation was considered and rejected: it would patch missing information with the simulation's assumptions. Possible design remedies (a different array shape, a lower threshold, smaller blocks) are noted as future work.

**Rationale (our words):** _______________

**Decided by / date:** Proposed 2026-10-07, pending team confirmation

---

## D-22 · Phase 3 setup: dataset, inputs, baselines, scope

**Status:** Proposed (2026-10-07), pending team confirmation

**Scope:** classifier (Q3, Q4) with two non-ML baselines, then an ML position study compared with log weighting and the two-shower fit (the D-21 edge-block problem). Code: `src/pi0resolve/dataset.py`, `src/pi0resolve/ml/`; studies in `studies/phase3/`. Datasets are cached in `data/phase3/` (not committed; regenerate from the seed).

**Dataset** (completes D-08 and D-09)
- **Merged π⁰ (label 1):** flat-mode π⁰s through the full chain. Both photons reach the array unconverted and not vetoed, reconstruction finds exactly one cluster, and its log-weighted position passes the 5 cm fiducial cut (same as Phase 2).
- **Single photon (label 0):** one photon per merged π⁰, with the same energy and production point, aimed at the energy-weighted mean entry point of the two π⁰ photons. Same selection. Energies and positions match by construction.
- Kept per cluster: the 3 × 3 window around the seed (zero outside the array), the whole 4 × 4 array, and truth: energy, entry point, photon separation, softer-photon energy.
- A single-cluster π⁰ can be either two overlapping photons or one photon below the seed threshold. Both fake a photon, so both count. In practice nearly all are overlaps (10 soft-photon cases in a 300 k-π⁰ test set).
- **Yield:** merged π⁰s are rare below 2 GeV (40–120 per 0.25 GeV bin from 300 k generated π⁰) and common above 2.5 GeV (700–2 300 per bin). Low-energy bins are reported with their larger uncertainties (D-11).

**Inputs** (completes D-10)
- **Shape features:** hottest-block fraction, second/first block ratio, width, elongation, number of blocks above threshold, and log cluster energy.
- **Raw window:** nine block energies divided by their total, plus log cluster energy.
- Cluster energy is included because a merged cluster's appearance depends on energy. A sanity check trains on the raw window *without* energy to show the separation comes from shape.

**Baselines (no training)**
- Width cut.
- Shower-fit Δχ²: χ²(best one-shower fit) − χ²(best two-shower fit). The two-shower fit starts from the cluster split in half and offset ±3 cm along u, v and both diagonals.

**Models:** logistic regression, gradient-boosted trees (`HistGradientBoostingClassifier`) and a neural network (`MLPClassifier`), each trained on both input sets. Each model is chosen from three settings by validation AUC. Split 60 / 20 / 20; the test set is used once.

**Metrics:** ROC and AUC overall; AUC per 0.5 GeV bin (Q4); photon efficiency at 90 % π⁰ rejection; AUC for overlap and soft-photon π⁰s separately. Sanity checks: energy-only and position-only classifiers (should be about 0.5).

**Sample size:** development at 1.5 M generated π⁰ (about 10³ or more per bin above 2 GeV); scale up only once results are stable (D-11).

**Findings while building it** (`tests/test_phase3.py`)
- Even noise-free, two showers inside one block, or 7 cm apart either side of one block boundary, give almost the same blocks as one shower (fit Δχ² below 10). This is the Q4 information limit.
- A pair is given away when it lights blocks in a pattern one shower cannot make, such as two diagonal neighbours.

**Correction during the study:** single-cluster π⁰s below about 2.5 GeV are **not** soft-photon losses. Their photons are 27–37 cm apart and the softer one carries 450–560 MeV, but it lands at the far edge and its shower leaks off the array (the D-21 edge effect), so it forms no cluster. Merged π⁰s are therefore split by true photon separation: **overlap** (< 20 cm) and **second photon lost** (≥ 20 cm). A third input set, **the whole 4 × 4 array** (16 blocks divided by their total, plus log energy), was added so models can see traces of the lost photon outside the 3 × 3 window.

**Results** (development run: 1.5 M generated π⁰, 171 377 clusters, 34 276 in the test set; `studies/phase3/results/`)

| Method | AUC | Photons kept at 90 % π⁰ rejection | AUC, overlaps | AUC, second photon lost |
|---|---|---|---|---|
| Width cut | 0.882 | 0.70 | 0.902 | 0.630 |
| Shower-fit Δχ² | 0.920 | 0.74 | 0.929 | 0.818 |
| Logistic regression (shape) | 0.904 | 0.73 | 0.915 | 0.771 |
| Boosted trees (raw window) | 0.960 | 0.88 | 0.967 | 0.874 |
| Neural network (raw window) | 0.962 | 0.88 | 0.969 | 0.875 |
| **Boosted trees (whole array)** | **0.976** | **0.94** | **0.977** | **0.960** |
| Neural network (whole array) | 0.964 | 0.88 | 0.966 | 0.938 |

- Machine learning beats both non-ML baselines; raw inputs beat hand-made shape features; the whole array beats the 3 × 3 window, mostly for π⁰s whose second photon was lost.
- **Sanity checks:** true position alone AUC 0.503 (matched). Cluster energy alone 0.587: merged clusters record slightly less energy, a genuine detector effect. Raw window *without* energy 0.951, so the separation comes from shape.
- **Q4:** with the whole array, AUC is 0.91 at 1.25 GeV, about 0.99 at 2.25–3.25 GeV, and falls slowly to 0.965 at 4.75 GeV as photons crowd into one block. At L = 1.5 m the photons are still about 8 cm apart at 5 GeV, so **the point where separation fails (E\*) lies above the 0.5–5 GeV range.** Finding it needs higher energies or a larger L.
- Results vary by about ±0.002 AUC between runs with different train/test splits.

**Rationale (our words):** _______________

**Decided by / date:** Proposed 2026-10-07, pending team confirmation

---

## D-23 · ML position estimates

**Status:** Proposed (2026-10-07), pending team confirmation

**Question:** Can machine learning do better than log weighting and the two-shower fit on the edge-block problem (D-21)?

**Method** (`studies/phase3/position.py`)
- Gradient-boosted regressors on the 16 block energies (divided by their total) plus log total energy, trained on half the simulated events and tested on the other half.
- **Single photons:** predict the shower centre (u, v).
- **π⁰ pairs:** predict the true photon separation directly; the mass uses calibrated cluster energies with the log-weighted positions stretched about their midpoint to the predicted separation.
- All three methods are compared on the same test events.

**What ML can and cannot do:** no method recovers information the blocks do not contain. In the outer half of an edge block, log weighting and the fit put every photon at the block centre. ML instead predicts the *typical* position in that zone under the simulation's assumptions: about 2 cm too far out near 15 cm and 2 cm too far in near 20 cm. **It spreads the error more evenly; it does not remove it.** Its gains there depend on the simulated shower shape and π⁰ spectrum, which Phase 4 must test.

**Results** (300 k single photons, 1.5 M π⁰; `studies/phase3/results/position*.csv`)
- **Single photons, position RMS:** log weighting 3.56 cm, fit 3.19 cm, ML **2.24 cm**. In the inner region (|u|, |v| < 15 cm): fit **1.57 cm**, ML 1.98 cm, log weighting 2.56 cm. The fit is best where position information exists; ML is best overall because of the edges.
- **π⁰ mass by energy** (1.25 → 4.75 GeV, the same 20 343 test events for all three):
  - log weighting: 115 → 149 MeV;
  - fit: 107 → 133 MeV;
  - **ML: 124 → 135 MeV, within 131–138 MeV above 1.5 GeV.**
- Median mass over all energies: log weighting 134.9, fit 123.1, ML 134.4 MeV.

**Decision:** report all three side by side. ML is the most uniform estimate of the mass, but on this simulation's terms; the two-shower fit is the most trustworthy method where the blocks contain the information.

**Rationale (our words):** _______________

**Decided by / date:** Proposed 2026-10-07, pending team confirmation

---

## Questions to send to the BL4S team

Email: bl4s.team@cern.ch. One email with all questions, sent by the coach.

1. Which lead-glass type are the 16 blocks (e.g. SF57 from OPAL)? Are the Molière radius and per-block noise known?
2. Can the array be mounted at an angle to the beam (about 10–20°), and how close to the beam axis is allowed?
3. Is a dipole magnet realistically available to sweep the beam away from the array?
4. Are thin carbon, copper and tin targets available (about 5 × 5 cm), or must teams supply them?
5. How thick is the charged-veto scintillator paddle that would sit in front of the lead-glass array (we assume 1 cm)? What is the beam-spot size at the target?

## References

- BL4S 2026, *Beams and Detectors*: https://beamlineforschools.cern/beams_detectors_bl4s_2026/
- HARP, forward π± production by protons on nuclear targets (T9, CERN PS), Phys. Rev. C 80, 035208 (2009): https://arxiv.org/abs/0907.3857
- HARP, forward π± production with incident π± beams: https://arxiv.org/abs/0902.2105
- HARP, large-angle π± production on C, Cu, Sn: https://arxiv.org/abs/0709.3464
- PDG Atomic and Nuclear Properties (copper, graphite): https://pdg.lbl.gov/2024/AtomicNuclearProperties/
- EIC Yellow Report, lead-glass properties (table 11.33): https://arxiv.org/abs/2103.05419
