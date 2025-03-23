from dotenv import load_dotenv
import os
import base64

load_dotenv()

DGIS_API = os.getenv("DGIS_API")
YANDEX_API = os.getenv("YANDEX_API")
DGIS_API_KEY = os.getenv("DGIS_API_KEY")
FLAMP_API = os.getenv("FLAMP_API")
REVIEWS_LIMIT = 50
KEY_STR = os.getenv("KEY")
KEY = base64.b64decode(KEY_STR)
