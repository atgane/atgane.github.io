import sys
sys.setrecursionlimit(200000)

class Node:
    def __init__(self, node):
        self.name = node
        self.root = None
        self.parent = None
    def add_parent(self, parent):
        self.parent = parent
    def del_parent(self):
        self.parent = None
        self.root = self
    def find_root(self):
        if self.root != self:
            self.root = self.parent.find_root()
        return self.root

N, Q = list(map(int, sys.stdin.readline().split()))
all_node = [Node(i) for i in range(N + 1)]
all_node[1].del_parent()
for i in range(2, N + 1):
    tmp = int(sys.stdin.readline())
    all_node[i].add_parent(all_node[tmp])
for i in range(N + Q - 1):
    tmp = list(map(int, sys.stdin.readline().split()))
    if tmp[0] == 0:
        all_node[tmp[1]].del_parent()
    if tmp[0] == 1:
        root_node1 = all_node[tmp[1]].find_root()
        root_node2 = all_node[tmp[2]].find_root()
        if root_node1 == root_node2:
            sys.stdout.write('YES\n')
        else:
            sys.stdout.write("NO\n")