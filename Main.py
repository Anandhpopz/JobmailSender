import streamlit as st
import requests
import base64
import json
import os
import time
import smtplib
from email.message import EmailMessage

# =========================
# --- CONFIGURATION ---
# =========================

api_key = st.secrets["api_key"]
sender_email = "anandhakrishnancareer@gmail.com"
sender_password = st.secrets["sender_password"]

GEMINI_MODEL_NAME = "gemini-2.5-flash-preview-09-2025"
API_URL_TEMPLATE = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL_NAME}:generateContent?key="
MAX_RETRIES = 5

# ===== CV LOCATION (EDIT THIS) =====
CV_FOLDER_PATH = r"/content/drive/MyDrive/Resume"  # 🔴 CHANGE THIS
CV_FILE_NAME = "AnandhaKrishnanS_CV.pdf"                     # 🔴 EXACT FILE NAME
# ====================================

# =========================
# --- Streamlit Setup ---
# =========================
st.set_page_config(page_title="AI Job Mail Assistant", layout="wide")

st.markdown("""
<style>
    .reportview-container { background: #f0f2f6; }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 10px;
        padding: 10px 20px;
        font-weight: bold;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #45a049;
        transform: scale(1.02);
    }
</style>
""", unsafe_allow_html=True)

# =========================
# --- Helper Functions ---
# =========================

def file_to_base64(uploaded_file):
    if uploaded_file is None:
        return None
    return base64.b64encode(uploaded_file.getvalue()).decode("utf-8")


def call_gemini_api(api_key, prompt, image_data_base64=None):
    if not api_key:
        st.error("Missing Gemini API key.")
        return {"MAIL_ID": "", "SUBJECT_LINE": "", "EMAIL_CONTENT": ""}

    headers = {"Content-Type": "application/json"}
    api_url = API_URL_TEMPLATE + api_key

    parts = [{"text": prompt}]
    if image_data_base64:
        parts.append({
            "inlineData": {
                "mimeType": "image/jpeg",
                "data": image_data_base64
            }
        })

    payload = {"contents": [{"parts": parts}]}

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(api_url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            result = response.json()

            text_output = (
                result.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )

            try:
                return json.loads(text_output)
            except:
                return {
                    "MAIL_ID": "",
                    "SUBJECT_LINE": "",
                    "EMAIL_CONTENT": text_output
                }

        except requests.exceptions.RequestException as e:
            if hasattr(response, "status_code") and response.status_code == 429 and attempt < MAX_RETRIES - 1:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
            else:
                st.error(f"API Error: {e}")
                return {"MAIL_ID": "", "SUBJECT_LINE": "", "EMAIL_CONTENT": ""}

    return {"MAIL_ID": "", "SUBJECT_LINE": "", "EMAIL_CONTENT": ""}


def send_email(sender_email, sender_password, to_email, subject, body):
    msg = EmailMessage()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body, subtype="plain", charset="utf-8")

    # ===== Attach CV from Fixed Folder =====
    cv_path = os.path.join(CV_FOLDER_PATH, CV_FILE_NAME)

    if os.path.exists(cv_path):
        try:
            with open(cv_path, "rb") as f:
                msg.add_attachment(
                    f.read(),
                    maintype="application",
                    subtype="pdf",
                    filename=CV_FILE_NAME
                )
                st.info(f"📎 Attached CV: {CV_FILE_NAME}")
        except Exception as e:
            st.error(f"Failed to attach CV: {e}")
            return "❌ CV attachment failed."
    else:
        st.error(f"❌ CV not found at: {cv_path}")
        return "❌ CV file not found."

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return "✅ Email with CV sent successfully!"
    except Exception as e:
        return f"❌ Failed to send email: {str(e)}"


# =========================
# --- Streamlit App ---
# =========================

def app():
    st.title("📨 AI-Powered Job Mail Sender")
    st.markdown("Upload job vacancy image → AI extracts details → Email sent automatically with CV attached.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1️⃣ Upload Job Image")
        uploaded_file = st.file_uploader("Upload image (JPG/PNG)", type=["jpg", "jpeg", "png"])
        if uploaded_file:
            st.image(uploaded_file, caption="Uploaded Job Posting", use_container_width=True)
            image_b64 = file_to_base64(uploaded_file)
        else:
            image_b64 = None

    with col2:
        st.subheader("2️⃣ AI Instructions")
        default_prompt = """
Analyze the uploaded job vacancy image.

Return ONLY valid JSON:
{
  "MAIL_ID": "",
  "SUBJECT_LINE": "",
  "EMAIL_CONTENT": ""
}

Applicant:
Name: Anandha Krishnan S
Education: MSc Computer Science
Skills: Python, ML, SQL, Power BI, TensorFlow, PyTorch
Tone: Professional, friendly, concise (120-150 words)
"""
        user_prompt = st.text_area("Prompt", value=default_prompt, height=350)

    if st.button("🚀 Extract & Analyze"):
        if not uploaded_file:
            st.error("Upload an image first.")
        else:
            with st.spinner("Analyzing..."):
                result = call_gemini_api(api_key, user_prompt, image_b64)
            st.session_state["analysis_result"] = result

    if "analysis_result" in st.session_state:
        parsed = st.session_state["analysis_result"]

        st.markdown("---")
        st.subheader("📋 Extracted Details")
        st.json(parsed)

        st.write(f"📩 To: {parsed.get('MAIL_ID','')}")
        st.write(f"🧾 Subject: {parsed.get('SUBJECT_LINE','')}")
        st.text_area("✉️ Email Body", parsed.get("EMAIL_CONTENT",""), height=200)

        if st.button("📤 Send Email"):
            if not parsed.get("MAIL_ID"):
                st.error("Recipient email not found.")
            else:
                with st.spinner("Sending email..."):
                    status = send_email(
                        sender_email,
                        sender_password,
                        parsed["MAIL_ID"],
                        parsed["SUBJECT_LINE"],
                        parsed["EMAIL_CONTENT"]
                    )

                if "✅" i
