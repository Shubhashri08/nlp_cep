"""Synthetic data generators (clearly labelled SYNTHETIC in the database and UI).

Used only where no open ward-level dataset exists for Mumbai:
  * citizen complaints (text + location + status) – category mix driven by REAL ward attributes
    (DEM low-lying share, Census literacy / density, OSM facility gaps) so spatial patterns are meaningful;
  * monthly service-demand series (water, waste, transit ridership) driven by Census population;
  * monthly environmental readings (rainfall from IMD Santacruz climatology, PM2.5 seasonality).
The phrase inventory here is intentionally different from backend/app/nlp/corpus.py so the classifier
is evaluated on text it was not trained on.
"""
import math
import random
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from shapely.geometry import Point, shape

# IMD Santacruz monthly rainfall normals (mm, 1991–2020, rounded) and mean temperature (°C)
RAINFALL_NORMAL = {1: 1, 2: 0.5, 3: 1, 4: 1, 5: 12, 6: 526, 7: 919, 8: 566, 9: 348, 10: 91, 11: 17, 12: 6}
TEMP_NORMAL = {1: 24.4, 2: 25.2, 3: 27.2, 4: 28.8, 5: 30.1, 6: 29.2, 7: 27.8, 8: 27.5, 9: 27.8, 10: 28.6, 11: 27.6, 12: 25.9}
# Typical Mumbai PM2.5 seasonality (µg/m³, SAFAR / CPCB reports: winter peak, monsoon washout)
PM25_SEASON = {1: 78, 2: 70, 3: 55, 4: 42, 5: 35, 6: 22, 7: 16, 8: 15, 9: 19, 10: 38, 11: 62, 12: 75}

COMPLAINT_PHRASES = {
    "FLOODING": ["Water has collected knee high {at} after last night's rain", "Our lane {at} goes under water every time it rains heavily",
                 "Rain water entered the ground floor shops {at}", "The subway {at} is flooded and people are wading through",
                 "Paani bhar gaya hai {at}, gaadiyan band pad gayi", "{at} पूरा पानी में डूब गया है"],
    "DRAINAGE": ["The gutter {at} is choked and dirty water is coming out", "Nullah {at} has not been cleaned, full of plastic",
                 "Sewage is flowing on the footpath {at}", "Drain cover broken {at}, very bad smell",
                 "Gatar tunbla aahe {at}, ghaan paani rastyavar", "{at} नाली बंद है और गंदा पानी बह रहा है"],
    "WASTE_MANAGEMENT": ["Nobody has picked up the garbage {at} this week", "The dustbin {at} is overflowing onto the road",
                         "People are throwing debris on the empty plot {at}", "Garbage is being burnt {at} every evening",
                         "Kachra gaadi nahi aayi {at}, bahut badbu", "{at} कचरा उचलला नाही"],
    "WATER_SUPPLY": ["We are getting water only for half an hour {at}", "Tap water {at} is brown and smells bad",
                     "A big pipe is leaking {at} and water is being wasted", "No water since two days {at}, we are buying tankers",
                     "Nal mein paani bahut kam aata hai {at}", "{at} पानी नहीं आ रहा है"],
    "ROAD_INFRASTRUCTURE": ["Huge potholes {at}, two wheelers are falling", "The road {at} was dug up and never repaired",
                            "Paver blocks on the footpath {at} are loose", "Road {at} has sunk near the manhole",
                            "Rasta pura kharab hai {at}, khadde hi khadde", "{at} सड़क में बड़े गड्ढे हैं"],
    "TRAFFIC": ["Terrible jam {at} every evening", "Cars parked on both sides {at}, ambulances cannot pass",
                "The signal {at} has been off for a week", "Buses and trucks block the junction {at}",
                "Roz traffic jaam hota hai {at}"],
    "PUBLIC_TRANSPORT": ["The bus to the station from {at} comes once an hour", "Need a bus shelter {at}, people stand in the sun",
                         "Feeder service {at} was stopped", "Too crowded at the stop {at}, buses don't stop",
                         "Bus stop {at} pe shed nahi hai"],
    "STREETLIGHT": ["The street lights {at} are not working at night", "Lamp post {at} has been dark for weeks",
                    "Very dark near the garden {at}, lights broken", "Street light {at} band hai"],
    "ELECTRICITY": ["Wires are hanging very low {at}", "The transformer {at} makes sparks", "Power goes every evening {at}",
                    "Bijli baar baar ja rahi hai {at}"],
    "PUBLIC_SAFETY": ["Stray dogs {at} bit a child", "Chain snatching again {at}", "No patrolling {at} after 10 pm",
                      "The old wall {at} may fall on someone"],
    "HEALTHCARE": ["The dispensary {at} has no doctor in the evening", "Dengue cases in our building {at}, no fogging",
                   "Long queue at the health post {at}, medicines not available", "Machhar bahut hai {at}, koi spray nahi"],
    "EDUCATION": ["The municipal school {at} roof is leaking", "No proper toilets in the school {at}", "Classrooms {at} are overcrowded"],
    "PARKS": ["The garden {at} is closed and swings are broken", "Playground {at} used for parking", "Need benches and lights in the park {at}"],
    "ENVIRONMENT": ["Trees are being cut {at} without permission", "Chemical water released into the creek {at}", "Loud construction noise {at} at night"],
    "AIR_QUALITY": ["So much dust from the construction {at}", "Smoke {at} makes breathing hard", "Concrete plant {at} spreads dust all day"],
    "HOUSING": ["Our building {at} has big cracks, it is dangerous", "SRA project {at} is stuck for years", "Illegal floor being built {at}"],
}
BASE_RATES = {"FLOODING": 0.07, "DRAINAGE": 0.09, "WASTE_MANAGEMENT": 0.14, "WATER_SUPPLY": 0.12, "ROAD_INFRASTRUCTURE": 0.12,
              "TRAFFIC": 0.07, "PUBLIC_TRANSPORT": 0.05, "STREETLIGHT": 0.06, "ELECTRICITY": 0.03, "PUBLIC_SAFETY": 0.05,
              "HEALTHCARE": 0.04, "EDUCATION": 0.02, "PARKS": 0.03, "ENVIRONMENT": 0.03, "AIR_QUALITY": 0.04, "HOUSING": 0.04}
