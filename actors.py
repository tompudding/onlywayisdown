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

class Animation(object):
    fps = 8
    num_frames = 8
    def __init__(self,texture,name):
        self.texture = texture
        self.name = name
        self.still_tc = globals.atlas.TextureSpriteCoords('%s_%s.png' % (self.texture,self.name))
        self.tcs = []
        self.start = 0
        for i in xrange(self.num_frames):
            self.tcs.append(globals.atlas.TextureSpriteCoords('%s_walk_right_%d.png' % (self.texture,i)))
            
        new_tcs = range(self.num_frames)
        if self.name != 'right':
            for i in xrange(self.num_frames):
                #flip the x-coords...
                j = self.num_frames - 1 - i
                new_tcs[i] = [self.tcs[j][3],self.tcs[j][2],self.tcs[j][1],self.tcs[j][0]]

            self.tcs = new_tcs

    def SetStart(self,x):
        self.start = x

    def GetTc(self,speed,x):
        if abs(speed) < 0.0001:
            return self.still_tc
        print x,self.start
        elapsed = (x - self.start)*0.125
        frame = int((elapsed*self.fps)%self.num_frames)
        return self.tcs[frame]

class Actor(object):
    texture = None
    width = None
    height = None
    threshold = 0.01
    overscan = 1.05
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
        self.move_direction = Point(0,0)
        for dir,name in self.dirsa:
            self.dirs[dir] = Animation(self.texture,name)

        #self.dirs = dict((dir,globals.atlas.TextureSpriteCoords('%s_%s.png' % (self.texture,name))) for (dir,name) in self.dirs)
        self.dir = Directions.RIGHT
        self.quad = drawing.Quad(globals.quad_buffer,tc = self.dirs[self.dir].GetTc(0,0))
        self.size = Point(self.width,self.height).to_float()/globals.tile_dimensions
        self.corners = Point(0,0),Point(self.size.x,0),Point(0,self.size.y),self.size
        self.SetPos(pos)
        self.current_sound = None
        self.jumping = False
        self.jumped = False

    def SetPos(self,pos):
        self.pos = pos
        over_size = Point(self.width,self.height)*self.overscan
        extra = Point(self.width,self.height)*(self.overscan-1)
        bl = (pos*globals.tile_dimensions) - extra/2
        tr = bl + over_size
        bl = bl.to_int()
        tr = tr.to_int()
        self.quad.SetVertices(bl,tr,4)

    def Facing(self):
        facing = self.pos + (self.size/2) + self.dirs_pos[self.dir]
        return facing.to_int()

    def on_ground(self):
        for x in 0,self.size.x:
            pos = self.pos + Point(x,-self.threshold*2)
            target_tile_y = self.map.data[int(pos.x)][int(pos.y)]
            if target_tile_y.type in game_view.TileTypes.Impassable:
                return True
        return False

    def Update(self,t):
        self.Move(t)

    def Move(self,t):
        if self.last_update == None:
            self.last_update = globals.time
            return
        elapsed = globals.time - self.last_update
        self.last_update = globals.time
        
        if self.on_ground():
            self.move_speed.x += self.move_direction.x*elapsed*0.03
            if self.jumping and not self.jumped:
                self.move_speed.y += self.jump_amount
                self.jumped = True
            self.move_speed.x *= 0.8*(1-(elapsed/1000.0))
        
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
            self.dirs[self.dir].SetStart(self.pos.x)
        self.quad.SetTextureCoordinates(self.dirs[self.dir].GetTc(amount.x,self.pos.x))

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
                if amount.x > 0:
                    amount.x = (int(target_x)-pos.x-self.threshold)
                else:
                    amount.x = (int(target_x)+1-pos.x+self.threshold)
                
                target_x = pos.x + amount.x
                
            elif (int(target_x),int(pos.y)) in self.map.object_cache:
                obj = self.map.object_cache[int(target_x),int(pos.y)]
                if obj.Contains(Point(target_x,pos.y)):
                    if amount.x > 0:
                        amount.x = (int(target_x)-pos.x-self.threshold)
                    else:
                        amount.x = (int(target_x)+1-pos.x+self.threshold)
                    target_x = pos.x + amount.x

        for corner in self.corners:
            pos = self.pos + corner
            target_y = pos.y + amount.y
            if target_y >= self.map.size.y:
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
                    if amount.y > 0:
                        amount.y = (int(target_y)-pos.y-self.threshold)
                    else:
                        amount.y = (int(target_y)+1+self.threshold-pos.y)
                    target_y = pos.y + amount.y
            
        #self.move_speed.y = amount.y
        if amount.y == 0:
            self.move_speed.y = 0
            
        self.SetPos(self.pos + amount)


    def GetPos(self):
        return self.pos

class Player(Actor):
    texture = 'player'
    width = 24/Actor.overscan
    height = 32/Actor.overscan
    jump_amount = 0.4
