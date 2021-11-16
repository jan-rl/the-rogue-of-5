#!/usr/bin/python
# -*- coding: utf-8 -*-
#

import libtcodpy as libtcod
import PyBearLibTerminal as T
import math
import textwrap
import shelve
import time
import random
import re
import string
from collections import defaultdict

import monsters
import items
import tiles
import timer

SUM = 0

SCR = 0
POT = 0
WEA = 0
ARM = 0
BOO = 0
GLA = 0
WAN = 0
RIN = 0


#actual size of the window
SCREEN_WIDTH = 90
SCREEN_HEIGHT = 30

#size of the map
MAP_WIDTH = 90
MAP_HEIGHT = 19

#sizes and coordinates relevant for the GUI
PANEL_HEIGHT = 10
PANEL_WIDTH = SCREEN_WIDTH
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT
MSG_X = 2
MSG_WIDTH = PANEL_WIDTH - MSG_X - 2
MSG_HEIGHT = PANEL_HEIGHT-1
INVENTORY_WIDTH = SCREEN_WIDTH - 40

#parameters for dungeon generator
ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30

FOV_ALGO = 0  #default FOV algorithm
FOV_LIGHT_WALLS = True  #light walls or not

LIMIT_FPS = 20  #20 frames-per-second maximum

FONT_SIZE = 14

NUMBER_FLOORS = 20

ELEMENTS = ['fire','air','water','earth','tangerine']
ELEMENT_COLOR = {
'fire': 'red',
'water': 'blue',
'air': 'sky',
'earth': 'yellow',
'tangerine': 'orange'
}

LEVEL_CAPS = [

0, 
5, 15, 40, 90, 165, 
265, 365, 456, 590, 715, 
840, 990, 1140, 1290, 1490, 
5555

]


#---------------------------------------------------------------------------------------------------------
# class Tile: now in tiles.py module

class Rect:
    #a rectangle on the map. used to characterize a room.
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h

    def center(self):
        center_x = (self.x1 + self.x2) / 2
        center_y = (self.y1 + self.y2) / 2
        return (center_x, center_y)

    def intersect(self, other):
        #returns true if this rectangle intersects with another one
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and
                self.y1 <= other.y2 and self.y2 >= other.y1)

class Object:
#this is a generic object the player, a monster, an item, the stairs
#it's always represented by a character on screen.
    def __init__(self, x, y, z, char, name, color, blocks=False, always_visible=False, fighter=None, ai=None, item=None, equipment=None):
        self.x = x
        self.y = y
        self.z = z
        self.char = char
        self.base_name = name
        self.color = color
        self.blocks = blocks
        self.always_visible = always_visible
        self.fighter = fighter
        if self.fighter:  #let the fighter component know who owns it
            self.fighter.owner = self

        self.ai = ai
        if self.ai:  #let the AI component know who owns it
            self.ai.owner = self

        self.item = item
        if self.item:  #let the Item component know who owns it
            self.item.owner = self      
            
        self.equipment = equipment
        if self.equipment:  #let the Equipment component know who owns it
            self.equipment.owner = self

            #there must be an Item component for the Equipment component to work properly
            if not self.item:    
                self.item = Item()
                self.item.owner = self
              
    @property
    def name(self):  #return actual name, by summing up the possible components
        
        nam = self.base_name
        
        if self.base_name in ident_table:
            if ident_table[self.base_name]:
                nam = ident_table[self.base_name]
        
        if self.equipment:
            if self.equipment.element_enchant:
                nam = nam + ' of ' + self.equipment.element_enchant
            if self.equipment.element_damage:
                nam = nam + ' + ' + str(self.equipment.element_damage)
        
        number = ''
        if self.item and self.item.number > 1:
            number = str(self.item.number) + ' '
        if self.item and self.item.charges:
            nam = nam + ' ' + str(self.item.charges) + '/' + str(self.item.max_charges)
        
        return number + nam
    
    @property
    def color_(self):
        color = self.color
        return color
    
    @property
    def char(self):
        return self.char
    
    def move(self, dx, dy):
        #check if leaving the map
        if self.x + dx < 0 or self.x + dx >= MAP_WIDTH or self.y + dy < 0 or self.y + dy >= MAP_HEIGHT:
            return
            
        #move by the given amount, if the destination is not blocked
        if not is_blocked(self.x + dx, self.y + dy, self.z):
            self.x += dx
            self.y += dy
            
    def move_away_from(self, target_x, target_y):
        #vector from this object to the target, and distance
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)

        #normalize it to length 1 (preserving direction), then round it and
        #convert to integer so the movement is restricted to the map grid
        dx = int(round(dx / distance))
        dy = int(round(dy / distance))
        self.move(-dx, -dy)
                        
    def move_towards(self, target_x, target_y):
        # #vector from this object to the target, and distance
        dx = target_x - self.x
        dy = target_y - self.y
        
        ddx = 0 
        ddy = 0
        if dx > 0:
            ddx = 1
        elif dx < 0:
            ddx = -1
        if dy > 0:
            ddy = 1
        elif dy < 0:
            ddy = -1
        if not is_blocked(self.x + ddx, self.y + ddy, self.z):
            self.move(ddx, ddy)
        else:
            if ddx != 0:
                if not is_blocked(self.x + ddx, self.y, self.z):
                    self.move(ddx, 0)
                    return
            if ddy != 0:
                if not is_blocked(self.x, self.y + ddy, self.z):
                    self.move(0, ddy)
                    return
    
    def distance_to(self, other):
        #return the distance to another object
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)

    def distance(self, x, y):
        #return the distance to some coordinates
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)

    def send_to_back(self):
        #make this object be drawn first, so all others appear above it if they're in the same tile.
        global objects
        objects[self.z].remove(self)
        objects[self.z].insert(0, self)

    def draw(self):
        #only show if it's visible to the player; or it's set to "always visible" and on an explored tile
        
        #invisible monsters are not drawn
        if self.fighter and self != player:
            if self.fighter.invisible:
                if not player.fighter.see_invisible and not player.fighter.telepathy:
                    return
                elif not player.fighter.see_invisible and player.fighter.telepathy:
                    T.color('white')
                    T.print_(self.x, self.y, 'I')
                    return
                
        if (visible_to_player(self.x,self.y) or
                (self.always_visible and map[self.z][self.x][self.y].explored)):
            T.color(self.color)
            T.print_(self.x, self.y, self.char)
            if self.item:
                self.always_visible = True
        elif self.fighter and player.fighter.telepathy:
            T.color('white')
            T.print_(self.x, self.y, 'I')
            
    def clear(self):
        #erase the character that represents this object
        if visible_to_player(self.x,self.y):
            #libtcod.console_put_char_ex(con, self.x, self.y, '.', libtcod.light_grey, libtcod.black)
            T.color('grey')
            T.print_(self.x, self.y, '.')
            
    def delete(self):
        #easy way to trigger removal from object
        #do not leave its ai
        if self.fighter:
            self.fighter = None
        
        for obj in objects[self.z]:
            if obj.fighter:
                if self in obj.fighter.inventory:
                    obj.fighter.inventory.remove(self)
            if self in objects[self.z]:
                objects[self.z].remove(self)
        self.clear()

class Fighter:
    #combat-related properties and methods (monster, player, NPC).
    def __init__(self, hp, damage, armor, wit, strength, spirit, speed=6, xp=0, level=0, hunger=1000, luck=0, temp_invisible=None, weak_spell=None, berserk_potion=None, death_function=None):

        self.base_hp = hp
        self.hp = hp
        
        self.hp_plus = 0 #additional hp granted later in the game
        
        self.base_damage = damage
        self.base_armor = armor
        
        self.base_wit = wit
        self.base_strength = strength
        
        self.base_spirit = spirit
        self.spirit = spirit
        
        self.base_speed = speed
        
        self.xp = xp
        self.level = level
        
        self.hunger = hunger
        
        self.luck = luck
        
        self.temp_invisible = temp_invisible
        self.weak_spell = weak_spell
        
        self.berserk_potion = berserk_potion
        
        self.death_function = death_function
        
        self.skills = []
        self.inventory = []
        self.strike = True
        
    @property
    def max_hp(self):  #return actual max_hp, by summing up the bonuses from all equipped items
        bonus = 0 #sum(equipment.max_hp_bonus for equipment in get_all_equipped(self.owner))
        hp = self.base_hp + self.hp_plus + bonus
        return hp
        
    @property
    def main_damage(self):  #return actual damage, by summing up the bonuses from all equipped items
        bonus = 0
        
        if get_equipped_in_slot('right hand', self.owner) or get_equipped_in_slot('both hands', self.owner):
            try:
                bonus += get_equipped_in_slot('right hand', self.owner).damage_bonus
            except:
                pass
            try:
                bonus += get_equipped_in_slot('both hands', self.owner).damage_bonus
            except:
                pass
        
        #str bonus
        bonus += self.strength / 5
        
        dam = self.base_damage + bonus
        
        if self.weak:
            dam = dam / 2
            
        if self.berserk:
            dam = dam * 2
            
        dam = int(round(dam))
        return dam
    
    @property
    def off_damage(self):  #return actual damage, by summing up the bonuses from all equipped items
        bonus = 0
        
        if get_equipped_in_slot('left hand', self.owner).damage_bonus:
            bonus += get_equipped_in_slot('left hand', self.owner).damage_bonus
        else:
            return 0
            
        #str bonus
        bonus += self.strength / 5

        dam = self.base_damage + bonus
        
        if self.weak:
            dam = dam / 2
        
        if self.berserk:
            dam = dam * 2
            
        dam = int(round(dam))
        return dam
    
    @property
    def armor(self):  #return actual defense, by summing up the bonuses from all equipped items
        bonus = sum(equipment.armor_bonus for equipment in get_all_equipped(self.owner))        
        
        ac = self.base_armor + bonus
        
        if 'armor wearer' in self.skills:
            ac = ac * 2    
        return ac

    @property
    def wit(self):  #return actual max_hp, by summing up the bonuses from all equipped items
        bonus = sum(equipment.wit_bonus for equipment in get_all_equipped(self.owner))
        
        
        if self.weak:
            bonus += 10
        elif self.hunger_status == 'satiated':
            bonus -= 10
        
        wit = self.base_wit + bonus
        if wit < 0:
            wit = 0
            
        return wit
        
    @property
    def strength(self):  #return actual max_hp, by summing up the bonuses from all equipped items
        bonus = sum(equipment.strength_bonus for equipment in get_all_equipped(self.owner))
        
        if self.weak:
            bonus -= 10
        elif self.hunger_status == 'satiated':
            bonus += 10
        
        str = self.base_strength + bonus
       
        if str < 0:
            str = 0
    
        return str
        
    @property
    def weak(self):
        if self.hunger_status == 'weak':
            return True
        elif self.weak_spell:
            return True
        else:
            return False
        
    @property
    def berserk(self):
        if self.berserk_potion:
            return True
        else:
            return False
        
    @property
    def speed(self):
        if self.berserk_potion:
            return self.base_speed - 3
        else:
            return self.base_speed
        
    @property
    def max_spirit(self):  #return actual max_hp, by summing up the bonuses from all equipped items
        bonus = sum(equipment.spirit_bonus for equipment in get_all_equipped(self.owner))
        
        if self.spirit > self.base_spirit + bonus:
            self.spirit = self.base_spirit + bonus
        
        return self.base_spirit + bonus
    
    def change_hunger(self, amount):
        if amount > 0:
            if self.owner == player: 
                #break food conduct
                conducts['conduct4'] = ''
                
        self.hunger += amount
        if self.hunger > 1500:
            self.hunger = 1500
        if self.hunger <= 0:
            self.hunger = 0
    
    def change_luck(self, amount):
        self.luck += amount
        if self.luck > 500:
            self.luck = 500
        if self.luck <= 0:
            self.luck = 0
    
    @property
    def telepathy(self):
        for equipment in get_all_equipped(self.owner):
            if equipment.owner.base_name == 'glasses of telepathy':
                return True
        return False
        
    @property
    def see_invisible(self):
        for equipment in get_all_equipped(self.owner):
            if equipment.owner.base_name == 'lenses of see invisible':
                return True
        return False
        
    @property
    def invisible(self):
        #check for ring
        for equipment in get_all_equipped(self.owner):
            if equipment.owner.base_name == 'ring of invisibility':
                if self.owner == player:
                    if ident_table['ring of invisibility']:
                        identify('ring of invisibility')
                    #break conduct
                    conducts['conduct3'] = ''
                return True
        
        #check temp_invisible (by potion)
        if self.temp_invisible:
            if self.owner == player:
                #break conduct
                conducts['conduct3'] = ''
            return True
    
        return False
        
    @property
    def hunger_status(self):
        if self.hunger >= 1100:
            status = 'satiated'
        elif self.hunger >= 100:
            status = None
        elif self.hunger >= 10:
            status = 'hungry'
        else:
            status = 'weak'
        return status
    
    def attack(self, target):
        #combat system was changed to deterministic, at and pa were commented out for time being
        no_weapon = True    
        
        if self.owner == player:
            word = ' hit '
            word2 = ' miss '
        else:
            word = ' hits '
            word2 = ' misses ' 
        
        main = None
        if get_equipped_in_slot('right hand', self.owner):
            main = get_equipped_in_slot('right hand', self.owner)
        elif get_equipped_in_slot('both hands', self.owner):
            main = get_equipped_in_slot('both hands', self.owner)
        off = None
        test = get_equipped_in_slot('left hand', self.owner)
        if test:
            if test.damage_bonus:
                off = get_equipped_in_slot('left hand', self.owner)
        
        to_hit = 85
        if self.invisible:
            to_hit += 35
        if target.fighter.invisible:
            to_hit -= 35
        
        if main:
            no_weapon = False
            if libtcod.random_get_int(0,0,100) <= to_hit:
                if main.damage_bonus != 0 and target.fighter:
                    message(self.owner.name.capitalize() + word + target.name + ' with '+ main.owner.name +'.')
                    do_phys_damage(self.owner, target, self.main_damage)
                    if main.element_damage != 0 and target.fighter:
                        do_element_damage(self.owner, target, main.element_damage, main.element_enchant)
            else:
                fight_effect(target.x, target.y, 'grey', 'X')
                message(self.owner.name.capitalize() + word2 + target.name + '.')
                
        if not target.fighter: #dead already?
            return
                
        if off: 
            no_weapon = False
            if libtcod.random_get_int(0,0,100) <= to_hit:            
                if off.damage_bonus != 0 and target.fighter:
                    message(self.owner.name.capitalize() + word + target.name + ' with '+ off.owner.name +'.')
                    do_phys_damage(self.owner, target, self.off_damage)
                    if off.element_damage != 0 and target.fighter:
                        do_element_damage(self.owner, target, off.element_damage, off.element_enchant)
            else:
                fight_effect(target.x, target.y, 'grey', 'X')
                message(self.owner.name.capitalize() + word2 + target.name + '.')
        
        if no_weapon:
            #str bonus
            bonus = 0
            bonus += self.strength / 5
            
            dam = self.base_damage + bonus
            
            if self.weak:
                dam = dam / 2
                
            if self.berserk:
                dam = dam * 2
                
            dam = int(round(dam))
            message(self.owner.name.capitalize() + word + target.name + ' with bare hands.')
            do_phys_damage(self.owner, target, dam)
            
    def take_damage(self, damage, type): 
        
        #apply damage if possible
        
        start = self.hp
        
        if damage > 0:
            self.hp -= damage
            if self.owner == player:
                message(self.owner.name.capitalize() + ' get ' + str(damage) + ' ' + type + ' damage.', 'red')
            else:
                message(self.owner.name.capitalize() + ' gets ' + str(damage) + ' ' + type + ' damage.', 'red')
       
        if self.hp < start:
            self.strike = not self.strike
            if self.strike:
                c = '/'
            else:
                c = '\\'
            fight_effect(self.owner.x, self.owner.y, 'red', c)
            self.owner.ai.got_damage = True
        else:
            message('No damage done.', 'grey')
            fight_effect(self.owner.x, self.owner.y, 'grey', self.owner.char)
        
        #check for death. if there's a death function, call it
        if self.hp <= 0:
            self.hp = 0
            function = self.death_function
            if function is not None:
                function(self.owner)
        
    def heal(self, amount):
        #heal by the given amount, without going over the maximum
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp
        
        #negative healing eg by suffocation or invisible
        if self.hp <= 0:
            self.hp = 0
            function = self.death_function
            if function is not None:
                function(self.owner)
        
    def remana(self, amount):
        #heal by the given amount, without going over the maximum
        if amount < 0 and self.spirit <= 0:
            return
        
        self.spirit += amount
        if self.spirit > self.max_spirit:
            self.spirit = self.max_spirit
    
class PlayerAI:
    '''Is actually the one who plays TPB. Needed to be scheduled. Takes keyboard input and calls handle_keys
    Renders screen and exits game, kind of the actual main loop together with play_game.
    '''
    def __init__(self, ticker, speed):
        self.ticker = ticker
        self.speed = speed
        self.ticker.schedule_turn(self.speed, self)
        
    def take_turn(self):
        '''called by scheduler on the players turn, contains the quasi main loop'''
        global key, mouse, fov_recompute
        action_speed = self.owner.fighter.speed
        
        while True:
            render_all()
            T.refresh()
            key = T.read()
            
            player_action = handle_keys()
            
            #regeneration function and hunger
            if player_action != 'didnt-take-turn':
                regenerate(player)
                hunger_turn()
                if game_state != 'dead' and game_state != 'exit':
                    breathe(player)
                equip_check(player)                        
                #check air
                for y in range(MAP_HEIGHT):
                    for x in range(MAP_WIDTH):
                        map[player.z][x][y].refill_air()
                
            if player_action == 'exit' or game_state == 'exit':
                break
                main_menu()
            
            if player_action != 'didnt-take-turn':
                fov_recompute = True
                break
            
        self.ticker.schedule_turn(action_speed, self)
            
def regenerate(target):

    if target.fighter.weak:
        if target.fighter.luck > 499:
            return
        if libtcod.random_get_int(0,0,1000) <= 10 * (5/(target.fighter.luck+1)):
            do_damage(target, 1)
            message(target.name + ' are suffering from being weak.', 'red')
        return

    chance = 3
    if target.fighter.hunger > 1300:
        chance = 10

    if not target.fighter.invisible:
        rate = 1
    else:
        chance = 10
        rate = -1
        
    #normal 5% chance to gain 1 hp per round
    if libtcod.random_get_int(0,0,100) <= chance:
        if rate > 0:            
            if target.fighter.hp < target.fighter.max_hp:            
                target.fighter.heal(rate)
                target.fighter.change_hunger(-10)
        else:
            target.fighter.heal(rate)
            target.fighter.change_hunger(-10)
            message('Invisibility hurts you.')
         
    #normal 5% chance to gain 1 hp per round, armor reduces recovery
    if target.fighter.armor > 5:
        chance -= 2
    if libtcod.random_get_int(0,0,100) <= chance:
        if rate > 0:
            if target.fighter.spirit < target.fighter.max_spirit:            
                target.fighter.remana(rate)
                target.fighter.change_hunger(-10)
        else:
            target.fighter.remana(rate)
            target.fighter.change_hunger(-10)
            message('Invisibility drains your mind.')
        
def hunger_turn():
    chance = 40 - player.fighter.luck / 50
    
    for equipment in get_all_equipped(player):
        if equipment.owner.name == 'hunger ring':
            chance = 100
    
    if libtcod.random_get_int(0,0,100) <= chance:
        player.fighter.change_hunger(-2)
    
def breathe(being):
    
    if not being.fighter:
        return
    
    chance = 80
    
    if being.fighter.luck > 300:
        chance = 40
    
    if not map[being.z][being.x][being.y].air:        
        if libtcod.random_get_int(0,0,100) <= chance:
            message(being.name + ' suffocate.', 'sky')
            fight_effect(being.x, being.y, 'sky', '#')
            do_element_damage(being, being, 1, 'air')
            
def equip_check(target):

    for equipment in get_all_equipped(player):
        #lucky ring increases luck by every turn
        if equipment.owner.name == 'lucky ring':
            target.fighter.change_luck(1)
            
