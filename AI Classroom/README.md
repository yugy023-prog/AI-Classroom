# AI Study Assistant

A self-contained working website project for the AI Study Assistant roadmap.

## Features

- Dashboard for study notes, summaries, quiz questions, and diagrams
- PDF/text upload analysis with extractive summaries
- Previous-year paper topic frequency analysis
- Generated quiz questions from uploaded content
- Interactive 2D concept diagram
- Simple local login and JSON-file storage
- No required third-party packages

## Run

```powershell
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

Data is stored locally in the `data/` folder.

## Project Structure

```text
app.py                Python standard-library web server and API
static/index.html     Main website UI
static/styles.css     Responsive styling
static/app.js         Frontend behavior
data/                 Created automatically for local saved data
```

## Notes

This minimum working version is designed for hackathon/demo use. It uses lightweight local heuristics for summaries and questions so the project works immediately. You can later connect the same frontend API to Flask, Firebase, OpenAI, or another AI backend.
