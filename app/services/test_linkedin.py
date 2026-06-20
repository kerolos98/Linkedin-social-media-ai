"""
Quick LinkedIn Company Page Post Test
Diamond Foxes
--------------------------------------
Requirements:
    pip install requests

Usage:
    1. Replace MAKE_WEBHOOK_URL with your Make.com webhook URL
    2. Run: python test_linkedin_post.py
"""

import requests
import os
# ── CONFIG ────────────────────────────────────────────────────────
MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL")  # Set this in your environment variables
# ─────────────────────────────────────────────────────────────────

POST_TEXT = """🧠 AI is reshaping healthcare in 2026 — and the numbers speak for themselves.

📊 Healthcare AI spending hit $1.4B in 2025 and is accelerating
🩺 75%+ of physicians say AI improves patient care
🤖 Agentic AI is becoming part of the clinical workforce
📋 Epic Systems rolling out 150+ AI-embedded clinical features

At Diamond Foxes, we're proud to be part of this transformation — helping healthcare organizations automate medical coding and unlock the full value of their data with AI.

The future of healthcare is intelligent. Are you ready?

#HealthcareAI #MedicalAI #DiamondFoxes #DigitalHealth"""

IMAGE_URL = "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=1024"


def test_post():
    print(f"📝 Post length: {len(POST_TEXT)} characters")
    print("📤 Sending test post (text + image) to LinkedIn via Make.com...")

    response = requests.post(
        MAKE_WEBHOOK_URL,
        json={
            "text": POST_TEXT,
            "image_url": IMAGE_URL
        },
        timeout=15
    )

    if response.status_code == 200:
        print("✅ Success! Check your LinkedIn Company Page.")
    else:
        print(f"❌ Failed. Status: {response.status_code}")
        print(f"Response: {response.text}")


if __name__ == "__main__":
    test_post()