import sys

N = int(sys.stdin.readline())
mat = []
for i in range(N):
    tmp = list(map(int, sys.stdin.readline().split()))
    mat.append(tmp)

count_list = [0, 0, 0]

def count(mat):
    global count_list
    n = len(mat)
    if n == 1:
        count_list[mat[0][0]] += 1
        return mat[0][0]
    div_list = [[] for _ in range(9)]
    for i in range(n // 3):
        tmp_list = [[] for _ in range(9)]
        for j in range(n // 3):
            for k in range(9):
                a, b = k // 3, k % 3
                tmp_list[k].append(mat[i + n // 3 * a][j + n // 3 * b])
        for k in range(9):
            div_list[k].append(tmp_list[k])
    flag = count(div_list[0])
    for i in range(1, 9):
        if flag != count(div_list[i]):
            flag = 2
    if flag == 0:
        count_list[0] -= 8
        return 0
    elif flag == 1:
        count_list[1] -= 8
        return 1
    elif flag == -1:
        count_list[-1] -= 8
        return -1
    else:
        return 2
    
count(mat)
sys.stdout.write(str(count_list[-1]) + "\n")
sys.stdout.write(str(count_list[0]) + "\n")
sys.stdout.write(str(count_list[1]))