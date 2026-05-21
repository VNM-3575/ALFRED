# tools/security_tools.py or tools/portal_tools.py
import os
import requests
import base64
from langchain_core.tools import tool


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
