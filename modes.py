from OpenGL.GL import *
import random, numpy, cmath, math, pygame

import ui, globals, drawing, os, copy
from globals.types import Point
import sys


class Mode(object):
    """Abstract base class to represent game modes"""

    def __init__(self, parent):
        self.parent = parent

    def KeyDown(self, key):
        pass

    def MouseMotion(self, pos, rel):
        pass

    def KeyUp(self, key):
        pass

    def MouseButtonDown(self, pos, button):
        return False, False

    def Update(self, t):
        pass


class TitleStages(object):
    STARTED = 0
    COMPLETE = 1
    TEXT = 2
    SCROLL = 3
    WAIT = 4


class Titles(Mode):
    blurb = "THE ONLY WAY IS DOWN"

    def __init__(self, parent):
        self.parent = parent
        self.start = pygame.time.get_ticks()
        self.stage = TitleStages.STARTED
        self.handlers = {TitleStages.STARTED: self.Startup, TitleStages.COMPLETE: self.Complete}
        bl = self.parent.GetRelative(Point(0, 0))
        tr = bl + self.parent.GetRelative(globals.screen)
        self.blurb_text = ui.TextBox(
            parent=self.parent,
            bl=bl,
            tr=tr,
            text=self.blurb,
            textType=drawing.texture.TextTypes.GRID_RELATIVE,
            colour=(1, 1, 1, 1),
            scale=4,
        )
        self.backdrop = ui.Box(
            parent=globals.screen_root, pos=Point(0, 0), tr=Point(1, 1), colour=(0, 0, 0, 0)
        )
        self.backdrop.Enable()

    def KeyDown(self, key):
        self.stage = TitleStages.COMPLETE

    def Update(self, t):
        self.elapsed = t - self.start
        self.stage = self.handlers[self.stage](t)

    def Complete(self, t):
        self.backdrop.Delete()
        self.blurb_text.Delete()
        self.parent.mode = GameOver(self.parent)

    def Startup(self, t):
        return TitleStages.STARTED


class GameMode(Mode):
    blurb = "THE ONLY WAY IS DOWN"
    speed = 12
    direction_amounts = {
        pygame.K_a: Point(-0.01 * speed, 0.00),
        pygame.K_d: Point(0.01 * speed, 0.00),
        pygame.K_w: Point(0.00, 0.01 * speed),
        pygame.K_s: Point(0.00, -0.01 * speed),
    }

    class KeyFlags:
        LEFT = 1
        RIGHT = 2
        UP = 4
        DOWN = 8

    keyflags = {
        pygame.K_a: KeyFlags.LEFT,
        pygame.K_d: KeyFlags.RIGHT,
        pygame.K_w: KeyFlags.UP,
        pygame.K_s: KeyFlags.DOWN,
    }

    inv_keys = [pygame.K_1, pygame.K_2, pygame.K_3]

    def __init__(self, parent):
        self.parent = parent
        bl = self.parent.GetRelative(self.parent.viewpos.pos)
        self.parent.viewpos.Follow(globals.time, self.parent.map.player)

        tr = bl + self.parent.GetRelative(globals.screen)
        self.blurb_text = ui.TextBox(
            parent=self.parent,
            bl=bl,
            tr=tr,
            text=self.blurb,
            textType=drawing.texture.TextTypes.GRID_RELATIVE,
            colour=(1, 1, 1, 1),
            scale=4,
        )
        self.keydownmap = 0

    def KeyDown(self, key):
        if key in self.direction_amounts:
            self.keydownmap |= self.keyflags[key]
            self.parent.map.player.move_direction += self.direction_amounts[key]
        elif key == pygame.K_SPACE:
            self.parent.map.player.jumping = True
            self.parent.map.player.jumped = False

    def KeyUp(self, key):
        if key in self.direction_amounts and (self.keydownmap & self.keyflags[key]):
            self.keydownmap &= ~self.keyflags[key]
            self.parent.map.player.move_direction -= self.direction_amounts[key]
        elif key == pygame.K_SPACE:
            self.parent.map.player.jumping = False
            self.parent.map.player.jumped = False
        elif key in self.inv_keys:
            inv = self.inv_keys.index(key)
            self.parent.map.player.Select(inv)

    def MouseButtonDown(self, pos, button):
        self.parent.map.player.Click(pos, button)
        return False, False

    def MouseMotion(self, pos, rel):
        self.parent.map.player.MouseMotion(pos, rel)


class GameOver(Mode):
    blurb = "GAME OVER : you were eaten by zombies"

    def __init__(self, parent):
        self.parent = parent
        self.blurb_text = None
        self.handlers = {
            TitleStages.TEXT: self.TextDraw,
            TitleStages.SCROLL: self.Wait,
            TitleStages.WAIT: self.Wait,
        }
        self.backdrop = ui.Box(
            parent=globals.screen_root, pos=Point(0, 0), tr=Point(1, 1), colour=(0, 0, 0, 0.6)
        )

        bl = self.parent.GetRelative(Point(0, 0))
        tr = bl + self.parent.GetRelative(Point(globals.screen.x, globals.screen.y * 0.5))
        self.blurb_text = ui.TextBox(
            parent=globals.screen_root,
            bl=bl,
            tr=tr,
            text=self.blurb,
            textType=drawing.texture.TextTypes.SCREEN_RELATIVE,
            scale=3,
        )

        self.start = None
        self.blurb_text.EnableChars(0)
        self.stage = TitleStages.TEXT
        self.played_sound = False
        self.skipped_text = False
        self.letter_duration = 20
        self.continued = False
        # pygame.mixer.music.load('end_fail.mp3')
        # pygame.mixer.music.play(-1)

    def Update(self, t):
        if self.start is None:
            self.start = t
        self.elapsed = t - self.start
        self.stage = self.handlers[self.stage](t)
        if self.stage == TitleStages.COMPLETE:
            raise sys.exit("Come again soon!")

    def Wait(self, t):
        return self.stage

    def SkipText(self):
        if self.blurb_text:
            self.skipped_text = True
            self.blurb_text.EnableChars()

    def TextDraw(self, t):
        if not self.skipped_text:
            if self.elapsed < (len(self.blurb_text.text) * self.letter_duration) + 2000:
                num_enabled = int(self.elapsed / self.letter_duration)
                self.blurb_text.EnableChars(num_enabled)
            else:
                self.skipped_text = True
        elif self.continued:
            return TitleStages.COMPLETE
        return TitleStages.TEXT

    def KeyDown(self, key):
        # if key in [13,27,32]: #return, escape, space
        if not self.skipped_text:
            self.SkipText()
        else:
            self.continued = True

    def MouseButtonDown(self, pos, button):
        self.KeyDown(0)
        return False, False


class GameWin(GameOver):
    blurb = "You launch the ICBM for some reason, killing many zombies (and people). You win?"
