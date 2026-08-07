import cv2
import numpy as np

def mask_using_threshold(image: np.ndarray, invert: bool = False) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV if not invert else cv2.THRESH_BINARY)
    return mask

def mask_using_kmeans(image: np.ndarray, k: int = 2) -> np.ndarray:
    pixel_values = image.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    _, labels, _ = cv2.kmeans(pixel_values, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    
    if np.sum(labels == 0) > np.sum(labels == 1):
        mask = (labels == 1).reshape(image.shape[:2])
    else:
        mask = (labels == 0).reshape(image.shape[:2])
    
    mask = mask.astype(np.uint8) * 255
    
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    
    return mask

def mask_using_grabcut(image: np.ndarray, rect_coords: tuple = None, iter_count: int = 10) -> np.ndarray:
    # Проверка входных данных
    if image is None:
        raise ValueError("Input image is None")
    
    # Инициализация маски
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    
    # Автоматическое определение прямоугольника если не задан
    if rect_coords is None:
        # Используем 85% от центра изображения по умолчанию
        h, w = image.shape[:2]
        border_w = int(w * 0.15)
        border_h = int(h * 0.15)
        rect_coords = (border_w, border_h, w - 2*border_w, h - 2*border_h)
    
    # Инициализация моделей
    bgd_model = np.zeros((1, 65), dtype=np.float64)
    fgd_model = np.zeros((1, 65), dtype=np.float64)
    
    # Первый проход GrabCut
    cv2.grabCut(image, mask, rect_coords, bgd_model, fgd_model, iter_count, cv2.GC_INIT_WITH_RECT)
    
    # Уточнение маски
    new_mask = np.where((mask == cv2.GC_PR_BGD) | (mask == cv2.GC_BGD), 0, 1).astype('uint8')
    
    # Морфологическая обработка для устранения шума
    kernel = np.ones((3,3), np.uint8)
    new_mask = cv2.morphologyEx(new_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    new_mask = cv2.morphologyEx(new_mask, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # Второй проход GrabCut с уточненной маской
    mask[new_mask == 1] = cv2.GC_FGD
    mask[new_mask == 0] = cv2.GC_BGD
    cv2.grabCut(image, mask, None, bgd_model, fgd_model, iter_count//2, cv2.GC_EVAL)
    
    # Финальная маска
    final_mask = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    
    # Контурная оптимизация
    contours, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest_contour = max(contours, key=cv2.contourArea)
        smoothed_mask = np.zeros_like(final_mask)
        cv2.drawContours(smoothed_mask, [largest_contour], -1, 255, -1)
        return smoothed_mask
    
    return final_mask

def apply_mask(image: np.ndarray, mask: np.ndarray, background_color: tuple = (255, 255, 255)) -> np.ndarray:
    result = image.copy()
    result[mask == 0] = background_color
    return result
