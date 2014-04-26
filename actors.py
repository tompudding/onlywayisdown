from globals.types import Point
import globals
import ui
import drawing
import os
import game_view
import random
import pygame

class Directions:
    UP    = 0
    DOWN  = 1
    RIGHT = 2
    LEFT  = 3

class Actor(object):
    texture = None
    width = None
    height = None
    def __init__(self,map,pos):
        self.map  = map
        self.dirsa = ((Directions.UP   ,'back' ),
                      (Directions.DOWN ,'front'),
                      (Directions.LEFT ,'left' ),
                      (Directions.RIGHT,'right'))
        self.dirs_pos = {Directions.UP    : Point(0,1),
                         Directions.DOWN  : Point(0,-1),
                         Directions.LEFT  : Point(-1,0),
                         Directions.RIGHT : Point(1,0)}
        self.dirs = {}
        for dir,name in self.dirsa:
            try:
                tc = globals.atlas.TextureSpriteCoords('%s_%s.png' % (self.texture,name))
            except KeyError:
                tc = globals.atlas.TextureSpriteCoords('%s_front.png' % self.texture)
            self.dirs[dir] = tc
        #self.dirs = dict((dir,globals.atlas.TextureSpriteCoords('%s_%s.png' % (self.texture,name))) for (dir,name) in self.dirs)
        self.dir = Directions.RIGHT
        self.quad = drawing.Quad(globals.quad_buffer,tc = self.dirs[self.dir])
        self.size = Point(float(self.width)/16,float(self.height)/16)
        self.corners = Point(0,0),Point(self.size.x,0),Point(0,self.size.y),self.size
        self.SetPos(pos)
        self.current_sound = None

    def SetPos(self,pos):
        self.pos = pos
        bl = pos * globals.tile_dimensions
        tr = bl + (globals.tile_scale*Point(self.width,self.height))
        bl = bl.to_int()
        tr = tr.to_int()
        self.quad.SetVertices(bl,tr,4)

    def Facing(self):
        facing = self.pos + (self.size/2) + self.dirs_pos[self.dir]
        return facing.to_int()

    def Move(self,amount):
        pass

    def GetPos(self):
        return self.pos

class Player(Actor):
    texture = 'player'
    width = 24
    height = 32
