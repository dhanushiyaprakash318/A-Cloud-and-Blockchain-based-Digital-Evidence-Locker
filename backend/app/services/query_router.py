import logging
import time
import json
from typing import Optional, Dict, Any, Callable

from app.services.bedrock_service import bedrock
from app.services.database import db
from app.services.chat_assistant import generate_chat_answer

logger = logging.getLogger(__name__)


# New intent set per design
INTENTS = {
    "CASE_STATISTICS",
    "CASE_SEARCH",
    "PERSON_SEARCH",
    "CASE_SUMMARY",
    "EVIDENCE_ANALYSIS",
    "GENERAL_HELP",
}


CLASSIFIER_SYSTEM_PROMPT = (
    "You are an intent and entity extractor for the DIVEL Case Management Assistant.\n\n"
    "INPUT: a single user question. OUTPUT: a single JSON object only (no explanatory text).\n\n"
    "Return JSON with the following schema: {\n"
    "  \"intent\": <ONE_OF=[CASE_STATISTICS,CASE_SEARCH,PERSON_SEARCH,CASE_SUMMARY,EVIDENCE_ANALYSIS,GENERAL_HELP]>,\n"
    "  \"filters\": { <optional key/value pairs for CASE_SEARCH or PERSON_SEARCH> },\n"
    "  \"metric\": <optional string for CASE_STATISTICS, e.g. 'under_investigation' or 'total_cases'>\n"
    "}\n\n"
    "Examples:\n"
    "Q: \"Show all cyber crime cases from Central Delhi\"\n"
    "--> {\"intent\":\"CASE_SEARCH\",\"filters\":{\"crime_type\":\"cyber\",\"location\":\"Central Delhi\"}}\n"
    "Q: \"List all absconding accused\"\n"
    "--> {\"intent\":\"PERSON_SEARCH\",\"filters\":{\"person_type\":\"accused\",\"status\":\"absconding\"}}\n"
    "Q: \"How many cases are under investigation\"\n"
    "--> {\"intent\":\"CASE_STATISTICS\",\"metric\":\"under_investigation\"}\n"
    "Q: \"Summarize case CR-2024-001\"\n"
    "--> {\"intent\":\"CASE_SUMMARY\",\"filters\":{\"case_id\":\"CR-2024-001\"}}\n"
    "Do not include any other keys. Return valid JSON only."
)


def _classify_and_extract(question: str, model_id: str = "amazon.nova-lite-v1:0") -> Dict[str, Any]:
    """Call Bedrock (Nova) to classify intent and extract structured filters.

    Returns a dict with keys: intent, filters (dict), metric (optional), confidence (float).
    The classifier is expected to return JSON only. We validate and provide
    a safe fallback (GENERAL_HELP) when parsing fails.
    """
    logger.debug("Classifying + extracting for question: %s", question)
    try:
        messages = [{"role": "user", "content": [{"text": question}]}]
        resp = bedrock.converse(model_id=model_id, system=CLASSIFIER_SYSTEM_PROMPT, messages=messages)
        text = (resp or {}).get("text", "") or ""
        text = text.strip()
        if not text:
            raise ValueError("Empty classifier response")

        # Attempt to extract JSON robustly using bedrock service helper
        try:
            parsed = bedrock._extract_json(text)
        except Exception:
            parsed = json.loads(text)

        intent = parsed.get("intent", "GENERAL_HELP")
        intent = intent.strip().upper() if isinstance(intent, str) else "GENERAL_HELP"
        if intent not in INTENTS:
            logger.warning("Classifier returned unknown intent '%s'", intent)
            intent = "GENERAL_HELP"

        filters = parsed.get("filters") or {}
        if not isinstance(filters, dict):
            logger.warning("Classifier 'filters' not an object; resetting to empty dict")
            filters = {}

        metric = parsed.get("metric")

        # Confidence handling: prefer provided numeric confidence, else set conservative default
        confidence = parsed.get("confidence")
        try:
            confidence = float(confidence) if confidence is not None else 0.9
            if confidence < 0.0 or confidence > 1.0:
                confidence = max(0.0, min(1.0, confidence))
        except Exception:
            confidence = 0.9

        return {"intent": intent, "filters": filters, "metric": metric, "confidence": confidence}
    except Exception as exc:
        logger.exception("Structured intent extraction failed: %s", exc)
        # Fallback: naive keyword mapping with conservative confidence
        q = question.lower()
        if any(k in q for k in ["how many", "count", "total cases", "under investigation"]):
            return {"intent": "CASE_STATISTICS", "filters": {}, "metric": None, "confidence": 0.6}
        if any(k in q for k in ["summarize", "summary", "case overview", "explain the case"]):
            return {"intent": "CASE_SUMMARY", "filters": {}, "metric": None, "confidence": 0.6}
        if any(k in q for k in ["who is", "suspect", "what happened", "witness", "evidence"]):
            return {"intent": "EVIDENCE_ANALYSIS", "filters": {}, "metric": None, "confidence": 0.6}
        return {"intent": "GENERAL_HELP", "filters": {}, "metric": None, "confidence": 0.5}


