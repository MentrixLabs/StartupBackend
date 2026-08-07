import cv2
import numpy as np

def add_padding(image, top, bottom, left, right, color=(0, 0, 0)):
    """
    Добавляет рамку к изображению
    :param image: исходное изображение (H, W, C)
    :param top: пикселей сверху
    :param bottom: пикселей снизу
    :param left: пикселей слева
    :param right: пикселей справа
    :param color: цвет рамки (B, G, R)
    :return: изображение с рамкой
    """
    # Создаем новое изображение с нужными размерами
    new_height = image.shape[0] + top + bottom
    new_width = image.shape[1] + left + right
    
    # Если изображение цветное (3 канала)
    if len(image.shape) == 3:
        new_image = np.zeros((new_height, new_width, image.shape[2]), dtype=image.dtype)
        new_image[:, :] = color
    # Если изображение в градациях серого
    else:
        new_image = np.zeros((new_height, new_width), dtype=image.dtype)
        if isinstance(color, tuple):
            # Для grayscale берем первый элемент кортежа
            new_image[:, :] = color[0]
        else:
            new_image[:, :] = color
    
    # Вставляем оригинальное изображение
    new_image[top:top+image.shape[0], left:left+image.shape[1]] = image
    return new_image