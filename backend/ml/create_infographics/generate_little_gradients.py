import numpy as np
from PIL import Image
import cv2

def create_elliptical_gradient(width=None, height=None, center_color=(0,0,0), 
                               center_x=None, center_y=None, 
                               radius_x=None, radius_y=None) -> ("R", "G", "B", "A"): #np.ndarray
    """
    Создает эллиптический градиент от цвета к прозрачности.
    
    Параметры:
    width, height - размеры изображения
    center_color - цвет в центре (RGB tuple)
    center_x, center_y - координаты центра
    radius_x, radius_y - радиусы эллипса по осям X и Y
    
    Возвращает:
    RGBA-массив numpy (uint8)
    """

    # Создаем координатную сетку
    y, x = np.ogrid[:height, :width]
    
    # Вычисляем эллиптическое расстояние
    dx = (x - center_x) / radius_x
    dy = (y - center_y) / radius_y
    dist = np.sqrt(dx**2 + dy**2)
    
    # Нормализуем и ограничиваем
    dist = np.clip(dist, 0, 1)
    
    # Создаем RGBA-массив
    gradient = np.zeros((height, width, 4), dtype=np.float32)
    
    # Цветовые каналы
    gradient[..., 0] = center_color[0]  # R
    gradient[..., 1] = center_color[1]  # G
    gradient[..., 2] = center_color[2]  # B
    
    # Альфа-канал (1 в центре, 0 на границе эллипса)
    gradient[..., 3] = 1 - dist
    
    return (np.clip(gradient, 0, 1) * 255).astype(np.uint8)

