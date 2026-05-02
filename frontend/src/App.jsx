import { useState } from "react";

function App() {
  const [page, setPage] = useState("welcome");
  const [sentence, setSentence] = useState("");
  const [startYear, setStartYear] = useState(2019);
  const [endYear, setEndYear] = useState(2026);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const email = "henryyhude@gmail.com";
  const phone = "+233 509927178";

  const generateCitation = async () => {
    if (!sentence.trim()) {
      alert("Please enter a sentence first.");
      return;
    }

    setLoading(true);
    setResults([]);

    try {
      const response = await fetch(
        "https://statedge-citation-app.onrender.com/generate-citation",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            sentence: sentence,
            start_year: Number(startYear),
            end_year: Number(endYear)
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
      <div style={styles.page}>
        <div style={styles.welcomeCard}>
          <img src="/logo.png" alt="Logo" style={styles.logo} />

          <h1 style={styles.title}>Welcome to StatEdge Consult</h1>

          <p style={styles.subtitle}>
            Your smart academic support platform for citations, data analysis,
            project work, transcription and research services.
          </p>

          <img src="/flier.png" alt="Service Flier" style={styles.flier} />

          <div style={styles.buttonRow}>
            <button style={styles.button} onClick={() => setPage("citation")}>
              Citation Generator
            </button>

            <a
              href={`mailto:${email}?subject=Research Services Request&body=Hello StatEdge Consult, I want to request your academic/research services.`}
              style={styles.emailButton}
            >
              Other Services
            </a>
          </div>

          <p style={styles.phone}>Contact: {phone}</p>
          <p style={styles.email}>Email: {email}</p>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <button style={styles.backButton} onClick={() => setPage("welcome")}>
          ← Back
        </button>

        <img src="/logo.png" alt="Logo" style={styles.smallLogo} />

        <div>
          <h1 style={styles.title}>AI Citation Generator</h1>
          <p style={styles.subtitle}>
            Type a sentence, select the year range, and generate possible
            academic in-text citations.
          </p>
          <p style={styles.phone}>Contact: {phone}</p>
        </div>
      </div>

      <div style={styles.card}>
        <label style={styles.label}>Enter your sentence or claim</label>

        <textarea
          placeholder="Example: Artificial intelligence improves education among students..."
          value={sentence}
          onChange={(e) => setSentence(e.target.value)}
          style={styles.textarea}
        />

        <div style={styles.row}>
          <div>
            <label style={styles.label}>Start Year</label>
            <input
              type="number"
              value={startYear}
              onChange={(e) => setStartYear(e.target.value)}
              style={styles.input}
            />
          </div>

          <div>
            <label style={styles.label}>End Year</label>
            <input
              type="number"
              value={endYear}
              onChange={(e) => setEndYear(e.target.value)}
              style={styles.input}
            />
          </div>
        </div>

        <button style={styles.button} onClick={generateCitation}>
          {loading ? "Searching articles..." : "Generate Citation"}
        </button>
      </div>

      <div style={styles.results}>
        {results.map((item, index) => (
          <div key={index} style={styles.resultCard}>
            <h3 style={styles.resultTitle}>{item.title}</h3>

            <p><strong>Sentence:</strong> {item.sentence_with_citation}</p>
            <p><strong>Citation:</strong> {item.citation}</p>
            <p><strong>Authors:</strong> {item.authors}</p>
            <p><strong>Year:</strong> {item.year}</p>
            <p><strong>Relevance Score:</strong> {item.similarity_score}</p>
            <p><strong>Cited By:</strong> {item.cited_by_count}</p>

            <a href={item.link} target="_blank" rel="noreferrer" style={styles.sourceButton}>
              View Source
            </a>

            <p style={styles.abstract}>
              <strong>Abstract:</strong> {item.abstract}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    background: "linear-gradient(135deg, #073b8e, #0f75d4)",
    fontFamily: "Segoe UI, Arial, sans-serif",
    padding: "40px 20px"
  },
  welcomeCard: {
    maxWidth: "950px",
    margin: "auto",
    background: "white",
    padding: "35px",
    borderRadius: "24px",
    textAlign: "center",
    boxShadow: "0 12px 35px rgba(0,0,0,0.25)"
  },
  logo: {
    width: "110px",
    height: "110px",
    objectFit: "contain",
    marginBottom: "10px"
  },
  smallLogo: {
    width: "85px",
    height: "85px",
    objectFit: "contain"
  },
  title: {
    margin: "10px 0",
    color: "#073b8e",
    fontSize: "38px",
    fontWeight: "800"
  },
  subtitle: {
    color: "#333",
    fontSize: "16px",
    lineHeight: "1.6"
  },
  flier: {
    width: "100%",
    maxWidth: "680px",
    borderRadius: "18px",
    marginTop: "22px",
    boxShadow: "0 8px 24px rgba(0,0,0,0.22)"
  },
  buttonRow: {
    marginTop: "28px",
    display: "flex",
    justifyContent: "center",
    gap: "16px",
    flexWrap: "wrap"
  },
  button: {
    background: "linear-gradient(135deg, #073b8e, #1e88e5)",
    color: "white",
    border: "none",
    padding: "14px 30px",
    borderRadius: "12px",
    fontSize: "16px",
    cursor: "pointer",
    fontWeight: "700",
    boxShadow: "0 5px 14px rgba(0,0,0,0.25)"
  },
  emailButton: {
    background: "#0f75d4",
    color: "white",
    padding: "14px 30px",
    borderRadius: "12px",
    fontSize: "16px",
    textDecoration: "none",
    fontWeight: "700",
    boxShadow: "0 5px 14px rgba(0,0,0,0.25)"
  },
  phone: {
    color: "#073b8e",
    fontWeight: "bold",
    marginTop: "18px"
  },
  email: {
    color: "#333",
    fontWeight: "600"
  },
  header: {
    maxWidth: "1050px",
    margin: "0 auto 25px auto",
    background: "white",
    padding: "25px",
    borderRadius: "20px",
    display: "flex",
    alignItems: "center",
    gap: "20px",
    boxShadow: "0 10px 28px rgba(0,0,0,0.25)"
  },
  backButton: {
    background: "#eaf3ff",
    color: "#073b8e",
    border: "none",
    padding: "11px 16px",
    borderRadius: "10px",
    cursor: "pointer",
    fontWeight: "bold"
  },
  card: {
    maxWidth: "1050px",
    margin: "auto",
    background: "white",
    padding: "28px",
    borderRadius: "20px",
    boxShadow: "0 10px 28px rgba(0,0,0,0.25)"
  },
  label: {
    display: "block",
    fontWeight: "bold",
    color: "#073b8e",
    marginBottom: "8px"
  },
  textarea: {
    width: "100%",
    height: "135px",
    padding: "15px",
    fontSize: "16px",
    borderRadius: "12px",
    border: "1px solid #b8d6f7",
    marginBottom: "18px",
    outline: "none",
    boxSizing: "border-box"
  },
  row: {
    display: "flex",
    gap: "20px",
    marginBottom: "22px",
    flexWrap: "wrap"
  },
  input: {
    padding: "12px",
    fontSize: "16px",
    borderRadius: "10px",
    border: "1px solid #b8d6f7",
    outline: "none"
  },
  results: {
    maxWidth: "1050px",
    margin: "28px auto"
  },
  resultCard: {
    background: "white",
    padding: "24px",
    borderRadius: "18px",
    marginBottom: "20px",
    boxShadow: "0 10px 25px rgba(0,0,0,0.22)"
  },
  resultTitle: {
    color: "#073b8e",
    fontSize: "22px"
  },
  sourceButton: {
    display: "inline-block",
    background: "#073b8e",
    color: "white",
    padding: "11px 16px",
    borderRadius: "10px",
    textDecoration: "none",
    marginTop: "8px",
    fontWeight: "bold"
  },
  abstract: {
    marginTop: "15px",
    lineHeight: "1.7",
    color: "#333"
  }
};

export default App;