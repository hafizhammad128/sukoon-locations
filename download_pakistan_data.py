
import json
import urllib.request
from pathlib import Path

BASE_URL = (
    "https://raw.githubusercontent.com/"
    "open-admin-data/"
    "pakistan-administrative-divisions/"
    "main/data/"
)

OUTPUT = Path("source_data/pakistan")
OUTPUT.mkdir(parents=True, exist_ok=True)

FILES = {
    "all-province.json": 7,
    "all-district.json": 160,
    "all-tehsil.json": 577,
}

for filename, expected in FILES.items():
    print("Downloading:", filename, flush=True)

    with urllib.request.urlopen(
        BASE_URL + filename,
        timeout=120
    ) as response:
        data = json.load(response)

    if not isinstance(data, list):
        raise ValueError(
            f"Invalid format: {filename}"
        )

    if len(data) < expected:
        raise ValueError(
            f"Incomplete dataset: {filename}"
        )

    ids = [str(item["id"]) for item in data]

    if len(ids) != len(set(ids)):
        raise ValueError(
            f"Duplicate IDs: {filename}"
        )

    destination = OUTPUT / filename

    destination.write_text(
        json.dumps(data, ensure_ascii=False),
        encoding="utf-8"
    )

    print(
        filename,
        "Records:",
        len(data),
        flush=True
    )

print("Pakistan source data downloaded.")
