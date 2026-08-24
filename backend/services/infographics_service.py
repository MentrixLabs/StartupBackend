import torch
from diffusers import Kandinsky5I2IPipeline
from diffusers.utils import load_image
from io import BytesIO
import base64
import logging
from typing import List, Optional
from fastapi import HTTPException
from db.db import async_session_maker
from db.ozon.dao import OzonItemDAO, InfographicsDataDAO


logger = logging.getLogger(__name__)

# Глобальный пайплайн – инициализируем лениво
_pipe = None


def get_pipeline():
    global _pipe
    if _pipe is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading Kandinsky I2I pipeline on {device}")
        model_id = "kandinskylab/Kandinsky-5.0-I2I-Lite-sft-Diffusers"
        try:
            _pipe = Kandinsky5I2IPipeline.from_pretrained(
                model_id,
                torch_dtype=torch.bfloat16 if device == "cuda" else torch.float32
            )
            _pipe = _pipe.to(device)
            if device == "cpu":
                _pipe.enable_sequential_cpu_offload()
            else:
                _pipe.enable_model_cpu_offload()
        except Exception as e:
            logger.error(f"Failed to load Kandinsky pipeline: {e}")
            raise RuntimeError("Could not initialize image generation model")
    return _pipe

async def generate_infographics(goods_id: int, user_id: int, count: int = 4) -> List[str]:
    """
    Генерирует изображения для товара с помощью Kandinsky I2I.
    Возвращает список data-URL (base64) или ссылки на placeholder при ошибке.
    """
    # 1. Получаем данные товара
    async with async_session_maker() as session:
        goods = await OzonItemDAO.find_one_or_none(id=goods_id, user_id=user_id)
        if not goods:
            raise HTTPException(status_code=404, detail="Товар не найден или доступ запрещён")

        image_url = None
        if goods.main_imgs and len(goods.main_imgs) > 0:
            image_url = goods.main_imgs[0]
        elif goods.desc_imgs and len(goods.desc_imgs) > 0:
            image_url = goods.desc_imgs[0]

        prompt = f"Professional product photography of {goods.cardname}. {goods.description[:200]}"
        if goods.brand:
            prompt += f" Brand: {goods.brand}."
        negative_prompt = "low quality, blurry, text, watermark, distorted"

    # 2. Загружаем пайплайн (может упасть, если модель не доступна)
    try:
        pipe = get_pipeline()
    except Exception:
        logger.warning("Kandinsky pipeline unavailable, returning placeholder images")
        return _generate_placeholder_images(count, goods.cardname)

    # 3. Загружаем входное изображение (если есть)
    input_image = None
    if image_url:
        try:
            input_image = load_image(image_url)
        except Exception as e:
            logger.warning(f"Could not load image from {image_url}: {e}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    images = []

    for i in range(count):
        try:
            generator = torch.Generator(device=device).manual_seed(42 + i)
            if input_image is not None:
                output = pipe(
                    image=input_image,
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    guidance_scale=3.5,
                    num_inference_steps=30,
                    generator=generator,
                    height=512,
                    width=512,
                )
            else:
                # Если нет входного изображения, используем T2I пайплайн – здесь для простоты возвращаем placeholder
                logger.warning("No input image, skipping I2I generation")
                return _generate_placeholder_images(count, goods.cardname)

            img = output.images[0] if isinstance(output.images, list) else output.images
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            images.append(f"data:image/png;base64,{img_base64}")
        except Exception as e:
            logger.error(f"Error generating image {i}: {e}")

    if not images:
        images = _generate_placeholder_images(count, goods.cardname)

    async with async_session_maker() as session:
        existing = await InfographicsDataDAO.find_one_or_none(goods_id=goods_id)
        data = {"generated_images": images}
        if existing:
            await InfographicsDataDAO.update(existing.id, **data)
        else:
            await InfographicsDataDAO.add(goods_id=goods_id, generated_images=[], enhanced_images=[data_url])

    return images

def _generate_placeholder_images(count: int, name: str) -> List[str]:
    """Заглушка – возвращает ссылки на случайные изображения."""
    return [f"https://picsum.photos/seed/{name}_{i}/400/400" for i in range(count)]