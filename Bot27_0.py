#!/usr/bin/env python3
# Python 3.6

# Import Halite SDK
import hlt
from hlt import constants
from hlt.positionals import Direction, Position
import logging

# Initialize and start game
game = hlt.game()

## Constants

## Field Class
# Used to store information about the game map
class Field:

    # Initialize relevant values to field
    def __init__(self):
        self.game_map = None
        self.shipyard = None

    # Updates relevant parts of the field at the beginning of each turn
    def updateField(self, game):
        self.game_map = game.game_map
        self.shipyard = game.me.shipyard

    # Computes and normalizes the directional offset
    def offset(self, pos, dir):
        return self.game_map.normalize(pos.directional_offset(dir))

## Command Class
# Used to issue commands to ships
class Command:

    # Initialize our command module
    def __init__(self, game):
        self.commandQueue = list()
        self.occupiedSpaces = set()
        self.game = game
        self.field = Field()
        
        self.me = None

    # Starts turn, gets new values for relevant field information, must be run to start turn
    def startTurn(self):
        self.game.update_frame()
        self.me = self.game.me
        self.field.updateField(self.game)

    # Ends turn, submitting commands in command queue
    def endTurn(self):
        self.game.end_turn(self.commandQueue)
        self.commandQueue = list()
        self.occupiedSpaces = set()

    # Returns True when ship has enough fuel to move
    # if unsafe = False, also checks to make sure no ships in target square
    def canMove(self, ship, target = None, unsafe = False):
        halite = self.field.haliteAt(ship.position)
        able = (ship.halite_amount >= halite // constants.MOVE_COST_RATIO)
        if target and not unsafe:
            able &= (target not in self.occupiedSpaces)
        return able

    # Builds a ship if possible
    def buildShip(self):
        if self.Field.shipyard.position in self.occupiedSpaces:
            return False
        else:
            self.commandQueue.append(self.Field.shipyard.spawn())
            self.occupiedSpaces.add(self.shipyard.position)
            return True

    # Moves ship if possible
    def moveShip(self, ship, dir, unsafe = False):
        target = self.Field.offset(ship.position, dir)
        if canMove(ship, target, unsafe):
            self.commandQueue.append(ship.move(dir))
            self.occupiedSpaces.add(target)
            return True
        else:
            return False

    # Holds ship if possible
    def holdShip(self, ship):
        if ship.position not in self.occupiedSpaces:
            self.commandQueue.append(ship.stay_still())
            self.occupiedSpaces.add(ship.position)
            return True
        else:
            return False

    # Moves ship towards target
    def moveShipTowards(self, ship, target, unsafe = False):
        for dir in self.Field.game_map.get_unsafe_moves(ship.position, target):
            if self.moveShip(ship, dir):
                return True
        return False

    # Get list of ships
    def getShips(self):
        return self.me.get_ships()

    # Get turs number
    def getTurn(self):
        return self.game.turn_number

    # Gets quantity of halite stored
    def getHalite(self):
        return self.me.halite_amount

    # Gets a ship by ID
    def getShip(self, shipID):
        return self.me.get_ship(shipID)

# Holds orders for ship's fleet
class Fleet
