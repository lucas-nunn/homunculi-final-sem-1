import os, json, pickle
import numpy as np
import pandas as pd


class Exp():
    def __init__(self, subj,
                 words=None, pseudowords=None,
                 durations=None, n_reps=1,
                 fixation_duration=0.5, mask_duration=0.15,
                 response_timeout=2.0, feedback_duration=0.5,
                 data_path='./data'):

        # basic params
        self.subj = subj

        # stimuli
        if words is None:
            self.words = ['garden', 'window', 'table', 'dream', 'silver',
                          'candle', 'forest', 'winter', 'yellow', 'sudden']
        else:
            self.words = words
        if pseudowords is None:
            self.pseudowords = ['drean', 'gardon', 'tible', 'windal', 'plone',
                                'froat', 'nemp', 'slinter', 'brask', 'marden']
        else:
            self.pseudowords = pseudowords

        # durations in seconds (40 ms and 200 ms)
        if durations is None:
            self.durations = [0.04, 0.2]
        else:
            self.durations = durations

        # timing params in seconds
        self.fixation_duration = fixation_duration
        self.mask_duration = mask_duration
        self.response_timeout = response_timeout
        self.feedback_duration = feedback_duration

        # repetitions
        self.n_reps = n_reps

        # data params
        self.data_path = data_path

        # compute n_trials: each stimulus at each duration, times number of repetitions
        self.n_trials = (len(self.words) + len(self.pseudowords)) * len(self.durations) * self.n_reps

        # generate trials
        self.generate_trials()

        # prepare response pandas DataFrame and dict to log timing
        # NOTE: I am doing one in a dict and the other in a pandas df so you can see both ways. You can do whichever you prefer.
        self.prepare_response_pd()  # store responses in a pandas DataFrame
        self.logs_timing = {}  # store the times when we wanted stuff to flip and when it did flip in a dict

    def generate_trials(self):
        # Each stimulus is presented once per duration per repetition
        # e.g. 20 stimuli x 2 durations x 1 rep = 40 trials

        all_stimuli = self.words + self.pseudowords
        all_lexicality = ['word'] * len(self.words) + ['pseudoword'] * len(self.pseudowords)

        rows = []
        for rep in range(self.n_reps):
            for dur in self.durations:
                for stim, lex in zip(all_stimuli, all_lexicality):
                    rows.append({
                        'stimulus': stim,
                        'lexicality': lex,
                        'duration': dur,
                    })

        self.trial_info = pd.DataFrame(rows)

        # Shuffle with constraint: no more than 3 trials in a row of the same lexicality
        for _ in range(1000):
            self.trial_info = self.trial_info.sample(frac=1).reset_index(drop=True)
            if self._check_lex_constraint():
                break

        self.trial_info['trial_number'] = np.arange(self.n_trials)
        self.trial_info = self.trial_info[['trial_number', 'stimulus', 'lexicality', 'duration']]

        # Save the DataFrame to a CSV file
        self.subj_dir = f'{self.data_path}/subj_{self.subj:02d}'
        os.makedirs(self.subj_dir, exist_ok=True)
        self.trial_info.to_csv(f'{self.subj_dir}/trial_info.csv', index=False)

    def _check_lex_constraint(self):
        """No more than 3 trials in a row of the same lexicality."""
        lexicalities = self.trial_info['lexicality'].values
        count = 1
        for i in range(1, len(lexicalities)):
            if lexicalities[i] == lexicalities[i - 1]:
                count += 1
                if count > 3:
                    return False
            else:
                count = 1
        return True

    def prepare_response_pd(self):
        # create new columns for the responses
        self.trial_responses = self.trial_info.copy()
        self.trial_responses['response'] = None
        self.trial_responses['RT'] = None
        self.trial_responses['accuracy'] = None

    def save_expt(self):
        # this is how to save a pandas dict to csv
        self.trial_responses.to_csv(f'{self.subj_dir}/trial_responses.csv', index=False)
        # this is how to save a dict to a json file
        with open(f'{self.subj_dir}/timing.json', 'w') as f:
            json.dump(self.logs_timing, f)
        # let's also save the whole Exp instance
        with open(f'{self.subj_dir}/exp.pkl', 'wb') as f:
            pickle.dump(self, f)
