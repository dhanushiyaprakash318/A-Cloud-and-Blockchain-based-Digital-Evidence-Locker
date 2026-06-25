import streamlit as st
import os
import shutil
from datetime import datetime
from inference.predictor import HybridPredictor
from inference.audio_predictor import AudioPredictor
from utils.report_generator import generate_report
from utils.url_loader import download_from_url

# Page Config
st.set_page_config(page_title="Deepfake Hybrid Forensic Tool", layout="wide")
st.title("🕵️‍♂️ Deepfake & Manipulation Forensic Tool (Hybrid)")

st.sidebar.markdown("### Model System")
st.sidebar.info(
    "**Hybrid Ensemble**:\n"
    "- EfficientNet-B0 (35%)\n"
    "- Xception (45%)\n"
    "- ELA (10%)\n"
    "- Noiseprint (10%)"
)

# Load Model
@st.cache_resource
def load_predictor():
    return HybridPredictor(device='cpu')

@st.cache_resource
def load_audio_predictor():
    return AudioPredictor()

predictor = load_predictor()
audio_predictor = load_audio_predictor()

# Main Interface with Tabs
st.write("Upload a file or paste a URL to analyze authenticity.")

tab1, tab2, tab3 = st.tabs(["📁 Upload File", "🔗 Paste URL", "🎵 Audio Input"])

filename = None
url_forensic_info = None  # Store URL info for report
security_forensic_info = None  # Store security info for report

with tab1:
    uploaded_file = st.file_uploader("Choose a file", type=["jpg", "png", "jpeg", "mp4", "mov", "avi"])
    
    if uploaded_file is not None:
        # Save uploaded file to temp
        with open("temp_input", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Determine extension
        ext = uploaded_file.name.split('.')[-1]
        filename = f"temp_input.{ext}"
        shutil.move("temp_input", filename)

with tab2:
    st.markdown("### 🛡️ URL Phishing Detector")
    st.caption("Check if a URL is safe or phishing - no download required")
    
    url_input = st.text_input("Enter URL to check for phishing")
    
    st.divider()
    st.markdown("### 📥 Deepfake Content Analysis")
    st.caption("Download video/image from this URL and run Deepfake Detection")

    if st.button("🚀 Analyze Media Content"):
        with st.spinner("Downloading media from URL..."):
            res = download_from_url(url_input)
            
            if res['file_path']:
                filename = res['file_path']
                url_forensic_info = res['url_info']
                st.success(f"Successfully downloaded: {os.path.basename(filename)}")
            else:
                st.error(f"Download failed: {res.get('error')}")

    if st.button("🔍 Check URL Security") and url_input:
        with st.spinner("Analyzing URL security..."):
            try:
                # Import security module directly
                from utils.url_security import URLSecurity
                
                sec = URLSecurity()
                sec_info = sec.analyze_url(url_input)
                
                risk_score = sec_info['risk_score']
                risk_level = sec_info['risk_level'].upper()
                is_phishing = sec_info['is_phishing']
                
                # === VERDICT ===
                st.markdown("---")
                if is_phishing or risk_score >= 60:
                    st.error(f"### 🚨 PHISHING / MALICIOUS")
                    verdict_color = "red"
                elif risk_score >= 30:
                    st.warning(f"### ⚠️ SUSPICIOUS")
                    verdict_color = "orange"
                else:
                    st.success(f"### ✅ SAFE")
                    verdict_color = "green"
                
                # === RISK SCORE with Visual Meter ===
                st.markdown(f"**Risk Score: {risk_score}/100**")
                
                # Visual risk meter using progress bar
                if risk_score >= 70:
                    st.progress(risk_score / 100, text=f"CRITICAL RISK - {risk_score}/100")
                elif risk_score >= 50:
                    st.progress(risk_score / 100, text=f"HIGH RISK - {risk_score}/100")
                elif risk_score >= 30:
                    st.progress(risk_score / 100, text=f"MEDIUM RISK - {risk_score}/100")
                else:
                    st.progress(risk_score / 100, text=f"LOW RISK - {risk_score}/100")
                
                # === RISK TREND (Visual Gauge) ===
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    if risk_score < 10:
                        st.metric("SAFE", "✓", delta="0-9", delta_color="normal")
                    else:
                        st.metric("SAFE", "", delta="0-9", delta_color="off")
                with col2:
                    if 10 <= risk_score < 30:
                        st.metric("LOW", "⚠️", delta="10-29", delta_color="normal")
                    else:
                        st.metric("LOW", "", delta="10-29", delta_color="off")
                with col3:
                    if 30 <= risk_score < 50:
                        st.metric("MEDIUM", "⚠️", delta="30-49", delta_color="inverse")
                    else:
                        st.metric("MEDIUM", "", delta="30-49", delta_color="off")
                with col4:
                    if 50 <= risk_score < 70:
                        st.metric("HIGH", "🚨", delta="50-69", delta_color="inverse")
                    else:
                        st.metric("HIGH", "", delta="50-69", delta_color="off")
                with col5:
                    if risk_score >= 70:
                        st.metric("CRITICAL", "🔴", delta="70-100", delta_color="inverse")
                    else:
                        st.metric("CRITICAL", "", delta="70-100", delta_color="off")
                
                st.markdown("---")
                
                # === SECURITY FLAGS ===
                if sec_info['flags']:
                    st.markdown("**🚩 Security Flags:**")
                    for flag in sec_info['flags']:
                        if "BRAND IMPERSONATION" in flag:
                            st.error(f"• {flag}")
                        elif "Fake" in flag or "Official" in flag:
                            st.warning(f"• {flag}")
                        elif "Suspicious" in flag or "Phishing" in flag:
                            st.warning(f"• {flag}")
                        else:
                            st.info(f"• {flag}")
                
                # === RECOMMENDATION ===
                st.markdown("---")
                if risk_score >= 60:
                    st.error("⛔ **RECOMMENDATION:** Do NOT visit this URL. Likely phishing/scam.")
                elif risk_score >= 30:
                    st.warning("⚠️ **RECOMMENDATION:** Exercise caution. Verify before proceeding.")
                else:
                    st.success("✅ **RECOMMENDATION:** URL appears safe.")
                
                # Store for potential report
                url_forensic_info = None
                security_forensic_info = sec_info
                filename = None  # No download
                    
            except Exception as e:
                st.error(f"Analysis error: {e}")
                import traceback
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())

