import re
import logging
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from dotenv import load_dotenv
import os
import httpx
from app.agents.excutive import ExcutiveAgent
from app.agents.publisher_agent import PublisherAgent
from app.agents.writer_agent import WriterAgent
from app.agents.research_agent import ResearchAgent
from app.debug_network import router as debug_router
#load_dotenv('app/.env')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("whatsapp_bot")

app = FastAPI()
app.include_router(debug_router)
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
OWNER_NUMBER = os.getenv("OWNER_NUMBER")

executive_agent = ExcutiveAgent(servers=None, identity=ExcutiveAgent.identity)
publisher_agent = PublisherAgent(servers=None, identity=PublisherAgent.identity)
research_agent = ResearchAgent(servers=None, identity=ExcutiveAgent.identity)
writer_agent = WriterAgent(servers=None, identity=WriterAgent.identity)

# --- Per-sender state (module-level, persists across requests) ---
# pending_drafts: sender -> draft text awaiting yes/no
# conversation_state: sender -> one of "awaiting_linkedin_topic",
#                                       "awaiting_text_target",
#                                       "awaiting_research_topic"
pending_drafts = {}
conversation_state = {}

# Note: these dicts are in-memory and per-process. Fine for a single worker.
# If you scale to multiple workers/instances, move this to Redis or a DB
# so state is shared across processes.

AFFIRMATIVE_RE = re.compile(r"\b(yes|yep|yeah|sure|ok|okay|post|publish)\b", re.IGNORECASE)
NEGATIVE_RE = re.compile(r"\b(no|nah|not|don'?t)\b", re.IGNORECASE)


def is_affirmative(text: str) -> bool:
    return bool(AFFIRMATIVE_RE.search(text))


def is_negative(text: str) -> bool:
    return bool(NEGATIVE_RE.search(text))


async def send_whatsapp_message(to_number: str, message: str):
    url = f"https://graph.facebook.com/v25.0/{PHONE_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": message},
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=30)
            logger.info("WhatsApp send status=%s body=%s", response.status_code, response.text)
            return response
    except Exception as e:
        logger.exception("Failed to send WhatsApp message to %s: %s", to_number, e)
        return None


async def create_linkedin_post(text: str, sender: str):
    current_draft = pending_drafts.get(sender)

    if current_draft and is_affirmative(text):
        await send_whatsapp_message(
            to_number=sender, message="Posting the content on LinkedIn..."
        )

        publish_prompt = (
            "The following LinkedIn content has been approved for publishing. "
            "Use the local tool `post_to_linkedin` to publish it. "
            "Extract the post text and, if an image URL is present in the content, pass it as `image_url`. "
            "Do not create new content. Return only the tool result or a concise status message.\n\n"
            f"Approved content:\n{current_draft}"
        )

        try:
            post_response = await publisher_agent.run_prompt(publish_prompt)
        except Exception as e:
            logger.exception("publisher_agent failed: %s", e)
            post_response = f"Error while publishing: {e}"

        pending_drafts.pop(sender, None)

        await send_whatsapp_message(
            to_number=sender,
            message=f"Content posted on LinkedIn. Response: {post_response}",
        )
        return

    if current_draft and is_negative(text):
        await send_whatsapp_message(
            to_number=sender,
            message="Okay, I will update the draft using your feedback.",
        )

        try:
            modified_draft = await writer_agent.run_prompt(
                f"Please modify the content as per the following feedback: {text}. "
                f"Original content: {current_draft}, and generate an updated version "
                "of the LinkedIn post. Return only the modified content without any explanations."
            )
        except Exception as e:
            logger.exception("writer_agent failed: %s", e)
            modified_draft = None

        if modified_draft:
            pending_drafts[sender] = modified_draft
            await send_whatsapp_message(
                to_number=sender,
                message=(
                    f"Modified content: {modified_draft}\n\n"
                    "Please review and reply with yes to post or no to update again."
                ),
            )
        else:
            await send_whatsapp_message(
                to_number=sender,
                message="I could not update the draft. Please share your feedback again.",
            )
        return

    if current_draft:
        await send_whatsapp_message(
            to_number=sender,
            message="I already have a draft for you. Reply with yes to post it or no to provide feedback.",
        )
        return

    try:
        generated_draft = await executive_agent.run_prompt(text)
    except Exception as e:
        logger.exception("executive_agent failed: %s", e)
        generated_draft = None

    if not generated_draft:
        await send_whatsapp_message(
            to_number=sender,
            message="I could not generate LinkedIn content from your request. Please try again.",
        )
        return

    pending_drafts[sender] = generated_draft
    await send_whatsapp_message(
        to_number=sender,
        message=(
            f"Please review the generated LinkedIn post below and reply with yes to post it "
            f"or no to make changes:\n\n{generated_draft}"
        ),
    )


