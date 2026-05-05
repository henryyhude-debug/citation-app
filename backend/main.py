from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import re
from urllib.parse import quote
from sentence_transformers import SentenceTransformer, util

app = FastAPI()
model = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://citation-app-plum.vercel.app",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_model():
    global model
    if model is None:
        model = SentenceTransformer("all-MiniLM-L6-v2")
    return model

class CitationRequest(BaseModel):
    sentence: str
    start_year: int
    end_year: int
    style: str = "APA"

STOPWORDS = {
    "the", "and", "that", "this", "with", "from", "for", "which",
    "have", "has", "were", "been", "what", "when", "then",
    "them", "they", "their", "these", "those", "about", "into",
    "would", "could", "should", "your", "there", "where", "also",
    "between", "other", "using", "used", "than", "each",
    "some", "many", "most", "more", "over", "such", "like", "while",
    "after", "before", "because", "through", "during", "within",
    "without", "under", "above", "per", "our", "own", "both",
    "may", "just", "only", "still", "even", "very"
}


def normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", " ", str(text).lower())


def extract_keywords(sentence: str, limit: int = 10) -> list[str]:
    tokens = re.findall(r"[a-z0-9']+", sentence.lower())
    keywords = []
    for token in tokens:
        if len(token) > 3 and token not in STOPWORDS and token not in keywords:
            keywords.append(token)
        if len(keywords) >= limit:
            break
    return keywords


def build_openalex_query(keywords: list[str]) -> str:
    return quote(" ".join(keywords)) if keywords else ""


def get_abstract(abstract_index) -> str:
    if not isinstance(abstract_index, dict):
        return "No abstract available."

    words = []
    for word, positions in abstract_index.items():
        if isinstance(positions, list):
            for position in positions:
                words.append((position, word))

    words.sort()
    return " ".join(word for _, word in words) if words else "No abstract available."


def format_authors(authorships: list[dict]) -> str:
    names = []
    for item in authorships:
        name = item.get("author", {}).get("display_name", "").strip()
        if name:
            names.append(name)

    if not names:
        return "Unknown"
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} & {names[1]}"
    return f"{names[0]} et al."


def format_reference(work: dict, style: str = "APA") -> str:
    title = work.get("display_name", "No title")
    year = work.get("publication_year")
    authors = format_authors(work.get("authorships", []))
    journal = work.get("host_venue", {}).get("display_name", "")
    doi = work.get("doi", "")
    doi_link = f"https://doi.org/{doi}" if doi else work.get("id", "")

    if style.upper() == "APA":
        parts = [authors, f"({year})." if year else "(n.d.).", f"{title}."]
        if journal:
            parts.append(f"{journal}.")
        if doi_link:
            parts.append(doi_link)
        return " ".join(part for part in parts if part)

    return f"{authors} ({year}). {title}. {journal}. {doi_link}"


def get_match_info(sentence: str, work: dict, keywords: list[str]) -> dict:
    document = " ".join(
        [
            work.get("display_name", ""),
            get_abstract(work.get("abstract_inverted_index")),
            work.get("host_venue", {}).get("display_name", ""),
        ]
    )
    normalized = normalize_text(document)
    matched = []
    for keyword in keywords:
        if re.search(rf"\b{re.escape(keyword)}\b", normalized):
            matched.append(keyword)
    return {
        "matched_keywords": matched,
        "exact_match_count": len(matched),
    }


def rank_works(sentence: str, works: list[dict], keywords: list[str]) -> list[dict]:
    if not works:
        return []

    texts = []
    for work in works:
        abstract = get_abstract(work.get("abstract_inverted_index"))
        texts.append(f"{work.get('display_name', '')} {abstract}")

    try:
        model = load_model()
        embeddings = model.encode([sentence] + texts, convert_to_tensor=True)
        user_embedding = embeddings[0]
        work_embeddings = embeddings[1:]
        similarities = util.cos_sim(user_embedding, work_embeddings)[0]
    except Exception:
        similarities = [0.0] * len(works)

    scored = []
    for i, work in enumerate(works):
        score = float(similarities[i]) if i < len(similarities) else 0.0
        work["similarity_score"] = score
        match_info = get_match_info(sentence, work, keywords)
        work.update(match_info)
        work["match_strength"] = work["exact_match_count"] * 10 + score
        scored.append(work)

    scored.sort(key=lambda w: (w["match_strength"], w["similarity_score"]), reverse=True)
    return scored


@app.get("/")
def home():
    return {"message": "Citation app backend is working"}


@app.post("/generate-citation")
def generate_citation(request: CitationRequest):
    sentence = request.sentence.strip()
    if not sentence:
        return {"original_sentence": "", "year_range": "", "search_keywords": [], "results": []}

    start_year = request.start_year
    end_year = request.end_year
    style = request.style or "APA"

    keywords = extract_keywords(sentence)
    query = build_openalex_query(keywords) or quote(sentence)

    url = (
        f"https://api.openalex.org/works?search={query}"
        f"&filter=from_publication_date:{start_year}-01-01,"
        f"to_publication_date:{end_year}-12-31"
        "&sort=relevance_score:desc"
        "&per-page=15"
    )

    response = requests.get(url, timeout=20)
    response.raise_for_status()
    data = response.json()

    works = data.get("results", [])
    works = rank_works(sentence, works, keywords)

    results = []
    for work in works:
        year = work.get("publication_year")
        author_text = format_authors(work.get("authorships", []))
        citation = f"({author_text}, {year})" if year else f"({author_text})"
        reference = format_reference(work, style=style)
        link = f"https://doi.org/{work.get('doi')}" if work.get('doi') else work.get('id', "")

        results.append({
            "title": work.get("display_name", "No title"),
            "year": year or "n.d.",
            "authors": author_text,
            "citation": citation,
            "reference": reference,
            "sentence_with_citation": f"{sentence} {citation}",
            "link": link,
            "cited_by_count": work.get("cited_by_count", 0),
            "similarity_score": round(work.get("similarity_score", 0), 3),
            "abstract": get_abstract(work.get("abstract_inverted_index")),
            "matched_keywords": work.get("matched_keywords", []),
            "exact_match_count": work.get("exact_match_count", 0),
        })

    return {
        "original_sentence": sentence,
        "year_range": f"{start_year}-{end_year}",
        "search_keywords": keywords,
        "results": results,
    }
