import sys
N = int(sys.stdin.readline())
num_list = list(map(int, sys.stdin.readline().split()))
stack = [0]
return_list = [-1 for _ in range(N + 1)]
