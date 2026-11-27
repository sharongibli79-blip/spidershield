"""
Local permission checks for agent tasks.

This module does not open a network connection and does not write telemetry.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional


class PermissionLevel(Enum):
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    ALLOWED = "allowed"


@dataclass
class ActionPolicy:
    """Policy for one action name."""

    action: str
    permission: PermissionLevel
    allowed_resources: List[str] = field(default_factory=list)
    timeout_seconds: int = 30
    require_audit: bool = True


_DANGEROUS = (
    re.compile(r"\bexec\s*\("),
    re.compile(r"\beval\s*\("),
    re.compile(r"__import__"),
    re.compile(r"\bos\s*\.\s*system\s*\("),
    re.compile(r"\bsubprocess\s*\.\s*(?:run|call|Popen|check_output|check_call)\s*\("),
    re.compile(r"\bshutil\s*\.\s*rmtree\s*\("),
    re.compile(r"\brequests\s*\.\s*post\s*\("),
    re.compile(r"\burllib\s*\.\s*(?:request\s*\.\s*)?urlopen\s*\("),
    re.compile(r"""\bopen\s*\([^)]*['\"][^'\"]*[wax+][^'\"]*['\"]"""),
)

_TASK_RULES = (
    ("file_delete", (r"\bdelete\b", r"\brmtree\b", r"\bunlink\b", r"\bremove\s+all\b")),
    ("file_write", (r"\bwrite\b", r"\boverwrite\b", r"\bsave\b")),
    ("file_download", (r"\bdownload\b",)),
    ("file_read", (r"\bread\b", r"\bopen\b")),
    ("network_http_post", (r"\bpost\b", r"\bupload\b")),
    ("network_http_get", (r"\bhttps?\b", r"\burl\b", r"\bfetch\b")),
    ("network_file_download", (r"\bdownload\b",)),
)


def task_permissions(task: str) -> List[str]:
    """Map a task sentence to policy names. Word boundaries, so 'already' is not 'read'."""
    text = task.lower()
    found: List[str] = []
    for name, patterns in _TASK_RULES:
        if any(re.search(pattern, text) for pattern in patterns):
            found.append(name)
    return found


class SafetyGuard:
    """In-memory allow / restrict / block decisions and a string scan."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._default_config()
        self.policies = self._build_policies()
        self.audit_log: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)

    def _default_config(self) -> Dict[str, Any]:
        return {
            "file_operations": {
                "read": PermissionLevel.ALLOWED,
                "write": PermissionLevel.RESTRICTED,
                "delete": PermissionLevel.BLOCKED,
                "download": PermissionLevel.RESTRICTED,
            },
            "network": {
                "http_get": PermissionLevel.ALLOWED,
                "http_post": PermissionLevel.RESTRICTED,
                "file_download": PermissionLevel.BLOCKED,
            },
            "execution": {"timeout_seconds": 30},
        }

    def _build_policies(self) -> Dict[str, ActionPolicy]:
        policies: Dict[str, ActionPolicy] = {}
        timeout = int(self.config.get("execution", {}).get("timeout_seconds", 30))
        for action, permission in self.config.get("file_operations", {}).items():
            policies[f"file_{action}"] = ActionPolicy(
                action=f"file_{action}",
                permission=permission,
                timeout_seconds=timeout,
            )
        for action, permission in self.config.get("network", {}).items():
            policies[f"network_{action}"] = ActionPolicy(
                action=f"network_{action}",
                permission=permission,
                timeout_seconds=timeout,
            )
        return policies

    def allow_resource(self, action: str, resource: str) -> None:
        """Add one resource to a RESTRICTED action. Does nothing for unknown actions."""
        policy = self.policies.get(action)
        if policy is None:
            return
        if resource not in policy.allowed_resources:
            policy.allowed_resources.append(resource)

    def check_permission(self, action: str, resource: Optional[str] = None) -> bool:
        """ALLOWED passes. BLOCKED fails. RESTRICTED passes only for a listed resource."""
        policy = self.policies.get(action)
        if policy is None:
            self._record(action, resource, False, "unknown")
            return False
        if policy.permission == PermissionLevel.ALLOWED:
            allowed = True
        elif policy.permission == PermissionLevel.BLOCKED:
            allowed = False
        elif policy.permission == PermissionLevel.RESTRICTED:
            allowed = bool(resource) and resource in policy.allowed_resources
        else:
            allowed = False
        self._record(action, resource, allowed, policy.permission.value)
        return allowed

    def validate_code(self, code: str) -> tuple[bool, List[str]]:
        """Flag dangerous call shapes. This is a scan, not a sandbox."""
        warnings: List[str] = []
        for pattern in _DANGEROUS:
            if pattern.search(code):
                warnings.append(f"Dangerous pattern detected: {pattern.pattern}")
        return (len(warnings) == 0), warnings

    def assess_task(self, task: str) -> tuple[bool, List[str]]:
        """Scan the text, then require every mapped permission to pass."""
        safe, warnings = self.validate_code(task)
        if not safe:
            return False, warnings
        for action in task_permissions(task):
            if not self.check_permission(action):
                warnings.append(f"Permission denied: {action}")
        return (len(warnings) == 0), warnings

    def _record(self, action: str, resource: Optional[str], allowed: bool, policy: str) -> None:
        self.audit_log.append(
            {
                "timestamp": time.time(),
                "action": action,
                "resource": resource,
                "allowed": allowed,
                "policy": policy,
            }
        )

    def get_audit_log(self) -> List[Dict[str, Any]]:
        return list(self.audit_log)

    def report(self) -> Dict[str, Any]:
        total = len(self.audit_log)
        allowed = sum(1 for row in self.audit_log if row["allowed"])
        return {
            "total_actions": total,
            "allowed_actions": allowed,
            "blocked_actions": total - allowed,
            "audit_log": self.get_audit_log(),
        }


def safe_execute(timeout_seconds: int = 30, require_audit: bool = False):
    """
    Stop waiting after timeout_seconds.

    The worker is a daemon thread. On this runtime a running thread cannot be
    force-killed, so a slow call may keep using CPU until the process exits.
    The caller gets a timeout result instead of hanging.
    require_audit is accepted so older call sites keep working. It does not
    send the result anywhere.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            box: Dict[str, Any] = {}

            def run() -> None:
                try:
                    box["result"] = func(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001 — return the error to the caller
                    box["error"] = exc

            started = time.time()
            worker = threading.Thread(target=run, daemon=True)
            worker.start()
            worker.join(timeout_seconds)
            elapsed = time.time() - started
            if worker.is_alive():
                return {
                    "success": False,
                    "error": f"Execution exceeded timeout: {timeout_seconds}s",
                    "elapsed_seconds": elapsed,
                    "audit": bool(require_audit),
                }
            if "error" in box:
                return {
                    "success": False,
                    "error": str(box["error"]),
                    "elapsed_seconds": elapsed,
                }
            return {
                "success": True,
                "result": box.get("result"),
                "elapsed_seconds": elapsed,
            }

        return wrapper

    return decorator


__all__ = [
    "ActionPolicy",
    "PermissionLevel",
    "SafetyGuard",
    "safe_execute",
    "task_permissions",
]
