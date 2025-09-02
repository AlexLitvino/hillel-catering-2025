import time
from typing import Literal
import asyncio
import random
import uuid

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel


STORAGE: dict[str, dict] = {}


app = FastAPI(title="Silpo API")
OrderStatus = Literal["not started", "cooking", "cooked", "finished"]


class OrderItem(BaseModel):
    dish: str
    quantity: int


class OrderRequestBody(BaseModel):
    order: list[OrderItem]


async def update_order_status(order_id: str):
    ORDER_STATUSES: tuple[OrderStatus, ...] = ("cooking", "cooked", "finished")
    for status in ORDER_STATUSES:
        await asyncio.sleep(random.randint(1, 2))
        STORAGE[order_id] = status
        print(f"Silpo [{order_id}] -> {status}")

@app.post("/api/orders")
async def make_order(body: OrderRequestBody, background_task: BackgroundTasks):
    print(body)

    order_id = str(uuid.uuid4())
    STORAGE[order_id] = "not started"
    background_task.add_task(update_order_status, order_id)

    return {
        "id": order_id,
        "status": "not started"
    }

@app.get("/api/orders/{order_id}")
async def get_order(order_id: str):
    return {"id": order_id, "status": STORAGE.get(order_id)}
