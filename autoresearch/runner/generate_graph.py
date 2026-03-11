#!/usr/bin/env python3
"""
AutoResearch Graph Generator

Generates improvement graphs from metrics_history.json.
Presentation-ready output.
"""
import json
import sys
from pathlib import Path

AUTORESEARCH_DIR = Path(__file__).parent.parent


def generate_graph():
    """Generate improvement graph from metrics history."""
    try:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed. Install with: pip install matplotlib")
        return

    history_path = AUTORESEARCH_DIR / "results" / "metrics_history.json"
    with open(history_path) as f:
        history = json.load(f)

    if not history:
        print("No metrics history to plot.")
        return

    iterations = [h["iteration"] for h in history]
    treatment = [h["treatment_overall"] * 100 for h in history]
    baseline = [h["baseline_overall"] * 100 for h in history]

    # Collect per-task data
    task_ids = set()
    for h in history:
        task_ids.update(h.get("per_task", {}).keys())
    task_ids = sorted(task_ids)

    # Create figure
    n_subplots = 1 + len(task_ids)
    fig, axes = plt.subplots(n_subplots, 1, figsize=(10, 3 * n_subplots), sharex=True)
    if n_subplots == 1:
        axes = [axes]

    # Main plot: overall pass rate
    ax = axes[0]
    ax.plot(iterations, treatment, 'b-o', label='Treatment (Genesis tools)', linewidth=2, markersize=8)
    ax.axhline(y=baseline[0] if baseline else 0, color='r', linestyle='--', label='Baseline (no tools)', linewidth=1.5)
    ax.set_ylabel('Pass Rate (%)')
    ax.set_title('Genesis AutoResearch: Tool-Augmented DDS Benchmark Performance', fontsize=14, fontweight='bold')
    ax.legend(loc='lower right')
    ax.set_ylim(-5, 105)
    ax.grid(True, alpha=0.3)

    # Per-task subplots
    for i, task_id in enumerate(task_ids):
        ax = axes[i + 1]
        task_treatment = [h.get("per_task", {}).get(task_id, 0) * 100 for h in history]
        ax.plot(iterations, task_treatment, 'b-o', linewidth=1.5, markersize=6)

        # Baseline for this task
        task_baseline = history[0].get("per_task", {}).get(task_id, 0) * 100 if history else 0
        ax.axhline(y=task_baseline, color='r', linestyle='--', linewidth=1)

        ax.set_ylabel('Pass Rate (%)')
        ax.set_title(f'{task_id}', fontsize=11)
        ax.set_ylim(-5, 105)
        ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel('Iteration')

    plt.tight_layout()
    output_path = AUTORESEARCH_DIR / "results" / "improvement_graph.png"
    plt.savefig(str(output_path), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Graph saved to {output_path}")


if __name__ == "__main__":
    generate_graph()
