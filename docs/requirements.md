# Requirements: Physics Study 3D × Physics AI Lab

Status: draft for team review (issue #5, "Recollect the Requirements"). Owner: Bael.
Scope update: adds **3D visualization**, **courses**, **AI chat (Omnigent)** and the **UI theme
(animal, blue, pixel)** to the existing scientific-discovery core.

**Priority key (MoSCoW):** **M** = must have for the hackathon submission · **S** = should have
for the demo · **C** = could have if time allows · **W** = won't do in the hackathon.

## 1. Product in one paragraph

A pixel-art, blue-themed physics study platform. Animal characters guide a student through short
**courses** built around interactive **3D experiments**. In every lesson the student predicts,
simulates and compares. In the final "Discovery Lab" the student uses the **AI chat** to hand a
research question to a team of **Omnigent** agents. The agents form hypotheses, run experiments
in the 3D world, and change their plan when a result surprises them. The 3D view, the courses
and the theme exist to make that discovery loop visible and learnable. They are not the
scientific contribution.

## 2. Non-negotiables from the hackathon (drive every decision)

| ID | Requirement (challenge rule) | Where it is satisfied |
|---|---|---|
| CORE-1 **M** | Omnigent orchestrates the live discovery workflow; specialist agents exchange outputs, use tools, run experiments and adapt their plan | `omnigent/physics_lab.yaml`; surfaced in CHAT-2 |
| CORE-2 **M** | One specific scientific question, answerable in 24 h | [science-spec.md](science-spec.md) §1 |
| CORE-3 **M** | Evidence: literature, established facts, simulations | literature agent, OpenAlex, cited facts |
| CORE-4 **M** | An experiment whose result changes the next decision | prediction miss → "escalate" decision; shown in VIS-4 and CHAT-3 |
| CORE-5 **M** | Measured progress against a baseline, no unsupported "10×" claim | `python -m physics_lab benchmark` → 2.9× fewer simulations |
| CORE-6 **M** | Human approval for consequential actions | safety agent + `experiment_gate` policy; approval UI in CHAT-4 |
| CORE-7 **M** | Cite facts, label AI hypotheses, keep uncertainty, list validation still needed | epistemic labels on every record entry; UI-6 |
| CORE-8 **M** | Never fabricate or hard-code results; measurements come from the simulation | VIS-6, CRS-5 |
| CORE-9 **M** | 2-minute demo of Question → … → Next experiment | §8 |

**Build order** (from the original brief): science and the loop first, then the 3D view, then
the courses, chat and theme. If time runs short, cut from the bottom of §9, never from §2.

## 3. 3D visualization (`technology/src/scenes/`)

Stack: React + react-three-fiber + drei (already in `technology/package.json`).

| ID | Pri | Requirement | Acceptance criteria |
|---|---|---|---|
| VIS-1 | M | **Projectile scene**: ground with distance markers, launcher with angle indicator, projectile, trajectory trail | Given trajectory frames from `/api/simulate`, the trail ends at the reported `range_m` (±1 % of scene scale) |
| VIS-2 | M | **Vectors**: velocity, gravity, drag and net force arrows, each labelled in text (not only by colour) | Drag arrow always points opposite the velocity; toggles per vector |
| VIS-3 | M | **Measurements HUD**: range, max height, flight time, energy lost to drag, launch angle, β | Values shown exactly as returned by the backend, with units |
| VIS-4 | M | **Experiment replay**: animate an agent's angle search step by step from `result.data.conditions[*].search_trace`, with each step's `note` as caption ("R(40) > R(45): optimum is below 45°; probe 35") | Replay of the example run shows 45° → 40° → 35° → bracket → refine |
| VIS-5 | S | **Comparison mode**: overlay several trajectories (e.g. 5 objects on Earth/Mars/Venus at the same β landing at the same optimal angle) | Up to 6 trajectories, distinct colours and labels, legend |
| VIS-6 | M | **Single source of truth**: measurements and AI evidence come from the backend simulator (`physics_lab`). Frontend `lib/` may interpolate and animate but must not produce numbers presented as results | No measured value in the UI is computed only in the browser |
| VIS-7 | S | **Sandbox**: sliders for speed, angle, mass, C_d, planet preset; re-simulate on release | Response < 300 ms on the hosted backend (warm); invalid input shows the backend's error |
| VIS-8 | S | **Pixel look** (see UI-3): low-resolution render or pixelation post-process; blocky/voxel models | Toggle "pixel effect off" for readability and slow GPUs |
| VIS-9 | C | More scenes: free fall, collisions (momentum), orbits | Each scene reuses VIS-2/3 components |
| VIS-10 | M | Performance: 60 fps on a mid-range laptop; at most 240 frames per trajectory (backend default) | Chrome performance panel during replay |

Data contract: trajectory frames and the research-record format are in [interfaces.md](interfaces.md)
(y-up, motion in the x–y plane).

## 4. Courses (`technology/src/components/courses/`, content as files)

Courses teach through the scientific method: **predict → simulate → compare → explain**. The
original brief warns against an "educational chatbot". Every lesson must have the student run
something, not just read.

| ID | Pri | Requirement | Acceptance criteria |
|---|---|---|---|
| CRS-1 | M | **One complete course** for the demo: *"How far can it fly?"*, 5 lessons (below) | All 5 lessons playable end to end |
| CRS-2 | M | **Lesson layout**: objective, short concept text, 3D scene, controls, checkpoint, "Ask the tutor" button | Same layout component for every lesson |
| CRS-3 | M | **Predict-then-test checkpoint**: student enters a prediction (number or choice), runs the simulation, sees prediction vs result and the difference | Feedback states the measured value and the student's error |
| CRS-4 | M | **Cited concept text**: factual statements link to their source (reuse the cited facts F1–F5) | Every fact in lesson text has a citation |
| CRS-5 | M | **No hard-coded answers**: checkpoint answers come from the simulator (or, for textbook facts like 45° in vacuum, from a cited fact) | Changing scene parameters changes the expected answer |
| CRS-6 | S | **Course catalog + progress**: catalog page, lesson list, progress saved in the browser (localStorage) | Refresh keeps progress; no account needed |
| CRS-7 | S | **Content as data**: courses are JSON/Markdown files in the repo (schema below), not hard-coded in components | Adding a lesson requires no code change |
| CRS-8 | C | Second course (e.g. momentum and collisions) | |
| CRS-9 | W | Accounts, teacher dashboards, grading, CMS | |

**MVP course "How far can it fly?"** maps one-to-one to the lab's experiments:

| Lesson | Concept | Student activity | Lab link |
|---|---|---|---|
| 1. Arrows of motion | velocity, acceleration, gravity as vectors | launch a ball; watch the vectors change | sandbox |
| 2. The 45° rule | vacuum range R = v0² sin 2θ / g (F1) | predict the best angle, then test it | control E1 |
| 3. Air pushes back | quadratic drag, F = ½ρC_dAv² (F2) | predict: does drag raise or lower the best angle? (F4 says it's not obvious) | drag probe E2 |
| 4. One number rules them all | dimensionless β; Earth vs Mars vs Venus | match β across planets and see the same best angle | invariance E3/E4 |
| 5. Discovery Lab | how scientists find laws | give the AI team the question in chat; watch it predict, miss, adapt | E5+, hold-out |

Lesson file schema (proposal):

```json
{
  "id": "projectile-2", "course": "how-far", "title": "The 45° rule",
  "objectives": ["..."], "body_md": "...", "citations": ["F1"],
  "scene": {"type": "projectile", "params": {"initial_velocity": 20, "drag_coefficient": 0},
            "show_vectors": ["velocity", "gravity"]},
  "checkpoint": {"type": "predict_number", "prompt": "Best launch angle?", "unit": "deg",
                 "answer_source": "simulation:optimize_angle", "tolerance": 1.0},
  "lab_link": {"experiment": "control"}
}
```

## 5. AI chat with Omnigent (`technology/src/components/chat/`, `backend/app/agents/`)

Naming: the framework is **Omnigent** (open source, `omnigent-ai/omnigent`). The backend README's
"Databricks OmniAgent" refers to the same thing; use "Omnigent" everywhere.

| ID | Pri | Requirement | Acceptance criteria |
|---|---|---|---|
| CHAT-1 | M | **Chat panel** docked beside the 3D view, available in every lesson and the Discovery Lab | Open/close without losing the conversation for the session |
| CHAT-2 | M | **Research mode**: the student's question or hypothesis starts an Omnigent session with the lab agents (planner, literature, hypothesis, experiment planner, analysis). Agent messages stream back | First agent message streams within 5 s; the answer cites record ids |
| CHAT-3 | M | **Experiment cards**: when an agent proposes or runs an experiment, the chat shows a card (question, prediction, result, verdict) with a "Show in 3D" button that triggers VIS-4 replay | Every `run_experiment` call produces a card |
| CHAT-4 | M | **Human approval in chat**: when the policy returns ASK (large or self-approved runs), show Approve / Deny buttons; the agent waits | Deny stops the run; the decision is logged in the record |
| CHAT-5 | M | **Labels on claims**: badges for established fact (with source), simulation result, AI hypothesis, assumption | Badge comes from the record entry's `epistemic_status` |
| CHAT-6 | S | **Tutor mode** (inside lessons): explains the current scene, grounded in the current parameters and results; refuses to invent numbers ("let's run it" instead) | Asking about the current trajectory includes its real measured values |
| CHAT-7 | S | **Agent identity**: every message shows which agent spoke, as its animal avatar (UI-4) | |
| CHAT-8 | M | **Cost and abuse limits**: per-session spending cap (Omnigent `cost_budget`), tool-call cap, backend rate limit per IP; API keys only on the server, never in `VITE_*` variables | Load test: requests over the limit get HTTP 429 |
| CHAT-9 | M | **Offline fallback**: if the LLM or Omnigent is unavailable, the Discovery Lab can replay the deterministic autopilot run (same record format) so the demo still works | Demo works with no API key |
| CHAT-10 | W | Saved chat history across devices, accounts | |

Backend endpoints needed (proposal for Tom; exact contracts go in [interfaces.md](interfaces.md)):

| Endpoint | Purpose |
|---|---|
| `GET /health` | exists |
| `POST /api/simulate` | one trajectory + measurements (`physics_lab.simulate`) |
| `POST /api/optimize` | best angle for given parameters, with search trace (lesson checkpoints) |
| `POST /api/lab/runs` | start a discovery run (`mode`: `omnigent` or `autopilot`) → run id |
| `GET /api/lab/runs/{id}/events` | server-sent events: each new record entry, approvals, status |
| `GET /api/lab/runs/{id}/record` | full research record |
| `POST /api/lab/runs/{id}/approvals/{request}` | approve or deny a pending ASK |
| `POST /api/chat` (SSE) | chat message → Omnigent session stream (tutor or research mode) |
| `GET /api/courses`, `GET /api/courses/{id}` | course content (or ship content statically with the frontend) |

## 6. UI theme: animal, blue, pixel

| ID | Pri | Requirement | Acceptance criteria |
|---|---|---|---|
| UI-1 | M | **Blue palette as design tokens** (CSS variables) used everywhere; no ad-hoc colours | Tokens below; components reference tokens only |
| UI-2 | M | **Readable pixel typography**: pixel font for headings and buttons only; a readable font for lesson text, numbers and chat | Body text ≥ 16 px; numbers never in the decorative font |
| UI-3 | S | **Pixel art style**: pixel borders/panels, pixel icons, `image-rendering: pixelated` for sprites; 3D pixel effect per VIS-8 | Sprites stay crisp at 2× and 3× |
| UI-4 | S | **Animal characters**: each agent and the tutor has a pixel animal avatar (mapping below); characters guide lessons and speak in chat | Each agent has a distinct avatar and name |
| UI-5 | M | **Accessibility**: WCAG AA contrast for text, status shown by icon + text (not colour alone), keyboard navigation for controls and chat, "reduce motion" respected | Lighthouse accessibility ≥ 90 |
| UI-6 | M | **Science stays legible**: hypothesis board, experiment cards and HUD use plain, readable styling inside the themed frame | A judge can read all numbers in the demo video |
| UI-7 | M | **Asset licensing**: fonts and sprites must be original or openly licensed (e.g. OFL, CC0); record sources in `frontend/CREDITS.md` | Every asset listed with its licence |
| UI-8 | S | **Responsive**: desktop first; on narrow screens chat becomes a bottom sheet and the 3D view stays visible | Usable at 375 px width |

**Palette (proposal, contrast-checked for the pairs listed):**

| Token | Hex | Use |
|---|---|---|
| `--bg-deep` | `#0B1B3A` | page background (navy) |
| `--bg-panel` | `#12305E` | panels, cards |
| `--primary` | `#1F5FC9` | buttons with white text (contrast 5.9:1) |
| `--primary-bright` | `#2F7BEA` | highlights, large text, borders only (4.1:1, not for small text) |
| `--sky` | `#8EC5FF` | links, selected states |
| `--text` | `#EAF4FF` | text on panel (11.7:1) |
| `--accent` | `#FFD23F` | velocity vector, attention |
| `--supported` / `--refuted` / `--testing` | `#3DDC97` / `#FF5D73` / `#FFD23F` | hypothesis status, always with ✓ / ✗ / … and a word |

Vectors in 3D: velocity `--accent`, gravity `--text`, drag coral `#FF8C61`, net `--supported`,
each with a text label.

**Fonts (open licence):** headings "Press Start 2P" or "Silkscreen"; body "VT323" or a clean
sans for long text (decide after a readability check).

**Animal cast (proposal):** projectiles stay balls. Animals are the scientists, never thrown.

| Role | Animal | Why |
|---|---|---|
| Research planner | Blue whale "Captain Blue" | big-picture lead, fits the blue theme |
| Literature agent | Owl | reads the papers |
| Hypothesis agent | Fox | clever guesses |
| Experiment planner | Beaver | builds experiments |
| Analysis agent | Raccoon | checks every number |
| Safety agent | Turtle | careful; asks before big runs |
| Course tutor | Otter | friendly guide in lessons |

## 7. Non-functional requirements

| ID | Pri | Requirement |
|---|---|---|
| NFR-1 | M | Hosting as set up by Tom: frontend on Vercel, backend on Render (switch to the paid plan before demo day to avoid cold starts); CI must pass before deploy |
| NFR-2 | M | Secrets only in server env vars; hard spending caps on every LLM key |
| NFR-3 | M | No personal data collected; no accounts; chat content kept only for the session unless the user is told otherwise |
| NFR-4 | M | Backend imports the science package (`physics_lab`, pure standard-library Python) rather than re-implementing physics |
| NFR-5 | S | Demo resilience: a recorded example run (`docs/results/example-run/record.json`) can drive every screen without network or keys |
| NFR-6 | S | Tests: physics vs closed form (exists), frontend `lib/` unit tests, one end-to-end smoke test of course lesson 2 and a chat research run |

## 8. Demo flow (2 minutes, acceptance test for the whole product)

| Time | Screen | What it proves |
|---|---|---|
| 0:00–0:15 | Pixel/blue home → course "How far can it fly?" → Otter tutor | product + theme |
| 0:15–0:35 | Lesson 3: student predicts drag's effect, runs it in 3D with vectors; measured vs predicted | courses + 3D + predict-then-test |
| 0:35–1:20 | Discovery Lab: student asks in chat "Is there a law for the best angle with air?". Whale planner delegates; Owl cites the 1998 paper; Fox proposes H1–H3; Beaver's experiments replay in 3D (Earth/Mars/Venus land at the same angle); Turtle asks for approval | Omnigent multi-agent loop, evidence, safety |
| 1:20–1:45 | Experiment card: "Predicted 22.9°, measured 25.2°: MISS" → decision "escalate" → new law predicts the next runs → hold-out error 0.03° | **result changes the next decision** |
| 1:45–2:00 | Results panel: law (pending human review), 2.9× fewer simulations than the manual baseline, limitations | measured progress, honesty |

## 9. Scope cut order (if time runs out, cut from the top)

1. VIS-9 extra scenes, CRS-8 second course
2. UI-4 full animal cast (keep the whale and otter only)
3. VIS-8 3D pixel effect (keep the pixel UI frame)
4. CHAT-6 tutor mode (keep research mode)
5. CRS-6 catalog/progress (link straight into the course)

Never cut: CORE-1…9, VIS-1…4, CRS-1…3, CHAT-2…4, CHAT-9, UI-5.

## 10. Proposed ownership (to confirm in the team chat)

| Area | Proposed owner |
|---|---|
| Hosting, CI/CD, backend API, Omnigent server integration (§5 endpoints, NFR-1/2) | Tom |
| 3D scenes and replay (§3) | Zafar / Khoi (frontend) |
| Courses UI, chat UI, theme (§4–6) | Zafar / Khoi (frontend) |
| Course content, citations, requirements, science package and agents | Bael + science |

## 11. Open questions for the team

1. "Courses": is one 5-lesson course enough for the hackathon, or do we need a catalog of several short ones?
2. Animal cast: animals as the scientists/tutor (proposed), or something else? (We recommend never using animals as projectiles.)
3. Pixel effect in 3D, or a pixel UI frame around a clean 3D scene? Readability of vectors is the risk.
4. Does the chat run Omnigent on the Render backend, or on a separate Omnigent server? (Affects NFR-1 and cold starts.)
5. Which LLM key and budget do we use for the demo, and who holds it?
6. Will the 3D frontend call `/api/simulate` for every replay frame set, or should the backend include trajectories in replay events?
