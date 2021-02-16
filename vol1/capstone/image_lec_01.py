import numpy as np
import cv2

def bilinear_interpolate(gray_np_image, p00, p10, p01, p11):
    