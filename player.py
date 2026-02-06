'''
Lexical Decision Task with Visual Masking

Within-subject 2x2 factorial design:
  IV1: Lexicality (word vs pseudoword)
  IV2: Presentation duration (40 ms vs 200 ms)
  DVs: Accuracy and Reaction Time

Trial structure:
  1. Fixation cross  (500 ms)
  2. Target string   (40 or 200 ms)
  3. Mask            (150 ms)
  4. Response window (up to 2000 ms)
  5. Feedback        (500 ms)
  6. ITI             (0 ms by default)

Usage examples:
  python player.py
  python player.py --subj 2
  python player.py --subj 3 --mask_duration 0.1 --fixation_duration 0.3
  python player.py --durations 0.04 0.1 0.2 --n_reps 2 --fullscreen
  python player.py --font_size 36 --response_timeout 3.0 --swap_keys
  python player.py --practice --iti_duration 0.3 --stimulus_font Helvetica

NOTE: this code is based on and extends the code from tachypy_example3.py.
'''

import argparse
import random
import time
from tachypy import (
    Text,
    Screen,
    FixationCross,
    center_rect_on_point,
    ResponseHandler,
)
### IMPORT OUR FUNCTIONS AND CLASSES FROM OTHER .PY FILES
from helper_functions import generate_mask


### PARSE COMMAND LINE ARGUMENTS FOR PER-RUN PARAMETER ADJUSTMENT
parser = argparse.ArgumentParser(description='Lexical Decision Task with Visual Masking')
# participant
parser.add_argument('--subj', type=int, default=1,
                    help='Subject ID (default: 1)')
# timing
parser.add_argument('--durations', type=float, nargs='+', default=[0.04, 0.2],
                    help='Stimulus presentation durations in seconds (default: 0.04 0.2)')
parser.add_argument('--fixation_duration', type=float, default=0.5,
                    help='Fixation cross duration in seconds (default: 0.5)')
parser.add_argument('--mask_duration', type=float, default=0.15,
                    help='Mask duration in seconds (default: 0.15)')
parser.add_argument('--response_timeout', type=float, default=2.0,
                    help='Maximum response time in seconds (default: 2.0)')
parser.add_argument('--feedback_duration', type=float, default=0.5,
                    help='Feedback display duration in seconds (default: 0.5)')
parser.add_argument('--iti_duration', type=float, default=0.0,
                    help='Inter-trial interval in seconds, blank screen after feedback (default: 0.0)')
# design
parser.add_argument('--n_reps', type=int, default=1,
                    help='Repetitions of the full stimulus set (default: 1 = 40 trials, 2 = 80 trials)')
parser.add_argument('--swap_keys', action='store_true',
                    help='Swap response keys: F=NOT A WORD, J=WORD (for counterbalancing)')
parser.add_argument('--practice', action='store_true',
                    help='Include 6 practice trials with feedback before the main experiment')
# display
parser.add_argument('--fullscreen', action='store_true',
                    help='Run in fullscreen mode')
parser.add_argument('--screen_number', type=int, default=1,
                    help='Screen/monitor number (default: 1)')
parser.add_argument('--font_size', type=int, default=48,
                    help='Stimulus font size in points (default: 48)')
parser.add_argument('--stimulus_font', type=str, default='Courier',
                    help='Font family for stimulus and mask text (default: Courier)')
# data
parser.add_argument('--data_path', type=str, default='./data',
                    help='Directory to save data (default: ./data)')
args = parser.parse_args()


### INITIALIZE THE EXPERIMENT (NOW CONFIGURED VIA COMMAND LINE ARGUMENTS)
from generator import Exp
exp = Exp(subj=args.subj, durations=args.durations, n_reps=args.n_reps,
          fixation_duration=args.fixation_duration, mask_duration=args.mask_duration,
          response_timeout=args.response_timeout, feedback_duration=args.feedback_duration,
          data_path=args.data_path)

