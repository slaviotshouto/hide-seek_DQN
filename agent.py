'''

THIS CODE WAS ADAPTED from Patrick Loeber, 2021
https://github.com/patrickloeber/snake-ai-pytorch

'''

import torch
import random
import numpy as np
from collections import deque  # data structure where we want to store our memory
from hide_seek import Game, screen, LIME
from model import Linear_QNet, QTrainer
from plot_helper import plot_rewards, plot_interaction, save_to_csv, save_dict_to_csv

MAX_MEMORY = 100_000
BATCH_SIZE = 1000
LR = 0.001

SITUATED = True
INTRINSIC = False

class Agent:

    def __init__(self):
        self.n_games = 0  # keep track of games
        self.epsilon = 0  # control the randomness # If you are loading a model, please adjust this to something smaller
        self.gamma = 0.9  # discount rate
        self.memory = deque(maxlen=MAX_MEMORY) # If we exceed this memory, then it would automatically remove elements from the left
        self.model = Linear_QNet(15, 256, 5) # Model: input, hidden, output size
        self.trainer = QTrainer(self.model, lr=LR, gamma=self.gamma) # trainer

    def get_state(self, game, player):
        # State consists of 15 values
        # [
        #  direction left, direction right, direction up, direction down,
        #  grabbed_object
        #  ray1, ray2, ray3, ray4, ray5, ray6, ray7, ra8, ray9, ray10
        # ]

        # Agent Direction
        direction = player.direction
        direction_list = [0, 0, 0, 0]
        direction_list[direction-1] = 1

        # Binary has agent grabbed an object
        grabbed_object = [1] if player.grabbed_obj else [0]

        # Agent FOV
        fov = player.fov
        encoded_fov = game.encode_fov(fov)

        state = direction_list + grabbed_object + encoded_fov

        return np.array(state, dtype=int)

    def train_long_memory(self):
        # We grab 1000 samples from our memory
        # We sample at random from the memory
        if len(self.memory) > BATCH_SIZE:
            mini_sample = random.sample(self.memory, BATCH_SIZE)  # list of tuples
        else:
            # If we don't 1000 samples, then we simply get the whole memory
            mini_sample = self.memory

        # We put every state, action, reward together
        states, actions, rewards, next_states, dones = zip(*mini_sample)
        # We call the trainer for multiple states, actions, rewards, etc
        self.trainer.train_step(states, actions, rewards, next_states, dones)

        # for state, action, reward, nexrt_state, done in mini_sample:
        #    self.trainer.train_step(state, action, reward, next_state, done)

    def train_short_memory(self, state, action, reward, next_state, game_over):
        # This trainer is called to the the optimization
        # It gets all the variables
        self.trainer.train_step(state, action, reward, next_state, game_over)

    def remember(self, state, action, reward, next_state, game_over):
        # We store this tuple of value in the memory
        self.memory.append((state, action, reward, next_state, game_over)) # Can only go to 100 000

    def get_action(self, state):
        # Get the action based on the state
        # At the beggining do some random moves: Exploration / exploitation
        # The better our agent gets, the less random moves we want to get and the more we want to explore
        self.epsilon = 80 - self.n_games  # We can play around with this value
        final_move = [0, 0, 0, 0, 0]  # LEFT, RIGHT, UP, DOWN, GRAB/RELEASE

        # The more games, the smaller the epsilon, the less frequent we move randomly
        if random.randint(0, 200) < self.epsilon:
            move = random.randint(0, 4)
            final_move[move] = 1
        else:
            # Convert to tensor
            state0 = torch.tensor(state, dtype=torch.float)
            prediction = self.model(state0)  # Predict the action based on one state (This executes the forward function)
            # It will return a list, containing raw float values, from which we want the argmax
            # Then we set the argmax item to 1
            move = torch.argmax(prediction).item()  # Int
            final_move[move] = 1

        return final_move


