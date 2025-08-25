import streamlit as st
import requests, base64

API_BASE = "http://localhost:8000/api"

st.title("🤖 AI Resume Sender (HuggingFace + Gmail)")

jd_text = st.text_area("Paste Job Description", height=200)

if st.button("Classify Job"):
    res = requests.post(f"{API_BASE}/classify", json={"text": jd_text})
    st.session_state["job"] = res.json()
    st.success(f"Job Type: {st.session_state['job']['jobType']}")

with st.form("emailform"):
    jobTitle = st.text_input("Job Title",value=st.session_state["job"].get("jobTitle", "") if "job" in st.session_state else "")

    company = st.text_input("Company")
    recruiterName = st.text_input("Recruiter Name")
    recruiterEmail = st.text_input("Recruiter Email")
    senderName = st.text_input("Your Name")
    senderEmail = st.text_input("Your Email")
    linkedIn = st.text_input("LinkedIn")
    resume = st.file_uploader("Upload Resume (PDF)", type="pdf")

    gen_btn = st.form_submit_button("Generate Email")
    if gen_btn:
        payload = {
            "senderName": senderName,
            "senderEmail": senderEmail,
            "linkedIn": linkedIn,
            "jobTitle": jobTitle,
            "company": company,
            "recruiterName": recruiterName,
            "JD_Summary": st.session_state["job"]["jd_summary"] 
        }
        res = requests.post(f"{API_BASE}/generate-email", json=payload)
        st.session_state["emailDraft"] = res.json()

if "emailDraft" in st.session_state:
    st.subheader("📧 Email Draft")
    st.text_area("Email Body", st.session_state["emailDraft"]["body"], height=250)

    if st.button("Send Email"):
        if not resume:
            st.error("Please upload a resume first.")
        else:
            b64_resume = base64.b64encode(resume.read()).decode()
            payload = {
                "to": recruiterEmail,
                "subject": st.session_state["emailDraft"]["subject"],
                "body": st.session_state["emailDraft"]["body"],
                "attachment": f"data:application/pdf;base64,{b64_resume}",
                "fileName": resume.name,
            }
            res = requests.post(f"{API_BASE}/send-email", json=payload)
            if res.ok:
                st.success("✅ Email sent successfully!")