# save the full run configuration so it is recorded alongside the data
exp.run_args = vars(args)

font_size = args.font_size
stimulus_font = args.stimulus_font

### RESPONSE KEY MAPPING (for counterbalancing across participants)
if args.swap_keys:
    key_word = 'j'       # J = WORD
    key_nonword = 'f'    # F = NOT A WORD
else:
    key_word = 'f'       # F = WORD
    key_nonword = 'j'    # J = NOT A WORD
word_label = key_word.upper()
nonword_label = key_nonword.upper()

### CONVERT S TO NS FOR TIMING
fixation_duration_ns = exp.fixation_duration * 1e9
mask_duration_ns = exp.mask_duration * 1e9
response_timeout_ns = exp.response_timeout * 1e9

### SETUP STUFF THAT WE'LL USE FOR ALL SCRIPTS
# Define screen we will draw to
screen = Screen(screen_number=args.screen_number, fullscreen=args.fullscreen, desired_refresh_rate=60)

# flip the screen (needed for frame_rate measurement below)
screen.fill([128, 128, 128])
# flip the screen to make the background color visible
screen.flip()

# get some relevant screen properties
center_x = screen.width // 2
center_y = screen.height // 2
frame_rate_measured = 1 / screen.test_flip_intervals(num_frames=100)
half_ifi_s = 1 / (2 * frame_rate_measured)  # half the inter-frame interval in seconds
half_ifi_ns = half_ifi_s * 1e9  # half the inter-frame interval in nanoseconds
print(f'Measured frame rate: {frame_rate_measured:.2f} Hz')


### SETUP VISUAL ELEMENTS
fixation_cross = FixationCross(center=[center_x, center_y], half_width=10, half_height=10, thickness=5.0, color=(0, 0, 0))

# define the text area for stimulus display
text_rect = center_rect_on_point([0, 0, 599, 199], [center_x, center_y])


### INITIALIZE RESPONSE HANDLER
response_handler = ResponseHandler(keys_to_listen=['escape', 'f', 'j'])


