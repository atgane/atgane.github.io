import sys
while True:
    input_list = list(map(int, sys.stdin.readline().split()))
    if input_list[0] == 0:
        break
    input_list.append(0)
    ret = 0
    stack = [[0, 0]]
    for i in range(1, input_list[0] + 2):
        while stack[-1][1] > input_list[i]:
            tmp_list = stack.pop()
            tmp_area = 0
            while stack[-1][1] == tmp_list[1]:
                stack.pop()
            print(stack, tmp_list)
            print(i, input_list[i], (i - 1 - stack[-1][0]) * tmp_list[1], (i - tmp_list[0]) * tmp_list[1])
            tmp_area = max((i - 1 - stack[-1][0]) * tmp_list[1], (i - tmp_list[0]) * tmp_list[1])
            if tmp_area > ret:
                ret = tmp_area
        stack.append([i, input_list[i]])
    print(ret)