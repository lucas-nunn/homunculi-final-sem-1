import os
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from tachypy import Texture

def load_textures(base_img_folder, w, h, categs):
    '''
    Load textures from images in the base_img_folder. The images are resized to w x h pixels.
    '''

    textures = {}

    for categ in categs:

        categ_folder = f'{base_img_folder}/{categ}'

        imgs_to_load = os.listdir(categ_folder)

        textures[categ] = []

        for i, img in enumerate(imgs_to_load):
            img = plt.imread(f'{categ_folder}/{img}')

            # make sure image is square
            if img.shape[0] != img.shape[1]:
                # if it is not square, take central crop
                min_dim = min(img.shape[0], img.shape[1])
                ch, cw = img.shape[0]//2, img.shape[1]//2
                img = img[ch-min_dim//2:ch+min_dim//2, cw-min_dim//2:cw+min_dim//2]            

            # resize image using PIL and convert to numpy array
            img = Image.fromarray((img))
            img = img.resize((h, w))
            img = np.array(img)

            # check that the img is in the right format (assert will throw an error if the condition is False)
            assert np.min(img) >= 0 and np.max(img) <= 255, "Image should be in range [0, 255]"
            assert np.issubdtype(img.dtype, np.integer), "Image should be of integer type"

            #  create a Texture object
            textures[categ].append(Texture(img))

    return textures