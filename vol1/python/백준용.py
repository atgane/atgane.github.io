n, k = list(map(int, input().split()))
inp_list = []
for i in range(n):
    tmp_list = list(map(int, input().split()))
    inp_list.append(tmp_list)

inp_list.sort(key=lambda x:x[0])
print(inp_list)