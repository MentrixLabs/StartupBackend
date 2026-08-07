import numpy as np

def create_round(image, color, center, radius):
    height, width = image.shape[:2]
    y, x = np.ogrid[:height, :width]

    dist = np.sqrt((x - center[0])**2 + (y - center[1])**2)

    # Маска для кольца толщиной ~10 пикселей вокруг радиуса
    mask = (dist >= radius - 5) & (dist <= radius + 5)

    round_img = np.zeros((height, width, 4), dtype=np.uint8)

    # Задаём цвет (0..255)
    round_img[..., 0] = int(color[0])
    round_img[..., 1] = int(color[1])
    round_img[..., 2] = int(color[2])
    round_img[..., 3] = 0  # прозрачный по умолчанию

    # Применяем альфа-канал к кольцу
    round_img[..., 3][mask] = 255

    return round_img

import numpy as np
import cv2  # для примера, можно использовать и другие библиотеки

# Создаем пустое изображение 200x200 с 3 каналами (RGB), заполненное белым цветом
img = np.ones((200, 200, 3), dtype=np.uint8) * 255
center = (100, 100)
radius = 50
color = (255, 0, 0)
cv2.circle(img, center, radius, color)