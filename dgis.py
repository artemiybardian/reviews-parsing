from fastapi import APIRouter
from config import DGIS_API, DGIS_API_KEY, REVIEWS_LIMIT
from schemas import ReviewListSchema
from responses import get_error_response, get_success_response
import aiohttp
import asyncio

router = APIRouter()


@router.get("/parse_reviews/2gis/")
async def parse_reviews(filial_id: int):
    filial_id_str = str(filial_id)
    URL = f"https://public-api.reviews.2gis.com/2.0/branches/{filial_id}/reviews"

    async def fetch_reviews(offset=50, delay=7):
        params = {"limit": REVIEWS_LIMIT, "offset": offset, "key": DGIS_API_KEY}

        async with aiohttp.ClientSession() as session:
            async with session.get(URL, params=params) as response:
                if response.status != 200:
                    print(await response.json())
                    return get_error_response(response.status, "Ошибка запроса к 2ГИС", filial_id=filial_id_str)

                data = await response.json()

                if not data.get("reviews"):
                    print("Отзывов больше нет, парсинг завершен")
                    return

                if not await save_reviews_to_storage(get_success_response(data["reviews"], filial_id=filial_id_str)):
                    print("Парсинг завершен, микросервис вернул false")
                    return

                print(f"Партия из {len(data['reviews'])} отзывов успешно отправлена в микросервис.")
                print("Завершена часть парсинга")

                await asyncio.sleep(delay)

                await fetch_reviews(offset + REVIEWS_LIMIT)

    await fetch_reviews()
    print("Парсинг завершен успешно")
    return {"message": "Парсинг завершён успешно."}


async def save_reviews_to_storage(reviews: ReviewListSchema):
    async with aiohttp.ClientSession() as session:
        async with session.post(DGIS_API, json=reviews) as response:
            if response.status != 200:
                return False
            return (await response.json()).get("result", False)
