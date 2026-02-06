def generate_mask(stimulus):
    '''
    Generate a mask string matched to the length of the stimulus.
    Uses '#' characters to create a visual mask.
    '''
    return '#' * len(stimulus)
