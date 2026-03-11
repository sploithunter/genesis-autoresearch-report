# Genesis AutoResearch - Iteration Log

Experiment: Can Genesis-based DDS tools make AI coding assistants reliably pass hard DDS benchmark tasks?

**Variable:** Genesis tool services (API reference, code patterns, diagnostics)
**Metric:** Pass rate on 3 hard harness-bench tasks (LR-01, LD-07, LQ-01)
**Model:** Opus 4.6 via Claude Code subscription
**Goal:** Consistent 3/3 passes (currently ~1/3 baseline)

---

## Iteration 0 - Baseline

### Setup
- Created branch: `autoresearch/experiment-v1`
- Built 3 Genesis services: DDSReferenceService, DDSPatternService, DDSDiagnosticService
- Built CLI client: genesis_dds_tool.py
- Established baseline: Opus 4.6 solo on 3 target tasks, 3 runs each

### Baseline Attempt 1 (FAILED - Environment Issue)
**Harness:** claude-sub, **Model:** opus (4.6), **Timeout:** 300s

| Task | Result | Failure Reason |
|------|--------|----------------|
| LR-01 | FAIL | verify.py: `ModuleNotFoundError: No module named 'rti'` |
| LD-07 | FAIL | `subscriber_gets_pub_guid.py not found` (timeout before file creation) |
| LQ-01 | FAIL | publisher.py: `ModuleNotFoundError: No module named 'rti'` |

**Root cause:** Benchmark ran outside Genesis `.venv` where RTI DDS is installed.
Verification scripts couldn't import `rti.connextdds`. All 3 hit 300s timeout.

**Fix:** Re-running with Genesis `.venv` activated and 600s timeout.

### Baseline Attempt 2 (IN PROGRESS)
**Harness:** claude-sub, **Model:** opus (4.6), **Timeout:** 600s
**Environment:** Genesis `.venv` activated, RTI DDS verified available

| Task | Run 1 | Pass Rate |
|------|-------|-----------|
| LR-01 | running | - |
| LD-07 | pending | - |
| LQ-01 | pending | - |

### Smoke Test Results (Pre-Baseline)
- All 3 Genesis services start and register on domain 55
- CLI client discovers 8 functions across 3 services
- `lookup_api(rti.rpc, Requester)` returns correct constructor + methods
- `get_qos_recipe(late_joiner)` returns TRANSIENT_LOCAL + RELIABLE + KEEP_ALL
- `diagnose_error("idl.dataclass is not defined")` correctly suggests @idl.struct
- End-to-end Genesis RPC working: service -> DDS -> CLI client -> JSON output

---
