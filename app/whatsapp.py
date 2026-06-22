from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
import os
import httpx
from app.agents.excutive import ExcutiveAgent
from app.agents.publisher_agent import PublisherAgent
from app.agents.writer_agent import WriterAgent
from app.agents.research_agent import ResearchAgent

load_dotenv('app/.env')

app = FastAPI()

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
OWNER_NUMBER = os.getenv("OWNER_NUMBER")
executive_agent = ExcutiveAgent(servers=None, identity=ExcutiveAgent.identity)
publisher_agent = PublisherAgent(servers=None, identity=PublisherAgent.identity)
research_agent = ResearchAgent(servers=None, identity=ExcutiveAgent.identity)
writer_agent = WriterAgent(servers=None, identity=WriterAgent.identity)
pending_drafts = {}


def is_affirmative(text: str) -> bool:
    normalized = text.lower()
    return any(
        token in normalized for token in ["yes", "yep", "yeah", "post", "publish"]
    )


def is_negative(text: str) -> bool:
    normalized = text.lower()
    return any(token in normalized for token in ["no", "nah", "not", "don'", "dont"])


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

        post_response = await publisher_agent.run_prompt(publish_prompt)
        pending_drafts.pop(sender, None)

        await send_whatsapp_message(
            to_number=sender,
            message=f"Content posted on LinkedIn. Response: {post_response}",
        )
        return {"status": "ok"}

    if current_draft and is_negative(text):
        await send_whatsapp_message(
            to_number=sender,
            message="Okay, I will update the draft using your feedback.",
        )

        modified_draft = await writer_agent.run_prompt(
            f"Please modify the content as per the following feedback: {text}. Original content: {current_draft}, and generate an updated version of the LinkedIn post. Return only the modified content without any explanations."
        )

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
        return {"status": "ok"}

    if current_draft:
        await send_whatsapp_message(
            to_number=sender,
            message="I already have a draft for you. Reply with yes to post it or no to provide feedback.",
        )
        return {"status": "ok"}

    generated_draft = await executive_agent.run_prompt(text)

    if not generated_draft:
        await send_whatsapp_message(
            to_number=sender,
            message="I could not generate LinkedIn content from your request. Please try again.",
        )
        return {"status": "ok"}

    pending_drafts[sender] = generated_draft
    await send_whatsapp_message(
        to_number=sender,
        message=(
            f"Please review the generated LinkedIn post below and reply with yes to post it or no to make changes:\n\n{generated_draft}"
        ),
    )


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

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=30)
        print(response.status_code)
        print(response.text)
    return response


@app.get("/webhook")
async def verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return int(challenge)
    raise HTTPException(status_code=403)


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    linkedin_followup = False
    text_on_behalf_followup = False
    do_research_followup = False
    try:
        value = data["entry"][0]["changes"][0]["value"]
        if "messages" not in value:
            return {"status": "ok"}

        message = value["messages"][0]
        sender = message["from"]
        if sender != OWNER_NUMBER:
            send_message = await send_whatsapp_message(
                to_number=OWNER_NUMBER,
                message=f"Received message from {sender}: {message}",
            )
        if sender != OWNER_NUMBER and text_on_behalf_followup:
            await send_whatsapp_message(
                to_number=OWNER_NUMBER,
                message=f"Received message from {sender} that seems to be a follow-up for sending text on behalf: {message}",
            )
            text_on_behalf_followup = True
            return {"status": "ok"}

        if message["type"] == "text" and sender == OWNER_NUMBER:
            text = message["text"]["body"].strip()
            if text.lower() == "help, Jarvis":
                print("Sending help message to owner...")
                send_message = await send_whatsapp_message(
                to_number=OWNER_NUMBER,
                message=f"Available commands: create linkedin post, text that number on my behalf \n\n if you want to create a linkedin post or text on behalf of your number. Please type the command followed by the content.",
            )
            if "create linkedin post" in text.lower():
                print("Received command to create LinkedIn post. Asking for topic details...")
                send_message = await send_whatsapp_message(
                    to_number=sender,
                    message="about what topic would you like to create a LinkedIn post? Please provide some details.",
                )
                return {"status": "ok"}
            if linkedin_followup:
                await create_linkedin_post(text, sender)
                linkedin_followup = False
                return {"status": "ok"}
            if "text that number on my behalf" in text.lower():
                print("Received command to text on behalf. Asking for number and message...")
                await send_whatsapp_message(
                    to_number=sender,
                    message="Please provide the number and the message you want to send.",
                )
                return {"status": "ok"}
            if text_on_behalf_followup:
                try:
                    number, msg = text.split(" ", 1)
                    await send_whatsapp_message(to_number=number, message=msg)
                    await send_whatsapp_message(
                        to_number=sender,
                        message=f"Message sent to {number} on your behalf.",
                    )
                    text_on_behalf_followup = False
                except ValueError:
                    await send_whatsapp_message(
                        to_number=sender,
                        message="Please provide the input in the format: <number> <message>",
                    )
                return {"status": "ok"}
            if "do research on" in text.lower():
                await send_whatsapp_message(
                    to_number=sender,
                    message="Please provide the topic you want me to research.",
                )
                do_research_followup = True
                return {"status": "ok"}
            if do_research_followup:
                research_topic = text
                research_prompt = (
                    f"Please conduct research on the following topic: {research_topic}. "
                    "Provide a summary of your findings and any relevant insights. "
                    "Return only the research summary without any additional explanations."
                )
                research_summary = await research_agent.run_prompt(research_prompt)
                await send_whatsapp_message(
                    to_number=sender,
                    message=f"Research summary on '{research_topic}':\n\n{research_summary}",
                )
                do_research_followup = False
                return {"status": "ok"}

    except Exception as e:
        print("Webhook Error:", e)

    return {"status": "ok"}
