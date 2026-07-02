# Dynamo log-report Task Submission Pack

## Step 1 — Defects (select all that apply)

- [x] task.toml: artifacts is a string instead of an array (and points to the wrong file)
- [x] environment/Dockerfile uses an unpinned base image
- [x] the agent image leaks the reference solution
- [x] the verifier is gameable (checks the file exists, not its values)
- [x] tests/test.sh writes reward to the wrong path and/or omits ctrf.json
- [x] instruction.md is ambiguous and inconsistent with the verifier

---

## Summarize what was broken and why

**Format:** `task.toml` declared `artifacts = "/app/out.json"` as a string instead of a TOML array, and pointed to the wrong path. Harbor expects a top-level array listing the exact artifact path the agent produces (`/app/report.json`).

**Environment:** The Dockerfile used `FROM python:latest` (unpinned, disallowed) and copied `solution_hint.py` — a full reference implementation — into the agent image. That leaks the oracle and makes the task non-reproducible.

**Verifier:** `test_outputs.py` only checked that `/app/report.json` exists and is nonempty. Any garbage file passes. `test.sh` wrote reward to `/app/reward.txt` instead of `/logs/verifier/reward.txt` and did not emit `ctrf.json`, so Harbor could not grade runs correctly.

**Instruction:** The prompt gave no output path, JSON schema, or numbered success criteria. Agents had no contract to match, and the verifier did not align with any stated requirements.

---

## Corrected task.toml

```toml
artifacts = ["/app/report.json"]

[task]
name = "dynamo/log-report"
description = "Parse an Apache-style access log into a small JSON summary report."

[metadata]
category = "data_processing_and_etl"
subcategory = "text_processing"
task_objective = ["transform", "generate"]
artifact_type = ["text_or_log_file", "generated_output_artifact"]
expert_time_estimate_hours = 0.3
model_tested = "GPT-5.4"
agent_tested = "Terminus-2"
difficulty_explanation = "Parse a small access log and emit summary stats."
solution_explanation = "Read the log, count requests/unique IPs, find the top path."
verification_explanation = "Assert /app/report.json exists, has the required JSON keys, and matches the expected request, IP, and top-path counts from access.log."

[verifier]
timeout_sec = 120.0

[agent]
timeout_sec = 120.0

[environment]
build_timeout_sec = 600.0
cpus = 1
memory_mb = 2048
storage_mb = 10240
gpus = 0
allow_internet = true
mcp_servers = []
```

---

## Corrected environment/Dockerfile

**Removed from build context:** `environment/solution_hint.py` (deleted — it was a leaked reference solution).

```dockerfile
FROM python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

RUN pip install --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5

WORKDIR /app

COPY access.log /app/access.log
```

---

## Why is the original verifier bad?

The original verifier only asserted that `/app/report.json` exists and has size > 0. That means any agent that writes a nonempty file passes — including `{}`, `{"foo": "bar"}`, or `{"total_requests": 999, "unique_ips": 0, "top_path": "/wrong"}`. Wrong counts, wrong schema, and arbitrary garbage all receive reward 1. The nop agent fails only because it creates no file at all, not because the grading checks correctness.

---

## Corrected verifier

### tests/test_outputs.py

```python
import json
from pathlib import Path

REPORT_PATH = Path("/app/report.json")
EXPECTED_KEYS = {"total_requests", "unique_ips", "top_path"}


def _load_report() -> dict:
    return json.loads(REPORT_PATH.read_text())


def test_report_exists():
    """Success criterion 1: /app/report.json exists."""
    assert REPORT_PATH.exists(), "no report.json found"


def test_report_schema():
    """Success criterion 2: valid JSON with exactly the required keys."""
    report = _load_report()
    assert set(report.keys()) == EXPECTED_KEYS, (
        f"expected keys {EXPECTED_KEYS}, got {set(report.keys())}"
    )


def test_total_requests():
    """Success criterion 3: total_requests equals 6."""
    report = _load_report()
    assert report["total_requests"] == 6, (
        f"expected total_requests=6, got {report['total_requests']}"
    )


def test_unique_ips():
    """Success criterion 4: unique_ips equals 3."""
    report = _load_report()
    assert report["unique_ips"] == 3, (
        f"expected unique_ips=3, got {report['unique_ips']}"
    )


def test_top_path():
    """Success criterion 5: top_path equals /index.html."""
    report = _load_report()
    assert report["top_path"] == "/index.html", (
        f"expected top_path='/index.html', got {report['top_path']!r}"
    )
```

### tests/test.sh

```bash
#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier

pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

rc=$?
if [ "$rc" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
```

---

## Rewritten instruction.md

```
There is an Apache-style access log at `/app/access.log`. Each non-blank line is one HTTP request. Parse the log and write a JSON summary report to `/app/report.json`.

For each line, treat the first whitespace-separated field as the client IP. Extract the request path from the quoted request line in the form `"METHOD /path HTTP/x.x"`. Skip blank lines.

The report must be valid JSON with exactly these keys:
- `total_requests` — integer count of non-blank log lines
- `unique_ips` — integer count of distinct client IPs
- `top_path` — string path with the highest request count

Success criteria:
1. `/app/report.json` exists.
2. The file contains valid JSON with exactly the keys `total_requests`, `unique_ips`, and `top_path` (no extra keys).
3. `total_requests` equals 6.
4. `unique_ips` equals 3.
5. `top_path` equals `"/index.html"`.
```

---

## Passing verifier output (oracle + nop)

### oracle

Command:

```bash
harbor run -p log-report -a oracle --job-name check-oracle
```

Result:

```text
Mean: 1.000
Errors: 0
Reward Distribution:
  reward = 1.0      1
```

Artifacts:

```text
reward.txt: 1
ctrf.json summary:
  tests=5, passed=5, failed=0, skipped=0, pending=0, other=0
```

Pytest summary:

```text
PASSED ../tests/test_outputs.py::test_report_exists
PASSED ../tests/test_outputs.py::test_report_schema
PASSED ../tests/test_outputs.py::test_total_requests
PASSED ../tests/test_outputs.py::test_unique_ips
PASSED ../tests/test_outputs.py::test_top_path
============================== 5 passed in 0.03s ===============================
```

### nop

Command:

```bash
harbor run -p log-report --agent nop --job-name check-nop
```

Result:

```text
Mean: 0.000
Errors: 0
Reward Distribution:
  reward = 0.0      1
```

Artifacts:

```text
reward.txt: 0
ctrf.json summary:
  tests=5, passed=0, failed=5, skipped=0, pending=0, other=0
```

Representative failure:

```text
FAILED ../tests/test_outputs.py::test_report_exists - AssertionError: no report.json found
```

---

## Bug proof — verifier catches wrong solution

**Bugged snippet in solution/solve.py:**

```python
json.dump(
    {
        "total_requests": 999,  # intentionally wrong
        "unique_ips": len(ips),
        "top_path": paths.most_common(1)[0][0],
    },
    out,
)
```

**Verifier output (reward=0):**

```
Command:
harbor run -p /tmp/log-report-bad -a oracle --job-name verify-bad-solution

Mean: 0.000
Errors: 0
reward.txt: 0
ctrf.json summary:
  tests=5, passed=4, failed=1, skipped=0, pending=0, other=0

FAILED ../tests/test_outputs.py::test_total_requests - AssertionError: expected total_requests=6, got 999
========================= 1 failed, 4 passed in 0.04s ==========================
```

---

## Link to full fixed task

Paste the final repository URL here after pushing the fixed task:

```
https://github.com/krishprav/dynamo-log-report
```
