#!/usr/bin/env python3
"""
Generate Haiku experiment improvement graph from iteration result files.
"""
import json
from pathlib import Path

AUTORESEARCH_DIR = Path(__file__).parent.parent
RESULTS_DIR = AUTORESEARCH_DIR / "results"


def load_iteration_results():
    """Load all Haiku iteration results."""
    iterations = []
    for d in sorted(RESULTS_DIR.glob("haiku_iteration_*")):
        results_file = d / "results.json"
        if results_file.exists():
            with open(results_file) as f:
                data = json.load(f)
            iter_num = data.get("iteration", int(d.name.split("_")[-1]))
            treatment = data.get("treatment", [])
            task_results = {}
            for t in treatment:
                task_results[t["task"]] = t["success"]
            iterations.append({
                "iteration": iter_num,
                "tasks": task_results,
                "overall": sum(task_results.values()) / len(task_results) if task_results else 0,
            })
    return iterations


def load_baseline():
    """Load Haiku baseline results."""
    baseline_file = RESULTS_DIR / "haiku_baseline" / "baseline_results.json"
    if not baseline_file.exists():
        return {}
    with open(baseline_file) as f:
        data = json.load(f)
    baseline_runs = data.get("baseline", [])
    # Group by task
    task_runs = {}
    for run in baseline_runs:
        task = run["task"]
        if task not in task_runs:
            task_runs[task] = []
        task_runs[task].append(run["success"])
    # Compute pass rates
    task_rates = {}
    for task, results in task_runs.items():
        task_rates[task] = sum(results) / len(results)
    return task_rates


def generate_graph():
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
    except ImportError:
        print("matplotlib not installed. Install with: pip install matplotlib")
        return

    iterations = load_iteration_results()
    baseline = load_baseline()

    if not iterations:
        print("No Haiku iteration results found.")
        return

    task_ids = sorted(set(t for it in iterations for t in it["tasks"]))
    task_labels = {
        "LR-01_dds_rpc_request_reply": "LR-01 (RPC Request/Reply)",
        "LD-07_discovery_guid_mining": "LD-07 (GUID Mining)",
        "LQ-01_late_joiner_durability": "LQ-01 (Late Joiner Durability)",
    }

    # Compute cumulative pass rates
    iter_nums = [it["iteration"] for it in iterations]
    cumulative_overall = []
    cumulative_per_task = {t: [] for t in task_ids}

    total_pass = 0
    total_runs = 0
    task_pass = {t: 0 for t in task_ids}
    task_runs = {t: 0 for t in task_ids}

    for it in iterations:
        for task in task_ids:
            if task in it["tasks"]:
                task_runs[task] += 1
                if it["tasks"][task]:
                    task_pass[task] += 1
                    total_pass += 1
                total_runs += 1
        cumulative_overall.append(total_pass / total_runs * 100 if total_runs else 0)
        for task in task_ids:
            rate = task_pass[task] / task_runs[task] * 100 if task_runs[task] else 0
            cumulative_per_task[task].append(rate)

    # Also compute per-iteration pass rate (rolling window of 5)
    window = 5
    rolling_overall = []
    for i in range(len(iterations)):
        start = max(0, i - window + 1)
        window_iters = iterations[start:i+1]
        passes = sum(sum(it["tasks"].values()) for it in window_iters)
        total = sum(len(it["tasks"]) for it in window_iters)
        rolling_overall.append(passes / total * 100 if total else 0)

    baseline_overall = sum(baseline.values()) / len(baseline) * 100 if baseline else 33.3

    # Create figure: 2x2 grid
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Top-left: Overall cumulative pass rate
    ax = axes[0, 0]
    ax.plot(iter_nums, cumulative_overall, 'b-o', linewidth=2, markersize=4, label='Cumulative pass rate')
    ax.plot(iter_nums, rolling_overall, 'g-', linewidth=1.5, alpha=0.7, label=f'Rolling {window}-iter rate')
    ax.axhline(y=baseline_overall, color='r', linestyle='--', linewidth=2, label=f'Baseline ({baseline_overall:.0f}%)')
    ax.set_ylabel('Pass Rate (%)')
    ax.set_title('Overall Pass Rate', fontsize=12, fontweight='bold')
    ax.legend(loc='lower right', fontsize=9)
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.3)

    # Top-right, Bottom-left, Bottom-right: Per-task
    positions = [(0, 1), (1, 0), (1, 1)]
    colors = ['#2196F3', '#FF9800', '#4CAF50']

    for idx, task in enumerate(task_ids):
        ax = axes[positions[idx]]
        label = task_labels.get(task, task)
        color = colors[idx]

        # Plot per-iteration result as dots
        for i, it in enumerate(iterations):
            if task in it["tasks"]:
                marker_color = color if it["tasks"][task] else 'red'
                marker = 'o' if it["tasks"][task] else 'x'
                ax.plot(it["iteration"], 100 if it["tasks"][task] else 0,
                       marker, color=marker_color, markersize=6, alpha=0.6)

        # Cumulative line
        ax.plot(iter_nums, cumulative_per_task[task], '-', color=color, linewidth=2)

        # Baseline
        bl = baseline.get(task, 0) * 100
        ax.axhline(y=bl, color='r', linestyle='--', linewidth=1.5,
                   label=f'Baseline ({bl:.0f}%)')

        ax.set_ylabel('Pass Rate (%)')
        ax.set_title(label, fontsize=11, fontweight='bold')
        ax.legend(loc='lower right', fontsize=9)
        ax.set_ylim(-5, 110)
        ax.grid(True, alpha=0.3)

    for ax in [axes[1, 0], axes[1, 1]]:
        ax.set_xlabel('Iteration')

    fig.suptitle('Genesis AutoResearch: Haiku Experiment (37 iterations)\n'
                 'Baseline 33% → With Genesis Tools 96%',
                 fontsize=14, fontweight='bold', y=1.02)

    plt.tight_layout()
    output_path = RESULTS_DIR / "haiku_improvement_graph.png"
    plt.savefig(str(output_path), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Graph saved to {output_path}")


if __name__ == "__main__":
    generate_graph()
