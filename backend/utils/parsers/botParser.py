import asyncio
import json
import os
import random
import re
import shutil

import dateparser
from playwright.async_api import async_playwright, Page, ElementHandle

from backend.utils.parsers.browserLauncher import ChromeBrowserLauncher
from backend.utils.parsers.downloader import Downloader
from backend.utils.parsers.pageWalker import PageWalker
from backend.utils.parsers.parserConfig import ParserConfig
from backend.utils.parsers.parserResult import ParsingData

import logging

logger = logging.getLogger(__name__)


class OzonParser:
    logger.info("1")
    def __init__(self):
        self.__url = None

    async def parse(self, url):
        self.__url = url
        logger.info("2")

        result = ParsingData.result(url, ParserConfig.CURRENT_TIMESTAMP)
        logger.info("3")
        browser = None

        async with (async_playwright() as p):
            try:
                logger.info("4")
                browser, context = await ChromeBrowserLauncher.launch(p)

                product_id = self.__get_product_id_from_url(url)
                output_path = self.__update_path_with_dynamic_info(f'{ParserConfig.OUTPUT_DIR}/tmp', product_id)
                shutil.rmtree(output_path, ignore_errors=True)
                product_data = await self.__run_in_browser_context(context, output_path)

                result["product_data"].update(product_data)
                result["success"] = True
                logger.info("5")

                # Сохраняем результат в JSON
                with open(os.path.join(output_path, 'product_data.json'), 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                logger.info("6")

                if ParserConfig.DEBUG_PARSING:
                    print(f"Результат парсинга: {result}")

                self.__rotate_dirs(output_path)
                logger.info("7")

                print(f"✅ Парсинг завершен. Данные сохранены в {output_path}")

            except Exception as e:
                print(f"🔥 Ошибка парсинга: {e}")
                # Логируем стек
                import traceback
                traceback.print_exc()
                raise
            finally:
                await ChromeBrowserLauncher.shutdown(browser)

        return result

    async def __run_in_browser_context(self, context, output_path):
        logger.info("8")
        page = await self.__user_interaction(ParserConfig.BASE_OZON_URL, context)
        logger.info("9")

        product_data = ParsingData.product_data()

        # ID продукта
        product_id = await self.__load_from_state(page, 'webDetailSKU')
        product_id = product_id['copyText']
        product_data['product_id'] = product_id

        # Имя продавца
        product = await self.__load_from_state(page, 'webStickyProducts')
        product_data['provider'] = product['seller']['name']

        # Категория
        product_categories = await self.__load_from_state(page, 'breadCrumbs')
        product_category = product_categories['breadcrumbs'][0]['text']
        product_data['category'] = product_category

        # Бренд
        product_brand = product_categories['breadcrumbs'][-1]['text']
        product_data['brand'] = product_brand

        # Название товара
        product_heading = await self.__load_from_state(page, 'webProductHeading')
        product_data['title'] = product_heading['title']

        # Цена товара
        product_price = await self.__load_from_state(page, 'webPrice')
        product_original_price = product_price['originalPrice']
        product_data['currency'] = re.split('\s+', product_original_price)[-1]
        product_data['original_price'] = int(self.__digits_only(product_original_price))
        product_data['price'] = int(self.__digits_only(product_price['price']))
        logger.info("10")

        # Описание товара
        await self.__expand_long_description(page)
        product_descriptions = await page.locator('[data-widget="webDescription"]').all_inner_texts()
        product_description = '\n\n'.join(product_descriptions)
        product_description = re.sub('\s+', ' ', product_description)
        product_data['description'] = product_description
        logger.info("11")

        # Изображения продукта
        img_dir = os.path.join(output_path, 'main_imgs')
        os.makedirs(img_dir, exist_ok=True)
        main_imgs = await self.__parse_images(page, img_dir)
        product_data['main_imgs'] = main_imgs

        # Рейтинг и количество отзывов
        review_product_score = await self.__load_from_state(page, 'webReviewProductScore')
        product_reviews_count = review_product_score['reviewsCount']
        product_data['reviews_count'] = int(product_reviews_count)

        product_data['rating'] = None
        logger.info("12")
        if product_reviews_count > 0:
            single_product_score = await self.__load_from_state(page, 'webSingleProductScore')
            product_score = single_product_score['text']
            product_rating = re.split('\s', product_score)[0]
            product_data['rating'] = float(product_rating) if product_rating is not None else None

            # Отзывы
            desc_img_dir = os.path.join(output_path, 'desc_imgs')
            os.makedirs(desc_img_dir, exist_ok=True)
            await self.__load_all_reviews(page, int(product_reviews_count))

            review_data = await self.__parse_reviews(page, desc_img_dir)
            product_data['reviews'] = review_data['reviews']
            product_data['desc_imgs'] = review_data['desc_imgs']
        logger.info("13")

        return product_data

    async def __user_interaction(self, base_url, context) -> Page:
        page: Page = await context.new_page()

        # Эмулируем поведение пользователя
        await page.goto(f'{base_url}', wait_until="networkidle")
        await asyncio.sleep(random.uniform(2, 3))

        # Основной запрос
        await page.goto(self.__url, wait_until="domcontentloaded", timeout=30000)
        page_title = await page.title()
        if "Доступ ограничен" in page_title:
            raise Exception("Обнаружена страница блокировки")

        # Дополнительные взаимодействия
        for _ in range(random.randint(2, 4)):
            await page.mouse.wheel(0, random.randint(300, 600))
            await asyncio.sleep(random.uniform(0.5, 1.5))

        # Прохождение страницы защиты по возрасту
        try:
            adult_page = await page.query_selector('[data-widget="userAdultModal"]')

            if adult_page is not None:
                year_of_birth_for_22y_old = ParserConfig.CURRENT_TIMESTAMP.date().year - 22
                await page.locator('input[type="text"]').fill(f'10.10.{year_of_birth_for_22y_old}')
                await page.get_by_role('button').get_by_text('Подтвердить').click()
                await asyncio.sleep(random.uniform(0.9, 1.5))

                await page.goto(self.__url, wait_until="domcontentloaded", timeout=10000)

        except Exception as e:
            print(f'Страница защиты возраста не пройдена: {e}')


        return page

    async def __load_from_state(self, page, state_name):
        state_locator = page.locator(f'div[id^="state-{state_name}-"]')
        state_string = await state_locator.get_attribute('data-state')
        state_json = json.loads(state_string)
        return state_json

    async def __load_all_reviews(self, page: Page, reviews_count: int):
        await PageWalker.scroll_to_element(page, '[data-widget="webAnchor"]')
        await page.wait_for_selector ('[data-widget="webListPhotos"]')
        await PageWalker.scroll_to_element(page, '[data-widget="webListPhotos"]')
        await PageWalker.scroll_to_element_continuously(page, '[data-widget="webListReviews"]', reviews_count)
        await self.__expand_long_reviews(page)
        await self.__expand_review_comments(page)

    async def __expand_long_description(self, page):
        tag = 'button'
        match_text = "Показать полностью"
        await PageWalker.click_element(page, tag, match_text)

    async def __expand_long_reviews(self, page):
        tag = 'span'
        match_text = "Читать полностью"
        await PageWalker.click_element(page, tag, match_text)

    async def __expand_review_comments(self, page):
        tag = 'button'
        match_text = "комментари"  # совпадает с (n комментариев)
        await PageWalker.click_element(page, tag, match_text)

    async def __parse_images(self, page, img_dir):
        main_imgs = []
        try:
            img_links = await PageWalker.extract_image_urls(page, '[data-widget="webGallery"] img[loading]')
            img_links = self.__filter_and_transform_img_src(img_links)
            # Возвращаем сами URL, не скачивая
            return img_links
        except Exception as e:
            print(f"🔥 Ошибка при парсинге изображений: {e}")
            return []

    async def __parse_reviews(self, page, desc_img_dir):
        review_data = {
            "reviews": {},
            "desc_imgs": []
        }

        try:
            review_elements: list[ElementHandle] = await page.query_selector_all('[data-review-uuid]')
            reviews = {}
            desc_imgs = []
            desc_img_counter = 1
            for review_element in review_elements:
                review_uuid = await review_element.get_attribute("data-review-uuid")
                review = ParsingData.product_review()

                review_text = re.sub("\s+", " ", await review_element.inner_text())
                review['review_text'] = review_text
                await self.__parse_review_text(review)

                all_svgs = await review_element.query_selector_all('svg')

                review_rating = 0
                for svg_element in all_svgs:
                    style_attribute = await svg_element.get_attribute('style')
                    if style_attribute is not None and style_attribute.startswith('color: rgb(255, 165, 0)'):
                        review_rating += 1

                review['review_rating'] = review_rating

                desc_img_links = await PageWalker.extract_image_urls(review_element, 'img[loading]')
                desc_img_links = self.__filter_and_transform_img_src(desc_img_links)

                review['review_images'] = desc_img_links
                reviews[review_uuid] = review

            review_data['reviews'] = reviews
            review_data['desc_imgs'] = desc_imgs
            return review_data

        except Exception as e:
            print(f"🔥 Ошибка при парсинге отзывов: {e}")
            return review_data

    async def __parse_review_text(self, review):
        try:
            review_text = review['review_text']
            regex = (r'(?:[A-ZА-ЯЁё]\s){0,1}([A-zА-яЁё\s\.]+)'
                     r'\s(\d{1,2}\s[a-я]+\s\d{4})'
                     r'\s([А-яЁё\s\w\W]+)'
                     r'\sВам помог этот отзыв\?'
                     r'\sДа\s(\d+)'
                     r'\sНет\s(\d+)'
                     r'\s*([А-яЁё\s\w\W]+)*')
            match = re.match(regex, review_text)

            review['reviewer_name'] = match.group(1) if not match.group(1).startswith("Пользователь предпочёл скрыть свои данные") else None

            parsed_date = match.group(2)
            json_date = dateparser.parse(parsed_date)
            review['review_date'] = json_date.strftime('%d.%m.%Y')

            review['review_comments'] = None
            review['review_text'] = match.group(3)
            review['positive_help'] = int(match.group(4))
            review['negative_help'] = int(match.group(5))

        except Exception as e:
            print(f"Ошибка при парсинге текста отзыва: {e}")

    def __digits_only(self, a_str):
        return ''.join(i for i in a_str if i.isdigit())

    def __filter_and_transform_img_src(self, image_sources):
        substrings_filter = [
            '/video',
            'ozonusercontent.com'
        ]
        res_image_sources = []
        for imgsrc in image_sources:
            if not any(substring in imgsrc for substring in substrings_filter):
                imgsrc = re.sub('/wc[15]00?/', '/wc1000/', imgsrc)
                res_image_sources.append(imgsrc)

        return res_image_sources

    def __get_product_id_from_url(self, url):
        try:
            product_id = url.removeprefix(f'{ParserConfig.BASE_OZON_URL}/product/')
            product_id = product_id.split('/')[0]
            product_id = product_id.split('?')[0]
            product_id = product_id.split('-')[-1]
            return product_id

        except Exception as e:
            print(f"Ошибка при получении product_id из url: {e}")
            return None

    def __update_path_with_dynamic_info(self, path: str, product_id) -> str:
        return path.replace('%product_id%', product_id)

    def __rotate_dirs(self, output_path):
        if ParserConfig.DEBUG_PARSING:
            print('TODO: реализовать ротацию каталогов current -> previous, tmp -> current ')


if __name__ == "__main__":

    print(f'🖙 Введите ссылку продукта Ozon:')
    product_url = str(input())

    url_prefix = 'https://'
    if not product_url.startswith(url_prefix):
        print(f'Ссылка продукта должна начинаться с {url_prefix}')
        exit(1)

    print('Начался процесс парсинга...')
    res = asyncio.run(OzonParser().parse(product_url))