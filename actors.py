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
import modes

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
        self.icon_tc = globals.atlas.TextureSpriteCoords(self.icon)
        
    def SetIconQuad(self,quad):
        quad.SetTextureCoordinates(self.icon_tc)

    def Disturbance(self):
        return Point(0,0)
        
    def Fire(self,pos):
        self.end = globals.time + self.duration
        self.save_anim = self.player.dirs[self.player.dir][self.type]
        self.player.quad.SetTextureCoordinates(self.save_anim.attack_tc)
        target = self.player.pos + self.vectors[self.player.dir] + self.Disturbance()
        
        target_tile = self.player.map.data[int(target.x)][int(target.y)]
        damage = self.damage + (random.random()-0.5)*2*self.variance
        for actor in target_tile.actors:
            if actor is self.player:
                continue
            if target.x >= actor.pos.x and target.x < actor.pos.x + actor.size.x and target.y >= actor.pos.y and target.y < actor.pos.y + actor.size.y:
                actor.Damage(damage,target)
        
    def Update(self,t):
        return True if t > self.end else False

class Gun(Weapon):
    wavery = 0.2
    def Fire(self,pos):
        if self.player.bullets <= 0:
            print 'click!'
            self.end = globals.time
            return
        self.player.AdjustBullets(-1)
        self.end = globals.time + self.duration
        
        print 'boom!'
        fire_angle = self.player.angle + (random.random()-0.5)*self.wavery
        bullet = Bullet(self.player.map,self.player.GunPos(),fire_angle,self.player)
        self.player.map.CreateActor(bullet)

class Fist(Weapon):
    duration = 500
    damage = 10
    variance = 10
    vectors = {Directions.LEFT : Point(-0.2,1.5), Directions.RIGHT: Point(1.5,1.5)}
    icon = 'fist.png'
    type = WeaponTypes.FIST

    def Disturbance(self):
        #sometimes we punch the stomach
        if random.random() < 0.2:
            return Point(0,-0.5)
        else:
            return Point(0,0)
        
class ZombieBite(Fist):
    duration = 1000
    vectors = {Directions.LEFT : Point(-0.4,1.5), Directions.RIGHT: Point(1.5,1.5)}

class Axe(Weapon):
    duration = 700
    damage = 20
    variance = 10
    vectors = {Directions.LEFT : Point(-0.5,1.5), Directions.RIGHT: Point(1.8,1.5)}
    icon = 'axe.png'
    type = WeaponTypes.AXE
 
class Pistol(Gun):
    duration = 200
    icon = 'pistol.png'
    type = WeaponTypes.PISTOL

