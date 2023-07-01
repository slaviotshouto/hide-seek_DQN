'''

THIS CODE WAS ADAPTED from Patrick Loeber, 2021
https://github.com/patrickloeber/snake-ai-pytorch

'''

import os
import matplotlib.pyplot as plt
from IPython import display
import pandas as pd

plt.ion()


def plot_rewards(hider_scores, seeker_scores, mean_hider_scores, mean_seeker_scores):
    display.clear_output(wait=True)
    display.display(plt.gcf())
    plt.clf()
    plt.title('Training Both Teams')
    plt.xlabel('Number of Games')
    plt.ylabel('Score')
    plt.plot(hider_scores, label='Hiders reward')
    plt.plot(seeker_scores, label='Seekers reward')
    plt.plot(mean_hider_scores, label='Hider mean score')
    plt.plot(mean_seeker_scores, label='Seeker mean score')
    plt.legend(loc='upper right')
    plt.text(len(hider_scores)-1, hider_scores[-1], str(hider_scores[-1]))
    plt.text(len(seeker_scores)-1, seeker_scores[-1], str(seeker_scores[-1]))
    plt.show(block=False)
    plt.pause(.1)


def plot_only_mean_rewards(mean_hider_scores, mean_seeker_scores):
    display.clear_output(wait=True)
    display.display(plt.gcf())
    plt.clf()
    plt.title('Deep-Q Learning after 2000 Episodes')
    plt.xlabel('Number of Games')
    plt.ylabel('Reward')
    plt.plot(mean_hider_scores, label='Hider mean score')
    plt.plot(mean_seeker_scores, label='Seeker mean score')
    plt.legend(loc='upper right')
    plt.text(len(mean_hider_scores)-1, mean_hider_scores[-1], str(mean_hider_scores[-1])[:4])
    plt.text(len(mean_seeker_scores)-1, mean_seeker_scores[-1], str(mean_seeker_scores[-1])[:4])
    plt.show(block=False)
    plt.pause(10)


def plot_interaction(interaction, plot_name):
    display.clear_output(wait=True)
    display.display(plt.gcf())
    plt.clf()
    plt.title('Object Interactions')
    plt.xlabel('Number of Games')
    plt.ylabel('Interactions')
    plt.scatter([i for i in range(1, 2001)], interaction, label=plot_name)
    plt.legend(loc='upper right')
    plt.show(block=False)
    plt.pause(0.1)


def save_to_csv(scores_list, file_name):
    model_folder_path = './pandas_plots'
    if not os.path.exists(model_folder_path):
        os.makedirs(model_folder_path)
    file_name = os.path.join(model_folder_path, file_name)

    df = pd.DataFrame(scores_list)
    df.to_csv(file_name, index=False, header=False)


def save_dict_to_csv(round_winners, file_name):
    model_folder_path = './pandas_plots'
    if not os.path.exists(model_folder_path):
        os.makedirs(model_folder_path)
    file_name = os.path.join(model_folder_path, file_name)

    df = pd.DataFrame.from_dict(round_winners, orient="index")
    df.to_csv(file_name)