import numpy as np
import cv2

def floor(image, color, vertices, blur_size = 0.1):
    h, w = image.shape[:2]
    
    # Вычисляем размер ядра на основе пропорции изображения
    kernel_size = int(min(h, w) * blur_size)
    kernel_size = max(1, kernel_size)
    if kernel_size % 2 == 0:  # Делаем нечетным
        kernel_size += 1
    
    # Создаем бинарную маску
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(mask, [vertices], 255)
    
    # Размываем маску
    mask_blurred = cv2.GaussianBlur(mask, (kernel_size, kernel_size), 0)
    mask_float = mask_blurred.astype(np.float32) / 255.0
    mask_3d = mask_float[:, :, np.newaxis]  # Преобразуем в 3D маску

    # Создаем цветной слой
    color_layer = np.zeros_like(image, dtype=np.float32)

    if len(color) == 3 and color_layer.shape[2] == 4:
        color = np.append(color, 255)

    color_layer[:] = color  # Работаем в RGB формате

    # Преобразуем фон
    bg_float = image.astype(np.float32)

    # Смешиваем
    blended = bg_float * (1 - mask_3d) + color_layer * mask_3d
    return blended.astype(np.uint8)