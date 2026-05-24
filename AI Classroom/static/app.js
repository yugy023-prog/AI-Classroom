const fallbackText = `This PDF contains the roadmap for building the AI Study Assistant website.
Plan the website pages. Choose technologies like HTML, CSS, JavaScript, Flask, Firebase.
Build frontend pages. Setup backend using Python Flask. Add PDF analysis using PyPDF2.
Analyze previous year papers. Add AI summaries. Create interactive 2D diagrams.
Build quiz system. Store data in database. Add login system. Generate AI questions.
Improve website design. Organize project structure. Add advanced AI features. Deploy website.
Build minimum working version for hackathon.`;

let latestAnalysis = null;

const els = {
  authStatus: document.querySelector("#authStatus"),
  username: document.querySelector("#username"),
  password: document.querySelector("#password"),
  loginBtn: document.querySelector("#loginBtn"),
  registerBtn: document.querySelector("#registerBtn"),
  analysisForm: document.querySelector("#analysisForm"),
  fileInput: document.querySelector("#fileInput"),
  sourceText: document.querySelector("#sourceText"),
  analysisStatus: document.querySelector("#analysisStatus"),
  resultTitle: document.querySelector("#resultTitle"),
  wordCount: document.querySelector("#wordCount"),
  topicCount: document.querySelector("#topicCount"),
  questionCount: document.querySelector("#questionCount"),
  summaryList: document.querySelector("#summaryList"),
  topicCloud: document.querySelector("#topicCloud"),
  quizList: document.querySelector("#quizList"),
  noteForm: document.querySelector("#noteForm"),
  noteTitle: document.querySelector("#noteTitle"),
  noteBody: document.querySelector("#noteBody"),
  notesList: document.querySelector("#notesList"),
  canvas: document.querySelector("#conceptCanvas"),
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    ...options,
    headers: options.body instanceof FormData ? options.headers : {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  if (response.status === 204) return {};
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "Request failed");
  return payload;
}

async function authenticate(mode) {
  try {
    const payload = await api(`/api/${mode}`, {
      method: "POST",
      body: JSON.stringify({
        username: els.username.value,
        password: els.password.value,
      }),
    });
    els.authStatus.textContent = `Signed in as ${payload.user}.`;
    els.password.value = "";
    loadNotes();
  } catch (error) {
    els.authStatus.textContent = error.message;
  }
}

function renderAnalysis(analysis) {
  latestAnalysis = analysis;
  els.resultTitle.textContent = analysis.title;
  els.wordCount.textContent = analysis.wordCount;
  els.topicCount.textContent = analysis.topics.length;
  els.questionCount.textContent = analysis.quiz.length;
  els.summaryList.innerHTML = analysis.summary.map(item => `<li>${escapeHtml(item)}</li>`).join("");
  els.topicCloud.innerHTML = analysis.topics.map(topic => `<span>${escapeHtml(topic.term)} · ${topic.count}</span>`).join("");
  els.quizList.innerHTML = analysis.quiz.map((item, index) => `
    <article class="quiz-card">
      <strong>Q${index + 1}. ${escapeHtml(item.question)}</strong>
      <button type="button" data-answer="${index}">Show Answer</button>
      <p class="answer" id="answer-${index}">${escapeHtml(item.answer)}</p>
    </article>
  `).join("");
  drawDiagram(analysis.diagram);
}

function drawDiagram(diagram) {
  const canvas = els.canvas;
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#f8fbfc";
  ctx.fillRect(0, 0, width, height);

  const center = { x: width / 2, y: height / 2 };
  const nodes = diagram.nodes.length ? diagram.nodes : ["Summary", "Quiz", "Notes"];
  const radius = Math.min(width, height) * 0.32;
  const colors = ["#2f7d6f", "#d59f3f", "#c7604f", "#3b6ea8", "#6b7a3f", "#8b5d78"];

  ctx.lineWidth = 2;
  ctx.font = "700 16px Segoe UI, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";

  nodes.forEach((node, index) => {
    const angle = (Math.PI * 2 * index) / nodes.length - Math.PI / 2;
    const x = center.x + Math.cos(angle) * radius;
    const y = center.y + Math.sin(angle) * radius;
    ctx.strokeStyle = "rgba(24, 32, 38, 0.18)";
    ctx.beginPath();
    ctx.moveTo(center.x, center.y);
    ctx.lineTo(x, y);
    ctx.stroke();

    ctx.fillStyle = colors[index % colors.length];
    roundRect(ctx, x - 78, y - 28, 156, 56, 8);
    ctx.fill();
    ctx.fillStyle = "#fff";
    wrapText(ctx, node, x, y, 128, 18);
  });

  ctx.fillStyle = "#182026";
  roundRect(ctx, center.x - 110, center.y - 38, 220, 76, 8);
  ctx.fill();
  ctx.fillStyle = "#fff";
  wrapText(ctx, diagram.center, center.x, center.y, 180, 20);
}

