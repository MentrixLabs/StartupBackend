import cv2
import numpy as np


def blend_with_condition(fg_color, bg_color, combined_alpha):
    """
    fg_color, bg_color: float32 в диапазоне [0,1], shape (H,W,3)
    combined_alpha: float32 в [0,1], shape (H,W,1)
    """

    # Проверяем белый цвет (точно)
    is_white = np.all(fg_color == 1.0, axis=-1) # shape (H,W)

    # Проверяем "похоже на серый" — например, max-min < 0.05
    max_rgb = np.max(fg_color, axis=-1)
    min_rgb = np.min(fg_color, axis=-1)
    is_gray = (max_rgb - min_rgb) < 0.01

    # Объединяем условия
    condition = is_white #| is_gray #|  # shape (H,W), bool

    # Расширяем размерность для broadcast
    condition_3ch = condition[..., np.newaxis]

    # Классическое смешивание
    blended = bg_color * (1-combined_alpha) + fg_color * combined_alpha

    # Итог: если условие истинно — смешиваем, иначе — fg_color без изменений
    out = np.where(condition_3ch, blended, fg_color)

    return out


def apply_background_with_blending(foreground, background_img, mask, blur_size=5):
    """
    Применяет фоновое изображение с плавным наложением с использованием маски.
    Поддерживает RGBA-изображения и различные форматы масок.
    
    Параметры:
    foreground - передний план (RGBA)
    background_img - фоновое изображение (RGBA или RGB)
    mask - маска объекта (1 канал, RGB или RGBA)
    blur_size - размер размытия для мягких границ
    
    Возвращает:
    RGBA-изображение с наложенным фоном
    """
    # Нормализация маски
    if mask.ndim == 3:
        if mask.shape[2] == 3:  # RGB-маска
            mask = cv2.cvtColor(mask, cv2.COLOR_RGB2GRAY)
        elif mask.shape[2] == 4:  # RGBA-маска
            mask = mask[:, :, 3]  # Берём альфа-канал
    
    # Создаём мягкую маску
    soft_mask = cv2.GaussianBlur(mask, (blur_size, blur_size), 0)
    soft_mask = soft_mask.astype(np.float32) / 255.0
    
    # Преобразуем в float для точных вычислений
    foreground = foreground.astype(np.float32) / 255.0
    background_img = background_img.astype(np.float32) / 255.0
    
    # Если передний план не имеет альфа-канала, добавляем его
    if foreground.shape[2] == 3:
        alpha_channel = np.ones((foreground.shape[0], foreground.shape[1], 1), dtype=np.float32)
        foreground = np.concatenate((foreground, alpha_channel), axis=2)
    
    # Если фон не имеет альфа-канала, добавляем его
    if background_img.shape[2] == 3:
        alpha_channel = np.ones((background_img.shape[0], background_img.shape[1], 1), dtype=np.float32)
        background_img = np.concatenate((background_img, alpha_channel), axis=2)
    
    # Разделяем передний план на цвет и альфу
    fg_color = foreground[:, :, :3]
    fg_alpha = foreground[:, :, 3:4]  # Сохраняем размерность (H, W, 1)
    
    # Разделяем фон на цвет и альфу
    bg_color = background_img[:, :, :3]
    bg_alpha = background_img[:, :, 3:4]  # Сохраняем размерность (H, W, 1)
    
    # Добавляем размерность канала к маске
    soft_mask = soft_mask[:, :, np.newaxis]  # (H, W, 1)
    
    # Комбинированная альфа (учитываем альфу переднего плана и маску)
    combined_alpha = fg_alpha * soft_mask
    
    # смешивание цветов
    blended_color = blend_with_condition(fg_color, bg_color, combined_alpha)

    # Смешивание альфа-каналов
    blended_alpha = combined_alpha + bg_alpha * (1.0 - combined_alpha)
    
    # Объединяем результат
    blended = np.concatenate([blended_color, blended_alpha], axis=-1)
    
    # Конвертируем обратно в uint8
    blended = np.clip(blended * 255, 0, 255).astype(np.uint8)
    
    return blended

# Обработка полупрозрачных областей
def apply_with_alpha(original_img, background_img, alpha_mask):
    # alpha_mask должна быть в диапазоне 0-255
    alpha = alpha_mask.astype(np.float32) / 255.0
    alpha = cv2.merge([alpha, alpha, alpha])
    
    result = original_img# * alpha + background_img * (1 - alpha)
    return result.astype(np.uint8)


def prepare_background(original_img, background_img):
    """Подгоняет фон под размер исходного изображения с центрированием и обрезкой лишнего."""
    h, w = original_img.shape[:2]
    bg_h, bg_w = background_img.shape[:2]
    
    # Вычисляем соотношения сторон
    target_ratio = w / h
    bg_ratio = bg_w / bg_h
    
    # Масштабируем фон с сохранением пропорций
    if bg_ratio > target_ratio:
        # Обрезаем по ширине (горизонтальный фон)
        new_width = int(bg_h * target_ratio)
        start_x = (bg_w - new_width) // 2
        cropped_bg = background_img[:, start_x:start_x+new_width]
    else:
        # Обрезаем по высоте (вертикальный фон)
        new_height = int(bg_w / target_ratio)
        start_y = (bg_h - new_height) // 2
        cropped_bg = background_img[start_y:start_y+new_height, :]
    
    # Ресайзим до точного размера оригинала
    prepared_bg = cv2.resize(cropped_bg, (w, h))
    
    return prepared_bg


def concotenate(foreground, background):
    brows, bcols = foreground.shape[:2]
    rows,cols,channels = background.shape
    # Ниже я изменил roi, чтобы картинка выводилась посередине, а не в левом верхнем углу
    roi = foreground[int(brows/2)-int(rows/2):int(brows/2)+int(rows/2), int(bcols/2)- 
    int(cols/2):int(bcols/2)+int(cols/2) ]

    img2gray = cv2.cvtColor(background,cv2.COLOR_BGR2GRAY)
    ret, mask = cv2.threshold(img2gray, 10, 255, cv2.THRESH_BINARY)
    mask_inv = cv2.bitwise_not(mask)

    img1_bg = cv2.bitwise_and(roi,roi,mask = mask_inv)

    img2_fg = cv2.bitwise_and(background,background,mask = mask)

    dst = cv2.add(img1_bg,img2_fg)
    foreground[int(brows/2)-int(rows/2):int(brows/2)+int(rows/2), int(bcols/2)- 
    int(cols/2):int(bcols/2)+int(cols/2) ] = dst

    return foreground