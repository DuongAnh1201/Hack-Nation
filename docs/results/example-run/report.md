# Physics AI Lab: research report

**Question.** For a projectile launched from level ground with quadratic air drag, how does the range-maximising launch angle theta* depend on launch speed, mass, size, drag coefficient, air density and gravity, and is there a compact law that predicts theta* for unseen conditions to within 0.1 deg?

## Answer (status: pending_human_review)

Within beta in [0.01, 100] and h0 = 0, theta* follows cot(theta*) = 1 + a*ln(1 + c*beta) (a = 0.2565, c = 0.7996); LOO RMSE 0.025 deg. On 10 random unseen physical conditions it predicted theta* with max error 0.028 deg using zero new fitting. Pending human review.

- Law: `cot(theta*) = 1 + a*ln(1 + c*beta)` with a = 0.2565, c = 0.7996
- Leave-one-out RMSE: 0.025 deg (max 0.062 deg)
- Hold-out (10 random unseen conditions): max error 0.028 deg

**Limitations**

- Point mass: no spin, no Magnus lift, no tumbling.
- Constant drag coefficient (no Reynolds- or Mach-number dependence).
- Still air, uniform gravity, flat ground; launch and landing at the same height (h0 = 0).
- Simulator: fixed-step RK4; accuracy is checked per run by step doubling and an energy balance.
- Empirical fit inside the sampled domain; not an analytic derivation, not claimed as novel (compare with analytic approximations in the cited literature before any claim).

**Validation needed before real-world use**

- Compare against measured trajectories (e.g. ball-tracking data) where C_d varies with speed.
- Add spin/Magnus lift and wind; both change the optimum in sports.
- Repeat with launch height > 0: H3 predicts a second number eta = g h0 / v0^2 will be needed.

**Recommended next experiment.** Test whether theta* = F(beta, eta) when launch height > 0 (second dimensionless group).

## Discovery timeline (decisions)

- **D1** Run a vacuum control before any drag experiment: Results under drag are only meaningful if the simulator reproduces the established vacuum result. _(based on F1)_
- **D2** Simulator validated; test drag next: Vacuum control matched theory, so drag effects can be attributed to physics, not numerics. _(based on R1)_
- **D3** theta* depends on drag; look for a parameter reduction before scanning: Five physical inputs (m, A, C_d, rho, g) plus v0 could matter. A naive 5-level grid over 5 inputs would need 5^5 = 3125 angle optimisations (~84,000 simulations at ~27 each). Testing a dimensional-analysis hypothesis first could make most of that unnecessary. _(based on R2, H1, H2)_
- **D4** Collapse the search to one variable, beta; reuse all earlier runs as data: H3 supported, so every earlier optimisation is a measurement of theta*(beta). That already gives 10 distinct beta values without new experiments. _(based on R3, R4, H3)_
- **D5** Next experiment: beta = 100: laws 'logarithmic' and 'saturating' disagree most here (5.615 deg), so this measurement best separates them _(based on N4, P1)_
- **D6** Escalate: propose richer laws: Best tier-1 law 'logarithmic' has LOO RMSE 0.767 deg, more than 2x the 0.1 deg target with 11 points (residuals systematic: True). More data will not fix a wrong form. _(based on N6, H8, H9, H10)_
- **D7** Next experiment: beta = 0.01: top laws agree to within 0.039 deg everywhere, so pick the beta farthest from existing data for an independent prospective test _(based on N7, P2)_
- **D8** Next experiment: beta = 0.1: top laws agree to within 0.039 deg everywhere, so pick the beta farthest from existing data for an independent prospective test _(based on N9, P3)_
- **D9** Stop scanning: law 'cot_log' meets the accuracy target: LOO RMSE 0.025 deg <= 0.1 deg and 2 consecutive prospective predictions within tolerance. _(based on N11)_

## Hypotheses

