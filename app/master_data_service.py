from datetime import date
from app.database import SessionLocal
from sqlalchemy.orm import joinedload
from app.models import Field, CropYear


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


def list_fields(active_only: bool = True):
    db = SessionLocal()
    try:
        query = db.query(Field)
        if active_only:
            query = query.filter(Field.active == True)
        return query.order_by(Field.field_name).all()
    finally:
        db.close()


def create_field(field_name: str, farm_name: str = "", acres: str = "", county: str = "", state: str = "", notes: str = ""):
    db = SessionLocal()
    try:
        clean_name = field_name.strip()
        existing = db.query(Field).filter(Field.field_name == clean_name).first()
        if existing:
            return existing

        field = Field(
            field_name=clean_name,
            farm_name=farm_name.strip() or None,
            acres=_to_float(acres),
            county=county.strip() or None,
            state=state.strip() or None,
            notes=notes.strip() or None,
            active=True,
        )
        db.add(field)
        db.commit()
        db.refresh(field)
        return field
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def list_crop_years(year: int | None = None):
    db = SessionLocal()
    try:
        query = db.query(CropYear).options(joinedload(CropYear.field)).join(Field)
        if year:
            query = query.filter(CropYear.crop_year == year)
        return query.order_by(Field.field_name, CropYear.crop_year.desc()).all()
    finally:
        db.close()


def get_crop_year(crop_year_id: int):
    db = SessionLocal()
    try:
        row = db.query(CropYear).options(joinedload(CropYear.field)).filter(CropYear.id == crop_year_id).first()
        if row:
            # load relationship before closing db
            _ = row.field.field_name if row.field else None
        return row
    finally:
        db.close()


def create_crop_year(field_id: str, crop_year: str, crop: str, variety_or_hybrid: str = "", planned_acres: str = "", yield_goal: str = "", notes: str = ""):
    db = SessionLocal()
    try:
        field_id_int = _to_int(field_id)
        crop_year_int = _to_int(crop_year)
        clean_crop = crop.strip()

        existing = (
            db.query(CropYear)
            .filter(
                CropYear.field_id == field_id_int,
                CropYear.crop_year == crop_year_int,
                CropYear.crop == clean_crop,
            )
            .first()
        )
        if existing:
            return existing

        field = db.query(Field).filter(Field.id == field_id_int).first()
        planned = _to_float(planned_acres)
        if planned is None and field:
            planned = field.acres

        crop_year_row = CropYear(
            field_id=field_id_int,
            crop_year=crop_year_int,
            crop=clean_crop,
            variety_or_hybrid=variety_or_hybrid.strip() or None,
            planned_acres=planned,
            yield_goal=_to_float(yield_goal),
            notes=notes.strip() or None,
        )
        db.add(crop_year_row)
        db.commit()
        db.refresh(crop_year_row)
        return crop_year_row
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
