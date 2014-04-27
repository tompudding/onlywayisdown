from OpenGL.GL import *
import random
import numpy
import cmath
import math
import pygame
import actors

import ui,globals,drawing,os,copy
from globals.types import Point
import modes
import random

class Viewpos(object):
    follow_threshold = 0
    max_away = Point(100,20)
    shake_radius = 4
    def __init__(self,point):
        self._pos = point
        self.NoTarget()
        self.follow = None
        self.follow_locked = False
        self.t = 0
        self.shake_end = None
        self.shake_duration = 1
        self.shake = Point(0,0)
        self.last_update   = globals.time

    def NoTarget(self):
        self.target        = None
        self.target_change = None
        self.start_point   = None
        self.target_time   = None
        self.start_time    = None

    @property
    def pos(self):
        return self._pos + self.shake

    def Set(self,point):
        self._pos = point.to_int()
        self.NoTarget()

    def ScreenShake(self,duration):
        self.shake_end = globals.time + duration
        self.shake_duration = float(duration)

    def SetTarget(self,point,t,rate=2,callback = None):
        #Don't fuck with the view if the player is trying to control it
        rate /= 4.0
        self.follow        = None
        self.follow_start  = 0
        self.follow_locked = False
        self.target        = point.to_int()
        self.target_change = self.target - self._pos
        self.start_point   = self._pos
        self.start_time    = t
        self.duration      = self.target_change.length()/rate
        self.callback      = callback
        if self.duration < 200:
            self.duration  = 200
        self.target_time   = self.start_time + self.duration

    def Follow(self,t,actor):
        """
        Follow the given actor around.
        """
        self.follow        = actor
        self.follow_start  = t
        self.follow_locked = False

    def HasTarget(self):
        return self.target != None

    def Skip(self):
        self._pos = self.target
        self.NoTarget()
        if self.callback:
            self.callback(self.t)
            self.callback = None

    def Update(self,t):
        try:
            return self.update(t)
        finally:
            self._pos = self._pos.to_int()

    def update(self,t):
        self.t = t
        elapsed = t - self.last_update
        self.last_update = t
        
        if self.shake_end:
            if t >= self.shake_end:
                self.shake_end = None
                self.shake = Point(0,0)
            else:
                left = (self.shake_end - t)/self.shake_duration
                radius = left*self.shake_radius
                self.shake = Point(random.random()*radius,random.random()*radius)

        if self.follow:
            #We haven't locked onto it yet, so move closer, and lock on if it's below the threshold
            fpos = (self.follow.GetPosCentre()*globals.tile_dimensions).to_int() + globals.screen*Point(0,0.1)
            if not fpos:
                return
            target = fpos - (globals.screen*0.5).to_int()
            diff = target - self._pos
            #print diff.SquareLength(),self.follow_threshold
            direction = diff.direction()
            
            if abs(diff.x) < self.max_away.x and abs(diff.y) < self.max_away.y:
                adjust = diff*0.02*elapsed*0.06
            else:
                adjust = diff*0.03*elapsed*0.06
            #adjust = adjust.to_int()
            if adjust.x == 0 and adjust.y == 0:
                adjust = direction
            self._pos += adjust
            return
                
        elif self.target:
            if t >= self.target_time:
                self._pos = self.target
                self.NoTarget()
                if self.callback:
                    self.callback(t)
                    self.callback = None
            elif t < self.start_time: #I don't think we should get this
                return
            else:
                partial = float(t-self.start_time)/self.duration
                partial = partial*partial*(3 - 2*partial) #smoothstep
                self._pos = (self.start_point + (self.target_change*partial)).to_int()


class TileTypes:
    AIR                 = 1
    GRASS               = 2
    PLAYER              = 3
    ZOMBIE              = 4
    ROCK                = 5
    LADDER              = 6
    LADDER_TOP          = 7
    TILE                = 8
    ROCK_FLOOR          = 9
    SIGN1               = 10
    AXE                 = 11
    PISTOL              = 12
    BULLETS             = 13
    HEALTH              = 14
    MUTANT_ZOMBIE       = 15
    MISSILE             = 16
    MISSILE_IMPASSABLE  = 17
    Impassable          = set((GRASS,ROCK,ROCK_FLOOR,MISSILE_IMPASSABLE))
    Ladders             = set((LADDER_TOP,LADDER))
    LadderTops          = set((LADDER_TOP,))

