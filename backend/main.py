from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import re
import math
from collections import Counter
from urllib.parse import quote

app = FastAPI()

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


def get_content_tokens(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9']+", normalize_text(text))
    return [token for token in tokens if len(token) > 3 and token not in STOPWORDS]


def cosine_similarity(left: Counter, right: Counter) -> float:
    if not left or not right:
        return 0.0

    shared = set(left) & set(right)
    dot_product = sum(left[token] * right[token] for token in shared)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot_product / (left_norm * right_norm)


def lightweight_similarity(sentence: str, paper: dict, keywords: list[str]) -> float:
    query_tokens = Counter(get_content_tokens(sentence))
    paper_text = " ".join([paper.get("title", ""), paper.get("abstract", ""), paper.get("venue", "")])
    paper_tokens = Counter(get_content_tokens(paper_text))
    token_score = cosine_similarity(query_tokens, paper_tokens)

    normalized_sentence = normalize_text(sentence)
    normalized_title = normalize_text(paper.get("title", ""))
    phrase_bonus = 0.12 if normalized_sentence and normalized_sentence in normalize_text(paper_text) else 0
    title_bonus = 0.0
    if keywords:
        title_matches = sum(1 for keyword in keywords if re.search(rf"\b{re.escape(keyword)}\b", normalized_title))
        title_bonus = min(title_matches / len(keywords), 1.0) * 0.18

    return min(token_score + phrase_bonus + title_bonus, 1.0)


def build_openalex_query(keywords: list[str]) -> str:
    return quote(" ".join(keywords)) if keywords else ""


def clean_markup(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", str(text or ""))
    return re.sub(r"\s+", " ", text).strip()


def normalize_doi(doi: str) -> str:
    doi = str(doi or "").strip().lower()
    doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
    doi = doi.replace("doi:", "").strip()
    return doi


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", normalize_text(title)).strip()


def get_source_from_openalex(work: dict) -> str:
    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}
    return (
        source.get("display_name")
        or work.get("host_venue", {}).get("display_name", "")
        or ""
    )


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


def get_year_from_crossref_date(date_parts: dict) -> int | None:
    parts = (date_parts or {}).get("date-parts") or []
    if parts and parts[0]:
        return parts[0][0]
    return None


def get_crossref_authors(authors: list[dict]) -> list[str]:
    names = []
    for author in authors or []:
        given = author.get("given", "")
        family = author.get("family", "")
        name = " ".join(part for part in [given, family] if part).strip()
        if name:
            names.append(name)
    return names


def get_openalex_authors(authorships: list[dict]) -> list[str]:
    names = []
    for item in authorships:
        name = item.get("author", {}).get("display_name", "").strip()
        if name:
            names.append(name)
    return names


def format_author_list(names: list[str]) -> str:
    if not names:
        return "Unknown"
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} & {names[1]}"
    return f"{names[0]} et al."


def format_authors(authorships: list[dict]) -> str:
    return format_author_list(get_openalex_authors(authorships))


def apa_author_name(name: str) -> str:
    parts = [part for part in re.split(r"\s+", name.strip()) if part]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    family = parts[-1]
    initials = " ".join(f"{part[0].upper()}." for part in parts[:-1] if part)
    return f"{family}, {initials}".strip()


def format_apa_authors(names: list[str]) -> str:
    formatted = [apa_author_name(name) for name in names if apa_author_name(name)]
    if not formatted:
        return "Unknown"
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) <= 20:
        return f"{', '.join(formatted[:-1])}, & {formatted[-1]}"
    return f"{', '.join(formatted[:19])}, ... {formatted[-1]}"


def format_apa_reference(paper: dict) -> str:
    authors = format_apa_authors(paper.get("authors", []))
    year = paper.get("year") or "n.d."
    title = clean_markup(paper.get("title") or "No title").rstrip(".")
    venue = clean_markup(paper.get("venue") or "").rstrip(".")
    doi = normalize_doi(paper.get("doi"))
    link = f"https://doi.org/{doi}" if doi else paper.get("url", "")

    parts = [f"{authors} ({year}).", f"{title}."]
    if venue:
        parts.append(f"{venue}.")
    if link:
        parts.append(link)
    return " ".join(parts)


