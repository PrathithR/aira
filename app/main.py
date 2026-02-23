# app/main.py
from fastapi import FastAPI

app = FastAPI(title="AIRA", version="0.1.0")

@app.get("/health")
async def health():
    return {"status": "ok"}