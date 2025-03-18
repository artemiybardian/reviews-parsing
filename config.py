from dotenv import load_dotenv
import os

load_dotenv()

DGIS_API = os.getenv("DGIS_API")
DGIS_API_KEY = os.getenv("DGIS_API_KEY")
FLAMP_API = os.getenv("FLAMP_API")
REVIEWS_LIMIT = 50
