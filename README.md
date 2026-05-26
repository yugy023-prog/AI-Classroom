# AI Study Assistant

A self-contained working website project for the AI Study Assistant roadmap. Built entirely with the Python standard library—no third-party dependencies required.

## 🚀 Features

- **Document Analysis**: Upload PDFs, text files, or paste raw text to instantly generate intelligent study materials.
- **Smart Summarization**: Uses a custom PageRank-based (TextRank) extractive summarization algorithm to highlight key concepts.
- **Auto-Generated Quizzes**: Automatically creates customized quiz questions based on the highest-frequency topics and keywords in your material.
- **Concept Mapping**: Interactive 2D diagram visualizations of core concepts using HTML5 Canvas.
- **Study Notes**: Dashboard for managing your quick revision notes.
- **Simple Local Auth**: Local user registration and session-based login.
- **Local Data Storage**: Lightweight JSON file storage (created automatically in the `data/` folder).
- **Zero Dependencies**: Runs immediately. Uses pure Python standard-library modules (custom PDF extractor, web server, heuristic generators).

## 🛠️ Prerequisites

- **Python**: Version 3.8 or higher is recommended. No additional packages (like Flask or PyPDF2) are needed for this base MVP.

## 🚦 How to Run

1. Open your terminal or command prompt in the project folder.
2. Run the application:

```powershell
python app.py
```

3. Open your browser and navigate to:

```text
http://127.0.0.1:5000
```

## 🏗️ Project Structure

```text
app.py                Main standard-library web server, API, and logic
static/index.html     Main UI structure
static/styles.css     Responsive styling and theme
static/app.js         Frontend interaction logic
data/                 Created automatically for local JSON data storage (notes, users)
```

## 🧠 Under the Hood

Because this is a zero-dependency project, several features were rebuilt from scratch:
- **Web Server**: Extends Python's `ThreadingHTTPServer` and `BaseHTTPRequestHandler` to provide REST API endpoints and serve static files.
- **PDF Extraction**: A custom text extractor traverses raw PDF bitstreams and unzips encoded sections without bringing in external libraries.
- **Summarization**: Processes sentences and calculates Jaccard similarity between word sets, scoring them iteratively with a damping factor (like PageRank).

## 🎯 Notes for Future Development

This minimum working version is designed for hackathon/demo use. It uses lightweight local heuristics for summaries and questions so the project works immediately offline. 

**Next Steps / Expansion Ideas:**
- Connect the frontend API to a robust backend like **Flask** or **FastAPI**.
- Integrate with **OpenAI API**, **Anthropic**, or **Gemini** to replace heuristics with advanced LLM summaries and generative Q&A.
- Swap the local JSON storage adapter for **PostgreSQL**, **Firebase**, or **MongoDB**.
- Enhance PDF extraction capabilities by adding libraries like **pdfplumber** or **PyPDF2**.
