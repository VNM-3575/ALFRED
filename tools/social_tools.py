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
