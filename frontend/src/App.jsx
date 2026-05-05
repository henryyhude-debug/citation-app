import { useState } from "react";
import "./App.css";

function App() {
  const [page, setPage] = useState("welcome");
  const [sentence, setSentence] = useState("");
  const [startYear, setStartYear] = useState(2019);
  const [endYear, setEndYear] = useState(2026);
  const [citationStyle, setCitationStyle] = useState("APA");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const email = "Statedgeconsult@gmail.com";
  const phone = "+233 558086317";
  const backendUrl = import.meta.env.VITE_BACKEND_URL || "https://statedge-citation-app.onrender.com";

  const generateCitation = async () => {
    if (!sentence.trim()) {
      alert("Please enter a sentence first.");
      return;
    }

    setLoading(true);
    setResults([]);

    try {
      const response = await fetch(
        `${backendUrl}/generate-citation`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            sentence: sentence,
            start_year: Number(startYear),
            end_year: Number(endYear),
            style: citationStyle,
          })
        }
      );

      const data = await response.json();
      setResults(data.results || []);
    } catch (error) {
      console.error(error);
      alert("Error connecting to backend.");
    }

    setLoading(false);
  };

  if (page === "welcome") {
    return (
      <div className="app-page">
        <div className="welcome-card">
          <img src="/logo.png" alt="Logo" className="logo" />

          <h1 className="title">Welcome to StatEdge Consult</h1>

          <p className="subtitle">
            Your smart academic support platform for citations, data analysis,
            project work, transcription and research services.
          </p>

          <img src="/flier.png" alt="Service Flier" className="flier" />

          <div className="button-row">
            <button className="primary-button" onClick={() => setPage("citation")}>
              Citation Generator
            </button>

            <a
              href={`mailto:${email}?subject=Research Services Request&body=Hello StatEdge Consult, I want to request your academic/research services.`}
              className="secondary-button"
            >
              Other Services
            </a>
          </div>

          <p className="phone">Contact: {phone}</p>
          <p className="email">Email: {email}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-page">
      <div className="header">
        <button className="back-button" onClick={() => setPage("welcome")}>
          Back
        </button>

        <img src="/logo.png" alt="Logo" className="small-logo" />

        <div className="header-copy">
          <h1 className="title">AI Citation Generator</h1>
          <p className="subtitle">
            Type a sentence, select the year range, and generate possible
            academic in-text citations.
          </p>
          <p className="phone">Contact: {phone}</p>
        </div>
      </div>

      <div className="card">
        <label className="label">Enter your sentence or claim</label>

        <textarea
          placeholder="Example: Artificial intelligence improves education among students..."
          value={sentence}
          onChange={(e) => setSentence(e.target.value)}
          className="textarea" />

        <div className="field-group">
          <label className="label">Citation Style</label>
          <select
            value={citationStyle}
            onChange={(e) => setCitationStyle(e.target.value)}
            className="select"
          >
            <option value="APA">APA</option>
            <option value="MLA">MLA</option>
            <option value="Chicago">Chicago</option>
          </select>
        </div>

        <div className="form-row">
          <div className="year-field">
            <label className="label">Start Year</label>
            <input
              type="number"
              value={startYear}
              onChange={(e) => setStartYear(e.target.value)}
              className="input" />
          </div>

          <div className="year-field">
            <label className="label">End Year</label>
            <input
              type="number"
              value={endYear}
              onChange={(e) => setEndYear(e.target.value)}
              className="input" />
          </div>
        </div>

        <button className="primary-button" onClick={generateCitation}>
          {loading ? "Searching articles..." : "Generate Citation"}
        </button>
      </div>

      <div className="results">
        {results.length === 0 && !loading && (
          <p className="no-results">Enter a sentence and click Generate Citation to start.</p>
        )}

        {results.map((item, index) => (
          <div key={index} className="result-card">
            <h3 className="result-title">{item.title}</h3>

            <p><strong>Sentence:</strong> {item.sentence_with_citation}</p>
            <p><strong>{citationStyle} In-text citation:</strong> {item.citation}</p>
            <p><strong>Reference:</strong> {item.reference}</p>
            <p><strong>Authors:</strong> {item.authors}</p>
            <p><strong>Year:</strong> {item.year}</p>
            <p><strong>Sources:</strong> {item.sources?.join(", ") || "Unknown"}</p>
            <p><strong>Exact word matches:</strong> {item.exact_match_count}</p>
            {item.matched_keywords?.length > 0 && (
              <p><strong>Matched keywords:</strong> {item.matched_keywords.join(", ")}</p>
            )}
            {item.title_keyword_matches?.length > 0 && (
              <p><strong>Title keyword overlap:</strong> {item.title_keyword_matches.join(", ")}</p>
            )}
            <p><strong>AI Similarity Score:</strong> {item.similarity_score} ({item.similarity_label})</p>
            <p><strong>Keyword Match Score:</strong> {item.keyword_overlap_score}</p>
            <p><strong>Final Score:</strong> {item.final_score}</p>
            <p><strong>Cited By:</strong> {item.cited_by_count}</p>

            <a href={item.link} target="_blank" rel="noreferrer" className="source-button">
              View Source
            </a>

            <p className="abstract">
              <strong>Abstract:</strong> {item.abstract}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;