class AIkobold:
    '''AI for a kobold. Schedules the turn depending on speed and decides whether to move or attack.
    '''
    def __init__(self, ticker, speed):
        self.ticker = ticker
        self.speed = speed
        self.ticker.schedule_turn(self.speed, self)
        
        self.seen_player = False
        self.heard_player = False
        self.got_damage = False
    
    def take_turn(self):
        '''checks whether monster and player are still alive, decides on move or attack'''
        #a basic monster takes its turn.
        monster = self.owner
        
        if not monster.fighter: #most likely because monster is dead
            return
        #stop when the player is already dead
        if game_state == 'dead':
            return
        
        self.speed = monster.fighter.speed
        
        #regenerate(monster)
        breathe(monster)
        #equip_check(monster)                        
        
        if not monster.fighter: #most likely because monster is dead by suffocation
            return
        
        inventory = []
        for i in monster.fighter.inventory:
            inventory.append(i.base_name)
            
        #wait if player on different floor 
        if monster.z != player.z:
            self.ticker.schedule_turn(self.speed, self)            
            return
       
        #--------------------------------------------------
        #hear player
        if monster.distance_to(player) < 3:
            self.heard_player = True
        
        #----------------------------------
        #see player
        #player invisible
        if player.fighter.invisible and not (monster.fighter.see_invisible or monster.fighter.telepathy):
            #can you hear him?
            if self.heard_player: #yes
                
                if libtcod.random_get_int(0,0,100) < 25:
                    pass
                elif monster.distance_to(player) < 3:
                    message(monster.name + ' strikes the air close to you.')
                    self.ticker.schedule_turn(self.speed, self)            
                    return
                elif monster.distance_to(player) > 10:
                    self.seen_player = False
                    self.heard_player = False
                    self.ticker.schedule_turn(self.speed, self)            
                    return
            
            else: #no
                self.ticker.schedule_turn(self.speed, self)            
                return
            
        if visible_to_player(monster.x, monster.y):
            self.seen_player = True
       
        #--------------------------------------------------
        
        if visible_to_player(monster.x, monster.y) or self.seen_player or self.heard_player or self.got_damage:
            #move towards player if far away
            if monster.distance_to(player) >= 2:
                (x,y) = monster.x, monster.y
                monster.move_towards(player.x, player.y)
                if monster.x == x and monster.y == y: #not moved?
                    monster.move(libtcod.random_get_int(0,-1,1), libtcod.random_get_int(0,-1,1)) #try again randomly
                
            #close enough, attack! (if the player is still alive.)
            elif player.fighter.hp > 0:
                monster.fighter.attack(player)
            
        #schedule next turn
        self.ticker.schedule_turn(self.speed, self)      
            
class AIgoblin:
    '''AI for a goblin. Schedules the turn depending on speed and decides whether to move or attack or use potions.
    '''
    def __init__(self, ticker, speed):
        self.ticker = ticker
        self.speed = speed
        self.ticker.schedule_turn(self.speed, self)
        
        self.seen_player = False
        self.heard_player = False
        self.got_damage = False
    
    def take_turn(self):
        '''checks whether monster and player are still alive, decides on move or attack'''
        #a basic monster takes its turn.
        monster = self.owner
        
        if not monster.fighter: #most likely because monster is dead
            return
        #stop when the player is already dead
        if game_state == 'dead':
            return
        
        self.speed = monster.fighter.speed
        
        #regenerate(monster)
        breathe(monster)
        #equip_check(monster)                        
        
        if not monster.fighter: #most likely because monster is dead by suffocation
            return
        
        inventory = []
        for i in monster.fighter.inventory:
            inventory.append(i.base_name)
            
        if monster.fighter.hp <= monster.fighter.max_hp / 2 and 'potion of healing' in inventory:
            for item in monster.fighter.inventory:
                if item.base_name == 'potion of healing':
                    item.item.use(monster)
                    return self.ticker.schedule_turn(self.speed, self)
        
        #wait if player on different floor 
        if monster.z != player.z:
            self.ticker.schedule_turn(self.speed, self)            
            return
       
        #--------------------------------------------------
        #hear player
        if monster.distance_to(player) < 3:
            self.heard_player = True
        
        #----------------------------------
        #see player
        #player invisible
        if player.fighter.invisible and not (monster.fighter.see_invisible or monster.fighter.telepathy):
            #can you hear him?
            if self.heard_player: #yes
                
                if libtcod.random_get_int(0,0,100) < 25:
                    pass
                elif monster.distance_to(player) < 3:
                    message(monster.name + ' strikes the air close to you.')
                    self.ticker.schedule_turn(self.speed, self)            
                    return
                elif monster.distance_to(player) > 10:
                    self.seen_player = False
                    self.heard_player = False
                    self.ticker.schedule_turn(self.speed, self)            
                    return
            
            else: #no
                self.ticker.schedule_turn(self.speed, self)            
                return
            
        if visible_to_player(monster.x, monster.y):
            self.seen_player = True
       
        #--------------------------------------------------
        
        if 'potion of invisibility' in inventory and visible_to_player(monster.x, monster.y) and monster.z == player.z:
            r = libtcod.random_get_int(0,0,100)
            if r <= 30:
                for item in monster.fighter.inventory:
                    if item.base_name == 'potion of invisibility':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)
            
        if 'potion of magma' in inventory and visible_to_player(monster.x, monster.y) and monster.z == player.z and not player.fighter.invisible:
            r = libtcod.random_get_int(0,0,100)
            if r <= 20:
                for item in monster.fighter.inventory:
                    if item.base_name == 'potion of magma':
                        item.item.monster_throw(monster, player.x, player.y)
                        return self.ticker.schedule_turn(self.speed, self)
        
        if 'potion of berserk rage' in inventory and visible_to_player(monster.x, monster.y) and monster.z == player.z:
            r = libtcod.random_get_int(0,0,100)
            if r <= 30:
                for item in monster.fighter.inventory:
                    if item.base_name == 'potion of berserk rage':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)
        
        if visible_to_player(monster.x, monster.y) or self.seen_player or self.heard_player or self.got_damage:
            #move towards player if far away
            if monster.distance_to(player) >= 2:
                (x,y) = monster.x, monster.y
                monster.move_towards(player.x, player.y)
                if monster.x == x and monster.y == y: #not moved?
                    monster.move(libtcod.random_get_int(0,-1,1), libtcod.random_get_int(0,-1,1)) #try again randomly
                
            #close enough, attack! (if the player is still alive.)
            elif player.fighter.hp > 0:
                monster.fighter.attack(player)
            
        #schedule next turn
        self.ticker.schedule_turn(self.speed, self)      
            
class AIorc:
    '''AI for an orc. Schedules the turn depending on speed and decides whether to move or attack or use potions or wands.
    '''
    def __init__(self, ticker, speed):
        self.ticker = ticker
        self.speed = speed
        self.ticker.schedule_turn(self.speed, self)
        
        self.seen_player = False
        self.heard_player = False
        self.got_damage = False
    
    def take_turn(self):
        '''checks whether monster and player are still alive, decides on move or attack'''
        #a basic monster takes its turn.
        monster = self.owner
        
        if not monster.fighter: #most likely because monster is dead
            return
        #stop when the player is already dead
        if game_state == 'dead':
            return
        
        self.speed = monster.fighter.speed
        
        #regenerate(monster)
        breathe(monster)
        #equip_check(monster)                        
        
        if not monster.fighter: #most likely because monster is dead by suffocation
            return
        
        inventory = []
        for i in monster.fighter.inventory:
            inventory.append(i.base_name)
            
        if monster.fighter.hp <= monster.fighter.max_hp / 2 and 'potion of healing' in inventory:
            for item in monster.fighter.inventory:
                if item.base_name == 'potion of healing':
                    item.item.use(monster)
                    return self.ticker.schedule_turn(self.speed, self)
        
        #wait if player on different floor 
        if monster.z != player.z:
            self.ticker.schedule_turn(self.speed, self)            
            return
       
        #--------------------------------------------------
        #hear player
        if monster.distance_to(player) < 3:
            self.heard_player = True
        
        #----------------------------------
        #see player
        #player invisible
        if player.fighter.invisible and not (monster.fighter.see_invisible or monster.fighter.telepathy):
            #can you hear him?
            if self.heard_player: #yes
                
                if libtcod.random_get_int(0,0,100) < 25:
                    pass
                elif monster.distance_to(player) < 3:
                    message(monster.name + ' strikes the air close to you.')
                    self.ticker.schedule_turn(self.speed, self)            
                    return
                elif monster.distance_to(player) > 10:
                    self.seen_player = False
                    self.heard_player = False
                    self.ticker.schedule_turn(self.speed, self)            
                    return
            
            else: #no
                self.ticker.schedule_turn(self.speed, self)            
                return
            
        if visible_to_player(monster.x, monster.y):
            self.seen_player = True
        #--------------------------------------------------
        
        add = 0
        if 'range ranger' in self.owner.fighter.skills:
            add += 20
        if 'elementalist' in self.owner.fighter.skills:
            add += 20
        
        if 'potion of invisibility' in inventory and visible_to_player(monster.x, monster.y) and monster.z == player.z:
            r = libtcod.random_get_int(0,0,100)
            if r <= 30:
                for item in monster.fighter.inventory:
                    if item.base_name == 'potion of invisibility':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)
            
        if 'potion of magma' in inventory and visible_to_player(monster.x, monster.y) and monster.z == player.z and not player.fighter.invisible:
            r = libtcod.random_get_int(0,0,100)
            if r <= 20 + add:
                for item in monster.fighter.inventory:
                    if item.base_name == 'potion of magma':
                        item.item.monster_throw(monster, player.x, player.y)
                        return self.ticker.schedule_turn(self.speed, self)
        
        if 'potion of berserk rage' in inventory and visible_to_player(monster.x, monster.y) and monster.z == player.z:
            r = libtcod.random_get_int(0,0,100)
            if r <= 30:
                for item in monster.fighter.inventory:
                    if item.base_name == 'potion of berserk rage':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)
        
        if 'wand of waterjet' in inventory and visible_to_player(monster.x, monster.y) and monster.z == player.z and not player.fighter.invisible:
            r = libtcod.random_get_int(0,0,100)
            if r <= 20 + add:
                for item in monster.fighter.inventory:
                    if item.base_name == 'wand of waterjet':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)
        
        if 'wand of fireball' in inventory and visible_to_player(monster.x, monster.y) and monster.z == player.z:
            r = libtcod.random_get_int(0,0,100)
            if r <= 20 + add:
                for item in monster.fighter.inventory:
                    if item.base_name == 'wand of fireball':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)

        if 'wand of air' in inventory and visible_to_player(monster.x, monster.y) and monster.distance_to(player) < 6:
            r = libtcod.random_get_int(0,0,100)
            if r <= 20:
                for item in monster.fighter.inventory:
                    if item.base_name == 'wand of air':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)
        
        if 'wand of digging' in inventory and visible_to_player(monster.x, monster.y) and monster.distance_to(player) < 5 and (monster.x == player.x or monster.y == player.y) and not player.fighter.invisible:
            r = libtcod.random_get_int(0,0,100)
            if r <= 80 + add:
                for item in monster.fighter.inventory:
                    if item.base_name == 'wand of digging':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)
 
        if visible_to_player(monster.x, monster.y) or self.seen_player or self.heard_player or self.got_damage:
            #move towards player if far away
            if monster.distance_to(player) >= 2:
                (x,y) = monster.x, monster.y
                monster.move_towards(player.x, player.y)
                if monster.x == x and monster.y == y: #not moved?
                    monster.move(libtcod.random_get_int(0,-1,1), libtcod.random_get_int(0,-1,1)) #try again randomly
                
            #close enough, attack! (if the player is still alive.)
            elif player.fighter.hp > 0:
                monster.fighter.attack(player)
            
        #schedule next turn
        self.ticker.schedule_turn(self.speed, self)      
            
class AIhuman:
    '''AI for a human. Schedules the turn depending on speed and decides whether to move or attack.
    '''
    def __init__(self, ticker, speed):
        self.ticker = ticker
        self.speed = speed
        self.ticker.schedule_turn(self.speed, self)
        
        self.seen_player = False
        self.heard_player = False
        self.attacked_player = False
        self.got_damage = False
    
    def take_turn(self):
        '''checks whether monster and player are still alive, decides on move or attack'''
        #a basic monster takes its turn.
        monster = self.owner
        
        if not monster.fighter: #most likely because monster is dead
            return
        #stop when the player is already dead
        if game_state == 'dead':
            return
        
        self.speed = monster.fighter.speed
        
        #regenerate(monster)
        breathe(monster)
        #equip_check(monster)                        
        
        if not monster.fighter: #most likely because monster is dead by suffocation
            return
        
        inventory = []
        for i in monster.fighter.inventory:
            inventory.append(i.base_name)
            
        if monster.fighter.hp <= monster.fighter.max_hp / 2 and 'potion of healing' in inventory:
            for item in monster.fighter.inventory:
                if item.base_name == 'potion of healing':
                    item.item.use(monster)
                    return self.ticker.schedule_turn(self.speed, self)
       
        if 'scroll of enchantment' in inventory:
            for item in monster.fighter.inventory:
                if item.base_name == 'scroll of enchantment':
                    item.item.use(monster)
                    return self.ticker.schedule_turn(self.speed, self)
        
        #wait if player on different floor 
        if monster.z != player.z:
            self.ticker.schedule_turn(self.speed, self)            
            return
       
        #--------------------------------------------------
        #hear player
        if monster.distance_to(player) < 3:
            self.heard_player = True
        
        #----------------------------------
        #see player
        #player invisible
        if player.fighter.invisible and not (monster.fighter.see_invisible or monster.fighter.telepathy):
            #can you hear him?
            if self.heard_player: #yes
                
                if libtcod.random_get_int(0,0,100) < 25:
                    pass
                elif monster.distance_to(player) < 3:
                    message(monster.name + ' strikes the air close to you.')
                    self.ticker.schedule_turn(self.speed, self)            
                    return
                elif monster.distance_to(player) > 10:
                    self.seen_player = False
                    self.heard_player = False
                    self.ticker.schedule_turn(self.speed, self)            
                    return
            
            else: #no
                self.ticker.schedule_turn(self.speed, self)            
                return
            
        if visible_to_player(monster.x, monster.y):
            self.seen_player = True
        #--------------------------------------------------
        #info about the upcoming battle with player
        #can monster damage him in melee?
        
        desperation = 0
        if self.attacked_player and monster.fighter.main_damage < player.fighter.armor:
            if get_equipped_in_slot('right hand', monster):
                if not get_equipped_in_slot('right hand', monster).element_damage:
                    desperation = 30
        
        add = 0
        if 'range ranger' in self.owner.fighter.skills:
            add += 20
        if 'elementalist' in self.owner.fighter.skills:
            add += 20
        
        if 'potion of invisibility' in inventory and visible_to_player(monster.x, monster.y) and monster.z == player.z:
            r = libtcod.random_get_int(0,0,100)
            if r <= 30 + desperation:
                for item in monster.fighter.inventory:
                    if item.base_name == 'potion of invisibility':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)
            
        if 'potion of magma' in inventory and visible_to_player(monster.x, monster.y) and monster.z == player.z and not player.fighter.invisible:
            r = libtcod.random_get_int(0,0,100)
            if r <= 20 + desperation + add:
                for item in monster.fighter.inventory:
                    if item.base_name == 'potion of magma':
                        item.item.monster_throw(monster, player.x, player.y)
                        return self.ticker.schedule_turn(self.speed, self)
        
        if 'potion of berserk rage' in inventory and visible_to_player(monster.x, monster.y) and monster.z == player.z:
            r = libtcod.random_get_int(0,0,100)
            if r <= 30:
                for item in monster.fighter.inventory:
                    if item.base_name == 'potion of berserk rage':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)
        
        if 'wand of waterjet' in inventory and visible_to_player(monster.x, monster.y) and monster.z == player.z and not player.fighter.invisible:
            r = libtcod.random_get_int(0,0,100)
            if r <= 20 + desperation + add:
                for item in monster.fighter.inventory:
                    if item.base_name == 'wand of waterjet':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)
        
        if 'wand of fireball' in inventory and visible_to_player(monster.x, monster.y) and monster.z == player.z:
            r = libtcod.random_get_int(0,0,100)
            if r <= 20 + desperation + add:
                for item in monster.fighter.inventory:
                    if item.base_name == 'wand of fireball':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)

        if 'wand of air' in inventory and visible_to_player(monster.x, monster.y) and monster.distance_to(player) < 6:
            r = libtcod.random_get_int(0,0,100)
            if r <= 20:
                for item in monster.fighter.inventory:
                    if item.base_name == 'wand of air':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)
        
        if 'wand of digging' in inventory and visible_to_player(monster.x, monster.y) and monster.distance_to(player) < 5 and (monster.x == player.x or monster.y == player.y) and not player.fighter.invisible:
            r = libtcod.random_get_int(0,0,100)
            if r <= 30 + desperation + add:
                for item in monster.fighter.inventory:
                    if item.base_name == 'wand of digging':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)
 
        if monster.fighter.hp <= monster.fighter.max_hp / 4 and 'scroll of teleport' in inventory:
            for item in monster.fighter.inventory:
                if item.base_name == 'scroll of teleport':
                    item.item.use(monster)
                    return self.ticker.schedule_turn(self.speed, self)
        
        if 'scroll of light' in inventory and visible_to_player(monster.x, monster.y) and monster.distance_to(player) < 3:
            r = libtcod.random_get_int(0,0,100)
            if r <= 100:
                for item in monster.fighter.inventory:
                    if item.base_name == 'scroll of light':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)
 
        if visible_to_player(monster.x, monster.y) or self.seen_player or self.heard_player or self.got_damage:
            #move towards player if far away
            if monster.distance_to(player) >= 2:
                (x,y) = monster.x, monster.y
                monster.move_towards(player.x, player.y)
                if monster.x == x and monster.y == y: #not moved?
                    monster.move(libtcod.random_get_int(0,-1,1), libtcod.random_get_int(0,-1,1)) #try again randomly
                
            #close enough, attack! (if the player is still alive.)
            elif player.fighter.hp > 0:
                monster.fighter.attack(player)
                self.attacked_player = True
            
        #schedule next turn
        self.ticker.schedule_turn(self.speed, self)      
            
