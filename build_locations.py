
import json
import zipfile
import urllib.request
import re

from pathlib import Path
from collections import defaultdict

# ==========================================
# SUKOON MATRIMONIAL
# Worldwide Offline Administrative Dataset
# Country > Province > District > Tehsil
# Version 2.0
# ==========================================

BASE_URL = (
    "https://download.geonames.org/export/dump/"
)

SOURCE = Path("source_data")
OUTPUT = Path("assets/locations")

SOURCE.mkdir(parents=True, exist_ok=True)
OUTPUT.mkdir(parents=True, exist_ok=True)

FILES = [
    "countryInfo.txt",
    "admin1CodesASCII.txt",
    "admin2Codes.txt",
    "allCountries.zip",
]

# ==========================================
# DOWNLOAD ORIGINAL DATA
# ==========================================

for filename in FILES:

    destination = SOURCE / filename

    if not destination.exists():

        print(
            "Downloading:", filename,
            flush=True
        )

        temporary = SOURCE / (filename + ".part")

        urllib.request.urlretrieve(
            BASE_URL + filename,
            temporary
        )

        temporary.replace(destination)

    print("Available:", filename, flush=True)


# ==========================================
# STORAGE
# ==========================================

countries = {}
provinces = defaultdict(dict)
districts = defaultdict(dict)
tehsils = defaultdict(dict)


# ==========================================
# INTERNATIONAL DIALING CODES
# ==========================================

def normalize_dial_codes(value):

    result = []

    for item in re.split(r"[,/;]", value):

        digits = re.sub(r"[^0-9]", "", item)

        if not digits:
            continue

        # North American Numbering Plan
        # Keep the international calling code
        # separate from the local area code.

        if len(digits) == 4 and digits.startswith("1"):
            digits = "1"

        code = "+" + digits

        if code not in result:
            result.append(code)

    return result


# ==========================================
# LOAD COUNTRIES
# ==========================================

with open(
    SOURCE / "countryInfo.txt",
    encoding="utf-8"
) as file:

    for line in file:

        if line.startswith("#"):
            continue

        if not line.strip():
            continue

        row = line.rstrip("\r\n").split("\t")

        if len(row) < 19:
            continue

        iso = row[0].strip()

        # Exclude obsolete country entries.

        if iso in ("AN", "CS"):
            continue

        dial_codes = normalize_dial_codes(row[12])

        countries[iso] = {
            "id": iso,
            "code": iso,
            "iso2": iso,
            "iso3": row[1],
            "numeric_code": row[2],
            "name": row[4],
            "capital": row[5],
            "continent": row[8],
            "currency": row[10],
            "dial": (
                dial_codes[0]
                if dial_codes else ""
            ),
            "dial_codes": dial_codes,
            "dial_source": row[12],
            "geoname_id": row[16]
        }

print(
    "Countries loaded:",
    len(countries),
    flush=True
)


# ==========================================
# LOAD PROVINCES / STATES
# ==========================================

with open(
    SOURCE / "admin1CodesASCII.txt",
    encoding="utf-8"
) as file:

    for line in file:

        row = line.rstrip("\r\n").split("\t")

        if len(row) < 4:
            continue

        parts = row[0].split(".")

        if len(parts) != 2:
            continue

        country, province = parts

        if country not in countries:
            continue

        full_code = f"{country}.{province}"

        provinces[country][full_code] = {
            "id": full_code,
            "code": full_code,
            "local_code": province,
            "name": row[1],
            "ascii_name": row[2],
            "country_code": country,
            "geoname_id": row[3],
            "level": 1
        }


# ==========================================
# LOAD DISTRICTS
# ==========================================