### SINGLE-TRIAL FUNCTION (used by both practice and main experiment)
def run_trial(stimulus, lexicality, duration_ns):
    """
    Run one trial: fixation -> stimulus -> mask -> response -> feedback.
    Returns (quit_requested, result_dict).
    """
    trial_start_ns = time.monotonic_ns()

    # pre-create Text objects for this trial (before precise timing loops)
    stim_text = Text(stimulus.upper(), dest_rect=text_rect,
                     font_name=stimulus_font, font_size=font_size, color=(0, 0, 0))
    msk_text = Text(generate_mask(stimulus), dest_rect=text_rect,
                    font_name=stimulus_font, font_size=font_size, color=(0, 0, 0))

    timing = {'trialStart': trial_start_ns / 1e9}

    # 1. FIXATION CROSS - precise timing
    estimated_time = trial_start_ns + fixation_duration_ns
    while time.monotonic_ns() < estimated_time - half_ifi_ns:
        screen.fill([128, 128, 128])
        fixation_cross.draw()
        true_time = screen.flip()
        response_handler.get_events()
        if response_handler.is_key_down('escape'):
            return True, {}
    timing['stimOnset'] = {
        'estimated': (estimated_time - trial_start_ns) / 1e9,
        'true': (true_time - trial_start_ns) / 1e9}

    # 2. STIMULUS PRESENTATION - precise timing
    estimated_time = estimated_time + duration_ns
    while time.monotonic_ns() < estimated_time - half_ifi_ns:
        screen.fill([128, 128, 128])
        stim_text.draw()
        true_time = screen.flip()
        response_handler.get_events()
        if response_handler.is_key_down('escape'):
            return True, {}
    timing['stimOffset'] = {
        'estimated': (estimated_time - trial_start_ns) / 1e9,
        'true': (true_time - trial_start_ns) / 1e9}

    # 3. MASK - precise timing
    estimated_time = estimated_time + mask_duration_ns
    while time.monotonic_ns() < estimated_time - half_ifi_ns:
        screen.fill([128, 128, 128])
        msk_text.draw()
        true_time = screen.flip()
        response_handler.get_events()
        if response_handler.is_key_down('escape'):
            return True, {}
    timing['maskOffset'] = {
        'estimated': (estimated_time - trial_start_ns) / 1e9,
        'true': (true_time - trial_start_ns) / 1e9}

    # 4. RESPONSE WINDOW
    screen.fill([128, 128, 128])
    prompt = Text(f'{word_label} = WORD    {nonword_label} = NOT A WORD', dest_rect=text_rect,
                  font_name='Helvetica', font_size=24, color=(0, 0, 0))
    prompt.draw()
    response_start_time = screen.flip()
    response_handler.get_events()  # clear any lingering key presses

    response = None
    timed_out = False
    while True:
        response_handler.get_events()
        if response_handler.is_key_down(key_word):
            response = 1  # "word"
            break
        elif response_handler.is_key_down(key_nonword):
            response = 0  # "not a word"
            break
        elif response_handler.is_key_down('escape'):
            return True, {}
        if time.monotonic_ns() - response_start_time > response_timeout_ns:
            timed_out = True
            break
    response_given_time = time.monotonic_ns()

    # compute correctness
    expected = 1 if lexicality == 'word' else 0
    correct = (response == expected) if not timed_out else False

    # 5. FEEDBACK (sloppy timing)
    time.sleep(0.5)
    screen.fill([128, 128, 128])
    if timed_out:
        fb_str = 'Too slow!'
    else:
        fb_str = 'Correct!' if correct else 'Incorrect.'
    fb_text = Text(fb_str, dest_rect=text_rect, font_name='Helvetica', font_size=24, color=(0, 0, 0))
    fb_text.draw()
    screen.flip()
    time.sleep(exp.feedback_duration)

    result = {
        'timing': timing,
        'response': response,
        'timed_out': timed_out,
        'correct': correct,
        'rt': (response_given_time - response_start_time) / 1e9 if not timed_out else None,
    }
    return False, result


# flip an initial screen and record starting time
screen.fill([128, 128, 128])
start_time = screen.flip()  # returns time in ns
exp.logs_timing['start'] = start_time / 1e9  # ns to s


### PRESENT INSTRUCTIONS AND WAIT FOR RESPONSE TO START
screen.fill([128, 128, 128])
instructions = Text(
    'You will see letter strings briefly followed by a mask.\n'
    'Decide if each string is a real English word.\n'
    f'Press {word_label} for WORD, {nonword_label} for NOT A WORD.\n\n'
    f'Press {word_label} or {nonword_label} to begin. Press Escape to quit at any time.',
    dest_rect=text_rect, font_name='Helvetica', font_size=24, color=(0, 0, 0))
instructions.draw()
screen.flip()

quit_experiment = False
while True:
    response_handler.get_events()
    if response_handler.is_key_down('f') or response_handler.is_key_down('j'):
        break
    if response_handler.is_key_down('escape'):
        quit_experiment = True
        break