class TileData(object):
    texture_names = {TileTypes.GRASS         : 'grass.png',
                     TileTypes.PLAYER        : 'grass.png',
                     TileTypes.ZOMBIE        : 'grass.png',
                     TileTypes.ROCK          : 'rock.png',
                     TileTypes.LADDER        : 'ladder.png',
                     TileTypes.TILE          : 'tile.png',
                     TileTypes.ROCK_FLOOR    : 'rock_floor.png',
                     TileTypes.SIGN1         : 'sign1.png',
                     TileTypes.AXE           : 'tile.png',
                     TileTypes.PISTOL        : 'tile.png',
                     TileTypes.HEALTH        : 'tile.png',
                     TileTypes.BULLETS       : 'tile.png',
                     TileTypes.MUTANT_ZOMBIE : 'tile.png',
                     TileTypes.MISSILE       : 'missile.png',
                     TileTypes.MISSILE_IMPASSABLE : 'missile.png',
                     TileTypes.LADDER_TOP    : 'ladder.png'}

    def __init__(self,type,pos):
        self.pos  = pos
        self.type = type
        self.actors = {}
        try:
            self.name = self.texture_names[type]
        except KeyError:
            self.name = self.texture_names[TileTypes.GRASS]
        #How big are we?
        self.size = Point(1,1)
        self.tex_size = (globals.atlas.SubimageSprite(self.name).size)/globals.tile_dimensions

        #what tcs do we want?
        full_tc = globals.atlas.TextureSpriteCoords(self.name)
        
        bl_tc = Point(pos.x%self.tex_size.x,pos.y%self.tex_size.y)/(self.tex_size.to_float())
        tr_tc = bl_tc + Point(1,1)/(self.tex_size.to_float())

        full_tc_size = (full_tc[2][0]-full_tc[0][0],full_tc[2][1]-full_tc[0][1])

        tc = [[full_tc[0][0] + bl_tc[0]*full_tc_size[0],full_tc[0][1] + bl_tc[1]*full_tc_size[1]],
              [full_tc[0][0] + bl_tc[0]*full_tc_size[0],full_tc[0][1] + tr_tc[1]*full_tc_size[1]],
              [full_tc[0][0] + tr_tc[0]*full_tc_size[0],full_tc[0][1] + tr_tc[1]*full_tc_size[1]],
              [full_tc[0][0] + tr_tc[0]*full_tc_size[0],full_tc[0][1] + bl_tc[1]*full_tc_size[1]]]
        
        #print tc

        self.quad = drawing.Quad(globals.quad_buffer,tc = tc)
        bl        = pos * globals.tile_dimensions
        tr        = bl + self.size*globals.tile_dimensions
        self.quad.SetVertices(bl,tr,0)
    def Delete(self):
        self.quad.Delete()
    def Interact(self,player):
        pass
    def AddActor(self,actor):
        self.actors[actor] = True

    def RemoveActor(self,actor):
        try:
            del self.actors[actor]
        except KeyError:
            pass

class TileDataAir(TileData):
    def __init__(self,type,pos):
        self.type = type
        self.pos = pos
        self.actors = {}
        self.name = 'air'
        self.size = Point(1,1)

    def Delete(self):
        pass

    def Interact(self,player):
        pass


def TileDataFactory(map,type,pos):
    if type in (TileTypes.AIR,TileTypes.PLAYER):
        return TileDataAir(type,pos)
    if type in (TileTypes.ZOMBIE,TileTypes.MUTANT_ZOMBIE) and naked_zombie:
        return TileDataAir(type,pos)
    return TileData(type,pos)

