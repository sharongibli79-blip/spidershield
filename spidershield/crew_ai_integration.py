"""
A local crew of named agents with a source policy table.

Names such as Crew are local classes. This file does not import or call
an external agent service, and it does not download sources.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .safety_guardrails import SafetyGuard


@dataclass
class SourcePolicy:
    source_name: str
    licensing: str
    government_restricted: bool
    public_domain: bool
    requires_attribution: bool


class RAGPermissionChecker:
    """Say whether a named source is allowed. It does not fetch the source."""

    def __init__(self):
        self.sources = self._init_sources()

    def _init_sources(self) -> Dict[str, SourcePolicy]:
        return {
            "github": SourcePolicy(
                source_name="GitHub",
                licensing="VARIES",
                government_restricted=False,
                public_domain=False,
                requires_attribution=True,
            ),
            "wikipedia": SourcePolicy(
                source_name="Wikipedia",
                licensing="CC-BY-SA",
                government_restricted=False,
                public_domain=False,
                requires_attribution=True,
            ),
            "public_domain": SourcePolicy(
                source_name="Public Domain",
                licensing="PUBLIC_DOMAIN",
                government_restricted=False,
                public_domain=True,
                requires_attribution=False,
            ),
            "government": SourcePolicy(
                source_name="Government Data",
                licensing="PUBLIC",
                government_restricted=True,
                public_domain=False,
                requires_attribution=False,
            ),
        }

    def can_download(self, source: str) -> tuple[bool, str]:
        policy = self.sources.get(source.lower())
        if policy is None:
            return False, f"Unknown source: {source}"
        if policy.government_restricted:
            return False, "Government data is restricted"
        if policy.public_domain:
            return True, "Public domain — allowed"
        if policy.requires_attribution:
            return True, f"{policy.licensing} — allowed only with attribution; nothing is downloaded"
        return True, f"{policy.source_name} — allowed; nothing is downloaded"

    def get_requirements(self, source: str) -> Dict[str, Any]:
        policy = self.sources.get(source.lower())
        if policy is None:
            return {}
        return {
            "source": policy.source_name,
            "requires_attribution": policy.requires_attribution,
            "licensing": policy.licensing,
            "government_restricted": policy.government_restricted,
        }


class SafeCrewAgent:
    """One named agent. Retrieval happens only if the caller passes a function."""

    def __init__(self, agent_name: str, agent_role: str):
        self.name = agent_name
        self.role = agent_role
        self.safety_guard = SafetyGuard()
        self.rag_checker = RAGPermissionChecker()
        self.task_history: List[Dict[str, Any]] = []

    def can_perform_task(self, task: str) -> tuple[bool, List[str]]:
        return self.safety_guard.assess_task(task)

    def can_access_source(self, source: str) -> tuple[bool, str]:
        return self.rag_checker.can_download(source)

    def execute_rag_query(
        self,
        query: str,
        sources: List[str],
        retriever: Optional[Callable[[str, str], Any]] = None,
    ) -> Dict[str, Any]:
        """
        Check each source. Call retriever only after an allow.

        Without a retriever the result data is null. No placeholder text is invented.
        """
        checked: List[Dict[str, Any]] = []
        results: List[Dict[str, Any]] = []
        for source in sources:
            allowed, reason = self.can_access_source(source)
            requirements = self.rag_checker.get_requirements(source)
            checked.append(
                {
                    "source": source,
                    "allowed": allowed,
                    "reason": reason,
                    "requirements": requirements,
                }
            )
            if not allowed:
                results.append({"source": source, "data": None, "note": reason})
                continue
            if retriever is None:
                results.append(
                    {
                        "source": source,
                        "data": None,
                        "note": "allowed; no retriever attached",
                        "attribution_needed": bool(requirements.get("requires_attribution")),
                    }
                )
                continue
            try:
                data = retriever(query, source)
            except Exception as exc:  # noqa: BLE001 — surface the caller's error
                data = None
                reason = str(exc)
            results.append(
                {
                    "source": source,
                    "data": data,
                    "note": reason,
                    "attribution_needed": bool(requirements.get("requires_attribution")),
                }
            )
        record = {"query": query, "sources": checked, "results": results}
        self.task_history.append({"query": query, "source_count": len(sources)})
        return record

    def get_audit_report(self) -> Dict[str, Any]:
        return {
            "agent": self.name,
            "role": self.role,
            "safety_report": self.safety_guard.report(),
            "task_count": len(self.task_history),
        }


class SafeAgentCrew:
    """A dictionary of SafeCrewAgent objects."""

    def __init__(self):
        self.agents: Dict[str, SafeCrewAgent] = {}
        self.safety_guard = SafetyGuard()

    def add_agent(self, agent_name: str, agent_role: str) -> SafeCrewAgent:
        agent = SafeCrewAgent(agent_name, agent_role)
        self.agents[agent_name] = agent
        return agent

    def execute_crew_task(self, task: str, agent_name: str) -> Dict[str, Any]:
        agent = self.agents.get(agent_name)
        if agent is None:
            return {"success": False, "error": f"Agent {agent_name} not found"}
        allowed, warnings = agent.can_perform_task(task)
        if not allowed:
            return {"success": False, "agent": agent_name, "warnings": warnings}
        return {
            "success": True,
            "agent": agent_name,
            "result": agent.execute_rag_query(task, []),
        }

    def get_crew_report(self) -> Dict[str, Any]:
        return {
            "agents": {name: agent.get_audit_report() for name, agent in self.agents.items()},
            "safety_report": self.safety_guard.report(),
        }


__all__ = [
    "RAGPermissionChecker",
    "SafeAgentCrew",
    "SafeCrewAgent",
    "SourcePolicy",
]