class Actor(object):
    texture   = None
    width     = None
    height    = None
    threshold = 0.01
    z_adjust  = 0
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
        try:
            self.dead_tc = globals.atlas.TextureSpriteCoords('%s_dead.png' % self.texture)
        except:
            self.dead_tc = self.dirs[self.dir][self.weapon.type].GetTc(0,0)
        self.splat_quad = drawing.Quad(globals.quad_buffer,tc = self.splat_tc)
        self.splat_size = globals.atlas.SubimageSprite('splat.png').size
        self.splat_quad.Disable()
        self.splat_pos = None
        self.splat_end = 0
        self.size = Point(self.width,self.height).to_float()/globals.tile_dimensions
        self.corners = (Point(0,0),
                        Point(0,self.size.y/2.0),
                        Point(self.size.x/2.0,0),
                        Point(self.size.x/2.0,self.size.y),
                        Point(self.size.x,0),
                        Point(self.size.x,self.size.y/2.0),
                        Point(0,self.size.y),
                        self.size)
        self.SetPos(pos)
        self.current_sound = None
        self.jumping = False
        self.jumped = False
        self.ladder = False
        self.ResetWalked()
        self.health = self.initial_health
        self.dead = False
        self.attacking = False

    def Collect(self,owner):
        pass

    def Damage(self,amount,pos):
        self.splat_pos = pos - self.pos
        self.splat_end = globals.time + 1000
        self.splat_quad.Enable()
        self.AdjustHealth(-amount)
        if self.health <= 0:
            self.dead = True
            self.splat_quad.Delete()
            tc = self.dead_tc
            if self.dir == Directions.RIGHT:
                tc = [tc[3],tc[2],tc[1],tc[0]]
            self.quad.SetTextureCoordinates(tc)

    def AdjustHealth(self,amount):
        self.health += amount
        if self.health < 0:
            self.health = 0

    def RemoveFromMap(self):
        if self.pos != None:
            bl = self.pos.to_int()
            tr = (self.pos+self.size).to_int()
            for x in xrange(bl.x,tr.x+1):
                for y in xrange(bl.y,tr.y+1):
                    self.map.RemoveActor(Point(x,y),self)

    def SetPos(self,pos):
        self.RemoveFromMap()
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
        self.quad.SetVertices(bl,tr,4 +self.z_adjust)
        if self.splat_pos:
            bl = (self.pos + self.splat_pos)*globals.tile_dimensions
            tr = bl + self.splat_size
            bl = bl.to_int()
            tr = tr.to_int()
            self.splat_quad.SetVertices(bl,tr,5+self.z_adjust)

    def Facing(self):
        facing = self.pos + (self.size/2) + self.dirs_pos[self.dir]
        return facing.to_int()

    def on_ground(self):
        for x in 0,self.size.x:
            pos = self.pos + Point(x,-self.threshold*2)
            target_tile_y = self.map.data[int(pos.x)][int(pos.y)]
            if target_tile_y.type in game_view.TileTypes.Impassable:
                return True
            for actor in target_tile_y.actors:
                if actor is self or isinstance(actor,Bullet) or isinstance(actor,Collectable):
                    continue
                if pos.x >= actor.pos.x and pos.x <= actor.pos.x + actor.size.x and pos.y > actor.pos.y and pos.y < actor.pos.y + actor.size.y:
                    return True
        return False

    def above_ladder(self):
        for x in 0,self.size.x:
            pos = self.pos + Point(x,-self.threshold*2)
            target_tile_y = self.map.data[int(pos.x)][int(pos.y)]
            if target_tile_y.type not in game_view.TileTypes.Ladders:
                return False
        return True

    def below_ladder(self):
        for x in 0,self.size.x:
            pos = self.pos + Point(x,self.threshold*2)
            target_tile_y = self.map.data[int(pos.x)][int(pos.y)]
            if target_tile_y.type not in game_view.TileTypes.Ladders:
                return False
        return True

    def on_ladder(self):
        return self.above_ladder() or self.below_ladder()

    def Update(self,t):
        if self.dead:
            self.RemoveFromMap()
            self.map.DeleteActor(self)
            return
        if self.attacking:
            finished = self.weapon.Update(t)
            if finished:
                self.attacking = False
        if self.splat_pos and t > self.splat_end:
            self.splat_quad.Disable()
            self.splat_pos = None
        self.Move(t)

    def TriggerCollide(self,target):
        if target:
            target.Collect(self)

    def Move(self,t):
        if self.last_update == None:
            self.last_update = globals.time
            return
        elapsed = globals.time - self.last_update
        self.last_update = globals.time
        if self.attacking:
            return

        #I don't understand why I need this. Occasionally get huge values here. Figure it out later
        if abs(self.move_speed.y) > 0.5:
            self.move_speed.y = 0
        if self.on_ground() or self.on_ladder():
            self.move_speed.x += self.move_direction.x*elapsed*0.03
            if self.jumping and not self.jumped:
                self.move_speed.y += self.jump_amount
                self.jumped = True
            self.move_speed.x *= 0.8*(1-(elapsed/1000.0))

        if self.ladder and not self.above_ladder():
            self.ladder = False

        if self.ladder or (self.on_ladder() and self.move_direction.y != 0):
            #no gravity on the ladder
            self.ladder = True
            self.move_speed.y = self.move_direction.y
        else:
            self.move_speed.y += globals.gravity*elapsed*0.03
        
        amount = Point(self.move_speed.x*elapsed*0.03,self.move_speed.y*elapsed*0.03)
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
                    if isinstance(actor,Collectable):
                        self.TriggerCollide(actor)
                        continue
                    if target_x >= actor.pos.x and target_x < actor.pos.x + actor.size.x and pos.y >= actor.pos.y and pos.y < actor.pos.y + actor.size.y:
                        self.TriggerCollide(actor)
                        if amount.x > 0:
                            new_amount = (actor.pos.x-pos.x-self.threshold)
                        else:
                            new_amount = (actor.pos.x+actor.size.x-pos.x+self.threshold)
                        if abs(new_amount - amount.x) < 0.2:
                            amount.x = new_amount
                        target_x = pos.x + amount.x
                        break

        for corner_i,corner in enumerate(self.corners):
            pos = self.pos + corner
            target_y = pos.y + amount.y
            if target_y >= self.map.size.y:
                target_y = self.map.size.y-self.threshold
                amount.y = target_y - pos.y
            elif target_y < 0:
                amount.y = -pos.y
                target_y = 0
            target_tile_y = self.map.data[int(pos.x)][int(target_y)]
            
            if target_tile_y.type in game_view.TileTypes.Impassable or not self.ladder and target_tile_y.type in game_view.TileTypes.LadderTops:
                if amount.y > 0:
                    amount.y = (int(target_y)-pos.y-self.threshold)
                else:
                    amount.y = (int(target_y)+1+self.threshold-pos.y)
                if amount.y < 0 and self.move_speed.y > 0:
                    #hit our head
                    print 'head'
                    self.move_speed.y = 0
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
                    if isinstance(actor,Collectable):
                        self.TriggerCollide(actor)
                        continue
                    if target_y >= actor.pos.y and target_y < actor.pos.y + actor.size.y and pos.x >= actor.pos.x and pos.x < actor.pos.x + actor.size.x:
                        if amount.y > 0:
                            new_amount = (actor.pos.y-pos.y-self.threshold)
                        else:
                            new_amount = (actor.pos.y+actor.size.y-pos.y+self.threshold)
                        if (abs(new_amount) < 0.2):
                            amount.y = new_amount
                        target_y = pos.y + amount.y
                        self.TriggerCollide(actor)
                        break
                
        #self.move_speed.y = amount.y
        if amount.y == 0:
            self.move_speed.y = 0
            
        self.SetPos(self.pos + amount)

    def Click(self,pos,button):
        if button == 1:
            if self.still and not self.attacking:
                self.weapon.Fire(pos)
                self.attacking = True
        elif button == 4:
            self.SelectNext()
        elif button == 5:
            self.SelectPrev()

    def GetPos(self):
        return self.pos

    def ResetWalked(self):
        self.walked = 0

