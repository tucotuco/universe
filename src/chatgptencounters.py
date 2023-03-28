#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random

class Character:
    def __init__(self, name, race, clas):
        self.name = name
        self.race = race
        self.clas = clas
        self.hp = random.randint(1, 20)
        self.mp = random.randint(1, 10)
        self.strength = random.randint(1, 20)
        self.intelligence = random.randint(1, 20)
        self.dexterity = random.randint(1, 20)
        self.is_alive = True
        
    def attack(self, target):
        damage = self.strength + random.randint(0, 6)
        target.hp -= damage
        print(f"{self.name} attacked {target.name} for {damage} damage!")
        if target.hp <= 0:
            target.is_alive = False
            print(f"{target.name} has been defeated!")

races = ["Human", "Elf", "Dwarf", "Orc"]
classes = ["Warrior", "Mage", "Thief", "Cleric"]

def generate_random_character():
    name = "Random" + str(random.randint(1,100))
    race = random.choice(races)
    clas = random.choice(classes)
    return Character(name, race, clas)

player1 = generate_random_character()
player2 = generate_random_character()

while player1.is_alive and player2.is_alive:
    player1.attack(player2)
    if player2.is_alive:
        player2.attack(player1)

if player1.is_alive:
    print(f"{player1.name} is victorious!")
else:
    print(f"{player2.name} is victorious!")

