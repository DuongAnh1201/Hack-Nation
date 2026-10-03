"""Research Record: the shared persistent lab notebook for all specialist agents."""

import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


KIND_PREFIXES = {
    "question": "Q",
    "assumption": "A",
    "fact": "F",
    "literature": "L",
    "hypothesis": "H",
    "prediction": "P",
    "experiment": "E",
    "approval": "S",
    "result": "R",
    "analysis": "N",
    "decision": "D",
    "conclusion": "C",
}

DEFAULT_EPISTEMIC = {
    "question": "research_question",
    "assumption": "assumption",
    "fact": "established_fact",
    "literature": "literature",
    "hypothesis": "ai_hypothesis",
    "prediction": "ai_prediction",
    "experiment": "experiment_plan",
    "approval": "safety_review",
    "result": "simulation_result",
    "analysis": "analysis",
    "decision": "decision",
    "conclusion": "conclusion",
}


@dataclass
class RecordEntry:
    """A single scientific entry in the research record."""

    id: str
    kind: str
    epistemic_status: str
    agent: str
    summary: str
    data: Dict[str, Any] = field(default_factory=dict)
    refs: List[str] = field(default_factory=list)
    iteration: int = 0
    t: float = 0.0
    status: Optional[str] = None
    status_history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        if self.status is None:
            del res["status"]
            if not self.status_history:
                del res["status_history"]
        return res


class ResearchRecord:
    """The central lab record tracking every scientific observation, decision and test."""

    def __init__(self, question: str = ""):
        self.schema_version = 1
        self.question = question
        self.metrics: Dict[str, Any] = {
            "simulations": 0,
            "experiments": 0,
            "hypotheses": 0,
            "decisions": 0,
        }
        self.entries: List[RecordEntry] = []
        self._counts: Dict[str, int] = {}
        self._start_time = time.time()
        self.listeners: List[Any] = []

    def next_id(self, kind: str) -> str:
        prefix = KIND_PREFIXES.get(kind, kind[:1].upper())
        self._counts[kind] = self._counts.get(kind, 0) + 1
        return f"{prefix}{self._counts[kind]}"

    def add_entry(
        self,
        kind: str,
        summary: str,
        agent: str,
        data: Optional[Dict[str, Any]] = None,
        refs: Optional[List[str]] = None,
        epistemic_status: Optional[str] = None,
        status: Optional[str] = None,
        custom_id: Optional[str] = None,
        iteration: int = 0,
    ) -> RecordEntry:
        """Add an entry to the research record with epistemic validation."""
        entry_id = custom_id if custom_id else self.next_id(kind)
        ep_status = epistemic_status or DEFAULT_EPISTEMIC.get(kind, "unclassified")

        # Validate that established facts cite a source
        if ep_status == "established_fact" and (not data or "source" not in data):
            raise ValueError(f"Entry {entry_id} of status 'established_fact' must provide a 'source' citation in data.")

        entry = RecordEntry(
            id=entry_id,
            kind=kind,
            epistemic_status=ep_status,
            agent=agent,
            summary=summary,
            data=data or {},
            refs=refs or [],
            iteration=iteration,
            t=round(time.time() - self._start_time, 2),
            status=status,
            status_history=[] if status is None else [{"status": status, "t": round(time.time() - self._start_time, 2)}],
        )

        self.entries.append(entry)

        # Update metrics
        if kind == "experiment":
            self.metrics["experiments"] = self.metrics.get("experiments", 0) + 1
        elif kind == "hypothesis":
            self.metrics["hypotheses"] = self.metrics.get("hypotheses", 0) + 1
        elif kind == "decision":
            self.metrics["decisions"] = self.metrics.get("decisions", 0) + 1

        for listener in self.listeners:
            try:
                listener(entry.to_dict())
            except Exception:
                pass

        return entry

    def update_hypothesis_status(self, hypothesis_id: str, new_status: str, rationale: str):
        """Update hypothesis status (proposed, testing, supported, refuted, inconclusive)."""
        entry = self.get_entry(hypothesis_id)
        if not entry:
            raise KeyError(f"Hypothesis '{hypothesis_id}' not found in record.")
        entry.status = new_status
        entry.status_history.append({
            "status": new_status,
            "rationale": rationale,
            "t": round(time.time() - self._start_time, 2),
        })

    def increment_simulations(self, count: int = 1):
        self.metrics["simulations"] = self.metrics.get("simulations", 0) + count

    def get_entry(self, entry_id: str) -> Optional[RecordEntry]:
        for e in self.entries:
            if e.id == entry_id:
                return e
        return None

    def list_entries(self, kind: Optional[str] = None, agent: Optional[str] = None) -> List[RecordEntry]:
        res = self.entries
        if kind:
            res = [e for e in res if e.kind == kind]
        if agent:
            res = [e for e in res if e.agent == agent]
        return res

    def summary(self) -> Dict[str, Any]:
        """Produce high level dashboard summary."""
        hypotheses = [
            {"id": e.id, "summary": e.summary, "status": e.status}
            for e in self.entries if e.kind == "hypothesis"
        ]
        decisions = [
            {"id": e.id, "summary": e.summary, "refs": e.refs}
            for e in self.entries if e.kind == "decision"
        ]
        latest_conclusion = next((e for e in reversed(self.entries) if e.kind == "conclusion"), None)
        return {
            "question": self.question,
            "metrics": self.metrics,
            "total_entries": len(self.entries),
            "hypotheses": hypotheses,
            "decisions": decisions,
            "conclusion": latest_conclusion.summary if latest_conclusion else None,
            "conclusion_status": latest_conclusion.status if latest_conclusion else None,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "question": self.question,
            "metrics": self.metrics,
            "entries": [e.to_dict() for e in self.entries],
        }

    def save(self, filepath: str):
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "ResearchRecord":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        rec = cls(question=data.get("question", ""))
        rec.schema_version = data.get("schema_version", 1)
        rec.metrics = data.get("metrics", {})
        for ed in data.get("entries", []):
            entry = RecordEntry(
                id=ed["id"],
                kind=ed["kind"],
                epistemic_status=ed.get("epistemic_status", "unclassified"),
                agent=ed.get("agent", "unknown"),
                summary=ed.get("summary", ""),
                data=ed.get("data", {}),
                refs=ed.get("refs", []),
                iteration=ed.get("iteration", 0),
                t=ed.get("t", 0.0),
                status=ed.get("status"),
                status_history=ed.get("status_history", []),
            )
            rec.entries.append(entry)
            kind = entry.kind
            # update counters
            num_part = ""
            for char in entry.id:
                if char.isdigit():
                    num_part += char
            if num_part:
                num = int(num_part)
                rec._counts[kind] = max(rec._counts.get(kind, 0), num)
        return rec
