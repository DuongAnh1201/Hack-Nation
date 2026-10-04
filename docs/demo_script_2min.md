# 2-Minute Discovery Demo Script

**Target Duration:** 120 seconds  
**Objective:** Demonstrate an autonomous scientific discovery loop: from literature paper ingest to an optimized 4-layer coating beating the Stanford 2014 benchmark, with full epistemic verification.

---

### Phase 1: The Scientific Problem & Control (0:00 – 0:30)
- **Visual:** Split screen: 2014 Stanford Nature paper on the left, Replay UI on the right.
- **Narrator:**
  > *"Daytime passive radiative cooling reflects sunlight while beaming heat to outer space through the 8–13 µm atmospheric window. In 2014, Stanford researchers designed a 7-layer HfO2/SiO2 photonic crystal cooling below ambient temperature. But multi-layer nanophotonic design is trapped in a combinatorial bottleneck."*
- **Action:** Launch discovery loop: `omni run ./lab/`.
- **UI State:** Event `L1` (Literature Agent ingests Raman 2014) $\to$ `E1` (Control verification confirms $97.7\%$ solar reflectance, passing the `control_first` policy).

---

### Phase 2: Hypothesis, Refutation & Adaptation (0:30 – 1:15)
- **Visual:** Replay UI node graph and spectrum visualizer.
- **Narrator:**
  > *"Cycle 1: The hypothesis agent proposes a 5-layer TiO2/SiO2 stack for high refractive index contrast. The experiment runner tests it in our Docker sandbox. Result? P_net is only 39.8 W/m²—refuted! Our analysis agent diagnoses the failure: TiO2 causes near-UV absorption below 0.38 µm. This refutation directly changes the next hypothesis: replacing TiO2 with Si3N4."*
- **UI State:** Verdict `V2` (Refuted: near-UV bottleneck) $\to$ Planner `P3` chooses Candidate A (Si3N4/SiO2) $\to$ Simulation `E3` achieves **$56.9\text{ W/m}^2$**!

---

### Phase 3: Speed-Up Proof & Human Safety Gate (1:15 – 2:00)
- **Visual:** Benchmark convergence curves (`results/speedup_chart.svg`).
- **Narrator:**
  > *"Across a 10-seed rigorous benchmark on the exact same physics simulator, standard Random Search reached the target in only 30% of runs. Our Omnigent Agent Lab converged in 90% of runs in a median of 34 simulations—proving an empirical 2.9× speedup with a 95% bootstrap confidence interval. Finally, the safety gate engages: proposing fabrication triggers a mandatory human approval gate. Scientific discovery is accelerated, verified, and safe."*
- **UI State:** `results/speedup_chart.svg` displayed $\to$ Final `approval` event marked `pending_human_review`.
