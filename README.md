# MoviePulse

MoviePulse is a small portfolio project that recommends recently released
movies based on a natural-language description of your taste. It uses
Gemini's Google Search grounding to find current movie information, then
asks Gemini to reason about whether each movie actually fits what you
described — not just its genre.

## Architecture

```
Streamlit (UI) --HTTP--> FastAPI (backend) --API call--> Gemini + Google Search
                                                                |
Streamlit (UI) <--HTTP-- FastAPI (backend) <-------------------+
```

Streamlit never talks to Gemini directly — all AI logic lives in FastAPI,
which is the part of this project meant to demonstrate backend development.

## Technologies

- Python 3
- FastAPI
- Pydantic
- httpx
- Streamlit
- Gemini API (`google-genai`)
- Google Search grounding

## Features

- Natural-language movie taste input (no genre dropdowns)
- Finds movies from roughly the last 7 days
- AI-generated, subjective "match" assessment with a short explanation
- IMDb / Rotten Tomatoes ratings where reliably available (never invented)
- Source links from Gemini's search grounding

## Setup

1. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create your `.env` file:
   ```bash
   cp .env.example .env
   ```

4. Add your Gemini API key to `.env`:
   ```
   GEMINI_API_KEY=your_key_here
   ```

5. Start the FastAPI backend (in one terminal, from the project root):
   ```bash
   uvicorn app.main:app --reload
   ```

6. Start the Streamlit frontend (in a second terminal, from the project root):
   ```bash
   streamlit run streamlit_app.py
   ```

7. Open the Streamlit UI, usually at:
   ```
   http://localhost:8501
   ```

## Deploy on Render

MoviePulse is live:

- **App:** [moviepulse-ui.onrender.com](https://moviepulse-ui.onrender.com)
- **API health:** [moviepulse-api-obl7.onrender.com/health](https://moviepulse-api-obl7.onrender.com/health)
- **Interactive API docs:** [moviepulse-api-obl7.onrender.com/docs](https://moviepulse-api-obl7.onrender.com/docs)

The repository includes a Render Blueprint (`render.yaml`) that creates two
web services: the FastAPI backend and the Streamlit frontend.

1. Push this repository to GitHub and create a new Blueprint in the
   [Render Dashboard](https://dashboard.render.com/).
2. Select this repository and confirm the Blueprint.
3. When prompted, enter `GEMINI_API_KEY` for the backend service. Keep this
   secret out of GitHub and do not put it in `.env.example`.
4. Wait for both services to deploy. Open the `moviepulse-ui` service URL.

The Blueprint connects the frontend to the backend automatically. The
services use Render's free plan, which may spin down when idle and take about
a minute to wake up. Free-tier Gemini quotas and Google Search grounding
availability still apply; public visitors can use the app's recommendation
endpoint, so monitor usage and billing before sharing it widely.

### API docs

FastAPI automatically generates interactive Swagger docs. While the backend
is running, visit:

```
http://localhost:8000/docs
```

## API

### `GET /health`

Returns `{"status": "ok"}` — used to confirm the backend is running.

### `POST /recommendations`

Request body:
```json
{
  "preference": "I like movies that are thrilling but not nonstop action..."
}
```

Response body:
```json
{
  "movies": [
    {
      "title": "Example Movie",
      "release_date": "2026-09-25",
      "imdb_rating": 7.4,
      "rotten_tomatoes_rating": 84,
      "overview": "...",
      "poster_url": null,
      "match": "Likely a good match",
      "insight": "...",
      "sources": ["https://..."]
    }
  ]
}
```

## Example request

```bash
curl -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{"preference": "I like weird, unpredictable movies with dark humor. Some horror is fine, but not extremely scary."}'
```

## How it works

1. You type your taste into the Streamlit text area and click "Find Movies".
2. Streamlit sends a `POST /recommendations` request to FastAPI over HTTP.
3. FastAPI validates the request body with a Pydantic model.
4. FastAPI calls Gemini with Google Search grounding enabled, asking it to
   find movies from the last ~7 days and compare them to your preference.
5. Gemini searches the web, reasons about each movie, and returns structured
   JSON text plus grounding metadata (source URLs).
6. FastAPI parses that JSON into Pydantic models and returns it as the API
   response.
7. Streamlit renders each movie: poster (if any), title, ratings, synopsis,
   match verdict, AI explanation, and sources.

## V1 scope

Intentionally excluded to keep the project small and readable:
no database, no separate movie API, no Redis, no Docker, no authentication,
no background workers, no vector database/embeddings, no ML recommendation
model. Everything is recomputed live on each request.
