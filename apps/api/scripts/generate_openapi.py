import json
import os
import sys

# Ensure retriever apps/api directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.main import app


def generate_openapi():
    openapi_schema = app.openapi()

    # Ensure docs directory exists
    docs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", "docs"))
    os.makedirs(docs_dir, exist_ok=True)

    openapi_path = os.path.join(docs_dir, "openapi.json")
    with open(openapi_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)
    print(f"Successfully generated OpenAPI schema at: {openapi_path}")


if __name__ == "__main__":
    generate_openapi()
