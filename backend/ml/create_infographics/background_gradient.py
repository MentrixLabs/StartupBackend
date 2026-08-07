import numpy as np
import cv2
from object_mask import mask_using_grabcut, mask_using_threshold
from sklearn.cluster import KMeans

def create_radial_gradient(width, height, center_color, edge_color):
    # Создаем сетку координат
    x = np.arange(width)
    y = np.arange(height)
    X, Y = np.meshgrid(x, y)
    
    # Центр изображения
    center_x = width / 2
    center_y = height / 2
    
    # Расстояние до центра
    dist = np.sqrt((X - center_x)**2 + (Y - center_y)**2)
    
    # Нормализация (максимальное расстояние до угла)
    max_dist = np.sqrt((width/2)**2 + (height/2)**2)
    dist = dist / max_dist
    
    # Создаем градиент
    gradient = np.zeros((height, width, 3))
    for i in range(3):
        gradient[..., i] = (1 - dist) * center_color[i] + dist * edge_color[i]

    #gradient[..., 3] = 255
    
    return np.clip(gradient, 0, 255).astype(np.uint8)

def gradient_circle(width, height, center_color):
    y, x = np.ogrid[:height, :width]
    
    # Вычисляем эллиптическое расстояние
    dx = (x - width/2) / width/3
    dy = (y - height/2) / height/3
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

def dominant_color_finding(image, mask) -> tuple["R", "G", "B"]:
    # определения доминантного цвета картинки
    resized_mask = cv2.resize(mask, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # Convert the original image to RGB
    pixels_inside_mask = image_rgb[resized_mask == 255]
    
    if len(pixels_inside_mask) > 10:  # минимум пикселей для кластеризации
        kmeans = KMeans(n_clusters=1)
        kmeans.fit(pixels_inside_mask)
        dominant_color = kmeans.cluster_centers_[0].astype(int)
    else:
        # Fallback if not enough pixels
        dominant_color = np.mean(pixels_inside_mask, axis=0).astype(int)
    
    return dominant_color