class GameMap(object):
    input_mapping = {' ' : TileTypes.AIR,
                     '-' : TileTypes.GRASS,
                     '.' : TileTypes.ROCK,
                     't' : TileTypes.TILE,
                     'l' : TileTypes.LADDER,
                     'L' : TileTypes.LADDER_TOP,
                     'p' : TileTypes.PLAYER,
                     '+' : TileTypes.ROCK_FLOOR,
                     's' : TileTypes.SIGN1,
                     'x' : TileTypes.AXE,
                     'P' : TileTypes.PISTOL,
                     'b' : TileTypes.BULLETS,
                     'h' : TileTypes.HEALTH,
                     'z' : TileTypes.ZOMBIE,
                     'm' : TileTypes.MISSILE,
                     'M' : TileTypes.MISSILE_IMPASSABLE,
                     'Z' : TileTypes.MUTANT_ZOMBIE,}
    def __init__(self,name,parent):
        global naked_zombie
        self.size   = Point(128,92)
        self.data   = [[TileTypes.AIR for i in xrange(self.size.y)] for j in xrange(self.size.x)]
        self.object_cache = {}
        self.object_list = []
        self.actors = []
        self.doors  = []
        self.player = None
        self.parent = parent
        tc = globals.atlas.TextureSpriteCoords('sky.png')
        sky_size = globals.atlas.SubimageSprite('sky.png').size
        tc_repeat = self.size.y*globals.tile_dimensions.y/sky_size.y
        self.sky_quads = []
        for i in xrange(tc_repeat):
            q = drawing.Quad(globals.quad_buffer,tc = tc)
            bl        = (Point(0,self.size.y-8)*globals.tile_dimensions) + Point(i*sky_size.x,0)
            tr        = bl + sky_size
            q.SetVertices(bl,tr,-0.1)
            self.sky_quads.append(q)

        y = self.size.y - 1
        with open ('level.txt') as f:
            for line in f:
                line = line.strip('\n')
                if len(line) < self.size.x:
                    line += ' '*(self.size.x - len(line))
                if len(line) > self.size.x:
                    line = line[:self.size.x]
                for inv_x,tile in enumerate(line[::-1]):
                    x = self.size.x-1-inv_x
                    #try:
                    if self.input_mapping[tile] in [TileTypes.ZOMBIE,TileTypes.MUTANT_ZOMBIE]:
                        print x,y,self.data[x+1][y].name
                        TileData.texture_names[TileTypes.ZOMBIE] = self.data[x+1][y].name
                        TileData.texture_names[TileTypes.MUTANT_ZOMBIE] = self.data[x+1][y].name
                        if self.data[x+1][y].name == 'air':
                            naked_zombie = True
                        else:
                            naked_zombie = False
                    td = TileDataFactory(self,self.input_mapping[tile],Point(x,y))
                    for tile_x in xrange(td.size.x):
                        for tile_y in xrange(td.size.y):
                            if self.data[x+tile_x][y+tile_y] != TileTypes.AIR:
                                self.data[x+tile_x][y+tile_y].Delete()
                                self.data[x+tile_x][y+tile_y] = TileTypes.AIR
                            if self.data[x+tile_x][y+tile_y] == TileTypes.AIR:
                                self.data[x+tile_x][y+tile_y] = td
                    if self.input_mapping[tile] == TileTypes.PLAYER:
                        self.player = actors.Player(self,Point(x+0.2,y))
                        self.actors.append(self.player)
                    if self.input_mapping[tile] == TileTypes.ZOMBIE:
                        zombie = actors.Zombie(self,Point(x+0.2,y))
                        self.actors.append(zombie)
                    if self.input_mapping[tile] == TileTypes.MUTANT_ZOMBIE:
                        zombie = actors.MutantZombie(self,Point(x+0.2,y))
                        self.actors.append(zombie)
                    if self.input_mapping[tile] == TileTypes.AXE:
                        axe = actors.AxeItem(self,Point(x+0.2,y))
                        self.actors.append(axe)
                    if self.input_mapping[tile] == TileTypes.PISTOL:
                        pistol = actors.PistolItem(self,Point(x+0.2,y))
                        self.actors.append(pistol)
                    if self.input_mapping[tile] == TileTypes.BULLETS:
                        bullets = actors.BulletsItem(self,Point(x+0.2,y))
                        self.actors.append(bullets)
                    if self.input_mapping[tile] == TileTypes.HEALTH:
                        health = actors.HealthItem(self,Point(x+0.2,y))
                        self.actors.append(health)
                    #except KeyError:
                    #    raise globals.types.FatalError('Invalid map data')
                y -= 1
                if y < 0:
                    break
        for i in xrange(len(self.data)):
            for j in xrange(len(self.data[i])):
                if not isinstance(self.data[i][j],TileData):
                    self.data[i][j] = TileDataAir('air',Point(i,j))

    def Update(self,t):
        for actor in self.actors:
            actor.Update(t)

    def AddObject(self,obj):
        self.object_list.append(obj)
        #Now for each tile that the object touches, put it in the cache
        for tile in obj.CoveredTiles():
            self.object_cache[tile] = obj

    def AddActor(self,pos,actor):
        self.data[pos.x][pos.y].AddActor(actor)

    def RemoveActor(self,pos,actor):
        self.data[pos.x][pos.y].RemoveActor(actor)

    def CreateActor(self,actor):
        self.actors.append(actor)

    def DeleteActor(self,actor):
        self.actors = [act for act in self.actors if act is not actor]

