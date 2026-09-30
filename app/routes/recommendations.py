"""
The HTTP layer: translates between FastAPI requests/responses and the
gemini_service business logic. Kept thin on purpose.
"""

from fastapi import APIRouter, HTTPException

from app.models.recommendation import PreferenceRequest, RecommendationsResponse
from app.services.gemini_service import GeminiServiceError, get_recommendations

router = APIRouter()


@router.post("/recommendations", response_model=RecommendationsResponse)
async def recommendations(request: PreferenceRequest) -> RecommendationsResponse:
    preference = request.preference.strip()
    if not preference:
        raise HTTPException(status_code=400, detail="preference must not be empty.")

    try:
        return get_recommendations(preference)
    except GeminiServiceError as exc:
        # Known, expected failure modes (missing key, bad Gemini response, etc.)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # anything unexpected
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {exc}") from exc
