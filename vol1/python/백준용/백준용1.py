import sys
while True:
    tmp = list(map(int, sys.stdin.readline().split()))
    if tmp[0] == 0:
        break
    max = tmp[0]
    for i in range(tmp[0]):
        for j in range(2, tmp[i + 1] + 1):
            k = 1
            while True:
                try:
                    if j <= tmp[i + k + 1]:
                        k += 1
                    else:
                        break
                except:
                    break
            if k * j > max:
                max = k * j
    print(max)