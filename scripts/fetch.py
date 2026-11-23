"""Download the newest public files from the Franklin County Auditor into data/raw.

The auditor publishes monthly appraisal and tax-accounting extracts, and nightly GIS shapes, at
apps.franklincountyauditor.com. This finds the newest folders, downloads the tab-delimited zips and the parcel
polygons, and unzips only what the pipeline reads.

Run: python scripts/fetch.py
"""
from __future__ import annotations

import json
import re
import zipfile
from datetime import date
from pathlib import Path
from urllib.parse import quote, unquote

import requests

BASE = "https://apps.franklincountyauditor.com"
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
HEADERS = {"User-Agent": "square-deal data refresh (https://github.com/ajthakkar/square-deal)"}
APPRAISAL_FILES = ["Parcel.txt", "Dwelling.txt", "Sales010.txt", "Sales020-277.txt", "Sales410-610.txt"]
TAX_FILES = ["Value.txt", "Parcel.txt", "TaxDetail.txt", "Transfer010.txt", "Transfer020-277.txt", "Transfer410-610.txt"]


def listing(path: str) -> list[str]:
    """Entries of an IIS directory page, as decoded paths."""
    html = requests.get(f"{BASE}{quote(path)}", headers=HEADERS, timeout=60).text
    return [unquote(h) for h in re.findall(r'HREF="([^"]+)"', html, flags=re.I)]


def newest(path: str, suffix: str) -> str:
    """The newest 'YYYY-MM-DD <suffix>' folder under `path`, looking in this year's folder, then last year's."""
    for year in (date.today().year, date.today().year - 1):
        found = sorted(e for e in listing(f"{path}{year}/") if e.rstrip("/").endswith(suffix))
        if found:
            return found[-1]
    raise RuntimeError(f"No '{suffix}' folder found under {path}")


def download(url_path: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(f"{BASE}{quote(url_path)}", headers=HEADERS, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    return dest


def extract(zip_path: Path, names: list[str] | None, dest: Path) -> None:
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            base = Path(info.filename).name
            if names is None or base in names:
                info.filename = base
                z.extract(info, dest)


def main():
    appraisal = newest("/Outside_User_Files/", "Appraisal")
    tax = newest("/Outside_User_Files/", "Tax Accounting")
    gis = next(e for e in listing("/GIS_Shapefiles/CurrentExtracts/") if e.endswith("_Parcel_Polygons.zip"))
    print("appraisal:", appraisal, "\ntax:", tax, "\ngis:", gis)

    z = download(f"{appraisal.rstrip('/')}/Tab-Delimited.zip", RAW / "tab.zip")
    extract(z, APPRAISAL_FILES, RAW)
    z = download(f"{tax.rstrip('/')}/Tab-Delimited.zip", RAW / "tax.zip")
    extract(z, TAX_FILES, RAW / "tax")
    z = download(gis, RAW / "parcels.zip")
    with zipfile.ZipFile(z) as zf:
        for info in zf.infolist():
            if Path(info.filename).suffix.lower() in {".shp", ".shx", ".dbf", ".prj"}:
                info.filename = Path(info.filename).name
                zf.extract(info, RAW / "gis")

    stamp = lambda p: re.search(r"(\d{4}-\d{2}-\d{2})", p).group(1)
    (RAW / "source.json").write_text(json.dumps({
        "appraisal": appraisal, "tax_accounting": tax, "parcel_polygons": gis,
        "appraisal_date": stamp(appraisal), "fetched": date.today().isoformat()}, indent=2))


if __name__ == "__main__":
    main()
