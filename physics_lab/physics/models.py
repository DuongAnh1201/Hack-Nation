"""Data models for physics parameters and simulation results."""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


ALLOWED_PARAM_KEYS = {
    "initial_velocity",
    "launch_angle",
    "mass",
    "gravity",
    "drag_coefficient",
    "cross_section_area",
    "air_density",
    "launch_height",
}


@dataclass
class ProjectileParams:
    """Input parameters for projectile flight simulation."""

    initial_velocity: float = 30.0
    launch_angle: float = 45.0
    mass: float = 0.145
    gravity: float = 9.81
    drag_coefficient: float = 0.0
    cross_section_area: float = 0.0042
    air_density: float = 1.225
    launch_height: float = 0.0

    def __post_init__(self):
        if self.initial_velocity <= 0:
            raise ValueError(f"initial_velocity must be > 0, got {self.initial_velocity}")
        if not (0 < self.launch_angle <= 90):
            raise ValueError(f"launch_angle must be in (0, 90], got {self.launch_angle}")
        if self.mass <= 0:
            raise ValueError(f"mass must be > 0, got {self.mass}")
        if self.gravity <= 0:
            raise ValueError(f"gravity must be > 0, got {self.gravity}")
        if self.drag_coefficient < 0:
            raise ValueError(f"drag_coefficient must be >= 0, got {self.drag_coefficient}")
        if self.cross_section_area <= 0:
            raise ValueError(f"cross_section_area must be > 0, got {self.cross_section_area}")
        if self.air_density < 0:
            raise ValueError(f"air_density must be >= 0, got {self.air_density}")
        if self.launch_height < 0:
            raise ValueError(f"launch_height must be >= 0, got {self.launch_height}")

    @property
    def k(self) -> float:
        """Drag factor k = rho * C_d * A / (2 * m)."""
        return (self.air_density * self.drag_coefficient * self.cross_section_area) / (2.0 * self.mass)

    @property
    def beta(self) -> float:
        """Dimensionless drag group beta = k * v0^2 / g."""
        return (self.k * (self.initial_velocity ** 2)) / self.gravity

    @property
    def eta(self) -> float:
        """Dimensionless launch height group eta = g * h0 / v0^2."""
        return (self.gravity * self.launch_height) / (self.initial_velocity ** 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initial_velocity": self.initial_velocity,
            "launch_angle": self.launch_angle,
            "mass": self.mass,
            "gravity": self.gravity,
            "drag_coefficient": self.drag_coefficient,
            "cross_section_area": self.cross_section_area,
            "air_density": self.air_density,
            "launch_height": self.launch_height,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectileParams":
        unknown = set(data.keys()) - ALLOWED_PARAM_KEYS
        if unknown:
            raise ValueError(f"Unknown projectile parameter(s): {', '.join(sorted(unknown))}")
        return cls(**{k: float(v) for k, v in data.items()})


@dataclass
class TrajectoryFrame:
    """State at a single time step for 3D visualization."""

    t: float
    position: List[float]
    velocity: List[float]
    acceleration: List[float]
    forces: Dict[str, List[float]]
    speed: float
    kinetic_energy: float
    potential_energy: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "t": round(self.t, 4),
            "position": [round(c, 4) for c in self.position],
            "velocity": [round(c, 4) for c in self.velocity],
            "acceleration": [round(c, 4) for c in self.acceleration],
            "forces": {k: [round(c, 4) for c in v] for k, v in self.forces.items()},
            "speed": round(self.speed, 4),
            "kinetic_energy": round(self.kinetic_energy, 4),
            "potential_energy": round(self.potential_energy, 4),
        }


@dataclass
class SimulationResult:
    """Summary and measurements from one trajectory run."""

    params: ProjectileParams
    range_m: float
    flight_time_s: float
    max_height_m: float
    time_to_apex_s: float
    impact_speed_m_s: float
    impact_angle_deg: float
    energy_initial_J: float
    energy_final_J: float
    energy_lost_to_drag_J: float
    energy_error_J: float
    beta: float
    eta: float
    numerical: Dict[str, Any] = field(default_factory=dict)
    trajectory: Optional[List[TrajectoryFrame]] = None

    def to_dict(self) -> Dict[str, Any]:
        res = {
            "params": self.params.to_dict(),
            "measurements": {
                "range_m": self.range_m,
                "flight_time_s": self.flight_time_s,
                "max_height_m": self.max_height_m,
                "time_to_apex_s": self.time_to_apex_s,
                "impact_speed_m_s": self.impact_speed_m_s,
                "impact_angle_deg": self.impact_angle_deg,
                "energy_initial_J": self.energy_initial_J,
                "energy_final_J": self.energy_final_J,
                "energy_lost_to_drag_J": self.energy_lost_to_drag_J,
                "energy_error_J": self.energy_error_J,
                "beta": self.beta,
                "eta": self.eta,
            },
            "numerical": self.numerical,
        }
        if self.trajectory is not None:
            res["trajectory"] = [f.to_dict() for f in self.trajectory]
        return res
