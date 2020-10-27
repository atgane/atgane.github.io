import numpy as np
input_card_array = [1, 2, 3, 4, 5, 6, 7]

for i in range(len(input_card_array)):
    straight_flag = 0
    for j in range(5):
        if i + j in input_card_array:
            straight_flag += 1
    if straight_flag == 5:
        print("스트레이트 존재")