class AIelf:
    '''AI for a human. Schedules the turn depending on speed and decides whether to move or attack.
    '''
    def __init__(self, ticker, speed):
        self.ticker = ticker
        self.speed = speed
        self.ticker.schedule_turn(self.speed, self)
        
        self.seen_player = False
        self.heard_player = False
        self.attacked_player = False
        
        self.got_damage = False
        
        self.casted_weaken = False
    
    def take_turn(self):
        '''checks whether monster and player are still alive, decides on move or attack'''
        #a basic monster takes its turn.
        monster = self.owner
        
        if not monster.fighter: #most likely because monster is dead
            return
        #stop when the player is already dead
        if game_state == 'dead':
            return
        
        self.speed = monster.fighter.speed
        
        #regenerate(monster)
        breathe(monster)
        #equip_check(monster)                        
        
        if not monster.fighter: #most likely because monster is dead by suffocation
            return
        
        inventory = []
        for i in monster.fighter.inventory:
            inventory.append(i.base_name)
            
        if monster.fighter.hp <= monster.fighter.max_hp / 2 and 'potion of healing' in inventory:
            for item in monster.fighter.inventory:
                if item.base_name == 'potion of healing':
                    item.item.use(monster)
                    return self.ticker.schedule_turn(self.speed, self)
       
        # if monster.fighter.spirit <= monster.fighter.max_spirit / 2 and 'potion of spirit' in inventory:
            # for item in monster.fighter.inventory:
                # if item.base_name == 'potion of spirit':
                    # item.item.use(monster)
                    # return self.ticker.schedule_turn(self.speed, self)
        
        if 'scroll of enchantment' in inventory:
            for item in monster.fighter.inventory:
                if item.base_name == 'scroll of enchantment':
                    item.item.use(monster)
                    return self.ticker.schedule_turn(self.speed, self)
        
        #wait if player on different floor 
        if monster.z != player.z:
            self.ticker.schedule_turn(self.speed, self)            
            return
       
        #--------------------------------------------------
        #hear player
        if monster.distance_to(player) < 3:
            self.heard_player = True
        
        #----------------------------------
        #see player
        
        #player invisible
        if player.fighter.invisible and not (monster.fighter.see_invisible or monster.fighter.telepathy):
            #can you hear him?
            if self.heard_player: #yes
                
                if libtcod.random_get_int(0,0,100) < 25:
                    pass
                elif monster.distance_to(player) < 3:
                    message(monster.name + ' strikes the air close to you.')
                    self.ticker.schedule_turn(self.speed, self)            
                    return
                elif monster.distance_to(player) > 10:
                    self.seen_player = False
                    self.heard_player = False
                    self.ticker.schedule_turn(self.speed, self)            
                    return
            
            else: #no
                self.ticker.schedule_turn(self.speed, self)            
                return
            
        if visible_to_player(monster.x, monster.y):
            self.seen_player = True
        #--------------------------------------------------
        #info about the upcoming battle with player
        #can monster damage him in melee?
        
        visor = False
        if get_equipped_in_slot('eyes', monster):
            if get_equipped_in_slot('eyes', monster).owner.base_name == 'Xray visor':
                visor = True
        
        desperation = 0
        if (self.attacked_player or visor) and monster.fighter.main_damage < player.fighter.armor:
            if get_equipped_in_slot('right hand', monster):
                if not get_equipped_in_slot('right hand', monster).element_damage:
                    desperation = 30
        
        add = 0
        if 'range ranger' in self.owner.fighter.skills:
            add += 20
        if 'elementalist' in self.owner.fighter.skills:
            add += 20
        
        spell = 0
        if 'spellslinger' in self.owner.fighter.skills:
            spell += 20
        
        if monster.fighter.hp <= monster.fighter.max_hp / 4 and 'scroll of teleport' in inventory:
            for item in monster.fighter.inventory:
                if item.base_name == 'scroll of teleport':
                    item.item.use(monster)
                    return self.ticker.schedule_turn(self.speed, self)
        
        if 'potion of invisibility' in inventory and visible_to_player(monster.x, monster.y) and monster.z == player.z:
            r = libtcod.random_get_int(0,0,100)
            if r <= 30 + desperation:
                for item in monster.fighter.inventory:
                    if item.base_name == 'potion of invisibility':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)
            
        if 'potion of magma' in inventory and visible_to_player(monster.x, monster.y) and monster.z == player.z and not player.fighter.invisible:
            r = libtcod.random_get_int(0,0,100)
            if r <= 20 + desperation + add:
                for item in monster.fighter.inventory:
                    if item.base_name == 'potion of magma':
                        item.item.monster_throw(monster, player.x, player.y)
                        return self.ticker.schedule_turn(self.speed, self)
        
        if 'potion of berserk rage' in inventory and visible_to_player(monster.x, monster.y) and monster.z == player.z:
            r = libtcod.random_get_int(0,0,100)
            if r <= 30:
                for item in monster.fighter.inventory:
                    if item.base_name == 'potion of berserk rage':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)
        
        if 'wand of waterjet' in inventory and visible_to_player(monster.x, monster.y) and monster.z == player.z and not player.fighter.invisible:
            r = libtcod.random_get_int(0,0,100)
            if r <= 20 + desperation + add:
                for item in monster.fighter.inventory:
                    if item.base_name == 'wand of waterjet':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)
        
        if 'wand of fireball' in inventory and visible_to_player(monster.x, monster.y) and monster.z == player.z:
            r = libtcod.random_get_int(0,0,100)
            if r <= 20 + desperation + add:
                for item in monster.fighter.inventory:
                    if item.base_name == 'wand of fireball':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)

        if 'wand of air' in inventory and visible_to_player(monster.x, monster.y) and monster.distance_to(player) < 6:
            r = libtcod.random_get_int(0,0,100)
            if r <= 20 + desperation:
                for item in monster.fighter.inventory:
                    if item.base_name == 'wand of air':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)
        
        if 'wand of digging' in inventory and visible_to_player(monster.x, monster.y) and monster.distance_to(player) < 5 and (monster.x == player.x or monster.y == player.y) and not player.fighter.invisible:
            r = libtcod.random_get_int(0,0,100)
            if r <= 30 + desperation + add:
                for item in monster.fighter.inventory:
                    if item.base_name == 'wand of digging':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)
 
        if 'scroll of light' in inventory and visible_to_player(monster.x, monster.y) and monster.distance_to(player) < 3:
            r = libtcod.random_get_int(0,0,100)
            if r <= 80:
                for item in monster.fighter.inventory:
                    if item.base_name == 'scroll of light':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)
        
        book = get_equipped_in_slot('left hand', monster)
        if book:
            if book.owner.base_name == 'book of sunfire' and monster.distance_to(player) < 5 and visible_to_player(monster.x, monster.y) and monster.fighter.spirit >= 5:
                r = libtcod.random_get_int(0,0,100)
                if r <= 20 + desperation + spell:
                    book.owner.item.spell_function(monster)
                    return self.ticker.schedule_turn(self.speed, self)
            elif book.owner.base_name == 'book of waterjet' and monster.distance_to(player) < 5 and visible_to_player(monster.x, monster.y) and monster.fighter.spirit >= 4:
                r = libtcod.random_get_int(0,0,100)
                if r <= 20 + desperation + spell:
                    book.owner.item.spell_function(monster)
                    return self.ticker.schedule_turn(self.speed, self)
            elif book.owner.base_name == 'book of weakness' and monster.distance_to(player) < 5 and visible_to_player(monster.x, monster.y) and monster.fighter.spirit >= 1:
                r = libtcod.random_get_int(0,0,100)
                if r <= 20 + desperation + spell and not self.casted_weaken:
                    self.casted_weaken = True
                    book.owner.item.spell_function(monster)
                    return self.ticker.schedule_turn(self.speed, self)
            
        if visible_to_player(monster.x, monster.y) or self.seen_player or self.heard_player or self.got_damage:
            #move towards player if far away
            if monster.distance_to(player) >= 2:
                (x,y) = monster.x, monster.y
                monster.move_towards(player.x, player.y)
                if monster.x == x and monster.y == y: #not moved?
                    monster.move(libtcod.random_get_int(0,-1,1), libtcod.random_get_int(0,-1,1)) #try again randomly
                
            #close enough, attack! (if the player is still alive.)
            elif player.fighter.hp > 0:
                monster.fighter.attack(player)
                self.attacked_player = True
            
        #schedule next turn
        self.ticker.schedule_turn(self.speed, self)      
            

class AIzombie:
    '''AI for a human. Schedules the turn depending on speed and decides whether to move or attack.
    '''
    def __init__(self, ticker, speed):
        self.ticker = ticker
        self.speed = speed
        self.ticker.schedule_turn(self.speed, self)
        
        self.seen_player = False
        self.attacked_player = False
        
        self.got_damage = False
        
        self.casted_weaken = False
    
    def take_turn(self):
        '''checks whether monster and player are still alive, decides on move or attack'''
        #a basic monster takes its turn.
        monster = self.owner
        
        if not monster.fighter: #most likely because monster is dead
            return
        #stop when the player is already dead
        if game_state == 'dead':
            return
        
        self.speed = monster.fighter.speed
        
        #regenerate(monster)
        #breathe(monster)
        #equip_check(monster)                        
        
        if not monster.fighter: #most likely because monster is dead by suffocation
            return
        
        inventory = []
        for i in monster.fighter.inventory:
            inventory.append(i.base_name)
       
        #wait if player on different floor 
        if monster.z != player.z:
            self.ticker.schedule_turn(self.speed, self)            
            return
       
        #----------------------------------
        #see player
        
        #player invisible
        if player.fighter.invisible and not (monster.fighter.see_invisible or monster.fighter.telepathy):        
            self.ticker.schedule_turn(self.speed, self)            
            return
        
        if visible_to_player(monster.x, monster.y):
            self.seen_player = True
        #--------------------------------------------------
        #info about the upcoming battle with player
        #can monster damage him in melee?
        
        visor = False
        if get_equipped_in_slot('eyes', monster):
            if get_equipped_in_slot('eyes', monster).owner.base_name == 'Xray visor':
                visor = True
        
        desperation = 0
        if (self.attacked_player or visor) and monster.fighter.main_damage < player.fighter.armor:
            if get_equipped_in_slot('right hand', monster):
                if not get_equipped_in_slot('right hand', monster).element_damage:
                    desperation = 30
        
        add = 0
        if 'range ranger' in self.owner.fighter.skills:
            add += 20
        if 'elementalist' in self.owner.fighter.skills:
            add += 20
        
        spell = 0
        if 'spellslinger' in self.owner.fighter.skills:
            spell += 20
        
        if monster.fighter.hp <= monster.fighter.max_hp / 4 and 'scroll of teleport' in inventory:
            for item in monster.fighter.inventory:
                if item.base_name == 'scroll of teleport':
                    item.item.use(monster)
                    return self.ticker.schedule_turn(self.speed, self)
        
        if 'potion of invisibility' in inventory and visible_to_player(monster.x, monster.y) and monster.z == player.z:
            r = libtcod.random_get_int(0,0,100)
            if r <= 30 + desperation:
                for item in monster.fighter.inventory:
                    if item.base_name == 'potion of invisibility':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)
            
        if 'potion of magma' in inventory and visible_to_player(monster.x, monster.y) and monster.z == player.z and not player.fighter.invisible:
            r = libtcod.random_get_int(0,0,100)
            if r <= 20 + desperation + add:
                for item in monster.fighter.inventory:
                    if item.base_name == 'potion of magma':
                        item.item.monster_throw(monster, player.x, player.y)
                        return self.ticker.schedule_turn(self.speed, self)
        
        if 'potion of berserk rage' in inventory and visible_to_player(monster.x, monster.y) and monster.z == player.z:
            r = libtcod.random_get_int(0,0,100)
            if r <= 30:
                for item in monster.fighter.inventory:
                    if item.base_name == 'potion of berserk rage':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)
        
        if 'wand of waterjet' in inventory and visible_to_player(monster.x, monster.y) and monster.z == player.z and not player.fighter.invisible:
            r = libtcod.random_get_int(0,0,100)
            if r <= 20 + desperation + add:
                for item in monster.fighter.inventory:
                    if item.base_name == 'wand of waterjet':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)
        
        if 'wand of fireball' in inventory and visible_to_player(monster.x, monster.y) and monster.z == player.z:
            r = libtcod.random_get_int(0,0,100)
            if r <= 20 + desperation + add:
                for item in monster.fighter.inventory:
                    if item.base_name == 'wand of fireball':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)

        if 'wand of air' in inventory and visible_to_player(monster.x, monster.y) and monster.distance_to(player) < 6:
            r = libtcod.random_get_int(0,0,100)
            if r <= 20 + desperation:
                for item in monster.fighter.inventory:
                    if item.base_name == 'wand of air':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)
        
        if 'wand of digging' in inventory and visible_to_player(monster.x, monster.y) and monster.distance_to(player) < 5 and (monster.x == player.x or monster.y == player.y) and not player.fighter.invisible:
            r = libtcod.random_get_int(0,0,100)
            if r <= 30 + desperation + add:
                for item in monster.fighter.inventory:
                    if item.base_name == 'wand of digging':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)
 
        if 'scroll of light' in inventory and visible_to_player(monster.x, monster.y) and monster.distance_to(player) < 3:
            r = libtcod.random_get_int(0,0,100)
            if r <= 80:
                for item in monster.fighter.inventory:
                    if item.base_name == 'scroll of light':
                        item.item.use(monster)
                        return self.ticker.schedule_turn(self.speed, self)
        
        book = get_equipped_in_slot('left hand', monster)
        if book:
            if book.owner.base_name == 'book of sunfire' and monster.distance_to(player) < 5 and visible_to_player(monster.x, monster.y) and monster.fighter.spirit >= 5:
                r = libtcod.random_get_int(0,0,100)
                if r <= 20 + desperation + spell:
                    book.owner.item.spell_function(monster)
                    return self.ticker.schedule_turn(self.speed, self)
            elif book.owner.base_name == 'book of waterjet' and monster.distance_to(player) < 5 and visible_to_player(monster.x, monster.y) and monster.fighter.spirit >= 4:
                r = libtcod.random_get_int(0,0,100)
                if r <= 20 + desperation + spell:
                    book.owner.item.spell_function(monster)
                    return self.ticker.schedule_turn(self.speed, self)
            elif book.owner.base_name == 'book of weakness' and monster.distance_to(player) < 5 and visible_to_player(monster.x, monster.y) and monster.fighter.spirit >= 1:
                r = libtcod.random_get_int(0,0,100)
                if r <= 20 + desperation + spell and not self.casted_weaken:
                    self.casted_weaken = True
                    book.owner.item.spell_function(monster)
                    return self.ticker.schedule_turn(self.speed, self)
            
        if visible_to_player(monster.x, monster.y) or self.seen_player or self.got_damage:
            #move towards player if far away
            if monster.distance_to(player) >= 2:
                (x,y) = monster.x, monster.y
                monster.move_towards(player.x, player.y)
                if monster.x == x and monster.y == y: #not moved?
                    monster.move(libtcod.random_get_int(0,-1,1), libtcod.random_get_int(0,-1,1)) #try again randomly
                
            #close enough, attack! (if the player is still alive.)
            elif player.fighter.hp > 0:
                monster.fighter.attack(player)
                self.attacked_player = True
            
        #schedule next turn
        self.ticker.schedule_turn(self.speed, self)      
            
class TempInvisible:
    '''counting down temp invis'''
    def __init__(self, ticker, speed, duration):
        self.ticker = ticker
        self.speed = speed
        self.duration = duration
        self.ticker.schedule_turn(self.speed, self)
        
    def take_turn(self):
        if not self.owner.fighter: #dead?
            return
            
        self.owner.fighter.temp_invisible = True
        
        self.duration -= 1
        
        if self.duration == 0:
            self.owner.fighter.temp_invisible = False
            return 
        
        #schedule next turn
        self.ticker.schedule_turn(self.speed, self)      
            
class TempWeak:
    '''counting down temp weakness from spell'''
    def __init__(self, ticker, speed, duration):
        self.ticker = ticker
        self.speed = speed
        self.duration = duration
        self.ticker.schedule_turn(self.speed, self)
        
    def take_turn(self):
        if not self.owner.fighter: #most likely dead
            return
            
        self.owner.fighter.weak_spell = True
        
        self.duration -= 1
        if self.duration == 0:
            
            self.owner.fighter.weak_spell = False
            return 
        
        #schedule next turn
        self.ticker.schedule_turn(self.speed, self)      
            
class TempBerserk:
    '''counting down temp Berserker rage from potion'''
    def __init__(self, ticker, speed, duration):
        self.ticker = ticker
        self.speed = speed
        self.duration = duration
        self.ticker.schedule_turn(self.speed, self)
        
    def take_turn(self):
        if not self.owner.fighter: #most likely dead
            return
            
        self.owner.fighter.berserk_potion = True
        
        self.duration -= 1
        if self.duration == 0:
            if self.owner == player:
                message(self.owner.name + " are not enraged anymore.")
            else:
                message(self.owner.name + " is not enraged anymore.")
            self.owner.fighter.berserk_potion = False
            return 
        
        #schedule next turn
        self.ticker.schedule_turn(self.speed, self)      
            
class AltarCheck:
    '''checking altar for sacrifices'''
    def __init__(self, ticker, speed):
        self.ticker = ticker
        self.speed = speed
        self.ticker.schedule_turn(self.speed, self)
        
    def take_turn(self):
        altar = self.owner
            
        if not altar.z == player.z:
            return self.ticker.schedule_turn(self.speed, self)
        
        for obj in objects[altar.z]:
            if obj.x == altar.x and obj.y == altar.y and not obj.fighter and not obj == self.owner:
                obj.delete()
                player.fighter.change_luck(50)
                message('Your sacrifice is taken.', 'sky')
        
        #schedule next turn
        self.ticker.schedule_turn(self.speed, self)      
        
class StoneCheck:
    '''checking whether the player has the last artifact'''
    def __init__(self, ticker, speed):
        self.ticker = ticker
        self.speed = speed
        self.ticker.schedule_turn(self.speed, self)
        
    def take_turn(self):
        
        for obj in player.fighter.inventory:
            if obj.base_name == 'The Stone For Kronos':
                message('Your sense a change. Hurry to bring the stone to the surface.', 'yellow')
                revive_corpses()
                player.fighter.luck = 0
                return
                
        #schedule next turn
        self.ticker.schedule_turn(self.speed, self)      
    
def revive_corpses():
    for floor in range(NUMBER_FLOORS-1):
        for obj in objects[floor]:
            if 'remains' in obj.name:
                obj.color = 'white'
                obj.blocks = True
                obj.always_visible = False
                obj.item = None
                        
                if 'kobold' in obj.name:
                    obj.char = 'k'
                    obj.base_name = 'kobold zombie'
                    # creating fighter component
                    fighter_component = Fighter(hp=10, damage=0, armor=0, wit=10, strength=60, spirit=1, speed=5, xp=1, death_function=DEATH_DICT['crumble_to_dust'])                
                    obj.fighter = fighter_component
                    fighter_component.owner = obj
                    
                    ai_component = AIzombie(ticker, speed=5)
                    obj.ai = ai_component
                    ai_component.owner = obj
                
                elif 'goblin' in obj.name:
                    obj.char = 'g'
                    obj.base_name = 'goblin skeleton'
                    # creating fighter component
                    fighter_component = Fighter(hp=15, damage=0, armor=0, wit=10, strength=80, spirit=1, speed=5, xp=1, death_function=DEATH_DICT['crumble_to_dust'])                
                    obj.fighter = fighter_component
                    fighter_component.owner = obj
                    
                    ai_component = AIzombie(ticker, speed=5)
                    obj.ai = ai_component
                    ai_component.owner = obj
                    
                elif 'orc' in obj.name:
                    obj.char = 'o'
                    obj.base_name = 'undead orc'
                    # creating fighter component
                    fighter_component = Fighter(hp=20, damage=0, armor=0, wit=10, strength=100, spirit=1, speed=5, xp=1, death_function=DEATH_DICT['crumble_to_dust'])                
                    obj.fighter = fighter_component
                    fighter_component.owner = obj
                    
                    ai_component = AIzombie(ticker, speed=5)
                    obj.ai = ai_component
                    ai_component.owner = obj
                    
                elif 'human' in obj.name:
                    obj.char = 'H'
                    obj.base_name = 'undead human'
                    # creating fighter component
                    fighter_component = Fighter(hp=20, damage=0, armor=0, wit=10, strength=120, spirit=1, speed=5, xp=1, death_function=DEATH_DICT['crumble_to_dust'])                
                    obj.fighter = fighter_component
                    fighter_component.owner = obj
                    
                    ai_component = AIzombie(ticker, speed=5)
                    obj.ai = ai_component
                    ai_component.owner = obj
                    
                elif 'elf' in obj.name:
                    obj.char = 'E'
                    obj.base_name = 'elven zombie'
                    # creating fighter component
                    fighter_component = Fighter(hp=20, damage=0, armor=0, wit=10, strength=100, spirit=1, speed=5, xp=1, death_function=DEATH_DICT['crumble_to_dust'])                
                    obj.fighter = fighter_component
                    fighter_component.owner = obj
                    
                    ai_component = AIzombie(ticker, speed=5)
                    obj.ai = ai_component
                    ai_component.owner = obj
                    
                    
class AINPC:
    '''AI for a simple NPC. Schedules the turn depending on speed and decides whether to move or attack.
    '''
    def __init__(self, ticker, speed):
        self.ticker = ticker
        self.speed = speed
        self.ticker.schedule_turn(self.speed, self)
        
    def take_turn(self):
        '''checks whether monster and player are still alive, decides on move or attack'''
        #a basic monster takes its turn.
        monster = self.owner
        
        if not monster.fighter: #most likely because monster is dead
            return
        #stop when the player is already dead
        if game_state == 'dead':
            return
        
        #regenerate(monster)
        breathe(monster)
        #equip_check(monster)                        
        
        if not monster.fighter: #most likely because monster is dead by suffocation
            return
        
        #wait if player on different floor 
        if monster.z != player.z:
            self.ticker.schedule_turn(self.speed, self)            
            return
       
        
        #--------------------------------------------------
        for obj in objects[monster.z]:
            if obj.name == 'altar':
                #move towards player if far away
                if monster.distance_to(obj) >= 4:
                    (x,y) = monster.x, monster.y
                    monster.move_towards(obj.x, obj.y)
                    if monster.x == x and monster.y == y: #not moved?
                        monster.move(libtcod.random_get_int(0,-1,1), libtcod.random_get_int(0,-1,1)) #try again randomly
                    
            #close enough, attack! (if the player is still alive.)
                else:
                    monster.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1)) #totally random direction
        
        if monster.fighter.hp < monster.fighter.max_hp: #hurt it and it becomes an enemy
            monster.ai = AIhuman(ticker, 6)
            monster.ai.owner = monster  #tell the new component who owns it
            message('You made ' + monster.name + ' angry!', 'red')
            return
            
        #schedule next turn
        self.ticker.schedule_turn(self.speed, self)      
        