def _handle_case_statistics(filters: Dict[str, Any], metric: Optional[str]) -> Dict[str, Any]:
    try:
        cases = db.list_cases()
        total = len(cases)
        under_investigation = sum(1 for c in cases if (c.get("status") or "").lower() == "under investigation")
        pending_trial = sum(1 for c in cases if (c.get("status") or "").lower() == "pending trial")
        closed = sum(1 for c in cases if (c.get("status") or "").lower() in {"closed", "convicted", "acquitted"})
        evidence_count = sum(len(c.get("evidence") or []) for c in cases)

        metrics = {
            "total_cases": total,
            "under_investigation": under_investigation,
            "pending_trial": pending_trial,
            "closed_cases": closed,
            "evidence_files": evidence_count,
        }

        if metric:
            key = metric.lower()
            value = metrics.get(key) if key in metrics else None
            if value is None:
                return {"intent": "CASE_STATISTICS", "answer": f"Metric '{metric}' not recognized. Available: {', '.join(metrics.keys())}."}
            return {"intent": "CASE_STATISTICS", "answer": str(value)}

        answer = (
            f"Total cases: {total}. Under investigation: {under_investigation}. "
            f"Pending trial: {pending_trial}. Closed/Resolved: {closed}. Evidence items recorded: {evidence_count}."
        )
        return {"intent": "CASE_STATISTICS", "answer": answer}
    except Exception:
        logger.exception("Failed to compute case statistics")
        return {"intent": "CASE_STATISTICS", "answer": "Failed to compute case statistics."}


def _handle_case_search(filters: Dict[str, Any], _: Optional[str]) -> Dict[str, Any]:
    # Filters may include: location, crime_type, status, date, officer
    try:
        cases = db.list_cases()
        def match_case(c):
            if not filters:
                return True
            # location -> district or sceneOfCrime
            loc = filters.get("location")
            if loc and loc.lower() not in ((c.get("district") or "").lower() + " " + (c.get("sceneOfCrime") or "").lower()):
                return False
            crime = filters.get("crime_type") or filters.get("crime")
            if crime:
                # check lawSections and unit
                ls = ",".join(c.get("lawSections") or [])
                if crime.lower() not in ls.lower() and crime.lower() not in (c.get("unit") or "").lower():
                    return False
            status = filters.get("status")
            if status and status.lower() not in (c.get("status") or "").lower():
                return False
            # date filter could be exact or year
            date = filters.get("date")
            if date and date not in (c.get("dateOfOffence") or "") and date not in (c.get("dateOfReport") or ""):
                return False
            officer = filters.get("officer")
            if officer and officer.lower() not in json.dumps(c).lower():
                return False
            return True

        matched = [c for c in cases if match_case(c)]
        if not matched:
            return {"intent": "CASE_SEARCH", "answer": "No cases found matching the requested filters."}

        # Build a readable multi-line summary
        lines = []
        for c in matched:
            cid = c.get("caseNumber") or c.get("id") or "unknown"
            district = c.get("district") or c.get("location") or ""
            status = c.get("status") or ""
            date = c.get("dateOfOffence") or c.get("dateOfReport") or ""
            lines.append(f"{cid} — {district} — {status}{(' - ' + date) if date else ''}".strip())

        answer = "Found {} case(s):\n\n".format(len(matched)) + "\n".join(lines)
        return {"intent": "CASE_SEARCH", "answer": answer}
    except Exception:
        logger.exception("Failed to perform case search")
        return {"intent": "CASE_SEARCH", "answer": "Search operation failed."}


def _handle_person_search(filters: Dict[str, Any], _: Optional[str]) -> Dict[str, Any]:
    # person_type: accused/victim/witness, status, name
    try:
        cases = db.list_cases()
        persons = []
        name_q = (filters.get("name") or "").lower()
        ptype = (filters.get("person_type") or "accused").lower()
        status_q = (filters.get("status") or "").lower()

        for c in cases:
            accused = c.get("accused") or []
            for a in accused:
                # a can be dict-like
                aname = (a.get("name") or "").lower()
                astatus = (a.get("status") or "").lower()
                if name_q and name_q not in aname:
                    continue
                if status_q and status_q not in astatus:
                    continue
                persons.append({"caseId": c.get("id"), "person_type": "accused", "name": a.get("name"), "status": a.get("status"), "details": a})

            # search customFields for witnesses/victims (best-effort)
            for cf in c.get("customFields") or []:
                try:
                    if isinstance(cf, dict) and cf.get("type") in {"witness", "victim"}:
                        pname = (cf.get("name") or "").lower()
                        if name_q and name_q not in pname:
                            continue
                        pstatus = (cf.get("status") or "").lower()
                        if status_q and status_q not in pstatus:
                            continue
                        persons.append({"caseId": c.get("id"), "person_type": cf.get("type"), "name": cf.get("name"), "status": cf.get("status"), "details": cf})
                except Exception:
                    continue

        if not persons:
            return {"intent": "PERSON_SEARCH", "answer": "No matching persons found."}

        # Format persons into readable list
        lines = []
        for p in persons:
            name = p.get("name") or "unknown"
            cId = p.get("caseId") or "unknown"
            ptype = p.get("person_type") or "person"
            status = p.get("status") or ""
            details = p.get("details") or {}
            extra = []
            if isinstance(details, dict):
                if details.get("age"):
                    extra.append(f"Age: {details.get('age')}")
                if details.get("gender"):
                    extra.append(details.get("gender"))
                if details.get("mobile"):
                    extra.append(f"Mobile: {details.get('mobile')}")
            line = f"{name} ({ptype}) — Case: {cId} — {status}"
            if extra:
                line = line + " — " + ", ".join(extra)
            lines.append(line)

        answer = "Found {} person(s):\n\n".format(len(lines)) + "\n".join(lines)
        return {"intent": "PERSON_SEARCH", "answer": answer}
    except Exception:
        logger.exception("Failed to perform person search")
        return {"intent": "PERSON_SEARCH", "answer": "Person search failed."}


