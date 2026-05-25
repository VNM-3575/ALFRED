import marimo

__generated_with = "0.8.0"
app = marimo.App(width="wide")


@app.cell
def __():
    import marimo as mo
    import requests
    import os
    import psycopg2
    import json
    import duckdb
    import pandas as pd
    return duckdb, json, mo, os, pandas, psycopg2, requests


@app.cell
def __(mo, os):
    persona_dropdown = mo.ui.dropdown(
        options=["ALFRED (Default)", "Student", "Content Creator",
                 "Business Analyst", "Data Scientist", "Ethical Hacker"],
        value="ALFRED (Default)",
        label="**🎭 Active Persona:**"
    )

    headless_toggle = mo.ui.switch(value=True, label="OpenClaw Headless Mode")
    return headless_toggle, persona_dropdown


@app.cell
def __(headless_toggle, os):
    os.environ["OPENCLAW_HEADLESS"] = str(headless_toggle.value)
    return


@app.cell
def __(mo, os, persona_dropdown, requests):
    def alfred_responder(messages, config):
        api_url = os.getenv("ALFRED_API_URL", "http://localhost:8000/chat")
        user_msg = messages[-1].content
        if persona_dropdown.value != "ALFRED (Default)":
            sys_note = f"[System Note: User prefers the {persona_dropdown.value} persona for this request]\n"
            user_msg = sys_note + user_msg

        headers = {
            "X-API-Key": os.getenv("ALFRED_API_KEY", "")} if os.getenv("ALFRED_API_KEY") else {}
        try:
            response = requests.post(api_url, json={"messages": [
                                     {"role": "user", "content": user_msg}], "thread_id": "marimo_session"}, headers=headers)
            return response.json().get("content", "Error reaching ALFRED.")
        except Exception as e:
            return f"Connection error: {e}"

    chat = mo.ui.chat(alfred_responder, prompts=[
        "What are my pending assignments?",
        "Run a system health check.",
        "Check my active tasks."
    ])
    return alfred_responder, chat


@app.cell
def __(mo):
    notif_count_state, set_notif_count = mo.state(0)
    return notif_count_state, set_notif_count


