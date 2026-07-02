from datetime import date
from typing import Optional

from app.database import SessionLocal
from app.models import Field, CropYear, FieldOperation, OperationInput


def _to_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def get_or_create_field(db, field_name: Optional[str]) -> Optional[Field]:
    if not field_name:
        return None

    clean_name = field_name.strip()
    if not clean_name:
        return None

    field = db.query(Field).filter(Field.field_name == clean_name).first()
    if field:
        return field

    field = Field(field_name=clean_name, active=True)
    db.add(field)
    db.flush()
    return field


def get_or_create_crop_year(db, field: Optional[Field], crop_year: Optional[int], crop: Optional[str]) -> Optional[CropYear]:
    if not field or not crop_year or not crop:
        return None

    crop_year_row = (
        db.query(CropYear)
        .filter(
            CropYear.field_id == field.id,
            CropYear.crop_year == crop_year,
            CropYear.crop == crop,
        )
        .first()
    )
    if crop_year_row:
        return crop_year_row

    crop_year_row = CropYear(
        field_id=field.id,
        crop_year=crop_year,
        crop=crop,
        planned_acres=field.acres,
    )
    db.add(crop_year_row)
    db.flush()
    return crop_year_row


def save_approved_field_record(draft: dict) -> FieldOperation:
    db = SessionLocal()
    try:
        field = None
        crop_year = None

        field_id = _to_int(draft.get("field_id"))
        crop_year_id = _to_int(draft.get("crop_year_id"))

        if field_id:
            field = db.query(Field).filter(Field.id == field_id).first()
        if crop_year_id:
            crop_year = db.query(CropYear).filter(CropYear.id == crop_year_id).first()
            if crop_year and not field:
                field = crop_year.field

        if not field:
            field = get_or_create_field(db, draft.get("field_name"))

        if not crop_year:
            crop_year = get_or_create_crop_year(
                db=db,
                field=field,
                crop_year=_to_int(draft.get("crop_year")),
                crop=draft.get("crop"),
            )

        operation = FieldOperation(
            field_id=field.id if field else None,
            crop_year_id=crop_year.id if crop_year else None,
            operation_date=_to_date(draft.get("operation_date")),
            operation_type=draft.get("operation_type") or "other",
            operator=draft.get("operator"),
            equipment=draft.get("equipment"),
            acres_covered=_to_float(draft.get("acres_covered")),
            weather_notes=draft.get("weather_notes"),
            field_conditions=draft.get("field_conditions"),
            notes=draft.get("notes"),
            source_text=draft.get("source_text") or "",
            review_status="approved",
        )
        db.add(operation)
        db.flush()

        for product in draft.get("products") or []:
            if not product.get("product_name"):
                continue
            db.add(
                OperationInput(
                    operation_id=operation.id,
                    product_name=product.get("product_name"),
                    product_type=product.get("product_type"),
                    rate=_to_float(product.get("rate")),
                    rate_unit=product.get("rate_unit"),
                    total_quantity=_to_float(product.get("total_quantity")),
                    total_quantity_unit=product.get("total_quantity_unit"),
                    unit_cost=_to_float(product.get("unit_cost")),
                    total_cost=_to_float(product.get("total_cost")),
                )
            )

        db.commit()
        db.refresh(operation)
        return operation
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