function roundRect(ctx, x, y, width, height, radius) {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.arcTo(x + width, y, x + width, y + height, radius);
  ctx.arcTo(x + width, y + height, x, y + height, radius);
  ctx.arcTo(x, y + height, x, y, radius);
  ctx.arcTo(x, y, x + width, y, radius);
  ctx.closePath();
}

function wrapText(ctx, text, x, y, maxWidth, lineHeight) {
  const words = text.split(" ");
  const lines = [];
  let line = "";
  words.forEach(word => {
    const test = `${line} ${word}`.trim();
    if (ctx.measureText(test).width > maxWidth && line) {
      lines.push(line);
      line = word;
    } else {
      line = test;
    }
  });
  lines.push(line);
  const start = y - ((lines.length - 1) * lineHeight) / 2;
  lines.forEach((item, index) => ctx.fillText(item, x, start + index * lineHeight));
}

async function analyzeDefault() {
  const payload = await api("/api/analyze", {
    method: "POST",
    body: JSON.stringify({ title: "AI Study Assistant Roadmap", text: fallbackText }),
  });
  renderAnalysis(payload.analysis);
}

async function loadNotes() {
  try {
    const payload = await api("/api/notes");
    els.notesList.innerHTML = payload.notes.length
      ? payload.notes.map(note => `
        <article class="note-card">
          <h3>${escapeHtml(note.title)}</h3>
          <p>${escapeHtml(note.body)}</p>
        </article>
      `).join("")
      : `<article class="note-card"><p>No notes saved yet.</p></article>`;
  } catch {
    els.notesList.innerHTML = `<article class="note-card"><p>Log in to save and view notes.</p></article>`;
  }
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, char => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

els.loginBtn.addEventListener("click", () => authenticate("login"));
els.registerBtn.addEventListener("click", () => authenticate("register"));

els.analysisForm.addEventListener("submit", async event => {
  event.preventDefault();
  els.analysisStatus.textContent = "Analyzing material...";
  els.analysisStatus.className = "status-text";
  try {
    let response;
    if (els.fileInput.files[0]) {
      const form = new FormData();
      form.append("file", els.fileInput.files[0]);
      form.append("text", els.sourceText.value);
      response = await api("/api/analyze", { method: "POST", body: form });
    } else {
      response = await api("/api/analyze", {
        method: "POST",
        body: JSON.stringify({
          title: "Pasted study material",
          text: els.sourceText.value || fallbackText,
        }),
      });
    }
    renderAnalysis(response.analysis);
    els.analysisStatus.textContent = "Analysis complete.";
    els.analysisStatus.className = "status-text success";
  } catch (error) {
    const offline = error instanceof TypeError || /fetch|network/i.test(error.message);
    els.analysisStatus.textContent = offline
      ? "The backend API is not responding. Run python app.py, then try again."
      : error.message;
    els.analysisStatus.className = "status-text error";
  }
});

els.quizList.addEventListener("click", event => {
  const button = event.target.closest("button[data-answer]");
  if (!button) return;
  document.querySelector(`#answer-${button.dataset.answer}`).classList.toggle("visible");
});

els.noteForm.addEventListener("submit", async event => {
  event.preventDefault();
  const title = els.noteTitle.value || latestAnalysis?.title || "Study note";
  const body = els.noteBody.value || latestAnalysis?.summary?.join("\n") || "";
  try {
    await api("/api/notes", {
      method: "POST",
      body: JSON.stringify({ title, body }),
    });
    els.noteTitle.value = "";
    els.noteBody.value = "";
    loadNotes();
  } catch (error) {
    alert(error.message);
  }
});

api("/api/me").then(payload => {
  if (payload.user) els.authStatus.textContent = `Signed in as ${payload.user}.`;
});

analyzeDefault();
loadNotes();
