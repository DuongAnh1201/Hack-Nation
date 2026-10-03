# Science specification

## 1. Question and bottleneck

**Question.** For a projectile launched from level ground with quadratic air drag, how does the
range-maximising launch angle θ\* depend on launch speed v0, mass m, cross-section A, drag
coefficient C_d, air density ρ and gravity g? Is there a compact law that predicts θ\* for unseen
conditions within 0.1°?

**Why it is a real discovery task.** No exact closed-form solution exists for quadratic drag
(Turkyilmazoglu 2016, [doi:10.1088/0143-0807/37/3/035001](https://doi.org/10.1088/0143-0807/37/3/035001)).
Even the direction of the effect is "often considered obvious" but is not: for some drag laws the
optimum exceeds 45° (Price & Romano 1998, [doi:10.1119/1.18804](https://doi.org/10.1119/1.18804)).
So the answer has to come from experiments.

**Bottleneck we attack.** Six inputs, each needing a full angle optimisation. A naive 5-level grid
is 5^5 = 3,125 optimisations (~84,000 simulations). Humans also choose each next condition by hand.

**Ground truth is known in principle, which is a feature.** Dimensional analysis and the vacuum
limit are textbook physics. That lets us check that the agents *rediscover* correct physics before
we trust them on the parts that are not closed-form (the shape of θ\*(β)).

## 2. Physics model

`m dv/dt = -m g ŷ - ½ ρ C_d A |v| v` ⇒ `dv/dt = -g ŷ - k|v|v`, with `k = ρ C_d A / (2m)`.

| Item | Status |
|---|---|
| Uniform gravity, quadratic drag law | established fact (OpenStax Univ. Physics 1, §4.3, §6.4) |
| Point mass, no spin/Magnus, constant C_d, still air, flat ground, h0 = 0 | **assumptions** (stated in every report) |
| RK4, step = (fastest time scale)/200; impact and apex found by Newton on a partial step | numerical method |
| Accuracy: vacuum results match closed form to ~1e-13 m; drag runs checked by step doubling (range error < 1e-6 relative) and an energy balance (KE + PE + drag work, error < 1e-8) | **tested** (`tests/test_physics.py`) |

Measurements per run (all computed from the trajectory, never hard-coded): `range_m`,
`flight_time_s`, `max_height_m`, `time_to_apex_s`, `impact_speed_m_s`, `impact_angle_deg`,
`energy_initial_J`, `energy_final_J`, `energy_lost_to_drag_J`, momenta, `beta`, `eta`, plus
numerical uncertainty.

Derived numbers: drag number **β = k v0²/g** (drag force / weight at launch speed), launch-height
number η = g h0 / v0².

## 3. Experiments

Every experiment records, **before it runs**: question, hypothesis ids, independent/controlled
variables, conditions, and each hypothesis's prediction. The safety agent reviews it, then results
and analysis are linked back by id.

| # | Question | Variables | Initial conditions | Hypotheses | Measurements | Decision rule |
|---|---|---|---|---|---|---|
| E1 control | Does the simulator reproduce θ\* = 45°, R = v0²/g in vacuum? | v0, g, m (C_d = 0) | baseball 20 & 60 m/s; shot put on Mars 12 m/s | established fact F1 | θ\*, R | pass if \|θ\*−45\| ≤ 0.02° and R error < 1e-6, else stop |
| E2 drag probe | Does drag move θ\* and which way? | C_d ∈ {0.1, 0.35, 1.0} | baseball, Earth, 40 m/s | H1 null (45°), H2 lower & monotone | θ\* | H1 refuted if any \|θ\*−45\| > 0.1°; H2 needs all < 45 and decreasing |
| E3 invariance | Same β ⇒ same θ\*? | m, A, C_d, ρ, g; v0 solved for β = 2 | baseball/Earth, shot put/Earth, ping-pong/Mars, beach ball/Earth, bowling ball/Venus | H3 θ\* = F(β) | θ\* spread | supported if spread ≤ 0.02° **and** E4 spread > 0.2° |
| E4 negative control | Same speed ⇒ different θ\*? | object/planet at 30 m/s | same five | H3 | θ\* spread | shows E3 can detect differences |
| E5… scaling points | θ\* at the β where competing laws disagree most | β | baseball/Earth, v0 solved | functional-form laws H4–H10 | θ\* | each law's prediction is logged first; hit if within 0.1° |
| hold-out | Does the law generalise to raw physical conditions? | random object, planet, speed, C_d (seeded) | 10 conditions with β in [0.01, 100] | best law + H3 | θ\* | reported as max error; never used for fitting |

**Angle search inside each experiment.** Start at the prior (45°), step 5° in the direction that
increases range until it drops (bracket), then golden-section to ±0.005°. Every evaluation is
logged with the reason it was chosen. This is the "45° → 40° → 35° → focus on 37–41°" behaviour,
recorded step by step for the 3D replay.

## 4. Hypothesis library for θ\*(β)

All laws reduce to 45° at β = 0. Tier 2 is only proposed after tier 1 fails with structured
residuals.

| Tier | Law |
|---|---|
| 1 | `45 + aβ`, `45 + aβ^p`, `45 + a ln(1+cβ)`, `45 + aβ/(1+cβ)` |
| 2 | `45 + a ln(1+cβ^p)`, `45/θ* = 1 + a ln(1+cβ)`, `cot θ* = 1 + a ln(1+cβ)` |
| any | LLM agents may propose their own formula; it is parsed with a math-only whitelist and fitted the same way |

**Ranking:** leave-one-out RMSE (prediction error on a point the law was not fitted on).
**Next experiment:** the β in [0.01, 100] where the two best laws disagree most. If they agree
everywhere (< 0.05°), the β farthest from existing data, as an independent check.
**Stopping rule:** best law LOO RMSE ≤ 0.1° **and** two consecutive correct prospective predictions.
Budget stop after 12 scan experiments.

## 5. Epistemic labels (every record entry has one)

`established_fact` (must cite a source, enforced in code) · `literature` · `assumption` ·
`ai_hypothesis` · `ai_prediction` (logged before the experiment) · `simulation_result` ·
`analysis` · `decision` · `conclusion` (always `pending_human_review`).

## 6. Measuring "faster discovery"

`python -m physics_lab benchmark` scores both arms against a separate high-precision reference
(tolerance 1e-4°) on 30 random β values. See [results/benchmark.md](results/benchmark.md). Current
measured result: **2.9× fewer simulations** than the cheapest manual grid meeting 0.1° (651 vs
1,870), **0 vs 17** human decisions, and a closed-form law instead of a table. Caveats are listed in
the benchmark output: the baseline gets the β reduction for free, the AI count includes controls
and hold-out, and a smarter baseline would do better than the manual protocol.

## 7. Safety and human approval

Purely computational, so the risks are bad inputs, runaway compute and over-claiming.
`physics_lab/safety.py` rejects invalid physics, asks for human approval above 400 simulations
per experiment or 5,000 per session, and warns when inputs leave the model's validity (speed above
250 m/s means compressibility is not modelled; β > 100 means extrapolation). In Omnigent the same
rules run as a policy (`physics_lab.policies.experiment_gate`). It returns ASK for large runs
**and for any call that claims `human_approved=true`**, so an agent cannot approve itself.
Conclusions are recorded as `pending_human_review`.

## 8. Validation still needed before real-world use

Compare with measured trajectories where C_d varies with Reynolds number. Add spin/Magnus lift
and wind. Extend to launch height > 0 (H3 predicts a second number η is needed; this is the
lab's recommended next experiment). The fitted law is empirical within β ∈ [0.01, 100]; it is not
claimed as novel until it has been compared with the analytic approximations in the literature.
