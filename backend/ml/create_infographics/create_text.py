from PIL import Image, ImageDraw, ImageOps, ImageFont
import cv2
import numpy as np
from typing import List, Tuple

def resize_object_centered(
    image: Image.Image,
    scale_factor: float = 0.5,
    background_color: tuple[int, int, int, int] = (255, 255, 255, 255)
) -> Image.Image:
    """
    Уменьшает объект на прозрачном изображении, сохраняя его в центре.
    
    Args:
        image (Image.Image): Исходное изображение (RGBA с прозрачностью).
        scale_factor (float): Во сколько раз уменьшить (0.5 = в 2 раза).
        background_color (tuple): Цвет фона (R, G, B, A), по умолчанию прозрачный.
    
    Returns:
        Image.Image: Новое изображение с уменьшенным объектом в центре.
    """
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    
    # 1. Получаем маску объекта (из альфа-канала)
    alpha = image.split()[3]
    bbox = alpha.getbbox()  # (x1, y1, x2, y2) объекта
    
    if not bbox:
        return image  # Нет объекта → возвращаем исходное
    
    # 2. Вырезаем объект
    object_crop = image.crop(bbox)
    
    # 3. Уменьшаем его
    new_width = int(object_crop.width * scale_factor)
    new_height = int(object_crop.height * scale_factor)
    resized_object = object_crop.resize((new_width, new_height), Image.LANCZOS)
    
    # 4. Создаём новое изображение с прозрачным фоном
    result = Image.new("RGBA", image.size, background_color)
    
    # 5. Вставляем уменьшенный объект в центр
    x_center = (image.width - new_width) // 2
    y_center = (image.height - new_height) // 2
    result.paste(resized_object, (x_center, y_center), resized_object)
    
    return result


def get_alpha_mask(image: Image.Image) -> Image.Image:
    """Извлекает альфа-канал изображения как маску"""
    # Убедимся, что изображение имеет альфа-канал
    try:
        if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
            # Извлекаем альфа-канал
            alpha = image.split()[-1]
            # Создаем маску (белый - непрозрачный, черный - прозрачный)
            mask = Image.new("L", alpha.size, 0)
            mask.paste(alpha, (0, 0))
            return mask
        else:
            # Если нет альфа-канала, создаем полностью непрозрачную маску
            return Image.new("L", image.size, 255)
    except:
        image = Image.fromarray(image)
        if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
            # Извлекаем альфа-канал
            alpha = image.split()[-1]
            # Создаем маску (белый - непрозрачный, черный - прозрачный)
            mask = Image.new("L", alpha.size, 0)
            mask.paste(alpha, (0, 0))
            return mask
        else:
            # Если нет альфа-канала, создаем полностью непрозрачную маску
            return Image.new("L", image.size, 255)
        
def find_empty_rectangles_in_all_mask(mask: Image.Image) -> List[Tuple[int, int, int, int]]:
    """Равномерно распределяет прямоугольники по всему изображению, игнорируя содержимое."""
    width, height = mask.width, mask.height
    
    # Количество областей по горизонтали и вертикали
    cols = 3
    rows = 3
    
    # Размеры каждого прямоугольника
    rect_width = width // cols
    rect_height = height // rows
    
    # Генерируем сетку прямоугольников
    rectangles = []
    for i in range(cols):
        for j in range(rows):
            x1 = i * rect_width
            y1 = j * rect_height
            x2 = (i + 1) * rect_width if i != cols - 1 else width
            y2 = (j + 1) * rect_height if j != rows - 1 else height
            rectangles.append((x1, y1, x2, y2))
    
    # Фильтруем слишком маленькие области (меняйте 0.01 при необходимости)
    min_area = (width * height) * 0.01
    return [rect for rect in rectangles 
            if (rect[2] - rect[0]) * (rect[3] - rect[1]) > min_area]

