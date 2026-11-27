# SPIDERSHIELD

Local permission checks for agent tasks.

The library decides whether a task sentence, a code snippet, or a source name is allowed. It keeps that decision in memory. It does not send the decision anywhere.

## What it does

- Allow, restrict, or block an action. A restricted action passes only for a resource you listed.
- Scan a snippet for dangerous call shapes such as `os.system`, `eval`, and `open(..., "w")`.
- Stop waiting on a slow call after a timeout. The caller returns. The library does not claim to kill the worker thread.
- Record an audit list on the object that made the decision.
- Say whether a known source name is allowed. It does not download the source.

## What it does not do

- It is not a firewall, an antivirus, or a sandbox.
- It does not call an agent service.
- It does not open a network connection.
- It does not collect usage data.
- It does not invent retrieved text. If you do not pass a retriever, `data` is null.

## Run

Python 3.10 or newer. The standard library is enough.

```bash
python example_usage.py
```

```bash
python -m unittest discover -s tests -v
```

`requirements.txt` is intentionally empty. This command installs nothing:

```bash
pip install -r requirements.txt
```

From this folder:

```python
from spidershield import SafeAgentCrew

crew = SafeAgentCrew()
researcher = crew.add_agent("Researcher", "Gather data")
result = researcher.execute_rag_query(
    query="Find climate data",
    sources=["wikipedia", "public_domain"],
)
```

`result["results"]` lists each source with `data: null` until you pass your own `retriever(query, source)`. A restricted source is not passed to that function.

## Layout

```
spidershield/
├── safety_guardrails.py    # decisions, scan, timeout, audit
├── agent_executor.py       # task gate, optional runner
├── crew_ai_integration.py  # named agents and source policy
example_usage.py
tests/test_guard.py
```

## License

MIT. See `LICENSE`.
