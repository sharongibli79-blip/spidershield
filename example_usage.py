"""Run the local safety demo. Nothing in this file contacts a server."""

import json

from spidershield import SafeAgentCrew, SafeAgentExecutor, SafetyGuard

print("=" * 50)
print("1. Safety Guard")
print("=" * 50)

guard = SafetyGuard()
print(f"read allowed: {guard.check_permission('file_read')}")
print(f"delete allowed: {guard.check_permission('file_delete')}")
print(f"write with no resource: {guard.check_permission('file_write')}")
guard.allow_resource("file_write", "notes/out.txt")
print(f"write notes/out.txt: {guard.check_permission('file_write', 'notes/out.txt')}")

print("\n" + "=" * 50)
print("2. Code scan")
print("=" * 50)

dangerous = 'import os\nos.system("rm -rf /")\n'
safe = 'import json\ndata = json.loads(\'{"key": "value"}\')\n'
is_safe, warnings = guard.validate_code(dangerous)
print(f"dangerous snippet safe: {is_safe}")
for warning in warnings:
    print(f"  {warning}")
is_safe, warnings = guard.validate_code(safe)
print(f"plain snippet safe: {is_safe}")
is_safe, warnings = guard.validate_code('open(path, "w")')
print(f'open for write safe: {is_safe} ({len(warnings)} warning)')

print("\n" + "=" * 50)
print("3. Task gate")
print("=" * 50)

executor = SafeAgentExecutor()
print(executor.execute_agent_task("read the data from file.txt"))
print(executor.execute_agent_task("delete all files in /etc"))

print("\n" + "=" * 50)
print("4. Source policy")
print("=" * 50)

crew = SafeAgentCrew()
researcher = crew.add_agent("Researcher", "Gather data")
result = researcher.execute_rag_query(
    query="Find climate data",
    sources=["wikipedia", "public_domain", "government", "unknown-feed"],
)
print(json.dumps(result, indent=2))
print("\nSafety system ready.")
