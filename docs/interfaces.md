# Interfaces for the backend and the 3D frontend

The science package is pure standard-library Python (3.10+), with no web framework. Wrap it
however the backend prefers. A ready-made sample record to build the UI against is at
[results/example-run/record.json](results/example-run/record.json).

## Python API

```python
from physics_lab import ProjectileParams, simulate
from physics_lab.agents import LabConfig, run_discovery
from physics_lab.record import ResearchRecord

# one trajectory, with per-frame vectors for the 3D view
r = simulate(ProjectileParams(initial_velocity=30, launch_angle=40, drag_coefficient=0.4),
             record_trajectory=True, max_frames=240)
r.to_dict()  # {"params": {...}, "measurements": {...}, "numerical": {...}, "trajectory": [...]}

# full discovery run with a live event stream (e.g. push each event over a websocket)
rec = run_discovery(LabConfig(offline=False), record_path="runs/live/record.json",
                    listeners=[lambda event: print(event)])

ResearchRecord.load("runs/live/record.json").summary()  # compact state for a dashboard
```

Minimal web wrapper (illustrative; FastAPI is not a dependency of this package):

```python
from fastapi import FastAPI
from physics_lab import ProjectileParams, simulate
from physics_lab.record import ResearchRecord

app = FastAPI()

@app.post("/simulate")
def sim(params: dict):
    return simulate(ProjectileParams.from_dict(params), record_trajectory=True).to_dict()

@app.get("/record")
def record():
    return ResearchRecord.load("runs/omnigent/record.json").to_dict()
```

## `ProjectileParams` (input)

| Field | Unit | Default |
|---|---|---|
| `initial_velocity` | m/s | 30 |
| `launch_angle` | degrees, (0, 90] | 45 |
| `mass` | kg | 0.145 |
| `gravity` | m/s² | 9.81 |
| `drag_coefficient` | C_d, 0 = vacuum | 0 |
| `cross_section_area` | m² | 0.0042 |
| `air_density` | kg/m³ | 1.225 |
| `launch_height` | m | 0 |

Unknown keys raise an error (e.g. `air_resistance`). Presets: objects `baseball`, `shot_put`,
`ping_pong_ball`, `beach_ball`, `bowling_ball`; planets `earth`, `mars`, `venus`
(`physics_lab.physics.presets.preset("ping_pong_ball", "mars")`).

## Trajectory frame (output, for rendering)

Coordinates are y-up (as in Three.js); motion is in the x-y plane, z = 0.

```json
{
  "t": 1.23,
  "position": [x, y, 0], "velocity": [vx, vy, 0], "acceleration": [ax, ay, 0],
  "forces": {"gravity": [0, -m*g, 0], "drag": [fx, fy, 0], "net": [..]},
  "speed": 21.4, "kinetic_energy": 33.2, "potential_energy": 12.1
}
```

Draw arrows from `velocity` (green), `forces.gravity` (down, constant), `forces.drag` (always
opposite the velocity) and `forces.net`. The trail is the list of `position` values. Also show the
`measurements` (range, max height, flight time, energy lost to drag).

## Research record (what the lab is doing)

```json
{"schema_version": 1, "question": "...", "metrics": {"simulations": 651, ...},
 "entries": [{"id": "H3", "kind": "hypothesis", "epistemic_status": "ai_hypothesis",
              "agent": "hypothesis_agent", "summary": "...", "data": {...}, "refs": ["F2", "R2"],
              "iteration": 2, "t": 0.41, "status": "supported", "status_history": [...]}]}
```

| kind | id | What the UI can show |
|---|---|---|
| `question`, `assumption`, `fact`, `literature` | Q, A, F, L | evidence panel (facts have `data.source`, `data.url`) |
| `hypothesis` | H | hypothesis board; colour by `status` (proposed/testing/supported/refuted/inconclusive) |
| `prediction` | P | "the AI predicts X before running": show next to the result |
| `experiment` | E | the spec: `data.conditions`, `data.predictions`, `data.rationale` |
| `approval` | S | safety verdict, human approvals |
| `result` | R | `data.conditions[*]`: `params`, `beta`, `theta_opt_deg`, `range_m`, **`search_trace`** |
| `analysis` | N | law ranking table (`data.ranking`), prospective hits/misses (`data.verdicts`) |
| `decision` | D | timeline caption: `summary` + `data.rationale`, linked to `refs` |
| `conclusion` | C | final law, hold-out error, limitations, `status: pending_human_review` |

**Replaying an experiment in 3D:** for each `result.data.conditions[i]`, iterate `search_trace`
(`angle_deg`, `range_m`, `note`). For each step, call `simulate(params with launch_angle =
angle_deg, record_trajectory=True)` and animate it, with `note` as the caption (e.g. "R(40) >
R(45): optimum is below 45 deg; probe 35"). That shows the agent narrowing the angle on screen.

## 2-minute demo script

Moved to [requirements.md §8](requirements.md#8-demo-flow-2-minutes-acceptance-test-for-the-whole-product)
(now includes the course, chat and theme). Record ids it relies on in the example run: Q1, F4
(question and literature warning), R2/R3 (search traces to replay), P1 → N5 (the failed
prediction), D6 (escalation), N8–N13 (prospective hits and hold-out).

Planned HTTP endpoints for the backend are listed in [requirements.md §5](requirements.md#5-ai-chat-with-omnigent-frontendsrccomponentschat-backendappagents).
