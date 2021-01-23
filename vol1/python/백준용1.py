import sys
from collections import deque
N = int(sys.stdin.readline())
M = int(sys.stdin.readline())
routeList = []
for i in range(M):
    tmpList = list(map(int, sys.stdin.readline().split()))
    if tmpList[1] < tmpList[0]:
        tmpList.append(i + 1)
        tmpList[1] += N
        routeList.append(list(tmpList))
        tmpList[1] -= N
        tmpList[0] -= N
        routeList.append(list(tmpList))
    else:
        tmpList.append(i + 1)
        routeList.append(tmpList)
routeList.sort(key=lambda x: -x[1])
routeList.sort(key=lambda x: x[0])
routeDeque = deque(routeList)
resultDeque = deque([routeDeque.popleft()])
lenRouteDeque = len(routeDeque)

print(routeList)

for i in range(lenRouteDeque):
    tmpList = routeDeque.popleft()
    if resultDeque[-1][1] >= tmpList[1]:
        pass
    else:
        resultDeque.append(tmpList)
result = sorted(list(resultDeque), key=lambda x: x[2])
flag = -1
lenResult = len(result)
for i in range(lenResult):
    if flag != result[i][2]:
        print(result[i][2], end=" ")
        flag = result[i][2]