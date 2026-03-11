#!/usr/bin/env python3
"""
AutoResearch Evaluator - Language-based evaluation of iteration results.

Computes quantitative metrics and produces qualitative evaluation.
Like Karpathy evaluates val_bpb, we evaluate pass rate + tool usage.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

AUTORESEARCH_DIR = Path(__file__).parent.parent


def load_baseline():
    """Load baseline results."""
    baseline_path = AUTORESEARCH_DIR / "results" / "baseline" / "baseline_results.json"
    if baseline_path.exists():
        with open(baseline_path) as f:
            return json.load(f)
    return None


def load_iteration(iteration_num):
    """Load iteration results."""
    results_path = AUTORESEARCH_DIR / "results" / f"iteration_{iteration_num:03d}" / "results.json"
    if results_path.exists():
        with open(results_path) as f:
            return json.load(f)
    return None


def compute_pass_rates(results_list):
    """Compute per-task pass rates from a list of results."""
    rates = {}
    for r in results_list:
        task = r["task"]
        # Extract just the task prefix (LR-01, LD-07, LQ-01)
        task_short = task.split("_")[0]
        if task_short not in rates:
            rates[task_short] = {"passed": 0, "total": 0}
        rates[task_short]["total"] += 1
        if r.get("success"):
            rates[task_short]["passed"] += 1

    for task in rates:
        rates[task]["rate"] = rates[task]["passed"] / max(rates[task]["total"], 1)
    return rates


def evaluate_iteration(iteration_num):
    """Evaluate a single iteration against baseline."""
    baseline = load_baseline()
    iteration = load_iteration(iteration_num)

    if not iteration:
        print(f"No results found for iteration {iteration_num}")
        return None

    # Compute metrics
    treatment_rates = compute_pass_rates(iteration.get("treatment", []))

    baseline_rates = {}
    if baseline:
        baseline_rates = compute_pass_rates(baseline.get("baseline", []))

    # Overall pass rate
    treatment_total = sum(r.get("passed", 0) for r in treatment_rates.values())
    treatment_count = sum(r.get("total", 0) for r in treatment_rates.values())
    treatment_overall = treatment_total / max(treatment_count, 1)

    baseline_total = sum(r.get("passed", 0) for r in baseline_rates.values())
    baseline_count = sum(r.get("total", 0) for r in baseline_rates.values())
    baseline_overall = baseline_total / max(baseline_count, 1)

    evaluation = {
        "iteration": iteration_num,
        "timestamp": datetime.now().isoformat(),
        "quantitative": {
            "treatment_pass_rates": {k: v["rate"] for k, v in treatment_rates.items()},
            "baseline_pass_rates": {k: v["rate"] for k, v in baseline_rates.items()},
            "treatment_overall": treatment_overall,
            "baseline_overall": baseline_overall,
            "delta": treatment_overall - baseline_overall,
        },
        "per_task_detail": {},
    }

    for task in treatment_rates:
        t_rate = treatment_rates[task]["rate"]
        b_rate = baseline_rates.get(task, {}).get("rate", 0)
        evaluation["per_task_detail"][task] = {
            "treatment": t_rate,
            "baseline": b_rate,
            "delta": t_rate - b_rate,
            "improved": t_rate > b_rate,
        }

    # Save evaluation
    eval_dir = AUTORESEARCH_DIR / "results" / f"iteration_{iteration_num:03d}"
    eval_dir.mkdir(parents=True, exist_ok=True)
    with open(eval_dir / "evaluation.json", "w") as f:
        json.dump(evaluation, f, indent=2)

    # Update metrics history
    history_path = AUTORESEARCH_DIR / "results" / "metrics_history.json"
    with open(history_path) as f:
        history = json.load(f)

    history.append({
        "iteration": iteration_num,
        "timestamp": evaluation["timestamp"],
        "treatment_overall": treatment_overall,
        "baseline_overall": baseline_overall,
        "per_task": {k: v["rate"] for k, v in treatment_rates.items()},
        "delta": treatment_overall - baseline_overall,
    })

    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)

    # Print summary
    print(f"\n{'='*60}")
    print(f"ITERATION {iteration_num} EVALUATION")
    print(f"{'='*60}")
    print(f"Overall: treatment={treatment_overall:.0%} baseline={baseline_overall:.0%} delta={treatment_overall - baseline_overall:+.0%}")
    print()
    for task, detail in evaluation["per_task_detail"].items():
        arrow = "^" if detail["improved"] else ("=" if detail["delta"] == 0 else "v")
        print(f"  {task}: treatment={detail['treatment']:.0%} baseline={detail['baseline']:.0%} {arrow}")
    print(f"{'='*60}")

    return evaluation


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate AutoResearch iteration")
    parser.add_argument("--iteration", "-i", type=int, required=True)
    args = parser.parse_args()
    evaluate_iteration(args.iteration)


if __name__ == "__main__":
    main()
