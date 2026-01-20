"""
Safety Guardrails System
מערכת הגנה מתקדמת לExecute Agents בטוח
"""

import json
import logging
from typing import Dict, List, Any, Callable
from dataclasses import dataclass
from enum import Enum
import time
from functools import wraps


# ===== Permission Levels =====
class PermissionLevel(Enum):
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    ALLOWED = "allowed"


# ===== Policy Definition =====
@dataclass
class ActionPolicy:
    """Policy for specific action"""
    action: str
    permission: PermissionLevel
    allowed_resources: List[str] = None
    timeout_seconds: int = 300
    max_retries: int = 3
    require_audit: bool = False


# ===== Safety Guard =====
class SafetyGuard:
    """Main Safety Guard System"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._default_config()
        self.policies = self._build_policies()
        self.audit_log = []
        self.logger = logging.getLogger(__name__)

    def _default_config(self) -> Dict:
        return {
            "file_operations": {
                "read": PermissionLevel.ALLOWED,
                "write": PermissionLevel.RESTRICTED,
                "delete": PermissionLevel.BLOCKED,
                "download": PermissionLevel.RESTRICTED
            },
            "network": {
                "http_get": PermissionLevel.ALLOWED,
                "http_post": PermissionLevel.RESTRICTED,
                "file_download": PermissionLevel.BLOCKED
            },
            "execution": {
                "timeout_seconds": 300,
                "max_memory_mb": 1024,
                "allowed_modules": [
                    "os", "sys", "json", "re", "datetime",
                    "math", "random", "requests"
                ]
            },
            "data": {
                "check_copyright": True,
                "check_licensing": True,
                "check_privacy": True
            }
        }

    def _build_policies(self) -> Dict[str, ActionPolicy]:
        """Build policies from config"""
        policies = {}

        # File policies
        for action, permission in self.config["file_operations"].items():
            policies[f"file_{action}"] = ActionPolicy(
                action=f"file_{action}",
                permission=permission,
                timeout_seconds=self.config["execution"]["timeout_seconds"]
            )

        # Network policies
        for action, permission in self.config["network"].items():
            policies[f"network_{action}"] = ActionPolicy(
                action=f"network_{action}",
                permission=permission,
                timeout_seconds=self.config["execution"]["timeout_seconds"]
            )

        return policies

    def check_permission(self, action: str, resource: str = None) -> bool:
        """Check if action is allowed"""
        policy = self.policies.get(action)

        if not policy:
            self.logger.warning(f"Unknown action: {action}")
            return False

        is_allowed = policy.permission == PermissionLevel.ALLOWED

        # Log to audit
        self.audit_log.append({
            "timestamp": time.time(),
            "action": action,
            "resource": resource,
            "allowed": is_allowed,
            "policy": policy.permission.value
        })

        return is_allowed

    def validate_code(self, code: str) -> tuple[bool, List[str]]:
        """Validate code for dangerous operations"""
        dangerous_patterns = [
            "exec(", "eval(", "__import__",
            "os.system(", "subprocess.run(",
            "open(..., 'w'", "shutil.rmtree(",
            "requests.post(", "urllib.urlopen("
        ]

        warnings = []
        for pattern in dangerous_patterns:
            if pattern in code:
                warnings.append(f"Dangerous pattern detected: {pattern}")

        is_safe = len(warnings) == 0
        return is_safe, warnings

    def get_audit_log(self) -> List[Dict]:
        """Get audit log"""
        return self.audit_log

    def report(self) -> Dict:
        """Generate safety report"""
        total_actions = len(self.audit_log)
        allowed_actions = sum(1 for log in self.audit_log if log["allowed"])
        blocked_actions = total_actions - allowed_actions

        return {
            "total_actions": total_actions,
            "allowed_actions": allowed_actions,
            "blocked_actions": blocked_actions,
            "audit_log": self.audit_log
        }


# ===== Execution Wrapper =====
def safe_execute(timeout_seconds=300, require_audit=False):
    """Decorator for safe execution"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time

                if elapsed > timeout_seconds:
                    raise TimeoutError(
                        f"Execution exceeded timeout: {elapsed}s > {timeout_seconds}s"
                    )

                return {
                    "success": True,
                    "result": result,
                    "elapsed_seconds": elapsed
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "elapsed_seconds": time.time() - start_time
                }

        return wrapper

    return decorator


# ===== Export =====
__all__ = ["SafetyGuard", "ActionPolicy", "PermissionLevel", "safe_execute"]