class Item:
    #an item that can be picked up and used.
    def __init__(self, charges=0, stackable=False, number = 1, use_function=None, spell_function=None):

        self.stackable = stackable
        self.number = number
        
        self.charges = charges
        self.max_charges = charges
        
        self.use_function = use_function
        self.spell_function = spell_function
        
    def pick_up(self, picker):
        #add to the player's inventory and remove from the map
        if len(picker.fighter.inventory) >= 26:
            message('Your inventory is full, cannot pick up ' + self.owner.name + '.', 'red')
        else:
            picker.fighter.inventory.append(self.owner)
            self.owner.x = 0
            self.owner.y = 0
            objects[self.owner.z].remove(self.owner)
            message('You picked up a ' + self.owner.name + '!', 'green')
                        
            #check for stack
            if self.stackable:
                for i in picker.fighter.inventory[:-1]:
                    if i.base_name == self.owner.base_name:
                        i.item.number += self.number
                        del picker.fighter.inventory[-1]
                        return


    def drop(self, dropper):
        #special case: if the object has the Equipment component, dequip it before dropping
        if self.owner.equipment:
            self.owner.equipment.dequip(dropper)

        #add to the map and remove from the player's inventory. also, place it at the player's coordinates
        objects[dropper.z].append(self.owner)
        dropper.fighter.inventory.remove(self.owner)
        self.owner.x = dropper.x
        self.owner.y = dropper.y
        self.owner.z = dropper.z
        message(dropper.name + ' dropped a ' + self.owner.name + '.', 'yellow')
        self.owner.send_to_back()
        
    def throw(self, thrower):
        #message('Left-click a target tile to throw the ' + self.owner.name+ ', or right-click to cancel.', 'blue')
        (x, y) = target_tile()
        if x is None or not visible_to_player(x,y): return 'cancelled'
        
        #special case: if the object has the Equipment component, dequip it before throwing
        was_equipped = False
        if self.owner.equipment and self.owner.equipment.is_equipped:
            self.owner.equipment.dequip(thrower)
            was_equipped = True
            
        throw_effect(player.x, player.y, x, y, self.owner.color, self.owner.char)
        
        #add to the map and remove from the player's inventory. also, run animation and place it at the new coordinates
        objects[thrower.z].append(self.owner)
        thrower.fighter.inventory.remove(self.owner)
        self.owner.x = x
        self.owner.y = y
        self.owner.z = thrower.z
        self.owner.send_to_back()
        
        if thrower == player:
            message(thrower.name + ' throw a ' + self.owner.name + '.', 'yellow')
        else:
            message(thrower.name + ' throws a ' + self.owner.name + '.', 'yellow')
        if self.owner.base_name == 'potion of magma': 
            damaged = False
            for i in range(self.number):
                message('The ' + self.owner.name + ' explodes.')
                for obj in objects[thrower.z]:
                    if obj.x == x and obj.y == y and obj.fighter:
                        damage = 20
                        if 'range ranger' in thrower.fighter.skills:
                            damage = damage * 2
                        do_element_damage(thrower, obj, damage, 'fire')
                        damaged = True
                self.owner.delete()
                
                if not damaged:
                    fight_effect(x, y, 'red', '#')
            identify('potion of magma')
        elif self.owner.equipment:
            if self.owner.equipment.damage_bonus and 'range ranger' in thrower.fighter.skills and was_equipped:
                for obj in objects[thrower.z]:
                    if obj.x == x and obj.y == y and obj.fighter:
                        damage = self.owner.equipment.damage_bonus + thrower.fighter.wit / 5
                        do_phys_damage(thrower, obj, damage)
                        if self.owner.equipment.element_damage:
                            do_element_damage(thrower, obj, self.owner.equipment.element_damage, self.owner.equipment.element_enchant)
    
    def monster_throw(self, thrower, x, y):
            
        throw_effect(thrower.x, thrower.y, x, y, self.owner.color, self.owner.char)
        
        #add to the map and remove from the player's inventory. also, run animation and place it at the new coordinates
        objects[thrower.z].append(self.owner)
        thrower.fighter.inventory.remove(self.owner)
        self.owner.x = x
        self.owner.y = y
        self.owner.z = thrower.z
        #self.owner.send_to_back()
        message(thrower.name + ' throws a ' + self.owner.name + '.', 'yellow')
        if self.owner.base_name == 'potion of magma': 
            for i in range(self.number):
                message('The ' + self.owner.name + ' explodes.')
                for obj in objects[thrower.z]:
                    if obj.x == x and obj.y == y and obj.fighter:
                        damage = 10
                        if 'range ranger' in thrower.fighter.skills:
                            damage = damage * 2
                        do_element_damage(thrower, obj, damage, 'fire')
                self.owner.delete()
            identify('potion of magma')
            
    def use(self, user):
        #cannor read scrolls with sunglasses
        if 'scroll' in self.owner.base_name and user == player and get_equipped_in_slot('eyes', player):
            if get_equipped_in_slot('eyes', player).owner.base_name == 'sunglasses of elemental protection':
                message('You cannot read the '+ self.owner.name + ' with sunglasses on.')
                identify('sunglasses of elemental protection')
                return
        
        #just call the "use_function" if it is defined
        if self.use_function is None:
            message('The ' + self.owner.name + ' cannot be used.')
        
        else:
            if self.use_function(user) != 'cancelled':
                if self.stackable and self.number > 1:
                    self.number -= 1
                elif self.charges:    
                    self.charges -= 1
                    if self.charges == 0:
                        if user.fighter: #dead?
                            user.fighter.inventory.remove(self.owner)  #destroy after use, unless it was cancelled for some reason
                else:
                    if user.fighter: #dead?
                        user.fighter.inventory.remove(self.owner)  #destroy after use, unless it was cancelled for some reason
                
    # def monster_use(self, user, x, y):
        # #just call the "use_function" if it is defined
        # if self.use_function(user) != 'cancelled':
            # if self.stackable and self.number > 1:
                # self.number -= 1
            # elif self.charges:    
                # self.charges -= 1
                # if self.charges == 0:
                    # user.fighter.inventory.remove(self.owner)  #destroy after use, unless it was cancelled for some reason
            # else:    
                # user.fighter.inventory.remove(self.owner)  #destroy after use, unless it was cancelled for some reason
            
def do_phys_damage(source, target, damage):
    #deal
    
    if not target.fighter: #most likely dead
        return
    
    #critical attack
    if libtcod.random_get_int(0,0,100) <= source.fighter.luck / 50:
        damage = damage * 2
        if source == player:
            message(source.name + ' execute a critical attack.')
        else:
            message(source.name + ' executes a critical attack.')
    damage = int(round(damage))
    
    armor = target.fighter.armor
    
    #critical block
    bonus = 0
    if 'armor wearer' in target.fighter.skills:
        bonus = 11
    if libtcod.random_get_int(0,0,100) <= target.fighter.luck / 50 + bonus:
        armor = armor * 2
        if target == player:
            message(target.name + ' perform a critical block.')
        else:
            message(target.name + ' performs a critical block.')
    damage -= armor
    
    target.fighter.take_damage(damage, 'physical')
        
def do_element_damage(source, target, damage, element):
    
    if not target.fighter: #most likely dead
        return
    
    #break conduct
    if source == player:
        conducts['conduct1'] = ''
    
    if source.fighter: #still alive?
        if 'elementalist' in source.fighter.skills:
            damage = damage * 2
        
    #check for fire res
    if element == 'fire':
        #if no air, half damage
        if not map[target.z][target.x][target.y].air:
            damage = damage / 2
        
        #check equip
        for equipment in get_all_equipped(target):
            #check ring
            if equipment.owner.base_name == 'ring of fire resistance':
                damage = damage / 2
            #check armor element resist
            if equipment.element_enchant == 'fire':
                damage = damage / 2
            #check armor element weakness
            if equipment.element_enchant == 'water':
                damage = damage * 2

    elif element == 'water':
        #check equip
        for equipment in get_all_equipped(target):
            #check armor element resist
            if equipment.element_enchant == 'water':
                damage = damage / 2
            #check armor element weakness
            if equipment.element_enchant == 'fire':
                damage = damage * 2

    elif element == 'earth':
        #check equip
        for equipment in get_all_equipped(target):
            #check armor element resist
            if equipment.element_enchant == 'earth':
                damage = damage / 2
            #check armor element weakness
            if equipment.element_enchant == 'air':
                damage = damage * 2

    elif element == 'air':
        #check equip
        for equipment in get_all_equipped(target):
            #check armor element resist
            if equipment.element_enchant == 'air':
                damage = damage / 2
            #check armor element weakness
            if equipment.element_enchant == 'earth':
                damage = damage * 2

    elif element == 'tangerine':
        #check equip
        for equipment in get_all_equipped(target):
            #check armor element resist
            if equipment.element_enchant == 'tangerine':
                damage = damage / 2
            
    if get_equipped_in_slot('eyes', target):
        if get_equipped_in_slot('eyes', target).owner.base_name == 'sunglasses of elemental protection':
            damage = damage / 2
        
    # if target.fighter: #still alive
        # if 'armor wearer' in target.fighter.skills:
            # damage -= target.fighter.armor
        
    damage = int(round(damage))
    target.fighter.take_damage(damage, element)
    
def do_damage(target, damage):
    #unspecific uncounterable damage
    damage = int(round(damage))    
    target.fighter.take_damage(damage, '')    
    
        
class Equipment:
    #an object that can be equipped, yielding bonuses. automatically adds the Item component.
    def __init__(self, slot, max_hp_bonus=0, damage_bonus=0, armor_bonus=0, wit_bonus=0, strength_bonus=0, spirit_bonus=0, element_enchant = None, element_damage=0): #, protection=None, enchanted=None):
        
        self.max_hp_bonus = max_hp_bonus
        self.damage_bonus = damage_bonus
        self.armor_bonus = armor_bonus
        self.wit_bonus = wit_bonus
        self.strength_bonus = strength_bonus
        self.spirit_bonus = spirit_bonus
        
        self.element_enchant = element_enchant
        self.element_damage = element_damage
        
        self.slot = slot
        self.is_equipped = False

    def toggle_equip(self, user):  #toggle equip/dequip status
        if self.is_equipped:
            self.dequip(user)
        else:
            self.equip(user)

    def equip(self, owner):
        #always dequip zweihaender if something is put in a hand
        if get_equipped_in_slot('both hands', owner) and (self.slot == 'left hand' or self.slot == 'right hand'):
            get_equipped_in_slot('both hands', owner).dequip(owner)        
        
        #if the slot is already being used, check for dual wield skill and/or dequip whatever is there first
        old_equipment = get_equipped_in_slot(self.slot, owner)
        if old_equipment is not None:
            
            #double dagger
            if old_equipment.damage_bonus and self.owner.base_name == 'dagger' and 'double dagger' in owner.fighter.skills:
                self.slot = 'left hand'
                old_off_equipment = get_equipped_in_slot('left hand', owner)
                if old_off_equipment is not None:
                    old_off_equipment.dequip(owner)        
            
            else:
                old_equipment.dequip(owner)        

        #if equip zweihaender
        if self.slot == 'both hands':
            try:    
                get_equipped_in_slot('right hand', owner).dequip(owner)
            except:
                pass
            try:    
                get_equipped_in_slot('left hand', owner).dequip(owner)
            except:
                pass
        
        #equip object and show a message about it
        self.is_equipped = True
        #message('Equipped ' + self.owner.name + ' on ' + self.slot + '.', 'light green')

    def dequip(self, user):
        #dequip object and show a message about it
        if not self.is_equipped: return
        
        
        if self.owner.base_name == 'dagger':
            self.slot = 'right hand'
        
        self.is_equipped = False
        #message('Dequipped ' + self.owner.name + ' from ' + self.slot + '.', libtcod.light_yellow)
        

def get_equipped_in_slot(slot, owner):  #returns the equipment in a slot, or None if it's empty
    for obj in owner.fighter.inventory:
        if obj.equipment and obj.equipment.slot == slot and obj.equipment.is_equipped:
            return obj.equipment
    return None

def get_all_equipped(wearer):  #returns a list of equipped items someone wears
    equipped_list = []
    for item in wearer.fighter.inventory:
        if item.equipment and item.equipment.is_equipped:
            equipped_list.append(item.equipment)
    return equipped_list

    
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
def make_map():
    global map, special_dict
    #general function for decision, which map to make
    #print direction,dungeon_level, 'DEBUG'
    
    #determine location of special rooms
    numbers = []
    for i in range(3,15):
        numbers.append(i)
    random.shuffle(numbers)
    random.shuffle(numbers)
    
    s_rooms = ['tangerine', 'temple', 'fountain', 'house', 'library']
    special_dict = {
    'tangerine': 0,
    'temple': 0,
    'fountain': 0,
    'house': 0,
    'library': 0
    }
    
    for i in range(5):
        special_dict[s_rooms[i]] = numbers[i]
    
    #------------------------------------------
    #make the map
    map = []
    for i in range(NUMBER_FLOORS):
        map.append(make_random_rl_map(i))
        
    #------------------------------------------
    #improvement statistics on distribution
    # print 'Ring: ',RIN
    # print 'Wand: ',WAN
    # print 'Weapons: ',WEA
    # print 'Armor: ',ARM
    # print 'Books: ',BOO
    # print 'Scroll: ',SCR
    # print 'Glasses: ',GLA
    # print 'Ption: ',POT

def is_blocked(x, y, z):
    try:
        #first test the map tile
        if map[z][x][y].blocked:
            return True
        #now check for any blocking objects
        for object in objects[z]:
            if object.blocks and object.x == x and object.y == y:
                return True
    except: # most of the times things outside the map
        return True
    
    return False

def create_room(room, map):
    #go through the tiles in the rectangle and make them passable
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            map[x][y].change_type('empty')
    
    #create the outter walls
    for x in range(room.x1, room.x2+1):
        if map[x][room.y1].type == 'rock wall':
            map[x][room.y1].change_type('horizontal wall')
        if map[x][room.y2].type == 'rock wall':
            map[x][room.y2].change_type('horizontal wall')
    
    for y in range(room.y1, room.y2+1):
        if map[room.x1][y].type == 'rock wall':
            map[room.x1][y].change_type('vertical wall')
        if map[room.x2][y].type == 'rock wall':
            map[room.x2][y].change_type('vertical wall')
    
    return map
                      
def create_h_tunnel(x1, x2, y, map):
    #horizontal tunnel. min() and max() are used in case x1>x2
    for x in range(min(x1, x2), max(x1, x2) + 1):
        map[x][y].change_type('empty')
    return map
        
def create_v_tunnel(y1, y2, x, map):
    #vertical tunnel
    for y in range(min(y1, y2), max(y1, y2) + 1):
        map[x][y].change_type('empty')
    return map
  
            
def get_map_char(location_name, x, y):
    i = getattr(maps, location_name) #this is maps.temple and would give maps.temple[y][x] == '+'
    return i[y][x]
                
def make_preset_map(location_name):
    temp = []
    
    #fill map with tiles according to preset maps.py (objects kept blank)
    temp = [[ tiles.Tile(True, type = maps.char_to_type( get_map_char(location_name, x, y ) ) )
             for y in range(MAP_HEIGHT) ]
           for x in range(MAP_WIDTH) ]  
           
    return temp

def place_preset_objects(z, location_name):
    pass
                
def make_random_rl_map(z):
    global stairs, upstairs
    
    #fill map with "blocked wall" tiles
    temp = [[ tiles.Tile(True, type = 'rock wall')
             for y in range(MAP_HEIGHT) ]
           for x in range(MAP_WIDTH) ]
           
    rooms = []
    num_rooms = 0

    for r in range(MAX_ROOMS):
        #random width and height
        w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        #random position without going out of the boundaries of the map
        x = libtcod.random_get_int(0, 0, MAP_WIDTH - w - 1)
        y = libtcod.random_get_int(0, 0, MAP_HEIGHT - h - 1)

        #"Rect" class makes rectangles easier to work with
        new_room = Rect(x, y, w, h)

        #run through the other rooms and see if they intersect with this one
        failed = False
        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                break

        if not failed: #THIS??????
        
            #this means there are no intersections, so this room is valid

            #"paint" it to the map's tiles
            temp = create_room(new_room, temp)
            
            #add some contents to this room, such as monsters or special rooms
            
            place_objects(z, new_room)
                
            #center coordinates of new room, will be useful later
            (new_x, new_y) = new_room.center()

            if num_rooms == 0:
                
                #create upstairs of ladder at the players starting position
                upstairs = Object(new_x, new_y, z, '<', 'upstairs', 'white', always_visible=True)
                objects[z].append(upstairs)
                upstairs.send_to_back()  #so it's drawn below the monsters
                
            else:
                #all rooms after the first:
                #connect it to the previous room with a tunnel

                #center coordinates of previous room
                (prev_x, prev_y) = rooms[num_rooms-1].center()

                #draw a coin (random number that is either 0 or 1)
                if libtcod.random_get_int(0, 0, 1) == 1:
                    #first move horizontally, then vertically
                    temp = create_h_tunnel(prev_x, new_x, prev_y, temp)
                    temp = create_v_tunnel(prev_y, new_y, new_x, temp)
                else:
                    #first move vertically, then horizontally
                    temp = create_v_tunnel(prev_y, new_y, prev_x, temp)
                    temp = create_h_tunnel(prev_x, new_x, new_y, temp)

            #finally, append the new room to the list
            rooms.append(new_room)
            num_rooms += 1
        
        else:
            pass
    
    #create a special room
    for key, value in special_dict.iteritems():
        if value == z:
            make_special_room(z, rooms[len(rooms) / 2], key)
        
    #the coordinates are from the last generated room -> exit room
    xe = libtcod.random_get_int(0,rooms[-1].x1+2, rooms[-1].x2-2)
    ye = libtcod.random_get_int(0,rooms[-1].y1+2, rooms[-1].y2-2)
    if z == 0:      
        o = create_item('the_bottle_of_holy_water', xe, ye, z)
        #o = create_item('the_stone_for_kronos', xe, ye, z)
        objects[z].append(o)
        o.send_to_back()
    elif z == 4:      
        o = create_item('the_golden_tangerine', xe, ye, z)
        objects[z].append(o)
        o.send_to_back()
    elif z == 9:      
        o = create_item('a_frozen_breeze_of_air', xe, ye, z)
        objects[z].append(o)
        o.send_to_back()
    elif z == 14:      
        o = create_item('the_eternal_flame_of_hephaistos', xe, ye, z)
        objects[z].append(o)
        o.send_to_back()
    elif z == 19:
        o = create_item('the_stone_for_kronos', xe, ye, z)
        objects[z].append(o)
        o.send_to_back()
    
    #create stairs at the center of the last room, not on last level
    if z != 19:
        stairs = Object(new_x, new_y, z, '>', 'stairs', 'white', always_visible=True)
        objects[z].append(stairs)
        stairs.send_to_back()  #so it's drawn below the monsters
    #print SUM
    return temp
 
def make_special_room(z, room, type):
    
    if type == 'tangerine':
        for i in range(3):
            o = create_item('potion_of_tangerine_juice', libtcod.random_get_int(0,room.x1+2, room.x2-2), libtcod.random_get_int(0,room.y1+2, room.y2-2), z)
            objects[z].append(o)
            o.send_to_back()
        
    elif type == 'library':
        for i in range(3):
            list = ['scroll_of_light', 'scroll_of_teleport', 'scroll_of_enchantment', 'scroll_of_earth', 'scroll_of_identify']
            random.shuffle(list)
            o = create_item(list[0], libtcod.random_get_int(0,room.x1+2, room.x2-2), libtcod.random_get_int(0,room.y1+2, room.y2-2), z)
            objects[z].append(o)
            o.send_to_back()
        r = libtcod.random_get_int(0,1,2)
        for i in range(r):
            list = ['book_of_make_tangerine_potion', 'book_of_healing', 'book_of_sunfire', 'book_of_waterjet', 'book_of_weakness' ]
            random.shuffle(list)
            o = create_item(list[0], libtcod.random_get_int(0,room.x1+2, room.x2-2), libtcod.random_get_int(0,room.y1+2, room.y2-2), z)
            objects[z].append(o)
            o.send_to_back()
            
    elif type == 'house':
        for x in range((room.x2-2) - (room.x1+2)):
            for y in range((room.y2-2) - (room.y1+2)):
                objects[z].append(create_monster('kobold', room.x1+x+1, room.y1+y+1, z))

    elif type == 'fountain':
        (xc, yc) = room.center()
        fountain = create_object('fountain', xc, yc, z)        
        objects[z].append(fountain)
        fountain.always_visible = True
        fountain.always_visible = True
        
 
    elif type == 'temple':
        (xc, yc) = room.center()
        altar = create_object('altar', xc, yc, z)        
        objects[z].append(altar)
        altar.always_visible = True
        check = AltarCheck(ticker, speed=6)
        check.owner = altar
        objects[z].append(create_monster('priest', xc, yc, z))
        
#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