class Player(Actor):
    texture = 'player'
    width = 24/Actor.overscan.x
    height = 32/Actor.overscan.y
    jump_amount = 0.5
    shoulder_pos = Point(10,21).to_float()
    weapon_types = WeaponTypes.all
    fps = 8
    initial_health = 100

    def __init__(self,map,pos):
        self.bullets = 6
        self.info_box = ui.Box(parent = globals.screen_root,
                               pos = Point(0,0),
                               tr = Point(1,0.08),
                               colour = (0,0,0,0.7))
        self.info_box.health_text = ui.TextBox(self.info_box,
                                               bl = Point(0.8,0),
                                               tr = Point(1,0.7),
                                               text = '\x81:%d' % self.initial_health,
                                               textType = drawing.texture.TextTypes.SCREEN_RELATIVE,
                                               colour = (1,1,0,1),
                                               scale = 3,
                                               alignment = drawing.texture.TextAlignments.CENTRE)
        self.info_box.bullet_text = ui.TextBox(self.info_box,
                                               bl = Point(0.5,0),
                                               tr = Point(1,0.7),
                                               text = '\x82:%d' % self.bullets,
                                               textType = drawing.texture.TextTypes.SCREEN_RELATIVE,
                                               colour = (1,1,0,1),
                                               scale = 3,
                                               alignment = drawing.texture.TextAlignments.CENTRE)
        self.inv_quads = [drawing.Quad(globals.screen_texture_buffer,tc = globals.atlas.TextureSpriteCoords('empty.png')) for i in xrange(3)]
        self.sel_quads = [drawing.Quad(globals.screen_texture_buffer,tc = globals.atlas.TextureSpriteCoords('selected.png')) for i in xrange(3)]
        box_size = 12
        sep_x = int((self.info_box.absolute.size.x*0.15 - box_size*3)/4)
        sep_y = int((self.info_box.absolute.size.y - box_size)/2)
        print self.info_box.absolute.size,sep_x,sep_y
        for i in xrange(3):    
            bl = self.info_box.absolute.bottom_left + Point(self.info_box.absolute.size.x*0.2,0) + Point(((i+1)*sep_x)+(i*box_size),sep_y)
            tr = bl + Point(box_size,box_size)
            print bl,tr
            self.inv_quads[i].SetVertices(bl,tr,9000)
            self.sel_quads[i].SetVertices(bl,tr,9001)
            self.inv_quads[i].Enable()
            self.sel_quads[i].Disable()
        

        self.inventory = [None,None,None]
        self.num_items = 0
        self.current_item = 0
        self.attacking = False
        self.AddItem(Fist(self))
        
        self.weapon = self.inventory[self.current_item]
        self.still = True
        self.angle = 0
        self.gun_pos = Point(14,21)
        self.mouse_pos = Point(0,0)
        
        super(Player,self).__init__(map,pos)
        
    def AddItem(self,item):
        self.inventory[self.num_items] = item
        item.SetIconQuad(self.inv_quads[self.num_items])
        self.num_items += 1
        #auto select the new item
        self.Select(self.num_items-1)

    def Select(self,index):
        if not self.attacking and self.inventory[index]:
            self.sel_quads[self.current_item].Disable()
            self.weapon = self.inventory[index]
            self.current_item = index
            self.sel_quads[self.current_item].Enable()

    def SelectNext(self):
        self.Select((self.current_item + 1)%self.num_items)

    def SelectPrev(self):
        self.Select((self.current_item + self.num_items - 1 )%self.num_items)

    def GunPos(self):
        return self.pos + self.gun_pos[self.dir].to_float()/globals.tile_dimensions

    def MouseMotion(self,pos,rel):
        self.mouse_pos = pos

    def Update(self,t):
        if self.dead:
            globals.current_view.mode = modes.GameOver(globals.current_view)
        self.UpdateMouse(self.mouse_pos,None)
        super(Player,self).Update(t)

    def AdjustHealth(self,amount):
        super(Player,self).AdjustHealth(amount)
        self.info_box.health_text.SetText('\x81:%d' % self.health,colour = (1,1,0,1))

    def AdjustBullets(self,amount):
        self.bullets += amount
        self.info_box.bullet_text.SetText('\x82:%d' % self.bullets,colour = (1,1,0,1))

    def UpdateMouse(self,pos,rel):
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
        globals.current_view.viewpos.ScreenShake(500)
        super(Player,self).Damage(amount,pos)