def train(intrinsic_motivation=False, situated_moves=False):
    file_name = 'RETESTED_situated'  # '_situated' if situated_moves else '_regular'
    motivation_suffix = 'fov100'  # '_intrinsic' if intrinsic_motivation else ''  # emergent
    round_winners = {'hiders': 0, 'seekers': 0}
    hiders_total_interaction_times = []
    seekers_total_interaction_times = []

    plot_hider_rewards = []
    plot_mean_hider_rewards = []
    reward_hider_team = 0
    total_reward_hider_team = 0
    best_hider_team_reward = float('-inf')

    plot_seeker_rewards = []
    plot_mean_seeker_rewards = []
    reward_seeker_team = 0
    total_reward_seeker_team = 0
    best_seeker_team_reward = float('-inf')

    agent_ha = Agent()
    agent_hb = Agent()

    agent_sa = Agent()
    agent_sb = Agent()

    game = Game(screen)
    while True:
        # Clear and then update the screen
        game.screen.fill(LIME)
        game.hiders_group.draw(game.screen)
        game.seekers_group.draw(game.screen)
        game.walls_group.draw(game.screen)
        game.crates_group.draw(game.screen)
        game.hammers_group.draw(game.screen)

        # Get the previous game state for hiders
        hider_a_state_old = agent_ha.get_state(game, game.hider_a)
        hider_b_state_old = agent_hb.get_state(game, game.hider_b)

        # Get the previous game state for seekers
        seeker_a_state_old = agent_sa.get_state(game, game.seeker_a)
        seeker_b_state_old = agent_sb.get_state(game, game.seeker_b)

        # Get the move based on the previous game state for hiders
        action_ha = agent_ha.get_action(hider_a_state_old)
        action_hb = agent_hb.get_action(hider_b_state_old)

        # Get the move based on the previous game state for seekers
        action_sa = agent_sa.get_action(seeker_a_state_old)
        action_sb = agent_sb.get_action(seeker_b_state_old)

        # Perform action and add rewards to teams
        game_over, r_seekers, r_hiders, winner = game.tick(action_ha, action_hb, action_sa, action_sb, situated_moves)
        reward_hider_team += r_hiders
        reward_seeker_team += r_seekers

        # Get the current new game state for hiders
        hider_a_state_new = agent_ha.get_state(game, game.hider_a)
        hider_b_state_new = agent_hb.get_state(game, game.hider_b)

        # Get the current new game state for seekers
        seeker_a_state_new = agent_sa.get_state(game, game.seeker_a)
        seeker_b_state_new = agent_sb.get_state(game, game.seeker_b)

        # Train the short memory of hiders
        agent_ha.train_short_memory(hider_a_state_old, action_ha, r_hiders, hider_a_state_new, game_over)
        agent_hb.train_short_memory(hider_b_state_old, action_hb, r_hiders, hider_b_state_new, game_over)

        # Train the short memory of seekers
        agent_sa.train_short_memory(seeker_a_state_old, action_sa, r_seekers, seeker_a_state_new, game_over)
        agent_sb.train_short_memory(seeker_b_state_old, action_sb, r_seekers, seeker_b_state_new, game_over)

        # Store in the memory deque for hider agents
        agent_ha.remember(hider_a_state_old, action_ha, r_hiders, hider_a_state_new, game_over)
        agent_hb.remember(hider_b_state_old, action_hb, r_hiders, hider_b_state_new, game_over)

        # Store in the memory deque for hider agents
        agent_sa.remember(seeker_a_state_old, action_sa, r_hiders, seeker_a_state_new, game_over)
        agent_sb.remember(seeker_b_state_old, action_sb, r_hiders, seeker_b_state_new, game_over)

        print(reward_hider_team, reward_seeker_team)
        if game_over:
            # Write down the number of times both teams interacted with objects
            hiders_total_interaction_times.append(game.hider_a.interaction_times + game.hider_b.interaction_times)
            seekers_total_interaction_times.append(game.seeker_a.interaction_times + game.seeker_b.interaction_times)

            # Collect round winner data
            round_winners[winner] += 1

            # Reset game and all player instances
            game.reset()

            # Add number of games
            agent_ha.n_games += 1
            agent_hb.n_games += 1
            agent_sa.n_games += 1
            agent_sb.n_games += 1

            # Experience replay
            agent_ha.train_long_memory()
            agent_hb.train_long_memory()
            agent_sa.train_long_memory()
            agent_sb.train_long_memory()

            # if reward_hider_team > best_hider_team_reward:
            #     best_hider_team_reward = reward_hider_team
            agent_ha.model.save('model_ha{}.pth'.format(file_name))
            agent_hb.model.save('model_hb{}.pth'.format(file_name))

            # if reward_seeker_team > best_seeker_team_reward:
            #     best_seeker_team_reward = reward_seeker_team
            agent_sa.model.save('model_sa{}.pth'.format(file_name))
            agent_sb.model.save('model_sb{}.pth'.format(file_name))

            print('R_hiders:', reward_hider_team, 'Games', agent_ha.n_games)
            print('R_seekers:', reward_seeker_team, 'Games', agent_sa.n_games)

            print('Round Winners: {}'.format(round_winners))

            plot_hider_rewards.append(reward_hider_team)
            plot_seeker_rewards.append(reward_seeker_team)

            # Calculate the mean scores over the games played so far
            total_reward_hider_team += reward_hider_team
            total_reward_seeker_team += reward_seeker_team

            plot_mean_hider_rewards.append(total_reward_hider_team/agent_ha.n_games)
            plot_mean_seeker_rewards.append(total_reward_seeker_team/agent_sa.n_games)

            reward_hider_team, reward_seeker_team = 0, 0
            # total_score += r_hiders
            # mean_score = total_score / agent_ha.n_games
            # plot_hider_mean_rewards.append(mean_score)
            save_to_csv(plot_hider_rewards, 'hider_rewards{}{}.csv'.format(file_name,
                                                                           motivation_suffix))
            save_to_csv(plot_seeker_rewards, 'seeker_rewards{}{}.csv'.format(file_name,
                                                                             motivation_suffix))
            save_to_csv(hiders_total_interaction_times, 'hiders_interaction{}{}.csv'.format(file_name,
                                                                                            motivation_suffix))
            save_to_csv(seekers_total_interaction_times, 'seekers_interaction{}{}.csv'.format(file_name,
                                                                                              motivation_suffix))
            save_dict_to_csv(round_winners, 'round_winners{}{}.csv'.format(file_name,
                                                                           motivation_suffix))

            plot_rewards(plot_hider_rewards, plot_seeker_rewards, plot_mean_hider_rewards, plot_mean_seeker_rewards)

            if agent_ha.n_games >= 2000:
                break
            # plot_interaction(hiders_interaction_times, seekers_interaction_times)


if __name__ == '__main__':
    # Set global variables to preference
    situated = True if SITUATED else False
    intrinsic = True if INTRINSIC else False

    train(intrinsic_motivation=intrinsic, situated_moves=situated)
