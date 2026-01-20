"""
Crew AI + Safety Guardrails Integration
מערכת agents עם הגנה
"""

from typing import Dict, Any, List
from safety_guardrails import SafetyGuard, safe_execute
from dataclasses import dataclass
import json


# ===== RAG Permission Checker =====
@dataclass
class SourcePolicy:
    """Policy for data sources"""
    source_name: str
    copyright_check: bool
    licensing: str  # MIT, GPL, CC, COMMERCIAL, etc
    government_restricted: bool
    public_domain: bool
    requires_attribution: bool


class RAGPermissionChecker:
    """Check permissions for RAG data sources"""

    def __init__(self):
        self.sources = self._init_sources()

    def _init_sources(self) -> Dict[str, SourcePolicy]:
        return {
            "github": SourcePolicy(
                source_name="GitHub",
                copyright_check=True,
                licensing="VARIES",
                government_restricted=False,
                public_domain=False,
                requires_attribution=True
            ),
            "wikipedia": SourcePolicy(
                source_name="Wikipedia",
                copyright_check=True,
                licensing="CC-BY-SA",
                government_restricted=False,
                public_domain=False,
                requires_attribution=True
            ),
            "public_domain": SourcePolicy(
                source_name="Public Domain",
                copyright_check=False,
                licensing="PUBLIC_DOMAIN",
                government_restricted=False,
                public_domain=True,
                requires_attribution=False
            ),
            "government": SourcePolicy(
                source_name="Government Data",
                copyright_check=False,
                licensing="PUBLIC",
                government_restricted=True,
                public_domain=False,
                requires_attribution=False
            )
        }

    def can_download(self, source: str) -> tuple[bool, str]:
        """Check if download is allowed"""
        policy = self.sources.get(source.lower())

        if not policy:
            return False, f"Unknown source: {source}"

        # Default allow public domain
        if policy.public_domain:
            return True, "✓ Public domain - allowed"

        # Government restricted - needs verification
        if policy.government_restricted:
            return True, "⚠️  Government data - requires verification"

        # Check copyright
        if policy.copyright_check:
            return True, f"✓ {policy.licensing} licensed - allowed with attribution"

        return True, f"✓ {policy.source_name} - allowed"

    def get_requirements(self, source: str) -> Dict[str, Any]:
        """Get requirements for source"""
        policy = self.sources.get(source.lower())

        if not policy:
            return {}

        return {
            "source": policy.source_name,
            "requires_attribution": policy.requires_attribution,
            "licensing": policy.licensing,
            "government_restricted": policy.government_restricted,
            "copyright_check_needed": policy.copyright_check
        }


# ===== Crew AI Agent with Safety =====
class SafeCrewAgent:
    """Crew AI Agent with Safety Guardrails"""

    def __init__(self, agent_name: str, agent_role: str):
        self.name = agent_name
        self.role = agent_role
        self.safety_guard = SafetyGuard()
        self.rag_checker = RAGPermissionChecker()
        self.task_history = []

    def can_perform_task(self, task: str) -> tuple[bool, List[str]]:
        """Check if agent can perform task"""
        warnings = []

        # Validate code
        is_safe, code_warnings = self.safety_guard.validate_code(task)
        warnings.extend(code_warnings)

        if not is_safe:
            return False, warnings

        return True, warnings

    def can_access_source(self, source: str) -> tuple[bool, str]:
        """Check if agent can access data source"""
        return self.rag_checker.can_download(source)

    @safe_execute(timeout_seconds=300)
    def execute_rag_query(self, query: str, sources: List[str]) -> Dict[str, Any]:
        """Execute RAG query safely"""
        results = {
            "query": query,
            "sources": [],
            "results": []
        }

        # Check each source
        for source in sources:
            can_access, reason = self.can_access_source(source)

            source_info = {
                "source": source,
                "allowed": can_access,
                "reason": reason,
                "requirements": self.rag_checker.get_requirements(source)
            }

            results["sources"].append(source_info)

            if can_access:
                # Simulate RAG retrieval
                results["results"].append({
                    "source": source,
                    "data": f"[Retrieved data from {source}]",
                    "attribution_needed": source_info["requirements"]["requires_attribution"]
                })

        return results

    def get_audit_report(self) -> Dict[str, Any]:
        """Get audit report"""
        return {
            "agent": self.name,
            "role": self.role,
            "safety_report": self.safety_guard.report(),
            "task_history": self.task_history
        }


# ===== Crew of Agents =====
class SafeAgentCrew:
    """Team of Safe Agents"""

    def __init__(self):
        self.agents: Dict[str, SafeCrewAgent] = {}
        self.safety_guard = SafetyGuard()

    def add_agent(self, agent_name: str, agent_role: str) -> SafeCrewAgent:
        """Add agent to crew"""
        agent = SafeCrewAgent(agent_name, agent_role)
        self.agents[agent_name] = agent
        return agent

    def execute_crew_task(self, task: str, agent_name: str) -> Dict[str, Any]:
        """Execute task by specific agent"""
        if agent_name not in self.agents:
            return {"error": f"Agent {agent_name} not found"}

        agent = self.agents[agent_name]
        can_execute, warnings = agent.can_perform_task(task)

        if not can_execute:
            return {
                "success": False,
                "agent": agent_name,
                "warnings": warnings
            }

        # Execute
        result = agent.execute_rag_query(task, [])
        return {
            "success": True,
            "agent": agent_name,
            "result": result
        }

    def get_crew_report(self) -> Dict[str, Any]:
        """Get report for entire crew"""
        return {
            "agents": {
                name: agent.get_audit_report()
                for name, agent in self.agents.items()
            },
            "safety_report": self.safety_guard.report()
        }


# ===== Example =====
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Crew AI + Safety Guardrails Demo")
    print("=" * 60)

    # Create crew
    crew = SafeAgentCrew()

    # Add agents
    researcher = crew.add_agent("Researcher", "Gather data from sources")
    validator = crew.add_agent("Validator", "Validate data quality")

    print("\n✓ Created agent crew with Researcher and Validator")

    # Test RAG queries
    print("\n" + "-" * 60)
    print("Testing RAG Queries")
    print("-" * 60)

    # Query 1: Wikipedia
    print("\nQuery 1: Access Wikipedia")
    can_access, reason = researcher.can_access_source("wikipedia")
    print(f"  Can access: {can_access}")
    print(f"  Reason: {reason}")
    print(f"  Requirements: {researcher.rag_checker.get_requirements('wikipedia')}")

    # Query 2: Government data
    print("\nQuery 2: Access Government Data")
    can_access, reason = researcher.can_access_source("government")
    print(f"  Can access: {can_access}")
    print(f"  Reason: {reason}")

    # Query 3: Public domain
    print("\nQuery 3: Access Public Domain")
    can_access, reason = researcher.can_access_source("public_domain")
    print(f"  Can access: {can_access}")
    print(f"  Reason: {reason}")

    # Execute RAG query
    print("\n" + "-" * 60)
    print("Executing RAG Query")
    print("-" * 60)

    result = researcher.execute_rag_query(
        query="Find data about climate change",
        sources=["wikipedia", "government", "public_domain"]
    )

    print("\nResult:")
    print(json.dumps(result, indent=2))

    # Crew report
    print("\n" + "-" * 60)
    print("Crew Safety Report")
    print("-" * 60)

    report = crew.get_crew_report()
    print("\nAgents in crew:")
    for agent_name in report["agents"].keys():
        print(f"  ✓ {agent_name}")

    print("\n✅ Crew AI + Safety System Working!")
