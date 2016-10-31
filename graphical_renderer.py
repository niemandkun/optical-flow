import numpy as np
from itertools import product
import matplotlib.pyplot as plt
import cv2


#cv2.imshow('Wow!', img)


class Renderer:

    def __init__(self, screen):
        self.screen = screen
        self.render_method = {}

    def register_entity(self, entity_cls, render_method):
        self.render_method[entity_cls] = render_method

    def get_screen_size(self):
        x, y = len(self.screen), len(self.screen[0])
        return y, x

    def render_on_screen(self, entities):
        cv2.namedWindow('screen', cv2.WINDOW_NORMAL)
        self.screen = np.zeros_like(self.screen)
        for entity in entities:
            render = self.render_method.get(type(entity))
            if render is not None:
                try:
                    render(entity)
                except Exception as e:
                    print(e)
                    print('Error: cannot render entity:', entity)
        cv2.imshow('screen', self.screen)

    def draw_player(self, player):
        center = (int(player.x), int(player.y))
        cv2.circle(self.screen, center, 1, (255, 0, 0), -1)

    def draw_bullet(self, bullet):
        maxx, maxy = self.get_screen_size()
        center = (int(bullet.x), int(bullet.y))
        if 0 <= bullet.y < maxy and 0 <= bullet.x < maxx:
            cv2.circle(self.screen, center, 1, (0, 255, 0), -1)

    def draw_enemy(self, enemy):
        center = (int(enemy.x), int(enemy.y))
        cv2.circle(self.screen, center, 1, (0, 0, 255), -1)

    def destroy(self):
        cv2.destroyAllWindows()
