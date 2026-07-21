from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base

class Entity(Base):
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, index=True)
    entity_name = Column(String, unique=True, nullable=False)
    entity_type = Column(String, nullable=True)  # individual, LLC, partnership, trust, landlord, tenant, other
    notes = Column(Text, nullable=True)
    active = Column(Boolean, default=True)

    field_ownerships = relationship("FieldOwnership", back_populates="entity")


class FieldOwnership(Base):
    __tablename__ = "field_ownerships"

    id = Column(Integer, primary_key=True, index=True)

    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)

    ownership_percent = Column(Float, nullable=False)
    ownership_type = Column(String, nullable=True)  # owned, rented, crop_share, custom, other
    effective_start_year = Column(Integer, nullable=True)
    effective_end_year = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    field = relationship("Field", back_populates="ownerships")
    entity = relationship("Entity", back_populates="field_ownerships")

    __table_args__ = (
        UniqueConstraint("field_id", "entity_id", "effective_start_year", name="uq_field_entity_year"),
    )

class Field(Base):
    __tablename__ = "fields"

    id = Column(Integer, primary_key=True, index=True)
    field_name = Column(String, unique=True, nullable=False)
    farm_name = Column(String, nullable=True)
    acres = Column(Float, nullable=True)
    county = Column(String, nullable=True)
    state = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    active = Column(Boolean, default=True)

    # Future import/export compatibility
    external_source = Column(String, nullable=True)
    external_id = Column(String, nullable=True)
    adapt_field_id = Column(String, nullable=True)
    geometry_ref = Column(Text, nullable=True)

    crop_years = relationship("CropYear", back_populates="field")
    operations = relationship("FieldOperation", back_populates="field")
    ownerships = relationship("FieldOwnership", back_populates="field")

class CropYear(Base):
    __tablename__ = "crop_years"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False)

    crop_year = Column(Integer, nullable=False)
    crop = Column(String, nullable=False)
    variety_or_hybrid = Column(String, nullable=True)
    planned_acres = Column(Float, nullable=True)
    actual_acres = Column(Float, nullable=True)
    yield_goal = Column(Float, nullable=True)
    actual_yield = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

    field = relationship("Field", back_populates="crop_years")
    operations = relationship("FieldOperation", back_populates="crop_year")


class FieldOperation(Base):
    __tablename__ = "field_operations"

    id = Column(Integer, primary_key=True, index=True)

    field_id = Column(Integer, ForeignKey("fields.id"), nullable=True)
    crop_year_id = Column(Integer, ForeignKey("crop_years.id"), nullable=True)

    operation_date = Column(Date, nullable=True)
    operation_type = Column(String, nullable=False)
    operator = Column(String, nullable=True)
    equipment = Column(String, nullable=True)
    acres_covered = Column(Float, nullable=True)

    weather_notes = Column(Text, nullable=True)
    field_conditions = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Original spoken/typed text for audit trail
    source_text = Column(Text, nullable=False)

    # Human review control
    review_status = Column(String, default="draft")

    created_at = Column(DateTime, default=datetime.utcnow)

    # Future ADAPT compatibility
    external_source = Column(String, nullable=True)
    external_id = Column(String, nullable=True)
    adapt_work_record_id = Column(String, nullable=True)
    adapt_operation_id = Column(String, nullable=True)
    geometry_ref = Column(Text, nullable=True)

    field = relationship("Field", back_populates="operations")
    crop_year = relationship("CropYear", back_populates="operations")
    inputs = relationship("OperationInput", back_populates="operation")


class OperationInput(Base):
    __tablename__ = "operation_inputs"

    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column(Integer, ForeignKey("field_operations.id"), nullable=False)

    product_name = Column(String, nullable=False)
    product_type = Column(String, nullable=True)

    rate = Column(Float, nullable=True)
    rate_unit = Column(String, nullable=True)
    total_quantity = Column(Float, nullable=True)
    total_quantity_unit = Column(String, nullable=True)

    unit_cost = Column(Float, nullable=True)
    total_cost = Column(Float, nullable=True)

    # Future ADAPT/product mapping
    external_source = Column(String, nullable=True)
    external_product_id = Column(String, nullable=True)
    adapt_product_id = Column(String, nullable=True)

    operation = relationship("FieldOperation", back_populates="inputs")