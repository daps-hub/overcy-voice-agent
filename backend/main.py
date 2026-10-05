from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
import websockets
import os
import json
import requests
import asyncio
DEFAULT_BUSINESS_ID = "tanimo"
from fastapi.responses import Response
from pydantic import BaseModel

from backend.agent import run_agent
from backend.database import initialize_database
from backend.tools.leads import create_lead
from backend.config.businesses import (
    get_business,
    get_business_by_phone,
)
from backend.tools.appointments import (
    create_appointment,
    cancel_appointment,
    reschedule_appointment,
)
from backend.tools.booking import create_lead_and_appointment
from backend.tools.knowledge import search_business_knowledge
from backend.voice import transcribe_audio, synthesize_speech
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="Voice Agent Demo",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://app.tanimosoftware.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



initialize_database()


class RealtimeToolRequest(BaseModel):
    name: str
    arguments: dict
    name_confirmed: bool = False
    appointment_confirmed: bool = False


class LeadRequest(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    interest: str | None = None


class ChatRequest(BaseModel):
    message: str


class TTSRequest(BaseModel):
    text: str


class AppointmentRequest(BaseModel):
    lead_id: int
    appointment_date: str
    appointment_time: str


@app.get("/")
def root():
    return {
        "status": "online",
        "service": "AI Voice Agent",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }


@app.post("/api/leads")
def add_lead(lead: LeadRequest):
    return create_lead(
        name=lead.name,
        phone=lead.phone,
        email=lead.email,
        interest=lead.interest,
    )


@app.post("/api/appointments")
def add_appointment(appointment: AppointmentRequest):
    return create_appointment(
        lead_id=appointment.lead_id,
        appointment_date=appointment.appointment_date,
        appointment_time=appointment.appointment_time,
    )
@app.get("/api/appointments")
def get_appointments():
    from backend.database import get_connection

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            appointments.id,
            appointments.lead_id,
            appointments.appointment_date,
            appointments.appointment_time,
            appointments.status,
            appointments.created_at,
            leads.name,
            leads.phone,
            leads.email,
            leads.interest
        FROM appointments
        LEFT JOIN leads
            ON appointments.lead_id = leads.id
        ORDER BY
            appointments.appointment_date ASC,
            appointments.appointment_time ASC
    """)

    rows = cursor.fetchall()
    connection.close()

    return {
        "appointments": [
            {
                "id": row["id"],
                "lead_id": row["lead_id"],
                "name": row["name"],
                "phone": row["phone"],
                "email": row["email"],
                "reason": row["interest"],
                "appointment_date": row["appointment_date"],
                "appointment_time": row["appointment_time"],
                "status": row["status"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    }

@app.post("/api/agent")
def agent_chat(request: ChatRequest):
    return run_agent(request.message)


@app.post("/api/voice/transcribe")
async def voice_transcribe(
    audio: UploadFile = File(...),
):
    audio_bytes = await audio.read()

    transcript = transcribe_audio(
        audio_bytes=audio_bytes,
        filename=audio.filename or "audio.webm",
    )

    return {
        "transcript": transcript,
    }


@app.post("/api/tts")
def text_to_speech(request: TTSRequest):
    speech_audio = synthesize_speech(request.text)

    return Response(
        content=speech_audio,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": "inline; filename=agent-response.mp3",
        },
    )


@app.post("/api/voice/speak")
async def voice_speak(
    audio: UploadFile = File(...),
    session_id: str = Form("default"),
):
    audio_bytes = await audio.read()

    transcript = transcribe_audio(
        audio_bytes=audio_bytes,
        filename=audio.filename or "audio.webm",
    )

    agent_result = run_agent(
        transcript,
        session_id=session_id,
    )

    response_text = agent_result["response"]
    speech_audio = synthesize_speech(response_text)

    return Response(
        content=speech_audio,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": "inline; filename=agent-response.mp3",
        },
    )


@app.post("/api/voice/conversation")
async def voice_conversation(
    audio: UploadFile = File(...),
    session_id: str = Form("default"),
):
    audio_bytes = await audio.read()

    transcript = transcribe_audio(
        audio_bytes=audio_bytes,
        filename=audio.filename or "audio.webm",
    )

    agent_result = run_agent(
        transcript,
        session_id=session_id,
    )

    return {
        "transcript": transcript,
        "response": agent_result["response"],
        "tool_called": agent_result.get("tool_called"),
        "tool_result": agent_result.get("tool_result"),
    }


@app.get("/api/realtime/token")
def create_realtime_token():
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return {
            "success": False,
            "error": "OPENAI_API_KEY is missing",
        }

    response = requests.post(
        "https://api.openai.com/v1/realtime/client_secrets",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "session": {
                "type": "realtime",
                "model": "gpt-realtime",
                "instructions": """
You are an English-speaking AI voice assistant for a business.

LANGUAGE RULES:
- The default conversation language is English.
- Always respond in English.
- Do not switch languages because of a single foreign word,
  uncertain transcription, accent, name, or speech-recognition error.
- If the transcription appears to contain a foreign-language word
  but the conversation is otherwise in English, continue in English.
- Only switch to another language if the customer explicitly asks
  to continue in that language.
- If speech is unclear or the language is uncertain, ask the
  customer in English to repeat what they said.

Speak clearly, naturally, professionally, and concisely.

You can capture customer leads and schedule appointments.

Remember information the customer gives you during this conversation.
Never invent customer information.


CUSTOMER NAME RULES:

- A real customer name is required before creating a lead or
  scheduling an appointment.
- Never use "Unknown", "unknown", "Customer", "Guest", "Caller",
  or any other placeholder as the customer's name.
- Never invent or guess a customer's name.
- A missing name is NOT permission to create a placeholder.
- If the customer wants to schedule an appointment but has not
  provided their name, ask:
  "May I have your name for the appointment?"
- Remember the name once the customer provides it.


NAME CONFIRMATION RULES:

- A customer's name must be explicitly confirmed before booking.
- After the customer provides their name, repeat it and ask:
  "I heard your name as [name]. Is that correct?"
- Do not call create_lead_and_appointment yet.
- Wait for the customer's answer.
- If the customer says yes, correct, that's right, or equivalent,
  mark the name as confirmed.
- If the customer says the name is incorrect, ask them to repeat
  or spell their name.
- Replace the previously heard name with the corrected name.
- After receiving a corrected name, confirm it again.
- Never schedule an appointment using an unconfirmed name.
- A correction to the customer's name does not mean the customer
  wants another appointment.
STRICT NAME CONFIRMATION:

- Providing a name is NOT the same as confirming a name.
- Immediately after the customer provides a name for the first time,
  your NEXT response MUST be:
  "I heard your name as [name]. Is that correct?"
- Do not ask about or confirm the appointment in that same response.
- Do not call any lead or appointment tool yet.
- Wait for the customer's next response.
- Only an affirmative response to the name-confirmation question
  marks the name as confirmed.
- After the name is confirmed, continue with appointment confirmation
  if the appointment details have not already been confirmed.

APPOINTMENT CONFIRMATION RULES:

- Before scheduling an appointment, confirm the exact appointment
  date and time with the customer.
- If the date and time have not been explicitly confirmed,
  do NOT call create_lead_and_appointment.

Say:
"Just to confirm, you'd like your appointment for [date]
at [time]. Is that correct?"

- Remember whether the appointment date and time have been confirmed.
- Confirmation of the appointment date/time does NOT confirm the
  customer's name.
- Confirmation of the customer's name does NOT confirm the
  appointment date/time.


BOOKING REQUIREMENTS:

Before calling create_lead_and_appointment, ALL of the following
must be true:

1. The customer provided a real name.
2. The customer explicitly confirmed that name.
3. The customer provided an appointment date.
4. The customer provided an appointment time.
5. The customer explicitly confirmed the appointment date and time.

If ANY requirement is missing, DO NOT call
create_lead_and_appointment.

If the date/time are confirmed but the customer's name is missing,
ask:
"May I have your name for the appointment?"

If a name exists but has not been confirmed, ask:
"I heard your name as [name]. Is that correct?"

Never generate "Unknown" or another placeholder just to satisfy
the tool's required name argument.

Only after BOTH the customer's real name AND appointment date/time
have been explicitly confirmed may you call
create_lead_and_appointment.

CONFIRMATION TOOL RULES:

- After asking "I heard your name as [name]. Is that correct?",
  wait for the customer's answer.

- If the customer explicitly confirms the name, call
  confirm_customer_name with that exact confirmed name.

- Do not call confirm_customer_name merely because the customer
  originally provided their name.

- After asking the customer to confirm the appointment date and
  time, wait for the customer's answer.

- If the customer explicitly confirms the appointment details,
  call confirm_appointment with the confirmed date and time.

- Name confirmation and appointment confirmation are two separate
  actions.

- confirm_customer_name does NOT confirm the appointment.

- confirm_appointment does NOT confirm the customer's name.

- Only after BOTH confirmation tools have completed successfully
  may you call create_lead_and_appointment.
DATE CONSISTENCY RULES:

- Convert appointment dates to YYYY-MM-DD before calling the tool.
- Treat the exact date and year most recently stated by the customer
  as authoritative.
- Never change, substitute, or guess the year.
- When repeating a date for confirmation, repeat the same month,
  day, and year the customer gave.
- If the customer corrects only the date or year, keep the other
  previously provided appointment details unless they change them.
- Before calling create_lead_and_appointment, verify that the
  appointment_date argument exactly matches the date most recently
  confirmed by the customer.
- If a booking tool rejects a date as being in the past, do not
  invent another date. Tell the customer which date was rejected
  and ask for a future date.


IMPORTANT TOOL RULES:

Do NOT call create_lead_and_appointment merely because the customer
said "yes."

Interpret "yes" according to the question immediately preceding it.

For example:

If you asked:
"Is July 3, 2028 at 3 PM correct?"

and the customer says:
"Yes."

That confirms ONLY the appointment date and time.

It does NOT confirm a missing customer name.

If the customer's name is still missing, your next response MUST be:
"May I have your name for the appointment?"

If you asked:
"I heard your name as Dapo. Is that correct?"

and the customer says:
"Yes."

That confirms the name.

Once the name AND appointment date/time have both been explicitly
confirmed, call create_lead_and_appointment.

After all required information is confirmed:

1. Call create_lead_and_appointment.
2. Wait for the function result.
3. Then tell the customer the result.

Never tell the customer an appointment was scheduled unless
create_lead_and_appointment was actually called and returned
successfully.

If the function fails, tell the customer that the appointment
could not be completed.

If the tool reports that the appointment slot is already booked,
tell the customer and ask for another date or time.

Do not call create_lead_and_appointment again merely because the
customer corrects their name after a booking attempt.
""",
              "tools": [
    {
        "type": "function",
        "name": "create_lead",
        "description": (
            "Create a customer lead after the customer "
            "provides their information and expresses interest."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                },
                "phone": {
                    "type": "string",
                },
                "email": {
                    "type": "string",
                },
                "interest": {
                    "type": "string",
                },
            },
            "required": [
                "name",
                "interest",
            ],
        },
    },

    # ------------------------------------------
    # CONFIRM CUSTOMER NAME
    # ------------------------------------------
    {
        "type": "function",
        "name": "confirm_customer_name",
        "description": (
            "Record that the customer explicitly confirmed "
            "their name after the assistant repeated the "
            "recognized name back to them. Do not call this "
            "when the customer merely provides their name."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": (
                        "The exact customer name that the "
                        "customer explicitly confirmed."
                    ),
                },
            },
            "required": [
                "name",
            ],
        },
    },

    # ------------------------------------------
    # CONFIRM APPOINTMENT
    # ------------------------------------------
    {
        "type": "function",
        "name": "confirm_appointment",
        "description": (
            "Record that the customer explicitly confirmed "
            "the appointment date and time after the "
            "assistant repeated those details back."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "appointment_date": {
                    "type": "string",
                    "description": (
                        "The explicitly confirmed appointment "
                        "date in YYYY-MM-DD format."
                    ),
                },
                "appointment_time": {
                    "type": "string",
                    "description": (
                        "The explicitly confirmed appointment time."
                    ),
                },
            },
            "required": [
                "appointment_date",
                "appointment_time",
            ],
        },
    },

    # ------------------------------------------
    # CREATE LEAD + APPOINTMENT
    # ------------------------------------------
    {
        "type": "function",
        "name": "create_lead_and_appointment",
        "description": (
            "Create a customer lead and schedule an "
            "appointment ONLY after confirm_customer_name "
            "and confirm_appointment have both completed "
            "successfully for the current conversation."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": (
                        "The customer's real and explicitly "
                        "confirmed name. Never use Unknown "
                        "or another placeholder."
                    ),
                },
                "phone": {
                    "type": "string",
                },
                "email": {
                    "type": "string",
                },
                "interest": {
                    "type": "string",
                },
                "appointment_date": {
                    "type": "string",
                    "description": (
                        "Confirmed appointment date "
                        "in YYYY-MM-DD format."
                    ),
                },
                "appointment_time": {
                    "type": "string",
                    "description": (
                        "Confirmed appointment time."
                    ),
                },
            },
            "required": [
                "name",
                "interest",
                "appointment_date",
                "appointment_time",
            ],
        },
    },
],
                "tool_choice": "auto",
                "audio": {
                    "input": {
                        "transcription": {
                            "model": "gpt-4o-transcribe",
                            "language": "en",
                        },
                    },
                    "output": {
                        "voice": "marin",
                    },
                },
            },
        },
        timeout=30,
    )

    if not response.ok:
        return {
            "success": False,
            "status_code": response.status_code,
            "error": response.text,
        }

    return response.json()


@app.websocket("/ws/voice")
async def voice_websocket(
    websocket: WebSocket,
):
    await websocket.accept()

    print("Voice WebSocket connected")

    try:
        await websocket.send_json(
            {
                "type": "connection",
                "status": "connected",
                "message": "Voice WebSocket connected",
            }
        )

        while True:
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                print("Voice WebSocket disconnected")
                break

            audio_chunk = message.get("bytes")

            if audio_chunk:
                print(
                    f"Received audio chunk: "
                    f"{len(audio_chunk)} bytes"
                )

    except WebSocketDisconnect:
        print("Voice WebSocket disconnected")


@app.post("/api/realtime/tool")
def execute_realtime_tool(
    request: RealtimeToolRequest
):
    if request.name == "create_lead":
        result = create_lead(
            name=request.arguments["name"],
            phone=request.arguments.get("phone"),
            email=request.arguments.get("email"),
            interest=request.arguments.get("interest"),
        )

        return {
            "success": True,
            "result": result
        }

    if request.name == "create_lead_and_appointment":

        customer_name = str(
            request.arguments.get("name", "")
        ).strip()

        invalid_names = {
            "",
            "unknown",
            "customer",
            "guest",
            "caller",
        }

        # Hard guard #1:
        # Never allow placeholder/missing customer names.
        if customer_name.lower() in invalid_names:
            return {
                "success": False,
                "result": {
                    "success": False,
                    "error": "name_required",
                    "message":
                        "A real customer name is required before booking."
                }
            }

        # Hard guard #2:
        # Customer must explicitly confirm the recognized name.
        if not request.name_confirmed:
            return {
                "success": False,
                "result": {
                    "success": False,
                    "error": "name_not_confirmed",
                    "message":
                        "The customer's name must be explicitly confirmed before booking."
                }
            }

        # Hard guard #3:
        # Customer must separately confirm the appointment.
        if not request.appointment_confirmed:
            return {
                "success": False,
                "result": {
                    "success": False,
                    "error": "appointment_not_confirmed",
                    "message":
                        "The appointment date and time must be explicitly confirmed before booking."
                }
            }

        result = create_lead_and_appointment(
            name=customer_name,
            phone=request.arguments.get("phone"),
            email=request.arguments.get("email"),
            interest=request.arguments.get("interest"),
            appointment_date=request.arguments[
                "appointment_date"
            ],
            appointment_time=request.arguments[
                "appointment_time"
            ],
        )

        return {
            "success": True,
            "result": result
        }

    return {
        "success": False,
        "error": f"Unknown tool: {request.name}"
    }

@app.post("/api/twilio/voice")
async def twilio_voice(request: Request):
    form = await request.form()

    called_number = form.get("To", "")

    print(f"TWILIO CALLED NUMBER: {called_number}")

    twiml = f"""
    <?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Connect>
            <Stream url="wss://api.tanimosoftware.com/ws/twilio-media">
                <Parameter
                    name="called_number"
                    value="{called_number}"
                />
            </Stream>
        </Connect>
    </Response>
    """

    return Response(
        content=twiml.strip(),
        media_type="application/xml",
    )


@app.websocket("/ws/twilio-media")

async def twilio_media_stream(websocket: WebSocket):
    
    """Bridge Twilio PCMU audio directly to OpenAI Realtime and back."""
    business = get_business(DEFAULT_BUSINESS_ID)

    if not business:
        print(
            f"BUSINESS NOT FOUND: {DEFAULT_BUSINESS_ID}"
        )
        await websocket.close()
        return

    print(
        f"ACTIVE BUSINESS: {business['name']}"
    )
    await websocket.accept()
    print("TWILIO MEDIA STREAM CONNECTED")

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        print("OPENAI_API_KEY is missing")
        await websocket.close(code=1011)
        return

    stream_sid = None

    realtime_url = (
        "wss://api.openai.com/v1/realtime?model=gpt-realtime"
    )

    try:
        async with websockets.connect(
            realtime_url,
            additional_headers={
                "Authorization": f"Bearer {api_key}"
            },
            max_size=None,
        ) as openai_ws:

            print("OPENAI REALTIME WEBSOCKET CONNECTED")

            await openai_ws.send(
                json.dumps(
                    {
                        "type": "session.update",
                        "session": {
                            "type": "realtime",
                            "model": "gpt-realtime",
                            "instructions": """
You are an English-speaking AI voice assistant for a business.

LANGUAGE RULES:
- The default conversation language is English.
- Always respond in English.
- Do not switch languages because of a single foreign word,
  uncertain transcription, accent, name, or speech-recognition error.
- If the transcription appears to contain a foreign-language word
  but the conversation is otherwise in English, continue in English.
- Only switch to another language if the customer explicitly asks
  to continue in that language.
- If speech is unclear or the language is uncertain, ask the
  customer in English to repeat what they said.

Speak clearly, naturally, professionally, and concisely.

You can capture customer leads and schedule appointments.
Remember information the customer gives you during this call.
Never invent customer information.


CUSTOMER NAME RULES:

- A real customer name is required before creating a lead or
  scheduling an appointment.
- Never use "Unknown", "unknown", "Customer", "Guest", "Caller",
  or any placeholder as the customer's name.
- Never invent or guess the customer's name.
- If the customer wants an appointment and has not provided their
  name, ask:
  "May I have your name for the appointment?"


NAME CONFIRMATION RULES:

- After the customer provides their name, repeat the name and ask:
  "I heard your name as [name]. Is that correct?"
- Do NOT book yet.
- Wait for explicit confirmation of the name.
- If the name is wrong, ask the customer to repeat or spell it.
- Replace the incorrect name with the corrected name.
- Confirm the corrected name again.
- Never book using an unconfirmed name.

STRICT NAME CONFIRMATION:

- Providing a name is NOT the same as confirming a name.
- Immediately after the customer provides a name for the first time,
  your NEXT response MUST be:
  "I heard your name as [name]. Is that correct?"
- Do not ask about or confirm the appointment in that same response.
- Do not call any lead or appointment tool yet.
- Wait for the customer's next response.
- Only an affirmative response to the name-confirmation question
  marks the name as confirmed.
- After the name is confirmed, continue with appointment confirmation
  if the appointment details have not already been confirmed.
BOOKING REQUIREMENTS:

Before calling create_lead_and_appointment, ALL of these must
be true:

1. A real customer name was provided.
2. The customer explicitly confirmed the name.
3. An appointment date was provided.
4. An appointment time was provided.
5. The customer explicitly confirmed the appointment date and time.

If ANY requirement is missing, do NOT call the booking tool.

A "yes" only confirms the question immediately preceding it.

If the customer confirms the date/time but their name is missing,
ask:
"May I have your name for the appointment?"

If the customer's name has not been confirmed, ask:
"I heard your name as [name]. Is that correct?"

Only after BOTH the name and appointment details are confirmed
may you call create_lead_and_appointment.

CONFIRMATION TOOL RULES:

- After asking "I heard your name as [name]. Is that correct?",
  wait for the customer's answer.

- If the customer explicitly confirms the name, call
  confirm_customer_name with that exact confirmed name.

- Do not call confirm_customer_name merely because the customer
  originally provided their name.

- After asking the customer to confirm the appointment date and
  time, wait for the customer's answer.

- If the customer explicitly confirms the appointment details,
  call confirm_appointment with the confirmed date and time.

- Name confirmation and appointment confirmation are two separate
  actions.

- confirm_customer_name does NOT confirm the appointment.

- confirm_appointment does NOT confirm the customer's name.

- Only after BOTH confirmation tools have completed successfully
  may you call create_lead_and_appointment.
DATE CONSISTENCY RULES:

- Convert appointment dates to YYYY-MM-DD before calling the tool.
- Treat the exact date and year most recently stated by the customer
  as authoritative.
- Never change, substitute, or guess the year.
- Repeat the same month, day, and year during confirmation.
- If the customer corrects the date or year, use the corrected value.

CANCELLATION RULES:

- If the customer wants to cancel an appointment, ask for their
  real name if it has not already been provided.

- Ask for the date of the appointment they want to cancel.

- Never guess or invent the appointment date.

- Before cancelling, repeat the appointment information and ask:
  "Just to confirm, you'd like to cancel your appointment on
  [date]. Is that correct?"

- Do NOT call cancel_appointment yet.

- Wait for the customer's answer.

- Only if the customer explicitly says yes, correct, that's right,
  or equivalent may you call cancel_appointment.

- If the customer says no, do NOT cancel the appointment.

- Call cancel_appointment using the customer's real name and the
  confirmed appointment date.

- Wait for the cancel_appointment tool result before telling the
  customer that the appointment was cancelled.

- Never claim an appointment was cancelled unless
  cancel_appointment returned success.

- If no matching scheduled appointment is found, tell the customer
  that no scheduled appointment was found for that name and date.

- Cancellation does NOT create a new lead or appointment.

RESCHEDULING RULES:

- If the customer wants to reschedule an appointment, ask for their
  real name if it has not already been provided.

- Ask for the date of their current appointment.

- Ask for the new appointment date and time they want.

- Never guess or invent the current date, new date, or new time.

- Before rescheduling, repeat the change and ask:
  "Just to confirm, you'd like to move your appointment from
  [current date] to [new date] at [new time]. Is that correct?"

- Do NOT call reschedule_appointment yet.

- Wait for the customer's answer.

- Only if the customer explicitly says yes, correct, that's right,
  or equivalent may you call reschedule_appointment.

- If the customer says no, do NOT reschedule the appointment.

- Call reschedule_appointment using the customer's real name,
  current appointment date, new appointment date, and new
  appointment time.

- Wait for the reschedule_appointment tool result before telling
  the customer that the appointment was rescheduled.

- Never claim an appointment was rescheduled unless
  reschedule_appointment returned success.

- If no matching scheduled appointment is found, tell the customer
  and ask them to verify their name and current appointment date.

- If the new appointment slot is already booked, tell the customer
  and ask for another date or time.

- Rescheduling does NOT create a new lead or appointment.
BUSINESS KNOWLEDGE RULES:

- When the customer asks a question about the business, use
  search_business_knowledge before answering.

- Business questions include services, pricing, business hours,
  policies, capabilities, appointment policies, and frequently
  asked questions.

- Do not guess or invent business information.

- Use the information returned by search_business_knowledge
  to answer the customer naturally and briefly.

- If search_business_knowledge returns found=false, tell the
  customer that you do not have that information available.

- Do not use search_business_knowledge for normal appointment
  booking, cancellation, or rescheduling unless the customer
  is asking a business-information question.
IMPORTANT TOOL RULES:

Do not call create_lead_and_appointment merely because the
customer says "yes."

Never create or use "Unknown" to satisfy the required name field.

After all required information is confirmed:

1. Call create_lead_and_appointment.
2. Wait for the function result.
3. Tell the customer the actual result.

Never claim an appointment was scheduled unless the tool returned
successfully.

If the tool fails, explain that the appointment was not completed.

If the slot is already booked, ask the customer for another
date or time.
""",
                            "audio": {
                                "input": {
                                    "format": {
                                        "type": "audio/pcmu",
                                    },
                                    "transcription": {
                                        "model": "gpt-4o-transcribe",
                                        "language": "en",
                                    },
                                    "turn_detection": {
                                            "type": "server_vad",
                                            "threshold": 0.5,
                                            "prefix_padding_ms": 300,
                                            "silence_duration_ms": 1200,
                                            "create_response": True,
                                            "interrupt_response": True,
                                        },
                                },
                                "output": {
                                    "format": {
                                        "type": "audio/pcmu",
                                    },
                                    "voice": "marin",
                                },
                            },
                            "tools": [
                                {
                                    "type": "function",
                                    "name": "create_lead",
                                    "description": (
                                        "Create a customer lead after the "
                                        "customer provides their information "
                                        "and expresses interest."
                                    ),
                                    "parameters": {
                                        "type": "object",
                                        "properties": {
                                            "name": {
                                                "type": "string",
                                            },
                                            "phone": {
                                                "type": "string",
                                            },
                                            "email": {
                                                "type": "string",
                                            },
                                            "interest": {
                                                "type": "string",
                                            },
                                        },
                                        "required": [
                                            "name",
                                            "interest",
                                        ],
                                    },
                                },
                                                                {
                                    "type": "function",
                                    "name": "confirm_customer_name",
                                    "description": (
                                        "Record the customer's explicitly "
                                        "confirmed real name."
                                    ),
                                    "parameters": {
                                        "type": "object",
                                        "properties": {
                                            "name": {
                                                "type": "string",
                                                "description": (
                                                    "The customer's confirmed "
                                                    "real name."
                                                ),
                                            },
                                        },
                                        "required": ["name"],
                                    },
                                },
                                {
                                    "type": "function",
                                    "name": "confirm_appointment",
                                    "description": (
                                        "Record the appointment date and time "
                                        "after the customer explicitly "
                                        "confirms them."
                                    ),
                                    "parameters": {
                                        "type": "object",
                                        "properties": {
                                            "appointment_date": {
                                                "type": "string",
                                                "description": (
                                                    "Confirmed appointment "
                                                    "date in YYYY-MM-DD format."
                                                ),
                                            },
                                            "appointment_time": {
                                                "type": "string",
                                                "description": (
                                                    "Confirmed appointment "
                                                    "time in HH:MM 24-hour "
                                                    "format."
                                                ),
                                            },
                                        },
                                        "required": [
                                            "appointment_date",
                                            "appointment_time",
                                        ],
                                    },
                                },
                                                                {
                                    "type": "function",
                                    "name": "cancel_appointment",
                                    "description": (
                                        "Cancel an existing scheduled appointment "
                                        "only after the customer identifies the "
                                        "appointment and explicitly confirms "
                                        "that they want to cancel it."
                                    ),
                                    "parameters": {
                                        "type": "object",
                                        "properties": {
                                            "customer_name": {
                                                "type": "string",
                                                "description": (
                                                    "The customer's real name "
                                                    "associated with the appointment."
                                                ),
                                            },
                                            "appointment_date": {
                                                "type": "string",
                                                "description": (
                                                    "The appointment date to cancel "
                                                    "in YYYY-MM-DD format."
                                                ),
                                            },
                                        },
                                        "required": [
                                            "customer_name",
                                            "appointment_date",
                                        ],
                                    },
                                },
                                                                {
                                    "type": "function",
                                    "name": "reschedule_appointment",
                                    "description": (
                                        "Reschedule an existing scheduled "
                                        "appointment only after the customer "
                                        "explicitly confirms the new "
                                        "appointment date and time."
                                    ),
                                    "parameters": {
                                        "type": "object",
                                        "properties": {
                                            "customer_name": {
                                                "type": "string",
                                            },
                                            "current_appointment_date": {
                                                "type": "string",
                                                "description": (
                                                    "Existing appointment date "
                                                    "in YYYY-MM-DD format."
                                                ),
                                            },
                                            "new_appointment_date": {
                                                "type": "string",
                                                "description": (
                                                    "New appointment date in "
                                                    "YYYY-MM-DD format."
                                                ),
                                            },
                                            "new_appointment_time": {
                                                "type": "string",
                                                "description": (
                                                    "New appointment time in "
                                                    "HH:MM 24-hour format."
                                                ),
                                            },
                                        },
                                        "required": [
                                            "customer_name",
                                            "current_appointment_date",
                                            "new_appointment_date",
                                            "new_appointment_time",
                                        ],
                                    },
                                },
                                {
                                    "type": "function",
                                    "name": "search_business_knowledge",
                                    "description": (
                                        "Search the business knowledge base to answer "
                                        "questions about the business, including services, "
                                        "pricing, business hours, policies, capabilities, "
                                        "and frequently asked questions. Use this tool "
                                        "instead of guessing business information."
                                    ),
                                    "parameters": {
                                        "type": "object",
                                        "properties": {
                                            "query": {
                                                "type": "string",
                                                "description": (
                                                    "The customer's question or the business "
                                                    "information that needs to be retrieved."
                                                ),
                                            },
                                        },
                                        "required": [
                                            "query",
                                        ],
                                    },
                                },


                                {
                                    "type": "function",
                                    "name": (
                                        "create_lead_and_appointment"
                                    ),
                                    "description": (
                                        "Create a customer lead and schedule "
                                        "an appointment only after a real "
                                        "customer name and appointment "
                                        "date/time have all been explicitly "
                                        "confirmed. Never use Unknown."
                                    ),
                                    "parameters": {
                                        "type": "object",
                                        "properties": {
                                            "name": {
                                                "type": "string",
                                                "description": (
                                                    "The customer's real "
                                                    "confirmed name. Never "
                                                    "use Unknown."
                                                ),
                                            },
                                            "phone": {
                                                "type": "string",
                                            },
                                            "email": {
                                                "type": "string",
                                            },
                                            "interest": {
                                                "type": "string",
                                            },
                                            "appointment_date": {
                                                "type": "string",
                                                "description": (
                                                    "Confirmed appointment "
                                                    "date in YYYY-MM-DD format"
                                                ),
                                            },
                                            "appointment_time": {
                                                "type": "string",
                                            },
                                        },
                                        "required": [
                                            "name",
                                            "interest",
                                            "appointment_date",
                                            "appointment_time",
                                        ],
                                    },
                                },
                            ],
                            "tool_choice": "auto",
                        },
                    }
                )
            )

            async def twilio_to_openai():
                nonlocal stream_sid

                try:
                    while True:
                        data = json.loads(
                            await websocket.receive_text()
                        )

                        event_type = data.get("event")

                        if event_type == "connected":
                            print("Twilio WebSocket connected")

                        elif event_type == "start":
                            stream_sid = data.get(
                                "start", {}
                            ).get("streamSid")

                            print(
                                "TWILIO STREAM STARTED:",
                                stream_sid,
                            )

                        elif event_type == "media":
                            payload = data.get(
                                "media", {}
                            ).get("payload")

                            if payload:
                                await openai_ws.send(
                                    json.dumps(
                                        {
                                            "type": (
                                                "input_audio_buffer.append"
                                            ),
                                            "audio": payload,
                                        }
                                    )
                                )

                        elif event_type == "stop":
                            print("TWILIO STREAM STOPPED")
                            return

                except WebSocketDisconnect:
                    print(
                        "TWILIO MEDIA STREAM DISCONNECTED"
                    )

            async def openai_to_twilio():
                nonlocal stream_sid

                async for raw_message in openai_ws:
                    event = json.loads(raw_message)
                    event_type = event.get("type")

                    if event_type == "session.updated":
                        print(
                            "OPENAI REALTIME SESSION CONFIGURED"
                        )

                        # Make the AI greet the caller immediately.
                        await openai_ws.send(
                            json.dumps(
                                {
                                    "type": "response.create",
                                    "response": {
                                        "instructions": (
                                            "Greet the caller now. "
                                            "Say: Hello, thank you for calling. "
                                            "How can I help you today?"
                                        )
                                    },
                                }
                            )
                        )

                    elif (
                        event_type
                        == "conversation.item."
                        "input_audio_transcription.completed"
                    ):
                        transcript = event.get(
                            "transcript",
                            "",
                        ).strip()

                        if transcript:
                            print(
                                "CALLER:",
                                transcript,
                            )

                    elif (
                        event_type
                        == "response.output_audio_transcript.done"
                    ):
                        transcript = event.get(
                            "transcript",
                            "",
                        ).strip()

                        if transcript:
                            print(
                                "AI:",
                                transcript,
                            )

                    elif (
                        event_type
                        == "response.output_audio.delta"
                    ):
                        audio_delta = event.get("delta")

                        if audio_delta and stream_sid:
                            await websocket.send_text(
                                json.dumps(
                                    {
                                        "event": "media",
                                        "streamSid": stream_sid,
                                        "media": {
                                            "payload": audio_delta
                                        },
                                    }
                                )
                            )

                    elif (
                        event_type
                        == "input_audio_buffer.speech_started"
                    ):
                        if stream_sid:
                            await websocket.send_text(
                                json.dumps(
                                    {
                                        "event": "clear",
                                        "streamSid": stream_sid,
                                    }
                                )
                            )

                    elif (
                        event_type
                        == "response.function_call_arguments.done"
                    ):
                        tool_name = event.get("name")
                        call_id = event.get("call_id")

                        try:
                            arguments = json.loads(
                                event.get("arguments") or "{}"
                            )

                            if tool_name == "create_lead":
                                tool_result = create_lead(
                                    name=arguments["name"],
                                    phone=arguments.get("phone"),
                                    email=arguments.get("email"),
                                    interest=arguments.get(
                                        "interest"
                                    ),
                                )


                            elif tool_name == "confirm_customer_name":
                                    confirmed_name = str(
                                        arguments.get("name", "")
                                    ).strip()

                                    tool_result = {
                                        "success": True,
                                        "name_confirmed": True,
                                        "name": confirmed_name,
                                        "message": (
                                            f"Customer explicitly confirmed the name "
                                            f"{confirmed_name}."
                                        ),
                                    }

                            elif tool_name == "confirm_appointment":
                                    confirmed_date = arguments.get(
                                        "appointment_date"
                                    )
                                    confirmed_time = arguments.get(
                                        "appointment_time"
                                    )

                                    tool_result = {
                                        "success": True,
                                        "appointment_confirmed": True,
                                        "appointment_date": confirmed_date,
                                        "appointment_time": confirmed_time,
                                        "message": (
                                            "Customer explicitly confirmed the "
                                            "appointment date and time."
                                        ),
                                    }
                            elif tool_name == "cancel_appointment":
                                    tool_result = cancel_appointment(
                                        customer_name=arguments[
                                            "customer_name"
                                        ],
                                        appointment_date=arguments[
                                            "appointment_date"
                                        ],
                                    )
                            elif tool_name == "reschedule_appointment":
                                tool_result = reschedule_appointment(
                                    customer_name=arguments[
                                        "customer_name"
                                    ],
                                    current_appointment_date=arguments[
                                        "current_appointment_date"
                                    ],
                                    new_appointment_date=arguments[
                                        "new_appointment_date"
                                    ],
                                    new_appointment_time=arguments[
                                        "new_appointment_time"
                                    ],
                                )
                            elif tool_name == "search_business_knowledge":
                                    tool_result = search_business_knowledge(
                                        query=arguments["query"],
                                        knowledge_file=business["knowledge_file"],
                                    )
                            elif (
                                tool_name
                                == "create_lead_and_appointment"
                            ):
                                tool_result = (
                                    create_lead_and_appointment(
                                        name=arguments["name"],
                                        phone=arguments.get(
                                            "phone"
                                        ),
                                        email=arguments.get(
                                            "email"
                                        ),
                                        interest=arguments.get(
                                            "interest"
                                        ),
                                        appointment_date=arguments[
                                            "appointment_date"
                                        ],
                                        appointment_time=arguments[
                                            "appointment_time"
                                        ],
                                    )
                                )

                            else:
                                tool_result = {
                                    "success": False,
                                    "error": (
                                        f"Unknown tool: {tool_name}"
                                    ),
                                }

                        except Exception as tool_error:
                            print(
                                "TWILIO TOOL ERROR:",
                                tool_error,
                            )

                            tool_result = {
                                "success": False,
                                "error": str(tool_error),
                            }

                        print(
                            "TWILIO REALTIME TOOL RESULT:",
                            tool_result,
                        )

                        await openai_ws.send(
                            json.dumps(
                                {
                                    "type": (
                                        "conversation.item.create"
                                    ),
                                    "item": {
                                        "type": (
                                            "function_call_output"
                                        ),
                                        "call_id": call_id,
                                        "output": json.dumps(
                                            tool_result
                                        ),
                                    },
                                }
                            )
                        )

                        await openai_ws.send(
                            json.dumps(
                                {
                                    "type": "response.create",
                                }
                            )
                        )

                    elif event_type == "error":
                        print(
                            "OPENAI REALTIME ERROR:",
                            json.dumps(
                                event.get(
                                    "error",
                                    event,
                                )
                            ),
                        )

            twilio_task = asyncio.create_task(
                twilio_to_openai()
            )

            openai_task = asyncio.create_task(
                openai_to_twilio()
            )

            done, pending = await asyncio.wait(
                {
                    twilio_task,
                    openai_task,
                },
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

            await asyncio.gather(
                *pending,
                return_exceptions=True,
            )

            for task in done:
                exception = task.exception()

                if exception:
                    raise exception

    except WebSocketDisconnect:
        print(
            "TWILIO MEDIA STREAM DISCONNECTED"
        )

    except Exception as error:
        print(
            "TWILIO/OPENAI REALTIME BRIDGE ERROR:",
            repr(error),
        )

        try:
            await websocket.close(
                code=1011,
            )

        except Exception:
            pass
