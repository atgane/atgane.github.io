import sys
n, r, q = list(map(int, sys.stdin.readline().split()))
inp_list = []
node_list = [0 for _ in range(n + 1)]
memo_list = [-1 for _ in range(n + 1)]
for _ in range(n - 1):
    vol_list = list(map(int, sys.stdin.readline().split()))
    inp_list.append(vol_list)
    node_list[vol_list[0]] += 1
    node_list[vol_list[1]] += 1
        
for i in range(n + 1):
    if i != r:
        node_list[i] -= 1

def func(q, p):
    if node_list[q] == 0:
        return 1
    elif memo_list[q] != -1:
        return memo_list[q]
    elif q == r:
        return n
    else:
        count = 0
        ret = 0
        for i in range(n - 1):
            if p not in inp_list[i] and q in inp_list[i]:
                count += 1
                a = list(set(inp_list) - set([q]))[0]
                if a == n:
                    return n;
                ret += func(a, q)
            if count == node_list[q] - 1:
                break
        
        

for _ in range(q):
    q = int(sys.stdin.readline())
    if node_list[q] == 0:
        print(1)
    else:
        



print(node_list)