import time
from collections import deque
import itertools
import random
import pickle

import numpy as np

from drl.actor import Actor
from mcts.mcts import MCTS
from games.hex import Hex


class ActorTrainer:

    def __init__(self, game, checkpoint_directory, actor=None, network_save_interval=100, rollouts=100,
                 start_game=0, replay_save_interval=250, replay_limit=20000, minibatch_size=50,
                 replay_file=None):
        self.game = game
        self.checkpoint_directory = checkpoint_directory
        self.network_save_interval = network_save_interval
        self.mcts = MCTS(game, simulations=rollouts, default_policy=self.create_default_policy())
        self.game_count = start_game
        self.replay_save_interval = replay_save_interval
        self.replay_buffer = deque(maxlen=replay_limit)
        self.rp_count = 0
        self.minibatch_size = minibatch_size
        self.replay_file = replay_file

        if actor:
            self.actor = actor
            self.save_actor_to_file()
        else:
            self.load_actor_from_file()
            if start_game > 0:
                self.actor.load_checkpoint(f'{checkpoint_directory}/game_{start_game}')

        if replay_save_interval > replay_limit:
            raise ValueError(f'replay_save_interval ({replay_save_interval}) must be smaller '
                             f'than replay_limit ({replay_limit})')

        if replay_file is not None:
            try:
                self.load_replays()
            except FileNotFoundError:
                pass

        if start_game == 0:
            self.actor.save_checkpoint(checkpoint_directory + '/game_0')

    def train(self, num_games):
        for i in range(num_games):
            self.game_count += 1
            game_start_time = time.time()
            print(f'[GAME {self.game_count}] Initializing state')
            state = self.game.get_initial_state()
            self.mcts.set_state(state)

            print(f'[GAME {self.game_count}] Simulating game')
            while not self.game.is_finished(state):
                move, probabilities = self.mcts.select_move(True)
                padded_probs = np.pad(probabilities, (0, self.game.num_possible_moves() - len(probabilities)),
                                      'constant')
                self.add_to_replay_buffer(state, padded_probs)
                state = game.get_outcome_state(state, move)
                self.mcts.set_state(state)

            print(f'[GAME {self.game_count}] Training neural network')
            self.train_network()

            if self.game_count % self.network_save_interval == 0:
                print(f'[GAME {self.game_count}] Saving neural network checkpoint')
                self.actor.save_checkpoint(f'{self.checkpoint_directory}/game_{self.game_count}')
            print(f'[GAME {self.game_count}] Time elapsed: {time.time() - game_start_time:.2f}')
            print()

    def train_network(self):
        minibatch = random.sample(self.replay_buffer, min(self.minibatch_size, len(self.replay_buffer)))
        for i in range(len(minibatch)):
            minibatch[i] = self.game.format_for_nn(minibatch[i][0]), minibatch[i][1]
        self.actor.network.train(minibatch=minibatch)

    def create_default_policy(self):
        def actor_default_policy(state, moves):
            move = self.actor.select_move(state, stochastic=True)
            return move

        return actor_default_policy

    def add_to_replay_buffer(self, state, probabilities):
        self.replay_buffer.append((state, probabilities))
        self.rp_count += 1

        if self.replay_save_interval != -1 and self.rp_count % self.replay_save_interval == 0 and self.rp_count != 0:
            replays = len(self.replay_buffer)
            self.save_replays(itertools.islice(self.replay_buffer, replays - self.replay_save_interval, replays))

    def save_replays(self, replays):
        if self.replay_file is None:
            return

        with open(self.replay_file, 'a') as f:
            for replay in replays:
                state_string = ','.join(map(str, replay[0][0])) + ',' + str(replay[0][1])
                probs_string = ','.join(map(str, replay[1]))
                rp_string = state_string + ';' + probs_string
                f.write(rp_string + '\n')

    def load_replays(self):
        with open(self.replay_file, 'r') as f:
            for line in f:
                state, probs = line.split(';')
                state = list(map(int, state.split(',')))
                player = state[-1]
                board = state[:-1]
                probs = list(map(float, probs.split(',')))
                self.replay_buffer.append(((board, player), probs))

    def load_actor_from_file(self):
        with open(f'{self.checkpoint_directory}/actor_params.txt') as f:
            lines = f.read().split('\n')
            one_hot = bool(lines[0])

        with open(f'{self.checkpoint_directory}/actor_layers.bin', 'rb') as f:
            layers = pickle.load(f)

        self.actor = Actor(self.game, layers, one_hot_encode_state=one_hot)

    def save_actor_to_file(self):
        with open(f'{self.checkpoint_directory}/actor_params.txt', 'w') as f:
            f.write(str(self.actor.one_hot_encode_state))

        with open(f'{self.checkpoint_directory}/actor_layers.bin', 'wb') as f:
            pickle.dump(self.actor.layers, f)


if __name__ == '__main__':
    game = Hex()
    layers = [100, 50]
    actor = Actor(game, layers, one_hot_encode_state=True)
    num_games = 100

    trainer = ActorTrainer(
        game=game,
        checkpoint_directory='model/test',
        actor=None,
        network_save_interval=50,
        rollouts=100,
        start_game=0,
        replay_save_interval=250,
        replay_limit=20000,
        minibatch_size=50,
        replay_file='model/replays/replays_100_rollouts.txt',
    )

    trainer.train(num_games)