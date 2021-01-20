import sys
import math
n = str(math.factorial(int(sys.stdin.readline())))
l = len(n)
for i in range(l):
    if n[-(i + 1)] != '0':
        print(i)
        break