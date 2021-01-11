---
layout: article
title: "백준 16288 파이썬"

categories:
  [백준, 그리디 알고리즘]
tags:
  [백준, 그리디 알고리즘]
key: 100
---

처음 들어오는 $n$개의 입국승객 번호를 data로 저장한다. 여기서 생각해야 할 것은 최대로 효율적인 방법으로, 즉 심사창구를 최대한 덜 사용하는 방법으로 배치할 수 없다면 주어진 순서대로 입국장을 빠져나갈 수 없다는 것이다. 따라서 효율적으로 배치하는 방법을 우선 찾아야 한다. 

주어진 순서에 대하여 효율적으로 심사창구에 $(i - 1)$명의 승객이 배치된 경우 $i$명의 승객을 배치하는 방법을 생각해보자. $i$번째 승객의 들어온 순서 $\pi_i$가 이전에 들어온 모든 승객의 순서보다 작다면 기존에 효율적으로 배치한 심사창구에 $i$번째 승객을 배치할 수 없으니 새로운 심사창구에 배치해야 한다. 하지만 그렇지 않다면 창구중에 가장 뒤에 서 있는 승객의 순서와 $\pi_i$의 차가 작은 곳에 배치하면 된다.

``` python
import sys
n, k = list(map(int, sys.stdin.readline().split()))
data = list(map(int, sys.stdin.readline().split()))
q = [[0] for i in range(k)]
flag = 1
for i in range(n):
    if i == 0:
        q[0].append(data[i])
    else:
        min = data[i]
        loc = -1
        for j in range(flag):
            if data[i] > q[j][-1] and min > data[i] - q[j][-1]:
                min = data[i] - q[j][-1]
                loc = j
        if loc == -1:
            flag += 1
            if flag > k:
                print("NO")
                flag = -1
                break
            q[flag - 1].append(data[i])
        else:
            q[loc].append(data[i])
if flag != -1:
    print("YES")
```