def normalize_openalex_work(work: dict) -> dict:
    doi = normalize_doi(work.get("doi"))
    url = f"https://doi.org/{doi}" if doi else work.get("id", "")
    return {
        "title": work.get("display_name", "No title"),
        "year": work.get("publication_year"),
        "authors": get_openalex_authors(work.get("authorships", [])),
        "venue": get_source_from_openalex(work),
        "doi": doi,
        "url": url,
        "abstract": get_abstract(work.get("abstract_inverted_index")),
        "cited_by_count": work.get("cited_by_count", 0),
        "sources": ["OpenAlex"],
    }


def normalize_semantic_scholar_paper(paper: dict) -> dict:
    external_ids = paper.get("externalIds") or {}
    doi = normalize_doi(external_ids.get("DOI"))
    url = f"https://doi.org/{doi}" if doi else paper.get("url", "")
    return {
        "title": paper.get("title", "No title"),
        "year": paper.get("year"),
        "authors": [author.get("name", "") for author in paper.get("authors", []) if author.get("name")],
        "venue": paper.get("venue", ""),
        "doi": doi,
        "url": url,
        "abstract": paper.get("abstract") or "No abstract available.",
        "cited_by_count": paper.get("citationCount", 0),
        "sources": ["Semantic Scholar"],
    }


def normalize_crossref_work(work: dict) -> dict:
    title = (work.get("title") or ["No title"])[0]
    venue = (work.get("container-title") or [""])[0]
    doi = normalize_doi(work.get("DOI"))
    year = (
        get_year_from_crossref_date(work.get("published-print"))
        or get_year_from_crossref_date(work.get("published-online"))
        or get_year_from_crossref_date(work.get("published"))
        or get_year_from_crossref_date(work.get("issued"))
    )
    return {
        "title": clean_markup(title),
        "year": year,
        "authors": get_crossref_authors(work.get("author", [])),
        "venue": clean_markup(venue),
        "doi": doi,
        "url": f"https://doi.org/{doi}" if doi else work.get("URL", ""),
        "abstract": clean_markup(work.get("abstract")) or "No abstract available.",
        "cited_by_count": work.get("is-referenced-by-count", 0),
        "sources": ["Crossref"],
    }


def get_match_info(sentence: str, paper: dict, keywords: list[str]) -> dict:
    document = " ".join(
        [
            paper.get("title", ""),
            paper.get("abstract", ""),
            paper.get("venue", ""),
        ]
    )
    normalized = normalize_text(document)
    normalized_title = normalize_text(paper.get("title", ""))
    matched = []
    title_matches = []
    for keyword in keywords:
        if re.search(rf"\b{re.escape(keyword)}\b", normalized):
            matched.append(keyword)
        if re.search(rf"\b{re.escape(keyword)}\b", normalized_title):
            title_matches.append(keyword)
    return {
        "matched_keywords": matched,
        "title_keyword_matches": title_matches,
        "exact_match_count": len(matched),
        "title_overlap_count": len(title_matches),
        "keyword_overlap_score": round(len(matched) / len(keywords), 3) if keywords else 0,
    }


def dedupe_papers(papers: list[dict]) -> list[dict]:
    deduped = {}
    for paper in papers:
        title_key = normalize_title(paper.get("title", ""))
        if not title_key:
            continue
        key = f"doi:{paper['doi']}" if paper.get("doi") else f"title:{title_key}:{paper.get('year') or ''}"
        existing = deduped.get(key)
        if not existing:
            deduped[key] = paper
            continue

        existing_sources = set(existing.get("sources", []))
        existing_sources.update(paper.get("sources", []))
        existing["sources"] = sorted(existing_sources)
        if existing.get("abstract") == "No abstract available." and paper.get("abstract") != "No abstract available.":
            existing["abstract"] = paper.get("abstract")
        if not existing.get("doi") and paper.get("doi"):
            existing["doi"] = paper.get("doi")
            existing["url"] = paper.get("url")
        if len(paper.get("authors", [])) > len(existing.get("authors", [])):
            existing["authors"] = paper.get("authors", [])
        existing["cited_by_count"] = max(existing.get("cited_by_count", 0), paper.get("cited_by_count", 0))
    return list(deduped.values())


