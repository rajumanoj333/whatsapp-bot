"""
Antz.ai WhatsApp Marketing Bot
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

app = FastAPI(title="Antz.ai WhatsApp Bot", version="1.0.0")

# --- In-memory conversation state (use Redis/DB for multi-instance) ---
conversations = {}

# --- Antz.ai Marketing Messages ---
WELCOME_MSG = (
    "Hey there! Welcome to *Antz.ai* - Build Your AI Workforce!\n\n"
    "We transform traditional businesses into autonomous enterprises "
    "using advanced AI Agents. Scale operations and unlock unprecedented efficiency.\n\n"
    "What would you like to know?\n\n"
    "1. About Antz.ai\n"
    "2. Our Solutions\n"
    "3. How It Works\n"
    "4. Book a Free Consultation\n"
    "5. Talk to Our Team\n\n"
    "Just reply with the number or type your question!"
)

ABOUT_MSG = (
    "*About Antz.ai*\n\n"
    "We test emerging AI tools, identify practical applications, and guide clients "
    "toward solutions that deliver *measurable results* - not just impressive demos.\n\n"
    "*Why Enterprises Work with Antz:*\n\n"
    "- *Rapid Deployment* - Concept to production-ready systems within weeks\n"
    "- *Trusted Security* - Data protection & privacy integrated throughout\n"
    "- *Extended Partner* - Ongoing collaboration to find new automation opportunities\n\n"
    "Reply *2* for solutions, *4* to book a consultation, or ask anything!"
)

SOLUTIONS_MSG = (
    "*Antz.ai Solutions*\n\n"
    "- *AI Agents* - Autonomous workforce that handles complex tasks\n"
    "- *Process Automation* - Streamline operations end-to-end\n"
    "- *Data Intelligence* - Turn your data into actionable insights\n"
    "- *Enterprise Consulting* - Strategic AI transformation roadmap\n\n"
    "Ready to transform your business? Reply *4* to book a free consultation!"
)

JOURNEY_MSG = (
    "*The Journey to Autonomy* - Our 4-Phase Process\n\n"
    "*Phase 1: Discovery*\n"
    "In-depth business analysis to find high-impact automation candidates\n\n"
    "*Phase 2: Strategy*\n"
    "Custom agentic architecture designed for your specific objectives\n\n"
    "*Phase 3: Execution*\n"
    "Agent development and seamless system integration\n\n"
    "*Phase 4: Extended Partnership*\n"
    "Continuous improvement and new automation identification\n\n"
    "Reply *4* to start your journey today!"
)

CONSULTATION_START_MSG = (
    "Great choice! Let's book your *free AI consultation*.\n\n"
    "I just need a few details. Let's start:\n\n"
    "What is your *full name*?"
)

SUPPORT_MSG = (
    "Our team is ready to help!\n\n"
    "- Website: https://antz.ai\n"
    "- LinkedIn: Antz.ai\n\n"
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

    # --- Consultation booking flow ---
    if step == "ask_name":
        conv["data"]["name"] = message.strip()
        conv["step"] = "ask_email"
        return f"Thanks *{message.strip()}*! Now, what's your *business email*?"

    if step == "ask_email":
        conv["data"]["email"] = message.strip()
        conv["step"] = "ask_company"
        return "What's your *company name*?"

    if step == "ask_company":
        conv["data"]["company"] = message.strip()
        conv["step"] = "ask_challenge"
        return (
            "What *business challenge* are you looking to solve with AI?\n\n"
            "e.g., Process automation, data analysis, customer support, etc."
        )

    if step == "ask_challenge":
        conv["data"]["challenge"] = message.strip()
        conv["step"] = "done"
        name = conv["data"].get("name", "")
        email = conv["data"].get("email", "")
        company = conv["data"].get("company", "")
        challenge = conv["data"].get("challenge", "")

        logger.info(
            f"NEW LEAD: {name} | {email} | {company} | {phone} | {challenge}"
        )

        return (
            f"You're all set, *{name}*!\n\n"
            f"*Your Details:*\n"
            f"- Name: {name}\n"
            f"- Email: {email}\n"
            f"- Company: {company}\n"
            f"- Challenge: {challenge}\n\n"
            "Our AI strategy team will reach out within 24 hours "
            "to schedule your free consultation.\n\n"
            "Meanwhile, visit https://antz.ai to explore more.\n\n"
            "Type *hi* anytime to start over!"
        )

    # --- Main menu handling ---
    if msg in ("1", "about"):
        conv["step"] = "menu"
        return ABOUT_MSG

    if msg in ("2", "solutions", "features", "services"):
        conv["step"] = "menu"
        return SOLUTIONS_MSG

    if msg in ("3", "how", "process", "journey", "how it works"):
        conv["step"] = "menu"
        return JOURNEY_MSG

    if msg in ("4", "demo", "book", "consult", "consultation", "register", "signup"):
        conv["step"] = "ask_name"
        return CONSULTATION_START_MSG

    if msg in ("5", "support", "help", "contact", "team"):
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
        "1. About Antz.ai\n"
        "2. Our Solutions\n"
        "3. How It Works\n"
        "4. Book a Free Consultation\n"
        "5. Talk to Our Team\n\n"
        "Or type *hi* to start over!"
    )


# --- API Endpoints ---


@app.get("/")
async def root():
    return {"status": "running", "bot": "Antz.ai WhatsApp Bot", "version": "1.0.0"}


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

    event = payload.get("event","")
    logger.info(f"Webhook event: {event}")

    if event.lower().replace("_", ".") != "messages.upsert":
        return {"ignored": True, "reason": f"event={event}"}

    try:
        data = payload.get("data", {})
        key = data.get("key", {})
        message_data = data.get("message", {})

        if key.get("fromMe", False):
            return {"ignored": True, "reason": "own message"}

        remote_jid = key.get("remoteJid", "")
        if remote_jid == "status@broadcast":
            return {"ignored": True, "reason": "status broadcast"}

        phone = remote_jid.split("@")[0]
        if not phone:
            return {"ignored": True, "reason": "no phone"}

        text = (
            message_data.get("conversation")
            or message_data.get("extendedTextMessage", {}).get("text")
            or ""
        )

        if not text:
            send_message(
                phone,
                "I can only read text messages for now. Please type your message!",
            )
            return {"status": "non-text handled"}

        logger.info(f"Message from {phone[:6]}***: {text[:50]}")

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
    """Get all collected leads (consultation bookings)."""
    leads = []
    for phone, conv in conversations.items():
        if conv.get("data"):
            leads.append({"phone": phone, **conv["data"], "last_seen": conv["last_seen"]})
    return {"leads": leads, "total": len(leads)}


@app.get("/conversations")
async def get_conversations():
    """Get all active conversations."""
    return {
        "total": len(conversations),
        "conversations": {
            phone: {"step": c["step"], "last_seen": c["last_seen"]}
            for phone, c in conversations.items()
        },
    }
