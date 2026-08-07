from playwright.async_api import async_playwright
import random
from datetime import datetime
import asyncio

import logging

logger = logging.getLogger(__name__)

async def parse_ozon(url):
    logger.info("1")
    
    result = {
        "url": url,
        "timestamp": datetime.now().isoformat(),
        "success": False,
        "product_data": {
            "title": None,
            "price": None,
            "currency": "₽",
            "rating": None,
            "reviews_count": None,
            "description": None,
            "category": None,
            "feedbacks": None
        }
    }
    logger.info("2")

    async with async_playwright() as p:
        browser = None
        try:
            logger.info("3")
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",  # Важно для Docker
                    "--disable-dev-shm-usage",   # Решает проблему с /dev/shm
                    "--disable-blink-features=AutomationControlled",
                    "--single-process",
                    "--start-maximized",
                    "--disable-web-security"
                ],
                slow_mo=random.randint(300, 800)
            )
            logger.info("4")

            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="ru-RU"
            )

            logger.info("5")

            page = await context.new_page()
            
            # Эмулируем поведение пользователя
            await page.goto("https://www.ozon.ru/", wait_until="networkidle")
            await asyncio.sleep(random.uniform(1, 3))
            
            logger.info("6")
            async def load_all_reviews():
                attempts = 0
                while True:
                    load_more_btn = await page.query_selector('button:has-text("Показать еще")')
                    if not load_more_btn:
                        break
                    
                    try:
                        await load_more_btn.click()
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                    except:
                        break
                    attempts += 1
            logger.info("7")

            await load_all_reviews()
            logger.info("8")

            # Основной запрос
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                logger.info("9")
            except Exception as e:
                logger.info("10")
                logger.error(f"Ошибка при загрузке страницы: {e}")
                result["error"] = str(e)
                return result
            
            logger.info("11")
            await page.wait_for_selector('[data-widget="webPrice"]', timeout=10000)
            page_title = await page.title()
            if "Доступ ограничен" in page_title:
                raise Exception("Обнаружена страница блокировки")

            logger.info("12")
            # Дополнительные взаимодействия
            for _ in range(random.randint(2, 4)):
                await page.mouse.wheel(0, random.randint(300, 600))
                await asyncio.sleep(random.uniform(0.5, 1.5))

            logger.info("13")
            # Извлекаем данные с помощью JavaScript
            try:
                product_info = await page.evaluate('''() => {
                    const result = {
                        title: null,
                        price: null,
                        currency: "₽",
                        rating: null,
                        reviews_count: null,
                        description: null,
                        category: null,
                        reviews: []
                    };

                    // Название товара
                    result.title = document.querySelector('h1')?.innerText.trim() || 
                                document.querySelector('[data-widget="webProductHeading"]')?.innerText.trim();

                    // Цена товара
                    const priceElement = document.querySelector('[data-widget="webPrice"]');
                    if (priceElement) {
                        price_inst= String(priceElement.innerText.trim());
                        result.price = parseFloat(price_inst.replace(/\s/g, ''));
                    }

                    // Рейтинг и отзывы
                    const ratingElement = document.querySelector('[data-widget="webSingleProductScore"]');
                    if (ratingElement) {
                        result.rating = parseFloat(ratingElement.innerText.trim());
                        
                        const reviewsElement = document.querySelector('[data-widget="webReviewProductScore"]');
                        if (reviewsElement) {
                            result.reviews_count = parseFloat(reviewsElement.innerText.trim());
                        }
                    }
                                            
                    // Описание товара
                    const descriptionElement = document.querySelector('[data-widget="webDescription"]');
                    if (descriptionElement) {
                        result.description = String(descriptionElement.innerText.trim()).replace(/\s+/g, ' ');
                    }
                    
                    // Категория
                    const categoryElement = document.querySelector('[data-widget="webPdpGrid"]');
                    if (categoryElement) {
                        const text = categoryElement.textContent.trim();
                        const words = text.split(/(?=[А-ЯЁA-Z])/);
                        result.category = words[0];
                    }
                                        
                    const reviewsElements = document.querySelectorAll('[data-widget="webListReviews"] .review-item'); // Уточните селектор
                    if (reviewsElements.length > 0) {
                        reviewsElements.forEach(el => {
                            const text = el.innerText
                                .replace(/Показать полностью/g, '')
                                .trim();
                            result.reviews.push(text);
                        });
                    }

                    return result;
                }''')
                logger.info("14")

            except Exception as e:
                logger.error(f"Ошибка при загрузке страницы: {e}")
                result["error"] = str(e)
                return result

            #image_urls = await page.evaluate('''() => {
            #    const images = new Set();
            #    
            #    // Основное изображение
            #    const mainImg = document.querySelector('[data-widget="webGallery"] img[loading="eager"]');
            #    if (mainImg && mainImg.src) images.add(mainImg.src);
            #    
            #    // Дополнительные изображения
            #    document.querySelectorAll('[data-widget="webGallery"] img[loading="lazy"]').forEach(img => {
            #        if (img.src) images.add(img.src);
            #    });
            #    
            #    return Array.from(images).slice(0, 5);
            #}''')

            result["product_data"].update(product_info)
            logger.info("-1")

            result["success"] = True

        except Exception as e:
            print(f"Ошибка: {e}")

        finally:
            if browser:
                await browser.close()
            
    return result