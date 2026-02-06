'''
NOTE: this code is based on and extends the code from tachypy_example3.py.
'''

import time
from tachypy import (
    Text,
    Screen,
    FixationCross,
    center_rect_on_point,
    ResponseHandler,
)
### IMPORT OUR FUNCTIONS AND CLASSES FROM OTHER .PY FILES
from helper_functions import load_textures


### INITIALIZE THE EXPERIMENT (THE IDEA IS THAT ONCE THE CODE RUNS YOU WILL ONLY EVER CHANGE THIS LINE
### TO CHANGE THE SUBJECT ID, EXPERIMENT PARAMETERS, ETC)
from generator import Exp
exp = Exp(subj=1, n_trials=10, categs=['cameleon', 'goat'], n_imgs_per_categ=5,
          im_h=300, im_w=300, im_folder='./imgs_cam_goa',
          trial_start_interval=0.5, stimulus_duration=0.5, data_path='./data_example4')

### CONVERT S TO NS FOR TIMING
trial_start_interval_ns = exp.trial_start_interval*1e9
stimulus_duration_ns = exp.stimulus_duration*1e9

### SETUP STUFF THAT WE'LL USE FOR ALL SCRIPTS
# Define screen we will draw to
screen_number = 1
screen = Screen(screen_number=screen_number, fullscreen=False, desired_refresh_rate=60)

# flip the screen (needed for frame_rate measruement below)
screen.fill([128, 128, 128])
# flip the screen to make the background color visible
screen.flip()

# get some relevant screen properties
center_x = screen.width//2 
center_y = screen.height//2 
frame_rate_measured = 1/screen.test_flip_intervals(num_frames=100)
half_ifi_s = 1/(2*frame_rate_measured)  # half the inter-frame interval in seconds
half_ifi_ns = half_ifi_s*1e9  # half the inter-frame interval in nanoseconds
print(f'Measured frame rate: {frame_rate_measured:.2f} Hz')


### LOAD UP STUFF WE WANT TO SHOW ON SCREEN
fixation_cross = FixationCross(center=[center_x, center_y], half_width=10, half_height=10, thickness=5.0, color=(0, 0, 0))


### LOAD UP IMAGES
all_textures = load_textures(exp.im_folder, exp.im_w, exp.im_h, exp.categs)


# define the position in which the Texture will be mapped.
dest_rect = center_rect_on_point([0, 0, exp.im_w-1, exp.im_h-1], [center_x, center_y])


### INITIALIZE RESPONSE HANDLER
response_handler = ResponseHandler(keys_to_listen=['escape', 'left', 'right'])


# flip an initial screen and record starting time
screen.fill([128, 128, 128])
start_time = screen.flip() # returns time in ns
exp.logs_timing['start'] = start_time/1e9 # ns to s


### PRESENT WELCOME TEXT AND WAIT FOR RESPONSE TO START
# print welcome message
screen.fill([128, 128, 128])
welcome_message = Text('Welcome to the experiment! Press left or right arrow to begin', dest_rect=dest_rect, font_name='Helvetica', font_size=24, color=(0, 0, 0))
welcome_message.draw()
screen.flip()
while True:
    response_handler.get_events()
    if response_handler.is_key_down('left') or response_handler.is_key_down('right'):
        break


### LOOP OVER TRIALS
for trial in range(exp.n_trials):

    # create empty "subdicts" for this trial (only needed for dicts, not for pandas)
    exp.logs_timing[f'trial_{trial}'] = {}

    # log the start of the trial and start trial timer
    trial_start_ns = time.monotonic_ns() # get the current time in nanoseconds
    exp.logs_timing[f'trial_{trial}']['trialStart'] = trial_start_ns/1e9  # log in seconds

    # look into our trial list to get the categ and image id
    trial_categ = exp.trial_info.loc[trial, 'categ']
    trial_categ_id = exp.trial_info.loc[trial, 'categ_id']
    trial_img = exp.trial_info.loc[trial, 'img_id']
    # get the corresponding texture
    trial_texture = all_textures[trial_categ][trial_img]
        

    # pre-stimulus blank screen presented for trial_start_interval_ns nanoseconds
    estimated_time = trial_start_ns + trial_start_interval_ns
    while time.monotonic_ns() < estimated_time - half_ifi_ns:
        screen.fill([128, 128, 128])
        fixation_cross.draw()
        true_time = screen.flip()
    exp.logs_timing[f'trial_{trial}']['stimOnset'] = {'estimated': (estimated_time-trial_start_ns)/1e9, 
                                                      'true': (true_time-trial_start_ns)/1e9} # ns to s


    # stimulus presentation
    estimated_time = estimated_time + stimulus_duration_ns
    while time.monotonic_ns() < estimated_time - half_ifi_ns:
        screen.fill([128, 128, 128])
        trial_texture.draw(dest_rect)
        fixation_cross.draw()
        true_time = screen.flip()
    exp.logs_timing[f'trial_{trial}']['stimOffset'] = {'estimated': (estimated_time-trial_start_ns)/1e9, 
                                                       'true': (true_time-trial_start_ns)/1e9} # ns to s


    # get response
    screen.fill([128, 128, 128])
    instruction = Text('Press left arrow for cameleon, right for goat', dest_rect=dest_rect, font_name='Helvetica', font_size=24, color=(0, 0, 0))
    instruction.draw()
    response_start_time = screen.flip()
    response_handler.get_events() # get rid of any lingering key presses
    while True:
        response_handler.get_events()
        if response_handler.is_key_down('left'):
            response = 0
            break
        elif response_handler.is_key_down('right'):
            response = 1
            break
        elif response_handler.is_key_down('escape'):
            screen.close()
            exit()
    response_given_time = time.monotonic_ns()
    exp.trial_responses.loc[trial, 'response'] = response
    exp.trial_responses.loc[trial, 'RT'] = (response_given_time - response_start_time)/1e9  # ns to s
    correct = response == trial_categ_id
    exp.trial_responses.loc[trial, 'accuracy'] = correct
    
    # wait with sloppy timing as this is not critical
    time.sleep(0.5)

    # Display feedback text
    screen.fill([128, 128, 128])
    text_str = 'Correct!' if correct else 'Incorrect.'
    feedback_message = Text(text_str, dest_rect=dest_rect, font_name='Helvetica', font_size=24, color=(0, 0, 0))
    feedback_message.draw()
    screen.flip()

    # wait with sloppy timing as this is not critical
    time.sleep(0.5)

# print goodbye message
screen.fill([128, 128, 128])
goodbye_message = Text('Goodbye!', dest_rect=dest_rect, font_name='Helvetica', font_size=24, color=(0, 0, 0))
goodbye_message.draw()
screen.flip()

 # wait with sloppy timing as this is not critical
time.sleep(2)

# close the screen
screen.close()

# save everything (responses, timing_logs, and Exp instance)
exp.save_expt()

print('Experiment finished!')