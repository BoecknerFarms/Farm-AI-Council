from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

from app.orchestrator import run_council

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
    <body>
        <h1>Farm AI Council</h1>

        <form action="/ask" method="post">
            <textarea name="question" rows="6" cols="80"></textarea>
            <br><br>
            <button type="submit">Ask Council</button>
        </form>
    </body>
    </html>
    """

@app.post("/ask", response_class=HTMLResponse)
def ask(question: str = Form(...)):
    result = run_council(question)

    return f"""
    <html>
    <body>
        <h1>Farm AI Council</h1>

        <h2>Question</h2>
        <pre>{question}</pre>

        <h2>Historian</h2>
        <pre>{result['historian']}</pre>

        <h2>Agronomist</h2>
        <pre>{result['agronomist']}</pre>

        <h2>Manager</h2>
        <pre>{result['manager']}</pre>

        <br>
        <a href="/">Ask another question</a>
    </body>
    </html>
    """