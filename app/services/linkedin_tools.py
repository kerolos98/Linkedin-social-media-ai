from dotenv import load_dotenv
import os
import requests
from typing import Optional
from langchain.tools import tool

#load_dotenv("app/services/.env")


@tool("post_to_linkedin", return_direct=True)
def post_to_linkedin(text: str, image_url: Optional[str] = None) -> str:
    """Posts text (and optionally a image_url url , it can be an image url) to LinkedIn.

    Returns a short status string describing the result.
    """
    payload = {"text": text}
    if image_url:
        payload["image_url"] = image_url

    webhook = os.getenv("LINKEDIN_WEBHOOK")
    if not webhook:
        return "Error: LINKEDIN_WEBHOOK not configured"

    try:
        response = requests.post(webhook, json=payload, timeout=15)
    except Exception as e:
        return f"Error: {e}"

    if response.status_code == 200:
        return "Success: Posted to LinkedIn."
    return f"Failed: {response.status_code} - {response.text}"
