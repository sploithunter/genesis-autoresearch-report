# Genesis AutoResearch - Iteration 1

## Current State
- Baseline not yet established
- Three Genesis DDS tool services built with initial reference data
- CLI client and workspace injection ready
- No treatment runs yet

## This Iteration's Goal
1. Establish the Opus 4.6 baseline (3 runs per task, no Genesis tools)
2. Run the first treatment iteration (1 run per task, with Genesis tools)
3. Compare results and identify which tools the coding agent uses (or doesn't)

## Steps
1. [ ] Run baseline: `cd autoresearch && python runner/run_benchmark.py --baseline`
2. [ ] Run treatment iteration 1: `python runner/run_benchmark.py --iteration 1 --treatment-only`
3. [ ] Evaluate: `python runner/evaluate.py --iteration 1`
4. [ ] Generate graph: `python runner/generate_graph.py`
5. [ ] Review results and update ITERATION_LOG.md
6. [ ] Update this file for iteration 2

## Success Criteria
- Baseline is established with clear pass/fail data
- Treatment shows at least 1 task improvement over baseline
- OR: tool usage logs reveal why tools weren't used (informs next iteration)

## Constraints
- Tools must remain general-purpose (not task-specific hints)
- Do NOT modify harness-bench code
- All tools must be Genesis services on domain 55

## What to Modify Next (based on evaluation)
If tools aren't being used:
  - Improve workspace CLAUDE.md instructions to be more prominent
  - Simplify the CLI tool interface

If tools are used but tasks still fail:
  - Review which functions were called and what was returned
  - Add missing API information to reference data
  - Improve pattern examples

If tasks pass with tools:
  - Document what worked
  - Try with Haiku model to test generalization
