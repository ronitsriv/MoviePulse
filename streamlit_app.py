"""
MoviePulse frontend.

Deliberately simple: a text area, a button, and a results list. All
the real work (talking to Gemini, doing the analysis) happens in the
FastAPI backend. This file's only job is to call that backend over
HTTP and render what comes back.
"""

import os

import httpx
import streamlit as st

FASTAPI_URL = os.environ.get("FASTAPI_URL", "http://localhost:8000")

st.set_page_config(page_title="MoviePulse", page_icon="🎬")

st.title("🎬 MoviePulse")
st.write("What kind of movie you are in the mood to watch?")

preference = st.text_area(
    "Your movie taste",
    placeholder="I like movies that are thrilling but not nonstop action...",
    height=120,
    label_visibility="collapsed",
)

find_clicked = st.button("Find Movies", type="primary")

if find_clicked:
    if not preference.strip():
        st.warning("Please describe what kind of movies you enjoy first.")
    else:
        with st.spinner("Searching for recent movies and comparing them to your taste..."):
            data = None
            try:
                resp = httpx.post(
                    f"{FASTAPI_URL}/recommendations",
                    json={"preference": preference},
                    timeout=90.0,
                )
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as exc:
                try:
                    detail = exc.response.json().get("detail", str(exc))
                except Exception:
                    detail = str(exc)
                st.error(f"Backend error: {detail}")
            except httpx.RequestError as exc:
                st.error(f"Could not reach the FastAPI backend at {FASTAPI_URL}. Is it running? ({exc})")

        if data is not None:
            movies = data.get("movies", [])
            if not movies:
                st.info("No recent movies found for this preference. Try rephrasing it.")
            else:
                st.subheader(f"Found {len(movies)} movie(s)")
                for movie in movies:
                    st.divider()

                    if movie.get("poster_url"):
                        poster_col, content_col = st.columns([1, 3])
                        with poster_col:
                            try:
                                st.image(movie["poster_url"], use_container_width=True)
                            except Exception:
                                pass
                    else:
                        content_col = st.container()

                    with content_col:
                        st.markdown(f"### {movie.get('title', 'Unknown title')}")

                        meta_bits = []
                        if movie.get("release_date"):
                            meta_bits.append(f"📅 {movie['release_date']}")
                        if movie.get("imdb_rating") is not None:
                            meta_bits.append(f"⭐ IMDb {movie['imdb_rating']}")
                        if movie.get("rotten_tomatoes_rating") is not None:
                            meta_bits.append(f"🍅 {movie['rotten_tomatoes_rating']}%")
                        if meta_bits:
                            st.caption(" | ".join(meta_bits))

                        if movie.get("overview"):
                            st.write(movie["overview"])

                        match = movie.get("match", "Maybe")
                        match_emoji = {
                            "Likely a good match": "✅",
                            "Maybe": "🤔",
                            "Probably not": "❌",
                        }.get(match, "🤔")
                        st.markdown(f"**{match_emoji} {match}**")
                        st.write(movie.get("insight", ""))

                        sources = movie.get("sources") or []
                        if sources:
                            with st.expander("Sources"):
                                for src in sources:
                                    st.markdown(f"- {src}")
