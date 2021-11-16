
# monster = {
    # 'hp': 1, 'damage': 1, 'armor': 2, 'wit': 10, 'stamina': 10, 'spirit': 20,
    # 'death_function': 'monster_death',
    # 'phys_damage_factor': 0.2,
    # 'fire_damage_factor': 2,
    # 'ai': 'BasicMonster',
    # 'char': 'M',
    # 'name': 'monster',
    # 'color': 'white',
    # 'speed': 6,
    # 'fire_being': False,
    # 'inventory': [  ('monster_item', 99), #name in items.py and probability, that monster has it 
                    # ('monster_weapon', 80), 
                    # ('monster_scroll', 10) ]
    # }    

kobold = {'stat_points': 5, 
    'spirit': 2,
    'death_function': 'monster_death', 
    'ai': 'AIkobold',
    'char': 'k',
    'name': 'kobold',
    'speed': 9,
    'color': 'orange',
    'xp': 1,
    'inventory': [ ('dagger', 100), ('sword', 5)]
    }    
    
goblin = {'stat_points': 10,  
    'spirit': 2,
    'death_function': 'monster_death', 
    'ai': 'AIgoblin',
    'char': 'g',
    'name': 'goblin',
    'speed': 6,
    'color': 'green',
    'xp': 10,
    'inventory': [ ('dagger', 100), ('sword', 50), ('potion', 40), ('potion', 10)   ]
    }    
    
orc = {'stat_points': 20, 
    'spirit': 2,
    'death_function': 'monster_death', 
    'ai': 'AIorc',
    'char': 'o',
    'name': 'orc',
    'speed': 6,
    'color': 'green',
    'xp': 15,
    'skill': 1,
    'inventory': [ ('sword', 100), ('mace', 20), ('potion', 40), ('potion', 10), ('leather_armor', 50), ('chain_armor', 50), ('wand', 25) ]
    }    
 
 
human = {'stat_points': 35,
    'spirit': 2,
    'death_function': 'monster_death', 
    'ai': 'AIhuman',
    'char': 'H',
    'name': 'human',
    'speed': 6,
    'color': 'magenta',
    'xp': 20,
    'skill': 2,
    'inventory': [ ('sword', 100), ('mace', 50), ('zweihander', 50), ('ring', 95), ('leather_armor', 50), ('chain_armor', 50), ('plate_armor', 50), ('wand', 20), ('scroll', 20), ('potion', 20), ('potion', 5)  ]
    }    
 
priest = {'stat_points': 35,
    'spirit': 2,
    'death_function': 'monster_death', 
    'ai': 'AINPC',
    'char': 'H',
    'name': 'priest',
    'speed': 18,
    'color': 'white',
    'xp': 20,
    'skill': 2,
    'inventory': [ ('mace', 100), ('chain_armor', 100), ('potion_of_healing', 100), ('book_of_healing', 100), ('scroll', 100),('scroll', 100),('scroll', 100) ]
    }    
    
elf = {'stat_points': 50, 
    'spirit': 15,
    'death_function': 'monster_death', 
    'ai': 'AIelf',
    'char': 'E',
    'name': 'elf',
    'speed': 6,
    'color': 'light green',
    'xp': 25,
    'skill': 3,
    'inventory': [ ('dagger', 100), ('staff', 50), ('dagger', 50), ('ring', 100), ('glasses', 100), ('cloth_armor', 50), ('mithril_armor', 50), ('wand', 20), ('scroll', 20), ('potion', 20), ('potion', 10), ('spellbook', 50) ]
    }    