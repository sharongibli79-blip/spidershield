"""
Safe Agent Executor
Crew AI agents עם Safety Guard
"""

from typing import Dict, Any, List
from safety_guardrails import SafetyGuard, PermissionLevel, safe_execute
import json
import logging


class SafeAgentExecutor:
    """Execute Crew AI agents safely"""

    def __init__(self, safety_config: Dict = None):
        self.safety_guard = SafetyGuard(config=safety_config)
        self.logger = logging.getLogger(__name__)

    def can_execute_action(self, action: str, resource: str = None) -> bool:
        """Check if action is permitted"""
        return self.safety_guard.check_permission(action, resource)

    @safe_execute(timeout_seconds=300)
    def execute_agent_task(self, agent, task, context: Dict = None):
        """Execute agent task safely"""

        # 1. Validate task
        if not self._validate_task(task):
            raise ValueError("Invalid task")

        # 2. Check permissions
        required_perms = self._extract_permissions(task)
        for perm in required_perms:
            if not self.can_execute_action(perm):
                raise PermissionError(f"Permission denied: {perm}")

        # 3. Execute with monitoring
        try:
            result = agent.execute(task, context)
            return result
        except Exception as e:
            self.logger.error(f"Agent execution failed: {e}")
            raise

    def _validate_task(self, task: str) -> bool:
        """Validate task"""
        is_safe, warnings = self.safety_guard.validate_code(task)

        if warnings:
            self.logger.warning(f"Task warnings: {warnings}")
            return False

        return True

    def _extract_permissions(self, task: str) -> List[str]:
        """Extract required permissions from task"""
        permissions = []

        if "download" in task.lower():
            permissions.append("file_download")
        if "read" in task.lower():
            permissions.append("file_read")
        if "http" in task.lower() or "url" in task.lower():
            permissions.append("network_http_get")

        return permissions

    def get_safety_report(self) -> Dict:
        """Get safety report"""
        return self.safety_guard.report()


# ===== Export =====
__all__ = ["SafeAgentExecutor"]
