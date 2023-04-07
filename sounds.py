import sys, pygame, glob, os

from pygame.locals import *
import pygame.mixer
import globals

pygame.mixer.init()


class Sounds(object):
    def __init__(self):
        self.axe_sounds = []
        self.gunshot_sounds = []
        self.punch_sounds = []
        self.zombie_attack_sounds = []
        self.zombie_sounds = []
        path = globals.pyinst.get_path()
        for filename in glob.glob(os.path.join(path, "*.ogg")):
            # print filename
            sound = pygame.mixer.Sound(filename)
            sound.set_volume(0.6)
            name = os.path.basename(os.path.splitext(filename)[0])
            if "axe" in name:
                self.axe_sounds.append(sound)
            if "gunshot" in name:
                self.gunshot_sounds.append(sound)
            if "punch" in name:
                self.punch_sounds.append(sound)
            if "zombie_attack" in name:
                self.zombie_attack_sounds.append(sound)
            if "zombie" in name and "zombie_" not in name:
                self.zombie_sounds.append(sound)

            setattr(self, name, sound)
