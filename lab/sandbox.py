"""Micro-VM Sandbox Orchestration Module for Docker Sandboxes (`sbx`).

Implements the multi-department architecture with central Knowledge & Memory consolidation
as defined by Person 3:

┌────────────────────────────────────────────────────────────────────────┐
│                              LAB DIRECTOR                              │
│                               Supervisor                               │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
       ┌──────────────┬─────────────┼─────────────┬──────────────┐
       │              │             │             │              │
       ▼              ▼             ▼             ▼              ▼
 ┌────────────┐ ┌────────────┐┌────────────┐┌────────────┐ ┌────────────┐
 │ LITERATURE │ │ HYPOTHESIS ││  PLANNING  ││  ANALYSIS  │ │REV & SAFETY│
 │ DEPARTMENT │ │ DEPARTMENT ││ DEPARTMENT ││ DEPARTMENT │ │ DEPARTMENT │
 └─────┬──────┘ └─────┬──────┘└─────┬──────┘└─────┬──────┘ └─────┬──────┘
       │              │             │             │              │
       └──────────────┴─────────────┼─────────────┴──────────────┘
                                    │
                                    ▼
                      ┌───────────────────────────┐
                      │    KNOWLEDGE & MEMORY     │
                      │        DEPARTMENT         │
                      └─────────────┬─────────────┘
                                    │
                                    ▼
                      ┌───────────────────────────┐
                      │     COMMON KNOWLEDGE      │
                      └─────────────┬─────────────┘
                                    │
                                    +----> next reasoning cycle

Dynamic Spawning Flexibility:
Person 3 determines the number of micro-VMs spawned:
- Hub-and-Spoke Mode (Recommended): 1 dedicated Knowledge & Memory Hub micro-VM + K execution workers.
- Departmental Mesh Mode: 6 micro-VMs (5 execution departments + 1 Knowledge & Memory Hub).
- Specialist Mode: 18 micro-VMs (15 execution specialists + 3 knowledge specialists).
- Unified Mode: 1 micro-VM handling all roles.
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("lab.sandbox")

# ---------------------------------------------------------------------------
# Department & Agent Taxonomy
# ---------------------------------------------------------------------------

SUPERVISOR_ROLE = "lab_director"

DEPARTMENT_HIERARCHY: Dict[str, Dict[str, Any]] = {
    # 5 Execution / Research Departments
    "literature": {
        "lead": "literature_lead",
        "specialists": ["search_agent", "citation_agent", "benchmark_agent"],
        "description": "Scientific papers, prior benchmarks, material databases, and optical constants",
    },
    "hypothesis": {
        "lead": "hypothesis_lead",
        "specialists": ["physics_agent", "material_agent", "design_agent"],
        "description": "Physical models, layer stack proposals, and falsifiable cooling hypotheses",
    },
    "planning": {
        "lead": "planning_lead",
        "specialists": ["cost_agent", "explore_agent", "exploit_agent"],
        "description": "Candidate experiment ranking, exploration vs exploitation, and evaluation budgeting",
    },
    "analysis": {
        "lead": "analysis_lead",
        "specialists": ["stats_agent", "compare_agent", "failure_agent"],
        "description": "Numerical metrics, speed-up statistics, and hypothesis verdict validation",
    },
    "review_safety": {
        "lead": "review_safety_lead",
        "specialists": ["evidence_agent", "claim_agent", "approval_agent"],
        "description": "Human-in-the-loop safety gates, claim audits, and fabrication approvals",
    },
    # Central Consolidation & Memory Department
    "knowledge_memory": {
        "lead": "memory_lead",
        "specialists": ["consolidation_agent", "epistemic_agent", "retrieval_agent"],
        "description": "Aggregates department findings into Common Knowledge to seed subsequent reasoning cycles",
    },
}

EXECUTION_DEPARTMENTS = ["literature", "hypothesis", "planning", "analysis", "review_safety"]
MEMORY_DEPARTMENTS = ["knowledge_memory"]
ALL_DEPARTMENTS = list(DEPARTMENT_HIERARCHY.keys())

ALL_SPECIALISTS = [
    agent
    for dept in DEPARTMENT_HIERARCHY.values()
    for agent in dept["specialists"]
]


# ---------------------------------------------------------------------------
# Common Knowledge & Epistemic State
# ---------------------------------------------------------------------------

@dataclass
class CommonKnowledge:
    """Consolidated state maintained by the Knowledge & Memory Department.

    Feeds into the next reasoning cycle of the Lab Director and departments.
    """
    cycle: int = 1
    target_w_m2: float = 11.827773867918992
    facts: List[Dict[str, Any]] = field(default_factory=list)
    hypotheses: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    plans: List[Dict[str, Any]] = field(default_factory=list)
    simulations: List[Dict[str, Any]] = field(default_factory=list)
    verdicts: List[Dict[str, Any]] = field(default_factory=list)
    safety_approvals: List[Dict[str, Any]] = field(default_factory=list)
    best_design: Optional[Dict[str, Any]] = None
    best_p_net_w_m2: Optional[float] = None
    distilled_insights: List[str] = field(default_factory=list)
    total_evaluations_used: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CommonKnowledge":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class CommonKnowledgeHub:
    """Knowledge & Memory Hub that aggregates findings and prepares next cycle context."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or (Path.cwd() / "runs" / "common_knowledge.json")
        self.state = CommonKnowledge()
        self._load_if_exists()

    def _load_if_exists(self):
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                self.state = CommonKnowledge.from_dict(data)
            except Exception as e:
                logger.warning(f"Could not load existing common knowledge: {e}")

    def save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(json.dumps(self.state.to_dict(), indent=2), encoding="utf-8")

    def record_finding(self, department: str, payload: Dict[str, Any]):
        """Record an entry from any department into Common Knowledge."""
        kind = payload.get("kind", "note")

        if department == "literature" or kind == "fact":
            self.state.facts.append(payload)
        elif department == "hypothesis" or kind == "hypothesis":
            h_id = payload.get("id", f"H{len(self.state.hypotheses) + 1}")
            self.state.hypotheses[h_id] = payload
        elif department == "planning" or kind == "plan":
            self.state.plans.append(payload)
        elif department == "analysis" or kind == "verdict":
            self.state.verdicts.append(payload)
            # Update hypothesis status if verdict references one
            ref_h = payload.get("hypothesis_id")
            if ref_h and ref_h in self.state.hypotheses:
                self.state.hypotheses[ref_h]["status"] = payload.get("status", "evaluated")
        elif department == "review_safety" or kind == "approval":
            self.state.safety_approvals.append(payload)

        # Track simulation results
        if kind == "simulation" or "p_net_w_m2" in payload:
            self.state.simulations.append(payload)
            self.state.total_evaluations_used += 1
            p_net = payload.get("p_net_w_m2")
            if p_net is not None:
                if self.state.best_p_net_w_m2 is None or p_net > self.state.best_p_net_w_m2:
                    self.state.best_p_net_w_m2 = p_net
                    self.state.best_design = payload.get("design", payload)

        self.save()

    def advance_reasoning_cycle(self, summary_note: Optional[str] = None) -> Dict[str, Any]:
        """Consolidate the current cycle and transition to the next reasoning cycle."""
        if summary_note:
            self.state.distilled_insights.append(f"Cycle {self.state.cycle}: {summary_note}")

        next_cycle_context = self.get_context_for_next_cycle()
        self.state.cycle += 1
        self.save()
        return next_cycle_context

    def get_context_for_next_cycle(self) -> Dict[str, Any]:
        """Structured briefing feeding the next reasoning cycle of the Lab Director."""
        supported_hypotheses = [
            h for h in self.state.hypotheses.values()
            if h.get("status") in ("supported", "confirmed")
        ]
        refuted_hypotheses = [
            h for h in self.state.hypotheses.values()
            if h.get("status") in ("refuted", "rejected")
        ]
        open_hypotheses = [
            h for h in self.state.hypotheses.values()
            if h.get("status") in ("proposed", "open", "inconclusive", None)
        ]

        target_met = (
            self.state.best_p_net_w_m2 is not None
            and self.state.best_p_net_w_m2 >= self.state.target_w_m2
        )

        return {
            "current_cycle": self.state.cycle,
            "target_w_m2": self.state.target_w_m2,
            "best_p_net_w_m2": self.state.best_p_net_w_m2,
            "target_met": target_met,
            "best_design": self.state.best_design,
            "total_simulations": len(self.state.simulations),
            "epistemic_summary": {
                "total_hypotheses": len(self.state.hypotheses),
                "supported_count": len(supported_hypotheses),
                "refuted_count": len(refuted_hypotheses),
                "open_count": len(open_hypotheses),
                "open_hypotheses": [h.get("claim", h.get("id")) for h in open_hypotheses],
            },
            "recent_insights": self.state.distilled_insights[-5:],
            "next_cycle_recommendation": (
                "Target reached! Refine layers and run prospective validation."
                if target_met
                else "Falsify lowest-confidence open hypothesis or exploit top candidate design."
            ),
        }