with open(
    SOURCE / "admin2Codes.txt",
    encoding="utf-8"
) as file:

    for line in file:

        row = line.rstrip("\r\n").split("\t")

        if len(row) < 4:
            continue

        parts = row[0].split(".")

        if len(parts) != 3:
            continue

        country, province, district = parts

        if country not in countries:
            continue

        province_code = f"{country}.{province}"

        district_code = (
            f"{country}.{province}.{district}"
        )

        districts[country][district_code] = {
            "id": district_code,
            "code": district_code,
            "local_code": district,
            "name": row[1],
            "ascii_name": row[2],
            "country_code": country,
            "province_code": province_code,
            "geoname_id": row[3],
            "level": 2
        }


# ==========================================
# EXTRACT ADMINISTRATIVE LEVELS
# ==========================================

processed = 0
missing_codes = 0

with zipfile.ZipFile(
    SOURCE / "allCountries.zip"
) as archive:

    with archive.open("allCountries.txt") as file:

        for raw in file:

            row = raw.decode("utf-8").rstrip(
                "\r\n"
            ).split("\t")

            if len(row) < 19:
                continue

            feature_class = row[6]
            feature_code = row[7]

            # Administrative regions only.

            if feature_class != "A":
                continue

            if feature_code not in (
                "ADM1",
                "ADM2",
                "ADM3"
            ):
                continue

            country = row[8]
            province = row[10]
            district = row[11]
            tehsil = row[12]

            if country not in countries:
                continue

            name = row[1]
            ascii_name = row[2]
            geoname_id = row[0]

            province_code = (
                f"{country}.{province}"
            )

            district_code = (
                f"{country}.{province}.{district}"
            )

            tehsil_code = (
                f"{country}.{province}."
                f"{district}.{tehsil}"
            )

            # Preserve records with missing codes
            # using their GeoNames ID.

            if feature_code == "ADM1":

                if not province:
                    province_code = (
                        f"{country}.GN{geoname_id}"
                    )
                    missing_codes += 1

                provinces[country][province_code] = {
                    "id": province_code,
                    "code": province_code,
                    "local_code": province,
                    "name": name,
                    "ascii_name": ascii_name,
                    "country_code": country,
                    "geoname_id": geoname_id,
                    "level": 1
                }

            elif feature_code == "ADM2":

                if not district:
                    district_code = (
                        f"{province_code}.GN{geoname_id}"
                    )
                    missing_codes += 1

                districts[country][district_code] = {
                    "id": district_code,
                    "code": district_code,
                    "local_code": district,
                    "name": name,
                    "ascii_name": ascii_name,
                    "country_code": country,
                    "province_code": province_code,
                    "geoname_id": geoname_id,
                    "level": 2
                }

            elif feature_code == "ADM3":

                if not tehsil:
                    tehsil_code = (
                        f"{district_code}.GN{geoname_id}"
                    )
                    missing_codes += 1

                tehsils[country][tehsil_code] = {
                    "id": tehsil_code,
                    "code": tehsil_code,
                    "local_code": tehsil,
                    "name": name,
                    "ascii_name": ascii_name,
                    "country_code": country,
                    "province_code": province_code,
                    "district_code": district_code,
                    "geoname_id": geoname_id,
                    "level": 3
                }

            processed += 1

            if processed % 10000 == 0:

                print(
                    "Administrative records:",
                    processed,
                    flush=True
                )


# ==========================================
# JSON WRITER
# ==========================================

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


def sort_records(records):

    return sorted(
        records,
        key=lambda item: (
            item["name"].casefold(),
            item["code"]
        )
    )


# ==========================================
# BUILD COUNTRY FILES
# ==========================================

total_provinces = 0
total_districts = 0
total_tehsils = 0

unlinked_districts = 0
unlinked_tehsils = 0

country_index = []

