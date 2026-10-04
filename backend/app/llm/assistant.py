"""Grounded urban planning assistant.

With an LLM provider (OpenAI / Gemini): the model plans which read-only tools to call (llm/tools.py), receives
their rows, and writes an answer constrained to those results. Evidence citations are taken from the tool calls
that actually ran – never from the model's text.

Without an LLM: deterministic intent routing over the same tools, answers composed from templates.
"""
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.app.llm.providers import get_llm
from backend.app.llm.tools import TOOL_SPECS, execute_tool, resolve_ward
from backend.app.models.entities import Ward

SYSTEM_PROMPT = """You are the analytical assistant of an Urban Planning Decision Support System for Greater Mumbai (24 BMC wards).
Rules:
- Answer ONLY from tool results. Call tools to fetch data; never guess numbers, places or dates.
- If the tools return no data or an error, say what is missing instead of estimating.
- Mention provenance where relevant (Census 2011 / OpenStreetMap / Sentinel-2 are real; complaint texts and monthly
  service series are synthetic demonstration data).
- Be concise and decision-oriented: key finding, supporting numbers, 2–3 recommended next steps.
- Use Markdown bold for key numbers and ward names. Do not include SQL in the answer."""

MAX_STEPS = 5


def _find_ward_in_text(db: Session, text: str) -> Optional[Ward]:
    m = re.search(r"\b([A-T](?:\s*[/\-]\s*(?:N|S|E|W|C|NORTH|SOUTH|EAST|WEST|CENTRAL))?)\s+ward\b|\bward\s+([A-T](?:\s*[/\-]\s*(?:N|S|E|W|C|NORTH|SOUTH|EAST|WEST|CENTRAL))?)\b",
                  text, re.IGNORECASE)
    if m:
        w = resolve_ward(db, m.group(1) or m.group(2))
        if w:
            return w
    low = text.lower()
    for w in db.query(Ward).all():
        for loc in (w.localities or "").split(","):
            loc = loc.strip().lower()
            if len(loc) >= 4 and re.search(rf"\b{re.escape(loc)}\b", low):
                return w
    return None


