

# example of item
Item = {
    'char': 'x',
    'name': 'item',
    'color': 'black',
    'equipment': False,
    'use_function': None,
    'ignite_function': None,
    'flammable_prob': 50,
    'conditions': [None, 'damaged']
    }


the_bottle_of_holy_water = {
    'char': '1',
    'name': 'The Bottle Of Holy Water',
    'color': 'blue'
    }
    
the_golden_tangerine = {
    'char': '2',
    'name': 'The Golden Tangerine',
    'color': 'orange'
    }
    
a_frozen_breeze_of_air = {
    'char': '3',
    'name': 'A Frozen Breeze Of Air',
    'color': 'sky'
    }
    
the_eternal_flame_of_hephaistos = {
    'char': '4',
    'name': 'The Eternal Flame Of Hephaistos',
    'color': 'red'
    }
    
the_stone_for_kronos = {
    'char': '5',
    'name': 'The Stone For Kronos',
    'color': 'yellow'
    }
    
book_of_make_tangerine_potion = {
    'char': '+',
    'name': 'book of make tangerine potion',
    'color': 'orange',
    'equipment': True,
    'slot': 'left hand',
    'spell_function': 'make_tangerine_potion'
    }
   
book_of_healing = {
    'char': '+',
    'name': 'book of healing',
    'color': 'orange',
    'equipment': True,
    'slot': 'left hand',
    'spell_function': 'cast_heal'
    }
    
book_of_sunfire = {
    'char': '+',
    'name': 'book of sunfire',
    'color': 'orange',
    'equipment': True,
    'slot': 'left hand',
    'spell_function': 'sunfire'
    }
    

book_of_waterjet = {
    'char': '+',
    'name': 'book of waterjet',
    'color': 'orange',
    'equipment': True,
    'slot': 'left hand',
    'spell_function': 'book_waterjet'
    }
    
book_of_weakness = {
    'char': '+',
    'name': 'book of weakness',
    'color': 'orange',
    'equipment': True,
    'slot': 'left hand',
    'spell_function': 'weaken'
    }
    
scroll_of_earth = {
    'char': '?',
    'name': 'scroll of earth',
    'color': 'white',
    'item': True,
    'use_function': 'earth_wall',
    'stackable': True
    }
    
scroll_of_light = {
    'char': '?',
    'name': 'scroll of light',
    'color': 'white',
    'item': True,
    'use_function': 'light_flash',
    'stackable': True
    }
    
scroll_of_identify = {
    'char': '?',
    'name': 'scroll of identify',
    'color': 'white',
    'item': True,
    'use_function': 'scroll_identify',
    'stackable': True
    }
    
scroll_of_enchantment = {
    'char': '?',
    'name': 'scroll of enchantment',
    'color': 'white',
    'item': True,
    'use_function': 'scroll_enchant',
    'stackable': True
    }

scroll_of_teleport = {
    'char': '?',
    'name': 'scroll of teleport',
    'color': 'white',
    'item': True,
    'use_function': 'scroll_teleport',
    'stackable': True
    }
    
wand_of_air = {
    'char': '/',
    'name': 'wand of air',
    'color': 'sky',
    'item': True,
    'charges': 5,
    'use_function': 'wand_air'
    }
    
wand_of_waterjet = {
    'char': '/',
    'name': 'wand of waterjet',
    'color': 'sky',
    'item': True,
    'charges': 5,
    'use_function': 'wand_waterjet'
    }
    
wand_of_digging = {
    'char': '/',
    'name': 'wand of digging',
    'color': 'sky',
    'item': True,
    'charges': 5,
    'use_function': 'wand_digging'
    }
    
wand_of_polymorph = {
    'char': '/',
    'name': 'wand of polymorph',
    'color': 'sky',
    'item': True,
    'charges': 5,
    'use_function': 'wand_polymorph'
    }
    
wand_of_fireball = {
    'char': '/',
    'name': 'wand of fireball',
    'color': 'sky',
    'item': True,
    'charges': 5,
    'use_function': 'wand_fireball'
    }
    
cloth_armor = {
    'char': '[U+005B]',
    'name': 'cloth armor',
    'color': 'grey',
    'equipment': True,
    'slot': 'body',
    'armor_bonus': 1,
    'spirit_bonus': 5
    }
    
leather_armor = {
    'char': '[U+005B]',
    'name': 'leather armor',
    'color': 'grey',
    'equipment': True,
    'slot': 'body',
    'armor_bonus': 2,
    'wit_bonus': -1
    }     
    
chain_armor = {
    'char': '[U+005B]',
    'name': 'chain armor',
    'color': 'grey',
    'equipment': True,
    'slot': 'body',
    'armor_bonus': 3,
    'wit_bonus': -3
    }     
    
