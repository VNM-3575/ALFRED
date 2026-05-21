# tools/security_tools.py or tools/portal_tools.py
import os
import json
import requests
import base64
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage


@tool
def download_portal_assignment(assignment_id: str, username: str = None, password: str = None, use_saved_session: bool = True) -> str:
    """
    Delegates task to OpenClaw API to securely log into the student portal, 
    navigate to the specified assignment ID, download the resource documents, 
    and return them to be saved locally to the 'data/' directory.
    """
    # Pull credentials dynamically from the arguments, or fallback to environment variables
    username = username or os.getenv("STUDENT_PORTAL_USER")
    password = password or os.getenv("STUDENT_PORTAL_PASS")
    captcha_key = os.getenv("CAPTCHA_API_KEY")
    output_path = f"data/assignment_{assignment_id}.pdf"

    # OpenClaw endpoint - adjust this to match your OpenClaw setup
    openclaw_url = os.getenv(
        "OPENCLAW_API_URL", "http://localhost:8000/api/automate")

    # Construct the instruction payload for OpenClaw
    payload = {
        "task_name": "portal_login_and_download",
        "login_url": "https://studentportal.example.edu/login",
        "target_url": f"https://studentportal.example.edu/assignments/{assignment_id}",
        "credentials": {
            "username": username,
            "password": password
        },
        "options": {
            "solve_captcha": True if captcha_key else False,
            "captcha_api_key": captcha_key,
            "use_saved_session": use_saved_session,
            "session_id": f"session_{username}" if username else "session_default",
            "headless": os.getenv("OPENCLAW_HEADLESS", "True").lower() == "true",
            "screenshot_on_error": True
        }
    }

    try:
        # Execute the task via OpenClaw REST API
        response = requests.post(openclaw_url, json=payload, timeout=120)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(response.content)

        return f"Successfully retrieved assignment via OpenClaw and saved to {output_path}"
    except requests.exceptions.RequestException as e:
        error_msg = f"OpenClaw execution failed: {str(e)}"
        if e.response is not None:
            try:
                err_data = e.response.json()
                if "error_screenshot" in err_data:
                    os.makedirs("data", exist_ok=True)
                    screenshot_data = base64.b64decode(
                        err_data["error_screenshot"])
                    with open("data/portal_error_screenshot.png", "wb") as f:
                        f.write(screenshot_data)
                    error_msg += "\n[A screenshot of the browser failure has been saved to data/portal_error_screenshot.png]"
            except Exception:
                pass
        return error_msg


@tool
def run_nmap_audit(target_ip: str, scan_type: str = "-sV") -> str:
    """
    Delegates task to OpenClaw API to perform an authorized Nmap security 
    audit against a specified target IP or hostname.
    """
    openclaw_url = os.getenv(
        "OPENCLAW_API_URL", "http://localhost:8000/api/automate")

    payload = {
        "task_name": "nmap_security_scan",
        "target_ip": target_ip,
        "scan_type": scan_type
    }

    try:
        response = requests.post(openclaw_url, json=payload, timeout=120)
        response.raise_for_status()

        result_data = response.json()
        scan_results = result_data.get(
            "output", "No output provided by OpenClaw.")

        return f"Nmap Audit Results for {target_ip}:\n{scan_results}"
    except requests.exceptions.RequestException as e:
        return f"OpenClaw Nmap execution failed: {str(e)}"


@tool
def get_allowed_account_credentials(account_name: str) -> str:
    """
    Reads login credentials for a specified account from the 'allowed-access-accounts' folder.
    Use this to retrieve dynamic credentials before instructing ALFRED/AFANDE to perform portal logins.
    """
    folder_path = "allowed-access-accounts"
    file_path = os.path.join(folder_path, f"{account_name}.json")

    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)
        return f"Folder '{folder_path}' was missing and has been created. Please populate it with {account_name}.json."

    if not os.path.exists(file_path):
        available = [f.split('.')[0] for f in os.listdir(
            folder_path) if f.endswith('.json')]
        return f"Credentials for '{account_name}' not found. Available accounts: {', '.join(available) if available else 'None'}"

    try:
        with open(file_path, 'r') as f:
            creds = json.load(f)
        return f"Credentials for {account_name}: {json.dumps(creds)}"
    except Exception as e:
        return f"Failed to read credentials for {account_name}. Error: {str(e)}"


@tool
def generic_openclaw_scrape(url: str, instructions: str = "Extract the main content of the page", wait_for_selector: str = None, run_sentiment_analysis: bool = False, session_id: str = None) -> str:
    """
    Uses OpenClaw's Playwright engine to scrape a generic URL.
    Useful for sites that block standard requests but can be accessed via a headless browser.
    You can optionally specify a CSS selector to wait for, and optionally run sentiment analysis on the result.
    Use session_id if you want OpenClaw to inject previously saved authentication cookies.
    """
    openclaw_url = os.getenv(
        "OPENCLAW_API_URL", "http://localhost:8000/api/automate")

    payload = {
        "task_name": "generic_scrape",
        "target_url": url,
        "instructions": instructions,
        "options": {
            "stealth_mode": True,
            "solve_captcha": bool(os.getenv("CAPTCHA_API_KEY")),
            "captcha_api_key": os.getenv("CAPTCHA_API_KEY"),
            "headless": os.getenv("OPENCLAW_HEADLESS", "True").lower() == "true",
            "screenshot_on_error": True
        }
    }

    if wait_for_selector:
        payload["options"]["wait_for_selector"] = wait_for_selector

    if session_id:
        payload["options"]["use_saved_session"] = True
        payload["options"]["session_id"] = session_id

    try:
        response = requests.post(openclaw_url, json=payload, timeout=120)
        response.raise_for_status()

        result_data = response.json()
        scraped_content = result_data.get(
            "output", "No output provided by OpenClaw.")

        result_str = f"Successfully scraped {url}:\n{scraped_content}"

        if run_sentiment_analysis:
            llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash", temperature=0.1)
            sentiment_prompt = f"Perform a detailed sentiment analysis on this scraped text. Identify the overall tone, emotional drivers, and key themes:\n\n{scraped_content[:15000]}"
            sentiment_response = llm.invoke(
                [HumanMessage(content=sentiment_prompt)])
            result_str += f"\n\n--- AUTO SENTIMENT ANALYSIS ---\n{sentiment_response.content}"

        return result_str
    except requests.exceptions.RequestException as e:
        error_msg = f"OpenClaw execution failed for generic scraper: {str(e)}"
        if e.response is not None:
            try:
                err_data = e.response.json()
                if "error_screenshot" in err_data:
                    os.makedirs("data", exist_ok=True)
                    screenshot_data = base64.b64decode(
                        err_data["error_screenshot"])
                    with open("data/scrape_error_screenshot.png", "wb") as f:
                        f.write(screenshot_data)
                    error_msg += "\n[A screenshot of the browser failure has been saved to data/scrape_error_screenshot.png]"
            except Exception:
                pass
        return error_msg
