import os
import requests
from langchain_core.tools import tool


@tool
def post_to_social_media(platform: str, content: str) -> str:
    """
    Automates posting content to social media sites (Twitter, LinkedIn, etc.).
    Relies on a configured SOCIAL_WEBHOOK_URL (like an n8n or Zapier trigger) in the environment.
    """
    try:
        webhook_url = os.getenv("SOCIAL_WEBHOOK_URL")
        if not webhook_url:
            return "SOCIAL_WEBHOOK_URL environment variable is missing. Cannot route social media post."

        payload = {"platform": platform, "content": content}
        response = requests.post(webhook_url, json=payload, timeout=30)
        response.raise_for_status()

        return f"Successfully queued post for {platform} via automation webhook."
    except Exception as e:
        return f"Failed to post to social media: {str(e)}"


@tool
def make_web_request(url: str, method: str = "GET", payload: dict = None) -> str:
    """
    Makes a generic HTTP web request to a given web address.
    Useful for triggering external APIs, scraping raw endpoints, or fetching remote data.
    """
    try:
        if method.upper() == "POST":
            res = requests.post(url, json=payload, timeout=30)
        else:
            res = requests.get(url, params=payload, timeout=30)
        res.raise_for_status()
        return f"Web request to {url} succeeded. Response preview:\n{res.text[:800]}"
    except Exception as e:
        return f"Web request failed: {str(e)}"


@tool
def send_text_message(to_number: str, message: str, use_whatsapp: bool = False) -> str:
    """
    Sends an SMS or WhatsApp message using Twilio.
    Requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER environment variables.
    Format phone numbers with country code (e.g., +1234567890).
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")

    if not all([account_sid, auth_token, from_number]):
        return "Error: Twilio credentials are not fully configured in the environment."

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

    if use_whatsapp:
        if not to_number.startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"
        if not from_number.startswith("whatsapp:"):
            from_number = f"whatsapp:{from_number}"

    payload = {
        "To": to_number,
        "From": from_number,
        "Body": message
    }

    try:
        response = requests.post(url, data=payload, auth=(
            account_sid, auth_token), timeout=10)
        response.raise_for_status()
        return f"Successfully sent {'WhatsApp' if use_whatsapp else 'SMS'} message to {to_number}."
    except Exception as e:
        return f"Failed to send message: {str(e)}"
