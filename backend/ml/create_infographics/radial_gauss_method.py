import numpy as np
from scipy.ndimage.filters import gaussian_filter

def gauss(image, radius=16, sigma=(5, 5, 0)):
    height, width = image.shape[:2]
    sigma_radius = min(height, width)//radius

    center_x, center_y = height//2, width//2

    y, x = np.indices((height, width))

    # расстояние от любой точки пространства x y до центра
    r = np.sqrt((x - center_x)**2 + (y - center_y)**2)
    
    # Создаем маску весов (0 в центре, 1 на краях)
    mask_weights = 1 - np.exp(-r**2 / (2 * sigma_radius**2))
    
    # гауссово размытие ко всему изображению
    blurred = gaussian_filter(image, sigma=sigma, mode='nearest')
    
    # Смешиваем исходное и размытое изображения с учетом маски
    if image.ndim == 3:
        mask_weights = mask_weights[:, :, np.newaxis]  # Добавляем измерение для цветных изображений
    
    result = image * (1 - mask_weights) + blurred * mask_weights

    result = np.clip(result, 0, 255).astype(np.uint8)

    return result