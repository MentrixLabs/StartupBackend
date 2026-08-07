from datetime import datetime


# Конфигурация
class ParserConfig:
    DEBUG_PARSING = True
    # DEBUG_BROWSER = True
    DEBUG_BROWSER = False
    CURRENT_TIMESTAMP = datetime.now()
    BASE_OZON_URL = "https://www.ozon.ru"
    BASE_OZON_DIR = 'parser_data/ozon'
    OUTPUT_DIR = f'{BASE_OZON_DIR}/%product_id%'
    MAX_RETRIES = 3