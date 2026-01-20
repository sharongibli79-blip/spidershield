
"""
דוגמה - Safe Crew AI with Guardrails
"""

from safety_guardrails import SafetyGuard, PermissionLevel
from agent_executor import SafeAgentExecutor
import json

# ===== דוגמה 1: Safety Guard בסיסי =====
print("=" * 50)
print("דוגמה 1: Safety Guard")
print("=" * 50)

guard = SafetyGuard()

# בדוק הרשאות
print(f"✓ Read file allowed: {guard.check_permission('file_read')}")
print(f"✗ Delete file allowed: {guard.check_permission('file_delete')}")
print(f"✗ Download file allowed: {guard.check_permission('file_download')}")

# ===== דוגמה 2: Validate Code =====
print("\n" + "=" * 50)
print("דוגמה 2: Code Validation")
print("=" * 50)

dangerous_code = """
import os
os.system("rm -rf /")
"""

safe_code = """
import json
data = json.loads('{"key": "value"}')
"""

is_safe, warnings = guard.validate_code(dangerous_code)
print(f"Dangerous code - Safe: {is_safe}")
if warnings:
    for w in warnings:
        print(f"  ⚠️  {w}")

is_safe, warnings = guard.validate_code(safe_code)
print(f"Safe code - Safe: {is_safe}")

# ===== דוגמה 3: Safe Agent Executor =====
print("\n" + "=" * 50)
print("דוגמה 3: Safe Agent Executor")
print("=" * 50)

executor = SafeAgentExecutor()

# מודל משימה
task_allowed = "read the data from file.txt"
task_denied = "delete all files in /etc"

print(f"Task '{task_allowed}' - Allowed: {executor.can_execute_action('file_read')}")
print(f"Task '{task_denied}' - Allowed: {executor.can_execute_action('file_delete')}")

# ===== דוגמה 4: Safety Report =====
print("\n" + "=" * 50)
print("דוגמה 4: Safety Report")
print("=" * 50)

# Trigger some actions
guard.check_permission("file_read", "data.txt")
guard.check_permission("file_delete", "important.txt")
guard.check_permission("network_http_get", "api.example.com")

report = guard.report()
print(json.dumps(report, indent=2))

print("\n✅ Safety System Ready!")
print("SPIDERSHIELD BOOTING")
