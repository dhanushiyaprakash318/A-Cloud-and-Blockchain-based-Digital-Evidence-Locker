from fpdf import FPDF
import os
import tempfile

class ForensicReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Deepfake Forensic Report (Hybrid System)', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_report(data, output_path='forensic_report.pdf'):
    pdf = ForensicReport()
    pdf.add_page()
    
    # Title Info
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f"File Name: {data.get('filename', 'Unknown')}", 0, 1)
    pdf.cell(0, 10, f"Analysis Date: {data.get('date', 'N/A')}", 0, 1)
    
    # URL Forensic Info (if available)
    if data.get('url_info'):
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, "URL Intelligence Report:", 0, 1)
        pdf.set_font('Arial', '', 10)
        
        url_info = data['url_info']
        
        # Redirect chain
        if url_info.get('redirect_info'):
            redirect_info = url_info['redirect_info']
            pdf.cell(0, 8, f"Redirect Count: {redirect_info['redirect_count']}", 0, 1)
            if redirect_info['redirect_count'] > 0:
                pdf.cell(0, 8, f"Final URL: {redirect_info['final_url'][:80]}...", 0, 1)
        
        # Content type
        if url_info.get('content_info'):
            content_info = url_info['content_info']
            pdf.cell(0, 8, f"Content Type: {content_info['content_type'].upper()}", 0, 1)
    
    # Security Info (if available)
    if data.get('security_info'):
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, "Security Analysis:", 0, 1)
        pdf.set_font('Arial', '', 10)
        
        sec_info = data['security_info']
        risk_level = sec_info.get('risk_level', 'unknown').upper()
        risk_score = sec_info.get('risk_score', 0)
        
        # Color code based on risk
        if risk_level in ['CRITICAL', 'HIGH']:
            pdf.set_text_color(255, 0, 0)
        elif risk_level == 'MEDIUM':
            pdf.set_text_color(255, 165, 0)
        else:
            pdf.set_text_color(0, 128, 0)
        
        pdf.cell(0, 8, f"Risk Level: {risk_level} (Score: {risk_score}/100)", 0, 1)
        pdf.set_text_color(0, 0, 0)
        
        flags = sec_info.get('flags', [])
        if flags:
            pdf.cell(0, 8, "Security Flags:", 0, 1)
            for flag in flags[:5]:  # Limit to 5 flags
                pdf.cell(0, 6, f"  - {flag}", 0, 1)
    
    pdf.ln(5)
    
    flags = data.get('quality', {}).get('flags', [])
    flag_str = ", ".join(flags) if flags else "None"
    pdf.cell(0, 10, f"Quality Flags: {flag_str}", 0, 1)
    pdf.ln(5)
    
    # Result
    label = data.get('label', 'Unknown')
    color = (0, 128, 0) if "REAL" in label else (255, 0, 0)
    if "SUSPICIOUS" in label:
        color = (255, 165, 0)
        
    pdf.set_text_color(*color)
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f"Prediction: {label}", 0, 1)
    pdf.set_text_color(0, 0, 0)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f"Final Fake Probability: {data.get('fake_prob', 0)*100:.2f}%", 0, 1)
    
    # Breakdown
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 10, "Component Breakdown:", 0, 1)
    pdf.set_font('Arial', '', 10)
    
    breakdown = data.get('breakdown', {})
    for k, v in breakdown.items():
        val = f"{v*100:.2f}%" if isinstance(v, (float, int)) else str(v)
        pdf.cell(0, 8, f" - {k}: {val}", 0, 1)
    pdf.ln(10)
    
    # Images
    # We need to save PIL images to temp files
    temp_files = []
    
    try:
        if data.get('original_face'):
            pdf.cell(0, 10, "Analyzed Face & GradCAM Heatmap:", 0, 1)
            
            face_path = tempfile.mktemp(suffix='.jpg')
            data['original_face'].save(face_path)
            temp_files.append(face_path)
            pdf.image(face_path, x=10, w=80)
            
            if data.get('heatmap'):
                hm_path = tempfile.mktemp(suffix='.jpg')
                data['heatmap'].save(hm_path)
                temp_files.append(hm_path)
                pdf.image(hm_path, x=100, y=pdf.get_y()-80, w=80)
                
            pdf.ln(85)
            
        if data.get('ela_image'):
            pdf.add_page()
            pdf.cell(0, 10, "Error Level Analysis (ELA):", 0, 1)
            ela_path = tempfile.mktemp(suffix='.jpg')
            data['ela_image'].save(ela_path)
            temp_files.append(ela_path)
            pdf.image(ela_path, x=10, w=150)
            pdf.ln(10)

    except Exception as e:
        pdf.cell(0, 10, f"Error adding images: {str(e)}", 0, 1)
        
    pdf.output(output_path)
    
    # Cleanup
    for f in temp_files:
        if os.path.exists(f):
            try: os.remove(f)
            except: pass

    return output_path
