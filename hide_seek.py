import pygame
import sys
import random

from plot_helper import save_to_csv, plot_rewards

pygame.init()

RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
LIME = (3, 252, 157)
WHITE = (255, 255, 255)

WINDOW_W = 600
WINDOW_H = 400

LEFT = 1
RIGHT = 2
UP = 3
DOWN = 4
GRAB_RELEASE = 5

EMPTY_FOV = 0
WALL_FOV = 1
CRATE_FOV = 2
HAMMER_FOV = 3
HIDER_FOV = 4
SEEKER_FOV = 5

block_size = 10
speed = block_size

fov_encode_map = {
    '_': EMPTY_FOV,
    'W': WALL_FOV,
    'C': CRATE_FOV,
    'HM': HAMMER_FOV,
    'HI': HIDER_FOV,
    'S' : SEEKER_FOV
}

key_move_map_old = {
    pygame.K_LEFT:  (-speed, 0),
    pygame.K_RIGHT: (speed, 0),
    pygame.K_UP:    (0, -speed),
    pygame.K_DOWN:  (0, speed),
}

key_move_map = {
    pygame.K_LEFT:  LEFT,
    pygame.K_RIGHT: RIGHT,
    pygame.K_UP:    UP,
    pygame.K_DOWN:  DOWN,
}

opposite_move_map = {
    LEFT: RIGHT,
    RIGHT: LEFT,
    UP: DOWN,
    DOWN: UP
}

direction_move_map = {
    LEFT:  (-speed, 0),
    RIGHT: (speed, 0),
    UP:    (0, -speed),
    DOWN:  (0, speed),
}

# Action Example
# [1, 0, 0, 0, 0] LEFT
# [0, 1, 0, 0, 0] RIGHT
# [0, 0, 1, 0, 0] UP
# [0, 0, 0, 1, 0] DOWN
# [0, 0, 0, 0, 1] GRAB/RELEASE

# game_over = False
# Define the fonts
font = pygame.font.Font('Arial.ttf', 36)

DEBUG = False

screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))


