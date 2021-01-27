from collections import deque
import sys
T = int(sys.stdin.readline())
for i in range(T):
    N, M = list(map(int, sys.stdin.readline().split()))
    d = deque(list(map(int, sys.stdin.readline().split())))
    m = max(d)
    k = 1
    while True:
        if M == 0 and d[M] == m:
            break
        elif M == 0:
            M = len(d) - 1
            d.append(d.popleft())
        else:
            tmp = d.popleft()
            if tmp == m:
                m = max(d)
                k += 1
            else:
                d.append(tmp)
            M -= 1
    print(k)