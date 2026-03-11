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
import time
from datetime import datetime
from pathlib import Path

AUTORESEARCH_DIR = Path(__file__).parent.parent
GENESIS_DIR = AUTORESEARCH_DIR.parent
CONFIG_PATH = AUTORESEARCH_DIR / "config.json"


def load_config():
    with open(CONFIG_PATH) as f:
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

    if with_genesis:
        # Inject Genesis tools via custom append prompt
        cli_tool_path = str(AUTORESEARCH_DIR / "cli" / "genesis_dds_tool.py")
        template_path = AUTORESEARCH_DIR / "cli" / "workspace_claude_md.txt"
        with open(template_path) as f:
            template = f.read()
        # The CLAUDE.md template has {GENESIS_DDS_TOOL_PATH} placeholder
        env["GENESIS_DDS_TOOL_PATH"] = cli_tool_path
        env["GENESIS_LIB_PATH"] = str(GENESIS_DIR)

    print(f"  Running {task_id} ({'with Genesis' if with_genesis else 'control'})...")
    start_time = time.time()

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
        # Look for the results JSON file
        results_dir = bench_path / "results"
        latest_results = sorted(results_dir.glob(f"dds_benchmark_*{task_id}*.json"),
                                key=os.path.getmtime, reverse=True)

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

    # Save results
    results_dir = AUTORESEARCH_DIR / "results" / f"iteration_{iteration_num:03d}"
    results_dir.mkdir(parents=True, exist_ok=True)

    with open(results_dir / "results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nResults saved to {results_dir}")
    return results


def main():
    parser = argparse.ArgumentParser(description="AutoResearch Benchmark Runner")
    parser.add_argument("--iteration", "-i", type=int, required=True, help="Iteration number")
    parser.add_argument("--treatment-only", action="store_true",
                        help="Skip control runs (use existing baseline)")
    parser.add_argument("--baseline", action="store_true",
                        help="Run baseline only (no treatment)")
    args = parser.parse_args()

    config = load_config()
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

        baseline_dir = AUTORESEARCH_DIR / "results" / "baseline"
        baseline_dir.mkdir(parents=True, exist_ok=True)
        with open(baseline_dir / "baseline_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nBaseline saved to {baseline_dir}")
    else:
        run_iteration(config, args.iteration, treatment_only=args.treatment_only)


if __name__ == "__main__":
    main()
