import requests
import sys


def trigger_alfred_task(prompt: str):
    """
    Sends an automated prompt to ALFRED's FastAPI backend.
    """
    url = "http://localhost:8000/chat"

    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "thread_id": "cron_scheduler_thread"
    }

    try:
        # Timeout set to 180 seconds to give ALFRED and OpenClaw time to execute the task
        response = requests.post(url, json=payload, timeout=180)
        response.raise_for_status()

        result = response.json()
        print(f"Task Succeeded!\nALFRED Response:\n{result.get('content')}")

    except requests.exceptions.RequestException as e:
        print(f"Task Failed: {e}")


if __name__ == "__main__":
    # Example: You can change this prompt to any task you want ALFRED to automate
    trigger_alfred_task(
        "Please tell AFANDE to run a quick Nmap audit on 127.0.0.1")
