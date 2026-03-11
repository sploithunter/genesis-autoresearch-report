#!/usr/bin/env python3
"""Generate presentation-ready graphs for Genesis AutoResearch report."""

import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

# Style configuration
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 12,
    'axes.titlesize': 16,
    'axes.labelsize': 14,
    'xtick.labelsize': 11,
    'ytick.labelsize': 11,
    'legend.fontsize': 11,
    'figure.dpi': 150,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
})

COLORS = {
    'baseline': '#e74c3c',
    'treatment': '#2ecc71',
    'ld07': '#3498db',
    'lq01': '#e67e22',
    'lr01': '#9b59b6',
    'bg': '#fafafa',
    'grid': '#ecf0f1',
    'accent': '#2c3e50',
}

def load_data():
    with open('data/iteration_results.json') as f:
        return json.load(f)

def load_haiku_data():
    with open('data/haiku_iteration_results.json') as f:
        return json.load(f)

def fig1_overall_pass_rate(data, outdir):
    """Main hero graph: overall pass rate over iterations."""
    iters = []
    pass_rates = []

    # Calculate rolling pass rate (cumulative from iter 7 onward)
    for d in data['iterations']:
        i = d['iter']
        iters.append(i)

        # Count passes up to this iteration
        total = 0
        passed = 0
        for prev in data['iterations'][:data['iterations'].index(d)+1]:
            for task in ['LD-07', 'LQ-01']:
                if task in prev:
                    total += 1
                    if prev[task]:
                        passed += 1
            if 'LR-01' in prev:
                total += 1
                if prev['LR-01']:
                    passed += 1
        pass_rates.append(passed / total * 100 if total > 0 else 0)

    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor('white')
    ax.set_facecolor(COLORS['bg'])

    # Baseline line
    ax.axhline(y=33.3, color=COLORS['baseline'], linestyle='--', linewidth=2, alpha=0.8, label='Baseline (33%)')

    # Treatment line
    ax.plot(iters, pass_rates, color=COLORS['treatment'], linewidth=2.5, marker='o', markersize=4, label='With Genesis Tools')

    # Fill between
    ax.fill_between(iters, 33.3, pass_rates, alpha=0.15, color=COLORS['treatment'])

    # Annotations
    ax.annotate('StructType\nBreakthrough', xy=(5, pass_rates[4]), xytext=(8, 55),
                arrowprops=dict(arrowstyle='->', color=COLORS['accent'], lw=1.5),
                fontsize=10, ha='center', color=COLORS['accent'], fontweight='bold')

    ax.annotate('32 consecutive\nperfect runs', xy=(38, pass_rates[-1]), xytext=(32, 75),
                arrowprops=dict(arrowstyle='->', color=COLORS['accent'], lw=1.5),
                fontsize=10, ha='center', color=COLORS['accent'], fontweight='bold')

    # Shaded regions for phases
    ax.axvspan(1, 7, alpha=0.05, color='blue', label='Tool Development (iter 1-7)')
    ax.axvspan(7, 38, alpha=0.03, color='green')

    ax.set_xlabel('Iteration')
    ax.set_ylabel('Cumulative Pass Rate (%)')
    ax.set_title('Genesis AutoResearch: Overall Pass Rate Over 38 Iterations')
    ax.set_ylim(0, 105)
    ax.set_xlim(0.5, 38.5)
    ax.legend(loc='lower right', framealpha=0.9)
    ax.grid(True, alpha=0.3, color=COLORS['grid'])

    plt.savefig(outdir / 'fig1_overall_pass_rate.png')
    plt.close()

