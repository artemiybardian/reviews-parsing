from dotenv import load_dotenv
from typing import Optional
from fastapi import APIRouter
from schemas import YandexRequestSchema, ReviewListSchema
from decoder import decrypt_session_id
from responses import get_error_response, get_success_response
from config import YANDEX_API
import re
import json
import aiohttp
import urllib3
import uuid
import time
import urllib.parse
import asyncio
import ssl as ssl_module
import os

router = APIRouter()

# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@router.get("/parse_reviews/yandex/")
async def parse_reviews(request: YandexRequestSchema):
    try:
        session_id = decrypt_session_id(request.encrypted_session_id)
    except Exception as e:
        return get_error_response(error_code=400, message=str(e))

    yandex_business = YandexBusinessAsync(request.filial_id, session_id, https_proxy=request.https_proxy)
    response = await yandex_business.send_all_reviews()
    if response["status"] == "error":
        return get_error_response(error_code=response["error"]["error_code"], message=response["error"]["message"])
    return {"status": response["status"], "error": None, "message": "Парсинг завершён успешно."}


class YandexBusinessAsync:
    def __init__(self, filial_id: str, session_id: str, https_proxy: Optional[str] = None, timeout: int = 3):

        # Parse cookies if string is provided
        self.session_id = session_id
        self.filial_id = filial_id
        self.timeout = timeout

        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
            "Cookie": f"i=2G7LCnUkOTyyWpRvX4fOZaek68FAGv8o8oQI7djCE2/gx2RBw6hsglNvqEqGvDkaqBS9/YDvNlCC2gpOnRWEH7+q8vM=; Session_id={self.session_id};",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
        }

        # Add proxy configuration
        self.proxies = {"http": "http://127.0.0.1:8080", "https": https_proxy}
        self.verify = False

        # Create an SSL context that doesn't verify certificates
        if not self.verify:
            self.ssl_context = ssl_module.create_default_context()
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl_module.CERT_NONE
        else:
            self.ssl_context = True

    # Get all reviews
    async def send_all_reviews(self):
        try:
            page = 1
            while True:
                data = await self.get_one_page_reviews(page)
                if data == False:
                    break

                reviews_json = get_success_response(data, filial_id=self.filial_id)

                try:
                    continue_parsing = await save_reviews_to_storage(reviews_json)
                    if not continue_parsing:
                        print("Парсинг завершен, микросервис вернул false")
                        break
                except Exception as e:
                    print(f"Ошибка при сохранении отзывов: {str(e)}")
                    return get_error_response(500, str(e))

                page += 1

                print(f"Партия из {len(data)} отзывов успешно отправлена в микросервис.")
                print("Завершена часть парсинга")

                await asyncio.sleep(self.timeout)

            return {"status": "success", "error": None}
        except Exception as e:
            return get_error_response(500, str(e))

    # Get one page reviews
    async def get_one_page_reviews(self, page):
        # Set session headers

        headers = self.headers.copy()
        headers.update(
            {
                "Accept": "application/json; charset=UTF-8",
                "Content-Type": "application/json; charset=UTF-8",
                "Referer": "https://yandex.ru/sprav/",
                "X-Requested-With": "XMLHttpRequest",
            }
        )

        try:
            # Format parameters
            param_str = f"ranking=by_time&page={page}&type=company&source=pagination"

            # Use the same session for the reviews request
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://yandex.ru/sprav/api/{self.filial_id}/reviews?" + param_str,
                    proxy=self.proxies.get("https") if self.proxies else None,
                    ssl=self.ssl_context,
                    headers=headers,
                ) as response:
                    # Save response to file for debugging
                    # with open(f"yandex_response_page_{page}.json", "w", encoding="utf-8") as f:
                    #     f.write(await response.text())

                    if response.status == 200:
                        data = await response.json()
                        return data["list"]["items"]
                    elif response.status == 400:
                        print("Отзывом больше нет")
                        return False
                    else:
                        print("Error:")
                        print(response.status)
                        text = await response.text()
                        print(text)
                        return False
        except Exception as e:
            print(f"Error during request: {str(e)}")
            return False


# async def main():
#     # Read from .env file
#     filial_id = os.getenv("YANDEX_filial_id")
#     session_id = os.getenv("YANDEX_SESSION_ID")

#     if not filial_id or not session_id:
#         raise ValueError("Please set YANDEX_filial_id and YANDEX_SESSION_ID in your .env file")

#     yandex_business = YandexBusinessAsync(filial_id, session_id)

#     # Get all reviews
#     reviews = await yandex_business.get_all_reviews()
#     print(f"Found {len(reviews)} reviews")


async def save_reviews_to_storage(reviews: ReviewListSchema):
    async with aiohttp.ClientSession() as session:
        async with session.post(YANDEX_API, json=reviews) as response:
            if response.status != 200:
                return False
            return (await response.json()).get("result", False)