def find_empty_rectangles(mask: Image.Image) -> List[Tuple[int, int, int, int]]:
    """Находит непересекающиеся прямоугольники вне объекта маски."""
    mask_np = np.array(mask)
    
    # Бинаризация маски
    if mask_np.max() > 1:
        _, mask_binary = cv2.threshold(mask_np, 1, 255, cv2.THRESH_BINARY)
    else:
        mask_binary = (mask_np * 255).astype(np.uint8)
    
    # Находим контуры объекта
    contours, _ = cv2.findContours(mask_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        print("нихуя не нашлось")
        return [(0, 0, mask.width, mask.height)]  # Вся картинка пустая
    
    # Получаем ограничивающий прямоугольник объекта
    x_obj, y_obj, w_obj, h_obj = cv2.boundingRect(np.concatenate(contours))
    x_end = x_obj + w_obj
    y_end = y_obj + h_obj
    
    empty_rectangles = []
    
    # 1. Слева от объекта (полная высота, но обрезаем справа)
    if x_obj > 0:
        empty_rectangles.append((0, 0, x_obj, mask.height))
    
    # 2. Справа от объекта (полная высота, но обрезаем слева)
    if x_end < mask.width:
        empty_rectangles.append((x_end, 0, mask.width, mask.height))
    
    # 3. Сверху от объекта (только между левым и правым прямоугольниками)
    if y_obj > 0:
        empty_rectangles.append((x_obj, 0, x_end, y_obj))
    
    # 4. Снизу от объекта (только между левым и правым прямоугольниками)
    if y_end < mask.height:
        empty_rectangles.append((x_obj, y_end, x_end, mask.height))
    
    return empty_rectangles

def check_no_overlap(rects: List[Tuple[int, int, int, int]]) -> bool:
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            r1, r2 = rects[i], rects[j]
            # Проверяем, что прямоугольники не пересекаются
            if not (r1[2] <= r2[0] or r1[0] >= r2[2] or r1[3] <= r2[1] or r1[1] >= r2[3]):
                return False
    return True

def draw_empty_rectangles_on_mask(mask: Image.Image, color: int = 128) -> Image.Image:
    """Рисует прямоугольники на маске, где нет объекта."""
    empty_rects = find_empty_rectangles(mask)
    if not empty_rects:
        return mask
    
    # Создаём копию маски для рисования
    drawn_mask = mask.copy()
    draw = ImageDraw.Draw(drawn_mask)
    
    for rect in empty_rects:
        x1, y1, x2, y2 = rect
        draw.rectangle([x1, y1, x2, y2], fill=color)
    
    return drawn_mask

def split_large_rectangles(
    rectangles: List[Tuple[int, int, int, int]],
    image_width: int,
    image_height: int,
    min_relative_width: float = 0.2,
    min_relative_height: float = 0.1,
    max_split_parts: int = 2
) -> List[Tuple[int, int, int, int]]:
    """Разделяет слишком большие прямоугольники на части, если они превышают заданные относительные размеры."""
    new_rectangles = []
    
    for x1, y1, x2, y2 in rectangles:
        rect_width = x2 - x1
        rect_height = y2 - y1
        
        # Проверяем, не слишком ли большой прямоугольник
        is_too_wide = rect_width > image_width * min_relative_width
        is_too_tall = rect_height > image_height * min_relative_height
        
        if not (is_too_wide or is_too_tall):
            new_rectangles.append((x1, y1, x2, y2))
            continue
        
        # Разделяем прямоугольник по наибольшей стороне
        if is_too_wide and rect_width >= rect_height:
            # Делим по ширине
            split_width = rect_width // max_split_parts
            for i in range(max_split_parts):
                new_x1 = x1 + i * split_width
                new_x2 = new_x1 + split_width
                new_rectangles.append((new_x1, y1, new_x2, y2))
        else:
            # Делим по высоте
            split_height = rect_height // max_split_parts
            for i in range(max_split_parts):
                new_y1 = y1 + i * split_height
                new_y2 = new_y1 + split_height
                new_rectangles.append((x1, new_y1, x2, new_y2))
    
    return new_rectangles


def split_rectangle_to_center(width, height, N, padding = None):
    if padding is None:
        padding = height // 9
    
    rectangles = []
    for k in range(N):
        offset_x = width//4
        offset_y = padding * k * (-1) ** k
        x1 = width//8
        y1 = height//2 - 400 + offset_y
        x2 = width*7//8
        y2 = height//2 + 400 + offset_y
        rectangles.append((x1, y1, x2, y2))
    return rectangles


def add_text_to_rectangles(
    image: Image.Image,
    empty_rects,
    texts: List[str],
    font_path: str = "arial.ttf",
    font_size: int = 20,
    text_color: Tuple[int, int, int, int] = (0, 0, 0, 255),
    padding: int = 5,
) -> Image.Image:
    
    if len(texts) < len(empty_rects):
        texts += [""] * (len(empty_rects) - len(texts))
    
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        font = ImageFont.load_default()
    
    result = image.copy()
    draw = ImageDraw.Draw(result)
    
    for i, (x1, y1, x2, y2) in enumerate(empty_rects):
        if i >= len(texts) or not texts[i]:
            continue
        
        rect_width = x2 - x1
        rect_height = y2 - y1
        
        text = texts[i]
        lines = []
        current_line = ""
        
        for word in text.split():
            test_line = current_line + " " + word if current_line else word

            test_width = draw.textlength(test_line, font=font)
            
            if test_width <= (rect_width - 2 * padding):
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        line_height = font_size + 2
        total_text_height = len(lines) * line_height
        
        if total_text_height > (rect_height - 2 * padding):
            continue
        
        y_text = y1 + (rect_height - total_text_height) // 2
        
        for line in lines:
            line_width = draw.textlength(line, font=font)
            x_text = x1 + (rect_width - line_width) // 2

            draw.text((x_text, y_text), line, fill=text_color, font=font)
            y_text += line_height
    
    result = np.array(result)

    return result