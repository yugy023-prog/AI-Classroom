from __future__ import annotations

import base64
import hashlib
import html
import json
import mimetypes
import os
import re
import secrets
import time
import zlib
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import urllib.request


ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DATA = ROOT / "data"
USERS_FILE = DATA / "users.json"
NOTES_FILE = DATA / "notes.json"
SESSIONS: dict[str, str] = {}


STOPWORDS = {
    "about", "after", "again", "also", "because", "before", "between", "could",
    "during", "each", "from", "have", "into", "more", "most", "other", "over",
    "should", "some", "such", "than", "that", "their", "there", "these", "this",
    "through", "under", "using", "very", "were", "what", "when", "where", "which",
    "while", "with", "would", "your", "study", "assistant", "question", "answer",
}


def ensure_data() -> None:
    DATA.mkdir(exist_ok=True)
    for path, default in ((USERS_FILE, {}), (NOTES_FILE, [])):
        if not path.exists():
            path.write_text(json.dumps(default, indent=2), encoding="utf-8")


def read_json(path: Path, default):
    ensure_data()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, value) -> None:
    ensure_data()
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def hash_password(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


def sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    return [part.strip() for part in parts if len(part.strip()) > 20]


def keywords(text: str, limit: int = 10) -> list[dict[str, int]]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9-]{3,}", text.lower())
    counts: dict[str, int] = {}
    for word in words:
        if word not in STOPWORDS:
            counts[word] = counts.get(word, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [{"term": term, "count": count} for term, count in ranked[:limit]]


def summarize(text: str, limit: int = 5) -> list[str]:
    raw_sentences = sentences(text)
    if not raw_sentences or len(raw_sentences) < limit:
        return raw_sentences or ["Add more source text to generate a stronger summary."]

    # 1. Pre-process and filter sentences
    processed_sentences = [re.findall(r'\w+', s.lower()) for s in raw_sentences]

    # 2. Build similarity matrix
    num_sentences = len(processed_sentences)
    similarity_matrix = [[0.0] * num_sentences for _ in range(num_sentences)]

    for i in range(num_sentences):
        for j in range(i, num_sentences):
            if i == j:
                continue
            set_i = set(processed_sentences[i])
            set_j = set(processed_sentences[j])
            
            # Jaccard similarity for sentence comparison
            intersection = len(set_i.intersection(set_j))
            union = len(set_i.union(set_j))
            if union > 0:
                similarity = intersection / union
                similarity_matrix[i][j] = similarity
                similarity_matrix[j][i] = similarity

    # 3. Rank sentences using PageRank-like algorithm (TextRank)
    scores = [1.0] * num_sentences
    damping = 0.85
    for _ in range(20):  # Iterations for convergence
        new_scores = [1 - damping] * num_sentences
        for i in range(num_sentences):
            s_i = sum(similarity_matrix[i][j] * scores[j] for j in range(num_sentences))
            new_scores[i] += damping * s_i
        scores = new_scores

    # 4. Select top sentences
    ranked_sentences = sorted(((scores[i], s) for i, s in enumerate(raw_sentences)), reverse=True)
    
    # Ensure we don't have duplicate sentences in the summary
    final_summary = []
    seen_sentences = set()
    for _, sentence in ranked_sentences:
        if sentence not in seen_sentences:
            final_summary.append(sentence)
            seen_sentences.add(sentence)
            if len(final_summary) == limit:
                break
    
    # Sort the final summary by appearance in the original text
    final_summary.sort(key=lambda s: raw_sentences.index(s))

    return final_summary


def generate_quiz(text: str) -> list[dict[str, str]]:
    top_terms = [item["term"] for item in keywords(text, 8)]
    source_sentences = sentences(text)
    quiz = []
    for term in top_terms[:5]:
        clue = next((s for s in source_sentences if term in s.lower()), "")
        quiz.append({
            "question": f"Explain the role of '{term}' in the study material.",
            "answer": clue or f"Review the uploaded material and connect '{term}' to the main topic.",
        })
    if not quiz:
        quiz.append({
            "question": "What are the three most important ideas in this material?",
            "answer": "Use the summary and topic list to identify the main ideas.",
        })
    return quiz


def extract_pdf_text(data: bytes) -> str:
    text_chunks: list[str] = []
    for stream in re.findall(rb"stream\r?\n(.*?)endstream", data, re.S):
        raw = stream.strip()
        candidates = []
        if raw.endswith(b"~>"):
            try:
                candidates.append(base64.a85decode(raw, adobe=True))
            except Exception:
                pass
        candidates.append(raw)
        decoded_candidates = []
        for candidate in list(candidates):
            try:
                decoded_candidates.append(zlib.decompress(candidate))
            except Exception:
                pass
        decoded_candidates.extend(candidates)
        for candidate in decoded_candidates:
            decoded = candidate.decode("latin1", errors="ignore")
            if " BT " not in f" {decoded} " and " Tj" not in decoded and " TJ" not in decoded:
                continue
            text_chunks.extend(re.findall(r"\((.*?)\)\s*Tj", decoded, re.S))
            for array_body in re.findall(r"\[(.*?)\]\s*TJ", decoded, re.S):
                text_chunks.append("".join(re.findall(r"\((.*?)\)", array_body, re.S)))
    plain = " ".join(unescape_pdf_text(chunk) for chunk in text_chunks)
    return re.sub(r"\s+", " ", plain).strip()


def unescape_pdf_text(value: str) -> str:
    return (
        value.replace("\\(", "(")
        .replace("\\)", ")")
        .replace("\\\\", "\\")
        .replace("\\r", " ")
        .replace("\\n", " ")
        .replace("\\t", " ")
    )


def short_text_error(title: str, is_upload: bool) -> dict | None:
    if not is_upload:
        return None
    if title.lower().endswith(".pdf"):
        return {
            "error": (
                "I could not extract readable text from this PDF. It may be scanned, image-based, "
                "or encoded in a PDF format this no-install demo parser cannot read yet. Try a text-based PDF, "
                "paste the content, or install a PDF extractor such as pypdf/PyPDF2 for better support."
            )
        }
    return {"error": "I could not find enough readable text in that file to summarize it."}


def analyze_text(text: str, title: str = "Uploaded material") -> dict:
    topic_list = keywords(text)
    
    if title in ("Pasted material", "Pasted study material", "Uploaded material", "Uploaded file") and topic_list:
        display_title = f"{topic_list[0]['term'].title()} Overview"
    else:
        display_title = title

    return {
        "title": display_title,
        "wordCount": len(re.findall(r"\w+", text)),
        "summary": summarize(text),
        "topics": topic_list,
        "quiz": generate_quiz(text),
        "diagram": {
            "center": display_title,
            "nodes": [
                {"label": item["term"].title(), "weight": item["count"]}
                for item in topic_list[:8]
            ] or ["Summary", "Quiz", "Notes"],
        },
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "AIStudyAssistant/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_file(STATIC / "index.html")
        elif parsed.path == "/api/me":
            self.send_json({"user": self.current_user()})
        elif parsed.path == "/api/notes":
            user = self.require_user()
            if not user:
                return
            notes = [note for note in read_json(NOTES_FILE, []) if note["user"] == user]
            self.send_json({"notes": notes})
        elif parsed.path.startswith("/static/"):
            self.send_file(ROOT / parsed.path.lstrip("/"))
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/register":
            payload = self.json_body()
            username = clean_name(payload.get("username", ""))
            password = payload.get("password", "")
            if len(username) < 3 or len(password) < 4:
                self.send_json({"error": "Use a 3+ character name and 4+ character password."}, 400)
                return
            users = read_json(USERS_FILE, {})
            if username in users:
                self.send_json({"error": "That username already exists."}, 409)
                return
            salt = secrets.token_hex(8)
            users[username] = {"salt": salt, "password": hash_password(password, salt)}
            write_json(USERS_FILE, users)
            self.create_session(username)
        elif parsed.path == "/api/login":
            payload = self.json_body()
            username = clean_name(payload.get("username", ""))
            password = payload.get("password", "")
            users = read_json(USERS_FILE, {})
            account = users.get(username)
            if not account or account["password"] != hash_password(password, account["salt"]):
                self.send_json({"error": "Invalid username or password."}, 401)
                return
            self.create_session(username)
        elif parsed.path == "/api/logout":
            token = self.cookie("session")
            if token:
                SESSIONS.pop(token, None)
            self.send_response(204)
            self.send_header("Set-Cookie", "session=; Path=/; Max-Age=0; SameSite=Lax")
            self.end_headers()
        elif parsed.path == "/api/analyze":
            self.handle_analyze()
        elif parsed.path == "/api/notes":
            user = self.require_user()
            if not user:
                return
            payload = self.json_body()
            note = {
                "id": secrets.token_hex(6),
                "user": user,
                "title": str(payload.get("title", "Untitled note"))[:80],
                "body": str(payload.get("body", ""))[:4000],
                "created": int(time.time()),
            }
            notes = read_json(NOTES_FILE, [])
            notes.insert(0, note)
            write_json(NOTES_FILE, notes)
            self.send_json({"note": note}, 201)
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def handle_analyze(self) -> None:
        content_type = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        title = "Analyzed Material"
        text = ""
        is_upload = False
        if "application/json" in content_type:
            payload = json.loads(raw.decode("utf-8") or "{}")
            text = str(payload.get("text", ""))
            title = str(payload.get("title", title))
        elif "multipart/form-data" in content_type:
            boundary_match = re.search(r"boundary=(.+)", content_type)
            if boundary_match:
                boundary = boundary_match.group(1).encode("utf-8")
                parts = raw.split(b"--" + boundary)
                for part in parts:
                    if b"\r\n\r\n" not in part:
                        continue
                    headers, body = part.split(b"\r\n\r\n", 1)
                    body = body.rstrip(b"\r\n-")
                    name_match = re.search(rb'name="([^"]+)"', headers)
                    filename_match = re.search(rb'filename="([^"]*)"', headers)
                    name = name_match.group(1).decode() if name_match else ""
                    if filename_match and body:
                        is_upload = True
                        title = filename_match.group(1).decode(errors="ignore") or "Uploaded file"
                        text = extract_pdf_text(body) if title.lower().endswith(".pdf") else body.decode("utf-8", errors="ignore")
                    elif name == "text":
                        text = body.decode("utf-8", errors="ignore")

        cleaned = text.strip()
        if len(cleaned) < 20:
            error = short_text_error(title, is_upload)
            if error:
                self.send_json(error, 422)
                return
        if not cleaned:
            text = "AI study assistant roadmap: plan pages, choose technologies, build frontend, setup backend, analyze PDFs and previous year papers, add AI summaries, diagrams, quizzes, login, database storage, question generation, design improvements, project structure, advanced AI features, deployment, and a minimum working hackathon version."
        self.send_json({"analysis": analyze_text(text, title)})

    def current_user(self) -> str | None:
        return SESSIONS.get(self.cookie("session") or "")

    def require_user(self) -> str | None:
        user = self.current_user()
        if not user:
            self.send_json({"error": "Please log in first."}, 401)
        return user

    def create_session(self, username: str) -> None:
        token = secrets.token_urlsafe(24)
        SESSIONS[token] = username
        self.send_json(
            {"user": username},
            headers={"Set-Cookie": f"session={token}; Path=/; HttpOnly; SameSite=Lax"},
        )

    def json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8") or "{}")

    def cookie(self, name: str) -> str | None:
        cookie_header = self.headers.get("Cookie", "")
        for part in cookie_header.split(";"):
            key, _, value = part.strip().partition("=")
            if key == name:
                return value
        return None

    def send_json(self, payload, status: int = 200, headers: dict[str, str] | None = None) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(encoded)

    def send_file(self, path: Path) -> None:
        try:
            resolved = path.resolve()
            if not str(resolved).startswith(str(ROOT)) or not resolved.exists():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            data = resolved.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(resolved.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except OSError:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, format: str, *args) -> None:
        print(f"{self.address_string()} - {format % args}")


def clean_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "", value)[:32]


if __name__ == "__main__":
    ensure_data()
    os.chdir(ROOT)
    host = "127.0.0.1"
    port = int(os.environ.get("PORT", "5000"))
    print(f"AI Study Assistant running at http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
