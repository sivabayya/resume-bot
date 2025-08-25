from fastapi import FastAPI
from pydantic import BaseModel
#import re
from transformers import pipeline
from contextlib import asynccontextmanager
import smtplib, ssl, base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os
from dotenv import load_dotenv
import logging
#from .db import Base, engine
#from . import models
#import backend.db  # ensures DB + tables get created


load_dotenv()
#print("DEBUG Gmail User:", GMAIL_USER)
from pathlib import Path
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

app = FastAPI()

# Lifespan event to replace on_event
#@asynccontextmanager
#async def lifespan(app: FastAPI):
    # Startup
 #   Base.metadata.create_all(bind=engine)
  #  yield
    # Shutdown (cleanup if needed)
#app = FastAPI(lifespan=lifespan)
@app.get("/")
def health_check():
    return {"status": "running"}

# Hugging Face Pipelines
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
#generator = pipeline("text-generation", model="gpt2")

email_generator = pipeline("text2text-generation", model="google/flan-t5-base")

#  Add summarizer
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# configure logging
logging.basicConfig(level=logging.INFO)

# Gmail credentials
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_PASS")

class JDRequest(BaseModel):
    text: str

class EmailGenRequest(BaseModel):
    senderName: str
    senderEmail: str
    linkedIn: str
    jobTitle: str
    company: str
    recruiterName: str
    JD_Summary: str

class EmailSendRequest(BaseModel):
    to: str
    subject: str
    body: str
    attachment: str  # base64 PDF
    fileName: str

@app.post("/api/classify")
def classify(req: JDRequest):
    labels = ["Software Engineer", "Data Scientist", "Project Manager", "DevOps Engineer"]
    result = classifier(req.text, labels)
    job_title = result["labels"][0]
  # Generate JD summary
    #summary = summarizer(req.text, max_length=100, min_length=30, do_sample=False)[0]["summary_text"]
  # Generate JD summary (raw)   
    raw_summary = summarizer(req.text, max_length=100, min_length=30, do_sample=False)[0]["summary_text"]
# Make it sound natural instead of copy-paste
    jd_summary = (
        f"The role emphasizes {raw_summary.lower()}. "
        f"My background and experience align closely with these requirements."
    )
    # call the extractor
  #  company, recruiter = extract_company_and_recruiter(text)

   
    return {"jobType": result["labels"][0],"jobTitle": result["labels"][0], "scores": result["scores"],"jd_summary": jd_summary}


#@app.post("/api/generate-email")
#def generate_email(req: EmailGenRequest):
 #   prompt = (
  #      f"Write a short professional job application email.\n\n"
   #     f"Applicant: {req.senderName}\n"
    #    f"Email: {req.senderEmail}\n"
     #   f"LinkedIn: {req.linkedIn if req.linkedIn else 'N/A'}\n"
      #  f"Job Title: {req.jobTitle}\n"
       # f"Company: {req.company}\n"
        #f"Recruiter: {req.recruiterName}\n\n"
        #f"Format the email with greeting, body, closing, and signature."
    #    out = email_generator(prompt, max_length=300, num_return_sequences=1)[0]["generated_text"]

    #subject = f"Application for {req.jobTitle} at {req.company}"
    #return {"subject": subject, "body": out.strip()}


@app.post("/api/generate-email")
def generate_email(req: EmailGenRequest):
       # Assume JD summary will come in req (you can rename as needed)
    jd_summary = getattr(req, "JD_Summary", None)  
    # A clean, professional email template
    body = f"""
Dear {req.recruiterName},

I hope this message finds you well. 

My name is {req.senderName}, and I am writing to express my interest in the {req.jobTitle} position at {req.company}. 
I have relevant experience and skills that I believe would make me a strong fit for this role.

Based on the job description, here is a quick summary of how my profile aligns:
- {req.JD_Summary}

You can find my resume attached for your review. 
I would be grateful for the opportunity to discuss how my background aligns with your team’s needs. 

Thank you for your time and consideration.  
I look forward to your response.

Best regards,  
{req.senderName}  
Phone : (+91)9989672496
Email: {req.senderEmail}  
LinkedIn: {req.linkedIn}
"""
    subject = f"Application for {req.jobTitle} at {req.company}"

    return {"subject": subject, "body": body}


@app.post("/api/send-email")
def send_email(req: EmailSendRequest):
    try:
        if not GMAIL_USER or not GMAIL_PASS:
            logging.error("❌ Gmail credentials missing. Check your .env file.")
            return {"status": "error", "message": "Missing Gmail credentials. Please check your .env file."}

        logging.info("Preparing email to send...")

        msg = MIMEMultipart()
        msg["From"] = GMAIL_USER
        msg["To"] = req.to
        msg["Subject"] = req.subject

        logging.info(f"📌 Subject: {req.subject}")
        msg.attach(MIMEText(req.body, "plain"))

        # Handle attachment if present
        if req.attachment:
            try:
                pdf_data = base64.b64decode(req.attachment.split(",")[-1])
                part = MIMEApplication(pdf_data, Name=req.fileName)
                part["Content-Disposition"] = f'attachment; filename="{req.fileName}"'
                msg.attach(part)
                logging.info(f"📎 Attached file: {req.fileName}")
            except Exception as e:
                logging.error(f"❌ Failed to attach file: {e}")
                return {"status": "error", "error": f"Attachment failed: {str(e)}"}

        # Always try sending the email (even if no attachment)
        try:
            logging.info("📨 Connecting to Gmail SMTP...")
            context = ssl.create_default_context()

            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(GMAIL_USER, GMAIL_PASS)
                server.sendmail(GMAIL_USER, req.to, msg.as_string())

            logging.info(f"✅ Email sent successfully to {req.to}")
            return {"status": "sent", "to": req.to,"subject": req.subject}

        except smtplib.SMTPAuthenticationError:
            logging.error("❌ Gmail authentication failed")
            return {"status": "error", "error": "Authentication failed. Check Gmail credentials or App Password."}
        except Exception as e:
            logging.error(f"❌ Failed to send email: {e}")
            return {"status": "error", "error": str(e)}

    except Exception as e:
        logging.error(f"🔥 Unexpected error: {e}")
        return {"status": "error", "error": str(e)}
        
