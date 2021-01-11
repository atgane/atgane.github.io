import random
n = random.randint(2, 5)
k = random.randint(2, 5)
print(n, k)
for i in range(n):
    for j in range(k):
        print(random.randint(0, 1), end='')
    print()
for i in range(n):
    for j in range(k):
        print(random.randint(0, 1), end='')
    print()
