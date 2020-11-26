import sys
n = int(input())

for i in range(n):
    x, y = map(int, sys.stdin.readline().rsplit())
    print(f'Case #{i + 1}: {x} + {y} = {x + y}')