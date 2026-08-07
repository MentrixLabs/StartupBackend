import cv2
import numpy as np

def calculate_contrast(image):
    """Вычисляет контрастность изображения по стандартному отклонению яркости."""
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    contrast = np.std(image)
    return contrast

def contrast_measurements(image):
    """Возвращает различные метрики контрастности"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

    rms_contrast = np.std(gray)
    max_val, min_val = np.max(gray), np.min(gray)
    michelson = (max_val - min_val) / (max_val + min_val + 1e-6)
    
    _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    psnr = cv2.PSNR(gray, binary)
    
    return {
        'rms_contrast': rms_contrast,
        'michelson_contrast': michelson,
        'psnr': psnr
    }

def regional_contrast(image, grid_size=(3, 3)):
    """Оценивает контраст по регионам изображения"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    h, w = gray.shape
    results = []
    
    for i in range(grid_size[0]):
        for j in range(grid_size[1]):
            y1, y2 = i*h//grid_size[0], (i+1)*h//grid_size[0]
            x1, x2 = j*w//grid_size[1], (j+1)*w//grid_size[1]
            region = gray[y1:y2, x1:x2]
            results.append(np.std(region))
    
    return {
        'mean_contrast': np.mean(results),
        'min_contrast': np.min(results),
        'max_contrast': np.max(results),
        'regional_values': results
    }

def auto_contrast(image, clip_hist_percent=1):
    """Автоматическая коррекция контраста с отсечением крайних значений гистограммы"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    
    hist = cv2.calcHist([gray], [0], None, [256], [0,256])
    hist_size = len(hist)
    
    accumulator = np.cumsum(hist)
    
    max_val = accumulator[-1]
    clip_hist_percent *= (max_val / 100.0)
    clip_hist_percent /= 2.0
    
    min_gray = 0
    while accumulator[min_gray] < clip_hist_percent:
        min_gray += 1
    
    max_gray = hist_size - 1
    while accumulator[max_gray] >= (max_val - clip_hist_percent):
        max_gray -= 1
    
    alpha = 255 / (max_gray - min_gray)
    beta = -min_gray * alpha
    
    result = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
    return result

def adjust_gamma(image, gamma=1.0):
    """Нелинейная коррекция контраста через гамма-коррекцию"""
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255
        for i in np.arange(0, 256)]).astype("uint8")
    
    return cv2.LUT(image, table)

def clahe_contrast(image, clip_limit=2.0, grid_size=(8,8)):
    """Адаптивное выравнивание гистограммы для улучшения локального контраста"""
    if len(image.shape) == 3:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
    else:
        l = image.copy()
    
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=grid_size)
    cl = clahe.apply(l)
    
    if len(image.shape) == 3:
        lab = cv2.merge((cl, a, b))
        result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    else:
        result = cl
    
    return result

def s_curve_contrast(image, strength=0.2):
    """S-образная коррекция контраста для фотографического вида"""
    img_float = image.astype(np.float32) / 255.0
    corrected = 0.5 * (1 + np.sin(np.pi * (img_float - 0.5)) * strength)
    return (corrected * 255).astype(np.uint8)

if __name__ == '__main__':
    image = cv2.imread('example/image.jpg')

    auto_result = auto_contrast(image)
    gamma_result = adjust_gamma(image, gamma=1.5)
    clahe_result = clahe_contrast(image, clip_limit=3.0)
    s_curve_result = s_curve_contrast(image, strength=0.3)

    cv2.imwrite('example/auto_contrast.jpg', auto_result)
    cv2.imwrite('example/gamma_corrected.jpg', gamma_result)
    cv2.imwrite('example/clahe_enhanced.jpg', clahe_result)
    cv2.imwrite('example/s_curve.jpg', s_curve_result)