MONSOON_BOOST = {"FLOODING": 6.0, "DRAINAGE": 2.2, "ROAD_INFRASTRUCTURE": 1.6, "HEALTHCARE": 1.6, "ELECTRICITY": 1.3}
RESOLUTION_DAYS = {"WASTE_MANAGEMENT": 4, "STREETLIGHT": 7, "DRAINAGE": 10, "WATER_SUPPLY": 8, "FLOODING": 6, "ROAD_INFRASTRUCTURE": 25,
                   "TRAFFIC": 15, "ELECTRICITY": 5, "PUBLIC_SAFETY": 12, "HEALTHCARE": 30, "EDUCATION": 45, "PARKS": 40,
                   "ENVIRONMENT": 30, "AIR_QUALITY": 30, "HOUSING": 60, "PUBLIC_TRANSPORT": 45}
SOURCES = ["MyBMC App", "Web Portal", "1916 Helpline", "Ward Office", "Twitter / X", "WhatsApp Chatbot"]


def month_starts(end: date, months: int) -> List[date]:
    out, y, m = [], end.year, end.month
    for _ in range(months):
        out.append(date(y, m, 1))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(out))


def random_point_in(geom, rng: random.Random, near: Optional[Tuple[float, float]] = None, radius_deg: float = 0.004):
    minx, miny, maxx, maxy = geom.bounds
    for _ in range(200):
        if near:
            lat = near[0] + rng.gauss(0, radius_deg)
            lng = near[1] + rng.gauss(0, radius_deg)
        else:
            lng, lat = rng.uniform(minx, maxx), rng.uniform(miny, maxy)
        if geom.contains(Point(lng, lat)):
            return round(lat, 6), round(lng, 6)
        near = None if _ > 20 else near
    c = geom.representative_point()
    return round(c.y, 6), round(c.x, 6)


