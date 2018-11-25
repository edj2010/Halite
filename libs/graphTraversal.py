from collections import deque
from heapq import *

# Extracts path from result
def getPath(cameFrom, end):
    
    path = list()

    while end in cameFrom:
        end = cameFrom[end]
        path.append(end)

    return path

# A* search
def astar(start, end, graph, heuristicf, costf, disf, adjf):
    seen = set()
    searched = set()
    cameFrom = dict()
    toSearch = list() # heap
    

    tCost = dict() # total cost so far
    hCost = dict() # total cost so far plus heuristic cost for the rest

    dis = disf(start, graph)

    tCost[start] = costf(0, start, start, dis, graph)
    hCost[start] = heuristicf(tCost[start], start, end, dis, graph)

    heappush(toSearch, (hCost[start], dis, start))
    seen.add(start)

    while toSearch:
        _, dis, curr = heappop(toSearch)

        if curr == end:
            return getPath(cameFrom, end)

        searched.add(curr)
        for neighbor in adjf(graph, curr):
            nDis = dis + disf(neighbor, graph)
            nTCost = costf(tCost[curr], curr, neighbor, nDis, graph)
            
            if neighbor in seen and nTCost >= tCost[neighbor]:
                continue

            cameFrom[neighbor] = curr
            tCost[neighbor] = nTCost
            hCost[neighbor] = heuristicf(tCost[neighbor], neighbor, end, nDis, graph)

            if neighbor not in seen:
                seen.add(neighbor)
                heapq.heappush(toSearch, (hCost[neighbor], nDis, neighbor))

# Finds the highest valued square within maxDepth of start
# Returns path to that square
def bfs_best(start, graph, valf, disf, adjf, maxDepth=0):
    seen = set()
    cameFrom = dict()
    toSearch = deque()

    val = dict()
    dis = dict()
    dis[start] = disf(start, graph)
    val[start] = valf(start, dis, graph)

    toSearch.append((start, 0))
    seen.add(start)

    best = (val[start], start)

    while toSearch:
        curr, depth = toSearch.popleft()
        
        best = max(best, (val[curr], curr))

        if depth == maxDepth:
            continue

        for neighbor in adjf(graph, curr):
            nDis = dis + disf(neighbor, graph)
            nVal = valf(neighbor, nDis, graph)

            if neighbor not in seen or nVal > val[neighbor]:
                val[neighbor] = nVal
                dis[neighbor] = nDis
                cameFrom[neighbor] = curr

            if neighbor not in seen:
                toSearch.append((neighbor, depth + 1))
                seen.add(neighbor)

    return getPath(cameFrom, best[1])
