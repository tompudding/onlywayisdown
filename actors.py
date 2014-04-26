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
    threshold = 0.01
    def __init__(self,map,pos):
        self.map  = map
        self.last_update = None
        self.dirsa = ((Directions.UP   ,'back' ),
                      (Directions.DOWN ,'front'),
                      (Directions.LEFT ,'left' ),
                      (Directions.RIGHT,'right'))
        self.dirs_pos = {Directions.UP    : Point(0,0),
                         Directions.DOWN  : Point(0,0),
                         Directions.LEFT  : Point(-1,0),
                         Directions.RIGHT : Point(1,0)}
        self.dirs = {}
        self.move_speed = Point(0,0)
        for dir,name in self.dirsa:
            try:
                tc = globals.atlas.TextureSpriteCoords('%s_%s.png' % (self.texture,name))
            except KeyError:
                tc = globals.atlas.TextureSpriteCoords('%s_front.png' % self.texture)
            self.dirs[dir] = tc
        #self.dirs = dict((dir,globals.atlas.TextureSpriteCoords('%s_%s.png' % (self.texture,name))) for (dir,name) in self.dirs)
        self.dir = Directions.RIGHT
        self.quad = drawing.Quad(globals.quad_buffer,tc = self.dirs[self.dir])
        self.size = Point(self.width,self.height).to_float()/globals.tile_dimensions
        self.corners = Point(0,0),Point(self.size.x,0),Point(0,self.size.y),self.size
        self.SetPos(pos)
        self.current_sound = None
        self.jumping = False
        self.jumped = False

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

    def on_ground(self):
        return True

    def Move(self):
        if self.last_update == None:
            self.last_update = globals.time
            return
        elapsed = globals.time - self.last_update
        self.last_update = globals.time
        
        if self.on_ground():
            if self.jumping and not self.jumped:
                self.move_speed.y += self.jump_amount
                self.jumped = True
        self.move_speed.y += globals.gravity*elapsed*0.03
        amount = Point(self.move_speed.x*elapsed*0.03,self.move_speed.y*elapsed*0.03)
        #print self.move_speed,amount
        dir = None
        if amount.x > 0:
            dir = Directions.RIGHT
        elif amount.x < 0:
            dir = Directions.LEFT
        if dir != None and dir != self.dir:
            self.dir = dir
            self.quad.SetTextureCoordinates(self.dirs[self.dir])

        #check each of our four corners
        for corner in self.corners:
            pos = self.pos + corner
            target_x = pos.x + amount.x
            if target_x >= self.map.size.x:
                target_x = self.map.size.x-self.threshold
                amount.x = target_x - pos.x
                
            elif target_x < 0:
                amount.x = -pos.x
                target_x = 0

            target_tile_x = self.map.data[int(target_x)][int(pos.y)]
            if target_tile_x.type in game_view.TileTypes.Impassable:
                amount.x = (int(target_x)-pos.x-self.threshold)
                target_x = pos.x + amount.x
                print target_x
                
            elif (int(target_x),int(pos.y)) in self.map.object_cache:
                obj = self.map.object_cache[int(target_x),int(pos.y)]
                if obj.Contains(Point(target_x,pos.y)):
                    amount.x = (int(target_x)-pos.x-self.threshold)
                    target_x = pos.x + amount.x

        for corner in self.corners:
            pos = self.pos + corner
            target_y = pos.y + amount.y
            if target_y >= self.map.size.y:
                print 'a'
                target_y = self.map.size.y-self.threshold
                amount.y = target_y - pos.y
                
            elif target_y < 0:
                amount.y = -pos.y
                target_y = 0
            target_tile_y = self.map.data[int(pos.x)][int(target_y)]
            if target_tile_y.type in game_view.TileTypes.Impassable:
                if amount.y > 0:
                    amount.y = (int(target_y)-pos.y-self.threshold)
                else:
                    amount.y = (int(target_y)+1+self.threshold-pos.y)
                target_y = pos.y + amount.y
            elif (int(pos.x),int(target_y)) in self.map.object_cache:
                obj = self.map.object_cache[int(pos.x),int(target_y)]
                if obj.Contains(Point(pos.x,target_y)):
                    print 'd'
                    amount.y = (int(target_y)-pos.y-self.threshold)
                    target_y = pos.y + amount.y
            
        #self.move_speed.y = amount.y
        if amount.y == 0:
            self.move_speed.y = 0
            
        self.SetPos(self.pos + amount)


    def GetPos(self):
        return self.pos

class Player(Actor):
    texture = 'player'
    width = 24
    height = 32
    jump_amount = 0.3
