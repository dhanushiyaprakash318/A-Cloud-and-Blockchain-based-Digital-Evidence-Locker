import re
from typing import Any, Dict, List, Optional

from app.services.database import db


class RetrievalService:
    def __init__(self):
        self.intent_map = [
            ("summarize_case", re.compile(r"\b(summariz|summary|summarize|summaries)\b", re.I)),
            ("count_cases", re.compile(r"\b(how many cases|count.*cases|cases.*under investigation|under investigation)\b", re.I)),
            ("search_accused", re.compile(r"\b(absconding|absconding accused|accused|suspect|suspects|who is the accused)\b", re.I)),
            ("pending_evidence", re.compile(r"\b(pending evidence|evidence still pending|still pending|missing evidence)\b", re.I)),
            ("search_evidence", re.compile(r"\b(show.*evidence|search.*evidence|find.*evidence|evidence.*case|evidence.*pending)\b", re.I)),
            ("search_case", re.compile(r"\b(show.*cases|list.*cases|search.*cases|robbery|fraud|narcotics|violent crime|economic offences|case.*status)\b", re.I)),
            ("explain_case", re.compile(r"\b(explain.*case|what happened|case details|describe.*case|case summary)\b", re.I)),
            ("generate_report", re.compile(r"\b(generate report|report.*case|create report|report on)\b", re.I)),
            ("timeline", re.compile(r"\b(timeline|chronology|sequence of events|when did|what happened first)\b", re.I)),
        ]

    def detect_intent(self, question: str) -> str:
        normalized = question.strip().lower()
        for intent, pattern in self.intent_map:
            if pattern.search(normalized):
                return intent
        # fallback when question clearly targets case or evidence
        if re.search(r"\b(case|cases|evidence|accused|suspect|report|timeline)\b", normalized):
            return "general_chat"
        return "general_chat"

    def parse_case_identifier(self, question: str) -> Optional[str]:
        match = re.search(r"\bcase\s*(?:number)?\s*[:#]?\s*([A-Za-z0-9-]+)\b", question, re.I)
        if match:
            return match.group(1).strip()

        match = re.search(r"\b(CR-[A-Za-z0-9-]+)\b", question, re.I)
        if match:
            return match.group(1).strip()

        digits = re.findall(r"\b(\d{2,})\b", question)
        return digits[0] if digits else None

    def _case_matches(self, case: Dict[str, Any], query: str) -> bool:
        normalized = query.lower()
        searchable = []
        for key in ["caseNumber", "status", "district", "unit", "sceneOfCrime", "description"]:
            value = case.get(key)
            if isinstance(value, str):
                searchable.append(value.lower())
        for section in case.get("lawSections", []) or []:
            searchable.append(str(section).lower())
        for field in case.get("customFields", []) or []:
            searchable.append(str(field).lower())
        return any(normalized in text for text in searchable)

    def _accused_matches(self, accused: Dict[str, Any], query: str) -> bool:
        normalized = query.lower()
        for key in ["name", "status", "gender", "address", "mobile", "fatherName"]:
            value = accused.get(key)
            if isinstance(value, str) and normalized in value.lower():
                return True
        return False

    def _evidence_matches(self, evidence: Dict[str, Any], query: str) -> bool:
        normalized = query.lower()
        searchable = []
        for key in ["filename", "content_type", "uploader", "uploader_role", "blockchain_status", "ai_summary", "url", "local_path"]:
            value = evidence.get(key)
            if isinstance(value, str):
                searchable.append(value.lower())
        for key, value in (evidence.get("metadata") or {}).items():
            if isinstance(value, str):
                searchable.append(value.lower())
        return any(normalized in text for text in searchable)

    def _find_case_by_identifier(self, identifier: str, cases: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not identifier:
            return None
        normalized = identifier.lower()
        for case in cases:
            if str(case.get("caseNumber", "")).lower() == normalized:
                return case
            if normalized in str(case.get("caseNumber", "")).lower():
                return case
            if normalized in str(case.get("id", "")).lower():
                return case
        return None

    def _filter_cases(self, cases: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        return [case for case in cases if self._case_matches(case, query)]

    def _collect_accused(self, cases: List[Dict[str, Any]], query: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        for case in cases:
            for accused in case.get("accused", []) or []:
                if query is None or self._accused_matches(accused, query):
                    suspect = accused.copy()
                    suspect["caseNumber"] = case.get("caseNumber")
                    suspect["case_id"] = case.get("id")
                    results.append(suspect)
        return results

    def _collect_evidence(self, cases: List[Dict[str, Any]], query: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        for case in cases:
            evidence_list = case.get("evidence") or []
            if query is None:
                results.extend(evidence_list)
            else:
                for evidence in evidence_list:
                    if self._evidence_matches(evidence, query):
                        evidence_with_case = evidence.copy()
                        evidence_with_case["caseNumber"] = case.get("caseNumber")
                        evidence_with_case["case_id"] = case.get("id")
                        results.append(evidence_with_case)
        return results

    def _pending_evidence(self, cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for case in cases:
            for evidence in case.get("evidence", []) or []:
                status = str(evidence.get("blockchain_status", "")).lower()
                tx_hash = evidence.get("tx_hash") or evidence.get("transaction_hash")
                if status != "anchored" and not tx_hash:
                    pending = evidence.copy()
                    pending["caseNumber"] = case.get("caseNumber")
                    pending["case_id"] = case.get("id")
                    results.append(pending)
        return results

    def retrieve(self, question: str) -> Dict[str, Any]:
        all_cases = db.list_cases()
        intent = self.detect_intent(question)
        case_identifier = self.parse_case_identifier(question)
        context: Dict[str, Any] = {
            "intent": intent,
            "question": question.strip(),
            "case_identifier": case_identifier,
            "cases": [],
            "evidence": [],
            "accused": [],
            "data_found": False,
            "summary": {},
        }

        if intent == "count_cases":
            matched = [case for case in all_cases if str(case.get("status", "")).lower() == "under investigation"]
            context["cases"] = matched
            context["data_found"] = len(matched) > 0
            context["summary"] = {"count": len(matched), "status": "Under Investigation"}
            return context

        if intent == "search_case":
            if case_identifier:
                matched_case = self._find_case_by_identifier(case_identifier, all_cases)
                if matched_case:
                    context["cases"] = [matched_case]
                else:
                    context["cases"] = self._filter_cases(all_cases, case_identifier)
            else:
                context["cases"] = self._filter_cases(all_cases, question)
            context["data_found"] = len(context["cases"]) > 0
            return context

        if intent in {"summarize_case", "explain_case", "generate_report", "timeline"}:
            if case_identifier:
                case = self._find_case_by_identifier(case_identifier, all_cases)
                if case:
                    context["cases"] = [case]
            if not context["cases"]:
                context["cases"] = self._filter_cases(all_cases, question)
            if context["cases"]:
                primary = context["cases"][0]
                context["evidence"] = primary.get("evidence", []) or db.list_case_evidence(primary.get("id"))
                context["accused"] = primary.get("accused", []) or []
                context["data_found"] = True
            return context

        if intent == "search_accused":
            normalized_q = question.lower()
            # Special-case: if user asks for absconding accused, match statuses like 'abscond', 'absconding', or 'wanted'
            if re.search(r"\b(abscond|absconding|absconded|absconder|abscongers|absconders|absconding accused|absconding accused)\b", normalized_q):
                matched = []
                for case in all_cases:
                    for accused in case.get("accused", []) or []:
                        status = str(accused.get("status", "")).lower()
                        if "abscond" in status or "want" in status or "abscon" in status:
                            a = accused.copy()
                            a["caseNumber"] = case.get("caseNumber")
                            a["case_id"] = case.get("id")
                            matched.append(a)
                context["accused"] = matched
                context["data_found"] = len(matched) > 0
                return context

            all_accused = self._collect_accused(all_cases, question)
            if not all_accused and case_identifier:
                case = self._find_case_by_identifier(case_identifier, all_cases)
                if case:
                    all_accused = self._collect_accused([case])
            context["accused"] = all_accused
            context["data_found"] = len(all_accused) > 0
            return context

        if intent == "pending_evidence":
            pending = self._pending_evidence(all_cases)
            context["evidence"] = pending
            context["data_found"] = len(pending) > 0
            return context

        if intent == "search_evidence":
            searched = self._collect_evidence(all_cases, question)
            context["evidence"] = searched
            context["data_found"] = len(searched) > 0
            return context

        # general_chat fallback: search the database for matching content before using Bedrock
        matched_cases = self._filter_cases(all_cases, question)
        matched_evidence = self._collect_evidence(all_cases, question)
        matched_accused = self._collect_accused(all_cases, question)
        context["cases"] = matched_cases[:10]
        context["evidence"] = matched_evidence[:10]
        context["accused"] = matched_accused[:10]
        context["data_found"] = bool(matched_cases or matched_evidence or matched_accused)
        return context


retrieval_service = RetrievalService()
