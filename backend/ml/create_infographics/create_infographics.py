import cv2
import numpy as np
from PIL import Image
from background import apply_background_with_blending, prepare_background, concotenate
from background_gradient import create_radial_gradient, dominant_color_finding, gradient_circle
from card_analysis import find_free_space_rectangles
from create_text import *
from object_mask import mask_using_threshold
from generate_little_gradients import create_elliptical_gradient
from padding_image import add_padding
from shapes.floor import floor
from radial_gauss_method import gauss
from sklearn.cluster import KMeans
import sys
import os
from contextlib import contextmanager
import uuid
import datetime
from scipy.ndimage.filters import gaussian_filter

@contextmanager
def suppress_stderr():
    """Временно подавляет вывод в stderr."""
    with open(os.devnull, 'w') as devnull:
        original_stderr = sys.stderr
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stderr = original_stderr

def load_image(file_path: str, background_color=(255, 255, 255)) -> np.ndarray:
    # Подавление stderr для игнорирования предупреждений
    with suppress_stderr():
        # Загружаем изображение с альфа-каналом (если есть)
        image = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
    
    if image is None:
        print(f"Error: Failed to load image at {file_path}", file=sys.stderr)
        return None

    # Обработка разных форматов изображений
    if len(image.shape) == 2:  # Grayscale (H, W)
        return cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    
    channels = image.shape[2]
    
    if channels == 4:  # Изображение с альфа-каналом (BGRA)
        # Конвертируем в RGBA
        rgba = cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA)
        rgb = rgba[:, :, :3]
        alpha = rgba[:, :, 3].astype(np.float32) / 255.0
        
        # Подготавливаем фон
        bg = np.array(background_color, dtype=np.float32)
        
        # Смешиваем с фоном с учетом прозрачности
        r = rgb[:, :, 0] * alpha + bg[0] * (1 - alpha)
        g = rgb[:, :, 1] * alpha + bg[1] * (1 - alpha)
        b = rgb[:, :, 2] * alpha + bg[2] * (1 - alpha)
        
        return np.stack([r, g, b], axis=-1).astype(np.uint8)
    
    elif channels == 3:  # Обычное цветное изображение (BGR)
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    else:  # Нестандартные форматы
        # Берем первые 3 канала и конвертируем как BGR
        return cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2RGB)

def determine_alpha(image, target_height, target_width) -> np.ndarray:
    has_alpha = image.shape[2] == 4
    
    if has_alpha:
        image_with_alpha = image  # Используем исходное изображение с альфа-каналом
    else:
        # Добавляем непрозрачный альфа-канал
        image_with_alpha = np.dstack((image, np.full((target_height, target_width), 255, dtype=np.uint8)))
    return image_with_alpha
"""
def save_image(image: np.ndarray, output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:6]  # 6-character random ID
    filename = f"image_{timestamp}_{unique_id}.png"
    output_path = os.path.join(output_dir, filename)
    
    cv2.imwrite(output_path, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))

def save_image(image: Image.Image, output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:6]  # 6-character random ID
    filename = f"image_{timestamp}_{unique_id}.png"
    output_path = os.path.join(output_dir, filename)

    image.save(output_path)
"""

def save_image(image: tuple[np.ndarray, Image.Image], output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:6]
    filename = f"image_{timestamp}_{unique_id}.png"
    output_path = os.path.join(output_dir, filename)
    
    if isinstance(image, Image.Image):
        image.save(output_path)
    else:
        cv2.imwrite(output_path, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))

def saturation_top(color, n):
    color *= n
    return np.clip(color, 0, 255)

def saturation_boat(color, n):
    color //= n
    return np.clip(color, 0, 255)

