from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    WebSocket,
    WebSocketDisconnect,
)
import websockets
import os
import json
import requests
import asyncio
from fastapi.responses import Response
from pydantic import BaseModel
from backend.agent import run_agent
from backend.database import initialize_database
from backend.tools.leads import create_lead
from backend.tools.appointments import create_appointment
from backend.tools.booking import create_lead_and_appointment
from backend.voice import transcribe_audio, synthesize_speech
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(
    title="Overcy Voice Agent Demo",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
initialize_database()

class RealtimeToolRequest(BaseModel):
    name: str
    arguments: dict
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
        "service": "AI Voice Agent"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.post("/api/leads")
def add_lead(lead: LeadRequest):

    return create_lead(
        name=lead.name,
        phone=lead.phone,
        email=lead.email,
        interest=lead.interest
    )


@app.post("/api/appointments")
def add_appointment(appointment: AppointmentRequest):

    return create_appointment(
        lead_id=appointment.lead_id,
        appointment_date=appointment.appointment_date,
        appointment_time=appointment.appointment_time
    )

@app.post("/api/agent")
def agent_chat(request: ChatRequest):
    return run_agent(request.message)

@app.post("/api/voice/transcribe")
async def voice_transcribe(
    audio: UploadFile = File(...)
):
    audio_bytes = await audio.read()

    transcript = transcribe_audio(
        audio_bytes=audio_bytes,
        filename=audio.filename or "audio.webm"
    )

    return {
        "transcript": transcript
    }
@app.post("/api/tts")
def text_to_speech(request: TTSRequest):
    speech_audio = synthesize_speech(
        request.text
    )

    return Response(
        content=speech_audio,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition":
                "inline; filename=agent-response.mp3"
        }
    )
@app.post("/api/voice/speak")
async def voice_speak(
    audio: UploadFile = File(...),
    session_id: str = Form("default")
):
    audio_bytes = await audio.read()

    transcript = transcribe_audio(
        audio_bytes=audio_bytes,
        filename=audio.filename or "audio.webm"
    )

    agent_result = run_agent(
        transcript,
        session_id=session_id
    )

    response_text = agent_result["response"]

    speech_audio = synthesize_speech(response_text)

    return Response(
        content=speech_audio,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition":
                "inline; filename=agent-response.mp3"
        }
    )
@app.post("/api/voice/conversation")
async def voice_conversation(
    audio: UploadFile = File(...),
    session_id: str = Form("default")
):
    audio_bytes = await audio.read()

    transcript = transcribe_audio(
        audio_bytes=audio_bytes,
        filename=audio.filename or "audio.webm"
    )

    agent_result = run_agent(
        transcript,
        session_id=session_id
    )

    return {
        "transcript": transcript,
        "response": agent_result["response"],
        "tool_called": agent_result.get("tool_called"),
        "tool_result": agent_result.get("tool_result")
    }

@app.post("/api/voice/speak")
async def voice_speak(
    audio: UploadFile = File(...)
):
    audio_bytes = await audio.read()

    transcript = transcribe_audio(
        audio_bytes=audio_bytes,
        filename=audio.filename or "audio.webm"
    )

    agent_result = run_agent(transcript)

    response_text = agent_result["response"]

    speech_audio = synthesize_speech(response_text)

    return Response(
        content=speech_audio,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": "inline; filename=agent-response.mp3"
        }
    )
@app.post("/api/voice/conversation")
async def voice_conversation(
    audio: UploadFile = File(...),
    session_id: str = Form("default")
):
    audio_bytes = await audio.read()

    transcript = transcribe_audio(
        audio_bytes=audio_bytes,
        filename=audio.filename or "audio.webm"
    )

    agent_result = run_agent(
        transcript,
        session_id=session_id
    )

    return {
        "transcript": transcript,
        "response": agent_result["response"],
        "tool_called": agent_result.get("tool_called"),
        "tool_result": agent_result.get("tool_result")
    }
