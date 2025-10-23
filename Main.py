import streamlit as st
import requests
import base64
import json
import time
import smtplib
from io import BytesIO
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
api_key = st.secrets["api_key"]
sender_email ="anandhakrishnancareer@gmail.com"
sender_password = st.secrets["sender_password"]
# --- Configuration ---
GEMINI_MODEL_NAME = "gemini-2.5-flash-preview-09-2025"
API_URL_TEMPLATE = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL_NAME}:generateContent?key="
MAX_RETRIES = 5

# --- Streamlit Setup ---
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
    .stTextInput>div>div>input, textarea {
        border-radius: 8px;
        border: 1px solid #ccc;
    }
</style>
""", unsafe_allow_html=True)


# --- Helper Functions ---
def file_to_base64(uploaded_file):
    """Convert uploaded file to base64 string."""
    if uploaded_file is None:
        return None
    bytes_data = uploaded_file.getvalue()
    return base64.b64encode(bytes_data).decode("utf-8")


def call_gemini_api(api_key, prompt, image_data_base64=None):
    """Call Gemini API with exponential backoff and expect structured JSON."""
    if not api_key:
        st.error("Please enter your Gemini API Key.")
        return {"MAIL_ID": "", "SUBJECT_LINE": "", "EMAIL_CONTENT": "API key missing."}

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

            # Try to parse JSON output directly
            try:
                return json.loads(text_output)
            except json.JSONDecodeError:
                # Try to extract JSON substring if Gemini added extra text
                import re
                match = re.search(r"\{.*\}", text_output, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group(0))
                    except json.JSONDecodeError:
                        return {"MAIL_ID": "", "SUBJECT_LINE": "", "EMAIL_CONTENT": text_output}
                else:
                    return {"MAIL_ID": "", "SUBJECT_LINE": "", "EMAIL_CONTENT": text_output}

        except requests.exceptions.RequestException as e:
            if response.status_code == 429 and attempt < MAX_RETRIES - 1:
                wait_time = 2 ** attempt
                st.warning(f"Rate limit hit. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                st.error(f"API Request Failed: {e}")
                return {"MAIL_ID": "", "SUBJECT_LINE": "", "EMAIL_CONTENT": "Error processing request."}
    return {"MAIL_ID": "", "SUBJECT_LINE": "", "EMAIL_CONTENT": "Failed after multiple retries."}


def send_email(sender_email, sender_password, to_email, subject, body):
    """Send an email using Gmail SMTP and automatically attach CV.pdf from repo."""
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    # --- Attach CV PDF from local repo ---
    cv_path = os.path.join(os.getcwd(), "CV_AnandhaKrishnanS.pdf")  # change filename if needed
    if os.path.exists(cv_path):
        try:
            with open(cv_path, "rb") as f:
                part = MIMEApplication(f.read(), _subtype="pdf")
                part.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=os.path.basename(cv_path)
                )
                msg.attach(part)
                st.info(f"📎 Attached CV: {os.path.basename(cv_path)}")
        except Exception as e:
            st.warning(f"⚠️ Failed to attach CV: {e}")
    else:
        st.warning("⚠️ CV file not found in repo path.")

    # --- Send email ---
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            return "✅ Email with CV sent successfully!"
    except Exception as e:
        return f"❌ Failed to send email: {str(e)}"



# --- Streamlit App ---
def app():
    st.title("📨 AI-Powered Job Mail Sender (JSON Enhanced)")
    st.markdown("Upload a job vacancy image → AI extracts structured email details → Send automatically.")

    # Sidebar
    
        # st.header("🔑 Gemini API Key")
    
    # st.markdown("⚠️ Use a Gmail *App Password*, not your main password.")

    # Main columns
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
        st.subheader("2️⃣ Define AI Task")
        default_prompt = """
Analyze the uploaded image containing job vacancy details.

Extract and generate the following as a valid JSON response:
{
  "MAIL_ID": "<official email ID found in the image or inferred>",
  "SUBJECT_LINE": "<short professional subject line for applying>",
  "EMAIL_CONTENT": "<well-written job application email in the same style as below>"
}

About the applicant (for context):
- Name: Anandha Krishnan S
- Education: Master’s in Computer Science, University of Kerala
- Skills: Python, Machine Learning, Data Analytics, SQL, Power BI, TensorFlow, PyTorch
- Experience: Projects in AI/ML including credit card transaction analysis, currency valuation prediction (LSTM), gesture recognition volume control, diabetic retinopathy detection (CNN), fake news prediction (SVM), employee attrition prediction.
- Interests: AI/ML, Data Science, Full-stack development, building real-world AI solutions
- Tone preference: Friendly, respectful, and professional, concise (120–150 words), first-person

Guidelines for EMAIL_CONTENT:
- Use a friendly, respectful, and professional tone.
- Include:
  1. Warm greeting addressing the recipient (if name found).
  2. Enthusiastic opening applying for the mentioned role and company.
  3. 1–2 sentences summarizing applicant’s skills and background (use above About Me info).
  4. Mention attached resume and willingness to discuss.
  5. Courteous closing with applicant name.
- Keep it concise (120–150 words), first-person, natural tone.

Example email format:
Hi Tresa / Anjana,

I hope you’re doing well. I’m excited to apply for the AI Intern position at ArtTech Group. I’m passionate about AI/ML and eager to contribute to innovative projects, explore new frameworks, and build AI-driven solutions alongside your team.

I recently graduated with a Master’s in CS and have experience with Python and ML libraries. I’m enthusiastic about learning, collaborating, and applying my skills to real-world AI initiatives.

Please find my resume attached. I would love the opportunity to discuss how I can contribute to your team.

Looking forward to your response.

Best regards,
Anandha Krishnan S
"""

        user_prompt = st.text_area("Custom Prompt (optional)", value=default_prompt, height=400)

    # Process Button
    if st.button("🚀 Extract & Analyze"):
        if not uploaded_file:
            st.error("Please upload an image first.")
        elif not api_key:
            st.error("Please enter your Gemini API key.")
        else:
            with st.spinner("Analyzing image with Gemini..."):
                result_json = call_gemini_api(api_key, user_prompt, image_b64)
            st.session_state["analysis_result"] = result_json

    # Show extracted info
    if "analysis_result" in st.session_state:
        parsed = st.session_state["analysis_result"]

        st.markdown("---")
        st.subheader("3️⃣ Extracted Details (from Gemini JSON)")
        st.json(parsed)
        st.markdown("---")

        st.write(f"📩 **To:** {parsed.get('MAIL_ID', 'Not found')}")
        st.write(f"🧾 **Subject:** {parsed.get('SUBJECT_LINE', 'Not found')}")
        st.text_area("✉️ **Email Body:**", parsed.get('EMAIL_CONTENT', ''), height=200)

        if st.button("📤 Send Email Automatically"):
            if not sender_email or not sender_password:
                st.error("Please enter your sender email and app password in sidebar.")
            elif not parsed.get("MAIL_ID"):
                st.error("No recipient email found in AI output.")
            else:
                with st.spinner("Sending email..."):
                    status = send_email(
                        sender_email,
                        sender_password,
                        parsed["MAIL_ID"],
                        parsed["SUBJECT_LINE"],
                        parsed["EMAIL_CONTENT"]
                    )
                st.success(status)


if __name__ == "__main__":
    app()





