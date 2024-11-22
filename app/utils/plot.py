
from os.path import join
from random import choice

import matplotlib.pyplot as plt

from app.utils.graph_cleaner import Cleaner


DEST_FOLDER = r"app\static\images\graphs"
ALPHABET = "abcdefghijklmnopqrstuvxywz0123456789"

def plot_n_save(y_data, x_data, title, x_label, y_label):
    fig_name = str().join([choice(ALPHABET) for _ in range(10)]) + ".png"
    fig_path = join(DEST_FOLDER, fig_name)

    fig, ax = plt.subplots()

    if x_data is None:
        ax.plot(y_data)
    else:
        ax.plot(y_data, x_data)

    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    
    fig.savefig(fig_path, bbox_inches='tight')

    cleaner = Cleaner()
    cleaner.new_image(fig_name)
    cleaner.recicle()

    return "images/graphs/" + fig_name