def fig2_per_task_pass_rate(data, outdir):
    """Per-task pass rate comparison: baseline vs final."""
    tasks = ['LR-01\n(RPC)', 'LD-07\n(GUID Mining)', 'LQ-01\n(Late Joiner)']
    baseline = [33.3, 0.0, 66.7]
    treatment = [100.0, 89.5, 97.4]

    x = np.arange(len(tasks))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor('white')
    ax.set_facecolor(COLORS['bg'])

    bars1 = ax.bar(x - width/2, baseline, width, label='Baseline (No Tools)',
                   color=COLORS['baseline'], alpha=0.85, edgecolor='white', linewidth=1.5)
    bars2 = ax.bar(x + width/2, treatment, width, label='With Genesis Tools',
                   color=COLORS['treatment'], alpha=0.85, edgecolor='white', linewidth=1.5)

    # Value labels
    for bar, val in zip(bars1, baseline):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 2,
                f'{val:.0f}%', ha='center', va='bottom', fontweight='bold', color=COLORS['baseline'])
    for bar, val in zip(bars2, treatment):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 2,
                f'{val:.0f}%', ha='center', va='bottom', fontweight='bold', color='#27ae60')

    # Delta arrows
    for i, (b, t) in enumerate(zip(baseline, treatment)):
        delta = t - b
        ax.annotate(f'+{delta:.0f}pp', xy=(i, (b+t)/2), fontsize=11,
                   ha='center', color=COLORS['accent'], fontweight='bold')

    ax.set_ylabel('Pass Rate (%)')
    ax.set_title('Pass Rate by Task: Baseline vs Genesis Tools')
    ax.set_xticks(x)
    ax.set_xticklabels(tasks)
    ax.set_ylim(0, 115)
    ax.legend(loc='upper left', framealpha=0.9)
    ax.grid(True, axis='y', alpha=0.3, color=COLORS['grid'])

    plt.savefig(outdir / 'fig2_per_task_comparison.png')
    plt.close()

