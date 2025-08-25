import streamlit as st
import requests, base64

API_BASE = "http://localhost:8000/api"

st.title("🤖 AI Resume Chatbot (HuggingFace + Gmail)")
# --- User Info Sidebar ---
#st.sidebar.header("Your Info")
#sender_name = st.sidebar.text_input("Your Name", value="Your Name")
#sender_email = st.sidebar.text_input("Your Email", value="your@email.com")
#sender_linkedin = st.sidebar.text_input("LinkedIn URL", value="https://linkedin.com/in/yourprofile")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Display previous messages
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# User input (chat)
if user_input := st.chat_input("Paste the JD or ask me to apply for a role..."):
    # Save user message
    st.session_state["messages"].append({"role": "user", "content": user_input})

    # Step 1: Call classify API
    classify_res = requests.post(f"{API_BASE}/classify", json={"text": user_input})
    job_data = classify_res.json()

    jobTitle = job_data.get("jobTitle") or ""
    jobType = job_data.get("jobType") or ""
    company = job_data.get("company") or ""
    recruiter = job_data.get("recruiter") or ""
    recruiterEmail = job_data.get("recruiterEmail") or ""
    st.session_state["recruiterEmail"] = recruiterEmail
    jd_summary = job_data.get("jd_summary") or ""

    # Step 2: Call generate-email API
    payload = {
        "senderName": "siva krishna Bayya",   # could be pre-filled from config
        "senderEmail": "sivabayya4208@gmail.com",
        "linkedIn": "https://www.linkedin.com/in/siva-bayya-50180810/",
        "jobTitle": jobTitle,
        "company": company,
        "recruiterName": recruiter,
        "recruiterEmail": recruiterEmail,
        "JD_Summary": jd_summary
    }
    email_res = requests.post(f"{API_BASE}/generate-email", json=payload)
    email_data = email_res.json()

    draft_subject = email_data.get("subject", "Job Application")
    draft_body = email_data.get("body", "")

    # Assistant response
    reply = f"""📌 **Job Classification**
- Job Title: {jobTitle}
- Job Type: {jobType}
- Company: {company}
- Recruiter: {recruiter}

✉️ **Draft Email**
**Subject:** {draft_subject}

{draft_body}

"""
st.session_state["messages"].append({"role": "assistant", "content": reply})
st.info("Would you like me to send this email now? (Please upload your resume first.)")
st.rerun()

# Resume upload + send email (after draft generated)
if st.session_state.get("messages") and "Draft Email" in st.session_state["messages"][-1]["content"]:
    resume = st.file_uploader("📎 Upload Resume (PDF)", type="pdf")
    if st.button("Send Email"):
        if not resume:
            st.error("Please upload a resume first.")
        else:
            # Last assistant message has draft email
            email_text = st.session_state["messages"][-1]["content"]
            draft_subject = email_text.split("**Subject:**")[1].split("\n")[0].strip()
            draft_body = "\n".join(email_text.split("**Subject:**")[1].split("\n")[1:]).strip()

            b64_resume = base64.b64encode(resume.read()).decode()
            payload = {
                #"to": recruiterEmail if recruiterEmail else "recruiter@email.com",  # can be detected or user-specified
                "to": st.session_state.get("recruiterEmail", "recruiter@email.com"),
                "subject": draft_subject,
                "body": draft_body,
                "attachment": f"data:application/pdf;base64,{b64_resume}",
                "fileName": resume.name,
            }
            res = requests.post(f"{API_BASE}/send-email", json=payload)
            if res.ok:
                st.success("✅ Email sent successfully!")
