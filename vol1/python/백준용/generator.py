import random

N = random.randint(1, 30)
M = random.randint(1, 30)
print(N, M)
for _ in range(M):
    print(random.randint(0, 1), random.randint(1, N), random.randint(1, N))