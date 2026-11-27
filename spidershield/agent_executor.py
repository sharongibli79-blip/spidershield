"""
Run a task only after the local safety check.

No network client lives here.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from .safety_guardrails import SafetyGuard, safe_execute


class SafeAgentExecutor:
    """Check a task, then optionally call a runner the user supplied."""

    def __init__(self, safety_config: Optional[Dict[str, Any]] = None):
        self.safety_guard = SafetyGuard(config=safety_config)
        self.logger = logging.getLogger(__name__)

    def can_execute_action(self, action: str, resource: Optional[str] = None) -> bool:
        return self.safety_guard.check_permission(action, resource)

    def execute_agent_task(
        self,
        task: str,
        runner: Optional[Callable[..., Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 30,
    ) -> Dict[str, Any]:
        """
        Refuse a task that fails the scan or the policy.

        When runner is omitted, a passing task is not pretended to have run.
        """
        allowed, warnings = self.safety_guard.assess_task(task)
        if not allowed:
            self.logger.warning("Task refused: %s", warnings)
            return {"success": False, "ran": False, "warnings": warnings}
        if runner is None:
            return {
                "success": True,
                "ran": False,
                "note": "permissions passed; no runner attached",
                "warnings": warnings,
            }

        wrapped = safe_execute(timeout_seconds=timeout_seconds)(runner)
        outcome = wrapped(task, context)
        outcome["ran"] = bool(outcome.get("success"))
        return outcome

    def get_safety_report(self) -> Dict[str, Any]:
        return self.safety_guard.report()


__all__ = ["SafeAgentExecutor"]
