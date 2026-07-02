from pathlib import Path
from html import escape

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.orchestrator import run_council

ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
CONVERSATIONS_DIR = ROOT / "conversations"

app = FastAPI()


def page_shell(title: str, body: str) -> str:
    return f"""
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{escape(title)}</title>
        <style>
            :root {{
                --bg: #f6f7f2;
                --card: #ffffff;
                --text: #1f2933;
                --muted: #667085;
                --border: #d9e2d0;
                --accent: #2f6f3e;
                --accent-dark: #245832;
                --soft: #eef5ea;
            }}
            * {{ box-sizing: border-box; }}
            body {{
                margin: 0;
                font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                color: var(--text);
                background: linear-gradient(180deg, #eef5ea 0%, var(--bg) 220px);
            }}
            .wrap {{
                width: min(980px, 100%);
                margin: 0 auto;
                padding: 18px;
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                gap: 12px;
                align-items: center;
                margin-bottom: 16px;
            }}
            .brand {{
                display: flex;
                flex-direction: column;
                gap: 2px;
            }}
            h1 {{
                font-size: clamp(1.5rem, 4vw, 2.3rem);
                margin: 0;
                line-height: 1.1;
            }}
            .subtitle {{ color: var(--muted); font-size: 0.95rem; }}
            .nav {{ display: flex; gap: 8px; flex-wrap: wrap; }}
            a, .link-button {{ color: var(--accent); text-decoration: none; font-weight: 650; }}
            .button, button {{
                border: 0;
                background: var(--accent);
                color: white;
                padding: 12px 16px;
                border-radius: 12px;
                font-size: 1rem;
                font-weight: 700;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
            }}
            .button:hover, button:hover {{ background: var(--accent-dark); }}
            .button.secondary {{
                background: white;
                color: var(--accent);
                border: 1px solid var(--border);
            }}
            .grid {{ display: grid; grid-template-columns: 1.4fr 0.8fr; gap: 14px; }}
            .card {{
                background: var(--card);
                border: 1px solid var(--border);
                border-radius: 18px;
                padding: 16px;
                box-shadow: 0 8px 24px rgba(31, 41, 51, 0.06);
            }}
            label {{ display: block; font-weight: 750; margin-bottom: 8px; }}
            textarea {{
                width: 100%;
                min-height: 180px;
                padding: 14px;
                font-size: 1rem;
                line-height: 1.4;
                border: 1px solid var(--border);
                border-radius: 14px;
                resize: vertical;
            }}
            .hint {{ color: var(--muted); font-size: 0.92rem; margin-top: 8px; }}
            .actions {{ display: flex; align-items: center; gap: 10px; margin-top: 12px; flex-wrap: wrap; }}
            .loading {{ display: none; color: var(--muted); font-weight: 650; }}
            form.submitting .loading {{ display: inline; }}
            .agent {{ margin-bottom: 14px; }}
            .agent h2, .card h2 {{ margin: 0 0 10px; font-size: 1.15rem; }}
            pre {{
                white-space: pre-wrap;
                word-wrap: break-word;
                background: #fbfcf9;
                border: 1px solid var(--border);
                border-radius: 14px;
                padding: 12px;
                overflow-x: auto;
                font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
                font-size: 0.92rem;
                line-height: 1.45;
            }}
            .history-list {{ display: flex; flex-direction: column; gap: 10px; }}
            .history-item {{
                background: var(--soft);
                border: 1px solid var(--border);
                border-radius: 14px;
                padding: 10px;
            }}
            .history-item .file {{ font-size: 0.82rem; color: var(--muted); margin-top: 4px; }}
            .empty {{ color: var(--muted); }}
            @media (max-width: 760px) {{
                .header {{ align-items: flex-start; flex-direction: column; }}
                .grid {{ grid-template-columns: 1fr; }}
                .wrap {{ padding: 12px; }}
                .card {{ padding: 13px; border-radius: 16px; }}
                textarea {{ min-height: 160px; }}
                .button, button {{ width: 100%; text-align: center; }}
            }}
        </style>
    </head>
    <body>
        <div class="wrap">
            <div class="header">
                <div class="brand">
                    <h1>Farm AI Council</h1>
                    <div class="subtitle">Historian → Agronomist → Managing Agent</div>
                </div>
                <div class="nav">
                    <a class="button secondary" href="/">Ask</a>
                    <a class="button secondary" href="/history">History</a>
                </div>
            </div>
            {body}
        </div>
    </body>
    </html>
    """


