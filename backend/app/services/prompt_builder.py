from typing import Any, Dict, List

SYSTEM_PROMPT = (
    "You are Divel AI, an assistant for police investigators.\n"
    "Use ONLY the information provided below.\n"
    "Do NOT use outside knowledge.\n"
    "If the answer is not present in the provided data, clearly state that it is unavailable.\n"
    "Answer naturally and concisely.\n"
)


class PromptBuilder:
    def __init__(self):
        self.system_prompt = SYSTEM_PROMPT

    def build_context_section(self, label: str, items: List[Any]) -> str:
        if not items:
            return f"{label}: None\n"
        if isinstance(items, dict):
            return f"{label}: {items}\n"
        text = f"{label}:\n"
        for item in items:
            text += f"- {item}\n"
        return text

    def case_to_text(self, case: Dict[str, Any]) -> str:
        lines = [
            f"Case Number: {case.get('caseNumber', 'N/A')}",
            f"Status: {case.get('status', 'N/A')}",
            f"District: {case.get('district', 'N/A')}",
            f"Unit: {case.get('unit', 'N/A')}",
            f"Date Of Offence: {case.get('dateOfOffence', 'N/A')}",
            f"Date Of Report: {case.get('dateOfReport', 'N/A')}",
            f"Scene Of Crime: {case.get('sceneOfCrime', 'N/A')}",
            f"Law Sections: {', '.join(case.get('lawSections', []) or [])}",
            f"Description: {case.get('description', 'N/A')}",
            f"Custom Fields: {case.get('customFields', [])}",
        ]
        return "\n".join(lines)

    def accused_to_text(self, accused: Dict[str, Any]) -> str:
        fields = [
            f"Name: {accused.get('name', 'N/A')}",
            f"Status: {accused.get('status', 'N/A')}",
            f"Age: {accused.get('age', 'N/A')}",
            f"Gender: {accused.get('gender', 'N/A')}",
            f"Father's Name: {accused.get('fatherName', 'N/A')}",
            f"Address: {accused.get('address', 'N/A')}",
            f"Mobile: {accused.get('mobile', 'N/A')}",
            f"Case Number: {accused.get('caseNumber', 'N/A')}",
        ]
        return "\n".join(fields)

    def evidence_to_text(self, evidence: Dict[str, Any]) -> str:
        lines = [
            f"Evidence ID: {evidence.get('evidence_id', evidence.get('id', 'N/A'))}",
            f"File Name: {evidence.get('filename', evidence.get('name', 'N/A'))}",
            f"Type: {evidence.get('content_type', evidence.get('type', 'N/A'))}",
            f"Uploaded By: {evidence.get('uploader', 'N/A')}",
            f"Uploader Role: {evidence.get('uploader_role', 'N/A')}",
            f"Status: {evidence.get('blockchain_status', 'N/A')}",
            f"URL: {evidence.get('url', 'N/A')}",
            f"Local Path: {evidence.get('local_path', 'N/A')}",
            f"AI Summary: {evidence.get('ai_summary', 'N/A')}",
        ]
        return "\n".join(lines)

    def build_prompt(self, question: str, retrieval_context: Dict[str, Any]) -> str:
        sections = [self.system_prompt, "\nRetrieved Data:\n"]

        cases = retrieval_context.get("cases", []) or []
        evidence = retrieval_context.get("evidence", []) or []
        accused = retrieval_context.get("accused", []) or []
        case_identifier = retrieval_context.get("case_identifier")
        summary = retrieval_context.get("summary")

        if case_identifier:
            sections.append(f"Case Identifier: {case_identifier}\n")

        if summary:
            for key, value in summary.items():
                sections.append(f"{key.capitalize()}: {value}\n")

        if cases:
            sections.append("Cases:")
            for case in cases:
                sections.append(self.case_to_text(case))
                sections.append("")
        else:
            sections.append("Cases: None\n")

        if accused:
            sections.append("Accused:")
            for person in accused:
                sections.append(self.accused_to_text(person))
                sections.append("")
        else:
            sections.append("Accused: None\n")

        if evidence:
            sections.append("Evidence:")
            for evidence_item in evidence:
                sections.append(self.evidence_to_text(evidence_item))
                sections.append("")
        else:
            sections.append("Evidence: None\n")

        if not retrieval_context.get("data_found"):
            sections.append(
                "Warning: No matching data was found for the user query. "
                "Answer only that the requested information is unavailable.\n"
            )

        sections.append("User Question:")
        sections.append(question)
        sections.append("\nAnswer:")

        return "\n".join(sections)

    def build_case_summary_prompt(self, case: Dict[str, Any], evidence_summaries: List[str]) -> str:
        sections = [
            "You are Divel AI, an assistant for police investigators.\n"
            "Write a single, coherent case summary using ONLY the information below.\n"
            "Do NOT use outside knowledge or invent facts.\n"
            "Weave the case details and evidence into a professional narrative "
            "(a few short paragraphs), highlighting key people, events, and findings.\n",
            "\nCase Details:",
            self.case_to_text(case),
        ]

        accused = case.get("accused") or []
        if accused:
            sections.append("\nAccused:")
            for person in accused:
                sections.append(self.accused_to_text(person))
                sections.append("")

        if evidence_summaries:
            sections.append("\nEvidence Summaries:")
            for summary in evidence_summaries:
                sections.append(f"- {summary}")
        else:
            sections.append("\nEvidence Summaries: None available")

        sections.append("\nCase Summary:")

        return "\n".join(sections)


prompt_builder = PromptBuilder()