def _handle_case_summary(filters: Dict[str, Any], _: Optional[str]) -> Dict[str, Any]:
    case_id = filters.get("case_id") if filters else None
    if not case_id:
        return {"intent": "CASE_SUMMARY", "answer": "Please provide a case identifier to summarize."}
    try:
        # Reuse chat assistant to generate a summary (it will call Bedrock)
        answer = generate_chat_answer(case_id, "Please provide a concise summary of this case based on stored evidence summaries.")
        return {"intent": "CASE_SUMMARY", "answer": answer}
    except Exception:
        logger.exception("Failed to generate case summary for %s", case_id)
        return {"intent": "CASE_SUMMARY", "answer": "Failed to generate case summary."}


def _handle_evidence_analysis(filters: Dict[str, Any], question: Optional[str]) -> Dict[str, Any]:
    # Expect filters may include case_id
    case_id = filters.get("case_id") if filters else None
    if not case_id:
        return {"intent": "EVIDENCE_ANALYSIS", "answer": "Case ID is required for evidence analysis."}
    try:
        answer = generate_chat_answer(case_id, question or "Please answer based on the stored evidence summaries.")
        return {"intent": "EVIDENCE_ANALYSIS", "answer": answer}
    except Exception:
        logger.exception("Failed to perform evidence analysis for %s", case_id)
        return {"intent": "EVIDENCE_ANALYSIS", "answer": "Failed to analyze evidence."}


HELP_TEXT = (
    "DIVEL AI Help:\n"
    "- Ask about case counts (e.g., how many active investigations).\n"
    "- Ask to search or view case details by Case ID.\n"
    "- Ask about evidence analysis for a specific case (provide Case ID).\n"
    "- To upload evidence, use the Upload page in the UI."
)


def _handle_general_help(_: Dict[str, Any], __: Optional[str]) -> Dict[str, Any]:
    return {"intent": "GENERAL_HELP", "answer": HELP_TEXT}


# Map intents to handler functions
HANDLERS: Dict[str, Callable[[Dict[str, Any], Optional[str]], Dict[str, Any]]] = {
    "CASE_STATISTICS": _handle_case_statistics,
    "CASE_SEARCH": _handle_case_search,
    "PERSON_SEARCH": _handle_person_search,
    "CASE_SUMMARY": _handle_case_summary,
    "EVIDENCE_ANALYSIS": _handle_evidence_analysis,
    "GENERAL_HELP": _handle_general_help,
}


def route(question: str, case_id: Optional[str] = None) -> Dict[str, Any]:
    """Main router: classify intent (Nova) -> call handler -> return answer.

    The classifier returns structured filters that handlers use to query DynamoDB
    or call the chat assistant. Nova is used only for classification.
    """
    start = time.time()
    logger.info("Routing question (case_id=%s): %s", case_id, question)

    structured = _classify_and_extract(question)
    intent = structured.get("intent")
    filters = structured.get("filters") or {}
    metric = structured.get("metric")

    # If a case_id was provided in the HTTP request and not present in filters, inject it
    if case_id and not filters.get("case_id"):
        filters["case_id"] = case_id

    handler = HANDLERS.get(intent, _handle_general_help)
    try:
        if intent == "CASE_STATISTICS":
            result = handler(filters, metric)
        elif intent in {"CASE_SEARCH", "PERSON_SEARCH"}:
            result = handler(filters, None)
        elif intent in {"CASE_SUMMARY", "EVIDENCE_ANALYSIS"}:
            # these require talking to Bedrock via chat_assistant
            result = handler(filters, question)
        else:
            result = handler(filters, None)
    except Exception:
        logger.exception("Handler %s failed", intent)
        result = {"intent": intent, "answer": "An internal error occurred while handling your request."}

    elapsed = time.time() - start
    logger.info("Routing completed: intent=%s elapsed=%.3fs", result.get("intent"), elapsed)
    return result
