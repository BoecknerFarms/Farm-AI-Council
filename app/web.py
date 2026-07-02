import json
from datetime import date

from app.record_parser import parse_field_record
from app.field_record_service import save_approved_field_record
from app.master_data_service import (
    list_fields,
    create_field,
    list_crop_years,
    create_crop_year,
    get_crop_year,
)

from app.database import SessionLocal
from app.models import FieldOperation

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
            textarea, input, select {{
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
                    <a class="button secondary" href="/record">Record</a>
                    <a class="button secondary" href="/records">Records</a>
                    <a class="button secondary" href="/setup">Setup</a>
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

@app.get("/setup", response_class=HTMLResponse)
def setup_page():
    fields = list_fields(active_only=True)
    crop_years = list_crop_years()

    field_options = "".join(
        f"<option value='{field.id}'>{escape(field.field_name)}</option>"
        for field in fields
    )

    field_rows = "".join(
        f"""
        <div class="history-item">
            <strong>{escape(field.field_name)}</strong>
            <div class="file">
                Acres: {field.acres if field.acres is not None else "Unknown"}
                {f" | Farm: {escape(field.farm_name)}" if field.farm_name else ""}
            </div>
        </div>
        """
        for field in fields
    ) or '<p class="empty">No fields entered yet.</p>'

    crop_rows = "".join(
        f"""
        <div class="history-item">
            <strong>{escape(cy.field.field_name if cy.field else "Unknown field")}</strong>
            <div class="file">
                {cy.crop_year} {escape(cy.crop)}
                {f" | Variety/Hybrid: {escape(cy.variety_or_hybrid)}" if cy.variety_or_hybrid else ""}
            </div>
        </div>
        """
        for cy in crop_years
    ) or '<p class="empty">No crop years entered yet.</p>'

    body = f"""
    <div class="grid">
        <section class="card">
            <h2>Add Field</h2>
            <form action="/setup/fields" method="post">
                <label>Field name</label>
                <input name="field_name" required>

                <label>Farm name</label>
                <input name="farm_name">

                <label>Acres</label>
                <input name="acres" type="number" step="0.01">

                <label>County</label>
                <input name="county">

                <label>State</label>
                <input name="state" value="NE">

                <label>Notes</label>
                <textarea name="notes"></textarea>

                <div class="actions">
                    <button type="submit">Save Field</button>
                </div>
            </form>
        </section>

        <section class="card">
            <h2>Add Crop Year</h2>
            <form action="/setup/crop-years" method="post">
                <label>Field</label>
                <select name="field_id" required>
                    <option value="">Select field...</option>
                    {field_options}
                </select>

                <label>Crop year</label>
                <input name="crop_year" type="number" value="{date.today().year}" required>

                <label>Crop</label>
                <select name="crop" required>
                    <option value="">Select crop...</option>
                    <option value="Corn">Corn</option>
                    <option value="Soybeans">Soybeans</option>
                    <option value="Wheat">Wheat</option>
                    <option value="Alfalfa">Alfalfa</option>
                    <option value="Pasture">Pasture</option>
                    <option value="Other">Other</option>
                </select>

                <label>Variety or hybrid</label>
                <input name="variety_or_hybrid">

                <label>Planned acres</label>
                <input name="planned_acres" type="number" step="0.01">

                <label>Yield goal</label>
                <input name="yield_goal" type="number" step="0.01">

                <label>Notes</label>
                <textarea name="notes"></textarea>

                <div class="actions">
                    <button type="submit">Save Crop Year</button>
                </div>
            </form>
        </section>
    </div>

    <br>

    <div class="grid">
        <section class="card">
            <h2>Fields</h2>
            <div class="history-list">{field_rows}</div>
        </section>

        <section class="card">
            <h2>Crop Years</h2>
            <div class="history-list">{crop_rows}</div>
        </section>
    </div>
    """
    return page_shell("Setup", body)


@app.post("/setup/fields")
def setup_add_field(
    field_name: str = Form(...),
    farm_name: str = Form(""),
    acres: str = Form(""),
    county: str = Form(""),
    state: str = Form(""),
    notes: str = Form(""),
):
    create_field(
        field_name=field_name,
        farm_name=farm_name,
        acres=acres,
        county=county,
        state=state,
        notes=notes,
    )
    return RedirectResponse("/setup", status_code=303)


@app.post("/setup/crop-years")
def setup_add_crop_year(
    field_id: str = Form(...),
    crop_year: str = Form(...),
    crop: str = Form(...),
    variety_or_hybrid: str = Form(""),
    planned_acres: str = Form(""),
    yield_goal: str = Form(""),
    notes: str = Form(""),
):
    create_crop_year(
        field_id=field_id,
        crop_year=crop_year,
        crop=crop,
        variety_or_hybrid=variety_or_hybrid,
        planned_acres=planned_acres,
        yield_goal=yield_goal,
        notes=notes,
    )
    return RedirectResponse("/setup", status_code=303)


@app.get("/record", response_class=HTMLResponse)
def record_form():
    current_year = date.today().year
    crop_years = list_crop_years(year=current_year)

    crop_year_options = "".join(
        f"""
        <option value="{cy.id}">
            {escape(cy.field.field_name if cy.field else "Unknown field")} — {cy.crop_year} {escape(cy.crop)}
        </option>
        """
        for cy in crop_years
    )

    if not crop_year_options:
        crop_year_options = '<option value="">No current crop years found. Add them in Setup first.</option>'

    operation_options = "".join(
        f'<option value="{op}">{op.title()}</option>'
        for op in [
            "scouting",
            "planting",
            "spraying",
            "fertilizer",
            "tillage",
            "irrigation",
            "harvest",
            "hauling",
            "repair",
            "other",
        ]
    )

    body = f"""
    <section class="card">
        <h2>Record a field trip</h2>
        <p class="hint">
            Select the known information first. The AI will then look in your note for:
            operator, equipment, acres covered, products or inputs used, rates,
            total quantities, costs, weather, field conditions, and extra notes.
        </p>

        <form action="/record/parse" method="post" onsubmit="this.classList.add('submitting')">
            <label>Field / Crop</label>
            <select name="crop_year_id" required>
                <option value="">Select field and crop...</option>
                {crop_year_options}
            </select>

            <label>Operation date</label>
            <input name="operation_date" type="date" value="{date.today().isoformat()}" required>

            <label>Operation type</label>
            <select name="operation_type" required>
                {operation_options}
            </select>

            <label for="source_text">Field trip note</label>
            <textarea id="source_text" name="source_text" required placeholder="Example: Dad ran the sprayer. 76 acres. Liberty 32 oz/ac, Enlist 32 oz/ac, AMS 3 lb/ac, 15 GPA. Dry field, 82 degrees, light wind."></textarea>

            <div class="actions">
                <button type="submit">Create Draft Entry</button>
                <span class="loading">Parsing record...</span>
            </div>
        </form>
    </section>
    """
    return page_shell("Record Field Trip", body)


@app.post("/record/parse", response_class=HTMLResponse)
def record_parse(
    crop_year_id: str = Form(...),
    operation_date: str = Form(...),
    operation_type: str = Form(...),
    source_text: str = Form(...),
):
    cy = get_crop_year(int(crop_year_id))

    context = {
        "operation_date": operation_date,
        "operation_type": operation_type,
        "crop_year_id": cy.id if cy else None,
        "field_id": cy.field.id if cy and cy.field else None,
        "field_name": cy.field.field_name if cy and cy.field else None,
        "crop_year": cy.crop_year if cy else None,
        "crop": cy.crop if cy else None,
    }

    draft = parse_field_record(source_text.strip(), context=context)
    draft_json = json.dumps(draft, indent=2)

    warnings = draft.get("warnings") or []
    warning_html = ""
    if warnings:
        warning_items = "".join(f"<li>{escape(str(w))}</li>" for w in warnings)
        warning_html = f"<div class='history-item'><strong>Review warnings:</strong><ul>{warning_items}</ul></div>"

    body = f"""
    <section class="card">
        <h2>Review draft field record</h2>
        <p class="hint">Review carefully. Nothing is saved until you approve.</p>
        {warning_html}

        <pre>{escape(draft_json)}</pre>

        <form action="/record/save" method="post">
            <textarea name="draft_json" style="display:none">{escape(draft_json)}</textarea>
            <div class="actions">
                <button type="submit">Approve and Save</button>
                <a class="button secondary" href="/record">Discard</a>
            </div>
        </form>
    </section>
    """
    return page_shell("Review Field Record", body)


@app.post("/record/save", response_class=HTMLResponse)
def record_save(draft_json: str = Form(...)):
    draft = json.loads(draft_json)
    operation = save_approved_field_record(draft)

    body = f"""
    <section class="card">
        <h2>Field record saved</h2>
        <p>Saved operation ID: <strong>{operation.id}</strong></p>
        <p>Operation type: <strong>{escape(operation.operation_type)}</strong></p>
        <div class="actions">
            <a class="button" href="/record">Record another field trip</a>
            <a class="button secondary" href="/setup">Setup fields/crops</a>
            <a class="button secondary" href="/">Back to council</a>
        </div>
    </section>
    """
    return page_shell("Field Record Saved", body)

@app.get("/records", response_class=HTMLResponse)
def records_page():
    db = SessionLocal()
    try:
        operations = (
            db.query(FieldOperation)
            .order_by(FieldOperation.id.desc())
            .limit(50)
            .all()
        )

        rows = ""

        for op in operations:
            field_name = op.field.field_name if op.field else "Unknown field"
            crop = op.crop_year.crop if op.crop_year else "Unknown crop"

            products = ""
            for item in op.inputs:
                rate = item.rate if item.rate is not None else ""
                rate_unit = item.rate_unit or ""
                products += f"<li>{escape(item.product_name)} — {rate} {escape(rate_unit)}</li>"

            if not products:
                products = "<li>No products recorded</li>"

            rows += f"""
            <div class="history-item">
                <strong>#{op.id} — {escape(op.operation_type)} — {escape(field_name)}</strong>
                <div class="file">
                    Date: {op.operation_date or "Unknown"} |
                    Crop: {escape(crop)} |
                    Acres: {op.acres_covered if op.acres_covered is not None else "Unknown"}
                </div>
                <p><strong>Operator:</strong> {escape(op.operator or "Unknown")}</p>
                <p><strong>Equipment:</strong> {escape(op.equipment or "Unknown")}</p>
                <p><strong>Conditions:</strong> {escape(op.field_conditions or "Unknown")}</p>
                <p><strong>Weather:</strong> {escape(op.weather_notes or "Unknown")}</p>
                <p><strong>Notes:</strong> {escape(op.notes or "")}</p>
                <p><strong>Products:</strong></p>
                <ul>{products}</ul>
                <details>
                    <summary>Original text</summary>
                    <pre>{escape(op.source_text or "")}</pre>
                </details>
            </div>
            """

        if not rows:
            rows = '<p class="empty">No field records saved yet.</p>'

        body = f"""
        <section class="card">
            <h2>Saved Field Records</h2>
            <div class="history-list">
                {rows}
            </div>
        </section>
        """

        return page_shell("Saved Field Records", body)

    finally:
        db.close()