def create_monster(type, x, y, z):
    # storage of data from monsters.py
    a = getattr(monsters, type)
    
    hp = 1
    wit = 0
    str = 0
    
    #randomly distribute stat points to three attributes
    for i in range(a['stat_points']):
        r = libtcod.random_get_int(0,0,100)
        if r <= 33:
            hp += 1
        elif r <= 66:
            wit += 1
        else:
            str += 1
    
    # creating fighter component
    fighter_component = Fighter(hp=hp, damage=0, armor=0, wit=wit, strength=str, spirit=a['spirit'], speed=a['speed'], xp=a['xp'], death_function=DEATH_DICT[a['death_function']])                
    
    #creating ai needs more info because of arguments
    if a['ai'] == 'AIkobold':
        ai_component = AIkobold(ticker, speed=a['speed'])
    elif a['ai'] == 'AIgoblin':
        ai_component = AIgoblin(ticker, speed=a['speed'])
    elif a['ai'] == 'AIorc':
            ai_component = AIorc(ticker, speed=a['speed'])
    elif a['ai'] == 'AIhuman':
            ai_component = AIhuman(ticker, speed=a['speed'])
    elif a['ai'] == 'AIelf':
            ai_component = AIelf(ticker, speed=a['speed'])
    elif a['ai'] == 'AINPC':
            ai_component = AINPC(ticker, speed=a['speed'])

            
    if 'skills' in a:
        skills_m = ['armor wearer', 'double dagger', 'elementalist', 'spell slinger', 'range ranger']
        random.shuffle(skills_m)
        for i in range(a['skills']):
            if libtcod.random_get_int(0,0,100) < 50:
                fighter_component.skills.append(skills_m.pop())
        
    #create the monster    
    monster = Object(x, y, z, a['char'], a['name'], a['color'], blocks=True, fighter=fighter_component, ai=ai_component)
    
    if 'inventory' in a:
        for item in a['inventory']:
            if libtcod.random_get_int(0,0,100) < item[1]:
                if item[0] == 'potion':
                    list = ['potion_of_healing', 'potion_of_berserk_rage', 'potion_of_magma', 'potion_of_tangerine_juice', 'potion_of_invisibility']
                    random.shuffle(list)
                    i = create_item(list[0])
                    monster.fighter.inventory.append(i)
                elif item[0] == 'scroll':
                    list = ['scroll_of_light', 'scroll_of_teleport', 'scroll_of_enchantment']
                    random.shuffle(list)
                    i = create_item(list[0])
                    monster.fighter.inventory.append(i)
                elif item[0] == 'wand':
                    list = ['wand_of_digging', 'wand_of_air', 'wand_of_fireball', 'wand_of_waterjet']
                    random.shuffle(list)
                    i = create_item(list[0])
                    monster.fighter.inventory.append(i)
                elif item[0] == 'ring':
                    list = ['ring_of_fire_resistance', 'ring_of_invisibility', 'hunger_ring', 'lucky_ring', 'ring_of_strength']
                    random.shuffle(list)
                    i = create_item(list[0])
                    monster.fighter.inventory.append(i)
                    i.equipment.equip(monster)
                elif item[0] == 'glasses':
                    list = ['lenses_of_see_invisible', 'sunglasses_of_elemental_protection', 'nerd_glasses', 'glasses_of_telepathy', 'Xray_visor']
                    random.shuffle(list)
                    i = create_item(list[0])
                    monster.fighter.inventory.append(i)
                    i.equipment.equip(monster)
                elif item[0] == 'spellbook':
                    list = ['book_of_sunfire', 'book_of_waterjet', 'book_of_weakness']
                    random.shuffle(list)
                    i = create_item(list[0])
                    monster.fighter.inventory.append(i)
                    i.equipment.equip(monster)
                else:
                    i = create_item(item[0], z = z)
                    monster.fighter.inventory.append(i)
                    if i.equipment:
                        i.equipment.equip(monster)
                            
    return monster
                
def create_item(type, x=0, y=0, z=0): 
    a = getattr(items, type)
    
    if 'equipment' in a:
        equipment_component = Equipment(slot=a['slot'])
        
        for value in a:
            if 'bonus' in value:
                setattr(equipment_component, value, a[value])
    
        if 'element_enchant' in a:
            r = libtcod.random_get_int(0,0,100)
            if r <= z * 3:                
                equipment_component.element_enchant = ELEMENTS[libtcod.random_get_int(0,0,4)]
                if 'damage_bonus' in a:
                    equipment_component.element_damage = libtcod.random_get_int(0,1,5)
        
    else:
        equipment_component = None

    item_component = Item()
    
    if 'stackable' in a:
        item_component.stackable = True
    
    if 'use_function' in a:
        item_component.use_function = globals()[a['use_function']]
    
    if 'spell_function' in a:
        item_component.spell_function = globals()[a['spell_function']]
     
    if 'charges' in a:
        item_component.charges = libtcod.random_get_int(0,1,5)
        item_component.max_charges = item_component.charges
    
    item = Object(x, y, z, a['char'], a['name'], a['color'], item=item_component, equipment=equipment_component)
    
    return item

def create_object(type, x=0, y=0, z=0):
    a = getattr(items, type)
    
    obj = Object(x, y, z, a['char'], a['name'], a['color'] )
   
   
    if 'blocks' in a:
        obj.blocks = a['blocks']
    if 'flammable_prob' in a:
        obj.flammable_prob = a['flammable_prob']
    if 'light_source' in a:
        obj.light_source = a['light_source']
    if 'ignite_function' in a:
        obj.ignite_function = globals()[a['ignite_function']]
    if 'glow' in a:
        obj.glow = a['glow']

    if a['name'] == 'lava':
        set_on_fire(obj,-1, system_call=True)
        
    return obj
    
def generate_name(length=5):
    
    cons = ['b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z']
    voc = ['a', 'e', 'i', 'o', 'u']
    name = []
    
    for i in range(length):
        if i%2==0:
            name.append(cons[libtcod.random_get_int(0,0,len(cons)-1)])
        else:    
            name.append(voc[libtcod.random_get_int(0,0,len(voc)-1)])
            
    return ''.join(name)
        
    
def random_choice_index(chances):  #choose one option from list of chances, returning its index
    #the dice will land on some number between 1 and the sum of the chances
    dice = libtcod.random_get_int(0, 1, sum(chances))

    #go through all chances, keeping the sum so far
    running_sum = 0
    choice = 0
    for w in chances:
        running_sum += w

        #see if the dice landed in the part that corresponds to this choice
        if dice <= running_sum:
            return choice
        choice += 1

def random_choice(chances_dict):
    #choose one option from dictionary of chances, returning its key
    chances = chances_dict.values()
    strings = chances_dict.keys()

    return strings[random_choice_index(chances)]

def from_dungeon_level(z, table):
    #returns a value that depends on level. the table specifies what value occurs after each level, default is 0.
    for (value, level) in reversed(table):
        if z >= level:
            return value
    return 0

def place_objects(z, room):
    global SUM, RIN, POT, SCR, ARM, WEA, BOO, WAN, GLA
    #this is where we decide the chance of each monster or item appearing.

    #maximum number of monsters per room
    max_monsters = from_dungeon_level(z, [[1, 0], [2, 5], [2, 10], [3, 15]])

    #chance of each monster
    monster_chances = {}
    monster_chances['kobold'] = from_dungeon_level(z, [[100, 0], [50, 3],  [5, 8],   [0, 13],   [0, 17]   ])
    monster_chances['goblin'] = from_dungeon_level(z, [[5, 0],   [100, 3], [50, 8],  [5, 13],   [0, 17]   ])
    monster_chances['orc'] = from_dungeon_level(z,    [[0, 0],   [5, 3],   [100, 8], [50, 13],  [5, 17]   ])
    monster_chances['human'] = from_dungeon_level(z,  [[0, 0],   [0, 3],   [5, 8],   [100, 13], [50, 17]  ])
    monster_chances['elf'] = from_dungeon_level(z,    [[0, 0],   [0, 3],   [0,8],    [5, 13],   [100, 17] ])
    
    
    #maximum number of items per room
    max_items = from_dungeon_level(z, [[1, 0], [2, 7]])

    #chance of each item (by default they have a chance of 0 at level 1, which then goes up)
    item_chances = {}
    item_chances['potions'] = from_dungeon_level(z, [[20, 0]])
    item_chances['scrolls'] = from_dungeon_level(z, [[20, 0]])
    item_chances['wands'] = from_dungeon_level(z, [[10, 0]])
    item_chances['weapons'] = from_dungeon_level(z, [[10, 0]])
    item_chances['armor'] = from_dungeon_level(z, [[5, 0]])
    item_chances['glasses'] = from_dungeon_level(z, [[10, 0]])
    item_chances['spellbooks'] = from_dungeon_level(z, [[10, 0]])
    item_chances['rings'] = from_dungeon_level(z, [[10, 0]])
    
    potions = {}
    potions['potion of magma'] = from_dungeon_level(z, [[20, 0]])
    potions['potion of invisibility'] = from_dungeon_level(z, [[10, 0]])
    potions['potion of healing'] = from_dungeon_level(z, [[30, 0]])
    potions['potion of tangerine juice'] = from_dungeon_level(z, [[25, 0]])
    potions['potion of berserk rage'] = from_dungeon_level(z, [[15, 0]])
    
    scrolls = {}
    scrolls['scroll of earth'] = from_dungeon_level(z, [[15, 0]])
    scrolls['scroll of identify'] = from_dungeon_level(z, [[25, 0]])
    scrolls['scroll of teleport'] = from_dungeon_level(z, [[20, 0]])
    scrolls['scroll of enchantment'] = from_dungeon_level(z, [[10, 0]])
    scrolls['scroll of light'] = from_dungeon_level(z, [[30, 0]])
    
    wands = {}
    wands['wand of digging'] = from_dungeon_level(z, [[30, 0]])
    wands['wand of fireball'] = from_dungeon_level(z, [[20, 0]])
    wands['wand of air'] = from_dungeon_level(z, [[25, 0]])
    wands['wand of waterjet'] = from_dungeon_level(z, [[15, 0]])
    wands['wand of polymorph'] = from_dungeon_level(z, [[10, 0]])
    
    weapons = {}
    weapons['dagger'] = from_dungeon_level(z, [[30, 0]])
    weapons['sword'] = from_dungeon_level(z, [[25, 0]])
    weapons['staff'] = from_dungeon_level(z, [[20, 0]])
    weapons['mace'] = from_dungeon_level(z, [[15, 0]])
    weapons['zweihander'] = from_dungeon_level(z, [[10, 0]])
    
    armor = {}
    armor['cloth armor'] = from_dungeon_level(z, [[30, 0]])
    armor['leather armor'] = from_dungeon_level(z, [[25, 0]])
    armor['chain armor'] = from_dungeon_level(z, [[20, 0]])
    armor['plate armor'] = from_dungeon_level(z, [[20, 0]])
    armor['mithril armor'] = from_dungeon_level(z, [[5, 0]])
    
    glasses = {}
    glasses['lenses of see invisible'] = from_dungeon_level(z, [[20, 0]])
    glasses['nerd glasses'] = from_dungeon_level(z, [[25, 0]])
    glasses['Xray visor'] = from_dungeon_level(z, [[15, 0]])
    glasses['glasses of telepathy'] = from_dungeon_level(z, [[10, 0]])
    glasses['sunglasses of elemental protection'] = from_dungeon_level(z, [[30, 0]])
    
    rings = {}
    rings['ring of fire resistance'] = from_dungeon_level(z, [[20, 0]])
    rings['ring of strength'] = from_dungeon_level(z, [[30, 0]])
    rings['hunger ring'] = from_dungeon_level(z, [[25, 0]])
    rings['ring of invisibility'] = from_dungeon_level(z, [[10, 0]])
    rings['lucky ring'] = from_dungeon_level(z, [[15, 0]])
    
    spellbooks = {}
    spellbooks['book of healing'] = from_dungeon_level(z, [[15, 0]])
    spellbooks['book of waterjet'] = from_dungeon_level(z, [[20, 0]])
    spellbooks['book of sunfire'] = from_dungeon_level(z, [[25, 0]])
    spellbooks['book of make tangerine potion'] = from_dungeon_level(z, [[10, 0]])
    spellbooks['book of weakness'] = from_dungeon_level(z, [[30, 0]])
    
    
    #choose random number of monsters
    num_monsters = libtcod.random_get_int(0, 0, max_monsters)
    
    for i in range(num_monsters):
        #choose random spot for this monster
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)

        #only place it if the tile is not blocked
        #if not is_blocked(x, y, z):
        #choose the monster
        choice = random_choice(monster_chances)
        #create the monster
        monster = create_monster(choice, x, y, z)
        
        objects[z].append(monster)
        SUM += monster.fighter.xp
        
    #choose random number of items
    num_items = libtcod.random_get_int(0, 0, max_items)

    for i in range(num_items):
        #choose random spot for this item
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)

        #only place it if the tile is not blocked
        #if not is_blocked(x, y, z):
        choice = random_choice(item_chances)
        if choice == 'potions':
            POT += 1
            choose = random_choice(potions)
        elif choice == 'scrolls':
            choose = random_choice(scrolls)
            SCR += 1
        elif choice == 'wands':
            choose = random_choice(wands)
            WAN += 1
        elif choice == 'weapons':
            choose = random_choice(weapons)
            WEA += 1
        elif choice == 'armor':
            choose = random_choice(armor)
            ARM += 1
        elif choice == 'glasses':
            choose = random_choice(glasses)
            GLA += 1
        elif choice == 'rings':
            choose = random_choice(rings)
            RIN += 1
        elif choice == 'spellbooks':
            choose = random_choice(spellbooks)
            BOO += 1

        choose = string.replace(choose, ' ', '_')
        item = create_item(choose, x, y, z)
        objects[z].append(item)
        item.send_to_back()
        
    #special rooms
    
        
#-----------------------------------------------------------------------------------------------------------------            
            
def get_names_under_cursor(x,y):
    #return a string with the names of all objects under the mouse or crosshair
    T.layer(2)
    T.clear_area(0,0,SCREEN_WIDTH,SCREEN_HEIGHT)
    
    #create a list with the names of all objects at the mouse's coordinates and in FOV
    # names = [obj.name for obj in reversed(objects[player.z])
             # if obj.x == x and obj.y == y and visible_to_player(x,y)]
    names = []
    for obj in reversed(objects[player.z]):
        if obj.x == x and obj.y == y and visible_to_player(x,y) and not obj.fighter:
            names.append(obj.name)
        elif obj.x == x and obj.y == y and visible_to_player(x,y) and obj.fighter:
            if not obj.fighter.invisible:
                names.append(obj.name)
            elif obj.fighter.invisible:
                if get_equipped_in_slot('eyes', player):
                    if get_equipped_in_slot('eyes', player).owner.base_name == 'lenses of see invisible':
                        names.append(obj.name)
    
    if get_equipped_in_slot('eyes', player):
        if get_equipped_in_slot('eyes', player).owner.base_name == 'Xray visor':
            for obj in reversed(objects[player.z]):
                if obj.x == x and obj.y == y and visible_to_player(x,y) and obj.fighter and obj != player:
                    items = [item.name for item in obj.fighter.inventory]
                    inventory = ', \n'.join(items)
                    
                    skills = ''
                    if obj.fighter.skills:
                        skills = ', \n'.join(obj.fighter.skills)
                    
                    pos = 70
                    if player.x >= 45:
                        pos = 3
                    
                    T.print_(pos, 1, '[color=white]' + 'Xray scan:' + '\n' +
                        obj.name + '\n' + 
                        'hp: ' + str(obj.fighter.hp) + '/' + str(obj.fighter.max_hp) + '\n' +
                        'ac: ' + str(obj.fighter.armor) + '\n' +
                        'wit: ' + str(obj.fighter.wit) + '\n' +
                        'strength: ' + str(obj.fighter.strength) + '\n' +
                        skills + '\n' +
                        inventory
                        )
    
    #get terrain type unter mouse (terrain, walls, etc..)
    if visible_to_player(x,y):
        if not map[player.z][x][y].name == 'empty':
            names.append(map[player.z][x][y].name)
            

    if names:
       
        pile = names
        i = 0
        for thing in pile:    
            pos = x+1
            #if x >= 60:
            if x + len(thing) >= SCREEN_WIDTH:
                pos = x-len(thing)
            T.print_(pos, y+i+1, thing)
            i += 1
        
    T.layer(0)
    
    #-----------------------------------------------------------------------------------------------
    
    
def render_all():
    global fov_map, fov_recompute, light_map, l_map 

    T.layer(0)
    #if fov_recompute:
    #recompute FOV if needed (the player moved or something)
    #fov_recompute = False
    vision = 10
    if get_equipped_in_slot('eyes', player):
        if get_equipped_in_slot('eyes', player).owner.base_name == 'sunglasses of elemental protection':
            vision = 5
    
    libtcod.map_compute_fov(fov_map, player.x, player.y, vision, FOV_LIGHT_WALLS, FOV_ALGO)
    T.clear()
    
    #go through all tiles, and set their background color according to the FOV
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
                 
            if not visible_to_player(x,y):
                #if it's not visible right now, the player can only see it if it's explored
                if map[player.z][x][y].explored:
                    T.print_(x, y, '[color=' + map[player.z][x][y].color_dark + ']' + map[player.z][x][y].char_dark)
            else:
                #it's visible
                color_a = map[player.z][x][y].color_light
                if not map[player.z][x][y].air:
                    color_a = 'sky'
                
                T.print_(x, y, '[color=' + color_a + ']' + map[player.z][x][y].char_light)
                
                #since it's visible, explore it
                map[player.z][x][y].explored = True

    #draw all objects in the list, except the player. we want it to
    #always appear over all other objects! so it's drawn later.
    for object in objects[player.z]:
        if object != player:
            object.draw()
    player.draw()
    
#------------------------------------------------------------------------------------------ 
    # #prepare to render the GUI panel
    T.layer(1)
    T.clear_area(0,0,SCREEN_WIDTH,SCREEN_HEIGHT)
    #print the game messages, one line at a time
    y = 1
    for (line, color) in game_msgs:
        T.color(color)
        T.print_(MSG_X, y + PANEL_Y, line)
        y += 1
#------------------------------------------------------------------------------------------  
    #player stats
    if player.fighter.weak:
        hunger = 'weak'
    elif player.fighter.hunger_status:
        hunger = player.fighter.hunger_status
    else:
        hunger = ''
    
    ele_dam = '0'
    ele_color_ac = 'white'
    if get_equipped_in_slot('body', player):
        if get_equipped_in_slot('body', player).element_enchant:
            ele_color_ac = ELEMENT_COLOR[get_equipped_in_slot('body', player).element_enchant]
    
    main_dam = '0'
    off_dam = ' '
    main_edam = '+0'
    off_edam = ''
    main_c = 'white'
    off_c = 'white'
    
    if get_equipped_in_slot('right hand', player):
        main_dam = str(player.fighter.main_damage)
        if get_equipped_in_slot('right hand', player).element_enchant:
            main_c = ELEMENT_COLOR[get_equipped_in_slot('right hand', player).element_enchant]
            main_edam = '+' + str(get_equipped_in_slot('right hand', player).element_damage)
            if 'elementalist' in player.fighter.skills:
                main_edam = '+' + str(int(main_edam)*2)
    
    if get_equipped_in_slot('both hands', player):
        main_dam = str(player.fighter.main_damage)
        if get_equipped_in_slot('both hands', player).element_enchant:
            main_c = ELEMENT_COLOR[get_equipped_in_slot('both hands', player).element_enchant]
            main_edam = '+' + str(get_equipped_in_slot('both hands', player).element_damage)
            if 'elementalist' in player.fighter.skills:
                main_edam = '+' + str(int(main_edam)*2)
    
    if get_equipped_in_slot('left hand', player):
        off_dam = ' ' + str(player.fighter.off_damage)
        if get_equipped_in_slot('left hand', player).element_enchant:
            off_c = ELEMENT_COLOR[get_equipped_in_slot('left hand', player).element_enchant]
            off_edam = '+' + str(get_equipped_in_slot('left hand', player).element_damage)
            if 'elementalist' in player.fighter.skills:
                off_edam = '+' + str(int(off_edam)*2)
    
        
    T.color('white')
    T.print_(1, 20, 'hp: ' + str(player.fighter.hp) + '/' + str(player.fighter.max_hp) + 
        ' spirit: ' + str(player.fighter.spirit) + '/' + str(player.fighter.max_spirit) +
        ' str: ' + str(player.fighter.strength) + 
        ' wit: ' + str(player.fighter.wit) +
        ' atk: ' + main_dam + '[color=' + main_c +']' + main_edam + '[color=white]' + off_dam + '[color=' + off_c +']' + off_edam +
        '[color=white] ac: ' + '[color=' + ele_color_ac + ']' + str(player.fighter.armor) + '[color=white]' +
        ' LVL: ' + str(player.fighter.level) + ' XP: ' + str(player.fighter.xp) + '/' + str(LEVEL_CAPS[player.fighter.level+1]) +
        #' ' + str(player.fighter.hunger) + 
        ' ' + hunger +
        ' DL: ' + str(player.z+1)
        )

#--------------------------------------------------------------------------------------------------------------------------        
    #get info under mouse as console window attached to the mouse pointer
    (x, y) = (T.state(T.TK_MOUSE_X), T.state(T.TK_MOUSE_Y))
    get_names_under_cursor(x,y)
    T.layer(0)
    
def visible_to_player(x,y, monster=None):
    if libtcod.map_is_in_fov(fov_map, x, y): #is in fov?
        return True
    return False
  
def make_GUI_frame(x, y, dx, dy, color='white'):
    #sides
    T.layer(4)
    for i in range(dx-1):
        T.print_(i+x, 0+y, '[color=' + color + ']' + '[U+2500]')
    for i in range(dx-1):
        T.print_(i+x, dy-1+y, '[color=' + color + ']' + '[U+2500]')
    for i in range(dy-1):
        T.print_(0+x, i+y, '[color=' + color + ']' + '[U+2502]')
    for i in range(dy-1):
        T.print_(dx-1+x, i+y, '[color=' + color + ']' + '[U+2502]')

    #corners
    T.print_(x, y, '[color=' + color + ']' + '[U+250C]')
    T.print_(dx-1+x, y, '[color=' + color + ']' + '[U+2510]')
    T.print_(x, dy-1+y, '[color=' + color + ']' + '[U+2514]')
    T.print_(dx-1+x, dy-1+y, '[color=' + color + ']' + '[U+2518]')
    T.layer(0)
    
    