with tab3:
    st.markdown("### 🎙️ Audio Forensics")
    st.caption("Upload audio files to detect synthesized speech or deepfake audio")
    
    audio_file = st.file_uploader("Choose an audio file", type=["wav", "mp3", "flac", "m4a"], key="audio_uploader")
    
    if audio_file:
        st.audio(audio_file, format='audio/wav')
        
        # Save audio to temp
        with open("temp_audio", "wb") as f:
            f.write(audio_file.getbuffer())
        
        # Determine extension
        audio_ext = audio_file.name.split('.')[-1]
        audio_filename = f"temp_audio.{audio_ext}"
        shutil.move("temp_audio", audio_filename)
        
        if st.button("🔍 Analyze Audio Authenticity"):
            with st.spinner("Decoding Audio Spectrograms..."):
                try:
                    audio_results = audio_predictor.predict(audio_filename)
                    
                    # Display Results
                    a_label = audio_results['label']
                    a_color = "green" if a_label == "REAL" else "red"
                    
                    st.markdown(f"<h2 style='text-align: center; color: {a_color};'>{a_label}</h2>", unsafe_allow_html=True)
                    
                    a_col1, a_col2 = st.columns(2)
                    with a_col1:
                        st.metric("Fake Probability", f"{audio_results['fake_prob']*100:.2f}%")
                    with a_col2:
                        st.metric("Real Probability", f"{audio_results['real_prob']*100:.2f}%")
                    
                    # Breakdown
                    st.divider()
                    st.subheader("🔊 Audio Feature Breakdown")
                    st.json(audio_results['breakdown'])
                    
                except Exception as e:
                    st.error(f"Audio analysis error: {e}")
                finally:
                    if os.path.exists(audio_filename):
                        os.remove(audio_filename)


