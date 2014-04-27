from globals.types import Point
import globals
import ui
import drawing
import os
import game_view
import random
import pygame
import cmath
import math

class Directions:
    UP    = 0
    DOWN  = 1
    RIGHT = 2
    LEFT  = 3

class Animation(object):
    num_frames = 8
    def __init__(self,texture,name,item,fps):
        self.texture = texture
        self.name = name
        self.fps = fps
        self.still_tc = globals.atlas.TextureSpriteCoords('%s_%s_%s.png' % (self.texture,self.name,item))
        if name in ('left','right'):
            self.attack_tc = globals.atlas.TextureSpriteCoords('%s_%s_%s_attack.png' % (self.texture,self.name,item))
        else:
            self.attack_tc = self.still_tc

        self.start = 0
        self.tcs = []
        flip = False
        for i in xrange(self.num_frames):
            try:
                self.tcs.append(globals.atlas.TextureSpriteCoords('%s_%s_walk_%s_%d.png' % (self.texture,item,name,i)))
            except KeyError:
                self.tcs.append(globals.atlas.TextureSpriteCoords('%s_%s_walk_right_%d.png' % (self.texture,item,i)))
                flip = True
            
        new_tcs = range(self.num_frames)
        if self.name != 'right' and flip:
            for i in xrange(self.num_frames):
                #flip the x-coords...
                j = self.num_frames - 1 - i
                new_tcs[i] = [self.tcs[j][3],self.tcs[j][2],self.tcs[j][1],self.tcs[j][0]]

            self.tcs = new_tcs

    def SetStart(self,x):
        self.start = x

    def GetTc(self,still,x):
        if still:
            return self.still_tc
        elapsed = (x - self.start)*0.125
        frame = int((elapsed*self.fps)%self.num_frames)
        return self.tcs[frame]

class GunAnimation(Animation):
    num_frames = 8
    current_still = 0
    def __init__(self,texture,name,item,fps):
        self.texture = texture
        self.name    = name
        self.item    = item
        self.fps     = fps
        if name in ('left','right'):
            self.still_tcs = [globals.atlas.TextureSpriteCoords('%s_%s_%s_%d.png' % (self.texture,self.name,self.item,i)) for i in xrange(5)]
        else:
            self.still_tcs = [globals.atlas.TextureSpriteCoords('%s_%s_%s_%d.png' % (self.texture,'right',self.item,i)) for i in xrange(5)]
        
        self.start = 0
        self.tcs = []
        for i in xrange(self.num_frames):
            self.tcs.append(globals.atlas.TextureSpriteCoords('%s_%s_walk_right_%d.png' % (self.texture,item,i)))

        new_tcs = range(self.num_frames)
        if self.name != 'right':
            for i in xrange(self.num_frames):
                #flip the x-coords...
                j = self.num_frames - 1 - i
                new_tcs[i] = [self.tcs[j][3],self.tcs[j][2],self.tcs[j][1],self.tcs[j][0]]

            self.tcs = new_tcs

    def GetTc(self,still,x):
        if still:
            return self.still_tcs[GunAnimation.current_still]
        elapsed = (x - self.start)*0.125
        frame = int((elapsed*self.fps)%self.num_frames)
        return self.tcs[frame]

class WeaponTypes:
    FIST   = 0
    AXE    = 1
    PISTOL = 2
    
    all = [FIST,AXE,PISTOL]
    guns = [PISTOL]
    names = {FIST : 'fist',
             AXE  : 'axe',
             PISTOL : 'pistol'}

class Weapon(object):
    def __init__(self,player):
        self.player = player
        
    def Fire(self,pos):
        self.end = globals.time + self.duration
        self.save_anim = self.player.dirs[self.player.dir][self.type]
        self.player.quad.SetTextureCoordinates(self.save_anim.attack_tc)
        
    def Update(self,t):
        return True if t > self.end else False

class Gun(Weapon):
    def Fire(self,pos):
        self.end = globals.time + self.duration
        
        print 'boom!'
        bullet = Bullet(self.player.map,self.player.GunPos(),self.player.angle,self.player)
        self.player.map.CreateActor(bullet)

class Fist(Weapon):
    duration = 500
    type = WeaponTypes.FIST

class Axe(Weapon):
    duration = 900
    type = WeaponTypes.AXE
 
class Pistol(Gun):
    duration = 200
    type = WeaponTypes.PISTOL


