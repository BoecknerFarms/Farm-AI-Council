import yaml
from pathlib import Path
from datetime import datetime

from app.ollama_client import ask_model
from app.history_loader import load_recent_history


ROOT = Path(__file__).resolve().parents[1]


def load_agent(agent_file: str) -> dict:
    path = ROOT / "agents" / agent_file
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_system_prompt(agent: dict) -> str:
    return f"""
Agent name: {agent["name"]}

Role:
{agent["role"]}

Required output format:
{agent["output_format"]}
"""


def clean_filename_part(value: str) -> str:
    if not value:
        return "general"

    cleaned = value.strip().replace(" ", "_")

    for char in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
        cleaned = cleaned.replace(char, "")

    return cleaned or "general"


def save_run(
    question: str,
    historian_response: str,
    agronomist_response: str,
    manager_response: str,
    field: str = "",
    crop: str = "",
    decision_type: str = "",
) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    field_value = field if field else "Unknown"
    crop_value = crop if crop else "Unknown"
    decision_type_value = decision_type if decision_type else "Unknown"

    field_for_filename = clean_filename_part(field_value)

    conversation_path = ROOT / "conversations" / f"{timestamp}_{field_for_filename}_conversation.md"
    report_path = ROOT / "reports" / f"{timestamp}_{field_for_filename}_manager_report.md"

    metadata_block = f"""```yaml
Date: {timestamp}
Question: {question}
Field: {field_value}
Crop: {crop_value}
Decision Type: {decision_type_value}
Risk Level: Unknown
Outcome Recorded: No
```"""

    conversation = f"""# Farm AI Council Conversation

## Metadata

{metadata_block}

## Question

{question}

## Historian

{historian_response}

## Agronomist

{agronomist_response}

## Managing Agent

{manager_response}
"""

    report = f"""# Farm AI Council Report

## Metadata

{metadata_block}

## Final Recommendation

{manager_response}

## Supporting Inputs

### Historian

{historian_response}

### Agronomist

{agronomist_response}
"""

    conversation_path.write_text(conversation, encoding="utf-8")
    report_path.write_text(report, encoding="utf-8")


def run_council(
    question: str,
    field: str = "",
    crop: str = "",
    decision_type: str = "",
) -> dict:
    historian = load_agent("historian.yaml")
    agronomist = load_agent("agronomist.yaml")
    manager = load_agent("manager.yaml")

    history = load_recent_history()

    historian_prompt = f"""
Current farm question:
{question}

Field:
{field if field else "Unknown"}

Crop:
{crop if crop else "Unknown"}

Decision type:
{decision_type if decision_type else "Unknown"}

Available prior history:
{history}

Review the available history and identify anything relevant.
"""

    historian_response = ask_model(
        model=historian["model"],
        system_prompt=build_system_prompt(historian),
        user_prompt=historian_prompt,
    )

    agronomist_prompt = f"""
Current farm question:
{question}

Field:
{field if field else "Unknown"}

Crop:
{crop if crop else "Unknown"}

Decision type:
{decision_type if decision_type else "Unknown"}

Relevant history from historian:
{historian_response}

Give your agronomy analysis.
"""

    agronomist_response = ask_model(
        model=agronomist["model"],
        system_prompt=build_system_prompt(agronomist),
        user_prompt=agronomist_prompt,
    )

    manager_prompt = f"""
Farm scenario or question:
{question}

Field:
{field if field else "Unknown"}

Crop:
{crop if crop else "Unknown"}

Decision type:
{decision_type if decision_type else "Unknown"}

Historian response:
{historian_response}

Agronomist response:
{agronomist_response}

Now make the final farm management decision.
"""

    manager_response = ask_model(
        model=manager["model"],
        system_prompt=build_system_prompt(manager),
        user_prompt=manager_prompt,
    )

    save_run(
        question=question,
        historian_response=historian_response,
        agronomist_response=agronomist_response,
        manager_response=manager_response,
        field=field,
        crop=crop,
        decision_type=decision_type,
    )

    return {
        "question": question,
        "field": field,
        "crop": crop,
        "decision_type": decision_type,
        "historian": historian_response,
        "agronomist": agronomist_response,
        "manager": manager_response,
    }