@app.get("/api/realtime/token")
def create_realtime_token():
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return {
            "success": False,
            "error": "OPENAI_API_KEY is missing"
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

                Always speak in English.
                Speak clearly, naturally, professionally, and concisely.

                You can capture customer leads and schedule appointments.

                Remember information the customer gives you during this conversation.
                Never invent customer information.

                Before scheduling an appointment, you MUST confirm the exact
                appointment date and time with the customer.

                If the customer has not explicitly confirmed the date and time,
                do NOT call create_lead_and_appointment.

                Instead say:
                "Just to confirm, you'd like your appointment for [date]
                at [time]. Is that correct?"

                Only call create_lead_and_appointment after the customer explicitly
                confirms with yes, correct, that's right, or equivalent confirmation.

                Do not ask the customer to repeat information they already provided.

                Convert appointment dates to YYYY-MM-DD before calling the tool.

                DATE CONSISTENCY RULES:
                Treat the exact date and year most recently stated by the customer
                as authoritative. Never change, substitute, or guess the year.
                When repeating a date for confirmation, repeat the same month,
                day, and year the customer gave.
                If the customer corrects only the date or year, keep the other
                previously confirmed appointment details unless they change them.
                Before calling create_lead_and_appointment, verify that the
                appointment_date argument exactly matches the date the customer
                most recently confirmed.
                If a booking tool rejects a date as being in the past, do not
                invent a different past date in your response. State the rejected
                date from the tool result and ask for a future date.

                After a tool completes successfully, clearly tell the customer
                what was completed.

                If a tool reports that the customer or appointment already exists,
                tell the customer rather than pretending a new record was created.

                If speech is unclear, ask the customer in English to repeat it.
                IMPORTANT TOOL RULES:

When the customer explicitly confirms an appointment,
you MUST call the create_lead_and_appointment function.

Never tell the customer that an appointment was scheduled
unless create_lead_and_appointment was actually called
and returned successfully.

Do not respond with a verbal booking confirmation instead
of calling the function.

After explicit confirmation:
1. Call create_lead_and_appointment.
2. Wait for the function result.
3. Then tell the customer the result.

If the function fails, tell the customer that the
appointment could not be completed.
                """,
                "tools": [
    {
        "type": "function",
        "name": "create_lead",
        "description": "Create a customer lead after the customer provides their information and expresses interest.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string"
                },
                "phone": {
                    "type": "string"
                },
                "email": {
                    "type": "string"
                },
                "interest": {
                    "type": "string"
                }
            },
            "required": [
                "name",
                "interest"
            ]
        }
    },
    {
        "type": "function",
        "name": "create_lead_and_appointment",
        "description": "Create a customer lead and schedule an appointment after the customer explicitly confirms the appointment date and time.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string"
                },
                "phone": {
                    "type": "string"
                },
                "email": {
                    "type": "string"
                },
                "interest": {
                    "type": "string"
                },
                "appointment_date": {
                    "type": "string",
                    "description": "Appointment date in YYYY-MM-DD format"
                },
                "appointment_time": {
                    "type": "string"
                }
            },
            "required": [
                "name",
                "interest",
                "appointment_date",
                "appointment_time"
            ]
        }
    }
],
"tool_choice": "auto",
                "audio": {
                    "input": {
                        "transcription": {
                            "model": "gpt-4o-transcribe",
                            "language": "en"
                        }
                    },
                    "output": {
                        "voice": "marin"
                    }
                }
            }
        },
        timeout=30,
    )

    if not response.ok:
        return {
            "success": False,
            "status_code": response.status_code,
            "error": response.text
        }

    return response.json()
@app.websocket("/ws/voice")
async def voice_websocket(
    websocket: WebSocket
):
    await websocket.accept()

    print("Voice WebSocket connected")

    try:
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "message": "Voice WebSocket connected"
        })

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
        result = create_lead_and_appointment(
            name=request.arguments["name"],
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
async def twilio_voice():
    twiml = """
    <?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Connect>
            <Stream url="wss://cosmic-thread-cyclic.ngrok-free.dev/ws/twilio-media" />
        </Connect>
    </Response>
    """

    return Response(
        content=twiml.strip(),
        media_type="application/xml"
    )
@app.websocket("/ws/twilio-media")
async def twilio_media_stream(websocket: WebSocket):
    """Bridge Twilio PCMU audio directly to OpenAI Realtime and back."""
    await websocket.accept()
    print("TWILIO MEDIA STREAM CONNECTED")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is missing")
        await websocket.close(code=1011)
        return

    stream_sid = None
    realtime_url = "wss://api.openai.com/v1/realtime?model=gpt-realtime"

    try:
        async with websockets.connect(
            realtime_url,
            additional_headers={"Authorization": f"Bearer {api_key}"},
            max_size=None,
        ) as openai_ws:
            print("OPENAI REALTIME WEBSOCKET CONNECTED")

            await openai_ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "type": "realtime",
                    "model": "gpt-realtime",
                    "instructions": """
You are an English-speaking AI voice assistant for a business.
Speak clearly, naturally, professionally, and concisely.
You can capture customer leads and schedule appointments.
Remember information the customer gives you during this call.
Never invent customer information.
Before scheduling, MUST confirm the exact appointment date and time.
Treat the exact date and year most recently stated by the customer as authoritative.
Never change, substitute, or guess the year. Repeat the same month, day, and year.
Convert appointment dates to YYYY-MM-DD before calling the tool.
Only call create_lead_and_appointment after explicit confirmation such as yes or correct.
Never claim an appointment was scheduled unless the tool actually succeeded.
If the tool fails, explain that it was not completed and recover from the tool result.
Do not ask the caller to repeat information already provided.
""",
                    "audio": {
                        "input": {
                            "format": {"type": "audio/pcmu"},
                            "transcription": {"model": "gpt-4o-transcribe", "language": "en"},
                            "turn_detection": {
                                "type": "server_vad",
                                "create_response": True,
                                "interrupt_response": True
                            }
                        },
                        "output": {
                            "format": {"type": "audio/pcmu"},
                            "voice": "marin"
                        }
                    },
                    "tools": [
                        {
                            "type": "function",
                            "name": "create_lead",
                            "description": "Create a customer lead after the customer provides their information and expresses interest.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "phone": {"type": "string"},
                                    "email": {"type": "string"},
                                    "interest": {"type": "string"}
                                },
                                "required": ["name", "interest"]
                            }
                        },
                        {
                            "type": "function",
                            "name": "create_lead_and_appointment",
                            "description": "Create a customer lead and schedule an appointment after explicit date/time confirmation.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "phone": {"type": "string"},
                                    "email": {"type": "string"},
                                    "interest": {"type": "string"},
                                    "appointment_date": {"type": "string", "description": "Appointment date in YYYY-MM-DD format"},
                                    "appointment_time": {"type": "string"}
                                },
                                "required": ["name", "interest", "appointment_date", "appointment_time"]
                            }
                        }
                    ],
                    "tool_choice": "auto"
                }
            }))

            async def twilio_to_openai():
                nonlocal stream_sid
                try:
                    while True:
                        data = json.loads(await websocket.receive_text())
                        event_type = data.get("event")
                        if event_type == "connected":
                            print("Twilio WebSocket connected")
                        elif event_type == "start":
                            stream_sid = data.get("start", {}).get("streamSid")
                            print("TWILIO STREAM STARTED:", stream_sid)
                        elif event_type == "media":
                            payload = data.get("media", {}).get("payload")
                            if payload:
                                await openai_ws.send(json.dumps({
                                    "type": "input_audio_buffer.append",
                                    "audio": payload
                                }))
                        elif event_type == "stop":
                            print("TWILIO STREAM STOPPED")
                            return
                except WebSocketDisconnect:
                    print("TWILIO MEDIA STREAM DISCONNECTED")

            async def openai_to_twilio():
                nonlocal stream_sid
                async for raw_message in openai_ws:
                    event = json.loads(raw_message)
                    event_type = event.get("type")

                    if event_type == "session.updated":
                        print("OPENAI REALTIME SESSION CONFIGURED")
                    elif event_type == "conversation.item.input_audio_transcription.completed":
                        transcript = event.get("transcript", "").strip()
                        if transcript:
                            print("CALLER:", transcript)
                    elif event_type == "response.output_audio_transcript.done":
                        transcript = event.get("transcript", "").strip()
                        if transcript:
                            print("AI:", transcript)
                    elif event_type == "response.output_audio.delta":
                        audio_delta = event.get("delta")
                        if audio_delta and stream_sid:
                            await websocket.send_text(json.dumps({
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": {"payload": audio_delta}
                            }))
                    elif event_type == "input_audio_buffer.speech_started":
                        if stream_sid:
                            await websocket.send_text(json.dumps({
                                "event": "clear",
                                "streamSid": stream_sid
                            }))
                    elif event_type == "response.function_call_arguments.done":
                        tool_name = event.get("name")
                        call_id = event.get("call_id")
                        try:
                            arguments = json.loads(event.get("arguments") or "{}")
                            if tool_name == "create_lead":
                                tool_result = create_lead(
                                    name=arguments["name"],
                                    phone=arguments.get("phone"),
                                    email=arguments.get("email"),
                                    interest=arguments.get("interest"),
                                )
                            elif tool_name == "create_lead_and_appointment":
                                tool_result = create_lead_and_appointment(
                                    name=arguments["name"],
                                    phone=arguments.get("phone"),
                                    email=arguments.get("email"),
                                    interest=arguments.get("interest"),
                                    appointment_date=arguments["appointment_date"],
                                    appointment_time=arguments["appointment_time"],
                                )
                            else:
                                tool_result = {"success": False, "error": f"Unknown tool: {tool_name}"}
                        except Exception as tool_error:
                            print("TWILIO TOOL ERROR:", tool_error)
                            tool_result = {"success": False, "error": str(tool_error)}

                        print("TWILIO REALTIME TOOL RESULT:", tool_result)
                        await openai_ws.send(json.dumps({
                            "type": "conversation.item.create",
                            "item": {
                                "type": "function_call_output",
                                "call_id": call_id,
                                "output": json.dumps(tool_result)
                            }
                        }))
                        await openai_ws.send(json.dumps({"type": "response.create"}))
                    elif event_type == "error":
                        print("OPENAI REALTIME ERROR:", json.dumps(event.get("error", event)))

            twilio_task = asyncio.create_task(twilio_to_openai())
            openai_task = asyncio.create_task(openai_to_twilio())
            done, pending = await asyncio.wait(
                {twilio_task, openai_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for task in done:
                exception = task.exception()
                if exception:
                    raise exception

    except WebSocketDisconnect:
        print("TWILIO MEDIA STREAM DISCONNECTED")
    except Exception as error:
        print("TWILIO/OPENAI REALTIME BRIDGE ERROR:", repr(error))
        try:
            await websocket.close(code=1011)
        except Exception:
            pass

