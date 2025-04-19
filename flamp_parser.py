import asyncio
import json

import aiohttp
from fake_useragent import UserAgent
from fastapi import APIRouter

from config import FLAMP_API, REVIEWS_LIMIT, FLAMP_API_KEY
from responses import get_success_response, get_error_response

router = APIRouter()


@router.get("/parse_reviews/flamp/")
async def parse_reviews(filial_id: int, timeout: int = 7):
    filial_id_str = str(filial_id)
    ACCESS_TOKEN_URL = f"https://flamp.ru/firm/{filial_id}/"
    REVIEWS_API_URL = f"https://flamp.ru/api/2.0/filials/{filial_id}/reviews?limit={REVIEWS_LIMIT}"
    # access_token = await get_access_token(ACCESS_TOKEN_URL)
    # if not access_token:
    #     return {"status": "error", "data": [], "error": {"code": 500, "message": "Не удалось получить токен доступа."}}

    access_token = FLAMP_API_KEY
    offset_id = None
    while True:
        reviews_batch = await get_reviews_batch(REVIEWS_API_URL, access_token, ACCESS_TOKEN_URL, offset_id)

        if reviews_batch["status"] == "error":
            return get_error_response(
                reviews_batch["error"]["code"], reviews_batch["error"]["message"], filial_id=filial_id_str
            )

        if len(reviews_batch["data"]) == 0:
            print("Отзывов больше нет")
            break
        # file_path = Path("reviews_json.json")

        # Добавление в файл по желанию, для проверки правильной работы
        # async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
        #     await f.write(json.dumps(reviews_json, ensure_ascii=False, indent=4))

        # Отправляем партию отзывов в микросервис
        async with aiohttp.ClientSession() as session:
            async with session.post(FLAMP_API+str(filial_id), json=reviews_batch) as response:
                if response.status == 200:
                    print(f"Партия из {len(reviews_batch["data"])} отзывов успешно отправлена в микросервис.")
                    print("Завершена часть парсинга.")
                    offset_id = reviews_batch["offset_id"]
                else:
                    print(f"Ошибка отправки: {response.status}")
                    break

                response = await response.json()
                if not response:
                    print(f"Партия из {len(reviews_batch["data"])} отзывов успешно отправлена в микросервис.")
                    print("Парсинг завершен, микросервис вернул false")
                    break
        await asyncio.sleep(timeout)

    return {"status": "success", "error": None, "message": "Парсинг завершён успешно."}


async def get_access_token(access_token_url: str):
    url = await get_filial_url_with_slug(access_token_url)

    if not url:
        return None

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            cookies = response.cookies
            access_token = cookies.get("__cat").value if "__cat" in cookies else "Не найдено"
            print(access_token)

    return access_token


async def get_filial_url_with_slug(access_token_url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(access_token_url) as response:
            if response.status != 200:
                print(f"Ошибка при получении ссылки: {response.status}, тело ответа: {await response.text()}")
                return None
            print(f"Полученная ссылка после редиректа:{response.url}")
            return str(response.url)


async def get_reviews_batch(
    reviews_api_url: str, access_token: str, access_token_url: str, offset_id=None, retries=13, delay=7
):
    if not access_token:
        print("Ошибка: Access Token не найден!")
        return [], None

    user_agent = UserAgent().random
    headers_template = {
        "User-Agent": user_agent,
        "Accept": ';q=1;depth=1;scopes={"user":{"fields":"id,name,url,image,reviews_count,sex"},"official_answer":{},"photos":{}};application/json',
    }

    url = f"{reviews_api_url}&offset_id={offset_id}" if offset_id else reviews_api_url

    # Попытки выполнения с задержкой
    for attempt in range(retries):
        headers = headers_template.copy()
        headers["Authorization"] = f"Bearer {access_token}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 401:
                        print(f"401 Unauthorized, обновляю access_token... (попытка {attempt + 1})")
                        access_token = await get_access_token(access_token_url=access_token_url)
                        await asyncio.sleep(delay)
                        continue
                    if response.status != 200:
                        print(f"Ошибка запроса (попытка {attempt + 1}): {response.status}")
                        if attempt < retries - 1:
                            print(f"Попытка повторения через {delay} секунд...")
                            await asyncio.sleep(delay)
                        continue  # Переход к следующей попытке
                    data = await response.json()
                    reviews = data.get("reviews", [])
                    offset_id = reviews[-1]["id"] if reviews else None
                    return get_success_response(reviews, offset_id=offset_id)

        except Exception as e:
            print(f"Ошибка при запросе (попытка {attempt + 1}): {str(e)}")
            if attempt < retries - 1:
                print(f"Попытка повторения через {delay} секунд...")
                await asyncio.sleep(delay)

    # После завершения всех попыток
    print("Не удалось получить данные после нескольких попыток.")
    return get_error_response(500, "Не удалось получить данные после нескольких попыток.", offset_id=None)
