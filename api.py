# api.py
import os
import smtplib
from email.message import EmailMessage
import uuid
import psycopg2
from fastapi import FastAPI, Form, Response, Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Any

from graph import alfred_app
from langchain_core.messages import HumanMessage, AIMessage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from tools.doctor_tools import run_pipeline_diagnostics
from tools.social_tools import send_text_message
from pdf_summarizer import summarize_pdfs_to_duckdb
from email_ingester import ingest_and_categorize_emails

# Define the request body model for type safety


class ChatRequest(BaseModel):
    # Using Any to be flexible with LangChain's message format
    messages: List[Any]
    thread_id: str = "default_thread"


class ScheduleRequest(BaseModel):
    task_prompt: str
    schedule_type: str  # 'interval' or 'cron'
    minutes: int = 0
    hour: int = 0
    minute: int = 0
    day_of_week: str = "*"
    job_id: str = None


# Initialize FastAPI app
app = FastAPI(
    title="ALFRED API",
    description="API endpoint for the ALFRED Meta-Agent Orchestrator",
    version="1.0.0"
)

# --- CORS Middleware ---
# This is CRITICAL. It allows your Netlify frontend to communicate with this backend.
# Update the `origins` list with your actual Netlify URL.
frontend_url = os.getenv(
    "FRONTEND_URL", "https://your-netlify-app-name.netlify.app")
origins = [
    "http://localhost:3000",  # For local JS frontend development
    frontend_url  # Your production frontend URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Key Security ---
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def get_api_key(api_key: str = Security(api_key_header)):
    expected_api_key = os.getenv("ALFRED_API_KEY")
    # Only enforce security if you have set an API key in your .env
    if expected_api_key and api_key != expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Could not validate API key"
        )
    return api_key

# --- Internal Task Scheduler ---
scheduler = AsyncIOScheduler()

# Store recent background task notifications
task_notifications = []


def send_email_notification(subject: str, body: str):
    """Sends an email notification using standard SMTP."""
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USERNAME")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    to_email = os.getenv("NOTIFICATION_EMAIL")

    if not all([smtp_server, smtp_user, smtp_pass, to_email]):
        print("Email notification skipped: SMTP credentials not fully configured in environment.")
        return

    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = smtp_user
        msg['To'] = to_email

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        print("Email notification sent successfully.")
    except Exception as e:
        print(f"Failed to send email notification: {e}")


def run_scheduled_task():
    """A sample automated task that ALFRED triggers internally."""
    print("Executing scheduled task...")
    # Create the task prompt directly
    inputs = {"messages": [HumanMessage(
        content="Please tell AFANDE to run a quick Nmap audit on 127.0.0.1")]}
    config = {"configurable": {"thread_id": "internal_cron_thread"}}

    try:
        # Invoke ALFRED directly in the background
        response = alfred_app.invoke(inputs, config)
        result_msg = response['messages'][-1].content
        print(f"Scheduled Task Succeeded:\n{result_msg}")
        send_email_notification("ALFRED Scheduled Task Completed",
                                f"Task: Quick Nmap audit\n\nResult:\n{result_msg}")
    except Exception as e:
        print(f"Scheduled Task Failed: {e}")
        send_email_notification("ALFRED Scheduled Task Failed", f"Error:\n{e}")


