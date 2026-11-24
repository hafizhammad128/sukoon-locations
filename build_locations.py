
import json
import zipfile
import urllib.request

from pathlib import Path
from collections import defaultdict

BASE = "https://download.geonames.org/export/dump/"

SOURCE = Path("source_data")
OUTPUT = Path("assets/locations")

SOURCE.mkdir(parents=True, exist_ok=True)
OUTPUT.mkdir(parents=True, exist_ok=True)

FILES = [
    "countryInfo.txt",
    "admin1CodesASCII.txt",
    "allCountries.zip"
]

# Download original GeoNames datasets

for name in FILES:
    path = SOURCE / name

    if not path.exists():
        print("Downloading:", name, flush=True)

        temp = path.with_suffix(
            path.suffix + ".part"
        )

        urllib.request.urlretrieve(
            BASE + name,
            temp
        )

        temp.replace(path)

    print("Available:", name, flush=True)


countries = {}
states = defaultdict(dict)
cities = defaultdict(
    lambda: defaultdict(list)
)


# Countries and international dialing codes

with open(
    SOURCE / "countryInfo.txt",
    encoding="utf-8"
) as file:

    for line in file:

        if line.startswith("#") or not line.strip():
            continue

        row = line.rstrip("\n").split("\t")

        if len(row) < 13:
            continue

        code = row[0]

        if code in ("AN", "CS"):
            continue

        countries[code] = {
            "code": code,
            "name": row[4],
            "dial": row[12]
        }

print("Countries loaded:", len(countries))


# Provinces and states

with open(
    SOURCE / "admin1CodesASCII.txt",
    encoding="utf-8"
) as file:

    for line in file:

        row = line.rstrip("\n").split("\t")

        if len(row) < 2 or "." not in row[0]:
            continue

        country, state = row[0].split(".", 1)

        states[country][state] = row[1]


# Cities and populated places

count = 0

with zipfile.ZipFile(
    SOURCE / "allCountries.zip"
) as archive:

    with archive.open("allCountries.txt") as file:

        for raw in file:

            row = raw.decode("utf-8").rstrip(
                "\n"
            ).split("\t")

            if len(row) < 19:
                continue

            if row[6] != "P":
                continue

            if row[7] in ("PPLQ", "PPLH", "PPLW"):
                continue

            country = row[8]
            state = row[10] or "00"

            if country not in countries:
                continue

            states[country].setdefault(
                state,
                "Other / Unspecified"
                if state == "00"
                else state
            )

            cities[country][state].append({
                "id": row[0],
                "name": row[1]
            })

            count += 1

            if count % 100000 == 0:
                print(
                    "Locations processed:",
                    count,
                    flush=True
                )


# Save compact JSON files

def save_json(filename, data):

    with open(
        OUTPUT / filename,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            separators=(",", ":")
        )


# Save all countries

save_json(
    "countries.json",
    sorted(
        countries.values(),
        key=lambda item: item["name"]
    )
)


# Save separate data file for every country

for code in countries:

    for items in cities[code].values():

        items.sort(
            key=lambda item:
            item["name"].casefold()
        )

    save_json(
        code + ".json",
        {
            "states": states[code],
            "cities": cities[code]
        }
    )


# GeoNames attribution

(OUTPUT / "ATTRIBUTION.txt").write_text(
    "Source: GeoNames\n"
    "https://www.geonames.org/\n"
    "License: CC BY 4.0\n"
    "Filtered and converted to JSON "
    "for Sukoon Matrimonial.\n",
    encoding="utf-8"
)


print("--------------------------------")
print("Sukoon Location Dataset")
print("Countries:", len(countries))
print("Populated places:", count)
print("Output:", OUTPUT)
print("Dataset generation completed.")
print("--------------------------------")
