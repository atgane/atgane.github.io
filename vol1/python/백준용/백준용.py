import sys
import heapq

ssr = sys.stdin.readline
V, E = list(map(int, ssr().split()))
K = int(ssr())
graph = {}
for i in range(V):
    graph[i + 1] = {}
for i in range(E):
    tmp = list(map(int, ssr().split()))
    graph[tmp[0]][tmp[1]] = tmp[2]
print(graph)

def dijkstra(graph, start):
    distances = {node: float('inf') for node in graph}
    distances[start] = 0
    queue = []
    heapq.heappush(queue, [distances[start], start])

    while queue:
        current_distance, current_destination = heapq.heappop(queue)

        if distances[current_destination] < current_distance:
            continue
        
        for new_destination, new_distance in graph[current_destination].items():
            distance = current_distance + new_distance 
            if distance < distances[new_destination]: 
                distances[new_destination] = distance
                heapq.heappush(queue, [distance, new_destination]) 
        
    return distances

print(dijkstra(graph, K))