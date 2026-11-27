"""Local safety checks for agent tasks. Standard library only. No telemetry."""

from .agent_executor import SafeAgentExecutor
from .crew_ai_integration import RAGPermissionChecker, SafeAgentCrew, SafeCrewAgent
from .safety_guardrails import (
    ActionPolicy,
    PermissionLevel,
    SafetyGuard,
    safe_execute,
    task_permissions,
)

__version__ = "0.2.0"

__all__ = [
    "ActionPolicy",
    "PermissionLevel",
    "RAGPermissionChecker",
    "SafeAgentCrew",
    "SafeAgentExecutor",
    "SafeCrewAgent",
    "SafetyGuard",
    "safe_execute",
    "task_permissions",
]