async def handle_text_on_behalf(text: str, sender: str):
    try:
        number, msg = text.split(" ", 1)
        await send_whatsapp_message(to_number=number, message=msg)
        await send_whatsapp_message(
            to_number=sender,
            message=f"Message sent to {number} on your behalf.",
        )
    except ValueError:
        await send_whatsapp_message(
            to_number=sender,
            message="Please provide the input in the format: <number> <message>",
        )


async def handle_research(text: str, sender: str):
    research_topic = text
    research_prompt = (
        f"Please conduct research on the following topic: {research_topic}. "
        "Provide a summary of your findings and any relevant insights. "
        "Return only the research summary without any additional explanations."
    )
    try:
        research_summary = await research_agent.run_prompt(research_prompt)
    except Exception as e:
        logger.exception("research_agent failed: %s", e)
        research_summary = f"Error while researching: {e}"

    await send_whatsapp_message(
        to_number=sender,
        message=f"Research summary on '{research_topic}':\n\n{research_summary}",
    )


async def process_text_message(text: str, sender: str):
    """
    Handles one incoming text message from the owner. Runs as a background
    task so the webhook can ack Meta immediately.
    """
    text_stripped = text.strip()
    text_lower = text_stripped.lower()
    state = conversation_state.get(sender)

    # --- Check pending state FIRST, before keyword matching, so replies
    # don't get reinterpreted as new commands. ---

    if sender in pending_drafts:
        # Mid-conversation about an existing LinkedIn draft (yes/no/feedback)
        await create_linkedin_post(text_stripped, sender)
        return

    if state == "awaiting_linkedin_topic":
        conversation_state.pop(sender, None)
        await create_linkedin_post(text_stripped, sender)
        return

    if state == "awaiting_text_target":
        conversation_state.pop(sender, None)
        await handle_text_on_behalf(text_stripped, sender)
        return

    if state == "awaiting_research_topic":
        conversation_state.pop(sender, None)
        await handle_research(text_stripped, sender)
        return

    # --- No pending state: check for commands ---

    if text_lower == "help, jarvis":
        await send_whatsapp_message(
            to_number=OWNER_NUMBER,
            message=(
                "Available commands: create linkedin post, text that number on my behalf, "
                "do research on <topic>\n\n"
                "Type the command and I'll ask you for the details I need."
            ),
        )
        return

    if "create linkedin post" in text_lower:
        conversation_state[sender] = "awaiting_linkedin_topic"
        await send_whatsapp_message(
            to_number=sender,
            message="About what topic would you like to create a LinkedIn post? Please provide some details.",
        )
        return

    if "text that number on my behalf" in text_lower:
        conversation_state[sender] = "awaiting_text_target"
        await send_whatsapp_message(
            to_number=sender,
            message="Please provide the number and the message you want to send.",
        )
        return

    if "do research on" in text_lower:
        conversation_state[sender] = "awaiting_research_topic"
        await send_whatsapp_message(
            to_number=sender,
            message="Please provide the topic you want me to research.",
        )
        return

    # Unrecognized command/text with no pending state
    await send_whatsapp_message(
        to_number=sender,
        message="I didn't recognize that. Send 'help, Jarvis' to see available commands.",
    )


async def process_webhook_payload(data: dict):
    """
    Background task: does all the actual work after Meta has already
    been ack'd with a 200 response.
    """
    try:
        value = data["entry"][0]["changes"][0]["value"]
        if "messages" not in value:
            return

        message = value["messages"][0]
        sender = message["from"]

        if sender != OWNER_NUMBER:
            # Notify the owner about messages from other numbers, but don't
            # act on them as commands.
            await send_whatsapp_message(
                to_number=OWNER_NUMBER,
                message=f"Received message from {sender}: {message}",
            )
            return

        if message.get("type") == "text":
            text = message["text"]["body"]
            await process_text_message(text, sender)

    except Exception as e:
        logger.exception("Webhook processing error: %s", e)
        # Best-effort notify owner that something broke, so failures aren't silent.
        try:
            await send_whatsapp_message(
                to_number=OWNER_NUMBER,
                message=f"Webhook processing error: {e}",
            )
        except Exception:
            pass


@app.get("/webhook")
async def verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return int(challenge)
    raise HTTPException(status_code=403)


@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    # Ack Meta immediately; do all real work in the background so we never
    # risk Meta timing out and retrying (which would cause duplicate sends).
    background_tasks.add_task(process_webhook_payload, data)
    return {"status": "ok"}