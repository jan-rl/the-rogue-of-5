# This module contains the Tile class 
#
#


class Tile:
    #a tile of the map and its properties
    def __init__(self, blocked, block_sight = None, type='dummy', name='dummy' ):
        self.blocked = blocked

        #all tiles start unexplored
        self.explored = False

        #by default, if a tile is blocked, it also blocks sight
        if block_sight is None: block_sight = blocked
        self.block_sight = block_sight
        
        #self.type = type #terrain options set in make_map() to show different appearance in render_all()
        
        self.name = name
        
        self.air = True
        self.air_count = 0
        
        self.change_type(type)
        
    def refill_air(self):
        if self.air_count > 0:
            self.air_count -= 1
            if self.air_count == 0:
                self.air = True
            return
            
    def change_type(self, type):    
        self.type = type
        
        if type == 'empty': #empty tile
            self.name = 'empty'
            self.char_light = '.'
            self.char_dark = ' '
            self.color_light = 'grey'
            self.color_dark = 'white'
            self.blocked = False
            self.block_sight = False

        elif type == 'rock wall':
            self.name = 'wall'
            self.char_light = '#'
            self.char_dark = '#'
            self.color_light = 'grey'
            self.color_dark = 'dark grey'
            self.blocked = True
            self.block_sight = True

        elif type == 'horizontal wall':
            self.name = 'wall'
            self.char_light = '-'
            self.char_dark = '-'
            self.color_light = 'grey'
            self.color_dark = 'dark grey'
            self.blocked = True
            self.block_sight = True
        
        elif type == 'vertical wall':
            self.name = 'wall'
            self.char_light = '|'
            self.char_dark = '|'
            self.color_light = 'grey'
            self.color_dark = 'dark grey'
            self.blocked = True
            self.block_sight = True

         
        else:
            self.name = 'dummy'
            self.char_light = '/'
            self.char_dark = '/'
            self.color_light = 'white'
            self.color_dark = 'blue'
            self.blocked = False
            self.block_sight = False