### PRACTICE TRIALS (optional, not recorded in main data)
if args.practice and not quit_experiment:
    # practice stimuli are separate from the main experiment stimuli
    practice_items = [
        ('house', 'word'),
        ('river', 'word'),
        ('bread', 'word'),
        ('brike', 'pseudoword'),
        ('flurn', 'pseudoword'),
        ('plave', 'pseudoword'),
    ]
    # assign durations: half short, half long
    practice_durs = [exp.durations[0]] * 3 + [exp.durations[-1]] * 3
    practice_trials = list(zip(practice_items, practice_durs))
    random.shuffle(practice_trials)

    # show practice intro
    screen.fill([128, 128, 128])
    practice_intro = Text(
        'PRACTICE TRIALS\n\n'
        'These trials will not be recorded.\n'
        f'Press {word_label} or {nonword_label} to start practice.',
        dest_rect=text_rect, font_name='Helvetica', font_size=24, color=(0, 0, 0))
    practice_intro.draw()
    screen.flip()
    while True:
        response_handler.get_events()
        if response_handler.is_key_down('f') or response_handler.is_key_down('j'):
            break
        if response_handler.is_key_down('escape'):
            quit_experiment = True
            break

    for (p_stim, p_lex), p_dur in practice_trials:
        if quit_experiment:
            break
        quit_experiment, _ = run_trial(p_stim, p_lex, p_dur * 1e9)

    # show "practice complete" message
    if not quit_experiment:
        screen.fill([128, 128, 128])
        practice_done = Text(
            'Practice complete!\n\n'
            'The real experiment will now begin.\n'
            f'Press {word_label} or {nonword_label} to start.',
            dest_rect=text_rect, font_name='Helvetica', font_size=24, color=(0, 0, 0))
        practice_done.draw()
        screen.flip()
        while True:
            response_handler.get_events()
            if response_handler.is_key_down('f') or response_handler.is_key_down('j'):
                break
            if response_handler.is_key_down('escape'):
                quit_experiment = True
                break


### LOOP OVER TRIALS
for trial in range(exp.n_trials):
    if quit_experiment:
        break

    # midpoint break for extended sessions (n_reps > 1)
    if exp.n_reps > 1 and trial == exp.n_trials // 2:
        screen.fill([128, 128, 128])
        break_text = Text(
            f'Halfway done! Take a short break.\nPress {word_label} or {nonword_label} to continue.',
            dest_rect=text_rect, font_name='Helvetica', font_size=24, color=(0, 0, 0))
        break_text.draw()
        screen.flip()
        while True:
            response_handler.get_events()
            if response_handler.is_key_down('f') or response_handler.is_key_down('j'):
                break
            if response_handler.is_key_down('escape'):
                quit_experiment = True
                break
        if quit_experiment:
            break

    # look into our trial list to get the stimulus info
    trial_stimulus = exp.trial_info.loc[trial, 'stimulus']
    trial_lexicality = exp.trial_info.loc[trial, 'lexicality']
    trial_duration = exp.trial_info.loc[trial, 'duration']

    quit_experiment, result = run_trial(trial_stimulus, trial_lexicality, trial_duration * 1e9)
    if quit_experiment:
        break

    # log timing
    exp.logs_timing[f'trial_{trial}'] = result['timing']

    # record response
    if result['timed_out']:
        exp.trial_responses.loc[trial, 'response'] = None
        exp.trial_responses.loc[trial, 'RT'] = None
        exp.trial_responses.loc[trial, 'accuracy'] = 0
    else:
        exp.trial_responses.loc[trial, 'response'] = result['response']
        exp.trial_responses.loc[trial, 'RT'] = result['rt']
        exp.trial_responses.loc[trial, 'accuracy'] = int(result['correct'])

    # inter-trial interval (blank screen, sloppy timing)
    if args.iti_duration > 0:
        screen.fill([128, 128, 128])
        screen.flip()
        time.sleep(args.iti_duration)

# print goodbye message
screen.fill([128, 128, 128])
if quit_experiment:
    goodbye_message = Text('Experiment interrupted. Data saved.', dest_rect=text_rect, font_name='Helvetica', font_size=24, color=(0, 0, 0))
else:
    goodbye_message = Text('Goodbye!', dest_rect=text_rect, font_name='Helvetica', font_size=24, color=(0, 0, 0))
goodbye_message.draw()
screen.flip()

# wait with sloppy timing as this is not critical
time.sleep(2)

# close the screen
screen.close()

# save everything (responses, timing_logs, and Exp instance)
exp.save_expt()

if quit_experiment:
    print('Experiment interrupted by user. Partial data saved.')
else:
    print('Experiment finished!')