def daily_health_check():
    """Automatically runs the DOCTOR tool directly and logs the report to a file."""
    print("Executing daily pipeline health check...")
    try:
        report = run_pipeline_diagnostics.invoke({})
        log_dir = os.path.join("data", "health_reports")
        os.makedirs(log_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_path = os.path.join(log_dir, f"report_{timestamp}.txt")

        with open(log_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"Health check complete. Log saved to {log_path}")
        send_email_notification(
            "ALFRED Daily Health Report", f"Saved to {log_path}\n\n{report}")

        if "⚠️ Issues Detected" in report or "❌" in report:
            admin_phone = os.getenv("ADMIN_PHONE_NUMBER")
            if admin_phone:
                try:
                    send_text_message.invoke({
                        "to_number": admin_phone,
                        "message": "ALFRED Alert 🚨\nDaily health check detected issues! Check your logs."
                    })
                    print("Sent failure SMS alert to Admin.")
                except Exception as sms_err:
                    print(f"Failed to send SMS alert: {sms_err}")
    except Exception as e:
        print(f"Daily health check failed: {e}")
        admin_phone = os.getenv("ADMIN_PHONE_NUMBER")
        if admin_phone:
            try:
                send_text_message.invoke({
                    "to_number": admin_phone,
                    "message": f"ALFRED Critical Alert 🚨\nThe daily health check crashed entirely: {str(e)[:100]}"
                })
            except:
                pass


def daily_pdf_summarizer():
    """Automatically runs the PDF summarizer workflow every night."""
    print("Executing nightly PDF summarizer workflow...")
    try:
        summarize_pdfs_to_duckdb()
        print("Nightly PDF summarizer workflow complete.")
    except Exception as e:
        print(f"Nightly PDF summarizer workflow failed: {e}")
        send_email_notification(
            "ALFRED Nightly Task Failed", f"Error in PDF summarizer:\n{e}")


def daily_system_logs_report():
    """Automatically queries the last 24 hours of system_logs and emails a formatted report."""
    print("Executing daily system logs report...")
    try:
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print("Skipping logs report: DATABASE_URL not found.")
            return

        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT created_at, log_level, message FROM system_logs WHERE created_at >= NOW() - INTERVAL '24 hours' ORDER BY created_at DESC;")
                rows = cur.fetchall()

        if not rows:
            report = "No system logs recorded in the past 24 hours."
        else:
            report = "Here are the ALFRED system logs from the past 24 hours:\n\n"
            for r in rows:
                report += f"[{r[0].strftime('%Y-%m-%d %H:%M:%S')}] {r[1]}: {r[2]}\n"

        send_email_notification("ALFRED Daily System Logs Report", report)
        print("Daily system logs report emailed successfully.")
    except Exception as e:
        print(f"Failed to generate daily system logs report: {e}")


def hourly_email_ingester():
    """Automatically runs the email ingestion and categorization workflow every hour."""
    print("Executing hourly email ingestion workflow...")
    try:
        ingest_and_categorize_emails()
        print("Hourly email ingestion workflow complete.")
    except Exception as e:
        print(f"Hourly email ingestion workflow failed: {e}")
        send_email_notification(
            "ALFRED Hourly Task Failed", f"Error in email ingester:\n{e}")


@app.on_event("startup")
async def start_scheduler():
    # Schedule the health check to run every day at 08:00 AM
    scheduler.add_job(daily_health_check, 'cron', hour=8, minute=0,
                      id='daily_health_check', name='Daily System Health Check', replace_existing=True)
    # Schedule the PDF summarizer to run every night at 02:00 AM
    scheduler.add_job(daily_pdf_summarizer, 'cron', hour=2, minute=0,
                      id='daily_pdf_summarizer', name='Nightly PDF Summarization', replace_existing=True)
    # Schedule the system logs report to run every night at 11:50 PM
    scheduler.add_job(daily_system_logs_report, 'cron', hour=23, minute=50,
                      id='daily_system_logs_report', name='Daily System Logs Report', replace_existing=True)
    # Schedule the email ingester to run every hour at the top of the hour
    scheduler.add_job(hourly_email_ingester, 'cron', minute=0,
                      id='hourly_email_ingester', name='Hourly Email Ingestion', replace_existing=True)
    scheduler.start()


@app.on_event("shutdown")
async def stop_scheduler():
    scheduler.shutdown()


@app.post("/chat")
async def chat_endpoint(request: ChatRequest, api_key: str = Depends(get_api_key)):
    """Receives chat history and returns ALFRED's response."""
    lc_messages = [
        HumanMessage(content=msg.get("content")) if msg.get("role") == "user"
        else AIMessage(content=msg.get("content"))
        for msg in request.messages
    ]

    inputs = {"messages": lc_messages}
    config = {"configurable": {"thread_id": request.thread_id}}

    response = alfred_app.invoke(inputs, config)
    final_msg = response["messages"][-1].content

    return {"role": "assistant", "content": final_msg}


@app.post("/schedule")
async def schedule_task(request: ScheduleRequest, api_key: str = Depends(get_api_key)):
    """Receives task details and dynamically schedules them in APScheduler."""
    def dynamic_task(prompt: str):
        print(f"Executing scheduled task: {prompt}")
        inputs = {"messages": [HumanMessage(content=prompt)]}
        config = {"configurable": {
            "thread_id": f"cron_{prompt[:10]}"}}

        try:
            response = alfred_app.invoke(inputs, config)
            result_msg = response['messages'][-1].content
            print(f"Scheduled Task Succeeded:\n{result_msg}")
            send_email_notification(
                f"ALFRED Task Completed: {prompt[:20]}...", f"Task:\n{prompt}\n\nResult:\n{result_msg}")
            task_notifications.append({
                "task": prompt[:50],
                "status": "✅ Success",
                "time": datetime.now().strftime("%I:%M %p")
            })
        except Exception as e:
            print(f"Scheduled Task Failed: {e}")
            send_email_notification(
                f"ALFRED Task Failed: {prompt[:20]}...", f"Task:\n{prompt}\n\nError:\n{e}")
            task_notifications.append({
                "task": prompt[:50],
                "status": "❌ Failed",
                "time": datetime.now().strftime("%I:%M %p")
            })

    job_id = request.job_id if request.job_id else str(uuid.uuid4())
    job_name = request.task_prompt[:50]

    if request.schedule_type == "interval":
        scheduler.add_job(dynamic_task, 'interval', args=[request.task_prompt],
                          minutes=request.minutes, id=job_id, name=job_name, replace_existing=True)
        msg = f"Task scheduled every {request.minutes} minutes."
    elif request.schedule_type == "cron":
        scheduler.add_job(dynamic_task, 'cron', args=[request.task_prompt],
                          day_of_week=request.day_of_week, hour=request.hour, minute=request.minute, id=job_id, name=job_name, replace_existing=True)
        msg = f"Task scheduled via cron at {request.hour:02d}:{request.minute:02d} on {request.day_of_week}."
    else:
        return {"status": "error", "message": "Invalid schedule type"}

    return {"status": "success", "message": msg}


@app.get("/jobs")
async def get_jobs(api_key: str = Depends(get_api_key)):
    """Returns a list of all currently scheduled jobs."""
    jobs = []
    for job in scheduler.get_jobs():
        is_paused = job.next_run_time is None
        jobs.append({
            "id": job.id,
            "name": job.args[0] if job.args else job.name,
            "next_run_time": str(job.next_run_time) if job.next_run_time else "Paused",
            "is_paused": is_paused
        })
    return {"jobs": jobs}


@app.post("/jobs/{job_id}/pause")
async def pause_job(job_id: str, api_key: str = Depends(get_api_key)):
    """Pauses an actively scheduled job."""
    try:
        scheduler.pause_job(job_id)
        return {"status": "success", "message": "Task paused."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/jobs/{job_id}/resume")
async def resume_job(job_id: str, api_key: str = Depends(get_api_key)):
    """Resumes a paused job."""
    try:
        scheduler.resume_job(job_id)
        return {"status": "success", "message": "Task resumed."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/jobs/{job_id}/run")
async def run_job_now(job_id: str, api_key: str = Depends(get_api_key)):
    """Executes a scheduled job immediately without waiting for its next run time."""
    try:
        job = scheduler.get_job(job_id)
        if not job:
            return {"status": "error", "message": "Job not found."}

        scheduler.add_job(job.func, 'date', run_date=datetime.now(
        ), args=job.args, id=f"run_now_{job_id}", replace_existing=True)
        return {"status": "success", "message": "Task triggered to run immediately."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/notifications")
async def get_notifications(api_key: str = Depends(get_api_key)):
    """Returns the most recent background task notifications."""
    return {"notifications": task_notifications[-5:]}


@app.delete("/jobs/{job_id}")
async def cancel_job(job_id: str, api_key: str = Depends(get_api_key)):
    """Cancels a scheduled job by its ID."""
    try:
        scheduler.remove_job(job_id)
        return {"status": "success", "message": "Task cancelled successfully."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...)
):
    """Receives incoming WhatsApp messages from Twilio and returns ALFRED's response."""
    # Create the LangChain HumanMessage from the incoming WhatsApp text
    inputs = {"messages": [HumanMessage(content=Body)]}

    # Use the sender's WhatsApp number as the thread ID to maintain conversation state per user
    config = {"configurable": {"thread_id": From}}

    # Invoke ALFRED's graph orchestrator
    response = alfred_app.invoke(inputs, config)
    final_msg = response["messages"][-1].content

    # Construct a TwiML (Twilio XML) response to send the message back to WhatsApp
    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{final_msg}</Message>
</Response>"""

    return Response(content=twiml_response, media_type="application/xml")


@app.post("/sms")
async def sms_webhook(
    Body: str = Form(...),
    From: str = Form(...)
):
    """Receives incoming SMS messages from Twilio and returns ALFRED's response."""
    inputs = {"messages": [HumanMessage(content=Body)]}
    config = {"configurable": {"thread_id": f"sms_{From}"}}

    response = alfred_app.invoke(inputs, config)
    final_msg = response["messages"][-1].content

    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{final_msg}</Message>
</Response>"""

    return Response(content=twiml_response, media_type="application/xml")


class OpenClawWebhookPayload(BaseModel):
    event: str
    data: Any


@app.post("/webhook/openclaw")
async def openclaw_webhook(payload: OpenClawWebhookPayload):
    """Receives automated webhook triggers directly from OpenClaw."""
    prompt = f"[Automated OpenClaw Trigger]\nEvent: {payload.event}\nData: {payload.data}\n\nPlease analyze this event and execute the corresponding workflow."

    inputs = {"messages": [HumanMessage(content=prompt)]}
    config = {"configurable": {"thread_id": "openclaw_auto_trigger"}}

    try:
        response = alfred_app.invoke(inputs, config)
        return {"status": "success", "response": response["messages"][-1].content}
    except Exception as e:
        return {"status": "error", "message": str(e)}