| ID | Statement | Status | Last rationale |
|---|---|---|---|
| H1 | H1 (null): theta* = 45 deg regardless of drag; the vacuum optimum carries over. | **refuted** | max deviation from 45 deg = 7.565 deg vs tolerance 0.1 deg |
| H2 | H2: quadratic drag lowers theta* below 45 deg, and stronger drag lowers it further. | **supported** | all below 45: True; strictly decreasing with C_d: True (supported for these conditions only) |
| H3 | H3: theta* depends on the physical parameters only through beta = k v0^2 / g, k = rho C_d A / (2 m). | **supported** | same-beta spread 0.0000 deg <= 0.02; negative control spread 14.45 deg |
| H4 | Law 'linear': theta* = 45 + a*beta | **refuted** | LOO RMSE 5.11 deg > 10x tolerance |
| H5 | Law 'power': theta* = 45 + a*beta^p | **refuted** | LOO RMSE 1.24 deg > 10x tolerance |
| H6 | Law 'logarithmic': theta* = 45 + a*ln(1 + c*beta) | **refuted** | LOO RMSE 0.708 deg misses target |
| H7 | Law 'saturating': theta* = 45 + a*beta/(1 + c*beta) | **refuted** | LOO RMSE 1.23 deg > 10x tolerance |
| H8 | Law 'log_power': theta* = 45 + a*ln(1 + c*beta^p) | **refuted** | LOO RMSE 0.547 deg misses target |
| H9 | Law 'reciprocal_log': 45/theta* = 1 + a*ln(1 + c*beta) | **inconclusive** | LOO RMSE 0.065 deg; not separated from best |
| H10 | Law 'cot_log': cot(theta*) = 1 + a*ln(1 + c*beta) | **supported** | best law; meets accuracy target |

## Experiments

| ID | Question | Simulations | Result |
|---|---|---|---|
| E1 | Control: does the simulator reproduce the known vacuum optimum (45 deg) and range v0^2/g? | 66 | E1: 66 simulations; theta* = [45.000, 45.000, 45.000] deg |
| E2 | Does quadratic drag move theta* away from 45 deg, and in which direction? | 67 | E2: 67 simulations; theta* = [43.491, 40.940, 37.435] deg |
| E3 | Do five very different objects/planets with the same beta = 2 share one theta*? | 110 | E3: 110 simulations; theta* = [38.780, 38.780, 38.780, 38.780, 38.780] deg |
| E4 | Negative control: do the same five objects at the same speed (30 m/s) differ in theta*? | 113 | E4: 113 simulations; theta* = [42.349, 44.775, 42.802, 30.321, 32.840] deg |
| E5 | What is theta* at beta = 100? | 25 | E5: 25 simulations; theta* = [25.155] deg |
| E6 | What is theta* at beta = 0.01? | 22 | E6: 22 simulations; theta* = [44.938] deg |
| E7 | What is theta* at beta = 0.1? | 22 | E7: 22 simulations; theta* = [44.428] deg |
| E8 | Hold-out validation: does the law predict theta* for random unseen physical conditions? | 226 | E8: 226 simulations; theta* = [43.673, 44.694, 44.223, 42.179, 43.952, 26.435, 26.103, 39.194, 43.780, 43.704] deg |

## Predictions made before experiments

- P1: Before running: predicted theta*(100) = logarithmic 22.936, saturating 28.551, power 11.820, linear -50.221
- P2: Before running: predicted theta*(0.01) = cot_log 44.942, reciprocal_log 44.943, log_power 44.989, logarithmic 44.922
- P3: Before running: predicted theta*(0.1) = cot_log 44.440, reciprocal_log 44.450, log_power 44.667, logarithmic 44.283

## Evidence

