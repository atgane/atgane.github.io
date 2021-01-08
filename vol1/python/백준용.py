import sys
from collections import deque
n, k = list(map(int, sys.stdin.readline().split()))
data = list(map(int, sys.stdin.readline().split()))
data = sorted(sorted(data, key=lambda x: x // 10), key= lambda x: x % 10)
data = list(map(int, data))
data = deque(data)
cnt = 0
while len(data) != 0:
    if data[0] == 10:
        cnt += 1
        data.popleft()
    elif data[0] > 10:
        if k == 0:
            break
        k -= 1
        cnt += 1
        data[0] -= 10
    elif data[0] < 10:
        data.popleft()
sys.stdout.write(f"{cnt}")