# Process the file if available
if filename is not None and os.path.exists(filename):
    st.info("Running Hybrid Analysis... (Checking Quality, EffNet, Xception, Forensics)")
    
    # Progress bar
    my_bar = st.progress(0)
    
    # Run Prediction
    try:
        results = predictor.predict(filename)
        my_bar.progress(100)
        
        # Display Results
        label = results['label']
        color = "green" if "REAL" in label else "red"
        if "SUSPICIOUS" in label: color = "orange"
        
        st.markdown(f"<h2 style='text-align: center; color: {color};'>{label}</h2>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
             st.metric("Final Fake Score", f"{results['fake_prob']*100:.2f}%")
        with col2:
             quality_data = results.get('quality') or {}
             q_score = quality_data.get('quality_score', 1.0)
             st.metric("Quality Score", f"{q_score*100:.0f}%", help="Lower score means image is blurry/dark")
        with col3:
             flags = ", ".join(quality_data.get('flags', []))
             st.text(f"Flags: {flags if flags else 'None'}")
             
        # Detailed Breakdown - EXPLAINABILITY
        st.divider()
        st.subheader("🔍 Model Breakdown & Explainability")
        with st.expander("See Detailed Model Scores", expanded=True):
            breakdown = results['breakdown']
            
            # Create columns for each model
            b_col1, b_col2, b_col3, b_col4 = st.columns(4)
            
            with b_col1:
                eff_score = breakdown.get('EfficientNet', 0)
                st.metric("EfficientNet", f"{eff_score*100:.1f}%" if isinstance(eff_score, float) else str(eff_score))
            
            with b_col2:
                xcp_score = breakdown.get('Xception', 'N/A')
                st.metric("Xception", f"{xcp_score*100:.1f}%" if isinstance(xcp_score, float) else str(xcp_score))
            
            with b_col3:
                ela_score = breakdown.get('ELA_Score', 0)
                st.metric("ELA Score", f"{ela_score*100:.1f}%")
            
            with b_col4:
                noise_score = breakdown.get('Noiseprint_Score', 0)
                st.metric("Noiseprint", f"{noise_score*100:.1f}%")
            
        st.divider()
        
        # Visuals
        st.subheader("📊 Visual Forensics")
        v_col1, v_col2 = st.columns(2)
        
        with v_col1:
            if results.get('original_face'):
                st.image(results['original_face'], caption="Analyzed Face (Highest Risk)")
            else:
                st.warning("No face detected.")
                
        with v_col2:
            if results.get('heatmap'):
                st.image(results['heatmap'], caption="🔥 Attention Heatmap (EfficientNet GradCAM)")
                
        if results.get('ela_image'):
            st.subheader("🔬 Image Manipulation Analysis")
            e_col1, e_col2 = st.columns(2)
            with e_col1:
                st.image(results['ela_image'], caption="Error Level Analysis (ELA)")
            with e_col2:
                if results.get('noiseprint'):
                    st.image(results['noiseprint'], caption="Noiseprint Analysis")
        
        # Report Generation
        st.divider()
        st.subheader("📄 Report")
        if st.button("Generate Forensic PDF"):
            report_data = results.copy()
            report_data['filename'] = filename
            report_data['date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Include URL forensic info if available
            if url_forensic_info:
                report_data['url_info'] = url_forensic_info
            if security_forensic_info:
                report_data['security_info'] = security_forensic_info
            
            pdf_path = generate_report(report_data)
            
            with open(pdf_path, "rb") as f:
                st.download_button("Download Report", f, file_name="forensic_report.pdf")
                
    except Exception as e:
        st.error(f"Error during analysis: {e}")
        import traceback
        st.code(traceback.format_exc())
    
    # Cleanup
    # os.remove(filename) 
