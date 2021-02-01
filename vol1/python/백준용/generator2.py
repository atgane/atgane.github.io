import random
n = random.randint(2, 10)
q = random.randint(2, 10)
print(n, q)
for i in range(n - 1):
    print(i + 1)
    
for i in range(n + q - 1):
    t = random.randint(0, 1)
    if t == 1:
        print(t, random.randint(1, n), random.randint(1, n))
    else:
        print(t, random.randint(1, n))