def fig3_per_task_timeline(data, outdir):
    """Per-task pass/fail timeline showing the progression."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    fig.patch.set_facecolor('white')

    for ax, task, title, color in [
        (ax1, 'LD-07', 'LD-07: Discovery GUID Mining (Baseline: 0%)', COLORS['ld07']),
        (ax2, 'LQ-01', 'LQ-01: Late Joiner Durability (Baseline: 67%)', COLORS['lq01']),
    ]:
        ax.set_facecolor(COLORS['bg'])
        iters = []
        results = []
        for d in data['iterations']:
            if task in d:
                iters.append(d['iter'])
                results.append(1 if d[task] else 0)

        colors_list = [COLORS['treatment'] if r else COLORS['baseline'] for r in results]
        ax.bar(iters, [1]*len(iters), color=colors_list, alpha=0.8, edgecolor='white', linewidth=0.5)

        ax.set_title(title, fontweight='bold')
        ax.set_ylabel('Result')
        ax.set_yticks([0, 1])
        ax.set_yticklabels(['FAIL', 'PASS'])
        ax.set_ylim(-0.1, 1.3)
        ax.grid(True, axis='x', alpha=0.3)

        # Count consecutive passes from end
        consecutive = 0
        for r in reversed(results):
            if r == 1:
                consecutive += 1
            else:
                break
        ax.text(0.98, 0.85, f'{consecutive} consecutive passes',
               transform=ax.transAxes, ha='right', fontsize=12,
               fontweight='bold', color=COLORS['treatment'],
               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

    ax2.set_xlabel('Iteration')
    fig.suptitle('Per-Task Results Over Time', fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(outdir / 'fig3_per_task_timeline.png')
    plt.close()

def fig4_cost_and_time(data, outdir):
    """Cost and time comparison."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor('white')

    # Cost comparison
    ax1.set_facecolor(COLORS['bg'])
    ld07_costs = [d['ld07_cost'] for d in data['iterations'] if 'ld07_cost' in d]
    lq01_costs = [d['lq01_cost'] for d in data['iterations'] if 'lq01_cost' in d]

    baseline_cost = 0.17
    treatment_avg = np.mean(ld07_costs[-20:] + lq01_costs[-20:])

    bars = ax1.bar(['Baseline\n(No Tools)', 'Genesis Tools\n(Last 20 iters)'],
                  [baseline_cost, treatment_avg],
                  color=[COLORS['baseline'], COLORS['treatment']], alpha=0.85,
                  edgecolor='white', linewidth=2, width=0.5)

    for bar, val in zip(bars, [baseline_cost, treatment_avg]):
        ax1.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.003,
                f'${val:.3f}', ha='center', va='bottom', fontweight='bold', fontsize=13)

    savings_pct = (1 - treatment_avg/baseline_cost) * 100
    ax1.text(0.5, 0.5, f'{savings_pct:.0f}% cheaper',
            transform=ax1.transAxes, ha='center', fontsize=14,
            fontweight='bold', color=COLORS['accent'])

    ax1.set_ylabel('Cost per Task (USD)')
    ax1.set_title('Cost per Task')
    ax1.grid(True, axis='y', alpha=0.3)

    # Time comparison
    ax2.set_facecolor(COLORS['bg'])
    ld07_times = [d['ld07_time'] for d in data['iterations'] if 'ld07_time' in d and d.get('LD-07', False)]
    lq01_times = [d['lq01_time'] for d in data['iterations'] if 'lq01_time' in d and d.get('LQ-01', False)]

    baseline_time = 310
    treatment_time = np.mean(ld07_times[-20:] + lq01_times[-20:])

    bars = ax2.bar(['Baseline\n(No Tools)', 'Genesis Tools\n(Last 20 iters)'],
                  [baseline_time, treatment_time],
                  color=[COLORS['baseline'], COLORS['treatment']], alpha=0.85,
                  edgecolor='white', linewidth=2, width=0.5)

    for bar, val in zip(bars, [baseline_time, treatment_time]):
        ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 5,
                f'{val:.0f}s', ha='center', va='bottom', fontweight='bold', fontsize=13)

    speedup = baseline_time / treatment_time
    ax2.text(0.5, 0.5, f'{speedup:.1f}x faster',
            transform=ax2.transAxes, ha='center', fontsize=14,
            fontweight='bold', color=COLORS['accent'])

    ax2.set_ylabel('Time per Task (seconds)')
    ax2.set_title('Time per Task')
    ax2.grid(True, axis='y', alpha=0.3)

    fig.suptitle('Efficiency Gains with Genesis Tools', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(outdir / 'fig4_cost_and_time.png')
    plt.close()

def fig5_architecture(outdir):
    """Architecture diagram showing the teacher-student-tools setup."""
    fig, ax = plt.subplots(figsize=(14, 8))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.axis('off')

    # Title
    ax.text(5, 7.5, 'Genesis AutoResearch Architecture', ha='center', fontsize=18, fontweight='bold')

    # Teacher Agent box
    rect = mpatches.FancyBboxPatch((0.5, 5.5), 3, 1.5, boxstyle="round,pad=0.2",
                                    facecolor='#3498db', alpha=0.2, edgecolor='#2980b9', linewidth=2)
    ax.add_patch(rect)
    ax.text(2, 6.5, 'Teacher Agent', ha='center', fontsize=14, fontweight='bold', color='#2c3e50')
    ax.text(2, 6.0, '(Claude Opus 4.6)', ha='center', fontsize=10, color='#7f8c8d')

    # Student Agent box
    rect = mpatches.FancyBboxPatch((6.5, 5.5), 3, 1.5, boxstyle="round,pad=0.2",
                                    facecolor='#e67e22', alpha=0.2, edgecolor='#d35400', linewidth=2)
    ax.add_patch(rect)
    ax.text(8, 6.5, 'Student Agent', ha='center', fontsize=14, fontweight='bold', color='#2c3e50')
    ax.text(8, 6.0, '(Claude Code + DDS Task)', ha='center', fontsize=10, color='#7f8c8d')

    # Genesis Services box
    rect = mpatches.FancyBboxPatch((3, 2.5), 4, 2.2, boxstyle="round,pad=0.2",
                                    facecolor='#2ecc71', alpha=0.2, edgecolor='#27ae60', linewidth=2)
    ax.add_patch(rect)
    ax.text(5, 4.2, 'Genesis DDS Tool Services', ha='center', fontsize=14, fontweight='bold', color='#2c3e50')
    ax.text(5, 3.7, 'DDSPatternService', ha='center', fontsize=10, color='#27ae60')
    ax.text(5, 3.3, 'DDSReferenceService', ha='center', fontsize=10, color='#27ae60')
    ax.text(5, 2.9, 'DDSDiagnosticService', ha='center', fontsize=10, color='#27ae60')

    # CLAUDE.md injection
    rect = mpatches.FancyBboxPatch((6.5, 1), 3, 1, boxstyle="round,pad=0.2",
                                    facecolor='#9b59b6', alpha=0.2, edgecolor='#8e44ad', linewidth=2)
    ax.add_patch(rect)
    ax.text(8, 1.5, 'CLAUDE.md Injection', ha='center', fontsize=12, fontweight='bold', color='#2c3e50')

    # harness-bench box
    rect = mpatches.FancyBboxPatch((0.5, 1), 2.5, 1, boxstyle="round,pad=0.2",
                                    facecolor='#ecf0f1', alpha=0.5, edgecolor='#bdc3c7', linewidth=2)
    ax.add_patch(rect)
    ax.text(1.75, 1.5, 'harness-bench', ha='center', fontsize=12, fontweight='bold', color='#2c3e50')

    # Arrows
    ax.annotate('', xy=(6.3, 6.25), xytext=(3.7, 6.25),
                arrowprops=dict(arrowstyle='->', lw=2, color='#2c3e50'))
    ax.text(5, 6.5, 'launches task', ha='center', fontsize=9, color='#7f8c8d')

    ax.annotate('', xy=(7, 5.3), xytext=(5.5, 4.8),
                arrowprops=dict(arrowstyle='->', lw=2, color='#27ae60'))
    ax.text(6.6, 5.2, 'DDS domain 55', ha='center', fontsize=9, color='#27ae60')

    ax.annotate('', xy=(8, 5.3), xytext=(8, 2.2),
                arrowprops=dict(arrowstyle='->', lw=2, color='#8e44ad'))
    ax.text(8.8, 3.8, 'reads tools', ha='center', fontsize=9, color='#8e44ad', rotation=90)

    ax.annotate('', xy=(1.75, 5.3), xytext=(1.75, 2.2),
                arrowprops=dict(arrowstyle='->', lw=2, color='#7f8c8d'))
    ax.text(1.0, 3.8, 'evaluates', ha='center', fontsize=9, color='#7f8c8d', rotation=90)

    plt.savefig(outdir / 'fig5_architecture.png')
    plt.close()

def fig6_ld07_deep_dive(data, outdir):
    """LD-07 deep dive: the hardest task going from 0% to 100%."""
    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor('white')
    ax.set_facecolor(COLORS['bg'])

    iters = []
    times = []
    success = []

    for d in data['iterations']:
        if 'LD-07' in d:
            iters.append(d['iter'])
            times.append(d['ld07_time'])
            success.append(d['LD-07'])

    colors_list = [COLORS['treatment'] if s else COLORS['baseline'] for s in success]
    ax.bar(iters, times, color=colors_list, alpha=0.8, edgecolor='white', linewidth=0.5)

    # Timeout line
    ax.axhline(y=300, color='red', linestyle=':', linewidth=1.5, alpha=0.5, label='Timeout (300s)')

    # Phase labels
    ax.axvspan(1, 4, alpha=0.08, color='red')
    ax.axvspan(5, 7, alpha=0.08, color='orange')
    ax.axvspan(7, 38, alpha=0.05, color='green')

    ax.text(2.5, 340, 'Failing\n(0% baseline)', ha='center', fontsize=9, color=COLORS['baseline'])
    ax.text(6, 340, 'Breakthrough', ha='center', fontsize=9, color='orange')
    ax.text(22, 340, '32 consecutive passes', ha='center', fontsize=9, color=COLORS['treatment'])

    pass_patch = mpatches.Patch(color=COLORS['treatment'], alpha=0.8, label='PASS')
    fail_patch = mpatches.Patch(color=COLORS['baseline'], alpha=0.8, label='FAIL')
    ax.legend(handles=[pass_patch, fail_patch], loc='upper right')

    ax.set_xlabel('Iteration')
    ax.set_ylabel('Time (seconds)')
    ax.set_title('LD-07 Discovery GUID Mining: From 0% to 100%\nThe hardest task — solved by StructType + DynamicData patterns')
    ax.set_ylim(0, 380)
    ax.grid(True, axis='y', alpha=0.3)

    plt.savefig(outdir / 'fig6_ld07_deep_dive.png')
    plt.close()

def fig7_haiku_overall_pass_rate(haiku_data, outdir):
    """Haiku overall cumulative pass rate over 37 iterations."""
    iters = []
    pass_rates = []

    for d in haiku_data['iterations']:
        iters.append(d['iter'])
        total = 0
        passed = 0
        for prev in haiku_data['iterations'][:haiku_data['iterations'].index(d)+1]:
            for task in ['LR-01', 'LD-07', 'LQ-01']:
                if task in prev:
                    total += 1
                    if prev[task]:
                        passed += 1
        pass_rates.append(passed / total * 100 if total > 0 else 0)

    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor('white')
    ax.set_facecolor(COLORS['bg'])

    # Baseline line (Haiku baseline: 0% — all 3 LR-01 runs failed)
    ax.axhline(y=0, color=COLORS['baseline'], linestyle='--', linewidth=2, alpha=0.8, label='Haiku Baseline (0%)')

    # Treatment line
    ax.plot(iters, pass_rates, color='#3498db', linewidth=2.5, marker='o', markersize=4, label='Haiku + Genesis Tools')

    # Fill between
    ax.fill_between(iters, 0, pass_rates, alpha=0.15, color='#3498db')

    # Annotations
    ax.annotate('LR-01 added\n(iter 7)', xy=(7, pass_rates[6]), xytext=(12, 75),
                arrowprops=dict(arrowstyle='->', color=COLORS['accent'], lw=1.5),
                fontsize=10, ha='center', color=COLORS['accent'], fontweight='bold')

    ax.annotate(f'Final: {pass_rates[-1]:.0f}%', xy=(37, pass_rates[-1]), xytext=(32, 80),
                arrowprops=dict(arrowstyle='->', color=COLORS['accent'], lw=1.5),
                fontsize=10, ha='center', color=COLORS['accent'], fontweight='bold')

    ax.set_xlabel('Iteration')
    ax.set_ylabel('Cumulative Pass Rate (%)')
    ax.set_title('Haiku Phase: Overall Pass Rate Over 37 Iterations\nSmallest Claude model + same Genesis tools')
    ax.set_ylim(0, 105)
    ax.set_xlim(0.5, 37.5)
    ax.legend(loc='lower right', framealpha=0.9)
    ax.grid(True, alpha=0.3, color=COLORS['grid'])

    plt.savefig(outdir / 'fig7_haiku_overall_pass_rate.png')
    plt.close()


def fig8_cross_model_comparison(opus_data, haiku_data, outdir):
    """Side-by-side Opus vs Haiku comparison — the money graph."""
    tasks = ['LR-01\n(RPC)', 'LD-07\n(GUID Mining)', 'LQ-01\n(Late Joiner)', 'Overall']

    # Compute Opus stats
    opus_lr01 = [d.get('LR-01') for d in opus_data['iterations'] if 'LR-01' in d]
    opus_ld07 = [d.get('LD-07') for d in opus_data['iterations'] if 'LD-07' in d]
    opus_lq01 = [d.get('LQ-01') for d in opus_data['iterations'] if 'LQ-01' in d]
    opus_rates = [
        sum(opus_lr01) / len(opus_lr01) * 100 if opus_lr01 else 100,
        sum(opus_ld07) / len(opus_ld07) * 100,
        sum(opus_lq01) / len(opus_lq01) * 100,
        0  # placeholder
    ]
    opus_total = sum(opus_lr01) + sum(opus_ld07) + sum(opus_lq01)
    opus_count = len(opus_lr01) + len(opus_ld07) + len(opus_lq01)
    opus_rates[3] = opus_total / opus_count * 100

    # Compute Haiku stats
    haiku_lr01 = [d.get('LR-01') for d in haiku_data['iterations'] if 'LR-01' in d]
    haiku_ld07 = [d.get('LD-07') for d in haiku_data['iterations'] if 'LD-07' in d]
    haiku_lq01 = [d.get('LQ-01') for d in haiku_data['iterations'] if 'LQ-01' in d]
    haiku_rates = [
        sum(haiku_lr01) / len(haiku_lr01) * 100 if haiku_lr01 else 0,
        sum(haiku_ld07) / len(haiku_ld07) * 100,
        sum(haiku_lq01) / len(haiku_lq01) * 100,
        0
    ]
    haiku_total = sum(haiku_lr01) + sum(haiku_ld07) + sum(haiku_lq01)
    haiku_count = len(haiku_lr01) + len(haiku_ld07) + len(haiku_lq01)
    haiku_rates[3] = haiku_total / haiku_count * 100

    # Baseline (combined)
    baseline_rates = [33.3, 0.0, 66.7, 33.3]

    x = np.arange(len(tasks))
    width = 0.25

    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor('white')
    ax.set_facecolor(COLORS['bg'])

    bars1 = ax.bar(x - width, baseline_rates, width, label='Baseline (No Tools)',
                   color=COLORS['baseline'], alpha=0.85, edgecolor='white', linewidth=1.5)
    bars2 = ax.bar(x, opus_rates, width, label='Opus + Genesis Tools',
                   color=COLORS['treatment'], alpha=0.85, edgecolor='white', linewidth=1.5)
    bars3 = ax.bar(x + width, haiku_rates, width, label='Haiku + Genesis Tools',
                   color='#3498db', alpha=0.85, edgecolor='white', linewidth=1.5)

    # Value labels
    for bars, vals, color in [(bars1, baseline_rates, COLORS['baseline']),
                               (bars2, opus_rates, '#27ae60'),
                               (bars3, haiku_rates, '#2980b9')]:
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1.5,
                    f'{val:.0f}%', ha='center', va='bottom', fontweight='bold',
                    fontsize=9, color=color)

    ax.set_ylabel('Pass Rate (%)')
    ax.set_title('Cross-Model Validation: Same Tools, Different Models\nGenesis tools encode genuinely useful knowledge', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(tasks)
    ax.set_ylim(0, 118)
    ax.legend(loc='upper left', framealpha=0.9)
    ax.grid(True, axis='y', alpha=0.3, color=COLORS['grid'])

    plt.savefig(outdir / 'fig8_cross_model_comparison.png')
    plt.close()


def fig9_haiku_per_task_timeline(haiku_data, outdir):
    """Haiku per-task pass/fail timeline — all 3 tasks."""
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    fig.patch.set_facecolor('white')

    for ax, task, title, color in [
        (ax1, 'LR-01', 'LR-01: DDS RPC Request/Reply (Haiku Baseline: 0%)', COLORS['lr01']),
        (ax2, 'LD-07', 'LD-07: Discovery GUID Mining (Haiku Baseline: N/A)', COLORS['ld07']),
        (ax3, 'LQ-01', 'LQ-01: Late Joiner Durability (Haiku Baseline: N/A)', COLORS['lq01']),
    ]:
        ax.set_facecolor(COLORS['bg'])
        iters = []
        results = []
        for d in haiku_data['iterations']:
            if task in d:
                iters.append(d['iter'])
                results.append(1 if d[task] else 0)

        if not iters:
            ax.text(0.5, 0.5, 'No data', transform=ax.transAxes, ha='center')
            ax.set_title(title, fontweight='bold')
            continue

        colors_list = [COLORS['treatment'] if r else COLORS['baseline'] for r in results]
        ax.bar(iters, [1]*len(iters), color=colors_list, alpha=0.8, edgecolor='white', linewidth=0.5)

        ax.set_title(title, fontweight='bold')
        ax.set_ylabel('Result')
        ax.set_yticks([0, 1])
        ax.set_yticklabels(['FAIL', 'PASS'])
        ax.set_ylim(-0.1, 1.3)
        ax.grid(True, axis='x', alpha=0.3)

        # Stats
        pass_count = sum(results)
        total = len(results)
        consecutive = 0
        for r in reversed(results):
            if r == 1:
                consecutive += 1
            else:
                break
        ax.text(0.98, 0.85, f'{pass_count}/{total} passed ({pass_count/total*100:.0f}%)',
               transform=ax.transAxes, ha='right', fontsize=11,
               fontweight='bold', color=COLORS['treatment'],
               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

    ax3.set_xlabel('Iteration')
    fig.suptitle('Haiku Phase: Per-Task Results Over 37 Iterations', fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(outdir / 'fig9_haiku_per_task_timeline.png')
    plt.close()


def fig10_cost_comparison(opus_data, haiku_data, outdir):
    """Opus vs Haiku cost comparison."""
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor('white')
    ax.set_facecolor(COLORS['bg'])

    # Compute average costs
    opus_costs = []
    for d in opus_data['iterations'][-20:]:
        for key in ['ld07_cost', 'lq01_cost', 'lr01_cost']:
            if key in d:
                opus_costs.append(d[key])
    haiku_costs = []
    for d in haiku_data['iterations'][-20:]:
        for key in ['ld07_cost', 'lq01_cost', 'lr01_cost']:
            if key in d:
                haiku_costs.append(d[key])

    categories = ['Baseline\n(Opus, No Tools)', 'Opus\n+ Genesis Tools', 'Haiku\n+ Genesis Tools']
    costs = [0.17, np.mean(opus_costs), np.mean(haiku_costs)]
    bar_colors = [COLORS['baseline'], COLORS['treatment'], '#3498db']

    bars = ax.bar(categories, costs, color=bar_colors, alpha=0.85, edgecolor='white', linewidth=2, width=0.5)

    for bar, val in zip(bars, costs):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.002,
                f'${val:.4f}', ha='center', va='bottom', fontweight='bold', fontsize=13)

    # Multiplier annotations
    ratio = costs[0] / costs[2]
    ax.annotate(f'{ratio:.0f}x cheaper', xy=(2, costs[2]), xytext=(2, costs[0]*0.6),
                fontsize=13, ha='center', fontweight='bold', color=COLORS['accent'],
                arrowprops=dict(arrowstyle='->', color=COLORS['accent'], lw=1.5))

    ax.set_ylabel('Average Cost per Task (USD)')
    ax.set_title('Cost per Task: Baseline vs Opus vs Haiku\nSame tools, 10x cost reduction with Haiku', fontweight='bold')
    ax.grid(True, axis='y', alpha=0.3)

    plt.savefig(outdir / 'fig10_cost_comparison.png')
    plt.close()


def main():
    data = load_data()
    haiku_data = load_haiku_data()
    outdir = Path('graphs')
    outdir.mkdir(exist_ok=True)

    print("Generating Opus graphs...")
    fig1_overall_pass_rate(data, outdir)
    print("  fig1_overall_pass_rate.png")
    fig2_per_task_pass_rate(data, outdir)
    print("  fig2_per_task_comparison.png")
    fig3_per_task_timeline(data, outdir)
    print("  fig3_per_task_timeline.png")
    fig4_cost_and_time(data, outdir)
    print("  fig4_cost_and_time.png")
    fig5_architecture(outdir)
    print("  fig5_architecture.png")
    fig6_ld07_deep_dive(data, outdir)
    print("  fig6_ld07_deep_dive.png")

    print("\nGenerating Haiku graphs...")
    fig7_haiku_overall_pass_rate(haiku_data, outdir)
    print("  fig7_haiku_overall_pass_rate.png")
    fig8_cross_model_comparison(data, haiku_data, outdir)
    print("  fig8_cross_model_comparison.png")
    fig9_haiku_per_task_timeline(haiku_data, outdir)
    print("  fig9_haiku_per_task_timeline.png")
    fig10_cost_comparison(data, haiku_data, outdir)
    print("  fig10_cost_comparison.png")
    print("\nDone! All graphs saved to graphs/")

if __name__ == '__main__':
    main()
