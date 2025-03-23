from fastapi import FastAPI
from flamp_parser import router as flamp_router
from api import router as api_router
from dgis import router as dgis_router
from yandex import router as yandex_router

app = FastAPI()
app.include_router(flamp_router)
app.include_router(api_router)
app.include_router(dgis_router)
app.include_router(yandex_router)
