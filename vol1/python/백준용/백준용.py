import sys
ssr = sys.stdin.readline
V, E = list(map(int, ssr().split()))
K = int(ssr())
graph = [list(map(int, ssr().split())) for _ in range(E)]
print(graph)



