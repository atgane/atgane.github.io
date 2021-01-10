import random
n = random.randint(2, 10)
k = random.randint(2, n)
print(n, k)
l = list(range(1, n + 1))
random.shuffle(l)
for i in range(n):
    print(l[i], end=' ')