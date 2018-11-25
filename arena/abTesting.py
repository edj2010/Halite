from multiprocessing.pool import ThreadPool 
from multiprocessing import Value, Lock, Array 
import subprocess
import time 
import sys 
import random 
import json

class CompareBots():
    def __init__(self, shipOne, shipTwo, initialParameters, geneticAlgo=True): 
        self.shipOne = shipOne
        self.shipTwo = shipTwo
        self.initialParameters = initialParameters
        self.geneticAlgo = geneticAlgo

    def runGame(self, info):
        if self.geneticAlgo:  
            parameters = info[4] 
            s = " ".join(map(str, parameters))
            botOne = f"\"python3 {self.shipOne} {s}\""
        else: 
            botOne = f"\"python3 {self.shipOne}\""
        print(botOne)
        
        args = "-vvv --no-logs --results-as-json --width 32 --height 32"
        
        botTwo = f"\"python3 {self.shipTwo}\""

        with subprocess.Popen(f"./halite {args} {botOne} {botTwo}", shell=True, stdout=subprocess.PIPE) as proc: 
            results = json.loads(proc.stdout.read())
            print("Done!")
            # print(results)
            if results["stats"]["0"]["rank"] == 1: 
                with info[1]: 
                    info[0].value += 1
            
            # Array is stored in info[2]
            if self.geneticAlgo:
                info[2][info[3]] = (results["stats"]["0"]["score"]+1) / (results["stats"]["1"]["score"]+1) 
            
    def perturb_parameters(self, parameters): 
        return  [random.uniform(.9, 1.1) * x for x in parameters] 

    def median(self, L): 
        L = sorted(L)
        return L[len(L) // 2]

    def run(self):          
        bots_per_generation = 5
        num_generations = 8
        games_per_bot = 5
        print("Starting...")

        count = 0 
        pool = ThreadPool()
        lock = Lock()

        array = Array("f", [0]*bots_per_generation)
        val = Value("i", 0)

        if self.geneticAlgo: 
            best_parameters = self.initialParameters

        for i in range(num_generations):
            print(f"Generation {i}.")
            if self.geneticAlgo:
                scores = [[] for _ in range(bots_per_generation)]
                parameters = [self.perturb_parameters(best_parameters) for i in range(bots_per_generation)]
                for j in range(games_per_bot): 
                    pool.map(self.runGame, [(val, lock, array, i, parameters[i]) for i in range(bots_per_generation)])
                    
                    for index, score in enumerate(array[:]): 
                        scores[index].append(score)
                    print(scores)
                
                # Take median of 5 games as the actual score  
                scores = list(map(self.median, scores))
                print(scores) 

                best_parameters = parameters[scores.index(max(scores))]
                print(best_parameters)
            else: 
                pool.map(self.runGame, [(val, lock) for i in range(bots_per_generation)])

        print(f"Player Zero Wins: {val.value}")
        print(f"Player One Wins: {num_generations * bots_per_generation * games_per_bot - val.value}")
        
if __name__ == "__main__":
    # Bot to optimize
    botOne = "MyBot.py"

    # Bot to compare the first bot to
    botTwo = "OldBot.py" 

    initial_parameters = [0.9, 4.5, 0.5, 0.0025]
    for index, arg in enumerate(sys.argv[1:]):
        if index == 0:
            botOne = arg
        elif index == 1: 
            botTwo = arg
        elif index == 2: 
            initial_parameters = list(map(float, arg.split(",")))

    compare = CompareBots(botOne, botTwo, initial_parameters, False)
    compare.run()
    