class GroundedPlanningAssistant:
    """LLM answers for repeated questions are cached (LLM_CACHE_TTL_SECONDS) to save free-tier quota."""

    def __init__(self):
        self._cache: Dict[Tuple[str, Optional[int]], Tuple[float, Dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def answer_query(self, question: str, db: Session, context_ward_id: Optional[int] = None) -> Dict[str, Any]:
        from backend.app.core.config import settings
        llm = get_llm()
        if not llm.available:
            return self._answer_with_rules(question, db, context_ward_id)
        key = (re.sub(r"\s+", " ", question.strip().lower()), context_ward_id)
        with self._lock:
            hit = self._cache.get(key)
        if hit and time.time() - hit[0] < settings.LLM_CACHE_TTL_SECONDS:
            return {**hit[1], "suggested_actions": hit[1]["suggested_actions"] + ["(cached answer)"]}
        try:
            res = self._answer_with_llm(llm, question, db, context_ward_id)
        except Exception as exc:  # outage / quota / local budget -> degrade gracefully to the rule engine
            res = self._answer_with_rules(question, db, context_ward_id)
            res["suggested_actions"].append(f"LLM unavailable ({str(exc)[:140]}); answered with the rule-based engine.")
            return res
        with self._lock:
            self._cache[key] = (time.time(), res)
        return res

    # ------------------------------------------------------------------ LLM path
    def _answer_with_llm(self, llm, question: str, db: Session, context_ward_id: Optional[int]) -> Dict[str, Any]:
        ctx = ""
        if context_ward_id:
            w = db.get(Ward, context_ward_id)
            if w:
                ctx = f"\n(The user is currently looking at ward {w.ward_code} – {w.name}.)"
        log: List[Dict[str, Any]] = []

        def executor(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
            return execute_tool(db, name, args)

        answer, log = llm.run_tools(SYSTEM_PROMPT, question + ctx, TOOL_SPECS, executor, max_steps=MAX_STEPS)
        sources = [c["result"]["citation"] for c in log if isinstance(c.get("result"), dict) and c["result"].get("citation")]
        findings = []
        for c in log:
            rows = (c.get("result") or {}).get("rows") or []
            findings.extend(rows[:5])
        ok_calls = [c for c in log if not (c.get("result") or {}).get("error")]
        confidence = 0.35 if not log else round(min(0.95, 0.55 + 0.1 * len(ok_calls) - 0.15 * (len(log) - len(ok_calls))), 2)
        return {
            "question": question,
            "intent": "LLM_TOOL_PLAN: " + (", ".join(dict.fromkeys(c["tool"] for c in log)) or "no tools"),
            "grounded_answer": (answer or "I could not produce an answer from the available data.").strip(),
            "structured_findings": findings[:25],
            "evidence_sources": sources,
            "suggested_actions": self._suggestions(log),
            "confidence": max(0.0, confidence),
            "provider": llm.name,
            "model": llm.model,
        }

    @staticmethod
    def _suggestions(log: List[Dict[str, Any]]) -> List[str]:
        tools = {c["tool"] for c in log}
        out = []
        if "infrastructure_gaps" in tools:
            out.append("Open Infrastructure Gaps to review the affected wards")
        if "forecast_demand" in tools:
            out.append("Compare forecasts across wards on the Predictions page")
        if "complaint_statistics" in tools or "search_complaints" in tools:
            out.append("Inspect complaint hotspots on the GIS Explorer")
        if "simulate_scenario" in tools:
            out.append("Save this what-if as a scenario in Scenario Studio")
        return out or ["Ask about a specific ward, sector or forecast horizon"]

    # ------------------------------------------------------------------ rule-based path
    def _answer_with_rules(self, question: str, db: Session, context_ward_id: Optional[int]) -> Dict[str, Any]:
        q = question.lower()
        ward = _find_ward_in_text(db, question) or (db.get(Ward, context_ward_id) if context_ward_id else None)
        calls: List[Tuple[str, Dict[str, Any]]] = []
        intent = "CITY_OVERVIEW"
        year = re.search(r"\b(20[3-5]\d)\b", q)

        if year and any(k in q for k in ("need", "require", "demand", "infrastructure", "plan")):
            intent = "FUTURE_INFRASTRUCTURE_DEMAND"
            calls.append(("infrastructure_demand", {"target_year": int(year.group(1))}))
        elif any(k in q for k in ("forecast", "predict", "next year", "next 12", "future", "projection", "trend")):
            intent = "DEMAND_FORECAST"
            metric = ("water_demand_mld" if "water" in q else "waste_generation_tpd" if any(k in q for k in ("waste", "garbage")) else
                      "transit_ridership" if any(k in q for k in ("transit", "bus", "ridership", "commut")) else "complaint_volume")
            calls.append(("forecast_demand", {"metric": metric, "ward": ward.ward_code if ward else None}))
        elif any(k in q for k in ("growth", "expansion", "sprawl", "built-up", "built up", "satellite", "ndvi", "urbanis", "urbaniz")):
            intent = "URBAN_GROWTH"
            calls.append(("urban_growth", {"ward": ward.ward_code if ward else None, "limit": 6}))
        elif any(k in q for k in ("recommend", "should", "intervention", "invest", "action", "what to do", "priorit")):
            intent = "RECOMMENDATIONS"
            calls.append(("recommendations", {"ward": ward.ward_code if ward else None, "sector": _sector_from(q), "limit": 5}))
        elif any(k in q for k in ("gap", "deficit", "shortage", "shortfall", "capacity", "lack", "inadequate")):
            intent = "INFRASTRUCTURE_GAPS"
            calls.append(("infrastructure_gaps", {"ward": ward.ward_code if ward else None, "sector": _sector_from(q), "limit": 6}))
        elif any(k in q for k in ("flood", "waterlog", "drain", "paani", "complaint", "grievance", "garbage", "pothole", "issue")):
            intent = "COMPLAINT_ANALYSIS"
            cat = _category_from(q)
            calls.append(("complaint_statistics", {"category": cat, "ward": ward.ward_code if ward else None,
                                                   "group_by": "category" if ward else "ward"}))
            if cat == "FLOODING":
                calls.append(("complaint_statistics", {"category": "DRAINAGE", "ward": ward.ward_code if ward else None,
                                                       "group_by": "category" if ward else "ward"}))
        elif ward:
            intent = "WARD_PROFILE"
            calls.append(("get_ward_profile", {"ward": ward.ward_code}))
        else:
            calls.append(("list_wards", {"sort_by": "priority", "limit": 5}))

        results = [(name, args, execute_tool(db, name, args)) for name, args in calls]
        answer, findings, actions = _compose(intent, results, ward)
        sources = [r["citation"] for _, _, r in results if r.get("citation")]
        has_rows = any(r.get("rows") for _, _, r in results)
        confidence = 0.8 if has_rows and intent != "CITY_OVERVIEW" else (0.6 if has_rows else 0.3)
        return {"question": question, "intent": intent, "grounded_answer": answer, "structured_findings": findings,
                "evidence_sources": sources, "suggested_actions": actions, "confidence": confidence, "provider": "rules", "model": None}


SECTOR_WORDS = {"water": "Water", "waste": "Waste", "garbage": "Waste", "drain": "Drainage", "flood": "Drainage",
                "health": "Health", "hospital": "Health", "school": "Education", "education": "Education",
                "transit": "Transit", "bus": "Transit", "park": "Open Space", "open space": "Open Space", "green": "Open Space"}
CATEGORY_WORDS = {"flood": "FLOODING", "waterlog": "FLOODING", "paani": "FLOODING", "drain": "DRAINAGE", "sewer": "DRAINAGE",
                  "garbage": "WASTE_MANAGEMENT", "waste": "WASTE_MANAGEMENT", "kachra": "WASTE_MANAGEMENT", "pothole": "ROAD_INFRASTRUCTURE",
                  "road": "ROAD_INFRASTRUCTURE", "water supply": "WATER_SUPPLY", "tap": "WATER_SUPPLY", "traffic": "TRAFFIC",
                  "bus": "PUBLIC_TRANSPORT", "streetlight": "STREETLIGHT", "light": "STREETLIGHT", "dengue": "HEALTHCARE",
                  "hospital": "HEALTHCARE", "school": "EDUCATION", "park": "PARKS", "air": "AIR_QUALITY", "dust": "AIR_QUALITY",
                  "tree": "ENVIRONMENT", "housing": "HOUSING", "building": "HOUSING", "dog": "PUBLIC_SAFETY", "safety": "PUBLIC_SAFETY"}


def _sector_from(q: str) -> Optional[str]:
    return next((v for k, v in SECTOR_WORDS.items() if k in q), None)


def _category_from(q: str) -> Optional[str]:
    return next((v for k, v in CATEGORY_WORDS.items() if k in q), None)


def _fmt(n) -> str:
    if isinstance(n, float) and n.is_integer():
        n = int(n)
    if isinstance(n, (int, float)) and abs(n) >= 100:
        return f"{n:,.0f}"
    return f"{n:,.2f}" if isinstance(n, float) else (f"{n:,}" if isinstance(n, int) else str(n))


def _compose(intent: str, results, ward: Optional[Ward]) -> Tuple[str, List[Dict[str, Any]], List[str]]:
    name, args, res = results[0]
    rows = res.get("rows") or []
    if res.get("error"):
        return f"I could not retrieve that: {res['error']}", [], ["Rephrase with a ward code (e.g. H/E) or a sector"]
    where = f" in **{ward.name}**" if ward else ""

    if intent == "COMPLAINT_ANALYSIS":
        merged: Dict[str, int] = {}
        key = "category" if ward else "ward"
        for _, _, r in results:
            for row in r.get("rows") or []:
                merged[row[key]] = merged.get(row[key], 0) + row["complaints"]
        ranked = sorted(merged.items(), key=lambda kv: -kv[1])
        if not ranked:
            return f"No matching complaints were recorded{where} in the last 12 months.", [], []
        label = (args.get("category") or "all").replace("_", " ").lower()
        if ward:
            text = f"In the last 12 months{where}, complaints ({label}) break down as: " + \
                   ", ".join(f"**{k.replace('_', ' ').title()}** {v}" for k, v in ranked[:5]) + "."
        else:
            text = (f"Over the last 12 months, **{ranked[0][0]} ward** recorded the most {label} complaints (**{ranked[0][1]}**), "
                    f"followed by " + ", ".join(f"**{k}** ({v})" for k, v in ranked[1:4]) + ".")
        text += " Complaint texts are synthetic demonstration data located at real OSM places."
        return text, [{key: k, "complaints": v} for k, v in ranked[:10]], [
            "Open the GIS Explorer hotspot layer for this category", "Check drainage / service gaps for the top wards"]

    if intent == "INFRASTRUCTURE_GAPS":
        if not rows:
            return f"No infrastructure gaps matched{where}.", [], []
        top = rows[0]
        text = (f"The largest deficit{where} is **{top['sector']}** in **{top['ward']}**: {_fmt(top['existing'])} available vs "
                f"{_fmt(top['required'])} required ({top['unit']}), a **{top['deficit_pct']}%** shortfall (**{top['severity']}**"
                f"{', low data confidence' if top.get('data_confidence') == 'LOW' else ''}). "
                f"Other major gaps: " + "; ".join(f"{r['sector']} in {r['ward_code']} ({r['deficit_pct']}%)" for r in rows[1:4]) + ". "
                f"Benchmarks: {top['norm']}.")
        return text, rows, ["Review the Infrastructure Gaps dashboard", "Generate recommendations for the affected wards"]

    if intent == "DEMAND_FORECAST":
        s = res.get("summary") or {}
        if not rows:
            return "No forecast is available for that metric.", [], []
        peak = max(rows, key=lambda p: p["predicted_value"])
        bt = s.get("backtest") or {}
        text = (f"For **{s.get('ward')}**, {s.get('metric', '').replace('_', ' ')} is forecast to average **{_fmt(s.get('forecast_average'))} {s.get('unit')}** "
                f"over the next {len(rows)} months ({s.get('growth_pct'):+.1f}% vs the last 12 months), peaking in **{peak['date']}** at "
                f"{_fmt(peak['predicted_value'])} (95% interval {_fmt(peak['lower_bound'])}–{_fmt(peak['upper_bound'])}). "
                f"Backtest MAPE: {bt.get('mape_pct')}% (seasonal-naive {bt.get('seasonal_naive_mape_pct')}%).")
        return text, rows, ["Open Predictions to compare wards", "Plan capacity for the peak month"]

    if intent == "URBAN_GROWTH":
        if not rows:
            return "No satellite-derived growth data is available (run the Sentinel-2 ingestion).", [], []
        r0 = rows[0]
        text = (f"Between {r0['period']}, **{r0['ward']}** shows the largest built-up change ({r0['built_up_change_sq_km']:+.2f} km², "
                f"now {r0['built_up_share_pct']}% of ward area; class **{r0['growth_class']}**). " +
                "Other wards: " + "; ".join(f"{r['ward_code']} {r['built_up_change_sq_km']:+.2f} km² ({r['growth_class']})" for r in rows[1:5]) +
                ". Source: Sentinel-2 L2A composites.")
        return text, rows, ["View the built-up change overlay on the GIS Explorer"]

    if intent == "RECOMMENDATIONS":
        if not rows:
            return f"No recommendations are currently generated{where}.", [], ["Run 'Regenerate recommendations'"]
        text = f"Top evidence-based interventions{where}:\n" + "\n".join(
            f"{i + 1}. **{r['title']}** ({r['ward_code']}, score {r['score']}, est. ₹{_fmt(r['estimated_cost_cr'])} Cr) — {r['proposal']}"
            for i, r in enumerate(rows[:5]))
        return text, rows, ["Open Recommendations to approve or reject proposals"]

    if intent == "FUTURE_INFRASTRUCTURE_DEMAND":
        t = res.get("city_totals") or {}
        text = (f"By **{args['target_year']}**, projected population is **{_fmt(t.get('population_projected'))}**. Norm-based needs: "
                f"water **{_fmt(t.get('water_required_mld'))} MLD** (additional {_fmt(t.get('additional_water_mld'))} MLD), waste processing "
                f"**{_fmt(t.get('waste_generated_tpd'))} TPD**, **{_fmt(t.get('additional_health_facilities'))}** more primary health facilities and "
                f"**{_fmt(t.get('additional_schools'))}** more schools. Largest water shortfalls: " +
                ", ".join(f"{r['ward_code']} (+{r['additional_water_mld']} MLD)" for r in rows[:4]) + f". Method: {res.get('method')}")
        return text, rows, ["Test augmentation options in Scenario Studio"]

    if intent == "WARD_PROFILE" and rows:
        p = rows[0]
        gaps = [g for g in p["infrastructure_gaps"] if g["severity"] in ("CRITICAL", "HIGH")]
        top_c = sorted(p["complaints_by_category"].items(), key=lambda kv: -kv[1])[:3]
        text = (f"**{p['name']}** ({p['localities']}): estimated population **{_fmt(p['population_estimate'])}**, density "
                f"**{_fmt(p['density_per_sqkm'])}/km²**, priority score **{p['priority_score']}/100**, growth pattern **{p['growth_class']}**. "
                f"{p['open_complaints']} complaints are open; most common: " + ", ".join(f"{k.replace('_', ' ').lower()} ({v})" for k, v in top_c) +
                ". Critical/high gaps: " + (", ".join(f"{g['sector']} ({g['deficit_pct']}%)" for g in gaps) or "none") + ".")
        return text, rows, [f"Open {p['ward_code']} on the GIS Explorer", "Ask for recommendations for this ward"]

    # city overview
    text = "Highest-priority wards by the MCDA score: " + ", ".join(
        f"**{r['ward_code']}** ({r['name'].split('(')[-1].rstrip(')')}, score {r['priority_score']})" for r in rows) + \
        ". Ask about flooding complaints, infrastructure gaps, growth patterns, forecasts or a specific ward."
    return text, rows, ["Which wards have the most flooding complaints?", "What are the critical infrastructure gaps?",
                        "Forecast water demand for the next year", "What infrastructure will Mumbai need in 2031?"]


planning_assistant = GroundedPlanningAssistant()
