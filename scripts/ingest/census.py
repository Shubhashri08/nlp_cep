"""Census of India 2011 ward-level data for Greater Mumbai (source: ORGI, republished by OpenCity).

The Census uses its own ward numbers (e.g. 1043); the "Mumbai – Census Data 2011" table maps each census
ward to its BMC administrative ward (A … T). The Primary Census Abstract (PCA) tables provide households,
literacy, child population and workers per census ward. We aggregate PCA rows to the 24 BMC wards.

Output: backend/data/external/census2011_mumbai_wards.csv
"""
import csv
from collections import defaultdict

from scripts.ingest.common import download, external_path

BASE = "https://data.opencity.in/dataset/1a81291d-369d-43e6-97b1-e62680434437/resource"
SOURCES = {
    "ward_map": (f"{BASE}/fcfeacdc-aa80-4028-a468-f0267fa05d23/download/95e22d97-7f59-4214-b244-2abbf52e6027.csv",
                 "census/mumbai_census_2011_wards.csv"),
    "pca_city": (f"{BASE}/b2261b97-db46-4d14-a1a7-a2a14976cede/download/fca87e9a-f012-41fe-93bc-cd1ae7e1f82a.csv",
                 "census/pca_mumbai_city_2011.csv"),
    "pca_suburban": (f"{BASE}/a33e01ed-6dec-458b-af70-395c59d4f89e/download/43c17944-e918-4270-ae91-63f986adfb93.csv",
                     "census/pca_mumbai_suburban_2011.csv"),
}


from backend.app.analytics.demography import CITY_ANNUAL_GROWTH, CITY_POP_2011, project_population  # noqa: F401


def _read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def build_census_table(refresh: bool = False) -> list:
    paths = {k: download(url, rel, refresh=refresh) for k, (url, rel) in SOURCES.items()}

    census_to_bmc = {}
    for row in _read(paths["ward_map"]):
        census_to_bmc[row["Ward Code"].strip().zfill(4)] = row["Ward Name"].strip()

    agg = defaultdict(lambda: defaultdict(int))
    fields = {"No_HH": "households", "TOT_P": "population", "TOT_M": "males", "TOT_F": "females",
              "P_06": "children_0_6", "P_SC": "sc", "P_ST": "st", "P_LIT": "literates", "TOT_WORK_P": "workers"}
    for key in ("pca_city", "pca_suburban"):
        for row in _read(paths[key]):
            if row["Level"].strip() != "WARD" or row["TRU"].strip() != "Urban":
                continue
            bmc = census_to_bmc.get(row["Ward"].strip().zfill(4))
            if not bmc:
                continue
            for src, dst in fields.items():
                agg[bmc][dst] += int(row[src])

    rows = []
    for code in sorted(agg):
        a = agg[code]
        literacy = 100.0 * a["literates"] / max(1, a["population"] - a["children_0_6"])
        rows.append({
            "ward_code": code,
            "population_2011": a["population"],
            "males": a["males"],
            "females": a["females"],
            "households": a["households"],
            "children_0_6": a["children_0_6"],
            "literates": a["literates"],
            "literacy_rate_pct": round(literacy, 2),
            "workers": a["workers"],
            "sc_population": a["sc"],
            "st_population": a["st"],
            "sex_ratio": round(1000.0 * a["females"] / max(1, a["males"]), 1),
            "avg_household_size": round(a["population"] / max(1, a["households"]), 2),
        })

    total = sum(r["population_2011"] for r in rows)
    if total != CITY_POP_2011:
        print(f"  [census] WARNING: aggregated population {total:,} != official {CITY_POP_2011:,}")
    out = external_path("census2011_mumbai_wards.csv")
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"  [census] {len(rows)} wards, total population {total:,}")
    return rows


def load_census_table() -> dict:
    path = external_path("census2011_mumbai_wards.csv")
    rows = _read(path)
    out = {}
    for r in rows:
        out[r["ward_code"]] = {k: (float(v) if "." in v else int(v)) if k != "ward_code" else v for k, v in r.items()}
    return out


if __name__ == "__main__":
    build_census_table()
