---
layout: article
title: "백준 13306 파이썬"

categories:
  [백준, 분리 집합]
tags:
  [백준, 분리 집합]
key: 100
---

[https://www.acmicpc.net/problem/13306](https://www.acmicpc.net/problem/13306)

<center><img src="/image/21-02-02/3738.png" width="60%" height="60%"><br>그림1. 이렇게 많이 틀릴 문제가 아니였는데...</center>

37번 틀리고 38번째 맞은 문제. 혼자푼다고 하지말고 진작에 좀 관련 알고리즘을 봤어야했는데...

우선 이 문제를 풀기전에 그래프, 분리집합에 대하여 혼자 구현해보거나 배워본적이 없다... 그래서 개고생을 했지만 시간복잡도를 신경쓰지 않은 처음에는 순조롭게 풀릴 것 같았다.

처음에는 그래프를 혼자 구현해보자며 클래스를 만들어서 접근하였다. 구체적인 방법은 다음과 같다. 
 - 이름, 루트, 자식노드, 부모노드를 맴버로 갖는 노드 클래스를 정의한다. 
 - 부모를 추가하는 add_parent, 자식을 추가하는 add_child, 자식의 루트를 자신의 루트와 같게 하는 check_root, 자식을 지우는 del_child 메서드를 정의하였다. 
 - 외부함수로 부모를 지우는 del_parent, 루트의 동일함을 판단하는 check_path함수를 정의하였다. 

 이렇게 함수랑 클래스를 나름 깔끔히(?) 정의해서 해결하려고 했다. 처음에 $N + 1$개의 노드로 구성된 배열 all_node 변수를 선언하고 각 노드를 집어넣었다. 이후 단순하게 $0$이 나오면 del_parent 함수로 해당하는 노드의 부모노드 맴버를 삭제하고 루트노드를 자기자신으로 바꿔 트리를 분리하였고 $1$이 나오면 두 노드의 루트가 같은지 다른지 검사한 다음 결과를 출력하는 check_path함수를 이용하였다. 

 결과는 시간초과. 아래는 시간초과코드. 

``` python
import sys
sys.setrecursionlimit(200000)

class Node:
    def __init__(self, node):
        self.name = node
        self.root = self
        self.child = []
        self.parent = None
    def add_parent(self, parent):
        self.parent = parent
        self.root = parent.root
        parent.child.append(self)
    def add_child(self, child):
        self.child.append(child)
        child.parent = self
    def check_root(self):
        for i in self.child:
            i.root = self.root
            i.check_root()
    def __repr__(self):
        return 'name:' + str(self.name)
    def del_child(self, child):
        l = len(self.child)
        for i in range(l):
            if self.child[i] == child:
                del self.child[i]
                break
    
def check_path(node1, node2):
    if node1.root == node2.root:
        return True
    return False

def del_parent(node1):
    tmp_node = node1.parent
    tmp_node.del_child(node1)
    node1.parent = None
    node1.root = node1
    node1.check_root()

N, Q = list(map(int, sys.stdin.readline().split()))
all_node = [Node(i) for i in range(N + 1)]
for i in range(2, N + 1):
    tmp = int(sys.stdin.readline())
    all_node[i].add_parent(all_node[tmp])
all_node[1].check_root()
for i in range(N + Q - 1):
    tmp = list(map(int, sys.stdin.readline().split()))
    if tmp[0] == 0:
        del_parent(all_node[tmp[1]])
    if tmp[0] == 1:
        result = check_path(all_node[tmp[1]], all_node[tmp[2]])
        if result:
            print("YES")
        else:
            print("NO")
```

이러면서 변수 몇개 지워도 보고 print를 sys.stdout.write로도 바꿔보고 한 열 몇번 틀리고 스스로 나름 괜찮다고 생각한 아이디어가 떠올랐다. 바로 check_root 메서드로 특정 노드의 모든 하위 노드의 루트를 바꾸는거보다 특정노드의 상위노드를 따라가서 제일 위에 있는 노드로 루트를 바꾸는 방법이였다. 

``` python
def find_root(self):
        if self.parent == None:
            return self
```

이렇게 하면 기존 check_root에서 find_root로 코드를 훨씬 더 간결하게 쓸 수 있음을 알 수 있다. 그리고 이렇게 상위로만 검색하면 좋은점이 자식노드를 굳이 맴버로 갖고 있지 않아도 상관이 없다는 점이다!

<center><img src="/image/21-02-02/method1.png" width="60%" height="60%"><br>그림2. check_root의 root처리</center>



<center><img src="/image/21-02-02/method2.png" width="60%" height="60%"><br>그림3. find_root의 root처리</center>

이렇게 검색을 하는 과정도 옆으로 튀는 것 없이 위로만 가면 되므로 시간을 더 아낄 수 있다고 생각했다. 그래서 풀릴 수 있을 줄 알았다... 하지만 아무리 자식 노드를 없애고 클래스를 최적화해도 시간초과를 넘을 수 없었다. 심지어 클래스를 포기하고 $2 \times (N + 1)$배열로 표현해도 틀렸다. 

시간초과 코드.

``` python
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
```

이쯤되서 big-O를 고려했다. find_root함수가 제일 비효율적으로 굴러가는 과정을 생각해보았다. 만약 20만개의 노드가 다음 그림과 같이 연결되어 있으면 시간복잡도가 어떻게 될까?

<center><img src="/image/21-02-02/bigo.png" width="60%" height="60%"><br>그림4. 최악의 경우. </center>

이렇게 20만개가 쌓여있으면 $N$번 검색해야 루트를 찾을 수 있을 것이다. 그런데 $Q$도 20만이고 이런 최악의 경우만 나온다면 $N^2$이 나와서 풀 수 없다. 최악의 경우는 400억번의 연산을 해야 답을 구할 수 있다!

하지만 그걸 알면 뭐하냐고... 다른 방법이 없는데...

혹여나 하고 받는 입력을 거꾸로 다시 올라가봤다. $0$이 $N-1$번 나오므로 최종상태에서는 모든 노드가 분리되어 있을 것이다. 따라서 모든 노드가 분리된 상태에서 부모 노드를 하나씩 연결하면 그나마 시간이 좀 줄어들지 않을까? 해서 다시 코드를 작성했다. 

하지만 부질없었다... 아래는 그렇게 바꾼 시간초과가 난 코드.

``` python
import sys
sys.setrecursionlimit(200000)

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
    all_node[i][1] = i

query_list = []
for i in range(N + Q - 1):
    tmp = list(map(int, sys.stdin.readline().split()))
    query_list.append(tmp)

result_list = []
for i in range(N + Q - 1):
    tmp = query_list.pop()
    if tmp[0] == 0:
        all_node[tmp[1]][1] = all_node[tmp[1]][0]
    elif tmp[0] == 1:
        root1 = find_root(all_node, tmp[1])
        root2 = find_root(all_node, tmp[2])
        if root1 == root2:
            result_list.append(True)
        else:
            result_list.append(False)
            
for i in range(Q):
    tmp = result_list.pop()
    if tmp:
        sys.stdout.write('YES\n')
    else:
        sys.stdout.write("NO\n")
```

정말 모르겠어서 알고리즘 분류를 봤다. 분리 집합, 오프라인 쿼리라 되어있어서 분리 집합에 관하여 찾아봤다. 아래는 참고로 본 분리 집합에 관한 다른 블로그 포스트이다. 

[https://ssungkang.tistory.com/entry/Algorithm-%EC%9C%A0%EB%8B%88%EC%98%A8-%ED%8C%8C%EC%9D%B8%EB%93%9CUnion-Find](https://ssungkang.tistory.com/entry/Algorithm-%EC%9C%A0%EB%8B%88%EC%98%A8-%ED%8C%8C%EC%9D%B8%EB%93%9CUnion-Find)

글을 읽어보니 내 find_root함수에 문제가 있음을 확인했다. 따라서 find_root함수를

``` python
def find_root(all_node, c_node_name):
    if all_node[c_node_name][1] != c_node_name:
        all_node[c_node_name][1] = find_root(all_node, all_node[c_node_name][0])
        all_node[c_node_name][0] = all_node[c_node_name][1]
    return all_node[c_node_name][1]
```

으로 바꾸고 다시 제출했다. 그랬더니 이게 맞네?

문제가 나에게 궁금한건 뭘까? 바로 루트이다. 따라서 각 노드는 루트에 대한 정보만 갖고 있으면 그만이다. 따라서 어떤 특정 노드의 자식노드가 루트를 검사하고 나면 그냥 특정노드 밑에 바로 위치하게 하면 되는거였다. 이러면 한줄로 늘어진 트리라도 아주 빠른 속도로 루트를 탐색할 수 있다. 

제발 모르고 덤비지 말아야지. 막상 알고풀면 37번 틀릴 만큼 크게 어려운 문제도 아니였는데...역시 아는만큼 보이나보다. 

최종 맞은 코드.

``` python
import sys
sys.setrecursionlimit(200000)

def find_root(all_node, c_node_name):
    if all_node[c_node_name][1] != c_node_name:
        all_node[c_node_name][1] = find_root(all_node, all_node[c_node_name][0])
        all_node[c_node_name][0] = all_node[c_node_name][1]
    return all_node[c_node_name][1]

N, Q = list(map(int, sys.stdin.readline().split()))
all_node = [[0, 0] for i in range(N + 1)]
all_node[1][1] = 1
for i in range(2, N + 1):
    tmp = int(sys.stdin.readline())
    all_node[i][0] = tmp
    all_node[i][1] = i

query_list = []
for i in range(N + Q - 1):
    tmp = list(map(int, sys.stdin.readline().split()))
    query_list.append(tmp)

result_list = []
for i in range(N + Q - 1):
    tmp = query_list.pop()
    if tmp[0] == 0:
        all_node[tmp[1]][1] = all_node[tmp[1]][0]
    elif tmp[0] == 1:
        root1 = find_root(all_node, tmp[1])
        root2 = find_root(all_node, tmp[2])
        if root1 == root2:
            result_list.append(True)
        else:
            result_list.append(False)
            
for i in range(Q):
    tmp = result_list.pop()
    if tmp:
        sys.stdout.write('YES\n')
    else:
        sys.stdout.write("NO\n")
```