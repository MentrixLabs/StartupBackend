import io
import base64
import logging
from typing import List, Optional
from PIL import Image, ImageDraw, ImageFont
import requests
from fastapi import HTTPException
from db.db import async_session_maker
from db.ozon.dao import OzonItemDAO, InfographicsDataDAO


logger = logging.getLogger(__name__)


def get_font(size: int):
    """Загружает шрифт Nunito из Google Fonts (кэширует в памяти)."""
    # Кэшируем шрифт в глобальной переменной (или используйте functools.lru_cache)
    if not hasattr(get_font, "cache"):
        url = "https://fonts.gstatic.com/s/nunito/v26/XRXV3I6Li01BKofIOOuBXso.woff2"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            font_bytes = io.BytesIO(resp.content)
            get_font.cache = ImageFont.truetype(font_bytes, size)
        else:
            get_font.cache = ImageFont.load_default()
    return get_font.cache

async def enhance_goods_images(goods_id: int, user_id: int) -> dict:
    """
    Улучшает изображения товара:
    - создаёт главное изображение-коллаж (если есть несколько)
    - добавляет текстовую информацию
    - возвращает список обработанных изображений (base64)
    """
    async with async_session_maker() as session:
        goods = await OzonItemDAO.find_one_or_none(id=goods_id, user_id=user_id)
        if not goods:
            raise HTTPException(404, "Товар не найден")

        # Собираем все URL изображений
        all_images = (goods.main_imgs or []) + (goods.desc_imgs or [])
        if not all_images:
            return {"enhanced": []}

        # Загружаем изображения (максимум 4 для коллажа)
        images = []
        for url in all_images[:4]:
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    img = Image.open(io.BytesIO(resp.content))
                    images.append(img)
            except Exception as e:
                logger.warning(f"Не удалось загрузить {url}: {e}")

        if not images:
            return {"enhanced": []}

        # 1. Создаём коллаж (если >1 изображения)
        if len(images) > 1:
            main_image = make_collage(images, cols=2)
        else:
            main_image = images[0].copy()

        # 2. Добавляем текстовую информацию (название, цена)
        main_image = add_text_overlay(main_image, goods.cardname or "Товар", goods.original_price, font_title = get_font(24), font_price = get_font(20))

        # 3. Конвертируем в WebP (оптимизация) и в base64
        buffered = io.BytesIO()
        main_image.save(buffered, format="WEBP", quality=85)
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        data_url = f"data:image/webp;base64,{img_base64}"

        async with async_session_maker() as session:
            existing = await InfographicsDataDAO.find_one_or_none(goods_id=goods_id)
            data = {"enhanced_images": [data_url]}  # список, т.к. может быть несколько
            if existing:
                await InfographicsDataDAO.update(existing.id, **data)
            else:
                # если записи нет, создаём с пустым generated_images и enhanced_images
                await InfographicsDataDAO.add(goods_id=goods_id, generated_images=[], enhanced_images=[data_url])

    return {"enhanced": [data_url]}


def make_collage(images, cols=2):
    """Создаёт квадратный коллаж из списка PIL Image."""
    # Определяем размер каждой миниатюры (квадратные)
    sizes = [img.size for img in images]
    min_side = min(min(w, h) for w, h in sizes)
    thumb_size = (min_side, min_side)
    thumbs = [img.resize(thumb_size, Image.LANCZOS) for img in images]

    rows = (len(thumbs) + cols - 1) // cols
    collage_width = cols * thumb_size[0]
    collage_height = rows * thumb_size[1]
    collage = Image.new('RGB', (collage_width, collage_height), color=(255,255,255))

    for idx, thumb in enumerate(thumbs):
        x = (idx % cols) * thumb_size[0]
        y = (idx // cols) * thumb_size[1]
        collage.paste(thumb, (x, y))

    return collage


def add_text_overlay(image: Image.Image, title: str, price: Optional[int] = None, font_title = get_font(24), font_price = get_font(20)) -> Image.Image:
    """Добавляет текст внизу изображения (полупрозрачная подложка)."""
    img = image.copy()
    draw = ImageDraw.Draw(img)
    # Пытаемся загрузить шрифт, если нет – используем дефолтный
    #try:
    #    font_title = ImageFont.truetype("arial.ttf", 24)
    #    font_price = ImageFont.truetype("arial.ttf", 20)
    #except:
    #    font_title = ImageFont.load_default()
    #    font_price = ImageFont.load_default()

    # Полоса внизу
    overlay = Image.new('RGBA', img.size, (0,0,0,0))
    overlay_draw = ImageDraw.Draw(overlay)
    # Полупрозрачный чёрный прямоугольник снизу
    overlay_draw.rectangle([(0, img.height-80), (img.width, img.height)], fill=(0,0,0,120))
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')

    # Текст
    draw = ImageDraw.Draw(img)
    text = title[:40] + "..." if len(title) > 40 else title
    draw.text((20, img.height-65), text, fill=(255,255,255), font=font_title)
    if price:
        draw.text((20, img.height-35), f"{price} ₽", fill=(255,215,0), font=font_price)
    else:
        draw.text((20, img.height-35), "Цена не указана", fill=(200,200,200), font=font_price)
    return img