class Actor(object):
    texture   = None
    width     = None
    height    = None
    threshold = 0.01
    overscan  = Point(1.2,1.05)
    def __init__(self,map,pos):
        self.map  = map
        self.pos = None
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
            self.dirs[dir] = {}
            for weapon_type in self.weapon_types:
                AnimationType = GunAnimation if weapon_type in WeaponTypes.guns else Animation
                self.dirs[dir][weapon_type] = AnimationType(self.texture,name,WeaponTypes.names[weapon_type],self.fps)

        #self.dirs = dict((dir,globals.atlas.TextureSpriteCoords('%s_%s.png' % (self.texture,name))) for (dir,name) in self.dirs)
        self.dir = Directions.RIGHT
        self.quad = drawing.Quad(globals.quad_buffer,tc = self.dirs[self.dir][self.weapon.type].GetTc(0,0))
        self.splat_tc = globals.atlas.TextureSpriteCoords('splat.png')
        self.splat_quad = drawing.Quad(globals.quad_buffer,tc = self.splat_tc)
        self.splat_size = globals.atlas.SubimageSprite('splat.png').size
        self.splat_quad.Disable()
        self.splat_pos = None
        self.splat_end = 0
        self.size = Point(self.width,self.height).to_float()/globals.tile_dimensions
        self.corners = Point(0,0),Point(self.size.x,0),Point(0,self.size.y),self.size
        self.SetPos(pos)
        self.current_sound = None
        self.jumping = False
        self.jumped = False
        self.ResetWalked()
        
        self.attacking = False

    def Damage(self,amount,pos):
        self.splat_pos = pos - self.pos
        self.splat_end = globals.time + 1000
        self.splat_quad.Enable()
        print 'sp',self.splat_pos

    def SetPos(self,pos):
        if self.pos != None:
            bl = self.pos.to_int()
            tr = (self.pos+self.size).to_int()
            for x in xrange(bl.x,tr.x+1):
                for y in xrange(bl.y,tr.y+1):
                    self.map.RemoveActor(Point(x,y),self)
        
        self.pos = pos
        bl = self.pos.to_int()
        tr = (self.pos+self.size).to_int()
        for x in xrange(bl.x,tr.x+1):
            for y in xrange(bl.y,tr.y+1):
                self.map.AddActor(Point(x,y),self)
        over_size = Point(self.width,self.height)*self.overscan
        extra = Point(self.width,self.height)*(self.overscan-Point(1,1))
        bl = (pos*globals.tile_dimensions) - extra/2
        tr = bl + over_size
        bl = bl.to_int()
        tr = tr.to_int()
        self.quad.SetVertices(bl,tr,4)
        if self.splat_pos:
            bl = (self.pos + self.splat_pos)*globals.tile_dimensions
            tr = bl + self.splat_size
            bl = bl.to_int()
            tr = tr.to_int()
            print 'yoyo',bl,tr
            self.splat_quad.SetVertices(bl,tr,5)

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

    def on_ladder(self):
        for x in 0,self.size.x:
            pos = self.pos + Point(x,-self.threshold*2)
            target_tile_y = self.map.data[int(pos.x)][int(pos.y)]
            if target_tile_y.type not in game_view.TileTypes.Ladders:
                return False
        return True

    def Update(self,t):
        if self.attacking:
            finished = self.weapon.Update(t)
            if finished:
                self.attacking = False
        if self.splat_pos and t > self.splat_end:
            self.splat_quad.Disable()
            self.splat_pos = None
        self.Move(t)

    def TriggerCollide(self,target):
        pass

    def Move(self,t):
        if self.last_update == None:
            self.last_update = globals.time
            return
        elapsed = globals.time - self.last_update
        self.last_update = globals.time
        if self.attacking:
            return
        
        if self.on_ground() or self.on_ladder():
            self.move_speed.x += self.move_direction.x*elapsed*0.03
            if self.jumping and not self.jumped:
                self.move_speed.y += self.jump_amount
                self.jumped = True
            self.move_speed.x *= 0.8*(1-(elapsed/1000.0))
        
        self.move_speed.y += globals.gravity*elapsed*0.03
        amount = Point(self.move_speed.x*elapsed*0.03,self.move_speed.y*elapsed*0.03)
        #print self.move_speed,amount
        self.walked += amount.x
        dir = None
        if amount.x > 0:
            dir = Directions.RIGHT
        elif amount.x < 0:
            dir = Directions.LEFT
        if dir != None and dir != self.dir:
            self.dir = dir
            self.dirs[self.dir][self.weapon.type].SetStart(self.walked)

        if abs(amount.x) <  0.0001:
            self.still = True
            amount.x = 0
            self.move_speed.x = 0
        else:
            self.still = False

        self.quad.SetTextureCoordinates(self.dirs[self.dir][self.weapon.type].GetTc(self.still,self.walked))
        
        if self.still:
            self.ResetWalked()

        #check each of our four corners
        for corner in self.corners:
            pos = self.pos + corner
            target_x = pos.x + amount.x
            target_y = pos.y + amount.y
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
                self.TriggerCollide(None)
                
            elif (int(target_x),int(pos.y)) in self.map.object_cache:
                obj = self.map.object_cache[int(target_x),int(pos.y)]
                if obj.Contains(Point(target_x,pos.y)):
                    if amount.x > 0:
                        amount.x = (int(target_x)-pos.x-self.threshold)
                    else:
                        amount.x = (int(target_x)+1-pos.x+self.threshold)
                    target_x = pos.x + amount.x
                    self.TriggerCollide(obj)
            else: 
                for actor in target_tile_x.actors:
                    if actor is self:
                        continue
                    if isinstance(actor,Bullet):
                        actor.TriggerCollide(self)
                        continue
                    if target_x >= actor.pos.x and target_x < actor.pos.x + actor.size.x and pos.y >= actor.pos.y and pos.y < actor.pos.y + actor.size.y:
                        self.TriggerCollide(actor)
                        if amount.x > 0:
                            amount.x = (actor.pos.x-pos.x-self.threshold)
                        else:
                            amount.x = (actor.pos.x+actor.size.x-pos.x+self.threshold)
                        target_x = pos.x + amount.x
                        break

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
            
            if target_tile_y.type in game_view.TileTypes.Impassable | game_view.TileTypes.Ladders:
                if amount.y > 0:
                    amount.y = (int(target_y)-pos.y-self.threshold)
                else:
                    amount.y = (int(target_y)+1+self.threshold-pos.y)
                target_y = pos.y + amount.y
                self.TriggerCollide(None)
                    
            elif (int(pos.x),int(target_y)) in self.map.object_cache:
                obj = self.map.object_cache[int(pos.x),int(target_y)]
                if obj.Contains(Point(pos.x,target_y)):
                    if amount.y > 0:
                        amount.y = (int(target_y)-pos.y-self.threshold)
                    else:
                        amount.y = (int(target_y)+1+self.threshold-pos.y)
                    target_y = pos.y + amount.y
                    self.TriggerCollide(obj)
            else:
                for actor in target_tile_y.actors:
                    if actor is self:
                        continue
                    if isinstance(actor,Bullet):
                        actor.TriggerCollide(self)
                        continue
                    if target_y >= actor.pos.y and target_y < actor.pos.y + actor.size.y and pos.x >= actor.pos.x and pos.x < actor.pos.x + actor.size.x:
                        if amount.y > 0:
                            amount.y = (actor.pos.y-pos.y-self.threshold)
                        else:
                            amount.y = (actor.pos.y+actor.size.y-pos.y+self.threshold)
                        target_y = pos.y + amount.y
                        self.TriggerCollide(actor)
                        break
                
            
        #self.move_speed.y = amount.y
        if amount.y == 0:
            self.move_speed.y = 0
            
        self.SetPos(self.pos + amount)

    def Click(self,pos,button):
        if self.still and not self.attacking:
            self.weapon.Fire(pos)
            self.attacking = True

    def GetPos(self):
        return self.pos

    def ResetWalked(self):
        self.walked = 0

