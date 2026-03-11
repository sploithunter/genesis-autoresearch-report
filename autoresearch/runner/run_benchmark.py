#!/usr/bin/env python3
"""
AutoResearch Benchmark Runner

Runs harness-bench tasks with or without Genesis DDS tools.
Handles workspace setup, service lifecycle, and result collection.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

AUTORESEARCH_DIR = Path(__file__).parent.parent
GENESIS_DIR = AUTORESEARCH_DIR.parent
CONFIG_PATH = AUTORESEARCH_DIR / "config.json"


def load_config(config_path=None):
    path = Path(config_path) if config_path else CONFIG_PATH
    with open(path) as f:
        return json.load(f)


def start_services():
    """Start Genesis DDS tool services."""
    script = AUTORESEARCH_DIR / "services" / "run_services.sh"
    subprocess.run(["bash", str(script)], cwd=str(GENESIS_DIR))
    print("Genesis services started.")


def stop_services():
    """Stop Genesis DDS tool services."""
    script = AUTORESEARCH_DIR / "services" / "stop_services.sh"
    subprocess.run(["bash", str(script)], cwd=str(GENESIS_DIR))
    print("Genesis services stopped.")


def verify_services():
    """Verify Genesis services are responding."""
    cli_tool = AUTORESEARCH_DIR / "cli" / "genesis_dds_tool.py"
    try:
        result = subprocess.run(
            [sys.executable, str(cli_tool), "--list", "--timeout", "10"],
            capture_output=True, text=True, timeout=15, cwd=str(GENESIS_DIR),
            env={**os.environ, "PYTHONPATH": str(GENESIS_DIR)}
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            count = data.get("count", 0)
            print(f"Genesis services verified: {count} functions available.")
            return count > 0
    except Exception as e:
        print(f"Service verification failed: {e}")
    return False


def _babysit_tmux(stop_event, poll_interval=10):
    """Background thread that monitors harness tmux sessions.

    Handles interactive prompts (trust dialog, confirmations) that would
    otherwise block the harness session indefinitely.
    """
    while not stop_event.is_set():
        try:
            # Find harness-bench tmux sessions
            result = subprocess.run(
                ["tmux", "list-sessions", "-F", "#{session_name}"],
                capture_output=True, text=True
            )
            sessions = [s for s in result.stdout.strip().split('\n')
                       if s.startswith('harness-bench-')]

            for session in sessions:
                pane = subprocess.run(
                    ["tmux", "capture-pane", "-t", session, "-p", "-S", "-30"],
                    capture_output=True, text=True
                ).stdout

                # Auto-accept trust dialog
                if "Yes, I trust this folder" in pane or "Enter to confirm" in pane:
                    print(f"  [babysit] Trust dialog detected in {session} - accepting")
                    subprocess.run(["tmux", "send-keys", "-t", session, "Enter"],
                                 capture_output=True)

                # Log errors
                for line in pane.split('\n'):
                    if 'Error:' in line and 'cannot launch inside' not in line:
                        print(f"  [babysit] Error in {session}: {line.strip()}")
        except Exception:
            pass  # tmux might not be available, that's fine

        stop_event.wait(poll_interval)


def run_task(config, task_id, with_genesis=False):
    """Run a single harness-bench task."""
    bench_path = Path(config["harness_bench_path"])
    runner = bench_path / "scripts" / "run_dds_benchmark.py"

    cmd = [
        sys.executable, str(runner),
        "--harness", config["harness"],
        "--model", config["model"],
        "--task", task_id,
        "--timeout", str(config["timeout_s"]),
        "--max-iterations", str(config["max_iterations"]),
        "--workers", "1",
    ]

    env = {**os.environ, "PYTHONPATH": str(GENESIS_DIR)}

    # Add Genesis venv Python to PATH so RTI DDS imports work.
    # Without this, the coding agent finds system Python (3.14) which
    # doesn't have rti.connextdds installed, wasting 2-3 minutes per run.
    venv_bin = str(GENESIS_DIR / ".venv" / "bin")
    env["PATH"] = venv_bin + ":" + env.get("PATH", "")

    # For subscription harness, remove ANTHROPIC_API_KEY so Claude CLI
    # falls back to OAuth token (subscription mode). API key always takes
    # priority and will cause $0/0-char failures if it has no credits.
    if config["harness"] == "claude-sub":
        env.pop("ANTHROPIC_API_KEY", None)

    # Track injected CLAUDE.md for cleanup
    injected_claude_md = None

    if with_genesis:
        # Inject Genesis tools by placing CLAUDE.md in the task template directory.
        # The harness copies all files from the template dir into the workspace,
        # so Claude Code will automatically read CLAUDE.md on startup.
        cli_tool_path = str(AUTORESEARCH_DIR / "cli" / "genesis_dds_tool.py")
        template_path = AUTORESEARCH_DIR / "cli" / "workspace_claude_md.txt"
        with open(template_path) as f:
            template = f.read()
        rendered = template.replace("{GENESIS_DDS_TOOL_PATH}", cli_tool_path)

        task_template_dir = bench_path / "templates" / "harness-bench-tasks" / "tasks" / "L2-dds" / task_id
        injected_claude_md = task_template_dir / "CLAUDE.md"
        with open(injected_claude_md, "w") as f:
            f.write(rendered)

        env["GENESIS_DDS_TOOL_PATH"] = cli_tool_path
        env["GENESIS_LIB_PATH"] = str(GENESIS_DIR)

    print(f"  Running {task_id} ({'with Genesis' if with_genesis else 'control'})...")
    start_time = time.time()

    # Start babysitter thread to handle interactive prompts in tmux
    stop_babysit = threading.Event()
    babysitter = threading.Thread(target=_babysit_tmux, args=(stop_babysit, 10),
                                 daemon=True)
    babysitter.start()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True,
            timeout=config["timeout_s"] + 120,  # extra buffer
            cwd=str(bench_path),
            env=env,
        )
        elapsed = time.time() - start_time

        # Parse result from harness-bench output
        # Look for the results JSON file (harness filenames don't include task_id,
        # so find the most recent dds_benchmark_*.json modified after start_time)
        results_dir = bench_path / "results"
        latest_results = sorted(
            [f for f in results_dir.glob("dds_benchmark_*.json")
             if os.path.getmtime(f) >= start_time],
            key=os.path.getmtime, reverse=True
        )

        if latest_results:
            with open(latest_results[0]) as f:
                bench_result = json.load(f)
            return {
                "task": task_id,
                "with_genesis": with_genesis,
                "success": bench_result.get("passed", 0) > 0,
                "elapsed": elapsed,
                "result_file": str(latest_results[0]),
                "details": bench_result,
                "stdout": result.stdout[-2000:] if result.stdout else "",
                "stderr": result.stderr[-2000:] if result.stderr else "",
            }
        else:
            return {
                "task": task_id,
                "with_genesis": with_genesis,
                "success": False,
                "elapsed": elapsed,
                "error": "No result file found",
                "stdout": result.stdout[-2000:] if result.stdout else "",
                "stderr": result.stderr[-2000:] if result.stderr else "",
            }
    except subprocess.TimeoutExpired:
        return {
            "task": task_id,
            "with_genesis": with_genesis,
            "success": False,
            "elapsed": config["timeout_s"] + 120,
            "error": "Timeout expired",
        }
    except Exception as e:
        return {
            "task": task_id,
            "with_genesis": with_genesis,
            "success": False,
            "elapsed": time.time() - start_time,
            "error": str(e),
        }
    finally:
        stop_babysit.set()
        # Clean up injected CLAUDE.md from task template to avoid polluting control runs
        if injected_claude_md and injected_claude_md.exists():
            injected_claude_md.unlink()


def run_iteration(config, iteration_num, treatment_only=False):
    """Run a complete iteration (control + treatment or treatment only)."""
    results = {"iteration": iteration_num, "timestamp": datetime.now().isoformat(),
               "control": [], "treatment": []}

    tasks = config["target_tasks"]

    # Control runs (skip if treatment_only)
    if not treatment_only:
        print("\n=== CONTROL RUNS (no Genesis tools) ===")
        for task in tasks:
            result = run_task(config, task, with_genesis=False)
            results["control"].append(result)
            print(f"  {task}: {'PASS' if result['success'] else 'FAIL'}")

    # Start Genesis services for treatment
    print("\n=== TREATMENT RUNS (with Genesis tools) ===")
    start_services()

    if not verify_services():
        print("WARNING: Genesis services not verified. Proceeding anyway...")

    for task in tasks:
        result = run_task(config, task, with_genesis=True)
        results["treatment"].append(result)
        print(f"  {task}: {'PASS' if result['success'] else 'FAIL'}")

    stop_services()

    # Save results (model-specific directory for non-opus models)
    model = config.get("model", "opus")
    if model != "opus":
        results_dir = AUTORESEARCH_DIR / "results" / f"{model}_iteration_{iteration_num:03d}"
    else:
        results_dir = AUTORESEARCH_DIR / "results" / f"iteration_{iteration_num:03d}"
    results_dir.mkdir(parents=True, exist_ok=True)

    with open(results_dir / "results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nResults saved to {results_dir}")
    return results


def main():
    parser = argparse.ArgumentParser(description="AutoResearch Benchmark Runner")
    parser.add_argument("--iteration", "-i", type=int, default=0, help="Iteration number")
    parser.add_argument("--treatment-only", action="store_true",
                        help="Skip control runs (use existing baseline)")
    parser.add_argument("--baseline", action="store_true",
                        help="Run baseline only (no treatment)")
    parser.add_argument("--config", type=str, default=None,
                        help="Path to config file (default: config.json)")
    args = parser.parse_args()

    config = load_config(args.config)
    print(f"AutoResearch Iteration {args.iteration}")
    print(f"Tasks: {config['target_tasks']}")
    print(f"Model: {config['model']}")

    if args.baseline:
        print("\n=== BASELINE RUNS ===")
        results = {"iteration": 0, "timestamp": datetime.now().isoformat(), "baseline": []}
        for task in config["target_tasks"]:
            for run in range(3):  # 3 runs for baseline
                result = run_task(config, task, with_genesis=False)
                results["baseline"].append(result)
                print(f"  {task} run {run+1}: {'PASS' if result['success'] else 'FAIL'}")

        model = config.get("model", "opus")
        baseline_dir = AUTORESEARCH_DIR / "results" / (f"{model}_baseline" if model != "opus" else "baseline")
        baseline_dir.mkdir(parents=True, exist_ok=True)
        with open(baseline_dir / "baseline_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nBaseline saved to {baseline_dir}")
    else:
        run_iteration(config, args.iteration, treatment_only=args.treatment_only)


if __name__ == "__main__":
    main()
