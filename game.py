#!/usr/bin/env python3
try:
    import curses
    HAS_CURSES = True
except ImportError:
    from graphical_renderer import Renderer as GRenderer
    HAS_CURSES = False


import socket
import struct
import time
import math
import random
import numpy as np
import cv2
from threading import Thread
from itertools import product


STARTING_POSITION = (10, 20)
GUN_FREEZE_TIME = 30
ENEMY_SPAWN_DURATION = 20
ENEMY_SPEED = 0.7
TARGET_FPS = 60

PLAYER_SPRITE = '@'
ENEMY_SPRITE = '#'
BULLET_SPRITE = '*'


def distance(first, second):
    return math.sqrt((first[0]-second[0]) ** 2 + (first[1]-second[1]) ** 2)


class Joystick:

    def __init__(self, name):
        self.update(0, 0)
        self.name = name

    def update(self, posx, posy):
        self.posx = posx
        self.posy = posy

    def __str__(self):
        return "{name}: ({posx}, {posy})".format(**self.__dict__)


class Entity:

    def __init__(self, game, x, y):
        self.game = game
        self.x = self.y = 0
        self.move(x, y)

    def __str__(self):
        return '<{}: at ({}, {})>'.format(type(self), self.x, self.y)

    def move(self, dx, dy):
        self.x += dx
        self.y += dy

    def controller_act(self, dx, dy):
        pass

    def logic_act(self):
        pass


class Gun(Entity):

    def __init__(self, game, parent_entity, freeze_time):
        self.game = game
        self.freeze_time = freeze_time
        self.ready_to_fire = 0
        self.parent = parent_entity

    def controller_act(self, dx, dy):
        if self.ready_to_fire == 0:
            bullet = Bullet(self.game, self.parent.x, self.parent.y)
            self.game.spawn_entity(bullet)
            self.game.set_velocity(bullet, dx, dy)
            self.ready_to_fire = self.freeze_time

    def logic_act(self):
        self.ready_to_fire = max(0, self.ready_to_fire - 1)


class Player(Entity):

    def controller_act(self, dx, dy):
        self.x += dx
        self.y += dy

    def logic_act(self):
        scr_x, scr_y = self.game.render.get_screen_size()
        self.x = min(scr_x - 3, max(self.x, 1))
        self.y = min(scr_y - 2, max(self.y, 1))
        self.spawn_enemy()
        self.check_collision()

    def check_collision(self):
        for enemy in (e for e in self.game.entities if isinstance(e, Enemy)):
            if distance((self.x, self.y), (enemy.x, enemy.y)) < 2:
                # game over if collide enemy once
                game.keep_alive = False

    def spawn_enemy(self):
        scr_x, scr_y = self.game.render.get_screen_size()
        time = self.game.ticks_count
        if time % ENEMY_SPAWN_DURATION == 0:
            self.game.spawn_entity(Enemy(self.game, scr_x - 3,
                                         random.random() * scr_y))


class DisposableEntity(Entity):

    def logic_act(self):
        scr_x, scr_y = self.game.render.get_screen_size()
        if self.x >= scr_x - 1 or self.x <= 0 or \
                self.y >= scr_y or self.y <= 0:
            self.game.kill_entity(self)


class Enemy(DisposableEntity):

    def __init__(self, *args):
        super().__init__(*args)
        self.__velocity = ENEMY_SPEED + (random.random() * 0.5 - 0.25)

    def logic_act(self):
        super().logic_act()
        self.x -= self.__velocity
        self.check_collision()

    def check_collision(self):
        for bullet in (b for b in self.game.entities if isinstance(b, Bullet)):
            if distance((self.x, self.y), (bullet.x, bullet.y)) < 2:
                # enemy dead if collide with bullet and add 1 score
                game.scores += 1
                game.kill_entity(self)
                game.kill_entity(bullet)


class Bullet(DisposableEntity):

    def logic_act(self):
        super().logic_act()


