import asyncio
import os
from fastapi import FastAPI

app = FastAPI()

DELAY = float(os.getenv("DELAY", "0"))

@app.get("/stock")
async def stock():
    if DELAY > 0:
        await asyncio.sleep(DELAY)

    return {"stock": 99}