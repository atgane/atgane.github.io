import sys
n, m = list(map(int, sys.stdin.readline().split()))
map = [list(map(int, sys.stdin.readline().split())) for _ in range(n)]

def cnt(_y, _x, _c):
    bf1 = False
    for j in range(_y, n):
        for i in range(_x, m):
            if map[j][i] == 1:
                map[j][i] = 0
                _c = _c + 1 + cnt(j, i, _c)
                bf1 = True
            if bf1:
                break
        if bf1:
            break
    return _c
v = 1
for i in range(n + 2):
    if v == 0:
        print(i - 1)
        break
    v = cnt(i, 0, 0)