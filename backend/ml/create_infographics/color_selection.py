import cv2
import numpy as np

def get_average_color(image):
    average_color = np.mean(image, axis=(0, 1)).astype(int)
    return tuple(average_color)

def get_average_color_masked(image, mask):
    """Средний цвет только в области маски"""
    masked = cv2.bitwise_and(image, image, mask=mask)
    pixels = masked[mask > 0]
    return np.mean(pixels, axis=0).astype(int)
