from app.core.config import settings
import json

class AIService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self._client = None

    @property
    def client(self):
        if self._client is None and self.api_key:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _process_multimodal(self, file_path: str, mime_type: str) -> dict:
        """Handles all evidence files via Gemini's File API."""
        try:
            if not self.client:
                return {"summary": "Gemini Client not initialized.", "graph": {"nodes": [], "links": []}}

            from google.genai import types

            print(f"Uploading {file_path} to Gemini...")
            uploaded_file = self.client.files.upload(path=file_path)

            summary_prompt = "You are a senior forensic detective. Analyze this evidence file and write a professional, concise case summary. Focus on facts, events, and key individuals."
            summary_response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[uploaded_file, summary_prompt]
            )

            graph_prompt = """
            Extract entities and relationships from this evidence for a Knowledge Graph.
            Return ONLY a JSON object with this exact schema:
            {
                "nodes": [{"id": "Name", "group": "Person|Location|Incident|Evidence"}],
                "links": [{"source": "Name", "target": "Name", "value": "relationship description"}]
            }
            """

            graph_response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[uploaded_file, graph_prompt],
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )

            return {
                "summary": summary_response.text,
                "graph": json.loads(graph_response.text)
            }
        except Exception as e:
            print(f"Multimodal processing error: {e}")
            return {
                "summary": f"Error processing multimodal evidence: {str(e)}",
                "graph": {"nodes": [], "links": []}
            }

    def generate_summary(self, file_path: str) -> dict:
        if not self.api_key:
            return {
                "summary": "AI Service not configured (Missing Gemini API Key)",
                "graph": {"nodes": [], "links": []}
            }

        mime_type = "application/octet-stream"
        ext = file_path.split('.')[-1].lower()
        if ext in ['mp4', 'mov', 'avi']:
            mime_type = "video/mp4"
        elif ext in ['mp3', 'wav', 'aac']:
            mime_type = "audio/mpeg"
        elif ext in ['jpg', 'png', 'jpeg', 'webp']:
            mime_type = "image/jpeg"

        return self._process_multimodal(file_path, mime_type)

ai_service = AIService()