for country_code in sorted(countries):

    country = countries[country_code]

    province_list = sort_records(
        provinces[country_code].values()
    )

    district_list = sort_records(
        districts[country_code].values()
    )

    tehsil_list = sort_records(
        tehsils[country_code].values()
    )

    province_ids = {
        item["code"]
        for item in province_list
    }

    district_ids = {
        item["code"]
        for item in district_list
    }

    districts_by_province = defaultdict(list)
    tehsils_by_district = defaultdict(list)

    orphan_districts = []
    orphan_tehsils = []

    for district in district_list:

        parent = district["province_code"]

        if parent in province_ids:

            districts_by_province[parent].append(
                district
            )

        else:

            orphan_districts.append(district)

    for tehsil in tehsil_list:

        parent = tehsil["district_code"]

        if parent in district_ids:

            tehsils_by_district[parent].append(
                tehsil
            )

        else:

            orphan_tehsils.append(tehsil)

    country_data = {
        "schema_version": 2,
        "country": country,
        "provinces": province_list,
        "districts": dict(
            districts_by_province
        ),
        "tehsils": dict(
            tehsils_by_district
        ),
        "unlinked_districts": orphan_districts,
        "unlinked_tehsils": orphan_tehsils,
        "counts": {
            "provinces": len(province_list),
            "districts": len(district_list),
            "tehsils": len(tehsil_list)
        }
    }

    save_json(
        country_code + ".json",
        country_data
    )

    country_index.append({
        **country,
        "file": country_code + ".json",
        "has_provinces": bool(province_list),
        "has_districts": bool(district_list),
        "has_tehsils": bool(tehsil_list),
        "counts": country_data["counts"]
    })

    total_provinces += len(province_list)
    total_districts += len(district_list)
    total_tehsils += len(tehsil_list)

    unlinked_districts += len(orphan_districts)
    unlinked_tehsils += len(orphan_tehsils)

    print(
        country_code,
        "| Provinces:", len(province_list),
        "| Districts:", len(district_list),
        "| Tehsils:", len(tehsil_list),
        flush=True
    )


# ==========================================
# COUNTRY INDEX
# ==========================================

save_json(
    "countries.json",
    sort_records(country_index)
)


# ==========================================
# COUNTRY DIALING CODE INDEX
# ==========================================

dialing_codes = {}

for code, country in countries.items():

    dialing_codes[code] = {
        "name": country["name"],
        "dial": country["dial"],
        "dial_codes": country["dial_codes"]
    }

save_json(
    "dialing_codes.json",
    dialing_codes
)


# ==========================================
# DATASET SUMMARY
# ==========================================

summary = {
    "app": "Sukoon Matrimonial",
    "schema_version": 2,
    "source": "GeoNames",
    "license": "CC BY 4.0",
    "countries": len(countries),
    "provinces": total_provinces,
    "districts": total_districts,
    "tehsils": total_tehsils,
    "unlinked_districts": unlinked_districts,
    "unlinked_tehsils": unlinked_tehsils,
    "records_with_missing_codes": missing_codes,
    "countries_without_dial_code": [
        code for code, item in countries.items()
        if not item["dial"]
    ],
    "administrative_levels": [
        "Country",
        "ADM1",
        "ADM2",
        "ADM3"
    ],
    "populated_places_included": False
}

save_json(
    "dataset_summary.json",
    summary
)


# ==========================================
# ATTRIBUTION
# ==========================================

(OUTPUT / "ATTRIBUTION.txt").write_text(
    "Source: GeoNames\n"
    "https://www.geonames.org/\n"
    "License: Creative Commons Attribution 4.0\n"
    "https://creativecommons.org/licenses/by/4.0/\n"
    "Filtered and converted to JSON for "
    "Sukoon Matrimonial.\n"
    "Includes ADM1, ADM2 and ADM3 records.\n",
    encoding="utf-8"
)


# ==========================================
# FINAL REPORT
# ==========================================

print("\n=================================")
print("SUKOON OFFLINE LOCATION DATASET")
print("=================================")

print(
    json.dumps(
        summary,
        indent=2,
        ensure_ascii=False
    )
)

print("Output directory:", OUTPUT)
print("Dataset generation completed.")
