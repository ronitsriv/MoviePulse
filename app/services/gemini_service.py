"""
All Gemini-related logic lives here: building the prompt, calling the
API with Google Search grounding enabled, and turning the raw model
output into our Pydantic models.

Keeping this in one file (rather than spreading Gemini logic across
the app) means you can read this single file top to bottom and
understand exactly how the AI integration works.
"""

import json
import os
import re
from typing import List

from google import genai
from google.genai import types

from app.models.recommendation import Movie, RecommendationsResponse

MODEL_NAME = "gemini-2.5-flash"


class GeminiServiceError(Exception):
    """Raised when something goes wrong talking to Gemini or parsing its response."""


def _get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise GeminiServiceError(
            "GEMINI_API_KEY is not set. Add it to your .env file (see .env.example)."
        )
    return genai.Client(api_key=api_key)


def _build_prompt(preference: str) -> str:
    """
    Compose the instructions we send to Gemini. This is where we tell
    the model what to search for, what to compare, and exactly what
    JSON shape to reply with.
    """
    return f"""You are a movie-discovery assistant. A user has described the kind of
movies they enjoy, in their own words:

USER PREFERENCE:
\"\"\"{preference}\"\"\"

Your task:

1. Use Google Search to find movies that were released in approximately the
   last 7 days (current/recent theatrical or major streaming releases).
2. For each movie found, gather (only if you can find it reliably via search):
   - title
   - release_date (YYYY-MM-DD if possible)
   - a short overview/synopsis
   - imdb_rating (a number, e.g. 7.4) if available, else null
   - rotten_tomatoes_rating (an integer percentage, e.g. 84) if available, else null
   - poster_url if you can find a direct, plausible image URL, else null
   - the source URLs you used for that movie
3. Do NOT invent release dates, ratings, plot details, or sources. If a piece
   of information cannot be reliably found, use null (for numbers/URLs) or
   "N/A" (for text) instead of guessing.
4. Compare EACH movie against the user's stated preference. Do not reduce the
   preference to a simple genre keyword search — reason about the actual
   characteristics of the movie (pacing, tone, balance of action vs story,
   suspense, humor, darkness, predictability, intensity, emotional tone,
   character focus) versus what the user described. Only mention a
   characteristic if it is actually supported by what you found via search.
5. For each movie, assign a "match" value of exactly one of:
   - "Likely a good match"
   - "Maybe"
   - "Probably not"
   This is your subjective interpretation, not an objective fact. Do not tell
   the user what they "should" watch — describe how the movie relates to what
   they said and let them decide.
6. Write a 2-3 sentence "insight" for each movie that specifically connects
   the user's stated preference to the movie's actual characteristics. Do not
   just restate the genre (e.g. avoid "it's a thriller and you like thrillers").

Respond with ONLY a single JSON object (no markdown fences, no commentary
before or after it) in exactly this shape:

{{
  "movies": [
    {{
      "title": "string",
      "release_date": "string or null",
      "imdb_rating": number or null,
      "rotten_tomatoes_rating": number or null,
      "overview": "string or null",
      "poster_url": "string or null",
      "match": "Likely a good match" | "Maybe" | "Probably not",
      "insight": "string",
      "sources": ["url1", "url2"]
    }}
  ]
}}

If you cannot find any suitable recent movies, return {{"movies": []}}.
Return at most 6 movies, the most relevant ones first.
"""


def _extract_json(text: str) -> dict:
    """
    Gemini is instructed to return raw JSON, but models sometimes wrap
    output in markdown code fences anyway. Strip those defensively,
    then parse. Raise a clear error if parsing still fails.
    """
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise GeminiServiceError(f"Gemini did not return valid JSON: {exc}") from exc


def _collect_grounding_sources(response) -> List[str]:
    """
    Pull source URLs out of Gemini's grounding metadata, as a fallback
    in case the model's own JSON 'sources' field is thin. Best-effort:
    if the SDK response shape doesn't have this, just return [].
    """
    urls: List[str] = []
    try:
        candidates = response.candidates or []
        for candidate in candidates:
            metadata = getattr(candidate, "grounding_metadata", None)
            if not metadata:
                continue
            chunks = getattr(metadata, "grounding_chunks", None) or []
            for chunk in chunks:
                web = getattr(chunk, "web", None)
                if web and getattr(web, "uri", None):
                    urls.append(web.uri)
    except Exception:
        return []
    return urls


def get_recommendations(preference: str) -> RecommendationsResponse:
    """
    Main entry point used by the /recommendations route.

    Calls Gemini with Google Search grounding turned on, parses the
    JSON it returns, and converts it into our Pydantic response model.
    """
    client = _get_client()
    prompt = _build_prompt(preference)

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
    except Exception as exc:  # network errors, auth errors, etc.
        raise GeminiServiceError(f"Gemini API request failed: {exc}") from exc

    text = getattr(response, "text", None)
    if not text:
        raise GeminiServiceError("Gemini returned an empty response.")

    data = _extract_json(text)
    movies_raw = data.get("movies", [])
    if not isinstance(movies_raw, list):
        raise GeminiServiceError("Malformed Gemini response: 'movies' is not a list.")

    fallback_sources = _collect_grounding_sources(response)

    movies: List[Movie] = []
    for raw in movies_raw:
        sources = raw.get("sources") or []
        if not sources:
            sources = fallback_sources
        movies.append(
            Movie(
                title=raw.get("title", "Unknown title"),
                release_date=raw.get("release_date"),
                imdb_rating=raw.get("imdb_rating"),
                rotten_tomatoes_rating=raw.get("rotten_tomatoes_rating"),
                overview=raw.get("overview"),
                poster_url=raw.get("poster_url"),
                match=raw.get("match", "Maybe"),
                insight=raw.get("insight", ""),
                sources=sources,
            )
        )

    return RecommendationsResponse(movies=movies)