def message(new_msg, color = 'white'):
    #split the message if necessary, among multiple lines
    new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)

    for line in new_msg_lines:
    
        #if the buffer is full, remove the first line to make room for the new one
        if len(game_msgs) == MSG_HEIGHT:
            del game_msgs[0]

        #add the new line as a tuple, with the text and the color
        game_msgs.append( (line, color) )


def player_move_or_attack(dx, dy):
    global fov_recompute

    #the coordinates the player is moving to/attacking
    x = player.x + dx
    y = player.y + dy

    #try to find an attackable object there
    target = None
    npc = None
    for object in objects[player.z]:
        if object.fighter and object.x == x and object.y == y:
            target = object
            break
            
    #attack if target found, move otherwise
    if target is not None:
        player.fighter.attack(target)
        fov_recompute = True
    else:
        player.move(dx, dy)
        fov_recompute = True
        
def menu(header, options, width, back=None, x1=0, y1=0):
    if len(options) > 26: raise ValueError('Cannot have a menu with more than 26 options.')
    
    #calculate total height for the header (after auto-wrap) and one line per option
    header_height = libtcod.console_get_height_rect(0, 0, 0, width, SCREEN_HEIGHT, header)
    if header == '':
        header_height = 0
    height = len(options) + header_height + 2

    if x1 == 0 and y1 == 0:
        x = SCREEN_WIDTH / 2 - width / 2
        y = SCREEN_HEIGHT / 2 - height / 2
    else:
        x = x1
        y = y1
        
    T.layer(2)
    
    #make_GUI_frame(x, y, width, height)
    
    #cursors position
    c_pos = 0
    
    output = None
    
    while True:
        T.layer(2)
        T.clear_area(0,0,SCREEN_WIDTH,SCREEN_HEIGHT)
        
        #create an off-screen console that represents the menu's window
        if back:
            T.composition(T.TK_ON)
            for i in range(width):
                for j in range(height):
                    T.print_(i+x,j+y, '[color=' + back + ']' + '[U+2588]')
        
        T.print_(x+1,y, '[color=white]' + header)
        
        #print all the options
        h = header_height
        letter_index = ord('a')
        run = 0
        for option_text in options:
            text = option_text
            
            if run == c_pos:
                T.print_(x+1,h+y+1, '[color=yellow]> ' + text)
                
            else:    
                T.print_(x+1,h+y+1, '[color=white] ' + text)
            h += 1
            letter_index += 1
            run += 1
            
        #present the root console to the player and wait for a key-press
        T.refresh()
        
        key = T.read()
        if key == T.TK_ESCAPE:
            break
        elif key == T.TK_UP or key == T.TK_KP_8:
            c_pos -= 1
            if c_pos < 0:
                c_pos = len(options)-1
                
        elif key == T.TK_DOWN or key == T.TK_KP_2:
            c_pos += 1
            if c_pos == len(options):
                c_pos = 0
        
        elif key == T.TK_ENTER:               
            #convert the ASCII code to an index; if it corresponds to an option, return it
            index = c_pos
            #if index >= 0 and index < len(options): 
            output = index
            break
            
    T.clear_area(0,0,SCREEN_WIDTH,SCREEN_HEIGHT)
    T.composition(T.TK_OFF)
    T.layer(0)
    return output
    
def inventory_menu(header):
    #show a menu with each item of the inventory as an option
    if len(player.fighter.inventory) == 0:
        options = ['Inventory is empty.']
    else:
        options = []
        for item in player.fighter.inventory:
            text = item.name
            #show additional information, in case it's equipped
            if item.equipment and item.equipment.is_equipped:
                text = text + ' (on ' + item.equipment.slot + ')'
            options.append(text)

    index = menu(header, options, INVENTORY_WIDTH, 'black', 1, 1)

    #if an item was chosen, return it
    if index is None or len(player.fighter.inventory) == 0: return None
    return player.fighter.inventory[index].item
    
def item_use_menu(item):
    #show a menu with each possible use of an item as an option
    
    header = 'What do you want to do with ' + item.owner.name + '?\n'
    
    options = ['cancel', 'drop', 'throw']
    if item.use_function:
        options.append('use')
    if item.owner.equipment: 
        if item.owner.equipment.is_equipped:
            options.append('dequip')
        else:
            options.append('equip')
    if item.owner.base_name in ident_table and ident_table[item.owner.base_name]:
        options.append('name')
    
    
    index = menu(header, options, INVENTORY_WIDTH/2, None, 1, 1)

    if index:
        #if an item was chosen, return resp option
        return options[index]

def msgbox(text, width=50):
    menu(text, [], width,  back = 'black', x1 = 40, y1 = 5)  #use menu() as a sort of "message box"
    
def enter_text_menu(header, max_length): #many thanks to Aukustus and forums for poviding this code. 
    #clear_screen()
    
    T.layer(2)
    T.clear_area(0,0, SCREEN_WIDTH, SCREEN_HEIGHT)
   
    T.print_(5, 4, '[color=white]' + header)
    
    T.print_(5, 5, '[color=white]Name: ')
    key = 0
    letter = ''
    output = ''
    waste, output = T.read_str(12,5, letter, max_length)    
    return output
    

def handle_keys():
    global key, stairs, upstairs, ladder, upladder, game_state, FONT_SIZE
    
    if key == T.TK_ESCAPE:
        choice = menu('Do you want to quit?', ['Yes', 'No'], 24,'black', SCREEN_WIDTH / 2 - 12, 7 )
        if choice == 0:                
            game_state = 'exit' #<- lead to crash WHY ??
            return 'exit' #exit game
        else:
            return 'didnt-take-turn'

    if game_state == 'playing':
        #movement keys
        if key == T.TK_UP or key == T.TK_KP_8:
            player_move_or_attack(0, -1)
        elif key == T.TK_DOWN or key == T.TK_KP_2:
            player_move_or_attack(0, 1)
        elif key == T.TK_LEFT or key == T.TK_KP_4:
            player_move_or_attack(-1, 0)
        elif key == T.TK_RIGHT or key == T.TK_KP_6:
            player_move_or_attack(1, 0)
        # elif key == T.TK_HOME or key == T.TK_KP_7:
            # player_move_or_attack(-1, -1)
        # elif key == T.TK_PAGEUP or key == T.TK_KP_9:
            # player_move_or_attack(1, -1)
        # elif key == T.TK_END or key == T.TK_KP_1:
            # player_move_or_attack(-1, 1)
        # elif key == T.TK_PAGEDOWN or key == T.TK_KP_3:
            # player_move_or_attack(1, 1)
        elif key == T.TK_KP_5 or key == T.TK_PERIOD:
            pass  #do nothing ie wait for the monster to come to you
        else:
            #test for other keys
            if key == T.TK_G:
                #pick up an item
                for object in reversed(objects[player.z]):  #look for an item in the player's tile
                    if object.x == player.x and object.y == player.y and object.item:
                        object.item.pick_up(player)
                        return 0
                    elif object.x == player.x and object.y == player.y and object.name == 'fountain':
                        choice = menu('Do you want to drink from the fountain?', ['Yes','No'], 40)
                        if choice == 0:
                            drink_fountain()
                            return 0
                        elif choice == 1:
                            pass
                            
            if key == T.TK_O:
                FONT_SIZE += 1
                T.set("font: courbd.ttf, size=" + str(FONT_SIZE))
            
            if key == T.TK_P:
                FONT_SIZE -= 1
                T.set("font: courbd.ttf, size=" + str(FONT_SIZE))
            
            if key == T.TK_X:
                pass
                # libtcod.line_init(1, 1, 10, 10)
                # while True:
                    # (a, b) = libtcod.line_step()
                    # print a, b
                    # if not a:
                        # break
    
            if key == T.TK_C:
                equip = get_equipped_in_slot('left hand', player)
                if equip:
                    if equip.owner.item.spell_function:
                        if get_equipped_in_slot('eyes', player):
                            if get_equipped_in_slot('eyes', player).owner.base_name == 'sunglasses of elemental protection':
                                message('You cannot read the '+ equip.owner.name + ' with sunglasses on.')
                                identify('sunglasses of elemental protection')
                            else:
                                return equip.owner.item.spell_function(player)
                        else:
                            return equip.owner.item.spell_function(player)
                            
                    else:
                        message('You try to cast a spell, but that is not a spellbook in your hand.')
                        return 'didnt-take-turn'
                else:
                    message('You try to cast a spell, but you do not have a spellbook ready.')
                    return 'didnt-take-turn'
                    
            if key == T.TK_H:
                msgbox('''
                Controls:
                up,down,left,right
                g grab item
                i inventory 
                c cast spell
                A stairs down
                a stairs up
                o,p screen bigger,smaller
                ESC quit,exit
                ENTER confirm
                ''')
            
            if key == T.TK_I:
            #show the inventory; if an item is selected, use it
                chosen_item = inventory_menu('Choose item from your inventory or ESC to cancel.\n')
                if chosen_item is not None:
                    #chosen_item.use(player)
                    decide = item_use_menu(chosen_item)
                    
                    if not decide:
                        return 'didnt-take-turn'
                    
                    if decide == 'drop':
                        chosen_item.drop(player)
                    elif decide == 'throw':
                        chosen_item.throw(player)
                        initialize_fov()
                    elif decide == 'use':
                        chosen_item.use(player)
                    elif decide == 'equip' or decide == 'dequip':
                        chosen_item.owner.equipment.toggle_equip(player)
                    elif decide == 'name':
                        name = enter_text_menu('How do you want to call ' + chosen_item.owner.name +'?',25)
                        ident_table[chosen_item.owner.base_name] = ident_table[chosen_item.owner.base_name] + ' named ' + name
                        #naming menue
                    
                    return 0

            if key == T.TK_R and T.check(T.TK_SHIFT):
                revive_corpses()
                    
            if key == T.TK_A and T.check(T.TK_SHIFT): #BACKSLASH and T.check(T.TK_SHIFT):
                #go down stairs, if the player is on them
                for obj in objects[player.z]:
                    if obj.name == 'stairs' and obj.x == player.x and obj.y == player.y:
                        next_level('stairs')
                    
                    elif obj.name == 'ladder' and obj.x == player.x and obj.y == player.y:
                        next_level('ladder')
                                
            elif key == T.TK_A: #BACKSLASH:
                #go up stairs, if the player is on them
                for obj in objects[player.z]:
                    if obj.name == 'upstairs' and obj.x == player.x and obj.y == player.y:
                        prev_level('stairs')
                    
                    elif obj.name == 'upladder' and obj.x == player.x and obj.y == player.y:
                        prev_level('ladder')
                        
            return 'didnt-take-turn'

def give_length(thing):
    i = 0
    for part in thing:
        i += 1
    return i
            
            
def ray_effect(x1, y1, x2, y2, color):#many thanks to pat for defender of the deep providing this code!!
    render_all()
    libtcod.console_set_default_foreground(0, color)

    for frame in range(LIMIT_FPS):
        libtcod.line_init(x1, y1, x2, y2)
        while True:
            (x, y) = libtcod.line_step()
            if x is None: break

            char = libtcod.random_get_int(0, libtcod.CHAR_SUBP_NW, libtcod.CHAR_SUBP_SW)
            libtcod.console_put_char(0, x, y, char, libtcod.BKGND_NONE)

        libtcod.console_check_for_keypress()
        libtcod.console_flush()
        


# def swing_effect(x1, y1, d, color, char): #x1, y1 = position of actor; d = radius of swing;
    # render_all()
    
    # segment = d*2 + 1
    
    # for frame in range(segment):
        # libtcod.line_init(x1, y1, x2, y2)
        # T.layer(3)
        # T.clear_area(0,0,SCREEN_WIDTH,SCREEN_HEIGHT)
        # while True:
            # (x, y) = libtcod.line_step()
            # if x is None: break
            # T.print_(x, y, '[color=' + color +  ']' + char)
    
    # T.refresh()
    # T.layer(0)
                    
def throw_effect(x1, y1, x2, y2, color, char):
    render_all()
    libtcod.line_init(x1, y1, x2, y2)
    while True:
        (a, b) = libtcod.line_step()
        T.layer(3)
        T.clear_area(0,0,SCREEN_WIDTH,SCREEN_HEIGHT)
        T.print_(a, b, '[color=' + color +  ']' + char)
        if not a: 
            break
        T.refresh()
        T.layer(0)
        T.delay(50)
        
def fight_effect(cx, cy, color, char):
    render_all()
    num_frames = LIMIT_FPS
    for frame in range(10):
        T.layer(1)
        T.print_(cx, cy, '[color=' + color + ']' + char)
        T.refresh()
        render_all()
    T.layer(0)
    T.clear()
    render_all()
        
def spell_effect(cx, cy, color, char):
    render_all()
    num_frames = LIMIT_FPS
    for frame in range(10):
        T.layer(1)
        T.print_(cx+1, cy, '[color=' + color + ']' + '?')
        T.print_(cx-1, cy, '[color=' + color + ']' + '?')
        T.print_(cx, cy+1, '[color=' + color + ']' + '?')
        T.print_(cx, cy-1, '[color=' + color + ']' + '?')
        T.refresh()
        render_all()
    T.layer(0)
    T.clear()
    render_all()
        
 
def check_level_up():
    global available_skills
    if game_state == 'dead':
        return
    #see if the player's experience is enough to level-up
    level_up_xp = LEVEL_CAPS[player.fighter.level+1]
    if player.fighter.xp >= level_up_xp:
        #it is! level up and ask to raise some stats
        player.fighter.level += 1
        #player.fighter.xp -= level_up_xp
        message('Your battle skills grow stronger! You reached level ' + str(player.fighter.level) + '!', 'yellow')
        render_all()
        choice = None
        points = 5
        while points:  #keep asking until a choice is made
            choice = menu('Level up! You have ' + str(points) + ' points. Choose stat to raise:',
                          ['HP (+1 HP, from ' + str(player.fighter.max_hp) + ')',
                           'Strength (+1 from ' + str(player.fighter.base_strength) + ')',
                           'Wit (+1 from ' + str(player.fighter.base_wit) + ')' ], 40, back= 'black')
                           #'Spirit (+1 from ' + str(player.fighter.base_spirit) + ')'
     
            if choice == 0:
                player.fighter.base_hp += 1
                player.fighter.hp += 1
                points -= 1
            elif choice == 1:
                player.fighter.base_strength += 1
                points -= 1
            elif choice == 2:
                player.fighter.base_wit += 1
                points -= 1
            elif choice == 3:
                player.fighter.base_spirit += 1
                player.fighter.spirit += 1
                points -= 1
            
        if player.fighter.level == 1 or player.fighter.level == 5 or player.fighter.level == 10 or player.fighter.level == 15 or player.fighter.level == 20: 
                
            choice = None
            choice = menu('Level up to 1 or multples of 5! You choose a new skill:\n',
                          available_skills, 40, back='black')
            
            if choice == 0:
                player.fighter.skills.append(available_skills[0])
                available_skills.remove(available_skills[0])
            elif choice == 1:
                player.fighter.skills.append(available_skills[1])
                available_skills.remove(available_skills[1])
            elif choice == 2:
                player.fighter.skills.append(available_skills[2])
                available_skills.remove(available_skills[2])
            elif choice == 3:
                player.fighter.skills.append(available_skills[3])
                available_skills.remove(available_skills[3])
            elif choice == 4:
                player.fighter.skills.append(available_skills[4])
                available_skills.remove(available_skills[4])
            
def player_death(player):
    #the game ended!
    global game_state
    #in case it gets called on many events happening the same loop
    if game_state == 'dead':
        return
    
    #identify all items
    for key, value in ident_table.iteritems():
        ident_table[key] = 0

    message('--You died!', 'red')
    game_state = 'dead'
    
    #for added effect, transform the player into a corpse!
    player.char = '%'    
    player.color = 'dark red'
    render_all()
    T.refresh()
    #show inventory
    chosen_item = inventory_menu('Your possessions are identified.\n')
    #show conducts
    msgbox('You \n' + conducts['conduct1'] + '\n' + conducts['conduct2'] + '\n' + conducts['conduct3'] + '\n' + conducts['conduct4'] + '\n' + conducts['conduct5'] + '\n')
    
def monster_death(monster):
    #transform it into a nasty corpse! it doesn't block, can't be
    #attacked and doesn't move
    message('The ' + monster.name + ' is dead, you gain ' + str(monster.fighter.xp) + ' xp!', 'yellow')
    
    for item in monster.fighter.inventory:
        if item.equipment:
            if item.equipment.is_equipped and libtcod.random_get_int(0,0,100) <= 20:
                item.item.drop(monster)
    
    #break pacifist conduct
    conducts['conduct5'] = ''
    
    # if libtcod.random_get_int(0,0,100) < 33:
        # return monster.delete()
    
    player.fighter.xp += monster.fighter.xp
    monster.char = '%'
    monster.color = 'dark red'
    monster.blocks = False
    
    monster.fighter = None
    monster.ai = None
    monster.base_name = 'remains of ' + monster.base_name

    item_component = Item(use_function=None) #use tbd
    monster.item = item_component 
    monster.item.owner = monster #monster corpse can be picked up
    
    if is_blocked(monster.x, monster.y, monster.z):
        monster.delete()
    
    # resulted in a bug. Player was dying by explosion of Goblin Alchemist -> list.remove(x): x not in list
    try:
        monster.send_to_back()
    except:
        pass
    
def crumble_to_dust(monster):
    #transform it into a nasty corpse! it doesn't block, can't be
    #attacked and doesn't move
    message('The ' + monster.name + ' crumbles to dust.', 'yellow')
    
    monster.delete()
    
DEATH_DICT = {
    'monster_death': monster_death,
    'crumble_to_dust': crumble_to_dust
    }

def distance_2_point(x1, y1, x2, y2):
        #return the distance to another object
        dx = x2 - x1
        dy = y2 - y1
        return math.sqrt(dx ** 2 + dy ** 2)
        
def target_ball(max_range=None):
    global key, mouse
    #return the position of a tile left-clicked in player's FOV (optionally in a range), or (None,None) if right-clicked.
    (x, y) = (player.x, player.y)
    while True:
        #render the screen. this erases the inventory and shows the names of objects under the mouse.
        libtcod.console_flush()
        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, key, mouse)
        render_all()
       
        if mouse.dx:
            (x, y) = (mouse.cx, mouse.cy)

        (x, y) = key_control_target(x, y, key)        
            
        libtcod.console_set_default_foreground(0, libtcod.red)
        i = player.fighter.firepower() + 1
        for y2 in range(MAP_HEIGHT):
            for x2 in range(MAP_WIDTH):
                if distance_2_point(x, y, x2, y2) <= i and visible_to_player(x2,y2) and visible_to_player(x,y):
                    libtcod.console_put_char(0, x2, y2, chr(7), libtcod.BKGND_NONE)
        
        
        if mouse.rbutton_pressed or key.vk == libtcod.KEY_ESCAPE:
            message('Canceled.')
            return (None, None)  #cancel if the player right-clicked or pressed Escape

        #accept the target if the player clicked in FOV, and in case a range is specified, if it's in that range
        if ( (key.vk == libtcod.KEY_ENTER or mouse.lbutton_pressed) and visible_to_player(x,y) and
                (max_range is None or player.distance(x, y) <= max_range)):
            return (x, y)    
    
def target_line(max_range=None):
    global key, mouse
    #return the position of a tile left-clicked in player's FOV (optionally in a range), or (None,None) if right-clicked.
    (x, y) = (player.x, player.y)
    while True:
        #render the screen. this erases the inventory and shows the names of objects under the mouse.
        libtcod.console_flush()
        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, key, mouse)
        render_all()
       
        if mouse.dx:
            (x, y) = (mouse.cx, mouse.cy)
        
        (x, y) = key_control_target(x, y, key)
        
        if not libtcod.map_is_in_fov(fov_map, x, y): continue
        
        for frame in range(LIMIT_FPS):
            libtcod.line_init(player.x, player.y, x, y)
            while True:
                (a, b) = libtcod.line_step()
                if a is None: break
                
                libtcod.console_set_default_foreground(0, libtcod.red)
              
                libtcod.console_put_char(0, a, b, chr(7), libtcod.green)
                
                if mouse.rbutton_pressed or key.vk == libtcod.KEY_ESCAPE:
                    message('Canceled.')
                    return (None, None)  #cancel if the player right-clicked or pressed Escape

                #accept the target if the player clicked in FOV, and in case a range is specified, if it's in that range
                if ( (key.vk == libtcod.KEY_ENTER or mouse.lbutton_pressed) and libtcod.map_is_in_fov(fov_map, x, y) and
                        (max_range is None or player.distance(x, y) <= max_range)):
                    return (x, y)
               
