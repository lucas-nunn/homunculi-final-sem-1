'''
Lexical Decision Task - Analysis Script

Loads trial_responses.csv from every participant folder in the data
directory, applies the exclusion criteria from the experimental design,
computes per-condition descriptive statistics, and produces bar plots
for accuracy and reaction time.

Usage:
  python analysis.py
  python analysis.py --data_path ./data
'''

import argparse
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------------
# Command-line arguments
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description='Analyse lexical-decision data')
parser.add_argument('--data_path', type=str, default='./data',
                    help='Directory that contains subj_XX folders (default: ./data)')
args = parser.parse_args()


# ---------------------------------------------------------------------------
# 1. Load data from all participants
# ---------------------------------------------------------------------------
all_frames = []
for folder in sorted(os.listdir(args.data_path)):
    csv_path = os.path.join(args.data_path, folder, 'trial_responses.csv')
    if os.path.isfile(csv_path):
        df = pd.read_csv(csv_path)
        df['subject'] = folder  # e.g. "subj_01"
        all_frames.append(df)

if not all_frames:
    print(f'No trial_responses.csv files found in {args.data_path}/')
    exit(1)

data = pd.concat(all_frames, ignore_index=True)
print(f'Loaded {len(data)} trials from {data["subject"].nunique()} participant(s).\n')


# ---------------------------------------------------------------------------
# 2. Participant-level sanity checks
# ---------------------------------------------------------------------------
print('=' * 60)
print('PARTICIPANT SANITY CHECKS')
print('=' * 60)

for subj, sdf in data.groupby('subject'):
    n_total = len(sdf)
    n_missing = sdf['response'].isna().sum()
    n_answered = n_total - n_missing
    overall_acc = sdf['accuracy'].mean()
    exclusion_rate = n_missing / n_total

    flags = []
    if overall_acc < 0.60:
        flags.append(f'low accuracy ({overall_acc:.0%})')
    if exclusion_rate > 0.25:
        flags.append(f'high exclusion rate ({exclusion_rate:.0%})')

    status = ', '.join(flags) if flags else 'OK'
    print(f'  {subj}: accuracy={overall_acc:.1%}, '
          f'missing/timeout={n_missing}/{n_total} ({exclusion_rate:.0%})  [{status}]')

print()


# ---------------------------------------------------------------------------
# 3. Trial-level RT exclusions
# ---------------------------------------------------------------------------
# Convert RT to numeric (missing responses are already NaN)
data['RT'] = pd.to_numeric(data['RT'], errors='coerce')

# Flag exclusions
data['excluded'] = False
data.loc[data['RT'].isna(), 'excluded'] = True           # no response / timeout
data.loc[data['RT'] < 0.2, 'excluded'] = True            # RT < 200 ms
data.loc[data['RT'] > 2.0, 'excluded'] = True            # RT > 2000 ms

n_excluded = data['excluded'].sum()
print(f'Trial-level exclusions: {n_excluded}/{len(data)} trials '
      f'({n_excluded / len(data):.0%}) removed (no response, RT<200ms, or RT>2000ms).\n')

# Keep only non-excluded trials for further analysis
clean = data[~data['excluded']].copy()


# ---------------------------------------------------------------------------
# 4. Condition means (Lexicality x Duration)
# ---------------------------------------------------------------------------
# Accuracy is computed on all clean trials; RT only on correct trials
acc_by_cond = clean.groupby(['subject', 'lexicality', 'duration'])['accuracy'].mean()
rt_correct = clean[clean['accuracy'] == 1].copy()
rt_by_cond = rt_correct.groupby(['subject', 'lexicality', 'duration'])['RT'].agg(['mean', 'median'])
rt_by_cond.columns = ['mean_RT', 'median_RT']

print('=' * 60)
print('CONDITION MEANS PER PARTICIPANT')
print('=' * 60)

print('\n--- Accuracy ---')
print(acc_by_cond.unstack('duration').to_string())

print('\n--- Mean correct RT (s) ---')
print(rt_by_cond['mean_RT'].unstack('duration').to_string())

print('\n--- Median correct RT (s) ---')
print(rt_by_cond['median_RT'].unstack('duration').to_string())
print()

# Grand means (across participants)
grand_acc = clean.groupby(['lexicality', 'duration'])['accuracy'].mean()
grand_rt = rt_correct.groupby(['lexicality', 'duration'])['RT'].agg(['mean', 'median'])
grand_rt.columns = ['mean_RT', 'median_RT']

print('=' * 60)
print('GRAND MEANS (across participants)')
print('=' * 60)

print('\n--- Accuracy ---')
print(grand_acc.unstack('duration').to_string())

print('\n--- Mean correct RT (s) ---')
print(grand_rt['mean_RT'].unstack('duration').to_string())

print('\n--- Median correct RT (s) ---')
print(grand_rt['median_RT'].unstack('duration').to_string())
print()


# ---------------------------------------------------------------------------
# 5. Plots
# ---------------------------------------------------------------------------
conditions = clean.groupby(['lexicality', 'duration']).agg(
    accuracy=('accuracy', 'mean'),
).reset_index()

rt_conditions = rt_correct.groupby(['lexicality', 'duration']).agg(
    mean_RT=('RT', 'mean'),
).reset_index()

durations = sorted(clean['duration'].unique())
lexicalities = ['word', 'pseudoword']
x = np.arange(len(durations))
bar_width = 0.35

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# --- Accuracy plot ---
ax = axes[0]
for i, lex in enumerate(lexicalities):
    subset = conditions[conditions['lexicality'] == lex]
    # ensure bars align with duration order
    vals = [subset[subset['duration'] == d]['accuracy'].values[0]
            if len(subset[subset['duration'] == d]) > 0 else 0
            for d in durations]
    ax.bar(x + i * bar_width, vals, bar_width, label=lex.capitalize())

ax.set_xlabel('Presentation duration (s)')
ax.set_ylabel('Accuracy (proportion correct)')
ax.set_title('Accuracy by Lexicality and Duration')
ax.set_xticks(x + bar_width / 2)
ax.set_xticklabels([str(d) for d in durations])
ax.set_ylim(0, 1.05)
ax.legend()

# --- RT plot ---
ax = axes[1]
for i, lex in enumerate(lexicalities):
    subset = rt_conditions[rt_conditions['lexicality'] == lex]
    vals = [subset[subset['duration'] == d]['mean_RT'].values[0]
            if len(subset[subset['duration'] == d]) > 0 else 0
            for d in durations]
    ax.bar(x + i * bar_width, vals, bar_width, label=lex.capitalize())

ax.set_xlabel('Presentation duration (s)')
ax.set_ylabel('Mean correct RT (s)')
ax.set_title('Reaction Time by Lexicality and Duration')
ax.set_xticks(x + bar_width / 2)
ax.set_xticklabels([str(d) for d in durations])
ax.legend()

plt.tight_layout()
plt.savefig(os.path.join(args.data_path, 'results.png'), dpi=150)
print(f'Figure saved to {args.data_path}/results.png')
plt.show()
