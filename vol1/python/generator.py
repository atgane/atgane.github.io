import random
n = random.randint(2, 20)
print(n)
m = random.randint(2, 15)
print(m)
k = []
for _ in range(m):
    a = 0; b = 0
    while a == b:
        a = random.randint(1, n); b = random.randint(1, n)
    print(a, b)
    k.append([a, b])
    
k.sort(key=lambda x: -x[1])
k.sort(key=lambda x: x[0])
print(k)