def target_tile(max_range=None):
    global key
    #return the position of a tile left-clicked in player's FOV (optionally in a range), or (None,None) if right-clicked.
    (x, y) = (player.x, player.y)
    while True:
        
        T.refresh()
        render_all()
        
        key = T.read()
        if key == T.TK_MOUSE_MOVE:
            (x, y) = (T.state(T.TK_MOUSE_X), T.state(T.TK_MOUSE_Y))
        
        T.layer(3)
        T.clear_area(0,0,SCREEN_WIDTH,SCREEN_HEIGHT)
        T.print_(x-1, y, '-')
        T.print_(x+1, y, '-')
        T.print_(x, y+1, '|')
        T.print_(x, y-1, '|')
        T.layer(0)    
        
        get_names_under_cursor(x,y)
            
        (x, y) = key_control_target(x, y, key)
            
        if key == T.TK_MOUSE_RIGHT or key == T.TK_ESCAPE:
            #message('Canceled.')
            T.layer(3)
            T.clear_area(0,0,SCREEN_WIDTH,SCREEN_HEIGHT)
            T.layer(0)
            return (None, None)  #cancel if the player right-clicked or pressed Escape

        #accept the target if the player clicked in FOV, and in case a range is specified, if it's in that range
        fighter = False
        for obj in objects[player.z]:
            if obj.x == x and obj.y == y and obj.fighter:
                fighter = True
        if (key == T.TK_MOUSE_LEFT or key == T.TK_ENTER) and (not is_blocked(x,y,player.z) or fighter):
            T.layer(3)
            T.clear_area(0,0,SCREEN_WIDTH,SCREEN_HEIGHT)
            T.layer(0)
            return (x, y)    
 
def key_control_target(a, b, key):
    (x, y) = 0, 0
    if key == T.TK_UP or key == T.TK_KP_8:
        y -= 1
    elif key == T.TK_DOWN or key == T.TK_KP_2:
        y += 1
    elif key == T.TK_LEFT or key == T.TK_KP_4:
        x -= 1        
    elif key == T.TK_RIGHT or key == T.TK_KP_6:
        x += 1    
    # elif key.vk == libtcod.KEY_HOME or key.vk == libtcod.KEY_KP7 or chr(key.c) == 'z':
        # x -= 1
        # y -= 1
    # elif key.vk == libtcod.KEY_PAGEUP or key.vk == libtcod.KEY_KP9 or chr(key.c) == 'u':
        # x += 1
        # y -= 1
    # elif key.vk == libtcod.KEY_END or key.vk == libtcod.KEY_KP1 or chr(key.c) == 'b':
        # x -= 1
        # y += 1
    # elif key.vk == libtcod.KEY_PAGEDOWN or key.vk == libtcod.KEY_KP3 or chr(key.c) == 'n':
        # x += 1
        # y += 1
    return a+x, b+y
            
def target_monster(max_range=None):
    #returns a clicked monster inside FOV up to a range, or None if right-clicked
    while True:
        (x, y) = target_tile(max_range)
        if x is None:  #player cancelled
            return None

        #return the first clicked monster, otherwise continue looping
        for obj in objects[player.z]:
            if obj.x == x and obj.y == y and obj.fighter and obj != player:
                return obj

def closest_monster(max_range):
    #find closest enemy, up to a maximum range, and in the player's FOV
    closest_enemy = None
    closest_dist = max_range + 1  #start with (slightly more than) maximum range

    for object in objects[player.z]:
        if object.fighter and not object == player and libtcod.map_is_in_fov(fov_map, object.x, object.y):
            #calculate distance between this object and the player
            dist = player.distance_to(object)
            if dist < closest_dist:  #it's closer, so remember it
                closest_enemy = object
                closest_dist = dist
    return closest_enemy


def monsters_around(center, range):
    #find all monsters around in range radius and visible
    monsters = []
    
    for object in objects[player.z]:
        if object.fighter and not object == player and libtcod.map_is_in_fov(fov_map, object.x, object.y):
            #calculate distance between this object and the player
            dist = center.distance_to(object)
            if dist < range + 1:
                monsters.append(object)
    return monsters

def beings_around(x, y, range):
    #find all monsters around in range radius and visible
    monsters = []
    
    for object in objects[player.z]:
        if object.fighter:
            #calculate distance between this object and the player
            dist = distance_2_point(x, y, object.x, object.y)
            if dist < range + 1:
                monsters.append(object)
    return monsters

def invisipotion(drinker=None):    
    if drinker == player:
        message('You drink the potion.')
        message('You turn invisible for a time.')
    else:
        message(drinker.name + ' drinks a potion.')
        message(drinker.name + ' turns invisible for a time.')
    
    temp = TempInvisible(ticker, speed=6, duration=50)
    temp.owner = drinker
    drinker.fighter.change_hunger(50)
    
    if drinker == player:
        #break conduct
        conducts['conduct3'] = ''

    if ident_table['potion of invisibility']:
        identify('potion of invisibility')
    
def drink_fountain():
    message('You drink from the fountain.', 'blue')
    #break food conduct
    conducts['conduct4'] = ''
    r = libtcod.random_get_int(0,0,100)
    if r <= 50:
        message('Mh, the water tastes like nothing.')
    elif r <= 60:
        message('The water tastes really bad, you vomit immediately.')
        player.fighter.change_hunger(-100)
    elif r <= 70:
        message('From down below shoots a jet of water.')
        fight_effect(player.x, player.y, 'blue', '#')
        do_element_damage(player, player, 30, 'water')
    elif r <= 100:
        message('You sip and swallow a coin.')
        player.fighter.change_luck(-500)
        
def drink_magma(drinker=None):
    message('You drink the potion.')
    drinker.fighter.change_hunger(50)
    if ident_table['potion of magma']:
        identify('potion of magma')
    do_element_damage(drinker, drinker, 20, 'fire')
    
def light_flash(source):
    
    spell_effect(source.x, source.y, 'yellow', 'w')
    
    if source == player:
        monsters = monsters_around(source, 5)
        message('You read the scroll.')
    else:
        monsters = beings_around(source.x, source.y, 5)
        message(source.name + ' reads a scroll.')
        
    message('A light flashes, blinding enemies.', 'yellow')
    if monsters:
        for monster in monsters:
            if monster != source:
                damage = source.fighter.wit
                if 'range ranger' in source.fighter.skills:
                    damage = damage * 2
        
                for equip in get_all_equipped(monster):
                    if equip.owner.base_name == 'sunglasses of elemental protection':
                        damage = damage / 2
                fight_effect(monster.x, monster.y, 'yellow', '#')
                do_damage(monster, damage)

    if source == player:
        #break conduct
        conducts['conduct2'] = ''
                
        if ident_table['scroll of light']:
            message('You learn that ' + ident_table['scroll of light'] + ' is a scroll of light.')
            ident_table['scroll of light'] = 0

def weaken(caster):
    cost = 2
    if 'spellslinger' in caster.fighter.skills:
        cost = cost / 2
        cost = int(round(cost))
    
    if caster.fighter.spirit < cost and caster == player:
        message('You do not have enough spirit to cast the spell.')
        return 'didnt-take-turn'
    
    spell_effect(caster.x, caster.y, 'orange', 'w')
    
    monsters = []
    if caster == player:
        #break conduct
        conducts['conduct2'] = ''
        message('You speak words of weakness', 'orange')
        monsters = monsters_around(caster, 5)
    else:
        message(caster.name + ' speaks words of weakness', 'orange')
        monsters = beings_around(caster.x, caster.y, 5)
    
    message('The spell weakens surrounded enemies.', 'orange')
     
    if monsters:
        for monster in monsters:
            if monster != caster:
                fight_effect(monster.x, monster.y, 'orange', '#')
                monster.fighter.weak_spell = True
                temp = TempWeak(ticker, speed=6, duration=50)
                temp.owner = monster
    
    caster.fighter.spirit -= cost
    
    if caster == player:        
        if ident_table['book of weakness']:
            identify('book of weakness')
                
    return 0
                
def sunfire(caster):
    cost = 12
    if 'spellslinger' in caster.fighter.skills:
        cost = cost / 2
        cost = int(round(cost))
    
    if caster.fighter.spirit < cost and caster == player:
        message('You do not have enough spirit to cast the spell.')
        return 'didnt-take-turn'
    
    spell_effect(caster.x, caster.y, 'red', 'w')
    
    monsters = []
    if caster == player:
        #break conduct
        conducts['conduct2'] = ''
        message('You speak the words of sunfire', 'red')
        monsters = monsters_around(caster, 10)
    else:
        message(caster.name + ' speaks the words of sunfire', 'red')
        monsters = beings_around(caster.x, caster.y, 10)
        
    message('A flame as bright as the sun damages the unprotected around.', 'orange')
    caster.fighter.spirit -= cost
     
    if monsters:
        for monster in monsters:
            if monster != caster:
                damage = 10
                
                fight_effect(monster.x, monster.y, 'red', '#')
                do_element_damage(caster, monster, damage, 'fire')
    
    if caster == player:        
        if ident_table['book of sunfire']:
            identify('book of sunfire')
            
    return 0
            
def book_waterjet(caster):
    cost = 7
    if 'spellslinger' in caster.fighter.skills:
        cost = cost / 2
        cost = int(round(cost))
    
    if caster.fighter.spirit < cost and caster == player:
        message('You do not have enough spirit to cast the spell.')
        return 'didnt-take-turn'
    
    spell_effect(caster.x, caster.y, 'blue', 'w')
    
    if caster == player:
        #break conduct
        conducts['conduct2'] = ''
    
    if caster == player:
        message('You cast the spell. Where do you want to shoot a water jet?', 'blue')
        target = target_monster(10)
    else:
        target = player
    
    if target:
        if caster == player:
            message('A jet of water shoots to the target.', 'blue')
        else:
            message(caster.name + ' mumbles words of water.', 'blue')
            message(caster.name + ' shoots a jet of water at you.', 'blue')
        
        damage = 10
        caster.fighter.spirit -= cost
        
        #throw_effect(caster.x, caster.y, target.x, target.y, 'blue', '*')
    
        fight_effect(target.x, target.y, 'blue', '#')
        do_element_damage(caster, target, damage, 'water')
        
    if caster == player:        
        if ident_table['book of waterjet']:
            identify('book of waterjet')

    return 0
        
def wand_waterjet(caster):
    damage = caster.fighter.wit + 5
    if 'range ranger' in caster.fighter.skills:
        damage = damage * 2

    spell_effect(caster.x, caster.y, 'blue', 'w')
    
    if caster == player:
        message('You evoke the wand. Where do you want to shoot a water jet?', 'blue')
        target = target_monster(10)
        
        if target:
            message('A jet of water shoots to the ' + target.name + '.', 'blue')
            fight_effect(target.x, target.y, 'blue', '#')
            do_element_damage(caster, target, damage, 'water')

    if caster != player:
        target = player
        message(caster.name + ' evokes a wand, a jet of water shoots at you.', 'blue')
        fight_effect(target.x, target.y, 'blue', '#')
        do_element_damage(caster, target, damage, 'water')

    if ident_table['wand of waterjet']:
        identify('wand of waterjet')

def wand_polymorph(caster):
    
    spell_effect(caster.x, caster.y, 'purple', 'w')
    
    message('You evoke the wand. Where do you want to zap?', 'magenta')
    if ident_table['wand of polymorph']:
        identify('wand of polymorph')

    (x,y) = target_tile()
    target = False
    for obj in objects[caster.z][:]:
        if obj.x == x and obj.y == y and obj.item and not 'remains' in obj.name:
            new_type = polymorph_object(obj)
            new_type = string.replace(new_type, ' ', '_')
            new_obj = create_item(new_type, obj.x, obj.y, obj.z)
            objects[caster.z].append(new_obj)
            message(obj.name + ' turns into ' + new_obj.name + '.', 'magenta')
            obj.delete()
            target = True
        elif obj.x == x and obj.y == y and obj.fighter and obj != player:
            monsters = ['kobold', 'goblin', 'orc', 'human', 'elf']
            random.shuffle(monsters)
            message(obj.name + ' turns into ' + monsters[0] + '.', 'magenta')
            obj.delete()
            objects[player.z].append(create_monster(monsters[0], x, y, player.z))
            target = True
        elif obj.x == x and obj.y == y and obj == player:
            #collect all stat points
            points = obj.fighter.base_hp + obj.fighter.base_strength + obj.fighter.base_wit - 15
            obj.fighter.base_hp = 5
            obj.fighter.base_strength = 5
            obj.fighter.base_wit = 5
            
            for i in range(points):
                r = libtcod.random_get_int(0,0,100)
                if r <= 33:
                    obj.fighter.base_hp += 1
                elif r <= 66:
                    obj.fighter.base_strength += 1
                else:
                    obj.fighter.base_wit += 1
            
            number_skills = len(obj.fighter.skills)
            
            av_skills = ['armor wearer','double dagger', 'elementalist', 'spellslinger','range ranger']
            random.shuffle(av_skills)
            obj.fighter.skills = []
            
            for i in range(number_skills):
                obj.fighter.skills.append(av_skills[i])
                
            message('You feel morphed into a new you.', 'magenta')
            target = True
        elif obj.x == x and obj.y == y and 'remains' in obj.base_name:
            monsters = ['kobold', 'goblin', 'orc', 'human', 'elf']
            random.shuffle(monsters)
            message(obj.name + ' turns into remians of ' + monsters[0] + '.', 'magenta')
            obj.base_name = 'remains of ' + monsters[0]
            target = True
            
    if not target:
        message('Nothing happens.')
        
def polymorph_object(obj):
    
    lists = [
    
    ['ring of fire resistance', 'ring of invisibility', 'hunger ring', 'ring of strength', 'lucky ring'],
    ['wand of air', 'wand of fireball', 'wand of waterjet', 'wand of digging', 'wand of polymorph'],
    ['scroll of identify', 'scroll of earth', 'scroll of light', 'scroll of teleport', 'scroll of enchantment'],
    ['lenses of see invisible', 'nerd glasses', 'sunglasses of elemental protection', 'glasses of telepathy', 'Xray visor'],
    ['cloth armor', 'leather armor', 'chain armor', 'plate armor', 'mithril armor'],
    ['dagger', 'sword', 'staff', 'mace', 'zweihander'],
    ['potion of healing', 'potion of berserk rage', 'potion of magma', 'potion of tangerine juice', 'potion of invisibility'],
    ['book of make tangerine potion', 'book of healing', 'book of sunfire', 'book of waterjet', 'book of weakness' ]
    ]
    
    for list in lists:
        for item_type in list:
            if obj.base_name == item_type:
               random.shuffle(list)
               return list[0]
        
def wand_fireball(caster):

    spell_effect(caster.x, caster.y, 'red', 'w')
    
    damage = caster.fighter.wit + 10
    if 'range ranger' in caster.fighter.skills:
        damage = damage * 2
    
    if caster == player:
        message('You evoke the wand. Where do you want to shoot?', 'red')
        
        (x,y) = target_tile()
        if not x and not y:
            return
        
        monsters = beings_around(x,y, 3)
    else:
        message(caster.name + ' evokes a wand. It shoots a fireball at you', 'red')
        monsters = beings_around(player.x, player.y, 5)
    
    if ident_table['wand of fireball']:
        identify('wand of fireball')

    if monsters:
        for monster in monsters:
            fight_effect(monster.x, monster.y, 'red', '#')
            do_element_damage(caster, monster, damage, 'fire')
    
def wand_air(caster):
    
    spell_effect(caster.x, caster.y, 'sky', 'w')
    
    if caster == player:
        message('You evoke the wand. It sucks away the air around you.', 'sky')
    else:
        message(caster.name + ' evokes a wand. It sucks away the air around.', 'sky')
    
    if ident_table['wand of air']:
        identify('wand of air')

    for x in range(MAP_WIDTH):
        for y in range(MAP_HEIGHT):
            dist = distance_2_point(caster.x, caster.y, x, y)
            if dist <= 6:
                map[caster.z][x][y].air_count = 50
                map[caster.z][x][y].air = False
        
def wand_digging(caster):
    
    spell_effect(caster.x, caster.y, 'sky', 'w')
    
    if caster == player:
        message('You evoke the wand. In which direction to dig?', 'sky')
        damage = caster.fighter.wit
        if 'range ranger' in caster.fighter.skills:
            damage = damage * 2
        while True:
            render_all()
            T.refresh()
            key = T.read()
            
            if key == T.TK_LEFT:
                for i in range(5):
                    if not caster.x-i-1 < 0:
                        map[caster.z][caster.x-i-1][caster.y].change_type('empty')
                        for obj in objects[caster.z]:
                            if obj.x == caster.x-i-1 and obj.y == caster.y and obj.fighter:
                                fight_effect(obj.x, obj.y, 'sky', '#')
                                do_element_damage(caster, obj, damage, 'air')
                break
            elif key == T.TK_RIGHT:
                for i in range(5):
                    if not caster.x+i+1 > MAP_WIDTH:
                        map[caster.z][caster.x+i+1][caster.y].change_type('empty')
                        for obj in objects[caster.z]:
                            if obj.x == caster.x+i+1 and obj.y == caster.y and obj.fighter:
                                fight_effect(obj.x, obj.y, 'sky', '#')
                                do_element_damage(caster, obj, damage, 'air')
                break
            elif key == T.TK_UP:
                for i in range(5):
                    if not caster.y-i-1 < 0:
                        map[caster.z][caster.x][caster.y-i-1].change_type('empty')
                        for obj in objects[caster.z]:
                            if obj.x == caster.x and obj.y == caster.y-i-1 and obj.fighter:
                                fight_effect(obj.x, obj.y, 'sky', '#')
                                do_element_damage(caster, obj, damage, 'air')
                break
            elif key == T.TK_DOWN:
                for i in range(5):
                    if not caster.y+i+1 > MAP_HEIGHT:
                        map[caster.z][caster.x][caster.y+i+1].change_type('empty')
                        for obj in objects[caster.z]:
                            if obj.x == caster.x and obj.y == caster.y+i+1 and obj.fighter:
                                fight_effect(obj.x, obj.y, 'sky', '#')
                                do_element_damage(caster, obj, damage, 'air')
                break
                    
        message('You dig a corridor.')    
    else:
        damage = caster.fighter.wit
        if 'range ranger' in caster.fighter.skills:
            damage = damage * 2
        message(caster.name + ' zaps a wand in your direction.', 'sky')
        if caster.x == player.x:
            if caster.y > player.y: #shoot up
                for i in range(5):
                    if not caster.y-i-1 < 0:
                        map[caster.z][caster.x][caster.y-i-1].change_type('empty')
                        for obj in objects[caster.z]:
                            if obj.x == caster.x and obj.y == caster.y-i-1 and obj.fighter:
                                fight_effect(obj.x, obj.y, 'sky', '#')
                                do_element_damage(caster, obj, damage, 'air')
            elif caster.y < player.y: #shoot down
                for i in range(5):
                    if not caster.y+i+1 < MAP_WIDTH:
                        map[caster.z][caster.x][caster.y+i+1].change_type('empty')
                        for obj in objects[caster.z]:
                            if obj.x == caster.x and obj.y == caster.y+i+1 and obj.fighter:
                                fight_effect(obj.x, obj.y, 'sky', '#')
                                do_element_damage(caster, obj, damage, 'air')
        elif caster.y == player.y:
            if caster.x > player.x: #shoot left
                for i in range(5):
                    if not caster.x-i-1 < 0:
                        map[caster.z][caster.x-i-1][caster.y].change_type('empty')
                        for obj in objects[caster.z]:
                            if obj.x == caster.x-i-1 and obj.y == caster.y and obj.fighter:
                                fight_effect(obj.x, obj.y, 'sky', '#')
                                do_element_damage(caster, obj, damage, 'air')
            elif caster.x < player.x: #shoot right
                for i in range(5):
                    if not caster.x+i+1 > MAP_WIDTH:
                        map[caster.z][caster.x+i+1][caster.y].change_type('empty')
                        for obj in objects[caster.z]:
                            if obj.x == caster.x+i+1 and obj.y == caster.y and obj.fighter:
                                fight_effect(obj.x, obj.y, 'sky', '#')
                                do_element_damage(caster, obj, damage, 'air')
                            
    if ident_table['wand of digging']:
        identify('wand of digging')
        
def earth_wall(source=None):
    global map
    
    spell_effect(source.x, source.y, 'yellow', '?')
    
    message('A wall of earth raises from the ground.', 'yellow')
    if ident_table['scroll of earth']: 
        identify('scroll of earth')
    if source == player:
        #break conduct
        conducts['conduct2'] = ''

    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            if distance_2_point(player.x, player.y, x, y) >= 1 and distance_2_point(player.x, player.y, x, y) < 2:
                map[source.z][x][y].change_type('rock wall')
                for obj in objects[source.z]:
                    if obj.x == x and obj.y == y and obj.fighter:
                        do_element_damage(source, obj, 200, 'earth')
    