class Game:
    def __init__(self, screen):
        # Init the game window
        self.screen = screen
        self.clock = pygame.time.Clock()
        pygame.display.set_caption('Hide&Seek')
        self.counter, self.text = 60, '60'.rjust(3)
        pygame.time.set_timer(pygame.USEREVENT, 1000)

        # Create the hiders
        self.hider_a, self.hider_b, self.hiders_group = self.generate_hiders()

        # Create the seekers
        self.seeker_a, self.seeker_b, self.seekers_group = self.generate_seekers()

        # Generate game objects
        self.walls_group = self.generate_walls()
        self.crates_group = self.generate_crates()
        self.hammers_group = self.generate_hammers()

    def tick(self, action_ha=None, action_hb=None, action_sa=None, action_sb=None):
        g_over = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # elif event.type == pygame.USEREVENT:
            #     self.counter -= 1
            #     self.text = str(self.counter).rjust(3)

            # Only if we are in Debug can move the player
            elif DEBUG and event.type == pygame.KEYDOWN:
                player = self.hider_a
                if event.key in key_move_map.keys():
                    # Get the correct button press action and translate into move
                    move = key_move_map[event.key]
                    # Move the player
                    player.move(move)
                    # Check if collision occurred, if so move the player back
                    if self.check_unit_wall_collision(player) or \
                            self.check_unit_crate_collision(player):
                        player.move(opposite_move_map[move], moved_back=True)

                elif event.key == pygame.K_SPACE:
                    crate = self.crates_group.sprites()[0]
                    hammer = self.hammers_group.sprites()[0]

                    print(crate.rect.midleft, player.rect.midleft)
                    if self.check_grab_proximity(player, crate):
                        print(1)
                        # Invert the boolean (True -> False, False -> True)
                        if not player.grabbed_obj:
                            player.grab_obj(crate.rect)
                        else:
                            player.release_obj()

                    elif self.check_grab_proximity(player, hammer):
                        if player in self.hiders_group:
                            self.hammers_group.remove(hammer)

                elif event.key == pygame.K_z:
                    hammer = self.hammers_group.sprites()[0]
                    #print(hammer.rect.midleft, self.seeker_a.rect.midleft)
                    if self.check_grab_proximity(player, hammer):
                        # Invert the boolean (True -> False, False -> True)
                        if not player.grabbed_obj:
                            player.grab_obj(hammer.rect)
                        else:
                            player.release_obj()

                        #print(self.seeker_a.grabbed_hammer, self.seeker_a.hammer_rect)

        self.counter -= 0.10
        self.text = str(int(self.counter)).rjust(3)

        # Perform passed action, hiders and seekers
        self.move_hiders(action_ha, action_hb)
        # Only move the seekers if the 10 seconds have passed
        if self.counter <= 50: self.move_seekers(action_sa, action_sb)

        seeker_a_fov, seeker_b_fov, hider_a_fov, hider_b_fov = self.get_all_fov()

        reward_hiders, reward_seekers = self.get_reward(seeker_a_fov, seeker_b_fov)

        self.check_player_collisions()
        self.check_hammer_wall_collisions()

        # Check Game over
        if self.counter <= 0 or len(self.hiders_group) <= 0:
            g_over = True

        # Update the screen
        self.screen.blit(font.render(self.text, True, WHITE), (550, 0))
        pygame.display.flip()  # update
        self.clock.tick(100)

        return g_over, reward_seekers, reward_hiders

    def reset(self):
        self.counter, self.text = 60, '60'.rjust(3)

        # Create the hiders
        self.hider_a, self.hider_b, self.hiders_group = self.generate_hiders()

        # Create the seekers
        self.seeker_a, self.seeker_b, self.seekers_group = self.generate_seekers()

        # Generate game objects
        self.walls_group = self.generate_walls()
        self.crates_group = self.generate_crates()
        self.hammers_group = self.generate_hammers()

    def move_seekers(self, action_space_a, action_space_b):
        # Get actions, check at which index there is a 1 value and add 1 to it
        seeker_a_action = action_space_a.index(1) + 1  # Left = idx 0 + 1 = 1
        seeker_b_action = action_space_b.index(1) + 1  # Grab = idx 4 + 1 = 5

        # Move the seekers
        if self.seeker_a in self.seekers_group:
            if seeker_a_action <= 4:
                self.seeker_a.move(seeker_a_action)
                if self.check_unit_wall_collision(self.seeker_a) or \
                        self.check_unit_crate_collision(self.seeker_a):
                    self.seeker_a.move(opposite_move_map[seeker_a_action], moved_back=True)
            else: # [0, 0, 0, 0, 1] = Grab/Release
                for hammer in self.hammers_group:
                    if self.check_grab_proximity(self.seeker_a, hammer):
                        # Invert the boolean (True -> False, False -> True)
                        if not self.seeker_a.grabbed_obj:
                            self.seeker_a.grab_object(hammer.rect)
                        else:
                            self.seeker_a.release_object()

        # Move the seekers
        if self.seeker_b in self.seekers_group:
            if seeker_b_action <= 4:
                self.seeker_b.move(seeker_b_action)
                if self.check_unit_wall_collision(self.seeker_b) or \
                        self.check_unit_crate_collision(self.seeker_b):
                    self.seeker_b.move(opposite_move_map[seeker_b_action], moved_back=True)
            else: # [0, 0, 0, 0, 1] = Grab/Release
                for hammer in self.hammers_group:
                    if self.check_grab_proximity(self.seeker_b, hammer):
                        # Invert the boolean (True -> False, False -> True)
                        if not self.seeker_b.grabbed_obj:
                            self.seeker_b.grab_object(hammer.rect)
                        else:
                            self.seeker_b.release_object()

    def move_hiders(self, action_hider_a, action_hider_b):
        # Get actions, check at which index there is a 1 value and add 1 to it
        hider_a_action = action_hider_a.index(1) + 1 # Left = idx 0 + 1 = 1
        hider_b_action = action_hider_b.index(1) + 1 # Grab = idx 4 + 1 = 5

        # Move the hiders
        if hider_a_action <= 4:
            self.hider_a.move(hider_a_action)
            if self.check_unit_wall_collision(self.hider_a) or \
                    self.check_unit_crate_collision(self.hider_a):
                self.hider_a.move(opposite_move_map[hider_a_action], moved_back=True)
        else: # [0, 0, 0, 0, 1] = Grab/Release
            for hammer in self.hammers_group:
                if self.check_grab_proximity(self.hider_a, hammer):
                    self.hider_a.interaction_times +=1
                    self.hammers_group.remove(hammer)

            for crate in self.crates_group:
                if self.check_grab_proximity(self.hider_a, crate):
                    # Invert the boolean (True -> False, False -> True)
                    if not self.hider_a.grabbed_obj:
                        self.hider_a.grab_obj(crate.rect)
                    else:
                        self.hider_a.release_obj()

        if hider_b_action <= 4:
            self.hider_b.move(hider_b_action)
            if self.check_unit_wall_collision(self.hider_b) or \
                    self.check_unit_crate_collision(self.hider_b):
                self.hider_b.move(opposite_move_map[hider_b_action], moved_back=True)
        else:  # [0, 0, 0, 0, 1] = Grab/Release
            for hammer in self.hammers_group:
                if self.check_grab_proximity(self.hider_b, hammer):
                    self.hider_b.interaction_times +=1
                    self.hammers_group.remove(hammer)

            for crate in self.crates_group:
                if self.check_grab_proximity(self.hider_b, crate):
                    # Invert the boolean (True -> False, False -> True)
                    if not self.hider_b.grabbed_obj:
                        self.hider_b.grab_obj(crate.rect)
                    else:
                        self.hider_b.release_obj()

    def get_all_fov(self):
        # Draw FOV of seekers and get encoded values for all rays
        seeker_a_fov = self.draw_fov(self.seeker_a)
        seeker_b_fov = self.draw_fov(self.seeker_b)

        fov_seeker_a = self.check_fov(self.seeker_a.direction, seeker_a_fov)
        fov_seeker_b = self.check_fov(self.seeker_b.direction, seeker_b_fov)

        self.seeker_a.fov = fov_seeker_a
        self.seeker_b.fov = fov_seeker_b

        # Draw FOV of hiders and get encoded values for all rays
        # Set to None, unless they are still alive
        fov_hider_a, fov_hider_b = None, None
        if self.hider_a in self.hiders_group:
            hider_a_fov = self.draw_fov(self.hider_a)
            fov_hider_a = self.check_fov(self.hider_a.direction, hider_a_fov)
            self.hider_a.fov = fov_hider_a
           # print(fov_hider_a)
            #print(self.encode_fov(fov_hider_a))

        if self.hider_b in self.hiders_group:
            hider_b_fov = self.draw_fov(self.hider_b)
            fov_hider_b = self.check_fov(self.hider_b.direction, hider_b_fov)
            self.hider_b.fov = fov_hider_b

        return fov_seeker_a, fov_seeker_b, fov_hider_a, fov_hider_b

    def draw_fov(self, player):
        ray_start_xy_map = {
            LEFT: (player.rect.midleft[0] - 1, player.rect.midleft[1]),
            RIGHT: player.rect.midright,
            UP: (player.rect.midtop[0], player.rect.midtop[1] - 1),
            DOWN: player.rect.midbottom,
        }

        direction_plus_values = {
            LEFT: (-100, 0),
            RIGHT: (100, 0),
            UP: (0, -100),
            DOWN: (0, 100),
        }

        ray_start = ray_start_xy_map[player.direction]
        add_values = direction_plus_values[player.direction]
        ray_direction = ray_start[0] + add_values[0], ray_start[1] + add_values[1]

        player_fov = []
        for i in range(-50, 50, 10):

            if player.direction in (LEFT, RIGHT):
                line = pygame.draw.line(self.screen, RED,
                                        ray_start,
                                        (ray_direction[0] + 0,
                                        ray_direction[1] + i), 2)
            else:
                line = pygame.draw.line(self.screen, RED,
                                        ray_start,
                                        (ray_direction[0] + i,
                                        ray_direction[1] + 0), 2)
            player_fov.append(line)

        return player_fov

    def check_fov(self, player_direction, player_fov):

        encoded_fov = []
        for line in player_fov:
            collided_with = '_'
            collided_with_dict = {}

            # TODO: Simplify
            for idx, wall in enumerate(self.walls_group):
                if line.colliderect(wall):
                    obj_id = 'W{}'.format(idx)
                    collided_with_dict[self.check_axis(wall, player_direction)] = obj_id

            for idx, crate in enumerate(self.crates_group):
                if line.colliderect(crate):
                    obj_id = 'C{}'.format(idx)
                    collided_with_dict[self.check_axis(crate, player_direction)] = obj_id

            for idx, hammer in enumerate(self.hammers_group):
                if line.colliderect(hammer):
                    obj_id = 'HM{}'.format(idx)
                    collided_with_dict[self.check_axis(hammer, player_direction)] = obj_id

            for idx, hider in enumerate(self.hiders_group):
                if line.colliderect(hider):
                    obj_id = 'HI{}'.format(idx)
                    collided_with_dict[self.check_axis(hider, player_direction)] = obj_id

            for idx, seeker in enumerate(self.seekers_group):
                if line.colliderect(seeker):
                    obj_id = 'S{}'.format(idx)
                    collided_with_dict[self.check_axis(seeker, player_direction)] = obj_id

            if not len(collided_with_dict) <= 0:
                if player_direction in (RIGHT, UP):
                    min_key = min(collided_with_dict)
                    collided_with = collided_with_dict[min_key][:-1]

                elif player_direction in (LEFT, DOWN):
                    min_key = max(collided_with_dict)
                    collided_with = collided_with_dict[min_key][:-1]

            encoded_fov.append(collided_with)

        return encoded_fov

    def get_reward(self, seeker_a_fov, seeker_b_fov):
        # Get the reward for both hiders and seekers
        reward_hiders, reward_seekers = 1, -1

        # If the preliminary stage has not passed, don't give rewards
        if self.counter > 50:
            reward_hiders, reward_seekers = 0, 0

        elif 'HI' in seeker_a_fov or 'HI' in seeker_b_fov:
            reward_hiders, reward_seekers = -1, 1

        return reward_hiders, reward_seekers

    @staticmethod
    def encode_fov(fov):
        encoded_fov = []

        for item in fov:
            encoded_fov.append(fov_encode_map[item])

        return encoded_fov

    @staticmethod
    def check_axis(obj, player_direction):

        position_to_xy = {
            LEFT: obj.rect.x,
            RIGHT: obj.rect.x,
            UP: obj.rect.y,
            DOWN: obj.rect.y
        }

        return position_to_xy[player_direction]

    @staticmethod
    def check_grab_proximity(player, obj):
        return (abs(obj.rect.midleft[0] - player.rect.midright[0]) <= 15 and
                abs(obj.rect.midleft[1] - player.rect.midright[1]) <= 15) or \
                (abs(obj.rect.midright[0] - player.rect.midleft[0]) <= 15 and
                 abs(obj.rect.midright[1] - player.rect.midleft[1]) <= 15) or \
                (abs(obj.rect.midtop[0] - player.rect.midbottom[0]) <= 15 and
                 abs(obj.rect.midtop[1] - player.rect.midbottom[1]) <= 15) or \
                (abs(obj.rect.midbottom[0] - player.rect.midtop[0]) <= 15 and
                 abs(obj.rect.midbottom[1] - player.rect.midtop[1]) <= 15)

    def check_player_collisions(self):
        # Check if seekers have caught hiders
        for seeker in self.seekers_group:
            for hider in self.hiders_group:
                if pygame.sprite.collide_rect(hider, seeker):
                    # Remove caught hiders
                    self.hiders_group.remove(hider)

    def check_hammer_wall_collisions(self):
        # Remove the wal if hit by a hammer
        for hammer in self.hammers_group:
            for wall in self.walls_group:
                if pygame.sprite.collide_rect(hammer, wall):
                    self.walls_group.remove(wall)

    def check_unit_wall_collision(self, unit):
        for wall in self.walls_group:
            if pygame.sprite.collide_rect(unit, wall):
                return True

        return False

    def check_unit_crate_collision(self, unit):
        for crate in self.crates_group:
            if pygame.sprite.collide_rect(unit, crate):
                return True

        return False

    def check_crate_grab(self, unit):
        for crate in self.crates_group:
            if pygame.sprite.collide_rect(unit, crate):
                return True

        return False

    @staticmethod
    def generate_hiders():
        hider_a = Hider(400, 50)
        hider_b = Hider(400, 150)

        return hider_a, hider_b, pygame.sprite.Group(hider_a, hider_b)

    @staticmethod
    def generate_seekers():
        seeker_a = Seeker(0, 50)
        seeker_b = Seeker(0, 150)

        return seeker_a, seeker_b, pygame.sprite.Group(seeker_a, seeker_b)

    @staticmethod
    def generate_walls():
        wall1 = Wall(WHITE, WINDOW_W - block_size, 250, block_size, 150)
        wall2 = Wall(WHITE, 375 - block_size, 250, block_size, 50)
        wall3 = Wall(WHITE, 375 - block_size, 350, block_size, 50)
        wall4 = Wall(WHITE, 375 - block_size, 250, 175, block_size)

        return pygame.sprite.Group(wall1, wall2, wall3, wall4)

    @staticmethod
    def generate_crates():
        crate1 = Crate(280, 250)
        crate2 = Crate(550, 75)

        return pygame.sprite.Group(crate1, crate2)

    @staticmethod
    def generate_hammers():
        hammer1 = Hammer(50, 350)
        hammer2 = Hammer(125, 150)

        return pygame.sprite.Group(hammer1, hammer2)