class Bullet(Actor):
    texture = 'bullet'
    width = 1
    height = 1
    damage_amount = 30
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
        self.quad.SetVertices(bl,tr,4+self.z_adjust)

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

class Collectable(Actor):
    z_adjust = -0.1
    overscan  = Point(1,1)
    def __init__(self,map,pos):
        self.map  = map
        self.pos = None
       
        self.tc = globals.atlas.TextureSpriteCoords(self.texture)
        self.quad = drawing.Quad(globals.quad_buffer,tc = self.tc)
        self.quad.Enable()
        self.size = Point(self.width,self.height).to_float()/globals.tile_dimensions
        
        self.SetPos(pos)
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
        self.quad.SetVertices(bl,tr,4+self.z_adjust)


    def Update(self,t):
        if self.destroyed:
            #remove it from things
            self.map.RemoveActor(self.pos.to_int(),self)
            self.map.DeleteActor(self)
            self.quad.Delete()

    def Move(self,t):
        pass

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

class AxeItem(Collectable):
    texture = 'axe_item.png'
    width = 6
    height = 19

    def Collect(self,owner):
        if isinstance(owner,Player) and not self.destroyed:
            owner.AddItem(Axe(owner))
            self.destroyed = True

class PistolItem(Collectable):
    texture = 'pistol_item.png'
    width = 20
    height = 14

    def Collect(self,owner):
        if isinstance(owner,Player) and not self.destroyed:
            owner.AddItem(Pistol(owner))
            self.destroyed = True

