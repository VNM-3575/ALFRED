# Streamlit UI Interface with Persona Swapping
import os
import streamlit as st
import requests
import psycopg2
from huggingface_hub import HfApi
from langchain_core.messages import HumanMessage, AIMessage
from graph import alfred_app
from PIL import ImageGrab
import base64
from io import BytesIO
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

st.set_page_config(page_title="ALFRED: Project Command", layout="wide")

if "edit_job_id" not in st.session_state:
    st.session_state.edit_job_id = None
if "edit_task_prompt" not in st.session_state:
    st.session_state.edit_task_prompt = ""

# --- SIDEBAR & CONFIG ---
with st.sidebar:
    st.title("⚙️ Control Panel")

    # Persona Swapping
    selected_persona = st.selectbox(
        "Active Persona",
        ["ALFRED (Core Director)", "Student", "Content Creator",
         "Business Analyst", "Data Scientist", "Ethical Hacker"]
    )

    # OpenClaw Debugging Toggle
    headless_mode = st.toggle("OpenClaw Headless Mode", value=True,
                              help="Turn off to visually see the browser UI during web tasks.")
    os.environ["OPENCLAW_HEADLESS"] = str(headless_mode)

    st.markdown("---")
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.subheader("👁️ ALFRED Vision")
    st.caption("Takes a snapshot of your local screen.")
    if st.button("Look at my screen"):
        # Capture screen and convert to base64
        screenshot = ImageGrab.grab()
        buffered = BytesIO()
        screenshot.save(buffered, format="JPEG", quality=80)
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # Append multimodal message payload
        st.session_state.messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": "This is a screenshot of my current screen. Please analyze it based on my next prompt or tell me what you see."},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/jpeg;base64,{img_str}"}}
            ]
        })
        st.rerun()

    st.markdown("---")
    st.subheader("🔐 Credential Manager")
    with st.expander("Manage Allowed Accounts"):
        creds_dir = "allowed-access-accounts"
        os.makedirs(creds_dir, exist_ok=True)
        import json

        # List existing accounts
        existing_accounts = [f.replace(".json", "") for f in os.listdir(
            creds_dir) if f.endswith(".json")]
        if existing_accounts:
            st.write("**Saved Accounts:**")
            for acc in existing_accounts:
                col1, col2 = st.columns([4, 1])
                col1.write(f"- `{acc}`")
                if col2.button("❌", key=f"del_cred_{acc}"):
                    os.remove(os.path.join(creds_dir, f"{acc}.json"))
                    st.rerun()
        else:
            st.info("No accounts saved yet.")

        st.markdown("**Add New Account**")
        with st.form("add_cred_form"):
            new_acc_name = st.text_input("Service Name (e.g., canvas, github)")
            new_username = st.text_input("Username / Email")
            new_password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Save Credentials")

            if submitted:
                if new_acc_name and new_username and new_password:
                    safe_name = new_acc_name.strip().lower().replace(" ", "_")
                    file_path = os.path.join(creds_dir, f"{safe_name}.json")
                    with open(file_path, "w") as f:
                        json.dump({"username": new_username,
                                  "password": new_password}, f)
                    st.success(f"Saved {safe_name}!")
                    st.rerun()
                else:
                    st.error("Please fill in all fields.")

        st.markdown("**Import Chrome Passwords**")
        st.caption(
            "You can export your passwords from Chrome Settings -> Password Manager and upload the CSV here.")
        uploaded_csv = st.file_uploader("Upload Chrome CSV", type=["csv"])
        if uploaded_csv is not None:
            import pandas as pd
            try:
                df = pd.read_csv(uploaded_csv)
                if "name" in df.columns and "username" in df.columns and "password" in df.columns:
                    count = 0
                    for index, row in df.iterrows():
                        if pd.notna(row['name']) and pd.notna(row['username']) and pd.notna(row['password']):
                            acc_name = str(row['name']).strip(
                            ).lower().replace(" ", "_")
                            if acc_name:
                                file_path = os.path.join(
                                    creds_dir, f"{acc_name}.json")
                                with open(file_path, "w") as f:
                                    json.dump(
                                        {"username": str(row['username']), "password": str(row['password'])}, f)
                                count += 1
                    st.success(f"Imported {count} credentials!")
                else:
                    st.error(
                        "Invalid CSV format. Missing required Chrome columns (name, username, password).")
            except Exception as e:
                st.error(f"Error parsing CSV: {e}")

    st.markdown("---")
    st.subheader("⏱️ Task Scheduler")
    with st.expander("Schedule a Task", expanded=bool(st.session_state.edit_job_id)):
        if st.session_state.edit_job_id:
            st.info("✏️ **Editing Existing Task**")
            if st.button("Cancel Edit"):
                st.session_state.edit_job_id = None
                st.session_state.edit_task_prompt = ""
                st.rerun()

        task_options = [
            "Custom Task...",
            "Check student portal for new assignments",
            "Scrape TechCrunch and save sentiment analysis to DuckDB",
            "Generate daily RSI chart for AAPL and summarize",
            "Run a quick Nmap audit on 127.0.0.1"
        ]
        selected_task = st.selectbox("Select a task template:", task_options)

        default_prompt = st.session_state.edit_task_prompt if st.session_state.edit_job_id else (
            "" if selected_task == "Custom Task..." else selected_task)
        task_prompt = st.text_area("Task instruction for ALFRED:", value=default_prompt,
                                   placeholder="E.g., Tell DATA_ANALYST to query local DuckDB...")
        schedule_type = st.radio(
            "Schedule Type", ["Interval (Minutes)", "Daily (Time)"])

        minutes, hour, minute = 0, 0, 0
        if schedule_type == "Interval (Minutes)":
            minutes = st.number_input(
                "Every X minutes:", min_value=1, value=30)
        else:
            schedule_time = st.time_input("Run daily at:")
            if schedule_time:
                hour = schedule_time.hour
                minute = schedule_time.minute

        if st.button("Schedule Task" if not st.session_state.edit_job_id else "Update Task"):
            payload = {
                "task_prompt": task_prompt,
                "schedule_type": "interval" if "Interval" in schedule_type else "cron",
                "minutes": minutes,
                "hour": hour,
                "minute": minute,
                "job_id": st.session_state.edit_job_id
            }
            try:
                resp = requests.post(
                    "http://localhost:8000/schedule", json=payload)
                if resp.status_code == 200:
                    st.success(resp.json().get("message", "Task Scheduled!"))
                    st.session_state.edit_job_id = None
                    st.session_state.edit_task_prompt = ""
                else:
                    st.error("Failed to schedule task.")
            except Exception as e:
                st.error(
                    f"API Connection Error. Make sure ALFRED backend is running: {e}")

    with st.expander("Active Tasks"):
        try:
            jobs_resp = requests.get("http://localhost:8000/jobs")
            if jobs_resp.status_code == 200:
                jobs = jobs_resp.json().get("jobs", [])
                if not jobs:
                    st.info("No active tasks running.")
                for job in jobs:
                    st.write(
                        f"**{job['name']}**\n\n*Next Run: {job['next_run_time']}*")
                    col1, col2, col3 = st.columns(3)

                    if job.get("is_paused"):
                        if col1.button("▶️ Resume", key=f"res_{job['id']}"):
                            requests.post(
                                f"http://localhost:8000/jobs/{job['id']}/resume")
                            st.rerun()
                    else:
                        if col1.button("⏸️ Pause", key=f"pau_{job['id']}"):
                            requests.post(
                                f"http://localhost:8000/jobs/{job['id']}/pause")
                            st.rerun()

                    if col2.button("✏️ Edit", key=f"edit_{job['id']}"):
                        st.session_state.edit_job_id = job['id']
                        st.session_state.edit_task_prompt = job['name']
                        st.rerun()
                    if col3.button("❌ Cancel", key=f"cancel_{job['id']}"):
                        res = requests.delete(
                            f"http://localhost:8000/jobs/{job['id']}")
                        if res.status_code == 200:
                            st.success("Cancelled!")
                            st.rerun()
                    st.divider()
        except Exception:
            st.error("Could not load active tasks.")

    st.markdown("---")
    st.subheader("📊 Systems & Logs")
    with st.expander("Connection Status"):
        db_url = os.getenv(
            "DATABASE_URL", "postgresql://alfred_admin:alfred_password@localhost:5432/alfred_warehouse")
        # Allow connection mapping if Streamlit is run on the host instead of inside Docker
        db_url = db_url.replace("@db:5432", "@localhost:5432")
        try:
            conn = psycopg2.connect(db_url)
            st.success("✅ PostgreSQL: Connected")
            conn.close()
        except Exception as e:
            st.error(f"❌ PostgreSQL: Disconnected")

        hf_key = os.getenv("HUGGINGFACE_API_KEY")
        if hf_key:
            try:
                api = HfApi()
                user = api.whoami(token=hf_key)
                st.success(f"✅ HuggingFace: Connected as {user['name']}")
            except Exception:
                st.error("❌ HuggingFace: Auth Failed")
        else:
            st.warning("⚠️ HuggingFace: Key missing in environment")

    with st.expander("Terminal Logs"):
        st.caption(
            "ALFRED operates via distributed containers. View real-time output in your terminal:")
        st.code("docker-compose logs -f alfred_core", language="bash")
        st.code("docker-compose logs -f db", language="bash")
        st.code("docker-compose logs -f openclaw", language="bash")

    st.markdown("---")
    st.subheader("📂 Generated Reports")
    with st.expander("Available PDFs"):
        if os.path.exists("data"):
            pdf_files = [f for f in os.listdir("data") if f.endswith('.pdf')]
            if not pdf_files:
                st.info("No reports generated yet.")
            else:
                for pdf_file in pdf_files:
                    file_path = os.path.join("data", pdf_file)
                    explanation = "No preview available."
                    if PdfReader:
                        try:
                            reader = PdfReader(file_path)
                            if len(reader.pages) > 0:
                                text = reader.pages[0].extract_text()
                                if text:
                                    clean = " ".join(text.split())
                                    explanation = clean[:150] + \
                                        "..." if len(clean) > 150 else clean
                        except Exception:
                            pass
                    st.write(f"**{pdf_file}**")
                    st.caption(f"📝 *Preview:* {explanation}")
                    with open(file_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Download",
                            data=f,
                            file_name=pdf_file,
                            mime="application/pdf",
                            key=f"dl_{pdf_file}"
                        )
                    st.divider()
        else:
            st.info("No reports generated yet.")

    st.markdown("---")
    st.subheader("💡 System Suggestions")
    with st.expander("View Automations & Improvements"):
        suggestion_file = "data/suggestions.md"
        if os.path.exists(suggestion_file):
            with open(suggestion_file, "r") as f:
                st.markdown(f.read())
        else:
            st.info(
                "No suggestions generated yet. Ask ALFRED to analyze and suggest improvements!")

    st.markdown("---")
    st.subheader("🤖 Agent Capabilities")
    with st.expander("View Agent Summaries"):
        capabilities_file = "data/capabilities.md"
        if os.path.exists(capabilities_file):
            with open(capabilities_file, "r", encoding="utf-8") as f:
                st.markdown(f.read())
        else:
            st.info(
                "No capabilities file found. Please ensure data/capabilities.md exists.")

    st.markdown("---")
    st.subheader("📈 Generated Charts")
    with st.expander("Available Charts"):
        if os.path.exists("data"):
            img_files = [f for f in os.listdir(
                "data") if f.endswith('.png') or f.endswith('.jpg')]
            if not img_files:
                st.info("No charts generated yet.")
            else:
                for img_file in img_files:
                    file_path = os.path.join("data", img_file)
                    st.image(file_path, caption=img_file)
                    with open(file_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Download",
                            data=f,
                            file_name=img_file,
                            mime="image/png",
                            key=f"dl_{img_file}"
                        )
                    st.divider()
        else:
            st.info("No charts generated yet.")

    st.markdown("---")
    st.subheader("🔄 Data Pipeline")
    with st.expander("Pipeline Architecture"):
        st.markdown("**1. dbt (Transformation)**")
        st.caption("• **Inputs:** Raw data sources, uncleaned external APIs, or raw logs.\n"
                   "• **Outputs:** Clean, standardized, and modeled SQL tables ready for storage.")
        st.divider()
        st.markdown("**2. PostgreSQL (Storage)**")
        st.caption("• **Inputs:** Transformed data streams from dbt and application state logs.\n"
                   "• **Outputs:** Persistent, reliable, and relational data warehouse (`alfred_warehouse`).")
        st.divider()
        st.markdown("**3. DuckDB (Interpretation)**")
        st.caption("• **Inputs:** Local Parquet/CSV files (HuggingFace datasets) or connections to PostgreSQL tables.\n"
                   "• **Outputs:** Lightning-fast analytical query results and Pandas DataFrames for MOR's data science tasks.")