@app.cell
def __(mo, notif_count_state, os, requests, set_notif_count):
    chat_refresh = mo.ui.refresh(
        options=["10s", "30s", "off"], default="10s", label="Auto-check for completed tasks")
    _ = chat_refresh.value

    headers = {"X-API-Key": os.getenv("ALFRED_API_KEY", "")
               } if os.getenv("ALFRED_API_KEY") else {}
    notif_banner = mo.md("")
    try:
        notifs = requests.get(
            "http://localhost:8000/notifications", headers=headers).json().get("notifications", [])
        if notifs:
            lines = [
                f"- **[{n['time']}]** {n['task']}... **({n['status']})**" for n in reversed(notifs)]

            audio_player = mo.md("")
            if len(notifs) > notif_count_state.value:
                set_notif_count(len(notifs))
                audio_player = mo.audio(
                    src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg", autoplay=True)
            elif len(notifs) < notif_count_state.value:
                set_notif_count(len(notifs))

            notif_callout = mo.callout(
                "\n".join(lines), title="🔔 Background Task Completed", kind="info")
            notif_banner = mo.vstack([notif_callout, audio_player])
    except:
        pass
    return chat_refresh, notif_banner


@app.cell
def __(mo, os, requests):
    refresh_btn = mo.ui.button(label="🔄 Refresh Tasks & Logs")

    task_prompt = mo.ui.text_area(
        placeholder="E.g., Query local DuckDB...", label="Task Instruction")
    schedule_type = mo.ui.dropdown(
        ["Interval (Minutes)", "Daily (Time)", "Weekly (Specific Days)"], value="Interval (Minutes)", label="Schedule Type")
    days_of_week = mo.ui.multiselect(
        options={"Monday": "mon", "Tuesday": "tue", "Wednesday": "wed",
                 "Thursday": "thu", "Friday": "fri", "Saturday": "sat", "Sunday": "sun"},
        value=["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        label="Days of the Week (if Weekly)"
    )
    minutes = mo.ui.number(start=1, stop=1440, value=30,
                           label="Every X minutes")
    hour = mo.ui.number(start=0, stop=23, value=8,
                        label="Hour (if Daily/Weekly)")
    minute = mo.ui.number(start=0, stop=59, value=0,
                          label="Minute (if Daily/Weekly)")

    def schedule_task():
        dow_str = "*"
        if "Weekly" in schedule_type.value:
            dow_str = ",".join(
                days_of_week.value) if days_of_week.value else "*"

        payload = {
            "task_prompt": task_prompt.value,
            "schedule_type": "interval" if "Interval" in schedule_type.value else "cron",
            "minutes": minutes.value,
            "hour": hour.value,
            "minute": minute.value,
            "day_of_week": dow_str
        }
        headers = {
            "X-API-Key": os.getenv("ALFRED_API_KEY", "")} if os.getenv("ALFRED_API_KEY") else {}
        try:
            requests.post("http://localhost:8000/schedule",
                          json=payload, headers=headers)
        except:
            pass

    schedule_btn = mo.ui.button(
        label="📅 Schedule Task", on_click=lambda _: schedule_task())
    return days_of_week, hour, minute, minutes, refresh_btn, schedule_btn, schedule_task, schedule_type, task_prompt


@app.cell
def __(mo, os, refresh_btn, requests):
    _ = refresh_btn.value
    headers = {"X-API-Key": os.getenv("ALFRED_API_KEY", "")
               } if os.getenv("ALFRED_API_KEY") else {}
    try:
        jobs_resp = requests.get(
            "http://localhost:8000/jobs", headers=headers).json()
        jobs = jobs_resp.get("jobs", [])
    except:
        jobs = []

    if not jobs:
        tasks_display = mo.md(
            "No active tasks running. (Ensure ALFRED API is active)")
    else:
        job_options = {
            f"{j['name'][:50]}... (Next: {j['next_run_time']})": j['id'] for j in jobs}
        job_selector = mo.ui.dropdown(
            options=job_options, label="**Select Task to Manage:**")

        run_btn = mo.ui.button(label="🚀 Run Now", on_click=lambda _: requests.post(
            f"http://localhost:8000/jobs/{job_selector.value}/run", headers=headers) if job_selector.value else None)
        pause_btn = mo.ui.button(label="⏸️ Pause", on_click=lambda _: requests.post(
            f"http://localhost:8000/jobs/{job_selector.value}/pause", headers=headers) if job_selector.value else None)
        resume_btn = mo.ui.button(label="▶️ Resume", on_click=lambda _: requests.post(
            f"http://localhost:8000/jobs/{job_selector.value}/resume", headers=headers) if job_selector.value else None)
        cancel_btn = mo.ui.button(label="❌ Cancel", on_click=lambda _: requests.delete(
            f"http://localhost:8000/jobs/{job_selector.value}", headers=headers) if job_selector.value else None)

        tasks_display = mo.vstack([
            job_selector,
            mo.hstack([run_btn, pause_btn, resume_btn, cancel_btn])
        ])

    return jobs, tasks_display


@app.cell
def __(mo, os, psycopg2, refresh_btn):
    _ = refresh_btn.value
    logs_md = "No logs found."
    db_url = os.getenv(
        "DATABASE_URL", "postgresql://alfred_admin:alfred_password@localhost:5432/alfred_warehouse")
    db_url = db_url.replace("@db:5432", "@localhost:5432")
    try:
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT created_at, log_level, message FROM system_logs ORDER BY created_at DESC LIMIT 50")
                rows = cur.fetchall()
                if rows:
                    rows_md = [
                        f"| {r[0].strftime('%Y-%m-%d %H:%M:%S')} | {r[1]} | {r[2]} |" for r in rows]
                    logs_md = "| Timestamp | Level | Message |\n|---|---|---|\n" + \
                        "\n".join(rows_md)
    except Exception as e:
        logs_md = f"Error connecting to logs (Ensure database is running): {e}"

    return db_url, logs_md


@app.cell
def __(mo, os, refresh_btn):
    _ = refresh_btn.value
    data_dir = "data"
    pdf_files = []
    img_files = []
    if os.path.exists(data_dir):
        pdf_files = sorted([f for f in os.listdir(data_dir)
                           if f.endswith('.pdf')], reverse=True)
        img_files = sorted([f for f in os.listdir(data_dir)
                           if f.endswith(('.png', '.jpg'))], reverse=True)

    pdf_dropdown = mo.ui.dropdown(options=pdf_files if pdf_files else [
                                  "No PDFs found"], value=pdf_files[0] if pdf_files else "No PDFs found", label="Select PDF:")
    img_dropdown = mo.ui.dropdown(options=img_files if img_files else [
                                  "No Charts found"], value=img_files[0] if img_files else "No Charts found", label="Select Chart:")
    return data_dir, img_dropdown, img_files, pdf_dropdown, pdf_files


@app.cell
def __(data_dir, img_dropdown, mo, os, pdf_dropdown):
    pdf_viewer = mo.md("No PDF selected.")
    if pdf_dropdown.value and pdf_dropdown.value != "No PDFs found":
        pdf_path = os.path.join(data_dir, pdf_dropdown.value)
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                pdf_viewer = mo.pdf(src=f.read(), width="100%", height="600px")

    img_viewer = mo.md("No Chart selected.")
    if img_dropdown.value and img_dropdown.value != "No Charts found":
        img_path = os.path.join(data_dir, img_dropdown.value)
        if os.path.exists(img_path):
            img_viewer = mo.image(src=img_path)

    return img_path, img_viewer, pdf_path, pdf_viewer


@app.cell
def __(duckdb, mo, os, refresh_btn):
    _ = refresh_btn.value
    db_path = "data/local_warehouse.duckdb"
    duckdb_tables = []
    if os.path.exists(db_path):
        try:
            with duckdb.connect(db_path) as con:
                duckdb_tables = [r[0]
                                 for r in con.execute("SHOW TABLES").fetchall()]
        except Exception:
            pass

    duckdb_table_dropdown = mo.ui.dropdown(
        options=duckdb_tables if duckdb_tables else ["No tables found"],
        value=duckdb_tables[0] if duckdb_tables else "No tables found",
        label="**Select DuckDB Table:**"
    )
    return db_path, duckdb_table_dropdown, duckdb_tables


@app.cell
def __(db_path, duckdb, duckdb_table_dropdown, mo, pandas):
    duckdb_viewer = mo.md("No table selected.")
    if duckdb_table_dropdown.value and duckdb_table_dropdown.value != "No tables found":
        try:
            with duckdb.connect(db_path) as con:
                _df = con.execute(
                    f"SELECT * FROM {duckdb_table_dropdown.value} LIMIT 500").fetchdf()
                duckdb_viewer = mo.ui.table(_df, selection=None)
        except Exception as e:
            duckdb_viewer = mo.md(f"Error loading table data: {e}")
    return duckdb_viewer,


@app.cell
def __(mo):
    email_refresh_btn = mo.ui.button(label="🔄 Refresh Emails")
    email_category_filter = mo.ui.dropdown(
        options=["All", "Invoice", "Newsletter", "Urgent",
                 "Alert", "Meeting", "Inquiry", "Spam", "General"],
        value="All",
        label="**Filter by Category:**"
    )
    return email_category_filter, email_refresh_btn


@app.cell
def __(email_category_filter, email_refresh_btn, mo, os, pandas, psycopg2):
    _ = email_refresh_btn.value
    email_viewer = mo.md("No emails found.")

    db_url_email = os.getenv(
        "DATABASE_URL", "postgresql://alfred_admin:alfred_password@localhost:5432/alfred_warehouse")
    db_url_email = db_url_email.replace("@db:5432", "@localhost:5432")

    try:
        with psycopg2.connect(db_url_email) as conn:
            query = "SELECT received_at, sender, subject, category, body FROM categorized_emails"
            params = []
            if email_category_filter.value != "All":
                query += " WHERE category = %s"
                params.append(email_category_filter.value)
            query += " ORDER BY received_at DESC LIMIT 100"

            with conn.cursor() as cur:
                cur.execute(query, params)
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                if rows:
                    df = pandas.DataFrame(rows, columns=columns)
                    email_viewer = mo.ui.table(df, selection=None)
                else:
                    email_viewer = mo.md(
                        f"No emails found for category: {email_category_filter.value}")
    except Exception as e:
        email_viewer = mo.md(f"Error loading categorized emails: {e}")
    return db_url_email, email_viewer


@app.cell
def __(mo, os, refresh_btn):
    _ = refresh_btn.value
    perception_path = "data/workflow_perceptions.md"
    perception_content = "No perceptions logged yet. Ask ALFRED to analyze your workflows!"
    if os.path.exists(perception_path):
        with open(perception_path, "r", encoding="utf-8") as f:
            perception_content = f.read()
    return perception_content, perception_path


@app.cell
def __(chat, chat_refresh, days_of_week, duckdb_table_dropdown, duckdb_viewer, email_category_filter, email_chart, email_refresh_btn, email_viewer, headless_toggle, hour, img_dropdown, img_viewer, logs_md, minute, minutes, mo, notif_banner, pdf_dropdown, pdf_viewer, perception_content, persona_dropdown, refresh_btn, schedule_btn, schedule_type, task_prompt, tasks_display):
    sidebar = mo.sidebar(
        mo.vstack([
            mo.md("### ⚙️ Control Panel"),
            persona_dropdown,
            headless_toggle,
            mo.md("---"),
            mo.md(
                "*(For advanced settings and API keys, edit your `.env` file directly.)*")
        ])
    )

    chat_tab = mo.vstack([
        mo.hstack([mo.md("*(ALFRED is monitoring background processes...)*"),
                  chat_refresh], justify="space-between"),
        notif_banner,
        chat
    ])

    scheduler_tab = mo.vstack([
        mo.md("### ⏱️ Schedule a New Task"),
        task_prompt, schedule_type, days_of_week, minutes, hour, minute, schedule_btn,
        mo.md("---"),
        mo.md("### 🏃 Active Tasks"),
        refresh_btn,
        tasks_display
    ])

    logs_tab = mo.vstack([
        mo.md("### 🖥️ PostgreSQL System Logs"),
        refresh_btn,
        mo.md(logs_md)
    ])

    media_tab = mo.vstack([
        mo.md("### 📂 Generated Reports & PDFs"),
        pdf_dropdown, pdf_viewer,
        mo.md("---"),
        mo.md("### 📈 Generated Charts"),
        img_dropdown, img_viewer
    ])

    duckdb_tab = mo.vstack([
        mo.md("### 🦆 DuckDB Data Warehouse"),
        refresh_btn,
        duckdb_table_dropdown,
        duckdb_viewer
    ])

    email_tab = mo.vstack([
        mo.md("### 📧 Categorized Emails"),
        mo.hstack([email_refresh_btn, email_category_filter]),
        email_chart,
        email_viewer
    ])

    memory_tab = mo.vstack([
        mo.md("### 🧠 ALFRED's Perception Log"),
        refresh_btn,
        mo.md(perception_content)
    ])

    tabs = mo.ui.tabs({
        "💬 Chat Center": chat_tab,
        "⏱️ Task Scheduler": scheduler_tab,
        "📊 System Logs": logs_tab,
        "📄 Media & Reports": media_tab,
        "🦆 DuckDB Viewer": duckdb_tab,
        "📧 Emails": email_tab,
        "🧠 Memory": memory_tab
    })

    return mo.vstack([
        sidebar,
        mo.md("# 🎩 ALFRED Command Center (Marimo)"),
        tabs
    ])
