from collections import deque
N, M = list(map(int, input().split()))
D = deque([i for i in range(1, N + 1)])
C = 0

def move_r():
    tmp = D.popleft()
    D.append(tmp)

def move_l():
    tmp = D.pop()
    D.appendleft(tmp)

def compare(a):
    if len(D)