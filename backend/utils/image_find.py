import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageFilter
import io
import logging

logger = logging.getLogger(__name__)


def prepare_image(image):
    img_url = image['src']
    image_data = requests.get(img_url).content
    
    image = Image.open(io.BytesIO(image_data))

    MAX_WIDTH = 2000
    MAX_HEIGHT = 2000
    width, height = image.size
    
    ratio = min(MAX_WIDTH / width, MAX_HEIGHT / height)
    new_width = int(width * ratio)
    new_height = int(height * ratio)

    resized_image = image.resize((new_width, new_height), Image.Resampling.BICUBIC)
    
    resized_image = resized_image.filter(ImageFilter.SHARPEN)
    
    img_byte_arr = io.BytesIO()
    resized_image.save(img_byte_arr, format='JPEG', quality=90)
    resized_image_bytes = img_byte_arr.getvalue()

    return resized_image_bytes


#def parse_image(query, image_number = 0):
#    url = f"https://www.google.com/search?q={query}&tbm=isch"
#    response = requests.get(url)
#    soup = BeautifulSoup(response.text, 'html.parser')
#    images = soup.find_all('img')[1:]
#    prepared_image = prepare_image(images[image_number])
#    
#    return prepared_image

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import quote_plus
import time
import logging
from io import BytesIO
from PIL import Image
import re

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_image(query, image_number=0):
    """Основная функция для получения изображения"""
    try:
        # 1. Сначала пробуем Google
        try:
            return get_from_google(query, image_number)
        except Exception as google_error:
            logger.warning(f"Google не сработал: {google_error}")

        # 2. Затем пробуем Bing
        try:
            return get_from_bing(query)
        except Exception as bing_error:
            logger.warning(f"Bing не сработал: {bing_error}")

        # 3. В конце пробуем Unsplash (без номера изображения)
        try:
            return get_from_unsplash(query)
        except Exception as unsplash_error:
            logger.warning(f"Unsplash не сработал: {unsplash_error}")

        # Если все источники не сработали
        raise Exception("Не удалось получить изображение ни из одного источника")

    except Exception as e:
        logger.error(f"Ошибка в parse_image: {e}")
        raise

def get_from_unsplash(query):
    """Получение изображения через Unsplash API"""
    try:
        url = f"https://source.unsplash.com/random/800x600/?{quote_plus(query)}"
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        if response.status_code != 200:
            raise ValueError(f"Unsplash вернул статус {response.status_code}")
        
        # Проверяем что это изображение
        Image.open(BytesIO(response.content)).verify()
        return response.content

    except Exception as e:
        raise ValueError(f"Ошибка Unsplash: {str(e)}")

def get_from_google(query, image_number=0):
    """Получение конкретного изображения из Google по индексу"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(f"https://www.google.com/search?q={quote_plus(query)}&tbm=isch")
        
        # Ждем загрузки миниатюр и прокручиваем страницу, чтобы загрузилось больше изображений
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "img.Q4LuWd"))
        )
        
        # Прокручиваем страницу, чтобы загрузить больше изображений
        for _ in range(image_number // 20 + 1):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
        
        # Получаем все миниатюры после прокрутки
        thumbnails = driver.find_elements(By.CSS_SELECTOR, "img.Q4LuWd")
        if not thumbnails:
            raise ValueError("Миниатюры изображений не найдены")
        
        if image_number >= len(thumbnails):
            logger.warning(f"Запрошенный номер {image_number} превышает количество найденных изображений ({len(thumbnails)}). Используем последнее изображение.")
            image_number = len(thumbnails) - 1
        
        # Кликаем по выбранному изображению (с обработкой возможных ошибок клика)
        try:
            thumbnails[image_number].click()
        except:
            driver.execute_script("arguments[0].click();", thumbnails[image_number])
        
        # Ждем загрузки большого изображения
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "img.sFlh5c, img.n3VNCb, img.iPVvYb"))
        )
        
        # Находим все возможные элементы с изображением и выбираем самый большой
        img_elements = driver.find_elements(By.CSS_SELECTOR, "img.sFlh5c, img.n3VNCb, img.iPVvYb")
        if not img_elements:
            raise ValueError("Не удалось найти элемент с большим изображением")
        
        # Выбираем изображение с максимальным размером
        img_element = max(img_elements, key=lambda img: int(img.get_attribute('width') or 0))
        img_url = img_element.get_attribute('src') or img_element.get_attribute('data-src') or img_element.get_attribute('data-iurl')
        
        if not img_url:
            raise ValueError("Не удалось получить URL изображения")
        
        # Загружаем изображение
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.google.com/'
        }
        response = requests.get(img_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Проверяем что это изображение
        Image.open(BytesIO(response.content)).verify()
        return response.content
        
    except Exception as e:
        raise ValueError(f"Ошибка Google Images (image_number={image_number}): {str(e)}")
    finally:
        if driver:
            driver.quit()

def get_from_bing(query):
    """Получение изображения через Bing Images"""
    try:
        url = f"https://www.bing.com/images/search?q={quote_plus(query)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Ищем URL изображения в ответе
        image_urls = re.findall(r'murl&quot;:&quot;(https?://[^&]+)', response.text)
        if not image_urls:
            raise ValueError("Bing не вернул изображения")
        
        # Берем первое изображение
        img_url = image_urls[0]
        img_response = requests.get(img_url, headers=headers, timeout=10)
        img_response.raise_for_status()
        
        # Проверяем что это изображение
        Image.open(BytesIO(img_response.content)).verify()
        return img_response.content
        
    except Exception as e:
        raise ValueError(f"Ошибка Bing: {str(e)}")