'''

THIS CODE WAS ADAPTED from Patrick Loeber, 2021
https://github.com/patrickloeber/snake-ai-pytorch

'''

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import os


class Linear_QNet(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        # Feedforward NN with an input layer, hidden layer and an output layer
        # TODO: Experiment
        super().__init__()
        # Create 2 linear layers
        self.linear1 = nn.Linear(input_size, hidden_size)
        self.linear2 = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        # X is the tensor
        # We apply the linear layer, then we apply our relu activation function
        x = F.relu(self.linear1(x))
        x = self.linear2(x)

        return x

    def save(self, file_name='model.pth'):
        model_folder_path = './model'
        if not os.path.exists(model_folder_path):
            os.makedirs(model_folder_path)

        file_name = os.path.join(model_folder_path, file_name)
        torch.save(self.state_dict(), file_name)


class QTrainer:
    def __init__(self, model, lr, gamma):
        self.lr = lr # learning rate
        self.gamma = gamma
        self.model = model
        self.optimizer = optim.Adam(model.parameters(), lr=self.lr) # We chose the adam optimizer
        self.criterion = nn.MSELoss() # loss function (Mean Squared Error)

    def train_step(self, state, action, reward, next_state, game_over):
        # Convert to pytorch tensor
        # If we passed multple values per parameter, they we already have the correct shape (Batch Size, X)
        state = torch.tensor(state, dtype=torch.float)
        next_state = torch.tensor(next_state, dtype=torch.float)
        action = torch.tensor(action, dtype=torch.long)
        reward = torch.tensor(reward, dtype=torch.float)

        # If we passed only one, then we want to torch.un squeeze to reach (1, x)
        if len(state.shape) == 1:
            # Append 1 dimension at the beginning -> (1, x)
            state = torch.unsqueeze(state, 0)
            next_state = torch.unsqueeze(next_state, 0)
            action = torch.unsqueeze(action, 0)
            reward = torch.unsqueeze(reward, 0)
            game_over = (game_over,)

        # Get predicted Q values with current (old) state
        pred = self.model(state) # This is the action so example [0, 0, 0, 0, 1]

        # 2: Q_new = r + y * max(next_predicted Q value) -> only do this if not game_over
        # pred.clone()
        # preds[argmax(action)] = Q_new, The index of the 1 is set to the new Q value

        target = pred.clone()
        for idx in range(len(game_over)):
            Q_new = reward[idx]  # Reward of the current index
            if not game_over[idx]:
                # If not done, then get the reward at the current index + gamma * the maximum value
                # of the next prediction
                Q_new = reward[idx] + self.gamma * torch.max(self.model(next_state[idx]))
            # Set the target of the maximum value of the action to this Q_new value
            target[idx][torch.argmax(action[idx]).item()] = Q_new

        self.optimizer.zero_grad()  # To empty the gradients
        loss = self.criterion(target, pred)  # Calculate the loss with the target and prediction (Qnew, Q)
        loss.backward()  # Apply back propagation and update gradients

        self.optimizer.step()