- **F1** In vacuum on level ground, range R = v0^2 sin(2 theta) / g, so the range-maximising launch angle is 45 deg independent of v0, m and g. Source: [OpenStax, University Physics Volume 1, Sec. 4.3 Projectile Motion](https://openstax.org/books/university-physics-volume-1/pages/4-3-projectile-motion)
- **F2** At high Reynolds number the drag force on a body is well approximated by F_D = (1/2) C rho A v^2, directed opposite to the velocity. Source: [OpenStax, University Physics Volume 1, Sec. 6.4 Drag Force and Terminal Speed](https://openstax.org/books/university-physics-volume-1/pages/6-4-drag-force-and-terminal-speed)
- **F3** When launch and landing heights differ, the optimum angle in vacuum differs from 45 deg (for a release above the ground it is below 45 deg). Source: [Lichtenberg & Wills (1978), Maximizing the range of the shot put, Am. J. Phys. 46, 546](https://doi.org/10.1119/1.11258)
- **F4** That air resistance lowers the optimal angle below 45 deg is 'often considered obvious' but is not: for some drag laws the optimum exceeds 45 deg. Source: [Price & Romano (1998), Aim high and go far, Am. J. Phys. 66, 109](https://doi.org/10.1119/1.18804)
- **F5** No exact closed-form solution is known for projectile motion with quadratic drag; analytic treatments are approximations. Source: [Turkyilmazoglu (2016), Highly accurate analytic formulae for projectile motion subjected to quadratic drag, Eur. J. Phys. 37, 035001](https://doi.org/10.1088/0143-0807/37/3/035001)
- **L1** query 'optimal launch angle projectile air resistance' (openalex-cache):
  - Aim high and go far—Optimal projectile launch angles greater than 45° (1998), American Journal of Physics https://doi.org/10.1119/1.18804
  - Critical Launch Angle for Projectile Motion (2024), ERU Research Journal https://doi.org/10.21608/erurj.2024.251675.1095
  - Optimization of projectile motion under linear air resistance (2015), Rendiconti del Circolo Matematico di Palermo Series 2 https://doi.org/10.1007/s12215-015-0205-y
  - Optimization of Projectile Motion Under Air Resistance Quadratic in Speed (2016), Mediterranean Journal of Mathematics https://doi.org/10.1007/s00009-016-0815-4
  - Exploring the Effect of Linear Air Resistance on the Optimal Angle of Release for an NBA Free Throw (2026), Research Square https://doi.org/10.21203/rs.3.rs-10588767/v1
  - On the locus formed by the maximum heights of projectile motion with air resistance (2010), European Journal of Physics https://doi.org/10.1088/0143-0807/31/6/002
- **L2** query 'projectile motion quadratic drag force' (openalex-cache):
  - On projectile motion with quadratic drag force (2018), European Journal of Physics https://doi.org/10.1088/1361-6404/aab343
  - Approximate Analytical Description of the Projectile Motion with a Quadratic Drag Force (2014), Athens Journal of Sciences https://doi.org/10.30958/ajs.1-2-2
  - Simple analytical description of projectile motion in a medium with quadratic drag force (2013),  
  - Exact turning invariants for projectile motion under quadratic drag and a vertical-axis Magnus force (2026), arXiv (Cornell University) https://doi.org/10.5281/zenodo.22852339
  - Exact turning invariants for projectile motion under quadratic drag and a vertical-axis Magnus force (2026), Zenodo (CERN European Organization for Nuclear Research) https://doi.org/10.5281/zenodo.22852340
  - Exact turning invariants for projectile motion under quadratic drag and a vertical-axis Magnus force (2026), arXiv (Cornell University) https://doi.org/10.48550/arxiv.2609.30305

**Assumptions**

- A1: Point mass: no spin, no Magnus lift, no tumbling.
- A2: Constant drag coefficient (no Reynolds- or Mach-number dependence).
- A3: Still air, uniform gravity, flat ground; launch and landing at the same height (h0 = 0).
- A4: Simulator: fixed-step RK4; accuracy is checked per run by step doubling and an energy balance.

## Metrics

- simulations: 651
- simulation_seconds: 0.941
- experiments: 8
- hypotheses_proposed: 10
- hypotheses_resolved: 9
- decisions: 9
- human_interventions: 0

## How to read labels

- `established_fact`: Established science, cited
- `literature`: Retrieved literature (metadata/abstract, not verified claims)
- `assumption`: Modelling assumption (not tested here)
- `ai_hypothesis`: AI-generated hypothesis
- `ai_prediction`: AI prediction recorded before the experiment ran
- `simulation_result`: Measured from simulation
- `analysis`: Computed from simulation results
- `decision`: AI planning decision
