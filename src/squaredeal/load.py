"""Read the Franklin County Auditor's public files (tab-delimited extracts and parcel shapes).

Layout under data/raw (scripts/fetch.py downloads it):
  Parcel.txt, Dwelling.txt, Sales*.txt       appraisal extract
  tax/Value.txt, tax/Parcel.txt, tax/TaxDetail.txt   tax-accounting extract
  gis/TAXPARCEL_*.shp/.shx/.dbf               parcel polygons (Ohio State Plane South, US feet)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ID = "PARCEL ID"


def _read(path: Path, usecols: list[str]) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t", dtype=str, encoding="utf-8-sig", usecols=lambda c: c.strip() in usecols,
                     keep_default_na=False, na_values=[""], quoting=0)
    df.columns = [c.strip() for c in df.columns]
    return df


def parcels(raw: Path) -> pd.DataFrame:
    cols = [ID, "ADRNOLOW", "ADRNOHIGH", "ADRDIR", "ADRSTR", "ADRSUF", "ADRSUF2", "UNITNO", "NBHD", "LUC",
            "COSTTOT", "CARDS", "ACRES", "CALCACRES"]
    df = _read(raw / "Parcel.txt", cols)
    df["value_2026"] = pd.to_numeric(df["COSTTOT"], errors="coerce")
    df["cards"] = pd.to_numeric(df["CARDS"], errors="coerce")
    acres = pd.to_numeric(df["ACRES"], errors="coerce")
    calc = pd.to_numeric(df["CALCACRES"], errors="coerce")
    df["acres"] = acres.where(acres > 0, calc)
    return df.drop(columns=["COSTTOT", "CARDS", "ACRES", "CALCACRES"]).drop_duplicates(ID)


def dwellings(raw: Path) -> pd.DataFrame:
    cols = [ID, "CARD", "RMBED", "FIXBATH", "FIXHALF", "STYLE", "STORIES", "BSMT", "FINBSMTAREA", "HEAT", "GRADE",
            "YRBLT", "EFFYR", "COND", "SFLA"]
    df = _read(raw / "Dwelling.txt", cols)
    return df[df["CARD"] == "1"].drop(columns=["CARD"])


def sales(raw: Path) -> pd.DataFrame:
    cols = [ID, "SALEDT", "NOPAR", "INSTRUMENT", "VALID", "PRICE", "SALETYPE"]
    files = sorted(raw.glob("Sales*.txt"))
    df = pd.concat([_read(f, cols) for f in files], ignore_index=True)
    df["date"] = pd.to_datetime(df["SALEDT"], format="%m/%d/%Y", errors="coerce")
    df["price"] = pd.to_numeric(df["PRICE"], errors="coerce")
    df["parcels_in_sale"] = pd.to_numeric(df["NOPAR"], errors="coerce")
    return df.drop(columns=["SALEDT", "PRICE", "NOPAR"])


def transfers(raw: Path) -> pd.DataFrame:
    """Every recorded transfer with the new owner's name (used only to tell people from companies)."""
    files = sorted((raw / "tax").glob("Transfer*.txt"))
    df = pd.concat([_read(f, ["Parcel Id", "SaleDate", "OwnerName1"]) for f in files], ignore_index=True)
    df["date"] = pd.to_datetime(df["SaleDate"], format="%m/%d/%Y", errors="coerce")
    return df.rename(columns={"Parcel Id": ID, "OwnerName1": "owner"}).drop(columns=["SaleDate"]).dropna(subset=["date"])


def values_2025(raw: Path) -> pd.Series:
    """Tax-year 2025 market value (land + building), summed over a parcel's value rows."""
    df = _read(raw / "tax" / "Value.txt", ["Parcel Id", "TaxYear", "MarketLand", "MarketImpr"])
    df = df[df["TaxYear"] == "2025"]
    total = pd.to_numeric(df["MarketLand"], errors="coerce").fillna(0) + pd.to_numeric(df["MarketImpr"], errors="coerce").fillna(0)
    return total.groupby(df["Parcel Id"]).sum().rename("value_2025")


def tax_parcels(raw: Path) -> pd.DataFrame:
    cols = [ID, "TaxYear", "SiteAddress", "ZipCode", "SchoolDistrictDesc", "TaxDistrict", "TaxDistrictDesc", "FullRate",
            "NonBusinessRate", "OwnOccRate"]
    df = _read(raw / "tax" / "Parcel.txt", cols)
    for c in ["FullRate", "NonBusinessRate", "OwnOccRate"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    # Some parcels have a row for the next tax year too; keep the latest.
    return df.sort_values("TaxYear").drop_duplicates(ID, keep="last").drop(columns=["TaxYear"])


def tax_detail(raw: Path) -> pd.DataFrame:
    """Annual 2025 tax charges: AnnualSubtotal is after Ohio's HB 920 reduction factors, before credits."""
    df = _read(raw / "tax" / "TaxDetail.txt", ["Parcel Id", "AnnualOriginal", "AnnualSubtotal", "AnnualNet"])
    for c in ["AnnualOriginal", "AnnualSubtotal", "AnnualNet"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.rename(columns={"Parcel Id": ID})


def centroids(gis_dir: Path) -> pd.DataFrame:
    """Parcel centers (bounding-box midpoints) in Ohio State Plane South feet, plus latitude and longitude."""
    import shapefile
    from pyproj import Transformer

    shp = next(gis_dir.glob("*.shp"))
    r = shapefile.Reader(str(shp.with_suffix("")))
    recs = [rec.as_dict() for rec in r.iterRecords(fields=["PARCELID", "ACRES"])]
    ids = [d["PARCELID"] for d in recs]
    gis_acres = [d["ACRES"] for d in recs]
    boxes = np.array([s.bbox if len(s.bbox) == 4 else (np.nan,) * 4 for s in r.iterShapes()], dtype=float)
    x = (boxes[:, 0] + boxes[:, 2]) / 2
    y = (boxes[:, 1] + boxes[:, 3]) / 2
    lon, lat = Transformer.from_crs("EPSG:3735", "EPSG:4326", always_xy=True).transform(x, y)
    df = pd.DataFrame({"pid10": ids, "x": x, "y": y, "lat": lat, "lon": lon, "gis_acres": gis_acres}).dropna(subset=["x"])
    return df.drop_duplicates("pid10")
