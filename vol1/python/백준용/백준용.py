import sys
sys.setrecursionlimit(200000)
def del_parent(all_node, c_node_name):
    all_node[c_node_name][0] = 0
    all_node[c_node_name][1] = c_node_name

def find_root(all_node, c_node_name):
    if all_node[c_node_name][1] != c_node_name:
        all_node[c_node_name][1] = find_root(all_node, all_node[c_node_name][0])
    return all_node[c_node_name][1]

N, Q = list(map(int, sys.stdin.readline().split()))
all_node = [[0, 0] for i in range(N + 1)]
all_node[1][1] = 1
for i in range(2, N + 1):
    tmp = int(sys.stdin.readline())
    all_node[i][0] = tmp
for i in range(N + Q - 1):
    tmp = list(map(int, sys.stdin.readline().split()))
    if tmp[0] == 0:
        del_parent(all_node, tmp[1])
    if tmp[0] == 1:
        root_name1 = find_root(all_node, tmp[1])
        root_name2 = find_root(all_node, tmp[2])
        if root_name1 == root_name2:
            sys.stdout.write('YES\n')
        else:
            sys.stdout.write("NO\n")
    print(all_node)