def get_recent_reports(limit: int = 10):
    REPORTS_DIR.mkdir(exist_ok=True)
    files = sorted(REPORTS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:limit]


def extract_question(text: str) -> str:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "Question:" and i + 1 < len(lines):
            return lines[i + 1].strip()
        if line.strip().startswith("Question:"):
            return line.split("Question:", 1)[1].strip()
    if "## Question" in text:
        after = text.split("## Question", 1)[1].strip().splitlines()
        return after[0].strip() if after else "Untitled question"
    return "Untitled question"


@app.get("/", response_class=HTMLResponse)
def home():
    recent = get_recent_reports(5)
    if recent:
        items = "".join(
            f"""
            <div class="history-item">
                <a href="/history/{escape(file.name)}">{escape(extract_question(file.read_text(encoding='utf-8', errors='ignore')))}</a>
                <div class="file">{escape(file.name)}</div>
            </div>
            """
            for file in recent
        )
    else:
        items = '<p class="empty">No reports yet. Ask a question to create the first one.</p>'

    body = f"""
    <div class="grid">
        <section class="card">
            <h2>Ask a farm question</h2>
            <form action="/ask" method="post" onsubmit="this.classList.add('submitting')">
                <label for="question">Question or scenario</label>
                <textarea id="question" name="question" required placeholder="Example: The beans are yellowing on the slopes of a new field. It does not look like herbicide damage. What might be causing it?"></textarea>
                <div class="hint">Keep it practical. Include crop, field, timing, weather, symptoms, and what you have already ruled out if you know them.</div>
                <div class="actions">
                    <button type="submit">Ask Council</button>
                    <span class="loading">Working... this may take a minute.</span>
                </div>
            </form>
        </section>
        <aside class="card">
            <h2>Recent reports</h2>
            <div class="history-list">{items}</div>
        </aside>
    </div>
    """
    return page_shell("Farm AI Council", body)


@app.post("/ask", response_class=HTMLResponse)
def ask(question: str = Form(...)):
    result = run_council(question.strip())

    body = f"""
    <section class="card">
        <h2>Question</h2>
        <pre>{escape(question)}</pre>
        <div class="agent">
            <h2>Historian</h2>
            <pre>{escape(result['historian'])}</pre>
        </div>
        <div class="agent">
            <h2>Agronomist</h2>
            <pre>{escape(result['agronomist'])}</pre>
        </div>
        <div class="agent">
            <h2>Managing Agent Final Decision</h2>
            <pre>{escape(result['manager'])}</pre>
        </div>
        <div class="actions">
            <a class="button" href="/">Ask another question</a>
            <a class="button secondary" href="/history">View history</a>
        </div>
    </section>
    """
    return page_shell("Council Response", body)


@app.get("/history", response_class=HTMLResponse)
def history():
    recent = get_recent_reports(30)
    if recent:
        items = "".join(
            f"""
            <div class="history-item">
                <a href="/history/{escape(file.name)}">{escape(extract_question(file.read_text(encoding='utf-8', errors='ignore')))}</a>
                <div class="file">{escape(file.name)}</div>
            </div>
            """
            for file in recent
        )
    else:
        items = '<p class="empty">No reports found.</p>'

    body = f"""
    <section class="card">
        <h2>Report history</h2>
        <div class="history-list">{items}</div>
    </section>
    """
    return page_shell("Report History", body)


@app.get("/history/{filename}", response_class=HTMLResponse)
def history_detail(filename: str):
    safe_name = Path(filename).name
    path = REPORTS_DIR / safe_name

    if not path.exists() or path.suffix.lower() != ".md":
        return RedirectResponse("/history", status_code=303)

    text = path.read_text(encoding="utf-8", errors="ignore")
    body = f"""
    <section class="card">
        <h2>{escape(safe_name)}</h2>
        <pre>{escape(text)}</pre>
        <div class="actions">
            <a class="button" href="/">Ask new question</a>
            <a class="button secondary" href="/history">Back to history</a>
        </div>
    </section>
    """
    return page_shell("Report Detail", body)
