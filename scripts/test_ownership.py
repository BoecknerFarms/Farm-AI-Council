import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.database import SessionLocal
from app.models import Field, Entity, FieldOwnership


def main():
    db = SessionLocal()

    try:
        fields = db.query(Field).order_by(Field.field_name).all()

        print("FIELDS")
        print("=" * 60)

        for field in fields:
            print(f"{field.id}: {field.field_name}")

        print()
        print("ENTITIES")
        print("=" * 60)

        entities = db.query(Entity).order_by(Entity.entity_name).all()

        for entity in entities:
            print(f"{entity.id}: {entity.entity_name} ({entity.entity_type or 'unknown'})")

        print()
        print("OWNERSHIP")
        print("=" * 60)

        ownerships = db.query(FieldOwnership).all()

        for row in ownerships:
            print(
                f"{row.field.field_name} | "
                f"{row.entity.entity_name} | "
                f"{row.ownership_percent}% | "
                f"{row.ownership_type or 'unspecified'}"
            )

    finally:
        db.close()


if __name__ == "__main__":
    main()