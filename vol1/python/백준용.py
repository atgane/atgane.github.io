import sys

def merge_sort(arr):
    def divide(_arr):
        n = len(_arr)
        if n == 1:
            return _arr
        else:
            return [divide(_arr[:n // 2 + n % 2]), divide(_arr[n // 2 + n % 2:])]
    
    def conquer(_arr):
        if len(_arr) == 1:
            return _arr
        elif len(_arr) == 2 and type(_arr[0][0]) == int:
            i, j = 0, 0
            ret = []
            while (i < len(_arr[0])) and (j < len(_arr[1])):
                if _arr[0][i] < _arr[1][j]:
                    ret.append(_arr[0][i]); i += 1
                else:
                    ret.append(_arr[1][j]); j += 1
            while i < len(_arr[0]):
                ret.append(_arr[0][i]); i += 1
            while j < len(_arr[1]):
                ret.append(_arr[1][j]); j += 1
            return ret
        else:
            return conquer([conquer(_arr[0]), conquer(_arr[1])])
    arr = divide(arr)
    arr = conquer(arr)
    return arr

n = int(sys.stdin.readline())
arr = []
for i in range(n):
    arr.append(sys.stdin.readline())

for i in merge_sort(arr):
    print(i)