class Player(Actor):
    texture = 'player'
    width = 24/Actor.overscan.x
    height = 32/Actor.overscan.y
    jump_amount = 0.4
    shoulder_pos = Point(10,21).to_float()
    weapon_types = WeaponTypes.all
    fps = 8

    def __init__(self,map,pos):
        self.weapon = Pistol(self)
        self.still = True
        self.angle = 0
        self.gun_pos = Point(14,21)
        super(Player,self).__init__(map,pos)

    def GunPos(self):
        return self.pos + self.gun_pos[self.dir].to_float()/globals.tile_dimensions

    def MouseMotion(self,pos,rel):
        diff = pos - ((self.pos*globals.tile_dimensions) + self.shoulder_pos)
        distance,angle = cmath.polar(complex(diff.x,diff.y))
        #print distance,angle
        if not self.still:
            return
        if abs(angle)*2 > math.pi:
            self.dir = Directions.LEFT
        else:
            self.dir = Directions.RIGHT
        sector = math.pi/16
        if abs(angle) < sector or abs(angle) > sector*15:
            GunAnimation.current_still = 0
            self.gun_pos = {Directions.LEFT : Point(2,22),Directions.RIGHT : Point(23,22)}
        elif (sector*3 < angle < sector*5) or (sector*13 < angle < sector*15):
            GunAnimation.current_still = 1
            self.gun_pos = {Directions.LEFT : Point(-4,28),Directions.RIGHT : Point(24,28)}
        elif (sector*5 < angle < sector*7) or (sector*11 < angle < sector*13):
            GunAnimation.current_still = 2
            self.gun_pos = {Directions.LEFT : Point(4,30),Directions.RIGHT : Point(18,32)}
        elif (sector < -angle < sector*3) or (sector*13 < -angle < sector*15):
            GunAnimation.current_still = 3
            self.gun_pos = {Directions.LEFT : Point(-4,15),Directions.RIGHT : Point(23,16)}
        elif (sector*3 < -angle < sector*5) or (sector*11 < -angle < sector*13):
            GunAnimation.current_still = 4
            self.gun_pos = {Directions.LEFT : Point(1,13),Directions.RIGHT : Point(20,13)}
        self.angle = angle
        #self.dirs[self.dir][self.weapon.type].

    def Damage(self,amount,pos):
        print 'player damaged by',amount

