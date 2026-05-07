import os
import time
import asyncio
import httpx
from fastapi import FastAPI

app = FastAPI()

B_URL = os.getenv("B_URL", "http://service-b:8081")

@app.get("/order")
async def order():
    start = time.time()

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                response = await client.get(f"{B_URL}/stock")

            return {
                "status": "ok",
                "attempts": attempt + 1,
                "stock_response": response.json(),
                "latency_ms": round((time.time() - start) * 1000)
            }

        except httpx.TimeoutException:
            if attempt == 2:
                return {
                    "status": "error",
                    "reason": "timeout after 3 attempts",
                    "attempts": 3,
                    "latency_ms": round((time.time() - start) * 1000)
                }

            await asyncio.sleep(0.1 * (2 ** attempt))