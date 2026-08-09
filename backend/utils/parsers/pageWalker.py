import asyncio
import random

from playwright.async_api import Page

from backend.utils.parsers.parserConfig import ParserConfig


class PageWalker:

    @classmethod
    async def click_element(cls, page, tag, match_text):
        try:
            await page.evaluate(
                f'[...document.querySelectorAll("{tag}")].filter(el => el.textContent.includes("{match_text}")).forEach(el => el.click())')
        except Exception as e:
            print(f"🔥 Отсутствуют текстовые элементы '{match_text}': {e}")

    @classmethod
    async def extract_image_urls(cls, handle, selector):
        try:
            images = await handle.query_selector_all(selector)
            image_sources = [await img.get_attribute('src') for img in images]
            return image_sources

        except Exception as e:
            print(f"🔥 Ошибка при получении ссылок на изображения: {e}")
            return None

    @classmethod
    async def scroll_to_element(cls, page, selector):
        try:
            target_element = await page.query_selector(selector)
            if target_element is not None:
                await page.evaluate(f"document.querySelector('{selector}').scrollIntoView()")
        except Exception as e:
            print(f"🔥 Невозможна прокрутка до выбранного элемента: {selector}; {e}")

    @classmethod
    async def scroll_to_element_continuously(cls, page: Page, selector,
                                             max_number_of_elements=1,
                                             max_retries=ParserConfig.MAX_RETRIES,
                                             debug=ParserConfig.DEBUG_PARSING):
        last_selector_element = f'{selector}:last-child'
        try:
            previous_number_of_elements = 0
            retries = 0
            while True:
                await PageWalker.scroll_to_element(page, last_selector_element)
                await asyncio.sleep(random.uniform(0.9, 1.5))

                # Get the current scroll height
                safe_selector = selector.replace('"', '\\"')
                current_number_of_elements = await page.evaluate(f'document.querySelectorAll("{safe_selector}").length')

                if debug:
                    print(
                        f'Кол-во элементов {selector} (до прокрутки/после прокрутки/всего):'
                        f' {previous_number_of_elements}/{current_number_of_elements}/{max_number_of_elements}')

                # Check if we've reached the bottom
                if (current_number_of_elements == previous_number_of_elements
                        or current_number_of_elements >= max_number_of_elements):
                    retries += 1
                else:
                    retries = 0

                if retries >= max_retries:
                    break

                previous_number_of_elements = current_number_of_elements
        except Exception as e:
            print(f"🔥 Невозможна циклическая прокрутка до выбранного элемента: {last_selector_element}")