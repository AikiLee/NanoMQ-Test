import json
from pathlib import Path
from typing import Any

from jsonschema import validate


SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"


def load_schema(schema_name: str) -> dict[str, Any]:
    schema_path = SCHEMA_DIR / schema_name
    with schema_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def validate_schema(payload: object, schema_name: str) -> None:
    validate(instance=payload, schema=load_schema(schema_name))
