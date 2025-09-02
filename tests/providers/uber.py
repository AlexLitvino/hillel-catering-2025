import asyncio
import os
import random
import uuid

import httpx
from fastapi import BackgroundTasks, FastAPI
from pydantic import BaseModel, Field

ORDER_STATUSES = ("not started", "delivery", "delivered")
STORAGE: dict[str, dict] = {}
CATERING_API_WEBHOOK_URL = f"http://{os.getenv("API_HOST", default="localhost")}:8000/webhooks/uber/de496ba9-faf3-4d31-b1c9-1212490fa248/"


app = FastAPI()


class OrderRequestBody(BaseModel):
    addresses: list[str] = Field(min_length=1)
    comments: list[str] = Field(min_length=1)

async def send_notification(order_id, status, location):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                CATERING_API_WEBHOOK_URL,
                data={"id": order_id, "status": status, "location": list(location)},
            )
            data = {"id": order_id, "status": status, "location": list(location)}
            print(f"DATA: {data}")
        except httpx.ConnectError:
            print("API connection failed")
        else:
            print(f"UBER: {CATERING_API_WEBHOOK_URL} notified about {status}")

async def update_order_status(order_id):
    await asyncio.sleep(random.randint(1, 2))  # wait from "not started" to "delivery" status
    for status in ORDER_STATUSES[1:]:
        STORAGE[order_id]["location"] = (random.random(), random.random())
        STORAGE[order_id]["status"] = status
        print(f"UBER: [{order_id}] -> {status}")

        if status == "delivery":
            for address in STORAGE[order_id]["addresses"]:
                for _ in range(random.randint(3, 6)):  # simulate different distance
                    location = (random.random(), random.random())
                    STORAGE[order_id]["location"] = location
                    await send_notification(order_id, status, location)
                    await asyncio.sleep(1)  # change location every 1 second

                print(f"🏁 Delivered to {address}")

        if status == "delivered":
            location = (random.random(), random.random())  # set final destination
            await send_notification(order_id, status, location)


@app.post("/drivers/orders")
async def make_order(body: OrderRequestBody, background_tasks: BackgroundTasks):
    print(body)

    order_id = str(uuid.uuid4())
    STORAGE[order_id] = {
        "id": order_id,
        "status": "not started",
        "addresses": body.addresses,
        "comments": body.comments,
        "location": (random.random(), random.random())
    }
    background_tasks.add_task(update_order_status, order_id)

    return STORAGE.get(order_id, {"error": "No such order"})

@app.get("/drivers/orders/{order_id}")
async def get_order(order_id: str):
    return STORAGE.get(order_id, {"error": "No such order"})
