
import random
import contest.util as util
from contest.capture_agents import CaptureAgent
from contest.game import Directions
from contest.util import nearest_point


def create_team(first_index, second_index, is_red,
                first='AdvancedOffensiveAgent', second='AdvancedDefensiveAgent', num_training=0):
    return [eval(first)(first_index), eval(second)(second_index)]


class ReflexCaptureAgent(CaptureAgent):
    def __init__(self, index, time_for_computing=.1):
        super().__init__(index, time_for_computing)
        self.start = None

    def register_initial_state(self, game_state):
        self.start = game_state.get_agent_position(self.index)
        CaptureAgent.register_initial_state(self, game_state)

    def choose_action(self, game_state):
        actions = game_state.get_legal_actions(self.index)
        values = [self.evaluate(game_state, a) for a in actions]
        max_value = max(values)
        best_actions = [a for a, v in zip(actions, values) if v == max_value]

        food_left = len(self.get_food(game_state).as_list())
        if food_left <= 2:
            best_dist = 9999
            best_action = None
            for action in actions:
                successor = self.get_successor(game_state, action)
                pos2 = successor.get_agent_position(self.index)
                dist = self.get_maze_distance(self.start, pos2)
                if dist < best_dist:
                    best_action = action
                    best_dist = dist
            return best_action

        return random.choice(best_actions)

    def get_successor(self, game_state, action):
        successor = game_state.generate_successor(self.index, action)
        pos = successor.get_agent_state(self.index).get_position()
        if pos != nearest_point(pos):
            return successor.generate_successor(self.index, action)
        else:
            return successor

    def evaluate(self, game_state, action):
        features = self.get_features(game_state, action)
        weights = self.get_weights(game_state, action)
        return features * weights

    def get_features(self, game_state, action):
        raise NotImplementedError

    def get_weights(self, game_state, action):
        raise NotImplementedError


class AdvancedOffensiveAgent(ReflexCaptureAgent):
    def get_features(self, game_state, action):
        features = util.Counter()
        successor = self.get_successor(game_state, action)
        food_list = self.get_food(successor).as_list()
        my_pos = successor.get_agent_state(self.index).get_position()

        # Food prioritization
        features['successor_score'] = -len(food_list)
        if len(food_list) > 0:
            min_distance = min([self.get_maze_distance(my_pos, food) for food in food_list])
            features['distance_to_food'] = min_distance

        # Avoiding enemies
        enemies = [successor.get_agent_state(i) for i in self.get_opponents(successor)]
        chasers = [a for a in enemies if not a.is_pacman and a.get_position() is not None]
        if len(chasers) > 0:
            dists = [self.get_maze_distance(my_pos, a.get_position()) for a in chasers]
            features['enemy_distance'] = min(dists)

        # Prioritize returning with food
        carrying = successor.get_agent_state(self.index).num_carrying
        if carrying > 3:
            features['return_priority'] = self.get_maze_distance(my_pos, self.start)

        return features

    def get_weights(self, game_state, action):
        return {'successor_score': 100, 'distance_to_food': -1, 'enemy_distance': 2, 'return_priority': -10}


class AdvancedDefensiveAgent(ReflexCaptureAgent):
    def get_features(self, game_state, action):
        features = util.Counter()
        successor = self.get_successor(game_state, action)
        my_state = successor.get_agent_state(self.index)
        my_pos = my_state.get_position()

        # Defense mode
        features['on_defense'] = 1
        if my_state.is_pacman:
            features['on_defense'] = 0

        # Invader tracking
        enemies = [successor.get_agent_state(i) for i in self.get_opponents(successor)]
        invaders = [a for a in enemies if a.is_pacman and a.get_position() is not None]
        features['num_invaders'] = len(invaders)
        if len(invaders) > 0:
            dists = [self.get_maze_distance(my_pos, a.get_position()) for a in invaders]
            features['invader_distance'] = min(dists)

        # Stop and reverse penalties
        if action == Directions.STOP:
            features['stop'] = 1
        rev = Directions.REVERSE[game_state.get_agent_state(self.index).configuration.direction]
        if action == rev:
            features['reverse'] = 1

        # Prioritize capsules
        capsules = self.get_capsules_you_are_defending(successor)
        if len(capsules) > 0:
            min_capsule_dist = min([self.get_maze_distance(my_pos, cap) for cap in capsules])
            features['capsule_proximity'] = -min_capsule_dist

        return features

    def get_weights(self, game_state, action):
        return {'num_invaders': -1000, 'on_defense': 100, 'invader_distance': -10, 'stop': -100, 'reverse': -2, 'capsule_proximity': 50}
