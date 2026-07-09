import os
import json
import uuid
import requests

BASE_URL = "http://127.0.0.1:8001/api/v1"
CASE_ID = "TESTCASE-RUN-001"
TMP_DIR = "tmp_test_files"

os.makedirs(TMP_DIR, exist_ok=True)

sample_files = [
    {
        "filename": "sample.txt",
        "content": b"This is a text evidence sample. The suspect confessed to the theft in the journal entry.",
        "content_type": "text/plain",
    },
    {
        "filename": "sample.pdf",
        "content": b"%PDF-1.4\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n4 0 obj << /Length 44 >> stream\nBT /F1 24 Tf 72 720 Td (Hello PDF upload test.) Tj ET\nendstream endobj\n5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\nxref\n0 6\n0000000000 65535 f \n0000000010 00000 n \n0000000061 00000 n \n0000000112 00000 n \n0000000207 00000 n \n0000000296 00000 n \ntrailer << /Root 1 0 R /Size 6 >>\nstartxref\n366\n%%EOF\n",
        "content_type": "application/pdf",
    },
    {
        "filename": "sample.docx",
        "content": None,
        "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
    {
        "filename": "sample.png",
        "content": b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x02\x00\x01E\xf3\x02\xb5\x00\x00\x00\x00IEND\xaeB`\x82",
        "content_type": "image/png",
    },
    {
        "filename": "sample.mp4",
        "content": b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42mp41isom\x00\x00\x00\x08free\x00\x00\x02\x3Cmdat\x00\x00\x00\x00",
        "content_type": "video/mp4",
    },
]

# Build a simple minimal docx file if python-docx is unavailable
try:
    import docx
    from docx import Document
    doc = Document()
    doc.add_paragraph("This is a DOCX evidence sample describing an incident report.")
    doc_bytes = None
    from io import BytesIO
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    doc_bytes = buf.read()
    for item in sample_files:
        if item["filename"] == "sample.docx":
            item["content"] = doc_bytes
except Exception:
    from zipfile import ZipFile
    from io import BytesIO
    docx_bytes = BytesIO()
    with ZipFile(docx_bytes, "w") as z:
        z.writestr("[Content_Types].xml", "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\"><Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/><Default Extension=\"xml\" ContentType=\"application/xml\"/><Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/></Types>")
        z.writestr("_rels/.rels", "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"word/document.xml\"/></Relationships>")
        z.writestr("word/document.xml", "<?xml version=\"1.0\" encoding=\"UTF-8\"?><w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\"><w:body><w:p><w:r><w:t>This is a DOCX evidence sample describing an incident report.</w:t></w:r></w:p></w:body></w:document>")
    docx_bytes.seek(0)
    for item in sample_files:
        if item["filename"] == "sample.docx":
            item["content"] = docx_bytes.read()

results = []

for item in sample_files:
    path = os.path.join(TMP_DIR, item["filename"])
    with open(path, "wb") as f:
        f.write(item["content"])
    with open(path, "rb") as f:
        files = {"file": (item["filename"], f, item["content_type"])}
        data = {"case_id": CASE_ID}
        print(f"Uploading {item['filename']} ({item['content_type']})...")
        resp = requests.post(f"{BASE_URL}/evidence/upload", files=files, data=data, timeout=60)
        print(resp.status_code, resp.text)
        try:
            results.append((item["filename"], resp.json()))
        except Exception as exc:
            print("JSON decode failed", exc)
            results.append((item["filename"], None))

print("\n--- Evidence list for case ---")
resp = requests.get(f"{BASE_URL}/evidence/{CASE_ID}", timeout=30)
print(resp.status_code)
try:
    evidence_list = resp.json()
    print(json.dumps(evidence_list, indent=2))
except Exception as exc:
    print("Failed to parse evidence list", exc)
    evidence_list = []

print("\n--- Assistant chat response ---")
question = "Summarize this case."
resp = requests.post(f"{BASE_URL}/assistant/chat", json={"case_id": CASE_ID, "question": question}, timeout=60)
print(resp.status_code)
try:
    print(json.dumps(resp.json(), indent=2))
except Exception as exc:
    print("Failed to parse chat response", exc)

print("\n--- Done ---")
