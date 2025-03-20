from fastapi import APIRouter
from pathlib import Path
from schemas import ReviewListSchema
import random
import json
import aiofiles

router = APIRouter()


@router.post("/random_bool/")
async def random_bool(request: ReviewListSchema):

    file_path = Path("reviews_dump.json")

    # Добавление в файл по желанию, для проверки правильной работы
    async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(request.model_dump(), ensure_ascii=False, indent=4))

    return {"result": random.randint(0, 10) < 8}  # шанс 80% на true
