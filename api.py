# api.py
import os
import smtplib
from email.message import EmailMessage
import uuid
from fastapi import FastAPI, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Any

from graph import alfred_app
from langchain_core.messages import HumanMessage, AIMessage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

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
origins = [
    "http://localhost:3000",  # For local JS frontend development
    "https://your-netlify-app-name.netlify.app"  # Your production frontend URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Internal Task Scheduler ---
scheduler = AsyncIOScheduler()


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


@app.on_event("startup")
async def start_scheduler():
    # We start the scheduler empty so jobs can be added dynamically via the UI
    # You can safely leave your hardcoded jobs here if you prefer
    scheduler.start()


@app.on_event("shutdown")
async def stop_scheduler():
    scheduler.shutdown()


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
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
async def schedule_task(request: ScheduleRequest):
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
        except Exception as e:
            print(f"Scheduled Task Failed: {e}")
            send_email_notification(
                f"ALFRED Task Failed: {prompt[:20]}...", f"Task:\n{prompt}\n\nError:\n{e}")

    job_id = request.job_id if request.job_id else str(uuid.uuid4())
    job_name = request.task_prompt[:50]

    if request.schedule_type == "interval":
        scheduler.add_job(dynamic_task, 'interval', args=[request.task_prompt],
                          minutes=request.minutes, id=job_id, name=job_name, replace_existing=True)
        msg = f"Task scheduled every {request.minutes} minutes."
    elif request.schedule_type == "cron":
        scheduler.add_job(dynamic_task, 'cron', args=[request.task_prompt],
                          hour=request.hour, minute=request.minute, id=job_id, name=job_name, replace_existing=True)
        msg = f"Task scheduled daily at {request.hour:02d}:{request.minute:02d}."
    else:
        return {"status": "error", "message": "Invalid schedule type"}

    return {"status": "success", "message": msg}


@app.get("/jobs")
async def get_jobs():
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
async def pause_job(job_id: str):
    """Pauses an actively scheduled job."""
    try:
        scheduler.pause_job(job_id)
        return {"status": "success", "message": "Task paused."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/jobs/{job_id}/resume")
async def resume_job(job_id: str):
    """Resumes a paused job."""
    try:
        scheduler.resume_job(job_id)
        return {"status": "success", "message": "Task resumed."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
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
