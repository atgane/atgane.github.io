import sys
import math

N = int(sys.stdin.readline())
data = []
for i in range(N):
    data.append(list(map(int, sys.stdin.readline().split())))
data.sort(key=lambda x: x[0])

def calc_dis(p1, p2):
    return (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2

def calc_min_len(arr):
    l_arr = len(arr)
    if l_arr == 2:
        return calc_dis(arr[0], arr[1])

    elif l_arr == 3:
        return min(calc_dis(arr[0], arr[1]), calc_dis(arr[0], arr[2]), calc_dis(arr[1], arr[2]))

    else:
        left_arr = arr[:l_arr // 2]
        right_arr = arr[l_arr // 2:]
        left_len = calc_min_len(left_arr)
        right_len = calc_min_len(right_arr)
        min_length = min(left_len, right_len)
        mid_line = (arr[l_arr // 2 - 1][0] + arr[l_arr // 2][0]) / 2
        small_arr = []

        for i in range(l_arr):
            if mid_line - min_length <= arr[i][0] and arr[i][0] <= mid_line + min_length:
                small_arr.append(arr[i])
        
        small_arr.sort(key=lambda x: x[1])
        l_s_arr = len(small_arr)

        for i in range(l_s_arr):
            for j in range(i + 1, l_s_arr):
                dy = (small_arr[i][1] - small_arr[j][1]) ** 2
                if dy < min_length:
                    dx = (small_arr[i][0] - small_arr[j][0]) ** 2
                    if dx < min_length - dy:
                        min_length = min(min_length, dx + dy)
                else:
                    break

        return min_length

print(calc_min_len(data))