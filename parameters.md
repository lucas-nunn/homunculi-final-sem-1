# Lexical Decision Task - Parameter Reference

Run the experiment with `python player.py` followed by any combination of the flags below.

## Quick Start

```bash
# Default run (subject 1, 40 trials, standard timing)
python player.py

# Subject 2, with practice trials
python player.py --subj 2 --practice

# Subject 3, counterbalanced keys, fullscreen
python player.py --subj 3 --swap_keys --fullscreen
```

## All Parameters

### Participant

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--subj` | int | `1` | Subject/participant ID. Data is saved into a folder named `subj_01`, `subj_02`, etc. Change this for every new participant. |

### Timing

These control the duration of each phase within a trial. All values are in **seconds**.

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--durations` | float(s) | `0.04 0.2` | The stimulus presentation durations that form the levels of the duration IV. Pass one or more values separated by spaces. Each stimulus is shown once at every listed duration, so adding a third value (e.g. `0.04 0.1 0.2`) increases the total number of trials. |
| `--fixation_duration` | float | `0.5` | How long the fixation cross is displayed before the stimulus appears (in seconds). Frame-locked precise timing. |
| `--mask_duration` | float | `0.15` | How long the `#######` mask is shown after the stimulus disappears (in seconds). Frame-locked precise timing. |
| `--response_timeout` | float | `2.0` | Maximum time the participant has to respond after the mask (in seconds). If no key is pressed before the timeout, the trial is recorded as a miss and "Too slow!" feedback is shown. |
| `--feedback_duration` | float | `0.5` | How long the feedback text ("Correct!", "Incorrect.", or "Too slow!") stays on screen (in seconds). |
| `--iti_duration` | float | `0.0` | Extra blank-screen pause inserted **after** feedback and **before** the next trial's fixation cross (in seconds). Set to `0` by default, meaning the next trial's fixation cross follows immediately after feedback. Useful for giving participants a brief rest between trials. |

### Experimental Design

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--n_reps` | int | `1` | Number of times the full stimulus set is repeated. With 20 stimuli and 2 durations: `1` rep = 40 trials, `2` reps = 80 trials. When `n_reps > 1`, a break screen is shown at the midpoint. |
| `--swap_keys` | flag | off | Swaps the response key mapping. Without this flag: **F = WORD, J = NOT A WORD**. With this flag: **F = NOT A WORD, J = WORD**. Use this to counterbalance response mapping across participants (e.g. odd-numbered subjects get default, even-numbered get `--swap_keys`). The instructions and response prompt update automatically. |
| `--practice` | flag | off | Adds 6 practice trials (3 words, 3 pseudowords) with feedback before the real experiment begins. Practice stimuli (`house`, `river`, `bread`, `brike`, `flurn`, `plave`) are separate from the main stimulus set and are not recorded in the data. Half use the shortest duration, half use the longest. |

### Display

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--fullscreen` | flag | off | Run the experiment in fullscreen mode. Recommended for real data collection to avoid distractions and ensure consistent visual angle. |
| `--screen_number` | int | `1` | Which monitor to display the experiment on. Use `1` for the primary display, `2` for a secondary monitor, etc. |
| `--font_size` | int | `48` | Font size in points for the stimulus word and the mask. Larger values make the stimulus more visible during brief presentations. Does not affect instruction or feedback text (those stay at 24pt). |
| `--stimulus_font` | str | `Courier` | Font family used for the stimulus word and mask. `Courier` (monospace) is recommended because the `#` mask characters match the stimulus width. Other options: `Helvetica`, `Arial`, `Times`. |

### Data

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--data_path` | str | `./data` | Directory where participant data is saved. Each participant gets a subfolder (e.g. `./data/subj_01/`). |

## Output Files

For each participant, three files are saved in `<data_path>/subj_<ID>/`:

| File | Format | Contents |
|------|--------|----------|
| `trial_info.csv` | CSV | The generated trial list (trial number, stimulus, lexicality, duration) |
| `trial_responses.csv` | CSV | Trial list plus recorded responses (response key, RT in seconds, accuracy) |
| `timing.json` | JSON | Frame-accurate timing logs for each trial (estimated vs. actual flip times) |
| `exp.pkl` | Pickle | The full `Exp` object including all parameters and the `run_args` dict recording every command-line flag used for that run |

## Example Workflows

### Basic data collection for 5 participants
```bash
python player.py --subj 1 --practice --fullscreen
python player.py --subj 2 --practice --fullscreen --swap_keys
python player.py --subj 3 --practice --fullscreen
python player.py --subj 4 --practice --fullscreen --swap_keys
python player.py --subj 5 --practice --fullscreen
```

### Pilot run with longer viewing times
```bash
python player.py --subj 99 --durations 0.1 0.5 --practice
```

### Extended session (80 trials) with extra gap between trials
```bash
python player.py --subj 1 --n_reps 2 --iti_duration 0.3 --fullscreen
```

### Testing three duration levels
```bash
python player.py --subj 1 --durations 0.04 0.1 0.2
```
This creates 20 stimuli x 3 durations = 60 trials.

## Notes

- **Escape to quit**: Press Escape at any point during the experiment (instructions, fixation, stimulus, mask, response, practice, or break screen). Partial data is saved automatically.
- **Timing precision**: Fixation, stimulus, and mask durations use frame-locked timing via `time.monotonic_ns()`. Feedback and ITI use `time.sleep()` (sufficient since they are not time-critical). The actual frame-level timing is logged in `timing.json`.
- **40 ms at 60 Hz**: A 40 ms stimulus corresponds to roughly 2-3 frames at 60 Hz (each frame ~16.67 ms), so the actual presentation may be quantized slightly.
- **Randomization**: Trials are shuffled with the constraint that no more than 3 trials of the same lexicality (word/pseudoword) appear in a row.