class Bullet(Actor):
    texture = 'bullet'
    width = 1
    height = 1
    damage_amount = 10
    speed = 1

    def __init__(self,map,pos,angle,launcher):
        self.map  = map
        self.pos = None
        self.last_update = None
        self.launcher = launcher
        ms = cmath.rect(self.speed,angle)
        self.move_speed = Point(ms.real,ms.imag)
        self.tc = globals.atlas.TextureSpriteCoords('bullet.png')
        self.quad = drawing.Quad(globals.quad_buffer,tc = self.tc)
        self.quad.Enable()
        self.size = Point(self.width,self.height).to_float()/globals.tile_dimensions
        
        self.SetPos(pos)
        self.current_sound = None
        self.jumping = False
        self.jumped = False
        self.ResetWalked()
        
        self.destroyed = False

    def SetPos(self,pos):
        if self.pos != None:
            self.map.RemoveActor(self.pos.to_int(),self)
        
        self.pos = pos
        self.map.AddActor(self.pos.to_int(),self)
        over_size = Point(self.width,self.height)*self.overscan
        extra = Point(self.width,self.height)*(self.overscan-Point(1,1))
        bl = (pos*globals.tile_dimensions) - extra/2
        tr = bl + over_size
        bl = bl.to_int()
        tr = tr.to_int()
        self.quad.SetVertices(bl,tr,4)

    def Facing(self):
        return 0

    def on_ground(self):
        return False

    def Update(self,t):
        if self.destroyed:
            #remove it from things
            self.map.RemoveActor(self.pos.to_int(),self)
            self.map.DeleteActor(self)
            return
        self.Move(t)

    def Move(self,t):
        if self.last_update == None:
            self.last_update = globals.time
            return
        elapsed = globals.time - self.last_update
        self.last_update = globals.time
        #self.move_speed.y += globals.gravity*elapsed*0.03
        amount = Point(self.move_speed.x*elapsed*0.03,self.move_speed.y*elapsed*0.03)

        target = self.pos + amount
        if target.x >= self.map.size.x:
            self.TriggerCollide(None)
                
        elif target.x < 0:
            self.TriggerCollide(None)

        try:
            target_tile = self.map.data[int(target.x)][int(target.y)]
        except IndexError:
            self.Destroy()
            return
        if target_tile.type in game_view.TileTypes.Impassable:
            self.TriggerCollide(None)

        elif (int(target.x),int(target.y)) in self.map.object_cache:
            obj = self.map.object_cache[int(target.x),int(target.y)]
            if obj.Contains(Point(target.x,target.y)):
                self.TriggerCollide(obj,target)
        else: 
            for actor in target_tile.actors:
                if actor is self or actor is self.launcher:
                    continue
                if target.x >= actor.pos.x and target.x < actor.pos.x + actor.size.x and target.y >= actor.pos.y and target.y < actor.pos.y + actor.size.y:
                    self.TriggerCollide(actor,target)
                    break

        if amount.y == 0:
            self.move_speed.y = 0
            
        self.SetPos(self.pos + amount)

    def Click(self,pos,button):
        pass

    def GetPos(self):
        return self.pos

    def ResetWalked(self):
        pass

    def Destroy(self):
        self.quad.Delete()
        self.destroyed = True
    
    def TriggerCollide(self,target,pos = None):
        if self.destroyed:
            return
        if target != None:
            target.Damage(self.damage_amount,pos if pos != None else self.pos)
        self.Destroy()

class Zombie(Actor):
    texture = 'zombie'
    overscan = Point(1.8,1.05)
    width = 24/overscan.x
    height = 32/overscan.y
    jump_amount = 0
    weapon_types = [WeaponTypes.FIST]
    fps = 24
    def __init__(self,map,pos):
        self.weapon = Fist(self)
        self.speed = 0.02 + random.random()*0.01
        super(Zombie,self).__init__(map,pos)
    

    def Update(self,t):
        #print 'zombie update',t
        #Try moving toward the player
        if self.map.player.pos.x > self.pos.x:
            self.move_direction = Point(self.speed,0)
        else:
            self.move_direction = Point(-self.speed,0)
        super(Zombie,self).Update(t)

    def ResetWalked(self):
        self.walked = random.random()

    def Damage(self,amount,pos):
        print 'Zombie damaged by',amount,pos
        super(Zombie,self).Damage(amount,pos)