class Hider(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()

        self.image = pygame.image.load('png/hider_small.png')
        self.rect = self.image.get_rect(topleft=[x, y])
        self.interaction_times = 0
        self.fov = ['_', '_', '_', '_', '_', '_', '_', '_', '_', '_']
        self.direction = RIGHT
        self.grabbed_obj = False
        self.obj_rect = None

    def move(self, direction, moved_back=False):
        # Get move coordinates and set players direction
        x, y = direction_move_map[direction]
        if not moved_back: self.direction = direction

        # Move the player
        self.rect.x += x
        self.rect.y += y
        # Make sure the player stays inside the screen
        if self.rect.x < 0:
            self.rect.x = 0
        if self.rect.x > WINDOW_W - block_size:
            self.rect.x = WINDOW_W - block_size
        if self.rect.y < 0:
            self.rect.y = 0
        if self.rect.y > WINDOW_H - block_size:
            self.rect.y = WINDOW_H - block_size

        # Move Crate if grabbed
        if self.grabbed_obj:
            self.obj_rect.x += x
            self.obj_rect.y += y

    def grab_obj(self, crate_rect):
        self.grabbed_obj = True
        self.obj_rect = crate_rect
        self.interaction_times += 1

    def release_obj(self):
        self.grabbed_obj = False
        self.obj_rect = None
        self.interaction_times += 1


class Seeker(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()

        self.image = pygame.image.load('png/seeker_small.png')
        self.rect = self.image.get_rect(topleft=[x, y])
        self.direction = RIGHT
        self.fov = ['_', '_', '_', '_', '_', '_', '_', '_', '_', '_']
        self.interaction_times = 0
        self.grabbed_obj = False
        self.obj_rect = None

    def move(self, direction, moved_back=False):
        # Get move coordinates and set players direction
        x, y = direction_move_map[direction]
        if not moved_back: self.direction = direction

        # Move the player
        self.rect.x += x
        self.rect.y += y

        # Make sure the seeker stays inside the screen
        if self.rect.x < 0:
            self.rect.x = 0
        if self.rect.x > WINDOW_W - block_size:
            self.rect.x = WINDOW_W - block_size
        if self.rect.y < 0:
            self.rect.y = 0
        if self.rect.y > WINDOW_H - block_size:
            self.rect.y = WINDOW_H - block_size

        # Move Crate if grabbed
        if self.grabbed_obj:
            self.obj_rect.x += x
            self.obj_rect.y += y

    def grab_object(self, crate_rect):
        self.grabbed_obj = True
        self.obj_rect = crate_rect
        self.interaction_times += 1

    def release_object(self):
        self.grabbed_obj = False
        self.obj_rect = None
        self.interaction_times += 1


class Wall(pygame.sprite.Sprite):
    def __init__(self, color, x, y, width, height):
        super().__init__()

        # Set the wall's color
        self.color = color

        # Set the wall's image
        self.image = pygame.Surface([width, height])
        self.image.fill(self.color)

        # Set the wall's position
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y


class Crate(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()

        self.image = pygame.image.load('png/pngwing.com.png')
        self.rect = self.image.get_rect(topleft=[x, y])


class Hammer(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()

        self.image = pygame.image.load('png/hammer.png')
        self.rect = self.image.get_rect(topleft=[x, y])


if __name__ == '__main__':
    # Initialize the game, together with the hiders and seekers

    game = Game(
        screen
    )

    hiders_total_interaction_times = []
    seekers_total_interaction_times = []

    plot_hider_rewards = []
    plot_mean_hider_rewards = []
    reward_hider_team = 0
    total_reward_hider_team = 0

    plot_seeker_rewards = []
    plot_mean_seeker_rewards = []
    reward_seeker_team = 0
    total_reward_seeker_team = 0

    # game loop
    n_games = 0
    while True:
        # Tick with the logic in place
        action_sa, action_sb = [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]
        idx1, idx2 = random.randint(0, 4), random.randint(0, 4)
        action_sa[idx1] = 1
        action_sb[idx2] = 1

        action_ha, action_hb = [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]
        idx3, idx4 = random.randint(0, 4), random.randint(0, 4)
        action_ha[idx3] = 1
        action_hb[idx4] = 1

        game_over, r_seekers, r_hiders = game.tick(action_ha, action_hb, action_sa, action_sb)
        reward_hider_team += r_hiders
        reward_seeker_team += r_seekers
        # Clear and then update the screen
        game.screen.fill(LIME)
        game.hiders_group.draw(game.screen)
        game.seekers_group.draw(game.screen)
        game.walls_group.draw(game.screen)
        game.crates_group.draw(game.screen)
        game.hammers_group.draw(game.screen)

        if game_over:
            n_games += 1

            hiders_total_interaction_times.append(game.hider_a.interaction_times + game.hider_b.interaction_times)
            seekers_total_interaction_times.append(game.seeker_a.interaction_times + game.seeker_b.interaction_times)

            game.reset()

            plot_hider_rewards.append(reward_hider_team)
            plot_seeker_rewards.append(reward_seeker_team)

            # Calculate the mean scores over the games played so far
            total_reward_hider_team += reward_hider_team
            total_reward_seeker_team += reward_seeker_team

            plot_mean_hider_rewards.append(total_reward_hider_team/n_games)
            plot_mean_seeker_rewards.append(total_reward_seeker_team/n_games)

            reward_hider_team, reward_seeker_team = 0, 0

            save_to_csv(plot_hider_rewards, 'random_hider_rewards.csv')
            save_to_csv(plot_seeker_rewards, 'random_seeker_rewards.csv')
            save_to_csv(hiders_total_interaction_times, 'random_hiders_interaction.csv')
            save_to_csv(seekers_total_interaction_times, 'random_seekers_interaction.csv')

            plot_rewards(plot_hider_rewards, plot_seeker_rewards, plot_mean_hider_rewards, plot_mean_seeker_rewards)