class Game:

    def __init__(self, left_controller, right_controller, screen):
        super().__init__()
        self.scores = 0
        self.render = self.create_renderer(screen)
        self.keep_alive = True
        player = Player(self, STARTING_POSITION[0], STARTING_POSITION[1])
        self.controllers = {
            left_controller: player,
            right_controller: Gun(self, player, GUN_FREEZE_TIME)
        }
        self.velocities = {}
        self.entities = list(self.controllers.values())
        self.ticks_count = 0

    def create_renderer(self, screen):
        if HAS_CURSES:
            render = Renderer(screen)
        else:
            size = 10
            render = GRenderer(np.zeros([9 * size, 16 * size, 3]))

        render.register_entity(Player, render.draw_player)
        render.register_entity(Bullet, render.draw_bullet)
        render.register_entity(Enemy, render.draw_enemy)
        return render

    def spawn_entity(self, entity):
        self.entities.append(entity)

    def kill_entity(self, entity):
        if entity in self.entities:
            self.entities.remove(entity)

    def set_velocity(self, entity, dx, dy):
        if dx == dy == 0:
            self.velocities.pop(entity)
            return
        self.velocities[entity] = (dx, dy)

    def run(self):
        while self.keep_alive:

            for controller, entity in self.controllers.items():
                if controller.posx != 0 and controller.posy != 0:
                    entity.controller_act(controller.posx, controller.posy)

            for entity, velocity in self.velocities.items():
                entity.move(*velocity)

            for entity in self.entities:
                entity.logic_act()

            print(time.time())
            self.render.render_on_screen(self.entities)
            self.ticks_count += 1

            if HAS_CURSES:
                time.sleep(1 / TARGET_FPS)
            else:
                k = cv2.waitKey(100 // TARGET_FPS) & 0xff
                if k == 27:
                    break

        return self.scores


class Renderer:

    def __init__(self, screen):
        self.screen = screen
        self.render_method = {}

    def register_entity(self, entity_cls, render_method):
        self.render_method[entity_cls] = render_method

    def get_screen_size(self):
        y, x = self.screen.getmaxyx()
        return x, y

    def render_on_screen(self, entities):
        self.screen.erase()
        for entity in entities:
            render = self.render_method.get(type(entity))
            if render is not None:
                try:
                    render(entity)
                except Exception:
                    curses.endwin()
                    print('Error: cannot render entity:', entity)
        self.screen.refresh()

    def draw_player(self, player):
        maxy, maxx = self.screen.getmaxyx()
        for dx, dy in product(range(-2, 2), range(-1, 2)):
            newx, newy = int(player.x) + dx, int(player.y) + dy
            if (abs(dx) != abs(dy) or dx == 0 or dx == -2) and \
                    0 <= newy < maxy and 0 <= newx < maxx:
                self.screen.move(newy, newx)
                self.screen.addch(PLAYER_SPRITE)

    def draw_bullet(self, bullet):
        maxy, maxx = self.screen.getmaxyx()
        if 0 <= bullet.y < maxy and 0 <= bullet.x < maxx:
            self.screen.move(int(bullet.y), int(bullet.x))
            self.screen.addch(BULLET_SPRITE)

    def draw_enemy(self, enemy):
        maxy, maxx = self.screen.getmaxyx()
        for dx, dy in product(range(-1, 2), repeat=2):
            newx, newy = int(enemy.x) + dx, int(enemy.y) + dy
            if (abs(dx) != abs(dy) or dx == 0 or dx == -2) and \
                    0 <= newy < maxy and 0 <= newx < maxx:
                self.screen.move(newy, newx)
                self.screen.addch(ENEMY_SPRITE)


class UpdateThread(Thread):

    def __init__(self, socket):
        super().__init__()
        self.socket = socket
        self.devices = []
        self.keep_alive = True

    def register_device(self, dev):
        self.devices.append(dev)

    def run(self):
        while self.keep_alive:
            data, addr = self.socket.recvfrom(1024)
            name, data = data.split(b'\r\n', 1)
            for dev in self.devices:
                if name.decode() == dev.name:
                    data = struct.unpack('>ff', data)
                    dev.update(*data)


server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind(("0.0.0.0", 38228))
joystick1 = Joystick("joystick1")
joystick2 = Joystick("joystick2")
updater = UpdateThread(server)
updater.register_device(joystick1)
updater.register_device(joystick2)
updater.start()

try:
    stdscr = None
    if HAS_CURSES:
        stdscr = curses.initscr()
        stdscr.border()
        # stdscr.bkgd('.')
        curses.curs_set(0)
        curses.noecho()

    game = Game(joystick1, joystick2, stdscr)
    scores = game.run()
except KeyboardInterrupt:
    game.keep_alive = False
finally:
    if HAS_CURSES:
        server.close()
        curses.endwin()
    else:
        game.render.destroy()
    updater.keep_alive = False
    updater.join()


print('Game Over.. Your scores: {}'.format(scores))
