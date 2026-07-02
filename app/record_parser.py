import json
from datetime import date

from app.ollama_client import ask_model


RECORD_EXTRACTION_PROMPT = """
You convert a farmer's plain-language field note into structured JSON for a farm management database.

Use provided form context as authoritative. If the form context gives operation_date, field_name, crop_year, crop, or operation_type, keep those values unless the user's note clearly corrects a mistake.

Extract only what the user actually said or what is safely implied. Do not invent missing values.
If a value is unknown, use null. Return JSON only. No markdown. No commentary.

Fields to extract or preserve:
- operation_date: ISO date YYYY-MM-DD
- field_id: database field id if provided by context
- crop_year_id: database crop year id if provided by context
- field_name: field name or number
- crop_year: numeric crop year
- crop: corn, soybeans, wheat, alfalfa, pasture, etc.
- operation_type: planting, spraying, fertilizer, tillage, scouting, harvest, hauling, irrigation, repair, other
- operator: person who did the work
- equipment: tractor, sprayer, planter, combine, applicator, tender, implement, etc.
- acres_covered: number of acres covered
- field_conditions: soil/field condition notes such as wet, dry, muddy, crusted, compacted, rutted
- weather_notes: temperature, wind, rain, humidity, forecast, or other weather details
- notes: useful details that do not fit elsewhere
- products: list of products or inputs used. For each product extract:
  - product_name
  - product_type: seed, fertilizer, herbicide, fungicide, insecticide, adjuvant, fuel, other
  - rate
  - rate_unit
  - total_quantity
  - total_quantity_unit
  - unit_cost
  - total_cost
- warnings: list of problems, uncertainties, or missing details the user should review before saving

Output exactly this JSON shape:
{
  "operation_date": null,
  "field_id": null,
  "crop_year_id": null,
  "field_name": null,
  "crop_year": null,
  "crop": null,
  "operation_type": "other",
  "operator": null,
  "equipment": null,
  "acres_covered": null,
  "field_conditions": null,
  "weather_notes": null,
  "notes": null,
  "products": [],
  "warnings": []
}
"""


def parse_field_record(source_text: str, context: dict | None = None, model: str = "qwen3:8b") -> dict:
    context = context or {}
    user_prompt = f"""
Today's date is {date.today().isoformat()}.

Form context selected by the user:
{json.dumps(context, indent=2)}

Farmer's field note:
{source_text}

Create the structured JSON draft now.
"""
    raw = ask_model(
        model=model,
        system_prompt=RECORD_EXTRACTION_PROMPT,
        user_prompt=user_prompt,
    )

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    try:
        draft = json.loads(cleaned)
    except json.JSONDecodeError:
        draft = {
            "operation_date": context.get("operation_date"),
            "field_id": context.get("field_id"),
            "crop_year_id": context.get("crop_year_id"),
            "field_name": context.get("field_name"),
            "crop_year": context.get("crop_year"),
            "crop": context.get("crop"),
            "operation_type": context.get("operation_type") or "other",
            "operator": None,
            "equipment": None,
            "acres_covered": None,
            "field_conditions": None,
            "weather_notes": None,
            "notes": cleaned,
            "products": [],
            "warnings": ["AI response was not valid JSON. Review the notes before saving."],
        }

    # Enforce selected form context unless missing from draft.
    for key in ["operation_date", "field_id", "crop_year_id", "field_name", "crop_year", "crop", "operation_type"]:
        if context.get(key) not in (None, ""):
            draft[key] = context.get(key)

    draft["source_text"] = source_text
    return draft
