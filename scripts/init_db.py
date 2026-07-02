import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.database import Base, engine
from app import models


def main():
    Base.metadata.create_all(bind=engine)
    print("Database initialized: data/farm_ai.db")


if __name__ == "__main__":
    main()