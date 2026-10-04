"""Micro-VM Sandbox Orchestration Module for Docker Sandboxes (`sbx`).

Manages isolated micro-VM sandboxes for research subagents across the
hierarchical departments defined by Person 3:

┌───────────────────────────────────────────────────────────┐
│                    LAB DIRECTOR                           │
│                     Supervisor                            │
└──────────────────────────┬────────────────────────────────┘
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  LITERATURE  │    │  HYPOTHESIS  │    │   PLANNING   │
│  DEPARTMENT  │    │  DEPARTMENT  │    │  DEPARTMENT  │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │
  Lead Agent          Lead Agent          Lead Agent
  ┌────┼────┐         ┌────┼────┐         ┌────┼────┐
  ▼    ▼    ▼         ▼    ▼    ▼         ▼    ▼    ▼
Search Cit  Bench   Phys  Mat   Des     Cost Explor Exploit

       ┌───────────────────┬───────────────────┐
       ▼                   ▼
┌──────────────┐    ┌──────────────┐
│   ANALYSIS   │    │REVIEW & SAFETY│
│  DEPARTMENT  │    │  DEPARTMENT  │
└──────┬───────┘    └──────┬───────┘
       │                   │
  Lead Agent          Lead Agent
  ┌────┼────┐         ┌────┼────┐
  ▼    ▼    ▼         ▼    ▼    ▼
Stats Comp Fail    Evid  Claim Appr

The number of micro-VMs is determined dynamically by Person 3:
- Shared mode (1 micro-VM)
- Department mode (5 micro-VMs, 1 per department)
- Specialist mode (15 micro-VMs, 1 per subagent)
- Elastic pool mode (K micro-VMs assigned to a worker queue)
"""

import json
import logging
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("lab.sandbox")

# ---------------------------------------------------------------------------
# Department & Agent Taxonomy
# ---------------------------------------------------------------------------

SUPERVISOR_ROLE = "lab_director"

DEPARTMENT_HIERARCHY = {
    "literature": {
        "lead": "literature_lead",
        "specialists": ["search_agent", "citation_agent", "benchmark_agent"],
    },
    "hypothesis": {
        "lead": "hypothesis_lead",
        "specialists": ["physics_agent", "material_agent", "design_agent"],
    },
    "planning": {
        "lead": "planning_lead",
        "specialists": ["cost_agent", "explore_agent", "exploit_agent"],
    },
    "analysis": {
        "lead": "analysis_lead",
        "specialists": ["stats_agent", "compare_agent", "failure_agent"],
    },
    "review_safety": {
        "lead": "review_safety_lead",
        "specialists": ["evidence_agent", "claim_agent", "approval_agent"],
    },
}

ALL_DEPARTMENTS = list(DEPARTMENT_HIERARCHY.keys())
ALL_SPECIALISTS = [
    agent
    for dept in DEPARTMENT_HIERARCHY.values()
    for agent in dept["specialists"]
]


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class MicroVMInstance:
    """Metadata and handle for a running micro-VM sandbox."""
    sandbox_id: str
    name: str
    department: Optional[str] = None
    assigned_roles: List[str] = field(default_factory=list)
    status: str = "created"  # created, running, stopped, terminated
    backend: str = "sbx_cloud"  # sbx_cloud, sbx_local, docker, mock
    cpus: int = 2
    memory: str = "4g"
    created_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Micro-VM Sandbox Manager
# ---------------------------------------------------------------------------

class MicroVMManager:
    """Manages spawning, execution, scaling, and teardown of Docker Micro-VM sandboxes.

    Person 3's Omnigent orchestration invokes this manager to spin up micro-VMs
    and execute simulations, queries, and agent scripts in isolated environments.
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

        # Determine backend: sbx_cloud if sbx is available, else local docker / mock
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
        """Dynamically spawn `count` micro-VM sandboxes as requested by Person 3.

        Allocation strategies:
        - count == 1: 1 shared micro-VM for the whole team.
        - count == 5: 1 micro-VM per department (literature, hypothesis, etc.).
        - count == 15: 1 micro-VM per specialist agent.
        - custom count: mapped according to department_allocation or round-robin.
        """
        import time

        new_instances: List[MicroVMInstance] = []

        if department_allocation:
            # Explicit department allocation
            for dept, dept_count in department_allocation.items():
                for idx in range(dept_count):
                    name = f"{self.prefix}-{dept}-{idx+1}"
                    roles = [DEPARTMENT_HIERARCHY.get(dept, {}).get("lead", "lead")]
                    vm = self._create_microvm(
                        name=name,
                        department=dept,
                        roles=roles,
                        cpus=cpus,
                        memory=memory,
                    )
                    new_instances.append(vm)
        elif count == 5:
            # 1 micro-VM per department
            for dept in ALL_DEPARTMENTS:
                name = f"{self.prefix}-{dept.replace('_', '-')}"
                roles = [DEPARTMENT_HIERARCHY[dept]["lead"]] + DEPARTMENT_HIERARCHY[dept]["specialists"]
                vm = self._create_microvm(
                    name=name,
                    department=dept,
                    roles=roles,
                    cpus=cpus,
                    memory=memory,
                )
                new_instances.append(vm)
        elif count == 15:
            # 1 micro-VM per specialist
            for dept, info in DEPARTMENT_HIERARCHY.items():
                for spec in info["specialists"]:
                    name = f"{self.prefix}-{spec.replace('_', '-')}"
                    vm = self._create_microvm(
                        name=name,
                        department=dept,
                        roles=[spec],
                        cpus=cpus,
                        memory=memory,
                    )
                    new_instances.append(vm)
        else:
            # Generic pool of count workers
            for idx in range(count):
                dept_idx = idx % len(ALL_DEPARTMENTS)
                dept = ALL_DEPARTMENTS[dept_idx]
                name = f"{self.prefix}-worker-{idx+1}"
                vm = self._create_microvm(
                    name=name,
                    department=dept,
                    roles=[f"worker_{idx+1}"],
                    cpus=cpus,
                    memory=memory,
                )
                new_instances.append(vm)

        return new_instances

    def _create_microvm(
        self,
        name: str,
        department: Optional[str],
        roles: List[str],
        cpus: int,
        memory: str,
    ) -> MicroVMInstance:
        """Create a single micro-VM sandbox."""
        import time

        sbx_id = f"sbx_{name}_{int(time.time())}"
        instance = MicroVMInstance(
            sandbox_id=sbx_id,
            name=name,
            department=department,
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
                logger.warning(f"sbx --cloud create failed ({e}), keeping local mock tracking")
        elif self.backend == "docker":
            # Can spin up container using Docker if desired
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
            # Mock execution (runs locally within workspace)
            res = subprocess.run(command, capture_output=True, text=True, cwd=self.workspace_dir)
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
        """Execute an isolated simulation within the micro-VM sandbox.

        Calls the simulator inside the micro-VM and parses the JSON output.
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
        return json.loads(output_line)

    def list_sandboxes(self) -> List[Dict[str, Any]]:
        """List all active micro-VM sandboxes."""
        return [inst.to_dict() for inst in self.sandboxes.values()]

    def teardown_all(self):
        """Clean up and remove all micro-VM sandboxes."""
        for name, inst in list(self.sandboxes.items()):
            if inst.backend == "sbx_cloud":
                try:
                    subprocess.run(["sbx", "--cloud", "rm", "--force", name], capture_output=True)
                except Exception:
                    pass
            inst.status = "terminated"
        self.sandboxes.clear()


# Default global instance
manager = MicroVMManager()


def get_manager() -> MicroVMManager:
    return manager