def scroll_identify(source=None):

    spell_effect(source.x, source.y, 'orange', 'w')
    
    if ident_table['scroll of identify']:
        message('You learn that ' + ident_table['scroll of identify'] + ' is a scroll of identify.')
        ident_table['scroll of identify'] = 0
    if source == player:
        #break conduct
        conducts['conduct2'] = ''    
    
    render_all()
    chosen_item = inventory_menu('Choose an item to use scroll of identify or ESC to cancel.\n')
    if chosen_item is not None:
        if chosen_item.owner.base_name in ident_table:
            identify(chosen_item.owner.base_name)
        else:
            return 'cancelled'

def identify(item):
    global ident_table
    
    if not ident_table[item]:
        return
    
    cover = ident_table[item]
    ident_table[item] = 0
    message('You learn that ' + cover + ' is a ' + item + '.')
    
def scroll_enchant(user=None):
    #enchant equip, either weapon or armor
    if user == player:
        spell_effect(user.x, user.y, 'orange', '?')
    
    if user == player:
        #break conduct
        conducts['conduct2'] = ''
        if ident_table['scroll of enchantment']:
            message('You learn that ' + ident_table['scroll of enchantment'] + ' is a scroll of enchantment.')
            ident_table['scroll of enchantment'] = 0
        
        list = []
        for equip in get_all_equipped(user):
            if equip.armor_bonus or equip.damage_bonus:
                list.append(equip)
        if not list:
            message('You are not wearing equipment to enchant.')
            return 'cancelled'
                
        random.shuffle(list)
        random.shuffle(ELEMENTS)
        target = list[0]
        #armor?
        if target.armor_bonus:
            target.armor_bonus += 1
            message('You enchanted your ' + target.owner.name + '.')
            if libtcod.random_get_int(0,0,100) <= 50:
                message('It follows a new elemental philosophy now.')
                target.element_enchant = ELEMENTS[0]
            
        #weapon
        elif target.damage_bonus:
            target.damage_bonus += 1
            message('You enchanted your ' + target.owner.name + '.')
            if libtcod.random_get_int(0,0,100) <= 30:
                message('It follows a new elemental philosophy now.')                
                target.element_enchant = ELEMENTS[0]
                target.element_damage += 1
    else:
        list = []
        for equip in get_all_equipped(user):
            if equip.armor_bonus or equip.damage_bonus:
                list.append(equip)
        if not list:
            return 'cancelled'
                
        random.shuffle(list)
        random.shuffle(ELEMENTS)
        target = list[0]
        #armor?
        if target.armor_bonus:
            target.armor_bonus += 1
            target.element_enchant = ELEMENTS[0]
            
        #weapon
        elif target.damage_bonus:
            target.damage_bonus += 1
            target.element_enchant = ELEMENTS[0]
            target.element_damage += 1
        
        
def scroll_teleport(user):

    spell_effect(user.x, user.y, 'sky', 'w')
    
    if user == player:
        #break conduct
        conducts['conduct2'] = ''
        message('You have been teleported to other surroundings.', 'sky')
        if ident_table['scroll of teleport']:
            message('You learn that ' + ident_table['scroll of teleport'] + ' is a scroll of teleport.')
            ident_table['scroll of teleport'] = 0
    else:
        message(user.name + ' reads a scroll and teleports away.', 'sky')
    
    while True:
        x = libtcod.random_get_int(0,0,MAP_WIDTH)
        y = libtcod.random_get_int(0,0,MAP_HEIGHT)
        if not is_blocked(x, y, user.z):
            break
    user.x = x
    user.y = y
    
def make_tangerine_potion(caster):
    cost = 4
    if 'spellslinger' in caster.fighter.skills:
        cost = cost / 2
    
    if caster.fighter.spirit < cost:
        message('You do not have enough spirit to cast the spell.')
        return 'didnt-take-turn'
    
    spell_effect(caster.x, caster.y, 'orange', 'w')
    
    if caster == player:
        #break conduct
        conducts['conduct2'] = ''
    
    caster.fighter.change_hunger(-50)
    objects[caster.z].append(create_item('potion_of_tangerine_juice', caster.x, caster.y, caster.z))
    objects[caster.z].append(create_item('potion_of_tangerine_juice', caster.x, caster.y, caster.z))
    caster.fighter.spirit -= cost
    message('You cast the spell, two potions appear at your feet.')
    
    if ident_table['book of make tangerine potion']:
        identify('book of make tangerine potion')

    return 0
    
def cast_heal(caster):
    cost = 3
    if 'spellslinger' in caster.fighter.skills:
        cost = cost / 2
        cost = int(round(cost))
    
    if caster.fighter.spirit < cost:
        message('You do not have enough spirit to cast the spell.')
        return 'didnt-take-turn'
    
    spell_effect(caster.x, caster.y, 'yellow', '?')
    
    if caster == player:
        #break conduct
        conducts['conduct2'] = ''
    
    #heal the player
    caster.fighter.change_hunger(-50)
    caster.fighter.heal(25)
    caster.fighter.spirit -= cost
    message('You cast the spell, your wounds start to feel much better!', 'sky')
    
    if caster == player:        
        if ident_table['book of healing']:
            identify('book of healing')
    return 0
    
def drink_heal(user=None):
    #heal the user
    name2 = user.name + "'s"
    
    if user == player:
        name2 = 'Your'
        message('You drink the potion.')
    else:
        message(user.name + ' drinks a potion.')
    
    user.fighter.change_hunger(50)
    message(name2 + ' wounds start to feel much better!', 'sky')
    user.fighter.heal(25)
    if user == player:
        identify('potion of healing')
    
def berserk_potion(drinker=None):
    
    if drinker == player:
        message('You drink the potion.')
        message('Your eyes turn red in berserker rage.')
    else:
        message(drinker.name + ' drinks a potion.')
        message(drinker.name + "'s eyes turn red in berserker rage.")
    
    temp = TempBerserk(ticker, speed=6, duration=50)
    temp.owner = drinker
    drinker.fighter.change_hunger(50)
    
    if drinker == player:
        #break conduct
        conducts['conduct3'] = ''

    if ident_table['potion of berserk rage']:
        identify('potion of berserk rage')
    
    
# def cast_full_spirit(user=None):
    
    # message('You drink the potion.')
    # #heal the user
    # name2 = user.name + "'s"
    
    # if user == player:
        # name2 = 'Your'
        # message('You drink the potion.')
    # else:
        # message(user.name + ' drinks a potion.')
    
    # user.fighter.change_hunger(50)
    # message(name2 + ' spirit recovers!', 'sky')
    # user.fighter.remana(200)
    # if user == player:
        # identify('potion of spirit')
    
def consume_food(user=None):
    message('You drink the potion.')
    message('You feel less hungry!', 'orange')
    identify('potion of tangerine juice')
    user.fighter.change_hunger(500)

def cast_firebolt(creator=None):
    #ask the player for a target tile to throw a fireball at
    message('Use keys or cursor to target, left-click or Enter at a target tile for FIREBOLT, or right-click or ESC to cancel.', 'blue')
    (x, y) = target_tile()
    if x is None: return 'cancelled'
   
    throw_effect(player.x, player.y, x, y, libtcod.orange, '*')
        
    for obj in objects[player.z]:  #damage every fighter in range, including the player
        if obj.x == x and obj.y == y:
            if obj.fighter:
                do_damage(obj, 0, (player.fighter.firepower()+1)*2)
            else:
                set_on_fire(obj)
                #message(obj.name + str(obj.flammable_prob))

def save_game():
    #open a new empty shelve (possibly overwriting an old one) to write the game data
    file = shelve.open('savegame', 'n')
    file['map'] = map
    file['objects'] = objects
    file['player_index1'] = player.z  #index of player in objects list
    file['player_index2'] = objects[player.z].index(player)
    #file['stairs_index'] = objects.index(stairs)  #same for the stairs
    file['game_msgs'] = game_msgs
    file['game_state'] = game_state
    #file['dungeon_level'] = dungeon_level
    file.close()
    
def unsave_game():
    #open a new empty shelve (possibly overwriting an old one) to clear the game data
    file = shelve.open('savegame', 'n')
    file['map'] = 0
    file['objects'] = 0
    file['player_index1'] = 0 #index of player in objects list
    file['player_index2'] = 0 
    #file['stairs_index'] = objects.index(stairs)  #same for the stairs
    file['game_msgs'] = 0
    file['game_state'] = 0
    #file['dungeon_level'] = 0
    file.close()

def load_game():
    #open the previously saved shelve and load the game data
    global map, objects, player, game_msgs, game_state
    file = shelve.open('savegame', 'r')
    map = file['map']
    objects = file['objects']
    player = objects[file['player_index1']][file['player_index2']]  #get index of player in objects list and access it
    #stairs = objects[file['stairs_index']]  #same for the stairs
    game_msgs = file['game_msgs']
    game_state = file['game_state']
    #dungeon_level = file['dungeon_level']
    file.close()
    
    unsave_game() #clears savegame file

    initialize_fov()

    
def create_player():
    #create object representing the player
    fighter_component = Fighter(hp=5, 
                                damage=0, 
                                armor=0, 
                                wit=5, 
                                strength=5, 
                                spirit=5,
                                death_function=player_death)
    ai_component = PlayerAI(ticker, 6)
    player = Object(0, 0, 0, '@', 'You', 'white', blocks=True, fighter=fighter_component, ai=ai_component)
    
    player.fighter.inventory.append(create_item('dagger'))
    #player.fighter.inventory.append(create_item('cloth_armor'))
    #player.fighter.inventory.append(create_item('sword'))
    #player.fighter.inventory.append(create_item('zweihander'))
    #player.fighter.inventory.append(create_item('sunglasses_of_elemental_protection'))
    #player.fighter.inventory.append(create_item('book_of_sunfire'))
    #player.fighter.inventory.append(create_item('glasses_of_telepathy'))
    #player.fighter.inventory.append(create_item('lenses_of_see_invisible'))
    #player.fighter.inventory.append(create_item('hunger_ring'))
    #player.fighter.inventory.append(create_item('potion_of_berserk_rage'))
    
    #player.fighter.inventory.append(create_item('potion_of_healing'))
    #player.fighter.inventory.append(create_item('potion_of_magma'))
    #player.fighter.inventory.append(create_item('potion_of_invisibility'))
    #player.fighter.inventory.append(create_item('scroll_of_teleport'))
    #player.fighter.inventory.append(create_item('scroll_of_light'))
    #player.fighter.inventory.append(create_item('wand_of_polymorph'))
    
    #player.fighter.inventory.append(create_item('plate_armor'))
    #player.fighter.inventory.append(create_item('ring_of_invisibility'))
    
    
    return player
    
    
def new_game():
    global player, game_msgs, game_state, objects, ticker, available_skills, conducts, SUM, special_rooms
    
    SUM = 0
    
    ticker = timer.Ticker()
    
    objects = [ [] for i in range(NUMBER_FLOORS)] #levels
    
    player = create_player()    
    
    objects[player.z].append(player)
    
    available_skills = ['armor wearer','double dagger', 'elementalist', 'spellslinger','range ranger']
    
    special_rooms = ['tangerine', 'library', 'house', 'temple', 'fountain'] 
    random.shuffle(special_rooms)
    
    make_map()
    
    conducts = {
    'conduct1': 'Never dealt elemental damage',
    'conduct2': 'Never read anything', 
    'conduct3': 'Have always been visible', 
    'conduct4': 'Did not consume food',
    'conduct5': 'never killed anything'}
    
    unidentify_items()
    
    check = StoneCheck(ticker, speed=12)
        
    set_player_on_upstairs('stairs')
    
    initialize_fov()

    game_state = 'playing'

    #create the list of game messages and their colors, starts empty
    game_msgs = []

    z_consistency() #general clean-up to set all z-coordinates of all items and objects
    
    #a warm welcoming message!
    message('Welcome to the dungeon! Retrive the 5 holy arctifacts from the depths and return to the surface! Press h for help.', 'yellow')

def unidentify_items():
    global ident_table

    ident_table = {
    
    'ring of fire resistance': 0,
    'ring of invisibility': 0,
    'hunger ring': 0,
    'ring of strength': 0, 
    'lucky ring': 0,
    
    'scroll of identify': 0,
    'scroll of earth': 0,
    'scroll of light': 0,
    'scroll of teleport': 0, 
    'scroll of enchantment': 0,

    'potion of healing': 0,
    'potion of berserk rage': 0,
    'potion of magma': 0,
    'potion of tangerine juice': 0, 
    'potion of invisibility': 0,

    'wand of air': 0,
    'wand of fireball': 0,
    'wand of waterjet': 0,
    'wand of polymorph': 0, 
    'wand of digging': 0,
    
    'book of healing': 0,
    'book of sunfire': 0,
    'book of waterjet': 0,
    'book of make tangerine potion': 0, 
    'book of weakness': 0,

    'lenses of see invisible': 0,
    'nerd glasses': 0,
    'sunglasses of elemental protection': 0,
    'glasses of telepathy': 0, 
    'Xray visor': 0

    }
    
    list_rings = ['ruby ring', 'topas ring', 'emerald ring', 'diamond ring', 'gold ring']
    random.shuffle(list_rings)
    
    ident_table['ring of fire resistance'] = list_rings[0]
    ident_table['ring of invisibility'] = list_rings[1]
    ident_table['hunger ring'] = list_rings[2]
    ident_table['ring of strength'] = list_rings[3]
    ident_table['lucky ring'] = list_rings[4]
    
    list_glasses = ['beryll glasses', 'green glasses', 'small glasses', 'octagonal lenses', 'milky glasses']
    random.shuffle(list_glasses)
    
    ident_table['lenses of see invisible'] = list_glasses[0]
    ident_table['nerd glasses'] = list_glasses[1]
    ident_table['sunglasses of elemental protection'] = list_glasses[2]
    ident_table['glasses of telepathy'] = list_glasses[3]
    ident_table['Xray visor'] = list_glasses[4]
    
    list_wands = ['oaken wand', 'silver wand', 'steel wand', 'carbon wand', 'birchen wand']
    random.shuffle(list_wands)
    
    ident_table['wand of air'] = list_wands[0]
    ident_table['wand of fireball'] = list_wands[1]
    ident_table['wand of waterjet'] = list_wands[2]
    ident_table['wand of polymorph'] = list_wands[3]
    ident_table['wand of digging'] = list_wands[4]
    
    list_scrolls = ['scroll of CHTHUHLHUH', 'scroll of YIGING', 'scroll of LETTER', 'scroll of BLOG', 'scroll of TWEED']
    random.shuffle(list_scrolls)
    
    ident_table['scroll of identify'] = list_scrolls[0]
    ident_table['scroll of earth'] = list_scrolls[1]
    ident_table['scroll of enchantment'] = list_scrolls[2]
    ident_table['scroll of teleport'] = list_scrolls[3]
    ident_table['scroll of light'] = list_scrolls[4]
    
    list_potions = ['clear potion', 'yellow potion', 'foaming potion', 'orange potion', 'viscous potion']
    random.shuffle(list_potions)
    
    ident_table['potion of healing'] = list_potions[0]
    ident_table['potion of tangerine juice'] = list_potions[1]
    ident_table['potion of berserk rage'] = list_potions[2]
    ident_table['potion of magma'] = list_potions[3]
    ident_table['potion of invisibility'] = list_potions[4]
    
    list_books = ['blue book', 'thin book', 'runic book', 'square book', 'white book']
    random.shuffle(list_books)
    
    ident_table['book of healing'] = list_books[0]
    ident_table['book of make tangerine potion'] = list_books[1]
    ident_table['book of sunfire'] = list_books[2]
    ident_table['book of waterjet'] = list_books[3]
    ident_table['book of weakness'] = list_books[4]
    
    
def z_consistency():
    global objects
    for i in range(5):
        for obj in objects[i]:
            obj.z = i
            if obj.fighter:
                for item in obj.fighter.inventory:
                    item.z = i
    
def set_player_on_upstairs(stair):
    global player
    
    if stair == 'ladder':
        for i in objects[player.z]:
            if i.name == 'upladder':
                player.x = i.x
                player.y = i.y
    else:
        for i in objects[player.z]:
            if i.name == 'upstairs':
                player.x = i.x
                player.y = i.y

def set_player_on_downstairs(stair):
    global player
    
    if (player.z == 8 or player.z == 15) and stair == 'ladder':
        for i in objects[player.z]:
            if i.name == 'ladder':
                player.x = i.x
                player.y = i.y
    else:
        for i in objects[player.z]:
            if i.name == 'stairs':
                player.x = i.x
                player.y = i.y
    
def next_level(stair):
    global player, special_dict
    
    objects[player.z].remove(player)
    
    if stair == 'stairs':    
        player.z += 1
       
    objects[player.z].append(player)
    set_player_on_upstairs(stair)
    message('You descend deeper into the heart of the dungeon...', 'blue')
    
    type = None
    for key, value in special_dict.iteritems():
        if value == player.z:
            type = key
    
    #------------------
    #level flavor
    
    if type == 'tangerine':
        message('You sense a place of fertility.', 'orange')
    elif type == 'house': 
        message('You hear a lot of voices chatting.', 'yellow')
    elif type == 'fountain':
        message('You hear water flowing.', 'blue')
    elif type == 'library':
        message('There is a place hoarding wisdom.', 'sky')
    elif type == 'temple':
        message('A place of holiness is near.', 'red')
    
    z_consistency()
    initialize_fov()

def prev_level(stair):
    global player
    
    if player.z == 0:
        score = 0
        for item in player.fighter.inventory:
            if item.name == 'The Bottle Of Holy Water':
                score += 100
            elif item.name == 'The Stone For Kronos':
                score += 100
            elif item.name == 'The Golden Tangerine':
                score += 100
            elif item.name == 'The Eternal Flame Of Hephaistos':
                score += 100
            elif item.name == 'A Frozen Breeze Of Air':
                score += 100
        
        if score:
            if score == 500:
                score += 500
            message('<3 Gluckwunsch!! You resurface and retrieve artifacts. You got a score of ' + str(score) + ' points!')
            win()
        else:
            message('You do not want to resurface without any of the 5 artifacts.')
            return

    objects[player.z].remove(player)
    
    if stair == 'stairs':              
        player.z -= 1  
            
    objects[player.z].append(player)    
    set_player_on_downstairs(stair)
    message('You go up the stairs cautiously.', 'blue')
    
    z_consistency()
    initialize_fov()

def initialize_fov():
    global fov_recompute, fov_map
    fov_recompute = True

    #create the FOV map, according to the generated map
    fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            libtcod.map_set_properties(fov_map, x, y, not map[player.z][x][y].block_sight, not map[player.z][x][y].blocked)
    
def play_game():
    global key, mouse, TURN_COUNT
    
    player_action = None
    
    #main loop
    while True:
        if game_state == 'exit':
            break
 
        #level up if needed
        check_level_up()
        
        ticker.ticks += 1
        ticker.next_turn()    
       
def intro_screen():
    img = libtcod.image_load('complogo.png')

    #show the background image, at twice the regular console resolution
    libtcod.image_blit_2x(img, 0, 0, 0)

    #present the root console to the player and wait for a key-press
    libtcod.console_flush()    
    key = libtcod.console_wait_for_keypress(True)

    # go on to main menu
    main_menu()
        
def main_menu():
    img = libtcod.image_load('title3.png')

    while True:
        #show the background image, at twice the regular console resolution
        T.layer(0)
        T.clear()
        T.set("0x00A7: tally.png, align=top-left");
        T.color('white')
        T.print_(0,0, '[U+00A7]')
        
        
        #show the game's title, and some credits!
        T.color('yellow')
        T.print_(SCREEN_WIDTH/2 + 20, SCREEN_HEIGHT/2-3, '[align=center]The Rogue of 5')
        T.print_(SCREEN_WIDTH/2, SCREEN_HEIGHT-2, '[align=center][color=green]#[color=white]IOLx3[color=yellow] Game by Jan | v1.0')
        
        options = ['Play a new game', 'Quit']
        
        #show options and wait for the player's choice
        choice = menu('', options, 10, None, SCREEN_WIDTH/2 + 10, SCREEN_HEIGHT/2 - 2)
        
        if choice == 0:  #new game
            new_game()
            play_game()
        # elif choice == 1:  #load last game
            # try:
                # load_game()
            # except:
                # msgbox('\n No saved game to load.\n', 24)
                # continue
            # play_game()
        elif choice == 1:  #quit
            break
                  
def win():
    global game_state
    
    for key, value in ident_table.iteritems():
        ident_table[key] = 0
    
    render_all()
    T.refresh()
    
    chosen_item = inventory_menu('Your possessions are identified.\n')
    
    msgbox('You conducted \n' + conducts['conduct1'] + '\n' + conducts['conduct2'] + '\n' + conducts['conduct3'] + '\n' + conducts['conduct4'] + '\n' + conducts['conduct5'] + '\n')
    game_state = 'exit'
    # while True:
        # key = T.read()
        # if key == T.TK_ENTER or key == T.TK_ESCAPE:
            # game_state = 'exit'
            # break 
T.open()
T.set("window: size=" + str(SCREEN_WIDTH) + "x" + str(SCREEN_HEIGHT) + ', title=The Rogue of 5')
T.set("font: courbd.ttf, size=" + str(FONT_SIZE))

main_menu()

