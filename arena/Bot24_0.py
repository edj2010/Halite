#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt
from hlt import constants
from hlt.positionals import Direction, Position
import logging

import random
import heapq
from collections import defaultdict, deque
import sys

# Initialize and start game
game = hlt.Game()

## Constants
RETURN_T = int(constants.MAX_HALITE * 0.8) # 1 to 1000
MINE_T = constants.MOVE_COST_RATIO * 5 # 1 to 1000
GROWTH = 1.0025

## Utility Functions
# Tells number of turns to mine square to desired level
def squareCost(halite, memo = dict()):
    if halite < MINE_T:
        return 1
    if halite in memo:
        return memo[halite]
    cost = squareCost(int(halite * (1.0 - 1.0 / constants.EXTRACT_RATIO))) + 1
    memo[halite] = cost
    return cost

def fastPow(a, b, memo = dict()):
    if b == 0:
        return 1
    if (a, b) in memo:
        return memo[(a, b)]
    if b % 2 == 1:
        memo[(a, b)] = fastPow(a, b-1)*a
        return memo[(a, b)]
    f = fastPow(a, b//2)
    memo[(a, b)] = f*f
    return f*f

# Command Module
# Used to issue orders to ships, manage collisions, and keep track of game state
class Command:

    # Initialize our command module and create/start game
    def __init__(self, game):
        self.commandQueue = list()
        self.occupiedSpaces = dict()
        self.game = game
        self.me =       None # needs to be updated each game loop
        self.game_map = None # needs to be updated each game loop
        self.shipyard = None # needs to be updated each game loop

    # Starts Turn. Must be run at beginning of game loop
    def startTurn(self):
        self.game.update_frame()
        self.me =       self.game.me
        self.game_map = self.game.game_map
        self.shipyard = self.me.shipyard

    # Returns True when ship has enough fuel to move
    def canMove(self, ship):
        return ship.halite_amount >= self.getHalitePos(ship.position) // constants.MOVE_COST_RATIO

    # Gets the Halite at a certain position
    def getHalitePos(self, pos):
        return self.game_map[pos].halite_amount

    # Builds a ship if none is present
    def buildShip(self):
        if self.shipyard.position in self.occupiedSpaces:
            return False
        else:
            self.commandQueue.append(self.shipyard.spawn())
            self.occupiedSpaces[self.shipyard.position] = 0
            return True

    # Moves ship to target location if no ships currently headed there
    def moveShip(self, ship, dir, unsafe = False):
        target = self.game_map.normalize(ship.position.directional_offset(dir))
        if (unsafe or target not in self.occupiedSpaces) and self.canMove(ship) :
            self.commandQueue.append(ship.move(dir))
            self.occupiedSpaces[target] = ship.id
            return True
        else:
            return False

    # Holds ship steady if no ships currently headed towards our ship
    def holdShip(self, ship):
        if ship.position not in self.occupiedSpaces:
            self.commandQueue.append(ship.stay_still())
            self.occupiedSpaces[ship.position] = ship.id
            return True
        else:
            return False

    # Moves ship towards target. Uses naive unsafe movement
    # allows for reversed order of movement preference for very simple optimization
    def moveShipTowards(self, ship, pos, unsafe = False, reverse = False):
        # assumes not at position
        moves = self.game_map.get_unsafe_moves(ship.position, pos)
        if reverse:
            moves = reversed(moves)
        for dir in moves:
            if self.moveShip(ship, dir):
                return True
        return False

    def moveShipSmart(self, ship, target, unsafe = False):
        # Used for seen and keeps track of which cell the best path came from
        # Except for initial cells which contain direction
        prevCell = dict()
        # Cells still to be searched
        toSearch = list()

        def cost(halite, distance):
            adjustedInv = (ship.halite_amount - halite)/fastPow(GROWTH, distance)
            return ship.halite_amount - adjustedInv

        def heuristic(pos, halite, distance):
            furtherDistance = self.game_map.calculate_distance(target, pos)
            newDistance = distance + furtherDistance
            expHalite = int((MINE_T + MINE_T * (1.0 - 1.0 / constants.EXTRACT_RATIO))/2.0)
            newHalite = halite + furtherDistance * expHalite // constants.MOVE_COST_RATIO
            return cost(newHalite, newDistance)

        # Add initial cells to search space
        for dir in Direction.get_all_cardinals():
            newPos = self.game_map.normalize(ship.position.directional_offset(dir))
            halite = self.game_map[ship.position].halite_amount // constants.MOVE_COST_RATIO
            distance = 1
            Cost = cost(halite, distance)
            heapq.heappush(toSearch, (heuristic(newPos, halite, distance), halite, distance, newPos))
            prevCell[newPos] = (Cost, ship.position, dir)

        curr = target
        # Search for target
        while toSearch:
            adjCost, halite, distance, pos = heapq.heappop(toSearch)
            if pos == target:
                curr = pos
                break
            for dir in Direction.get_all_cardinals():
                newPos = self.game_map.normalize(pos.directional_offset(dir))
                newHalite = halite + self.game_map[pos].halite_amount // constants.MOVE_COST_RATIO
                newDistance = distance + 1
                Cost = cost(newHalite, newDistance)
                if newPos not in prevCell:
                    heapq.heappush(toSearch, (heuristic(newPos, newHalite, newDistance), newHalite, newDistance, newPos))
                    prevCell[newPos] = (Cost, pos, dir)
                else:
                    prevCell[newPos] = min(prevCell[newPos], (Cost, pos, dir))
            logging.info(prevCell)


        # Find original cell
        while prevCell[curr][1] != ship.position:
            logging.info(curr)
            curr = prevCell[curr][1]

        return self.moveShip(ship, prevCell[curr][2])

    # Gets the list of ships
    def getShips(self):
        return self.me.get_ships()

    # Gets turn number
    def getTurn(self):
        return self.game.turn_number

    # Gets the quantity of halite
    def getHalite(self):
        return self.me.halite_amount

    # Gets a ship by ID
    def getShip(self, shipID):
        return self.me.get_ship(shipID)

    # Must be run at end of game cycle. Sends commands to game object
    def endTurn(self):
        logging.info(self.commandQueue)
        self.game.end_turn(self.commandQueue)
        self.commandQueue = list()
        self.occupiedSpaces = dict()

# Holds ordered orders for ships in the fleet
# Orders are stored in the following pattern
# All orders are a 3-tuple
# The first element is a string describing the order
# Options include
#   'mine'  (mine an area),
#   'move'  (move to a location)
#   'hold'  (stay in one spot)
#   'rand'  (move in a random direction)
#   'done'  (come to nearest dropoff/shipyard, crashing ok)
#   'drop'  (unimplimented, builds a dropoff point at location)
# The second element is the location (for 'move', 'mine', and 'drop') and irrelevent otherwise
# The third element is another order, to be executed if the first order fails (causes a collision)
# This can be left blank, if hold is the desired action and collisions are acceptable

class Fleet:
    
    # Initializes Fleet Orders
    def __init__(self, command_module):
        self.command = command_module
        self.fleetOrders = dict() # ship.id: order tuple
        self.targets = list() # [..., [score, target, shipID], ...]
        self.initTargets()

    # Updates our orders dictionary to remove any ships not currently present and add new ships
    def updateShipList(self):
        ids = set(self.fleetOrders.keys())
        for ship in self.command.getShips():
            if ship.id in ids:
                ids.remove(ship.id)
            else:
                self.fleetOrders[ship.id] = None    # Initialize dictionary space
        for ID in ids:
            self.fleetOrders[ID] = None          # Clear orders
            self.unassignShip(ID)

    # Unclaims the specific target so another ship can claim it
    def unassignShip(self, ID):
        for i in range(len(self.targets)):
            if self.targets[i][2] == ID:
                self.targets[i][2] = None
                break

    # Assigns ship to specified target location
    def assignShip(self, ID, target):
        logging.info(str(ID) + ": " + str(target))
        for i in range(len(self.targets)):
            if self.targets[i][1] == target:
                self.targets[i][2] = ID

    # Used to determine if the ship is inside the region specified by the coordinate
    # Currently just means equal to coordinate, but will be extended
    def inRegion(self, shipPos, regPos):
        return shipPos == regPos

    # Executes the order for a ship that already has orders
    # Assumes ship has an order, otherwise errors
    # Contains logic for executing orders and transitioning between orders
    def _executeOrder(self, ship, order):
        if not order:
            return  # Only happens when no order to give
        command, pos, backup = order
        if command == 'mine': # Mine a specific target/region
            # At target
            if self.inRegion(ship.position, pos):
                # Mineable
                if self.goodTarget(pos) and ship.halite_amount < RETURN_T:
                    if not self.command.holdShip(ship):
                        # Backup plan
                        self._executeOrder(ship, backup)
                        return
                elif ship.halite_amount >= RETURN_T:
                    # Ship issued a return order
                    self.unassignShip(ship.id)
                    self.fleetOrders[ship.id] = ('move', self.command.shipyard.position, ('hold', None, ('rand', None, None)))
                    self._executeOrder(ship, self.fleetOrders[ship.id])
                else:
                    # Ship told to find a nearby target
                    target = self.findNearTarget(ship)
                    self.unassignShip(ship.id)
                    if target:
                        # Target Found
                        self.assignShip(ship.id, target)
                        self.fleetOrders[ship.id] = ('mine', target, ('rand', None, ('hold', None, None)))
                    else:
                        # Return home
                        self.fleetOrders[ship.id] = ('move', self.command.shipyard.position, ('hold', None, ('rand', None, None)))
                    self._executeOrder(ship, self.fleetOrders[ship.id])
            else:
                # Mine if space above threshold
                if self.goodTarget(ship.position) and ship.halite_amount < RETURN_T:
                    if not self.command.holdShip(ship):
                        self._executeOrder(ship, backup)
                        return
                elif ship.halite_amount >= RETURN_T:
                    # Ship issued a return order
                    self.unassignShip(ship.id)
                    self.fleetOrders[ship.id] = ('move', self.command.shipyard.position, ('hold', None, ('rand', None, None)))
                    self._executeOrder(ship, self.fleetOrders[ship.id])
                elif not self.command.moveShipTowards(ship, pos):
                    self._executeOrder(ship, backup)
                    return
            
        elif command == 'move': # Move to a specific place
            if ship.position == pos:
                self.issueNewCommand(ship)
            else:
                if not self.command.moveShipSmart(ship, pos):
                    self._executeOrder(ship, backup)
                    return

        elif command == 'hold': # Stay Still
            if not self.command.holdShip(ship):
                self._executeOrder(ship, backup)
                return
        
        elif command == 'rand': # Move in a random direction
            moved = False
            dirs = Direction.get_all_cardinals()
            random.shuffle(dirs)
            for dir in dirs:
                if self.command.moveShip(ship, dir):
                    moved = True
                    break
            if not moved:
                self._executeOrder(ship, backup)
                return

        elif command == 'done': # Move ship towards home, disregarding crashes
            if not self.command.moveShipTowards(ship, self.command.shipyard.position, unsafe = True):
                self.command.holdShip(ship)

        elif command == 'drop': # Unimplemented
            a = 1

        else:
            logging.info(f"Illegal Command {command} Given to ship {ship.id}")

    # Issues new command to ship, since it has completed it's last one
    # Contains high level strategy like choosing targets
    def issueNewCommand(self, ship):
        for i in range(len(self.targets)):
            if self.targets[i][2] == None:
                self.targets[i][2] = ship.id
                logging.info(str(ship.id) + ': ' + str(self.targets[i][1]))
                self.fleetOrders[ship.id] = ('mine', self.targets[i][1], ('rand', None, ('hold', None, None)))
                self._executeOrder(ship, self.fleetOrders[ship.id])
                break

    # Checks whether a certain position has a ship assigned already
    def posAssigned(self, pos):
        for i in range(len(self.targets)):
            if self.targets[i][1] == pos:
                return self.targets[i][2] != None
        return False

    # Finds nearby squares that are good targets for mining
    # Returns said target
    def findNearTarget(self, ship, maxDis=10):
        toSearch = deque()
        seen = set()
        toSearch.append((0, ship.position))
        seen.add(ship.position)

        def metric(pos):
            halite = self.command.getHalitePos(pos)# - MINE_T
            #distance = (self.command.game_map.calculate_distance(pos, self.command.shipyard.position) + self.command.game_map.calculate_distance(pos, ship.position) + 1) 
            distance = (self.command.game_map.calculate_distance(pos, ship.position) + 1)
            return halite/distance

        bestSquare = (metric(ship.position), ship.position)
        while toSearch:
            depth, pos = toSearch.popleft()
            if not self.posAssigned(pos):
                bestSquare = max((metric(pos), pos), bestSquare)
            if depth < maxDis:
                for dir in Direction.get_all_cardinals():
                    newPos = self.command.game_map.normalize(pos.directional_offset(dir))
                    if newPos not in seen:
                        seen.add(newPos)
                        toSearch.append((depth+1, newPos))
        if bestSquare[1] != ship.position:
            return bestSquare[1]
        return None


    # Returns whether it is worth it to keep mining a square
    def goodTarget(self, target):
        return self.command.getHalitePos(target) >= MINE_T

    # returns the amount of halite present squared over the distance
    def evalTarget(self, target):
        halite = self.command.getHalitePos(target)# - MINE_T
        distance = (self.command.game_map.calculate_distance(self.command.shipyard.position, target) + 1)
        return halite/distance

    # sorts targets by value
    def sortTargets(self):
        self.targets.sort(reverse = True)

    # updates the valuation of all targets
    def computeTargets(self):
        for i in range(len(self.targets)):
            self.targets[i][0] = self.evalTarget(self.targets[i][1])

    # completely updates the target list
    def updateTargets(self):
        self.computeTargets()
        self.sortTargets()

    # initializes the list of targets
    def initTargets(self):
        cap = self.command.game.game_map.height
        for i in range(0, cap, 1):
            for j in range(0, cap, 1):
                self.targets.append([None, Position(i, j), None])

    # executes the next turn for every bot
    def executeFleetOrders(self):
        unProcessed = list()
        for ship in self.command.getShips():
            if not self.command.canMove(ship):
                self.command.holdShip(ship)
            else:
                unProcessed.append(ship)
        for ship in unProcessed:
            if ship.id in self.fleetOrders and self.fleetOrders[ship.id]:
                self._executeOrder(ship, self.fleetOrders[ship.id])
            else:
                logging.info(f"New Command for ship {ship.id}")
                self.issueNewCommand(ship)
        
        logging.info(self.fleetOrders)

    # build ships when appropriate
    def buildShips(self):
        if self.command.me.halite_amount >= constants.SHIP_COST and self.command.game.turn_number < constants.MAX_TURNS * 0.4:
            self.command.buildShip()

    # executes turn
    def executeTurn(self):
        self.updateShipList()
        self.updateTargets()
        self.executeFleetOrders()
        self.buildShips()


# Initialize command Module (starts game)
game.ready("Bobert")
command = Command(game)

# Initialize the fleet
fleet = Fleet(command)

while True:
    command.startTurn()
    fleet.executeTurn()
    command.endTurn()