plate_armor = {
    'char': '[U+005B]',
    'name': 'plate armor',
    'color': 'grey',
    'equipment': True,
    'slot': 'body',
    'armor_bonus': 4,
    'wit_bonus': -5,
    'element_enchant': True
    }     
    
mithril_armor = {
    'char': '[U+005B]',
    'name': 'mithril armor',
    'color': 'light grey',
    'equipment': True,
    'slot': 'body',
    'armor_bonus': 5,
    'wit_bonus': -2
    }     
    
potion_of_healing = {
    'char': '!',
    'name': 'potion of healing',
    'color': 'blue',
    'item': True,
    'use_function': 'drink_heal',
    'stackable': True
    }
    
potion_of_invisibility = {
    'char': '!',
    'name': 'potion of invisibility',
    'color': 'blue',
    'item': True,
    'use_function': 'invisipotion',
    'stackable': True
    }
    
potion_of_tangerine_juice = {
    'char': '!',
    'name': 'potion of tangerine juice',
    'color': 'blue',
    'item': True,
    'use_function': 'consume_food',
    'stackable': True
    }
    
potion_of_berserk_rage = {
    'char': '!',
    'name': 'potion of berserk rage',
    'color': 'blue',
    'item': True,
    'use_function': 'berserk_potion',
    'stackable': True
    }
    
potion_of_magma = {
    'char': '!',
    'name': 'potion of magma',
    'color': 'blue',
    'item': True,
    'use_function': 'drink_magma',
    'stackable': True
    }
    
dagger = {
    'char': ')',
    'name': 'dagger',
    'color': 'grey',
    'equipment': True,
    'slot': 'right hand',
    'damage_bonus': 1,
    'element_enchant': True
    }

sword = {
    'char': ')',
    'name': 'sword',
    'color': 'grey',
    'equipment': True,
    'slot': 'right hand',
    'damage_bonus': 3,
    'element_enchant': True
    }

staff = {
    'char': ')',
    'name': 'staff',
    'color': 'grey',
    'equipment': True,
    'slot': 'right hand',
    'damage_bonus': 2,
    'spirit_bonus': 2,
    'element_enchant': True
    }
   
mace = {
    'char': ')',
    'name': 'mace',
    'color': 'grey',
    'equipment': True,
    'slot': 'right hand',
    'damage_bonus': 4,
    'element_enchant': True
    }
    
zweihander = {
    'char': ')',
    'name': 'zweihander',
    'color': 'grey',
    'equipment': True,
    'slot': 'both hands',
    'damage_bonus': 5,
    'element_enchant': True
    }
    
lucky_ring = {
    'char': '=',
    'name': 'lucky ring',
    'color': 'yellow',
    'equipment': True,
    'slot': 'finger'
    }
    
hunger_ring = {
    'char': '=',
    'name': 'hunger ring',
    'color': 'yellow',
    'equipment': True,
    'slot': 'finger'
    }
    
ring_of_strength = {
    'char': '=',
    'name': 'ring of strength',
    'color': 'yellow',
    'equipment': True,
    'strength_bonus': 10,
    'slot': 'finger'
    }
    
ring_of_invisibility = {
    'char': '=',
    'name': 'ring of invisibility',
    'color': 'yellow',
    'equipment': True,
    'slot': 'finger'
    }
    
ring_of_fire_resistance = {
    'char': '=',
    'name': 'ring of fire resistance',
    'color': 'yellow',
    'equipment': True,
    'slot': 'finger'
    }
    
nerd_glasses = {
    'char': '(',
    'name': 'nerd glasses',
    'color': 'magenta',
    'equipment': True,
    'wit_bonus': 10,
    'slot': 'eyes'
    }
    
glasses_of_telepathy = {
    'char': '(',
    'name': 'glasses of telepathy',
    'color': 'magenta',
    'equipment': True,
    'slot': 'eyes'
    }
    
sunglasses_of_elemental_protection = {
    'char': '(',
    'name': 'sunglasses of elemental protection',
    'color': 'magenta',
    'equipment': True,
    'slot': 'eyes'
    }
    
lenses_of_see_invisible = {
    'char': '(',
    'name': 'lenses of see invisible',
    'color': 'magenta',
    'equipment': True,
    'slot': 'eyes'
    }

Xray_visor = {
    'char': '(',
    'name': 'Xray visor',
    'color': 'magenta',
    'equipment': True,
    'slot': 'eyes'
    }   
 
altar = {
    'char': '_',
    'name': 'altar',
    'color': 'white'
    }   
    
fountain = {
    'char': '{',
    'name': 'fountain',
    'color': 'blue'
    }   
 