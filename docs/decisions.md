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