class GameView(ui.RootElement):
    def __init__(self):
        self.atlas = globals.atlas = drawing.texture.TextureAtlas('tiles_atlas_0.png','tiles_atlas.txt')
        self.map = GameMap('level.txt',self)
        self.map.world_size = self.map.size * globals.tile_dimensions
        print self.map.world_size
        self.viewpos = Viewpos(Point(0,self.map.world_size.y-globals.screen.y))
        self.game_over = False 
        
        #pygame.mixer.music.load('music.ogg')
        #self.music_playing = False
        super(GameView,self).__init__(Point(0,0),globals.screen)
        #skip titles for development of the main game
        self.mode = modes.GameMode(self)
        #self.mode = modes.LevelOne(self)
        self.StartMusic()

    def StartMusic(self):
        pass
        #pygame.mixer.music.play(-1)
        #self.music_playing = True

    def Draw(self):
        drawing.ResetState()
        drawing.Translate(-self.viewpos.pos.x,-self.viewpos.pos.y,0)
        drawing.DrawAll(globals.quad_buffer,self.atlas.texture.texture)
        drawing.DrawAll(globals.nonstatic_text_buffer,globals.text_manager.atlas.texture.texture)
        
    def Update(self,t):
        #print self.viewpos.pos
        if self.mode:
            self.mode.Update(t)

        if self.game_over:
            return
            
        self.t = t
        self.viewpos.Update(t)
        if self.viewpos.pos.x < 0:
            self.viewpos.pos.x = 0
        if self.viewpos.pos.y < 0:
            self.viewpos.pos.y = 0
        if self.viewpos.pos.x > (self.map.world_size.x - globals.screen.x):
            self.viewpos.pos.x = (self.map.world_size.x - globals.screen.x)
        if self.viewpos.pos.y > (self.map.world_size.y - globals.screen.y):
            self.viewpos.pos.y = (self.map.world_size.y - globals.screen.y)

        self.map.Update(t)

    def GameOver(self):
        self.game_over = True
        self.mode = modes.GameOver(self)
        
    def KeyDown(self,key):
        self.mode.KeyDown(key)

    def KeyUp(self,key):
        if key == pygame.K_DELETE:
            if self.music_playing:
                self.music_playing = False
                pygame.mixer.music.set_volume(0)
            else:
                self.music_playing = True
                pygame.mixer.music.set_volume(1)
        self.mode.KeyUp(key)

    def MouseButtonDown(self,pos,button):
        if self.mode:
            pos = self.viewpos.pos + pos
            return self.mode.MouseButtonDown(pos,button)
        else:
            return False,False

    def MouseMotion(self,pos,rel,handled):
        #print 'mouse',pos
        #if self.selected_player != None:
        #    self.selected_player.MouseMotion()
        screen_pos = self.viewpos.pos + pos
        self.mode.MouseMotion(screen_pos,rel)

        return super(GameView,self).MouseMotion(pos,rel,handled)