class BulletsItem(Collectable):
    texture = 'bullets_item.png'
    width = 20
    height = 14

    def Collect(self,owner):
        if isinstance(owner,Player) and not self.destroyed:
            owner.AdjustBullets(2)
            self.destroyed = True

class HealthItem(Collectable):
    texture = 'health_item.png'
    width = 20
    height = 14

    def Collect(self,owner):
        if isinstance(owner,Player) and not self.destroyed:
            owner.AdjustHealth(10)
            self.destroyed = True


class Zombie(Actor):
    texture = 'zombie'
    overscan = Point(1.8,1.05)
    width = 24/overscan.x
    height = 32/overscan.y
    jump_amount = 0
    weapon_types = [WeaponTypes.FIST]
    fps = 24
    initial_health = 40
    reaction_time = 500
    reload_time = 2000
    def __init__(self,map,pos):
        self.weapon = ZombieBite(self)
        self.speed = 0.02 + random.random()*0.01
        self.random_walk_end = None
        self.close_trigger = None
        super(Zombie,self).__init__(map,pos)

    def Update(self,t):
        #print 'zombie update',t
        #Try moving toward the player
        if self.random_walk_end:
            if globals.time > self.random_walk_end:
                self.random_walk_end = None

        if not self.random_walk_end:
            diff = self.map.player.pos - self.pos
            if (abs(diff.x) > 10 or abs(diff.y) > 2):
                #Too far away, try a random walk
                self.move_direction = random.choice((Point(self.speed,0),Point(-self.speed,0)))
                self.random_walk_end = globals.time + random.gauss(800,1)
                self.close_trigger = None
            else:
                #walk towards the player
                if self.map.player.pos.x > self.pos.x:
                    self.move_direction = Point(self.speed,0)
                else:
                    self.move_direction = Point(-self.speed,0)
                if self.dir == Directions.LEFT:
                    th = 1.5
                else:
                    th = 1
                if not self.attacking and abs(diff.x) < th:
                    if self.close_trigger and self.close_trigger <= globals.time:
                        self.weapon.Fire(None)
                        self.attacking = True
                    elif self.close_trigger == None:
                        self.close_trigger = globals.time + self.reaction_time
                        print 'yo',self.close_trigger
                if abs(diff.x) >= th:
                    self.close_trigger = None
                        
        super(Zombie,self).Update(t)

    def ResetWalked(self):
        self.walked = random.random()

    def Damage(self,amount,pos):
        rel_pos = (pos-self.pos)/self.size
        if rel_pos.y < 0.65:
            #Zombies take less damage below the head area
            amount *= 0.2
        elif 0.75 <= rel_pos.y < 0.92:
            #headshot!
            amount *= 1.5
        pos.x = self.pos.x + (pos.x-self.pos.x)*0.5
        print 'zd',amount
        super(Zombie,self).Damage(amount,pos)