def generate_complaints(wards: List[Dict[str, Any]], gazetteer_by_ward: Dict[str, List[Dict[str, Any]]],
                        end_month: date, months: int = 36, total: int = 3200, seed: int = 11) -> List[Dict[str, Any]]:
    """wards: [{code, geometry, population, area, low_lying, literacy, health_gap, transit_gap, green_share}]"""
    rng = random.Random(seed)
    starts = month_starts(end_month, months)
    pop_weights = {w["code"]: w["population"] ** 0.9 for w in wards}
    total_w = sum(pop_weights.values())
    records = []
    for w in wards:
        geom = shape(w["geometry"])
        n_ward = int(total * pop_weights[w["code"]] / total_w)
        rates = dict(BASE_RATES)
        rates["FLOODING"] *= 0.4 + 4.0 * w["low_lying"]
        rates["DRAINAGE"] *= 0.6 + 2.5 * w["low_lying"]
        rates["WATER_SUPPLY"] *= 1 + (92 - w["literacy"]) / 6
        rates["WASTE_MANAGEMENT"] *= 0.7 + min(1.5, w["density"] / 40000)
        rates["HEALTHCARE"] *= 0.6 + 1.2 * w["health_gap"]
        rates["PUBLIC_TRANSPORT"] *= 0.6 + 1.2 * w["transit_gap"]
        rates["PARKS"] *= 0.5 + max(0.0, (10 - w["green_share"]) / 10)
        rates["AIR_QUALITY"] *= 0.7 + w.get("industrial_share", 0) / 10
        places = [p for p in gazetteer_by_ward.get(w["code"], []) if p["kind"] in ("STATION", "PLACE", "ROAD", "LANDMARK")]
        # growth in complaint volume over time (digital channel adoption + growth pressure)
        month_weights = []
        for i, ms in enumerate(starts):
            monsoon = ms.month in (6, 7, 8, 9)
            month_weights.append((1 + 0.012 * i) * (1.35 if monsoon else 1.0))
        mw_total = sum(month_weights)
        for i, ms in enumerate(starts):
            n_month = max(1, round(n_ward * month_weights[i] / mw_total + rng.gauss(0, 0.8)))
            monsoon = ms.month in (6, 7, 8, 9)
            month_rates = {c: r * (MONSOON_BOOST.get(c, 1.0) if monsoon else (0.25 if c == "FLOODING" else 1.0)) for c, r in rates.items()}
            cats, weights = zip(*month_rates.items())
            for _ in range(n_month):
                cat = rng.choices(cats, weights=weights)[0]
                place = rng.choice(places) if places and rng.random() < 0.8 else None
                at = f"near {place['name']}" if place and place["kind"] != "ROAD" else (f"on {place['name']}" if place else "in our area")
                phrase = rng.choice(COMPLAINT_PHRASES[cat])
                text = phrase.format(at=at)
                if rng.random() < 0.25:
                    text += rng.choice([" Please help.", " Complained before, no action.", " Urgent!", " Kindly look into this.", " Since many days."])
                has_gps = rng.random() < 0.55
                lat, lng = random_point_in(geom, rng, near=(place["lat"], place["lng"]) if place else None)
                day = rng.randint(1, 28)
                created = datetime(ms.year, ms.month, day, rng.randint(6, 22), rng.randint(0, 59), tzinfo=timezone.utc)
                age_days = (datetime(end_month.year, end_month.month, 28, tzinfo=timezone.utc) - created).days
                typical = RESOLUTION_DAYS[cat]
                p_resolved = 1 - math.exp(-age_days / (typical * 1.6))
                r = rng.random()
                if r < p_resolved * 0.88:
                    status = "RESOLVED" if rng.random() < 0.85 else "CLOSED"
                    resolved_at = created + timedelta(days=max(1, int(rng.expovariate(1 / typical))))
                elif r < p_resolved:
                    status, resolved_at = "IN_PROGRESS", None
                else:
                    status, resolved_at = "OPEN", None
                records.append({
                    "text": text, "true_category": cat, "ward_code": w["code"], "created_at": created,
                    "gps": (lat, lng) if has_gps else None, "fallback_point": (lat, lng),
                    "status": status, "resolved_at": resolved_at, "source": rng.choice(SOURCES),
                })
    rng.shuffle(records)
    return records


def service_series(ward: Dict[str, Any], months: List[date], annual_growth: float, seed: int) -> Dict[str, List[float]]:
    """Monthly demand series for one ward (water MLD, waste TPD, daily transit boardings)."""
    rng = random.Random(seed)
    water, waste, ridership = [], [], []
    base_pop = ward["population"]
    n = len(months)
    for i, ms in enumerate(months):
        pop = base_pop * (1 + annual_growth) ** ((i - n + 1) / 12)
        summer = 1.07 if ms.month in (4, 5) else (0.96 if ms.month in (7, 8) else 1.0)
        lpcd = ward.get("consumption_lpcd", 150)
        water.append(round(pop * lpcd / 1e6 * summer * (1 + rng.gauss(0, 0.015)), 3))
        festive = 1.06 if ms.month in (8, 9, 10, 11) else 1.0
        waste.append(round(pop * 0.48 / 1000 * festive * (1 + 0.002 * i) * (1 + rng.gauss(0, 0.02)), 3))
        monsoon = 0.9 if ms.month in (6, 7, 8) else 1.0
        exams = 0.95 if ms.month in (4, 5) else 1.0
        ridership.append(round(pop * ward["trips_per_capita"] * ward["pt_share"] * monsoon * exams * (1 + 0.003 * i) * (1 + rng.gauss(0, 0.02))))
    return {"water_demand_mld": water, "waste_generation_tpd": waste, "transit_ridership": ridership}


def environmental_series(ward: Dict[str, Any], months: List[date], seed: int) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    rows = []
    for ms in months:
        rain = max(0.0, RAINFALL_NORMAL[ms.month] * rng.lognormvariate(0, 0.25))
        pm25 = PM25_SEASON[ms.month] * (0.85 + 0.03 * ward.get("industrial_share", 0) + 0.004 * ward.get("built_share", 50)) * rng.lognormvariate(0, 0.12)
        rows.append({
            "recorded_at": datetime(ms.year, ms.month, 15, tzinfo=timezone.utc),
            "rainfall_mm": round(rain, 1),
            "aqi_pm25": round(pm25, 1),
            "aqi_pm10": round(pm25 * rng.uniform(1.7, 2.1), 1),
            "avg_temperature_c": round(TEMP_NORMAL[ms.month] + rng.gauss(0, 0.6), 1),
        })
    return rows
