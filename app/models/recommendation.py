"""
Pydantic models for the /recommendations endpoint.

These define the exact "shape" of data going in (the request) and
coming out (the response) of the API. FastAPI uses these models to:
  - validate incoming JSON automatically
  - generate the Swagger/OpenAPI docs
  - serialize the response back to JSON
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class PreferenceRequest(BaseModel):
    """What the client (Streamlit) sends us."""

    preference: str = Field(
        ...,
        min_length=1,
        description="Natural-language description of the kind of movies the user enjoys.",
        examples=[
            "I like movies that are thrilling but not nonstop action. "
            "I enjoy a good story and don't want something that takes forever to get going."
        ],
    )


class Movie(BaseModel):
    """A single recommended movie plus the AI's subjective take on it."""

    title: str
    release_date: Optional[str] = None
    imdb_rating: Optional[float] = None
    rotten_tomatoes_rating: Optional[int] = None
    overview: Optional[str] = None
    poster_url: Optional[str] = None
    match: str = Field(
        description='One of: "Likely a good match", "Maybe", "Probably not"'
    )
    insight: str = Field(
        description="2-3 sentence explanation connecting the user's stated preference to the movie's actual characteristics."
    )
    sources: List[str] = Field(default_factory=list)


class RecommendationsResponse(BaseModel):
    """What we send back to Streamlit."""

    movies: List[Movie]
