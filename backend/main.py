from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from urllib.parse import quote

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CitationRequest(BaseModel):
    sentence: str
    start_year: int
    end_year: int
    style: str = "APA"

def format_authors(authorships):
    authors = []

    for item in authorships:
        name = item.get("author", {}).get("display_name", "")
        if name:
            surname = name.split()[-1]
            authors.append(surname)

    if len(authors) == 0:
        return "Unknown"
    elif len(authors) == 1:
        return authors[0]
    elif len(authors) == 2:
        return f"{authors[0]} & {authors[1]}"
    else:
        return f"{authors[0]} et al."

def get_abstract(abstract_index):
    if not abstract_index:
        return "No abstract available."

    words = []

    for word, positions in abstract_index.items():
        for position in positions:
            words.append((position, word))

    words.sort()
    return " ".join([word for position, word in words])

@app.get("/")
def home():
    return {"message": "Citation app backend is working"}

@app.post("/generate-citation")
def generate_citation(request: CitationRequest):
    sentence = request.sentence.strip()
    start_year = request.start_year
    end_year = request.end_year

    words = sentence.split()
    keywords = " ".join(words[:5])
    encoded_sentence = quote(keywords)

    url = (
        f"https://api.openalex.org/works?search={encoded_sentence}"
        f"&filter=from_publication_date:{start_year}-01-01,"
        f"to_publication_date:{end_year}-12-31"
        "&sort=relevance_score:desc"
        "&per-page=5"
    )

    response = requests.get(url, timeout=20)
    data = response.json()

    works = data.get("results", [])
    results = []

    for work in works:
        title = work.get("display_name", "No title")
        year = work.get("publication_year", "n.d.")
        authorships = work.get("authorships", [])

        author_text = format_authors(authorships)
        citation = f"({author_text}, {year})"

        doi = work.get("doi", "")
        link = doi if doi else work.get("id", "")

        abstract = get_abstract(work.get("abstract_inverted_index"))

        results.append({
            "title": title,
            "year": year,
            "authors": author_text,
            "citation": citation,
            "sentence_with_citation": f"{sentence} {citation}",
            "link": link,
            "cited_by_count": work.get("cited_by_count", 0),
            "abstract": abstract
        })

    return {
        "original_sentence": sentence,
        "year_range": f"{start_year}-{end_year}",
        "results": results
    }