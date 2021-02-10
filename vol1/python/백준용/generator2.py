import random
#n = random.randint(3, 100)
n = 300
k = 100000
print(n)
for _ in range(n):
    print(random.randint(-k, k), random.randint(-k, k))