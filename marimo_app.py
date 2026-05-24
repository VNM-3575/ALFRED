import marimo

__generated_with = "0.8.0"
app = marimo.App(width="medium")


@app.cell
def __():
    import marimo as mo
    import requests
    import os

    persona_dropdown = mo.ui.dropdown(
        options=["ALFRED (Default)", "Student", "Content Creator",
                 "Business Analyst", "Data Scientist", "Ethical Hacker"],
        value="ALFRED (Default)",
        label="**🎭 Active Persona:**"
    )

    def alfred_responder(messages, config):
        api_url = os.getenv("ALFRED_API_URL", "http://localhost:8000/chat")
        # Grab the latest message from the user
        user_msg = messages[-1].content

        # Inject persona guidance into the prompt exactly like Streamlit did
        if persona_dropdown.value != "ALFRED (Default)":
            sys_note = f"[System Note: User prefers the {persona_dropdown.value} persona for this request]\n"
            user_msg = sys_note + user_msg

        response = requests.post(
            api_url,
            json={"messages": [
                {"role": "user", "content": user_msg}], "thread_id": "marimo_session"}
        )
        return response.json().get("content", "Error reaching ALFRED.")

    chat = mo.ui.chat(alfred_responder, prompts=[
        "What are my pending assignments?",
        "Run a system health check.",
        "Ask the DATA_ANALYST to query the pdf_summaries table in DuckDB."
    ])
    return alfred_responder, chat, mo, os, persona_dropdown, requests


@app.cell
def __(mo, os):
    reports_dir = os.path.join("data", "health_reports")
    report_files = []
    if os.path.exists(reports_dir):
        report_files = sorted([f for f in os.listdir(
            reports_dir) if f.endswith('.txt')], reverse=True)

    report_dropdown = mo.ui.dropdown(
        options=report_files if report_files else ["No reports found"],
        value=report_files[0] if report_files else "No reports found",
        label="**Select Health Report:**"
    )

    data_dir = "data"
    pdf_files = []
    if os.path.exists(data_dir):
        pdf_files = sorted([f for f in os.listdir(data_dir)
                           if f.endswith('.pdf')], reverse=True)

    pdf_dropdown = mo.ui.dropdown(
        options=pdf_files if pdf_files else ["No PDFs found"],
        value=pdf_files[0] if pdf_files else "No PDFs found",
        label="**Select PDF Report:**"
    )
    return data_dir, pdf_dropdown, pdf_files, report_dropdown, report_files, reports_dir


@app.cell
def __(chat, data_dir, mo, os, pdf_dropdown, persona_dropdown, report_dropdown, reports_dir):
    report_content = "No report selected."
    download_btn = mo.md("No report available to download.")

    if report_dropdown.value and report_dropdown.value != "No reports found":
        file_path = os.path.join(reports_dir, report_dropdown.value)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                report_content = f.read()

            download_btn = mo.download(
                data=report_content.encode("utf-8"),
                filename=report_dropdown.value,
                label="⬇️ Download Report",
                mimetype="text/plain"
            )

    report_tab = mo.vstack([
        mo.md("### 🏥 Pipeline Health Reports\nView and download daily system diagnostics."),
        report_dropdown,
        download_btn,
        mo.accordion({"View Report Content": mo.md(f"```text\n{report_content}\n```")}
                     ) if report_content != "No report selected." else mo.md("")
    ])

    pdf_viewer = mo.md("No PDF selected.")
    pdf_download_btn = mo.md("")

    if pdf_dropdown.value and pdf_dropdown.value != "No PDFs found":
        pdf_path = os.path.join(data_dir, pdf_dropdown.value)
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            # Pass the file bytes directly to the PDF component
            pdf_viewer = mo.pdf(src=pdf_bytes, width="100%", height="600px")

            pdf_download_btn = mo.download(
                data=pdf_bytes,
                filename=pdf_dropdown.value,
                label="⬇️ Download PDF",
                mimetype="application/pdf"
            )

    pdf_tab = mo.vstack([
        mo.md("### 📂 Generated PDF Reports\nView and download output reports."),
        pdf_dropdown,
        pdf_download_btn,
        pdf_viewer
    ])

    chat_tab = mo.vstack([
        persona_dropdown,
        chat
    ])

    tabs = mo.ui.tabs({
        "💬 Chat Center": chat_tab,
        "📊 Health Reports": report_tab,
        "📄 PDF Reports": pdf_tab
    })

    mo.vstack([
        mo.md("# 🎩 ALFRED Command Center (Marimo)"),
        tabs
    ])
