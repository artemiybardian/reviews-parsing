from fastapi import APIRouter, HTTPException
from pathlib import Path
from config import DGIS_API, DGIS_API_KEY, REVIEWS_LIMIT
from schemas import ReviewListSchema
from responses import get_error_response, get_success_response
import aiohttp
import asyncio
import aiofiles
import json

router = APIRouter()


@router.get("/parse_reviews/2gis/")
async def parse_reviews(filial_id: int):
    try:
        filial_id_str = str(filial_id)
        URL = f"https://public-api.reviews.2gis.com/2.0/branches/{filial_id}/reviews"

        async def fetch_reviews(offset=50, delay=7):
            try:
                params = {"limit": REVIEWS_LIMIT, "offset": offset, "key": DGIS_API_KEY}

                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.get(URL, params=params) as response:
                            if response.status != 200:
                                error_data = await response.json()
                                print(f"Ошибка API 2ГИС: {error_data}")
                                raise HTTPException(response.status, error_data)

                            data = await response.json()

                            if not data.get("reviews"):
                                print("Отзывов больше нет, парсинг завершен")
                                return

                            reviews_json = get_success_response(data["reviews"], filial_id=filial_id_str)

                            # file_path = Path("reviews_json.json")

                            # Добавление в файл по желанию, для проверки правильной работы
                            # async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                            #     await f.write(json.dumps(reviews_json, ensure_ascii=False, indent=4))

                            try:
                                continue_parsing = await save_reviews_to_storage(reviews_json)
                                if not continue_parsing:
                                    print("Парсинг завершен, микросервис вернул false")
                                    return
                            except Exception as e:
                                print(f"Ошибка при сохранении отзывов: {str(e)}")
                                raise HTTPException(500, str(e))

                            print(f"Партия из {len(data['reviews'])} отзывов успешно отправлена в микросервис.")
                            print("Завершена часть парсинга")

                            await asyncio.sleep(delay)

                            await fetch_reviews(offset + REVIEWS_LIMIT)
                    except aiohttp.ClientError as e:
                        print(f"Ошибка HTTP запроса: {str(e)}")
                        raise HTTPException(500, str(e))
            except Exception as e:
                print(f"Неожиданная ошибка в fetch_reviews: {str(e)}")
                return get_error_response(500, "Внутренняя ошибка сервера", filial_id=filial_id_str)

        await fetch_reviews()
        print("Парсинг завершен успешно")
        return {"status": "success", "error": None, "message": "Парсинг завершён успешно."}

    except HTTPException as e:
        return get_error_response(e.status_code, e.detail, filial_id=str(filial_id))

    except Exception as e:
        print(f"Критическая ошибка: {str(e)}")
        return get_error_response(500, "Критическая ошибка сервера", filial_id=str(filial_id))


async def save_reviews_to_storage(reviews: ReviewListSchema):
    async with aiohttp.ClientSession() as session:
        async with session.post(DGIS_API, json=reviews) as response:
            if response.status != 200:
                return False
            return (await response.json()).get("result", False)
