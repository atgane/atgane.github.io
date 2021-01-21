import sys
N = int(sys.stdin.readline())
num_list = list(map(int, sys.stdin.readline().split()))
stack = [num_list.pop()]
return_list = [-1]
while num_list != []:
    tmp = num_list.pop()
    if tmp > stack[0]:
        stack = [tmp]
        return_list.append(-1)
        max_loc = 0
    else:
        l = len(stack)
        for i in range(1, l + 1):
            if tmp <= stack[-i]:
                return_list.append(stack[-i])
                stack = stack[:l - i + 1] + [tmp]
                break
return_list.reverse()
for i in return_list:
    sys.stdout.writelines(f"{i} ")