def rank_papers(sentence: str, papers: list[dict], keywords: list[str]) -> list[dict]:
    if not papers:
        return []

    scored = []
    for paper in papers:
        score = lightweight_similarity(sentence, paper, keywords)
        paper["similarity_score"] = score
        match_info = get_match_info(sentence, paper, keywords)
        paper.update(match_info)
        paper["final_score"] = (0.6 * score) + (0.4 * paper["keyword_overlap_score"])
        paper["ranking_score"] = paper["final_score"]
        if score >= 0.45:
            scored.append(paper)

    scored.sort(key=lambda item: (item["ranking_score"], item["similarity_score"]), reverse=True)
    return scored


def get_similarity_label(score: float) -> str:
    if score >= 0.60:
        return "Very strong"
    if score >= 0.45:
        return "Acceptable"
    return "Weak"


def search_openalex(query: str, start_year: int, end_year: int) -> list[dict]:
    url = (
        f"https://api.openalex.org/works?search={quote(query)}"
        f"&filter=from_publication_date:{start_year}-01-01,"
        f"to_publication_date:{end_year}-12-31"
        "&sort=relevance_score:desc"
        "&per-page=10"
    )
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return [normalize_openalex_work(work) for work in response.json().get("results", [])]


def search_semantic_scholar(query: str, start_year: int, end_year: int) -> list[dict]:
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": 10,
        "year": f"{start_year}-{end_year}",
        "fields": "title,year,abstract,authors,venue,citationCount,externalIds,url",
    }
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    return [normalize_semantic_scholar_paper(paper) for paper in response.json().get("data", [])]


def search_crossref(query: str, start_year: int, end_year: int) -> list[dict]:
    url = "https://api.crossref.org/works"
    params = {
        "query.bibliographic": query,
        "filter": f"from-pub-date:{start_year}-01-01,until-pub-date:{end_year}-12-31",
        "rows": 10,
        "select": "DOI,title,author,container-title,published,published-print,published-online,issued,abstract,is-referenced-by-count,URL",
    }
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    return [normalize_crossref_work(work) for work in response.json().get("message", {}).get("items", [])]


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

    keywords = extract_keywords(sentence)
    query = " ".join(keywords) if keywords else sentence

    papers = []
    search_errors = {}
    searchers = {
        "OpenAlex": search_openalex,
        "Semantic Scholar": search_semantic_scholar,
        "Crossref": search_crossref,
    }

    for source, searcher in searchers.items():
        try:
            papers.extend(searcher(query, start_year, end_year))
        except requests.RequestException as error:
            search_errors[source] = str(error)

    unique_papers = dedupe_papers(papers)
    ranked_papers = rank_papers(sentence, unique_papers, keywords)

    results = []
    for paper in ranked_papers:
        year = paper.get("year")
        author_text = format_author_list(paper.get("authors", []))
        citation = f"({author_text}, {year})" if year else f"({author_text})"

        results.append({
            "title": paper.get("title", "No title"),
            "year": year or "n.d.",
            "authors": author_text,
            "citation": citation,
            "reference": format_apa_reference(paper),
            "sentence_with_citation": f"{sentence} {citation}",
            "link": paper.get("url", ""),
            "doi": paper.get("doi", ""),
            "venue": paper.get("venue", ""),
            "sources": paper.get("sources", []),
            "cited_by_count": paper.get("cited_by_count", 0),
            "similarity_score": round(paper.get("similarity_score", 0), 3),
            "similarity_label": get_similarity_label(paper.get("similarity_score", 0)),
            "final_score": round(paper.get("final_score", 0), 3),
            "ranking_score": round(paper.get("ranking_score", 0), 3),
            "abstract": paper.get("abstract", "No abstract available."),
            "matched_keywords": paper.get("matched_keywords", []),
            "title_keyword_matches": paper.get("title_keyword_matches", []),
            "exact_match_count": paper.get("exact_match_count", 0),
            "title_overlap_count": paper.get("title_overlap_count", 0),
            "keyword_overlap_score": paper.get("keyword_overlap_score", 0),
        })

    return {
        "original_sentence": sentence,
        "year_range": f"{start_year}-{end_year}",
        "search_keywords": keywords,
        "minimum_similarity_score": 0.45,
        "searched_sources": list(searchers.keys()),
        "source_errors": search_errors,
        "total_before_dedupe": len(papers),
        "total_after_dedupe": len(unique_papers),
        "results": results,
    }
