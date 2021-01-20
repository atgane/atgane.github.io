import sys
n = int(sys.stdin.readline())
for _ in range(n):
    k = int(sys.stdin.readline())
    vol_dict ={}
    for _ in range(k):
        s = sys.stdin.readline().split()
        if s[1] not in vol_dict.keys():
            vol_dict[s[1]] = 0
        vol_dict[s[1]] += 1
    vol_list = list(vol_dict.values())
    vol_len = len(vol_list)
    ret = 1
    for i in range(vol_len):
        ret *= vol_list[i] + 1
    print(ret - 1)