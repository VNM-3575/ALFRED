#!/usr/bin/env python3
import requests
import sys
import time


def run_student_workflow():
    print("🎓 =========================================")
    print("🎓 ALFRED: Student Autopilot Workflow")
    print("🎓 =========================================\n")

    target_url = input(
        "🔗 Enter the Student Portal URL (e.g., https://canvas.edu): ").strip()
    if not target_url:
        print("URL is required. Exiting.")
        sys.exit(1)

    account_name = input(
        "🔑 Enter the saved credential account name (or press Enter if ALFRED should ask/detect): ").strip()

    target_module = input(
        "📚 Enter the specific Module or Course Name (e.g., 'Phase 3 Data Science'): ").strip()

    phone_number = input(
        "📱 Enter your phone number for SMS alerts (e.g., +1234567890) or press Enter to skip: ").strip()

    notification_instruction = ""
    if phone_number:
        notification_instruction = f"\n\n    6. NOTIFICATION: Once step 5 is complete, instruct the AFANDE agent to use the `send_text_message` tool to text {phone_number} with a concise summary of the completed checklist."

    print("\n[ALFRED] Compiling Master Directive for the multi-agent team...")

    # Constructing the complex step-by-step workflow for the LLM Orchestrator
    master_prompt = f"""
    Initiate the 'Student Autopilot Workflow' for the following portal: {target_url} focusing on module: {target_module}.
    
    Please execute these exact steps sequentially:
    
    1. AUTHENTICATION: Check if we have credentials for '{account_name}' using your `get_allowed_account_credentials` tool. 
       If no credentials exist, stop immediately and ask me to provide them.
       
    2. DISCOVERY & CHECKLIST: Instruct the STUDENT agent to use OpenClaw to log into {target_url} and navigate to {target_module}. 
       Scrape the dashboard/module page and generate a strict checklist of ALL pending assignments for this specific module.
       
    3. EXECUTION: For each pending assignment on the checklist:
       a. Use `extract_grading_rubric` or `generic_openclaw_scrape` to read the exact assignment instructions and DOM elements.
       b. Pass the extracted data to the DATA_ANALYST to compute, write code, or formulate the correct academic answers (leveraging local analytics if needed).
       
    4. RECORDING & SUBMISSION DRAFTING: 
       a. Route to the CONTENT_CREATOR to format the final answers for each assignment into a PDF report. 
          CRITICAL: Instruct CONTENT_CREATOR to save these using `generate_pdf_report` with the filename formatted exactly as 'assignments_completed/your_assignment_name.pdf'.
       b. Route back to the STUDENT agent to use the `draft_portal_submission` tool to safely paste the answers or upload the generated PDF into the portal.
    
    5. REVIEW: Report back to me with the fully checked-off list when all drafts are staged on the screen and all PDFs are securely saved in the 'assignments_completed' folder for my final manual review. Do NOT click submit.{notification_instruction}
    """

    print("[ALFRED] Sending directive to orchestrator. Please wait, this may take a few minutes as OpenClaw navigates the web...\n")

    try:
        # Send the prompt to ALFRED's FastAPI backend
        # High timeout because web scraping, reasoning, and drafting takes time
        response = requests.post(
            "http://localhost:8000/chat",
            json={
                "messages": [{"role": "user", "content": master_prompt}],
                "thread_id": f"student_autopilot_{int(time.time())}"
            },
            timeout=600
        )
        response.raise_for_status()

        print("🎩 ALFRED'S REPORT:\n")
        print(response.json().get("content", "No response received."))
    except Exception as e:
        print(f"\n❌ Workflow Execution Failed: {e}")


if __name__ == "__main__":
    run_student_workflow()
