# Genesis AutoResearch - Current Iteration

## Philosophy: Teacher-Student Knowledge Persistence

The core insight: **once an answer is found, it becomes persistent.**

1. **Teacher provides environment knowledge** — don't let the student waste time on things we already know (which Python has RTI, PATH setup, etc.)
2. **Read ALL logs** (pass and fail) — identify what the agent struggled with
3. **Capture discoveries as Genesis tools** — when a student figures something out, encode it as a Genesis service function so future runs never struggle with it again
4. **Each iteration compounds** — the tool library grows with real, battle-tested knowledge

## Current State: ITERATION 4 — DynamicData Fix for LD-07 + LQ-01 refinement
- **Baseline: 3/9 (33%)** — LR-01: 1/3, LD-07: 0/3, LQ-01: 2/3
- **Iteration 1: 2/3 (67%)** — LR-01 PASS, LD-07 FAIL, LQ-01 PASS
- **Iteration 2: 1/3 (33%)** — LR-01 PASS, LD-07 FAIL, LQ-01 FAIL (regression)
- **Iteration 3: 1/3 (33%)** — LR-01 PASS, LD-07 FAIL, LQ-01 FAIL
- LR-01 SOLVED (100% treatment), dropped from further testing
- Key fixes for iteration 4:
  - **CRITICAL**: Added `dynamicdata_subscriber` pattern — @idl.struct receives ZERO samples from DynamicData publishers (root cause of LD-07 failures)
  - Updated discovery patterns to emphasize DynamicData approach
  - Added @idl.struct vs DynamicData incompatibility to common_errors.json
  - Added DynamicData warning prominently in workspace CLAUDE.md
  - Simplified LQ-01 publisher keepalive guidance (time.sleep(5) only)

## Environment Fixes Applied (for ALL runs)
- `ANTHROPIC_API_KEY` stripped for `claude-sub` → forces OAuth subscription
- Genesis `.venv/bin` prepended to PATH → `python` finds RTI DDS
- Babysitter thread polls tmux every 10s → auto-accepts trust dialogs

## After Baseline Completes

### Step 1: Read conversation logs from ALL baseline runs
```bash
# Find conversation logs from baseline runs
find /Users/jason/Documents/harness-bench/results/logs -name "*.json" -newer baseline_start_marker | sort
```
- Read each log looking for: what did the agent struggle with? What took the longest?
- Even for PASSES: what workarounds did the agent discover? How can we save those?

### Step 2: Extract knowledge into Genesis tools
For each struggle identified:
- If it's API knowledge → add to `dds_reference_service.py` reference data
- If it's a code pattern → add to `dds_pattern_service.py` patterns
- If it's an error/environment issue → add to `dds_diagnostic_service.py`
- If it's a new category → create a new Genesis function

### Step 3: Write CLAUDE.md for treatment workspaces
Create a workspace CLAUDE.md that:
- Tells the agent about available Genesis DDS tools
- Provides environment hints (Python path, RTI DDS location)
- Points to the CLI tool for queries

### Step 4: Run treatment iteration 1
```bash
python autoresearch/runner/run_benchmark.py --iteration 1 --treatment-only
```

### Step 5: Evaluate and document
- Compare treatment vs baseline pass rates
- Check which Genesis functions were called
- Read treatment logs to see if tools were used and helped
- Update ITERATION_LOG.md
- Generate improvement graph
- Commit to branch

## Config
- Harness: claude-sub (subscription, OAuth token)
- Model: opus (4.6)
- Timeout: 300s per task
- Max iterations: 5
- Domain: 55 (Genesis services)
- Runs per task: 1 (treatment), 3 (baseline)
