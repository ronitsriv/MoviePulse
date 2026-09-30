"""
FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI


from app.routes.recommendations import router as recommendations_router

from dotenv import load_dotenv
load_dotenv()

app = FastAPI(
    title="MoviePulse API",
    description=(
        "Finds recent movies and compares them against your natural-language "
        "taste, using Gemini + Google Search grounding."
    ),
    version="1.0.0",
)

app.include_router(recommendations_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
