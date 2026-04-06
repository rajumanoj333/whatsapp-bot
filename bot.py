"""
CareerG1 WhatsApp Marketing Bot
Production-ready webhook bot using Evolution API + FastAPI
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
import os
import logging
import json
from datetime import datetime

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("wabot")

# --- Config ---
EVOLUTION_API = os.getenv("EVOLUTION_API_URL", "").rstrip("/")
API_KEY = os.getenv("EVOLUTION_API_KEY", "")
INSTANCE = os.getenv("INSTANCE_NAME", "")
BOT_NUMBER = os.getenv("BOT_NUMBER", "")  # Your WhatsApp number (without +)

app = FastAPI(title="CareerG1 WhatsApp Bot", version="1.0.0")

# --- In-memory conversation state (use Redis/DB for multi-instance) ---
# State per user: {phone: {"step": "...", "data": {...}, "last_seen": "..."}}
conversations = {}

# --- Product catalog / marketing messages ---
WELCOME_MSG = (
    "Hey there! Welcome to *CareerG1* - Your AI-Powered Career Guidance Platform!\n\n"
    "We help students discover the right career path with personalized AI guidance.\n\n"
    "What would you like to know?\n\n"
    "1. About CareerG1\n"
    "2. Our Features\n"
    "3. Pricing\n"
    "4. Book a Free Demo\n"
    "5. Talk to Support\n\n"
    "Just reply with the number or type your question!"
)

ABOUT_MSG = (
    "*About CareerG1*\n\n"
    "CareerG1 is an AI-powered career guidance platform that helps students:\n\n"
    "- Discover their ideal career path\n"
    "- Get personalized college recommendations\n"
    "- Access AI-driven aptitude assessments\n"
    "- Connect with mentors and counselors\n\n"
    "We've helped 10,000+ students find their perfect career!\n\n"
    "Reply *2* for features, *4* to book a demo, or ask anything!"
)

FEATURES_MSG = (
    "*CareerG1 Features*\n\n"
    "- AI Career Assessment & RIASEC Test\n"
    "- Personalized College Recommendations\n"
    "- Entrance Exam Preparation Guides\n"
    "- 1-on-1 Mentorship Sessions\n"
    "- Resume Builder & Interview Prep\n"
    "- Real-time Application Tracking\n\n"
    "Ready to get started? Reply *4* to book a free demo!"
)

PRICING_MSG = (
    "*CareerG1 Plans*\n\n"
    "*Free Plan* - Basic career assessment\n"
    "*Pro Plan* - Full AI guidance + mentorship\n"
    "*Premium Plan* - Everything + priority support\n\n"
    "Reply *4* to book a free demo and we'll find the best plan for you!"
)

DEMO_START_MSG = (
    "Awesome! Let's book your *free demo*.\n\n"
    "I just need a few details. Let's start:\n\n"
    "What is your *full name*?"
)

SUPPORT_MSG = (
    "Our support team is available!\n\n"
    "- Email: hello@careerg1.app\n"
    "- Website: https://careerg1.app\n\n"
    "Or just type your question here and we'll get back to you!"
)


def get_conversation(phone: str) -> dict:
    if phone not in conversations:
        conversations[phone] = {
            "step": "new",
            "data": {},
            "last_seen": datetime.utcnow().isoformat(),
        }
    conversations[phone]["last_seen"] = datetime.utcnow().isoformat()
    return conversations[phone]


def send_message(number: str, text: str):
    """Send a WhatsApp text message via Evolution API."""
    url = f"{EVOLUTION_API}/message/sendText/{INSTANCE}"
    headers = {"apikey": API_KEY, "Content-Type": "application/json"}
    data = {"number": number, "text": text}

    try:
        resp = requests.post(url, json=data, headers=headers, timeout=10)
        resp.raise_for_status()
        logger.info(f"Message sent to {number[:6]}***")
    except requests.RequestException as e:
        logger.error(f"Failed to send message to {number}: {e}")


def send_bulk_marketing(numbers: list[str], message: str):
    """Send marketing message to a list of numbers."""
    results = {"sent": 0, "failed": 0}
    for number in numbers:
        try:
            send_message(number, message)
            results["sent"] += 1
        except Exception:
            results["failed"] += 1
    return results


def handle_message(phone: str, message: str) -> str:
    """Process incoming message and return reply based on conversation state."""
    conv = get_conversation(phone)
    step = conv["step"]
    msg = message.strip().lower()

    # --- Demo booking flow (collecting info) ---
    if step == "ask_name":
        conv["data"]["name"] = message.strip()
        conv["step"] = "ask_email"
        return f"Thanks *{message.strip()}*! Now, what's your *email address*?"

    if step == "ask_email":
        conv["data"]["email"] = message.strip()
        conv["step"] = "ask_course"
        return "What *course or career* are you interested in?"

    if step == "ask_course":
        conv["data"]["course"] = message.strip()
        conv["step"] = "done"
        name = conv["data"].get("name", "")
        email = conv["data"].get("email", "")
        course = conv["data"].get("course", "")

        logger.info(
            f"NEW LEAD: {name} | {email} | {phone} | {course}"
        )

        return (
            f"You're all set, *{name}*!\n\n"
            f"*Your Details:*\n"
            f"- Name: {name}\n"
            f"- Email: {email}\n"
            f"- Interest: {course}\n\n"
            "Our team will reach out to you within 24 hours to schedule your free demo.\n\n"
            "Meanwhile, check out https://careerg1.app\n\n"
            "Type *hi* anytime to start over!"
        )

    # --- Main menu handling ---
    if msg in ("1", "about"):
        conv["step"] = "menu"
        return ABOUT_MSG

    if msg in ("2", "features", "feature"):
        conv["step"] = "menu"
        return FEATURES_MSG

    if msg in ("3", "pricing", "price", "plans"):
        conv["step"] = "menu"
        return PRICING_MSG

    if msg in ("4", "demo", "book", "register", "signup", "sign up"):
        conv["step"] = "ask_name"
        return DEMO_START_MSG

    if msg in ("5", "support", "help"):
        conv["step"] = "menu"
        return SUPPORT_MSG

    if msg in ("hi", "hello", "hey", "start", "menu"):
        conv["step"] = "menu"
        return WELCOME_MSG

    # Default: treat as a question, send welcome
    if step == "new" or step == "done":
        conv["step"] = "menu"
        return WELCOME_MSG

    # If in menu but unrecognized input
    conv["step"] = "menu"
    return (
        "I didn't quite get that. Please reply with a number:\n\n"
        "1. About CareerG1\n"
        "2. Features\n"
        "3. Pricing\n"
        "4. Book a Free Demo\n"
        "5. Support\n\n"
        "Or type *hi* to start over!"
    )


# --- API Endpoints ---


@app.get("/")
async def root():
    return {"status": "running", "bot": "CareerG1 WhatsApp Bot", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/webhook")
async def webhook(request: Request):
    """Handle incoming webhook from Evolution API."""
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    # Log event type for debugging
    event = payload.get("event")
    logger.info(f"Webhook event: {event}")

    # Only process incoming messages
    if event != "messages.upsert":
        return {"ignored": True, "reason": f"event={event}"}

    try:
        data = payload.get("data", {})
        key = data.get("key", {})
        message_data = data.get("message", {})

        # Skip messages sent by the bot itself
        if key.get("fromMe", False):
            return {"ignored": True, "reason": "own message"}

        # Skip status broadcasts
        remote_jid = key.get("remoteJid", "")
        if remote_jid == "status@broadcast":
            return {"ignored": True, "reason": "status broadcast"}

        # Extract phone number
        phone = remote_jid.split("@")[0]
        if not phone:
            return {"ignored": True, "reason": "no phone"}

        # Extract message text (handle different message types)
        text = (
            message_data.get("conversation")
            or message_data.get("extendedTextMessage", {}).get("text")
            or ""
        )

        if not text:
            # Handle non-text messages (images, audio, etc.)
            send_message(
                phone,
                "I can only read text messages for now. Please type your message!",
            )
            return {"status": "non-text handled"}

        logger.info(f"Message from {phone[:6]}***: {text[:50]}")

        # Process and reply
        reply = handle_message(phone, text)
        send_message(phone, reply)

        return {"status": "replied"}

    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        return {"error": str(e)}


@app.post("/send")
async def send_single(request: Request):
    """API endpoint to send a message to a specific number."""
    body = await request.json()
    number = body.get("number", "")
    text = body.get("text", "")

    if not number or not text:
        return JSONResponse({"error": "number and text required"}, status_code=400)

    send_message(number, text)
    return {"status": "sent", "number": number}


@app.post("/broadcast")
async def broadcast(request: Request):
    """Send a marketing message to multiple numbers."""
    body = await request.json()
    numbers = body.get("numbers", [])
    message = body.get("message", "")

    if not numbers or not message:
        return JSONResponse(
            {"error": "numbers (list) and message required"}, status_code=400
        )

    results = send_bulk_marketing(numbers, message)
    return {"status": "broadcast complete", **results}


@app.get("/leads")
async def get_leads():
    """Get all collected leads (demo bookings)."""
    leads = []
    for phone, conv in conversations.items():
        if conv.get("data"):
            leads.append({"phone": phone, **conv["data"], "last_seen": conv["last_seen"]})
    return {"leads": leads, "total": len(leads)}


@app.get("/conversations")
async def get_conversations():
    """Get all active conversations (for debugging)."""
    return {
        "total": len(conversations),
        "conversations": {
            phone: {"step": c["step"], "last_seen": c["last_seen"]}
            for phone, c in conversations.items()
        },
    }
