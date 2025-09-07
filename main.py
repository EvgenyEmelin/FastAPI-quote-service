import asyncio
import logging

from fastapi import FastAPI, HTTPException, Form
from pydantic import BaseModel, Field
from database import database
from models import Quote, Source
from sqlalchemy import select, func
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.staticfiles import StaticFiles

import random

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

class QuoteCreate(BaseModel):
    text: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    weight: float = Field(default=1.0)


@app.on_event("startup")
async def startup():
    retries = 5
    for attempt in range(retries):
        try:
            await database.connect()
            logging.info("Connected to database")
            break
        except Exception as e:
            logging.warning(f"Database connection failed (attempt {attempt + 1}/{retries}): {e}")
            await asyncio.sleep(3)
    else:
        raise RuntimeError("Failed to connect to database after several attempts")


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.post("/quotes/")
async def create_quote(
    text: str = Form(...),
    source_name: str = Form(...),
    weight: float = Form(1.0),
):
    # Поиск источника
    query_source = select(Source).where(Source.name == source_name)
    source = await database.fetch_one(query_source)

    if not source:
        # Создаем источник
        query_insert_source = Source.__table__.insert().values(name=source_name)
        source_id = await database.execute(query_insert_source)
    else:
        source_id = source["id"]

    # Проверка лимита цитат у источника
    query_count = select(func.count()).select_from(Quote).where(Quote.source_id == source_id)
    count = await database.fetch_val(query_count)
    if count >= 3:
        raise HTTPException(status_code=400, detail="Источник включает в себя макс 3 цитаты")

    # Проверка дубликата по тексту цитаты
    query_dup = select(Quote).where(Quote.text == text)
    dup = await database.fetch_one(query_dup)
    if dup:
        raise HTTPException(status_code=400, detail="Дублированная цитата")

    # Добавление цитаты
    query_insert = Quote.__table__.insert().values(
        text=text,
        source_id=source_id,
        weight=weight,
        views=0,
        likes=0,
        dislikes=0,
    )
    quote_id = await database.execute(query_insert)
    return {"id": quote_id, "message": "Цитата успешно добавлена"}


@app.get("/quotes/random")
async def get_random_quote():
    query = select(Quote)
    quotes = await database.fetch_all(query)
    if not quotes:
        raise HTTPException(status_code=404, detail="Еще нет цитат")

    weights = [q["weight"] for q in quotes]
    chosen = random.choices(quotes, weights=weights, k=1)[0]

    # Увеличиваем счетчик просмотров
    query_update = Quote.__table__.update().where(Quote.id == chosen["id"]).values(views=chosen["views"] + 1)
    await database.execute(query_update)

    # Возвращаем данные цитаты
    return {
        "id": chosen["id"],
        "text": chosen["text"],
        "source_id": chosen["source_id"],
        "weight": chosen["weight"],
        "views": chosen["views"] + 1,
        "likes": chosen["likes"],
        "dislikes": chosen["dislikes"],
    }


@app.post("/quotes/{quote_id}/like")
async def like_quote(quote_id: int):
    query = select(Quote).where(Quote.id == quote_id)
    quote = await database.fetch_one(query)
    if not quote:
        raise HTTPException(status_code=404, detail="Цитата не найдена")

    query_update = Quote.__table__.update().where(Quote.id == quote_id).values(likes=quote["likes"] + 1)
    await database.execute(query_update)
    return {"message": "Liked"}


@app.post("/quotes/{quote_id}/dislike")
async def dislike_quote(quote_id: int):
    query = select(Quote).where(Quote.id == quote_id)
    quote = await database.fetch_one(query)
    if not quote:
        raise HTTPException(status_code=404, detail="Цитата не найдена")

    query_update = Quote.__table__.update().where(Quote.id == quote_id).values(dislikes=quote["dislikes"] + 1)
    await database.execute(query_update)
    return {"message": "Disliked"}


@app.get("/quotes/top")
async def top_quotes():
    query = select(Quote).order_by(Quote.likes.desc()).limit(10)
    quotes = await database.fetch_all(query)
    return quotes

@app.get("/")
async def read_random_quote(request: Request):
    query = select(Quote)
    quotes = await database.fetch_all(query)
    if not quotes:
        quote = None
    else:
        import random
        weights = [q["weight"] for q in quotes]
        quote = random.choices(quotes, weights=weights, k=1)[0]
        # Обновляем просмотры (можно в фоне)
        query_update = Quote.__table__.update().where(Quote.id == quote["id"]).values(views=quote["views"] + 1)
        await database.execute(query_update)

    return templates.TemplateResponse("index.html", {"request": request, "quote": quote})


@app.get("/add")
async def add_quote_form(request: Request):
    return templates.TemplateResponse("add_quote.html", {"request": request})


@app.get("/top")
async def top_quotes_page(request: Request):
    query = select(Quote).order_by(Quote.likes.desc()).limit(10)
    quotes = await database.fetch_all(query)
    return templates.TemplateResponse("top.html", {"request": request, "quotes": quotes})