# How to Build an AutoResearch Loop with Genesis

A step-by-step technical guide to replicating the Genesis AutoResearch pattern — where a teacher AI agent iteratively builds domain-specific tool services that make student AI agents reliably solve hard coding tasks.

This guide covers two approaches:
1. **Claude Code teacher + Claude Code students** (the approach used in the original experiment)
2. **External orchestrator + any coding agent** (Codex, Devin, Claude Code, or any agent with tool access)

---

## Prerequisites

- **Genesis_LIB** installed and working (`pip install -e .` from the repo root)
- **RTI Connext DDS 7.3.0+** installed with `NDDSHOME` set
- A Python virtual environment with RTI DDS bindings (`rti.connextdds`, `rti.rpc`, `rti.types`)
- A coding benchmark or evaluation harness (we used [harness-bench](https://github.com/sploithunter/harness-bench), but any repeatable task works)
- An LLM API key (Anthropic, OpenAI, etc.)

---

## Part 1: Architecture Overview

The AutoResearch pattern has three components:

```
┌─────────────────────────────────────────────────────────────┐
│                    TEACHER AGENT                             │
│  (Claude Code, Codex, or external script)                    │
│                                                              │
│  1. Analyze student failures                                 │
│  2. Improve Genesis service reference data                   │
│  3. Run next iteration                                       │
│  4. Evaluate results                                         │
│  5. Log and commit                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │ modifies
                       v
┌─────────────────────────────────────────────────────────────┐
│              GENESIS TOOL SERVICES (Domain 55)               │
│                                                              │
│  DDSPatternService     — verified code patterns              │
│  DDSReferenceService   — API signatures and types            │
│  DDSDiagnosticService  — error diagnosis and QoS checking    │
│                                                              │
│  All use @genesis_function() on MonitoredService             │
│  All communicate over DDS domain 55 (isolated from tasks)    │
└──────────────────────┬──────────────────────────────────────┘
                       │ discovered via DDS
                       v
┌─────────────────────────────────────────────────────────────┐
│                    STUDENT AGENT                             │
│  (Claude Code instance solving a benchmark task)             │
│                                                              │
│  1. Reads CLAUDE.md (injected into workspace)                │
│  2. Calls genesis_dds_tool.py to query services              │
│  3. Writes solution code                                     │
│  4. Solution verified by independent test harness            │
└─────────────────────────────────────────────────────────────┘
```

**Key design constraint:** The student agent never sees task answers directly. Genesis services provide general-purpose domain knowledge (API docs, patterns, QoS recipes) — the same kind of reference material a human developer would want. The student still has to write the solution.

---

## Part 2: Building the Genesis Services

### Step 1: Create the directory structure

```
autoresearch/
  config.json                    # Experiment settings
  genesis_program.md             # Iteration goals (teacher reads this)
  ITERATION_LOG.md               # Append-only experiment log

  services/
    dds_reference_service.py     # API reference lookups
    dds_pattern_service.py       # Verified code patterns
    dds_diagnostic_service.py    # Error diagnosis
    reference_data/
      rti_rpc_api.json           # API signatures for rti.rpc
      rti_types_api.json         # API signatures for rti.types
      rti_connextdds_api.json    # API signatures for rti.connextdds
      patterns.json              # Working code patterns
      common_errors.json         # Error → cause → fix mappings
      qos_recipes.json           # QoS configurations by goal
    run_services.sh              # Start all services
    stop_services.sh             # Stop all services

  cli/
    genesis_dds_tool.py          # CLI client for student agents
    workspace_claude_md.txt      # CLAUDE.md template for workspace injection

  runner/
    run_benchmark.py             # Benchmark orchestrator
    evaluate.py                  # Results evaluation
    generate_graph.py            # Improvement graph

  results/
    baseline/                    # Control results (no tools)
    iteration_001/               # Per-iteration treatment results
    iteration_002/
    ...
```

### Step 2: Write the services

Each service inherits from `MonitoredService` and uses `@genesis_function()`. Here's the pattern:

```python
#!/usr/bin/env python3
"""DDSPatternService — serves verified, working code patterns."""

import json
import asyncio
from pathlib import Path
from genesis_lib.monitored_service import MonitoredService
from genesis_lib.decorators import genesis_function

REFERENCE_DIR = Path(__file__).parent / "reference_data"


class DDSPatternService(MonitoredService):
    def __init__(self):
        super().__init__(
            service_name="DDSPatternService",
            domain_id=55,  # Isolated from task domain
        )
        with open(REFERENCE_DIR / "patterns.json") as f:
            self.patterns = json.load(f)

    @genesis_function()
    async def get_pattern(self, pattern_name: str) -> dict:
        """Return a verified, working code pattern by name."""
        if pattern_name in self.patterns:
            return self.patterns[pattern_name]
        # Fuzzy match
        matches = [k for k in self.patterns if pattern_name.lower() in k.lower()]
        if matches:
            return self.patterns[matches[0]]
        return {
            "error": f"Pattern '{pattern_name}' not found",
            "available": list(self.patterns.keys()),
        }

    @genesis_function()
    async def list_patterns(self, category: str = "") -> dict:
        """List available patterns, optionally filtered by category."""
        if category:
            filtered = {
                k: v["description"]
                for k, v in self.patterns.items()
                if category.lower() in v.get("category", "").lower()
            }
            return {"patterns": filtered}
        return {
            "patterns": {k: v["description"] for k, v in self.patterns.items()}
        }

    @genesis_function()
    async def get_qos_recipe(self, goal: str) -> dict:
        """Return QoS configuration for a specific goal."""
        with open(REFERENCE_DIR / "qos_recipes.json") as f:
            recipes = json.load(f)
        if goal in recipes:
            return recipes[goal]
        return {"error": f"Recipe '{goal}' not found", "available": list(recipes.keys())}


async def main():
    service = DDSPatternService()
    print("DDSPatternService running on domain 55...")
    service.run()
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    asyncio.run(main())
```

Follow the same pattern for `DDSReferenceService` (serves API signatures) and `DDSDiagnosticService` (serves error diagnosis). The key is that each service loads its knowledge from JSON reference files, making the knowledge easy to inspect, version, and modify.

### Step 3: Populate reference data

Start with minimal reference data. The teacher agent will improve it over iterations. Here's an example `patterns.json` entry:

```json
{
  "rpc_requester": {
    "description": "Complete RPC Requester pattern using rti.rpc",
    "category": "rpc",
    "code": "import rti.connextdds as dds\nimport rti.rpc as rpc\n\nparticipant = dds.DomainParticipant(domain_id=0)\nrequester = rpc.Requester(\n    request_type=RequestType,\n    reply_type=ReplyType,\n    participant=participant,\n    service_name='MyService'\n)\n\n# Wait for replier\nwhile requester.matched_replier_count == 0:\n    time.sleep(0.1)\n\n# Send request and get reply\nrequester.send_request(request)\nreplies = requester.receive_replies(max_wait=dds.Duration(seconds=10))\nfor reply in replies:\n    print(reply.data)",
    "notes": "Use matched_replier_count (not matched_subscription_count) to wait for replier discovery."
  }
}
```

### Step 4: Build the CLI client

The CLI client is how student agents call Genesis services. It uses `FunctionRequester` from genesis_lib:

```python
#!/usr/bin/env python3
"""CLI client for Genesis DDS tool services."""

import argparse
import json
import sys
import time
from genesis_lib.genesis_app import GenesisApp


def main():
    parser = argparse.ArgumentParser(description="Genesis DDS Tool Client")
    parser.add_argument("-f", "--function", help="Function name to call")
    parser.add_argument("-a", "--args", default="{}", help="JSON arguments")
    parser.add_argument("-l", "--list", action="store_true", help="List available functions")
    parser.add_argument("-d", "--domain", type=int, default=55, help="DDS domain ID")
    parser.add_argument("-t", "--timeout", type=float, default=10, help="Timeout in seconds")
    args = parser.parse_args()

    app = GenesisApp(app_name="DDSToolClient", domain_id=args.domain)
    requester = app.create_function_requester()

    # Wait for function discovery
    deadline = time.time() + args.timeout
    last_count = 0
    stable_since = None
    while time.time() < deadline:
        funcs = requester.discovered_functions()
        if len(funcs) > 0:
            if len(funcs) != last_count:
                last_count = len(funcs)
                stable_since = time.time()
            elif stable_since and time.time() - stable_since > 2.0:
                break
        time.sleep(0.25)

    if args.list:
        funcs = requester.discovered_functions()
        print(json.dumps({"functions": [f.name for f in funcs]}, indent=2))
        return

    if not args.function:
        print("Error: --function required", file=sys.stderr)
        sys.exit(1)

    try:
        fn_args = json.loads(args.args)
        result = requester.call_function(args.function, **fn_args, timeout=args.timeout)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Step 5: Create the workspace CLAUDE.md template

This is how Genesis tools reach the student agent. Create `cli/workspace_claude_md.txt`:

```markdown
# DDS Development Tools

You have Genesis DDS tool services available on DDS domain 55.
Use these tools to look up correct API signatures, get verified code patterns,
and diagnose errors.

## IMPORTANT: Use the correct Python

System Python does NOT have RTI DDS. Always use:
  /path/to/your/.venv/bin/python

## Available Functions

Call functions using:
  /path/to/your/.venv/bin/python {GENESIS_DDS_TOOL_PATH} -f FUNCTION_NAME -a '{"param":"value"}'

### lookup_api — Look up RTI DDS API signatures
  -f lookup_api -a '{"module":"rti.rpc","class_name":"Requester"}'

### get_pattern — Get verified working code patterns
  -f get_pattern -a '{"pattern_name":"rpc_requester"}'

### get_qos_recipe — Get QoS configuration for a goal
  -f get_qos_recipe -a '{"goal":"late_joiner"}'

### diagnose_error — Diagnose DDS errors
  -f diagnose_error -a '{"error_message":"your error here"}'

### list_patterns — List all available patterns
  -f list_patterns -a '{}'

## CRITICAL: @idl.struct vs DynamicData

@idl.struct subscribers receive ZERO samples from DynamicData publishers.
This is a silent failure. For discovery tasks, ALWAYS use:
  -f get_pattern -a '{"pattern_name":"discovery_publication_guid"}'
And copy the StructType + DynamicData pattern directly.

## Tips

- ALWAYS look up APIs before using unfamiliar RTI DDS classes
- Use get_pattern for complete, tested code examples — copy them directly
- Use diagnose_error when you encounter unexpected behavior
```

The `{GENESIS_DDS_TOOL_PATH}` placeholder gets replaced at runtime by `run_benchmark.py`.

---

## Part 3: The Iteration Loop

### Approach A: Claude Code as Teacher (Original Experiment)

In this approach, you (the human) work with Claude Code as a pair programmer. Claude Code acts as the teacher — analyzing results, improving services, running benchmarks.

**Step 1: Establish baseline (run once)**

```bash
python autoresearch/runner/run_benchmark.py --baseline --config autoresearch/config.json
```

This runs each target task 3 times without Genesis tools. Results go to `results/baseline/`.

**Step 2: Run iterations via `/loop`**

In Claude Code, use the `/loop` slash command to trigger recurring iterations:

```
/loop 7m Continue the autoresearch experiment. Run the next treatment iteration, evaluate results, log findings, and commit.
```

This creates a cron job that prompts Claude Code every 7 minutes. Claude Code (the teacher) will:
1. Start Genesis services
2. Run `run_benchmark.py --iteration N --treatment-only`
3. Evaluate results
4. Read student logs if failures occurred
5. Improve reference data if needed
6. Append to `ITERATION_LOG.md`
7. Commit results

**Step 3: Monitor and intervene**

The teacher runs autonomously, but you can intervene at any time:
- Read `ITERATION_LOG.md` to track progress
- Cancel the loop when results plateau
- Manually improve reference data if the teacher misses something

**When to stop:** When you see a sustained streak of perfect runs (we ran 32 consecutive in Phase 1, 19 in Phase 2) and no new failure modes are appearing.


### Approach B: External Orchestrator (Codex, Devin, or any agent)

If your coding agent doesn't have a built-in loop command, use an external cron job to drive the iteration cycle. This is the "Ralph Wiggum loop" pattern from harness-bench — an outer process that repeatedly launches the agent.

**Step 1: Write an iteration script**

Create `run_iteration.sh`:

```bash
#!/bin/bash
# Run one autoresearch iteration
set -e

GENESIS_DIR="/path/to/Genesis_LIB"
CONFIG="$GENESIS_DIR/autoresearch/config.json"
ITERATION_FILE="$GENESIS_DIR/autoresearch/.current_iteration"

# Read and increment iteration counter
if [ -f "$ITERATION_FILE" ]; then
    ITER=$(cat "$ITERATION_FILE")
else
    ITER=1
fi
echo $((ITER + 1)) > "$ITERATION_FILE"

cd "$GENESIS_DIR"
source .venv/bin/activate

# 1. Start Genesis services
bash autoresearch/services/run_services.sh
sleep 5

# 2. Run treatment iteration
python autoresearch/runner/run_benchmark.py \
    --config "$CONFIG" \
    --iteration "$ITER" \
    --treatment-only

# 3. Stop services
bash autoresearch/services/stop_services.sh

# 4. Evaluate
python autoresearch/runner/evaluate.py --iteration "$ITER"

# 5. Generate graph
python autoresearch/runner/generate_graph.py

# 6. Commit results
cd "$GENESIS_DIR"
git add autoresearch/results/ autoresearch/ITERATION_LOG.md
git commit -m "data: iteration $ITER results" || true

echo "Iteration $ITER complete"
```

**Step 2: Schedule with cron**

```bash
# Run every 10 minutes
*/10 * * * * /path/to/run_iteration.sh >> /path/to/autoresearch.log 2>&1
```

Or use a simple while loop for a bounded run:

```bash
#!/bin/bash
# Run N iterations with M-minute gaps
for i in $(seq 1 50); do
    echo "=== Iteration $i ==="
    bash run_iteration.sh
    echo "Sleeping 5 minutes..."
    sleep 300
done
```

**Step 3: Add a teacher step (optional but recommended)**

The external script above runs benchmarks but doesn't improve tools based on failures. To add a teacher:

```bash
# After evaluation, invoke your coding agent as teacher
# Example with Claude Code CLI:
claude --dangerously-skip-permissions -p "
Read autoresearch/results/iteration_${ITER}/results.json and
autoresearch/results/iteration_${ITER}/evaluation.json.
If any tasks failed, read the student logs in the harness-bench results directory.
Identify what went wrong and improve the relevant Genesis service reference data.
Append findings to autoresearch/ITERATION_LOG.md.
"

# Example with Codex:
codex -p "Analyze iteration $ITER results and improve Genesis tools..." \
    --working-dir "$GENESIS_DIR"
```

**Step 4: Add a Codex-specific student runner**

If using Codex as the student agent instead of Claude Code, modify `run_benchmark.py` to launch Codex:

```python
def run_task_codex(task_dir, task_name, with_genesis=False):
    """Run a single task using Codex as the student agent."""
    if with_genesis:
        # Inject tool instructions into the task
        inject_claude_md(task_dir)  # Works for any agent that reads CLAUDE.md
        # Or inject into the prompt directly:
        tool_instructions = open("cli/workspace_claude_md.txt").read()

    prompt = f"""
    Solve the DDS programming task in this directory.
    Run verify.py to check your solution.
    {tool_instructions if with_genesis else ""}
    """

    result = subprocess.run(
        ["codex", "-p", prompt, "--working-dir", str(task_dir)],
        capture_output=True, timeout=timeout_s + 120
    )
    return parse_result(task_dir)
```

---

## Part 4: The Reference Data — What to Encode

The reference data is the variable in the experiment. Here's what we found works:

### Patterns (`patterns.json`)

Each pattern should be:
- **Complete** — a full, working code example, not a fragment
- **Copy-paste ready** — the student can use it directly with minimal modification
- **Annotated** — include `notes` explaining critical details and common pitfalls

```json
{
  "pattern_name": {
    "description": "What this pattern does",
    "category": "rpc|discovery|qos|filtering",
    "code": "complete working Python code as a string",
    "notes": "Critical details, common mistakes, and why alternatives fail"
  }
}
```

### Error Diagnosis (`common_errors.json`)

Map error messages to causes and fixes. Use substring matching:

```json
{
  "errors": [
    {
      "pattern": "ModuleNotFoundError: No module named 'rti'",
      "cause": "Using system Python instead of venv Python",
      "fix": "Use /path/to/.venv/bin/python which has RTI DDS installed"
    },
    {
      "pattern": "receive zero samples",
      "cause": "@idl.struct subscribers cannot receive DynamicData",
      "fix": "Use StructType + DynamicData.DataReader instead of @idl.struct"
    }
  ]
}
```

### QoS Recipes (`qos_recipes.json`)

Complete QoS configurations for specific goals:

```json
{
  "late_joiner": {
    "description": "Allow late-joining subscribers to receive historical data",
    "writer_qos": {
      "durability": "TRANSIENT_LOCAL",
      "reliability": "RELIABLE",
      "history": "KEEP_ALL"
    },
    "reader_qos": {
      "durability": "TRANSIENT_LOCAL",
      "reliability": "RELIABLE",
      "history": "KEEP_ALL"
    },
    "notes": "All three settings must match on both sides. Use time.sleep(5) for publisher keepalive, not wait_for_acknowledgments."
  }
}
```

### What we learned about reference data

1. **Be opinionated.** Don't give the student options. Give it THE answer. "Use this pattern" beats "here are three approaches."
2. **Include warnings about what NOT to do.** The `@idl.struct` warning was more valuable than the `StructType` pattern itself.
3. **Specify the environment.** Telling the student which Python to use saved 30-120 seconds per run.
4. **Start minimal, iterate.** Don't try to encode everything upfront. Run the baseline, see what fails, encode the fix. That's the loop.

---

## Part 5: Evaluation and Metrics

### Per-iteration metrics

After each iteration, `evaluate.py` computes:

```json
{
  "iteration": 15,
  "timestamp": "2026-03-11T...",
  "treatment": {
    "overall_pass_rate": 1.0,
    "per_task": {
      "LR-01": {"passed": true, "time": 73.6, "cost": 0.007},
      "LD-07": {"passed": true, "time": 134.0, "cost": 0.007},
      "LQ-01": {"passed": true, "time": 189.3, "cost": 0.007}
    }
  },
  "baseline_pass_rate": 0.333,
  "delta": 0.667
}
```

### Tracking improvement over time

Append to `metrics_history.json` each iteration. Use this for graphing:

```python
# Minimal graph generation
import json
import matplotlib.pyplot as plt

with open("results/metrics_history.json") as f:
    history = json.load(f)

iters = [h["iteration"] for h in history]
rates = [h["treatment"]["overall_pass_rate"] * 100 for h in history]

plt.plot(iters, rates, 'b-o', label="With Genesis Tools")
plt.axhline(y=33.3, color='r', linestyle='--', label="Baseline")
plt.xlabel("Iteration")
plt.ylabel("Pass Rate (%)")
plt.legend()
plt.savefig("results/improvement_graph.png")
```

### When to declare success

- **Stability:** 10+ consecutive perfect iterations with no tool changes
- **Cross-model:** Same tools work on a cheaper/smaller model
- **Statistical significance:** p < 0.01 that results are not chance (easy to hit with 10+ consecutive passes on a 0% baseline task)

---

## Part 6: Adapting to Your Domain

The DDS experiment is one instance of a general pattern. To apply this to your domain:

### 1. Identify the knowledge gaps

Run your coding agent on your benchmark tasks without tools. Look for:
- Systematic failures (same task fails every time → knowledge gap)
- Common error patterns (model tries the same wrong approach repeatedly)
- Underdocumented APIs or subtle incompatibilities

### 2. Build Genesis services for your domain

Replace DDS-specific services with your domain:

| DDS Experiment | Your Domain |
|---|---|
| DDSPatternService | `YourDomainPatternService` — verified code patterns |
| DDSReferenceService | `YourDomainReferenceService` — API signatures |
| DDSDiagnosticService | `YourDomainDiagnosticService` — error diagnosis |

The service structure stays the same. Only the reference data changes.

### 3. Keep the architecture

- **Domain 55** (or any isolated domain) for Genesis services
- **CLAUDE.md injection** for student tool discovery
- **CLI client** as the bridge between student agent and services
- **JSON reference data** for easy versioning and modification

### 4. Run the loop

Whether you use Claude Code's `/loop`, an external cron job, or a custom orchestrator, the iteration cycle is always:

```
modify tools → run benchmark → evaluate → log → repeat
```

The teacher can be a human, an AI agent, or a combination. The loop works regardless.

---

## Quick Reference

### Start services
```bash
cd autoresearch/services && bash run_services.sh
```

### Run a single iteration
```bash
python autoresearch/runner/run_benchmark.py \
    --config autoresearch/config.json \
    --iteration 1 \
    --treatment-only
```

### Run baseline (once)
```bash
python autoresearch/runner/run_benchmark.py \
    --config autoresearch/config.json \
    --baseline
```

### Evaluate
```bash
python autoresearch/runner/evaluate.py --iteration 1
```

### Query a Genesis service manually
```bash
.venv/bin/python autoresearch/cli/genesis_dds_tool.py \
    -f get_pattern -a '{"pattern_name":"rpc_requester"}'
```

### List all available functions
```bash
.venv/bin/python autoresearch/cli/genesis_dds_tool.py --list
```

### Generate improvement graph
```bash
python autoresearch/runner/generate_graph.py
```

---

## Experiment Configurations

### Minimal config (`config.json`)

```json
{
  "genesis_lib_path": "/path/to/Genesis_LIB",
  "harness_bench_path": "/path/to/harness-bench",
  "target_tasks": ["YOUR_TASK_ID"],
  "harness": "claude-sub",
  "model": "opus",
  "timeout_s": 300,
  "max_iterations": 5,
  "genesis_domain_id": 55,
  "runs_per_task": 1
}
```

### Key parameters

| Parameter | Description | Recommended |
|---|---|---|
| `model` | Student model | Start with your best model, then validate on cheaper ones |
| `timeout_s` | Per-task timeout | 300s (5 min) is a good starting point |
| `max_iterations` | harness-bench retry limit | 5 (the benchmark retries within each run) |
| `genesis_domain_id` | DDS domain for services | 55 (anything not used by your tasks) |
| `runs_per_task` | Runs per task per iteration | 1 for treatment (fast iteration), 3 for baseline |

---

## What We Learned

1. **Start with the baseline.** You can't improve what you can't measure. Run 3+ baseline attempts per task before building any tools.

2. **Read the student logs.** The teacher's most important job is understanding WHY students fail, not just THAT they fail. The fix is always in the failure mode.

3. **One fix at a time.** Change one thing per iteration so you can attribute improvements. When we changed patterns AND environment setup simultaneously, we couldn't tell which helped.

4. **Copy-paste beats explanation.** Students that received complete, working code patterns succeeded far more often than students that received API documentation. Be prescriptive.

5. **The tools plateau fast.** In our experiment, 7 iterations of active tool development produced stable tools that then ran for 30+ iterations without changes. Most of the value comes from 3-5 key insights.

6. **Cross-model validation is the proof.** Running the same tools on a different (especially smaller) model proves the knowledge is real, not a model-specific complement. This is the strongest possible validation.

7. **The loop cost is trivial.** Our 75 iterations across both phases cost ~$8 total. The iteration loop is cheap. Don't over-plan — just run it and learn from what happens.
