import os, json, pickle
import numpy as np
import pandas as pd


class Exp():
    def __init__(self, subj, n_trials, categs=['cameleon', 'goat'], n_imgs_per_categ=5,
                 im_h=300, im_w=300, im_folder='./imgs_cam_goa',
                 trial_start_interval=0.5, stimulus_duration=0.5, data_path='./data'):
        
        # basic params
        self.subj = subj
        self.n_trials = n_trials

        # category params
        self.categs = categs
        self.n_categs = len(categs)
        self.categ_ids = np.arange(self.n_categs)
        self.categ_id2str = {i: categ for i, categ in zip(self.categ_ids, self.categs)}
        self.categ_str2id = {v: k for k, v in self.categ_id2str.items()}
        self.n_imgs_per_categ = n_imgs_per_categ

        # image params
        self.im_h = im_h
        self.im_w = im_w
        self.im_folder = im_folder

        # timing params
        self.trial_start_interval = trial_start_interval
        self.stimulus_duration = stimulus_duration

        # data params
        self.data_path = data_path
        
        # generate trials
        self.generate_trials()

        # prepare response pandas DataFrame and dict to log timing
        # NOTE: I am doing one in a dict and the other in a pandas df so you can see both ways. You can do whichever you prefer.
        self.prepare_response_pd()  # store responses in a pandas DataFrame
        self.logs_timing = {}  # store the times when we wanteed stuff to flip and when it did flip in a dict

    def generate_trials(self):

        force_equal_number_of_trials = True

        # Randomly select categ IDs and img IDs for each trial
        if force_equal_number_of_trials:
            categ_ids = np.array([0] * self.n_imgs_per_categ + [1] * self.n_imgs_per_categ)

            imgs_ids = []
            for _ in range(len(self.categ_ids)):
                imgs_ids.append(np.random.permutation(range(self.n_imgs_per_categ)))
            imgs_ids = np.concatenate(imgs_ids)

            indices = np.random.permutation(self.n_trials)
            categ_ids = categ_ids[indices]
            imgs_ids = imgs_ids[indices]

            # Check that we get each image exactly once
            done_imgs = []
            for i in range(len(categ_ids)):
                if (categ_ids[i], imgs_ids[i]) in done_imgs:
                    raise ValueError(f'Image {imgs_ids[i]} from categ {categ_ids[i]} was already selected')
                done_imgs.append((categ_ids[i], imgs_ids[i]))

        else:
            categ_ids = np.random.choice(self.categ_ids, self.n_trials)
            imgs_ids = np.random.choice(range(self.n_imgs_per_categ), self.n_trials)

        trial_numbers = np.arange(self.n_trials)
        categs = [self.categ_id2str[categ_id] for categ_id in categ_ids]

        # Create a pandas DataFrame
        self.trial_info = pd.DataFrame({'trial_number': trial_numbers, 'categ': categs, 'categ_id': categ_ids, 'img_id': imgs_ids})

        # Save the DataFrame to a CSV file
        self.subj_dir = f'./{self.data_path}/subj_{self.subj:02d}'
        os.makedirs(self.subj_dir, exist_ok=True)
        self.trial_info.to_csv(f'{self.subj_dir}/trial_info.csv', index=False)

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
        with open(f"{self.subj_dir}/exp.pkl", 'wb') as f:
            pickle.dump(self, f)
    