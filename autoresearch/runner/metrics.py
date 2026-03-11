#!/usr/bin/env python3
"""
AutoResearch Metrics - Utility for metrics collection and reporting.
"""
import json
from pathlib import Path

AUTORESEARCH_DIR = Path(__file__).parent.parent


def get_metrics_history():
    """Load full metrics history."""
    path = AUTORESEARCH_DIR / "results" / "metrics_history.json"
    with open(path) as f:
        return json.load(f)


def print_summary():
    """Print a summary of all iterations."""
    history = get_metrics_history()
    if not history:
        print("No iterations recorded yet.")
        return

    print(f"\n{'Iter':>4} | {'Treatment':>10} | {'Baseline':>10} | {'Delta':>8} | {'Tasks'}")
    print("-" * 70)
    for h in history:
        tasks = " ".join(f"{k}:{v:.0%}" for k, v in h.get("per_task", {}).items())
        print(f"{h['iteration']:4d} | {h['treatment_overall']:10.0%} | {h['baseline_overall']:10.0%} | {h['delta']:+8.0%} | {tasks}")


if __name__ == "__main__":
    print_summary()
