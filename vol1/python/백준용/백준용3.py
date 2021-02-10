import sys

def calc_len(p1, p2):
    return (p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2

N = int(sys.stdin.readline())
data = []
for i in range(N):
    data.append(list(map(int, sys.stdin.readline().split())))
data.sort(key=lambda x: x[1])
data.sort(key=lambda x: x[0])
length = calc_len(data[0], data[1])
for i in range(N):
    for j in range(i + 1, N):
        if abs(data[j][0] - data[i][0]) < length:
            if abs(data[j][1] - data[i][1]) < length:
                length = min(length, calc_len(data[i], data[j]))
                print(i, j, data[i], data[j])
        else:
            break
print(length)