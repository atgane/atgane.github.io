import sys

def print_recursive(depth, _str, _size):
    if depth == 1:
        _line = '----'
        print(_line + _str[0])
        print(_size * _line + '"재귀함수는 자기 자신을 호출하는 함수라네"')
        print(_line + _str[len(_str) - 1])
    else:
        _new = [] + _str
        for i in range(len(_str)):
            _new[i] = '----' + _str[i]
        for i in range(len(_new) - 1):
            print(_new[i])
        print_recursive(depth - 1, _new, _size)
        print(_new[len(str) - 1])

intro = "어느 한 컴퓨터공학과 학생이 유명한 교수님을 찾아가 물었다."
long_str = '''"재귀함수가 뭔가요?"
"잘 들어보게. 옛날옛날 한 산 꼭대기에 이세상 모든 지식을 통달한 선인이 있었어.
마을 사람들은 모두 그 선인에게 수많은 질문을 했고, 모두 지혜롭게 대답해 주었지.
그의 답은 대부분 옳았다고 하네. 그런데 어느 날, 그 선인에게 한 선비가 찾아와서 물었어."
라고 답변하였지.'''

str = long_str.split('\n')
size = int(sys.stdin.readline())
print(intro)
for n in range(len(str) - 1):
    print(str[n])
print_recursive(size, str, size)
print(str[len(str) - 1],end="")