# ---------------------------------------------------------------------------
# Micro-VM Sandbox Model & Topology
# ---------------------------------------------------------------------------

@dataclass
class MicroVMInstance:
    """Metadata and handle for a running micro-VM sandbox."""
    sandbox_id: str
    name: str
    department: str
    role_type: str  # "knowledge_hub", "execution_worker", "supervisor"
    assigned_roles: List[str] = field(default_factory=list)
    status: str = "created"  # created, running, stopped, terminated
    backend: str = "sbx_cloud"  # sbx_cloud, sbx_local, docker, mock
    cpus: int = 2
    memory: str = "4g"
    created_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MicroVMManager:
    """Redesigned Micro-VM Sandbox Manager for Docker Sandboxes (`sbx`).

    Supports flexible topologies determined dynamically by Person 3:
    1. Hub-and-Spoke: 1 dedicated Knowledge & Memory Hub sandbox + K execution workers.
    2. Departmental Mesh: 6 sandboxes (5 execution departments + 1 Knowledge & Memory Hub).
    3. Specialist: 18 sandboxes (all leads and specialists isolated).
    4. Arbitrary Pool: scales dynamically to any number requested.
    """

    def __init__(
        self,
        prefix: str = "rc-sbx",
        default_backend: Optional[str] = None,
        workspace_dir: Optional[Path] = None,
    ):
        self.prefix = prefix
        self.workspace_dir = workspace_dir or Path.cwd()
        self.sandboxes: Dict[str, MicroVMInstance] = {}
        self.knowledge_hub = CommonKnowledgeHub(
            storage_path=self.workspace_dir / "runs" / "common_knowledge.json"
        )

        # Detect active backend
        if default_backend:
            self.backend = default_backend
        elif shutil.which("sbx"):
            # Check if sbx --cloud is logged in
            res = subprocess.run(
                ["sbx", "--cloud", "ls"],
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                self.backend = "sbx_cloud"
            else:
                self.backend = "docker" if shutil.which("docker") else "mock"
        elif shutil.which("docker"):
            self.backend = "docker"
        else:
            self.backend = "mock"

        logger.info(f"MicroVMManager initialized using backend: {self.backend}")

    def spawn_sandboxes(
        self,
        count: int,
        department_allocation: Optional[Dict[str, int]] = None,
        cpus: int = 2,
        memory: str = "4g",
    ) -> List[MicroVMInstance]:
        """Spawn `count` micro-VM sandboxes dynamically according to Person 3's decision.

        Guarantees that the Knowledge & Memory Hub is always provisioned:
        - If count == 1: Unified sandbox (hosts Knowledge & Memory + Execution).
        - If count == 6: 1 micro-VM per department (5 execution + 1 Knowledge & Memory Hub).
        - If count == 18: 1 micro-VM per specialist role + memory roles.
        - Any count K >= 2: Hub-and-Spoke topology (1 Knowledge & Memory Hub + (K - 1) execution workers).
        """
        new_instances: List[MicroVMInstance] = []

        if department_allocation:
            for dept, dept_count in department_allocation.items():
                for idx in range(dept_count):
                    name = f"{self.prefix}-{dept.replace('_', '-')}-{idx+1}"
                    role_type = "knowledge_hub" if dept == "knowledge_memory" else "execution_worker"
                    roles = [DEPARTMENT_HIERARCHY.get(dept, {}).get("lead", "lead")]
                    vm = self._create_microvm(
                        name=name,
                        department=dept,
                        role_type=role_type,
                        roles=roles,
                        cpus=cpus,
                        memory=memory,
                    )
                    new_instances.append(vm)

        elif count == 1:
            # Unified sandbox
            name = f"{self.prefix}-unified"
            vm = self._create_microvm(
                name=name,
                department="all",
                role_type="knowledge_hub",
                roles=["supervisor", "all_departments", "memory_lead"],
                cpus=cpus,
                memory=memory,
            )
            new_instances.append(vm)

        elif count == 6:
            # Departmental Mesh Mode: 5 execution + 1 knowledge & memory hub
            for dept in ALL_DEPARTMENTS:
                name = f"{self.prefix}-{dept.replace('_', '-')}"
                role_type = "knowledge_hub" if dept == "knowledge_memory" else "execution_worker"
                roles = [DEPARTMENT_HIERARCHY[dept]["lead"]] + DEPARTMENT_HIERARCHY[dept]["specialists"]
                vm = self._create_microvm(
                    name=name,
                    department=dept,
                    role_type=role_type,
                    roles=roles,
                    cpus=cpus,
                    memory=memory,
                )
                new_instances.append(vm)

        elif count == 18:
            # Full Specialist Mode
            for dept, info in DEPARTMENT_HIERARCHY.items():
                role_type = "knowledge_hub" if dept == "knowledge_memory" else "execution_worker"
                for spec in info["specialists"]:
                    name = f"{self.prefix}-{spec.replace('_', '-')}"
                    vm = self._create_microvm(
                        name=name,
                        department=dept,
                        role_type=role_type,
                        roles=[spec],
                        cpus=cpus,
                        memory=memory,
                    )
                    new_instances.append(vm)

        else:
            # Hub-and-Spoke: 1 Knowledge & Memory Hub + (count - 1) Execution Workers
            hub_name = f"{self.prefix}-knowledge-memory-hub"
            hub_vm = self._create_microvm(
                name=hub_name,
                department="knowledge_memory",
                role_type="knowledge_hub",
                roles=["memory_lead", "consolidation_agent", "retrieval_agent"],
                cpus=cpus,
                memory=memory,
            )
            new_instances.append(hub_vm)

            worker_count = max(1, count - 1)
            for idx in range(worker_count):
                dept_idx = idx % len(EXECUTION_DEPARTMENTS)
                dept = EXECUTION_DEPARTMENTS[dept_idx]
                name = f"{self.prefix}-worker-{idx+1}"
                vm = self._create_microvm(
                    name=name,
                    department=dept,
                    role_type="execution_worker",
                    roles=[f"{dept}_worker_{idx+1}"],
                    cpus=cpus,
                    memory=memory,
                )
                new_instances.append(vm)

        return new_instances

    def _create_microvm(
        self,
        name: str,
        department: str,
        role_type: str,
        roles: List[str],
        cpus: int,
        memory: str,
    ) -> MicroVMInstance:
        """Instantiate and track a micro-VM instance."""
        sbx_id = f"sbx_{name}_{int(time.time())}"
        instance = MicroVMInstance(
            sandbox_id=sbx_id,
            name=name,
            department=department,
            role_type=role_type,
            assigned_roles=roles,
            status="running",
            backend=self.backend,
            cpus=cpus,
            memory=memory,
            created_at=time.time(),
        )

        if self.backend == "sbx_cloud":
            try:
                cmd = [
                    "sbx", "--cloud", "create",
                    "--name", name,
                    "--cpus", str(cpus),
                    "--memory", memory,
                    "claude",
                ]
                subprocess.run(cmd, check=True, capture_output=True, text=True)
            except Exception as e:
                logger.warning(f"sbx --cloud create failed ({e}), continuing with tracked instance")
        elif self.backend == "docker":
            pass

        self.sandboxes[name] = instance
        return instance

    def exec_command(self, name: str, command: List[str]) -> Dict[str, Any]:
        """Execute a command inside a specific micro-VM sandbox."""
        if name not in self.sandboxes:
            raise KeyError(f"Sandbox {name} not found")

        instance = self.sandboxes[name]

        if instance.backend == "sbx_cloud":
            cmd = ["sbx", "--cloud", "exec", name] + command
            res = subprocess.run(cmd, capture_output=True, text=True)
            return {
                "exit_code": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr,
            }
        elif instance.backend == "docker":
            cmd = ["docker", "exec", name] + command
            res = subprocess.run(cmd, capture_output=True, text=True)
            return {
                "exit_code": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr,
            }
        else:
            # Mock execution (runs on host in workspace directory)
            repo_root = str(Path(__file__).resolve().parent.parent)
            env = dict(os.environ)
            env["PYTHONPATH"] = f"{repo_root}:{env.get('PYTHONPATH', '')}"
            res = subprocess.run(command, capture_output=True, text=True, cwd=self.workspace_dir, env=env)
            return {
                "exit_code": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr,
            }

    def run_simulation_in_sandbox(
        self,
        name: str,
        materials: List[str],
        thicknesses_nm: List[float],
        substrate: str = "Ag",
    ) -> Dict[str, Any]:
        """Execute an isolated simulation inside a micro-VM, and automatically record

        the outcome into Common Knowledge.
        """
        if name not in self.sandboxes:
            raise KeyError(f"Sandbox {name} not found")
        instance = self.sandboxes[name]

        code = f"""
import json, sys
from lab import physics
res = physics.simulate_stack({materials}, {thicknesses_nm}, '{substrate}')
print(json.dumps(res))
"""
        py_bin = sys.executable if instance.backend == "mock" else "python3"
        exec_res = self.exec_command(name, [py_bin, "-c", code])
        if exec_res["exit_code"] != 0:
            raise RuntimeError(f"Simulation failed inside {name}: {exec_res['stderr']}")

        output_line = exec_res["stdout"].strip().splitlines()[-1]
        result = json.loads(output_line)

        # Pipe simulation result into Common Knowledge Hub
        self.knowledge_hub.record_finding(
            department="planning",
            payload={
                "kind": "simulation",
                "sandbox": name,
                "design": {
                    "materials": materials,
                    "thicknesses_nm": thicknesses_nm,
                    "substrate": substrate,
                },
                "p_net_w_m2": result.get("p_net_w_m2"),
                "solar_reflectance": result.get("solar_reflectance"),
                "window_emissivity": result.get("window_emissivity"),
                "valid": result.get("valid", False),
            },
        )

        return result

    def get_knowledge_hub(self) -> CommonKnowledgeHub:
        return self.knowledge_hub

    def advance_cycle(self, summary_note: Optional[str] = None) -> Dict[str, Any]:
        """Advance the Common Knowledge cycle to feed into the next reasoning cycle."""
        return self.knowledge_hub.advance_reasoning_cycle(summary_note=summary_note)

    def list_sandboxes(self) -> List[Dict[str, Any]]:
        return [inst.to_dict() for inst in self.sandboxes.values()]

    def teardown_all(self):
        for name, inst in list(self.sandboxes.items()):
            if inst.backend == "sbx_cloud":
                try:
                    subprocess.run(["sbx", "--cloud", "rm", "--force", name], capture_output=True)
                except Exception:
                    pass
            inst.status = "terminated"
        self.sandboxes.clear()


# Default singleton instance
manager = MicroVMManager()


def get_manager() -> MicroVMManager:
    return manager