def create_infographics(image, texts, number, image_background = False, need_mask = True, font_path = "./assets/Monteserat-Medium/Montserrat-Medium.ttf"):
    average_color = np.mean(image, axis=(0, 1))
    target_height, target_width = image.shape[:2]

    # определение доминантного цвета картинки
    mask = mask_using_threshold(image)
    dominant_color = dominant_color_finding(image, mask)

    
    """kernel_size = max(1, target_height)
    if kernel_size % 2 == 0:  # Делаем нечетным
        kernel_size += 1
    mask = np.ones((target_width, target_height), dtype=np.uint8)*255
    image =cv2.GaussianBlur(mask, (kernel_size, kernel_size), 0) #gaussian_filter(image, sigma=(5, 5, 0), mode='nearest')"""

    
    top = bottom = target_height//2
    left = right = target_width//2
    #image = add_padding(image, top, bottom, left, right, color=image[0][0])
    image = Image.fromarray(image)
    image = resize_object_centered(image, scale_factor=0.7)
    image = np.array(image)
    
    target_height, target_width  = image.shape[:2]

    # делаем бэкграунд
    target_back_height, target_back_width = image_background.shape[:2]

    ellipse = create_elliptical_gradient(width=target_back_width, height=target_back_height, center_color=dominant_color, 
                               center_x=target_back_width//2, center_y=target_back_height//2, 
                               radius_x=target_back_width//2, radius_y=target_back_height//2)   
    
    if number == 0:
        image_background = gauss(np.array(image_background), radius=30, sigma=(10, 10, 0))
        image = gauss(image, radius=25, sigma=(2, 2, 0))

    if image_background.shape[2] == 3:
        print("Добавляем альфа-канал")
        alpha_channel = np.full((target_back_height, target_back_width), 255, dtype=np.uint8)
        image_background = np.dstack((image_background, alpha_channel))
        print("Min:", image_background.min(), "Max:", image_background.max())
        print(image_background[0, 0])

    #image_background = create_radial_gradient(target_width, target_height, dominant_color, average_color)

    #prepared_for_ellipse_bg = prepare_background(image_background, ellipse)

    image_background = apply_background_with_blending(ellipse, image_background, image_background)

    #image_background = concotenate(ellipse, image_background)


    center = (target_back_height//2, target_back_width//2)
    radius = target_back_width//4

    cv2.circle(image_background, center, radius, average_color)
    vertices = np.array([[0, target_back_width],
                        [0, target_back_width*4//7],
                        #[0, target_height*6//11],
                        [target_back_height*3//4, target_back_width//2],
                        [target_back_height, target_back_width*60//100],
                        [target_back_height, target_back_width]])
    
    image_background = floor(image_background, average_color, vertices)

    image = resize_object_centered(Image.fromarray(image), scale_factor=0.7)
    mask_image = resize_object_centered(image, scale_factor=0.5, background_color = (0, 0, 0, 0))

    prepared_bg = prepare_background(np.array(image), image_background)

    if image.mode != "RGBA":
        image = image.convert("RGBA")

    if mask_image.mode != "RGBA":
        mask_image = mask_image.convert("RGBA")

    text_color = (255, 255, 255) if np.mean(dominant_color) > 128 else (0, 0, 0)

    width, height = image.width, image.height

    # маска прозрачной картинки
    mask = get_alpha_mask(mask_image)
    if number == 0:
        empty_rects = find_empty_rectangles(mask)

        empty_rects = split_large_rectangles(
        empty_rects,
        width,
        height,
        min_relative_width = 0.2,
        min_relative_height = 0.1
        )
    else:
        empty_rects = [(0, 0, width, height)] #[(width*2//5, height//3, width*3//5, height//2), (0, height//2, width//3, height), (width//3, height//2, width*2//3, height), (width*2//3, height//2, width, height)]
        empty_rects = split_rectangle_to_center(width, height, len(texts))
        #empty_rects = not_first_split_large_rectangles(
        #empty_rects,
        #width,
        #height,
        #min_relative_width = 0.2,
        #min_relative_height = 0.1,
        #max_split_parts = 8
        #)
        #find_empty_rectangles_in_all_mask(mask)

    # разбить большие прямоугольники на несколько поменьше (чтобы вставить больше текста)
    #width, height = image.shape[:2]
    
    #not_first_split_large_rectangles

    if need_mask:
        mask = mask_using_threshold(image)
        image = Image.fromarray(apply_background_with_blending(np.array(image), prepared_bg, mask))
    else:
        image = Image.fromarray(apply_background_with_blending(np.array(image), prepared_bg, prepared_bg))

    if number != 0:
        image = gauss(np.array(image), radius=30, sigma=(80, 80, 0))
        image = Image.fromarray(image)

    image = add_text_to_rectangles(
        Image.fromarray(image_background),
        empty_rects,
        texts,
        font_path=font_path,
        font_size=200,
        text_color=(0,0,0),
        padding=15
    )

    return np.array(image)