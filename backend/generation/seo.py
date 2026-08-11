from backend.utils import DeepSeekModel

YANDEX_CLOUD_FOLDER = "b1gkcgd1bmt9rp9j1pj2"
YANDEX_CLOUD_API_KEY = "<API_key_value>"
YANDEX_CLOUD_MODEL = "deepseek-v4-flash/latest"
BASE_AI_URL = "https://ai.api.cloud.yandex.net/v1"

generation_model = DeepSeekModel(api_key = YANDEX_CLOUD_API_KEY,
                                 base_url = BASE_AI_URL,
                                 model = YANDEX_CLOUD_MODEL,
                                 max_tokens = 1500)