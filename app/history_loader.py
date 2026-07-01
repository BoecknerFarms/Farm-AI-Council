from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HISTORY_FOLDERS = [
    ROOT / "conversations",
    ROOT / "reports",
    ROOT / "knowledge" / "farm_history",
]


def load_recent_history(max_chars: int = 8000) -> str:
    collected = []

    for folder in HISTORY_FOLDERS:
        if not folder.exists():
            continue

        files = sorted(
            list(folder.glob("*.md")) + list(folder.glob("*.txt")),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        for file in files:
            try:
                text = file.read_text(encoding="utf-8")
                collected.append(f'--- Source: {file.name} ---\n{text}')
            except Exception:
                continue

    combined = "\n\n".join(collected)

    if not combined.strip():
        return "No prior history files found."

    return combined[:max_chars]