# --- MAIN UI ---
st.title("🎩 ALFRED: Meta-Agent Orchestrator")
st.subheader(f"Current Mode: {selected_persona}")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat (Updated to support images)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if isinstance(msg["content"], list):
            for block in msg["content"]:
                if block["type"] == "text":
                    st.markdown(block["text"])
                elif block["type"] == "image_url":
                    # Render base64 image inside the Streamlit chat
                    st.image(block["image_url"]["url"])
        else:
            st.markdown(msg["content"])

# User Input
if prompt := st.chat_input("ALFRED, let's build SHUGA&SPICE's art logic..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Convert Streamlit history into LangChain message objects
    lc_messages = []
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            content = msg["content"]
            # Attach persona guidance to the most recent prompt securely
            if msg == st.session_state.messages[-1]:
                sys_note = f"[System Note: User prefers the {selected_persona} persona for this request]\n"
                if isinstance(content, str):
                    content = sys_note + content
                elif isinstance(content, list) and len(content) > 0 and content[0]["type"] == "text":
                    # Create a copy so we don't mutate Streamlit's history
                    content = list(content)
                    content[0] = {"type": "text",
                                  "text": sys_note + content[0]["text"]}

            lc_messages.append(HumanMessage(content=content))
        else:
            lc_messages.append(AIMessage(content=msg["content"]))

    # Run ALFRED
    inputs = {"messages": lc_messages}
    config = {"configurable": {"thread_id": "dev_session"}}

    with st.spinner("ALFRED is thinking..."):
        response = alfred_app.invoke(inputs, config)
        final_msg = response["messages"][-1].content
        st.session_state.messages.append(
            {"role": "assistant", "content": final_msg})

    st.rerun()
