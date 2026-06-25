from app.core.config import settings
from google import genai
from google.genai import types
import json
from docling.document_converter import DocumentConverter

class AIService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.client = None
        # Lazy load converter to avoid startup issues if not used immediately
        self._converter = None
        
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)

    @property
    def converter(self):
        if self._converter is None:
            self._converter = DocumentConverter()
        return self._converter

    def _convert_file_to_markdown(self, file_path: str) -> str:
        """Uses Docling to convert PDF/Image to Markdown."""
        try:
            result = self.converter.convert(file_path)
            return result.document.export_to_markdown()
        except Exception as e:
            print(f"Docling conversion error: {e}")
            return f"Error parsing document: {str(e)}"

    def _process_multimodal(self, file_path: str, mime_type: str) -> dict:
        """Handles Video/Audio/Images directly via Gemini's File API."""
        try:
            if not self.client:
                return {"summary": "Gemini Client not initialized.", "graph": {"nodes": [], "links": []}}

            # 1. Upload file to Gemini
            print(f"Uploading {file_path} to Gemini...")
            uploaded_file = self.client.files.upload(path=file_path)
            
            # 2. Generate Summary (Detective Agent)
            summary_prompt = "You are a senior forensic detective. Analyze this evidence (video/audio/image) and write a professional, concise case summary. Focus on facts, events, and key individuals."
            summary_response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[uploaded_file, summary_prompt]
            )
            
            # 3. Extract Knowledge Graph (Analyst Agent)
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

    def _run_detective_agent(self, context: str) -> str:
        """
        Role: Senior Detective
        Task: Analyze text evidence and produce a summary.
        """
        try:
            if not self.client: return "AI Service Unavailable"
            
            prompt = f"""
            You are a Senior Forensic Detective. 
            Analyze the following evidence content and provide a professional case summary.
            
            Evidence Content:
            {context[:30000]}  # Limit context window just in case
            
            Output Guidelines:
            - Start with a strict status (Relevant/Irrelevant)
            - Summarize key facts, timeline, and involved individuals.
            - maintain a professional, objective tone.
            """
            
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            return response.text
        except Exception as e:
            print(f"Detective Agent Error: {e}")
            return f"Error analyzing document: {str(e)}"

    def _run_analyst_agent(self, context: str) -> dict:
        """
        Role: Intelligence Analyst
        Task: Extract entities and relationships for knowledge graph.
        """
        try:
            if not self.client: return {"nodes": [], "links": []}

            prompt = f"""
            You are a Criminal Intelligence Analyst.
            Extract entities and relationships from the text below for a Knowledge Graph.
            
            Evidence Content:
            {context[:30000]}
            
            Return ONLY a JSON object with this exact schema:
            {{
                "nodes": [{{"id": "Name", "group": "Person|Location|Incident|Evidence"}}],
                "links": [{{"source": "Name", "target": "Name", "value": "relationship description"}}]
            }}
            """
            
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"Analyst Agent Error: {e}")
            return {"nodes": [], "links": []}

    def generate_summary(self, file_path: str) -> dict:
        if not self.api_key:
             return {
                "summary": "AI Service not configured (Missing Gemini API Key)",
                "graph": {"nodes": [], "links": []}
            }
        
        # Determine if we should use Docling or Multimodal
        ext = file_path.split('.')[-1].lower()
        doc_exts = ['pdf', 'docx', 'pptx', 'xlsx', 'md', 'txt', 'html']
        media_exts = [
            'mp4', 'mpeg', 'mov', 'avi', 'flv', 'mpg', 'webm', 'wmv', '3gp',  # Video
            'mp3', 'wav', 'aac', 'm4a', 'ogg', 'flac',                       # Audio
            'jpg', 'png', 'jpeg', 'webp', 'heic', 'heif'                      # Image
        ]

        if ext in doc_exts:
            # 1. Parse Document via Docling
            markdown_content = self._convert_file_to_markdown(file_path)
            # 2. Run Agents on text
            summary = self._run_detective_agent(markdown_content)
            graph_data = self._run_analyst_agent(markdown_content)
            return {"summary": summary, "graph": graph_data}
        elif ext in media_exts:
            # Determine mime type roughly
            mime_type = "application/octet-stream"
            if ext in ['mp4', 'mov', 'avi']: mime_type = "video/mp4"
            elif ext in ['mp3', 'wav', 'aac']: mime_type = "audio/mpeg"
            elif ext in ['jpg', 'png', 'jpeg', 'webp']: mime_type = "image/jpeg"
            
            return self._process_multimodal(file_path, mime_type)
        else:
            # Fallback to multimodal for unknown types
            return self._process_multimodal(file_path, "application/octet-stream")

ai_service = AIService()
