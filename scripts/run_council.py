import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.orchestrator import run_council


def main():
    print("Farm AI Council")
    print("Agents: Historian, Agronomist, Managing Agent")
    print()

    question = input("Question: ").strip()

    if not question:
        print("No question entered.")
        return

    result = run_council(question=question)

   
    print()
    print("=" * 80)
    print("HISTORIAN")
    print("=" * 80)
    print(result["historian"])

    print()
    print("=" * 80)
    print("AGRONOMIST")
    print("=" * 80)
    print(result["agronomist"])

    print()
    print("=" * 80)
    print("MANAGING AGENT FINAL DECISION")
    print("=" * 80)
    print(result["manager"])

    print()
    print("Saved conversation and report.")


if __name__ == "__main__":
    main()