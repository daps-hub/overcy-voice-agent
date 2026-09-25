\# 🎙️ Overcy AI Voice Agent



\*\*Overcy\*\* is a real-time AI voice agent that can answer phone calls, hold natural conversations with callers, capture leads, and schedule appointments automatically.



The V1 application integrates \*\*Twilio Programmable Voice\*\*, \*\*OpenAI Realtime\*\*, \*\*FastAPI\*\*, WebSockets, a database-backed lead/appointment workflow, and a \*\*Next.js\*\* frontend.



\---



\## 🚀 Overview



Overcy demonstrates an end-to-end AI voice automation workflow.



A customer calls a Twilio phone number. Twilio connects the live call to the FastAPI backend using a webhook and media stream. The backend establishes a WebSocket connection with OpenAI Realtime, allowing the caller and AI agent to communicate in real time.



During the conversation, the AI agent can collect customer information and invoke backend tools to create leads and schedule appointments.



\### V1 Capabilities



\- 📞 Receive real phone calls through Twilio

\- 🎙️ Stream caller audio in real time

\- 🤖 Conduct AI-powered voice conversations

\- 🔄 Twilio ↔ OpenAI Realtime WebSocket bridge

\- 👤 Capture caller information as CRM leads

\- 📅 Schedule appointments during a live call

\- 🛠️ AI tool/function calling

\- 🗄️ Persist leads and appointments

\- 🚫 Reject appointment dates that are already in the past

\- 💬 Provide appointment confirmation conversationally

\- 🌐 FastAPI REST/WebSocket backend

\- 🖥️ Next.js frontend

\- 🔐 Environment-variable-based secret management



\---



\# 🏗️ Architecture



```text

&#x20;                        ┌─────────────────────┐

&#x20;                        │       Caller        │

&#x20;                        │   Mobile / Phone    │

&#x20;                        └──────────┬──────────┘

&#x20;                                   │

&#x20;                                   │ PSTN Call

&#x20;                                   ▼

&#x20;                        ┌─────────────────────┐

&#x20;                        │       Twilio        │

&#x20;                        │ Programmable Voice  │

&#x20;                        └──────────┬──────────┘

&#x20;                                   │

&#x20;                        Voice Webhook / Media

&#x20;                                   │

&#x20;                                   ▼

&#x20;                ┌────────────────────────────────┐

&#x20;                │        FastAPI Backend         │

&#x20;                │                                │

&#x20;                │  /api/twilio/voice             │

&#x20;                │  /ws/twilio-media              │

&#x20;                │                                │

&#x20;                │  Voice orchestration           │

&#x20;                │  Tool execution                │

&#x20;                └──────────────┬─────────────────┘

&#x20;                               │

&#x20;                        WebSocket / Audio

&#x20;                               │

&#x20;                               ▼

&#x20;                ┌────────────────────────────────┐

&#x20;                │       OpenAI Realtime          │

&#x20;                │                                │

&#x20;                │  Speech understanding          │

&#x20;                │  Conversation reasoning        │

&#x20;                │  Voice generation              │

&#x20;                │  Tool calling                  │

&#x20;                └──────────────┬─────────────────┘

&#x20;                               │

&#x20;                          Tool Calls

&#x20;                               │

&#x20;                ┌──────────────┴───────────────┐

&#x20;                ▼                              ▼

&#x20;       ┌─────────────────┐            ┌─────────────────┐

&#x20;       │   Lead / CRM    │            │  Appointments   │

&#x20;       │     Tools       │            │      Tools      │

&#x20;       └────────┬────────┘            └────────┬────────┘

&#x20;                │                              │

&#x20;                └──────────────┬───────────────┘

&#x20;                               ▼

&#x20;                      ┌─────────────────┐

&#x20;                      │    Database     │

&#x20;                      │ Leads / Booking │

&#x20;                      └─────────────────┘

```



\---



\# 🔄 Real-Time Call Flow



```text

Caller

&#x20;  │

&#x20;  ▼

Twilio Phone Number

&#x20;  │

&#x20;  │ POST /api/twilio/voice

&#x20;  ▼

FastAPI

&#x20;  │

&#x20;  │ WebSocket

&#x20;  ▼

/ws/twilio-media

&#x20;  │

&#x20;  ├──────── Caller audio ────────► OpenAI Realtime

&#x20;  │

&#x20;  ◄──────── AI audio ──────────── OpenAI Realtime

&#x20;  │

&#x20;  ▼

Twilio

&#x20;  │

&#x20;  ▼

Caller hears AI response

```



When the caller requests an appointment:



```text

Caller

&#x20;  │

&#x20;  │ "I'd like to schedule a meeting"

&#x20;  ▼

OpenAI Realtime

&#x20;  │

&#x20;  │ Tool Call

&#x20;  ▼

Booking Tool

&#x20;  │

&#x20;  ├── Capture lead

&#x20;  ├── Validate requested date

&#x20;  ├── Create appointment

&#x20;  └── Store appointment

&#x20;  │

&#x20;  ▼

Tool Result

&#x20;  │

&#x20;  ▼

OpenAI Realtime

&#x20;  │

&#x20;  ▼

Voice confirmation to caller

```



\---



\# 🧰 Technology Stack



\## Backend



\- Python

\- FastAPI

\- WebSockets

\- OpenAI Realtime API

\- Twilio Programmable Voice

\- Database-backed lead and appointment management



\## Frontend



\- Next.js

\- React

\- TypeScript

\- CSS



\## AI / Voice



\- OpenAI Realtime

\- Real-time speech interaction

\- Tool/function calling

\- Conversational appointment scheduling



\## Telephony



\- Twilio Programmable Voice

\- Twilio Voice Webhooks

\- Twilio Media Streams



\## Development / Infrastructure



\- Git

\- GitHub

\- ngrok for local webhook tunneling

\- PowerShell

\- Uvicorn



\---



\# 📁 Project Structure



```text

overcy-voice-agent/

│

├── backend/

│   ├── main.py

│   ├── agent.py

│   ├── database.py

│   ├── models.py

│   ├── voice.py

│   │

│   └── tools/

│       ├── appointments.py

│       ├── booking.py

│       ├── crm.py

│       ├── leads.py

│       └── requirements.txt

│

├── frontend/

│   ├── app/

│   │   ├── layout.tsx

│   │   ├── page.tsx

│   │   └── globals.css

│   │

│   ├── public/

│   ├── package.json

│   ├── package-lock.json

│   ├── next.config.ts

│   └── tsconfig.json

│

├── .gitignore

└── README.md

```



\---



\# 📞 Twilio Integration



Twilio handles incoming telephone calls.



The configured voice webhook points to:



```text

POST /api/twilio/voice

```



The backend returns instructions that connect the call to the application's real-time media WebSocket:



```text

/ws/twilio-media

```



The media stream allows Overcy to exchange live call audio with the AI voice pipeline.



For local development, the FastAPI application can be exposed to Twilio through an HTTPS tunnel such as ngrok.



\---



\# 🤖 OpenAI Realtime Integration



Once the Twilio media stream connects, the backend establishes a real-time connection to OpenAI.



The application then acts as a bridge:



```text

Twilio Audio

&#x20;    ↓

FastAPI WebSocket

&#x20;    ↓

OpenAI Realtime

&#x20;    ↓

AI Response Audio

&#x20;    ↓

FastAPI WebSocket

&#x20;    ↓

Twilio

&#x20;    ↓

Caller

```



This allows the caller to communicate naturally with the AI without requiring a traditional text-only chatbot interface.



\---



\# 🛠️ Tool Calling



The voice agent can invoke application tools while speaking with a caller.



Examples include:



\### Lead Capture



The agent can collect caller information and create a lead.



\### Appointment Scheduling



The agent can collect:



\- Customer name

\- Requested date

\- Requested time



The backend validates the request before creating the appointment.



For example, a request for an appointment in the past is rejected and the AI asks the caller to choose a future date.



\---



\# 🗄️ Data Layer



The backend includes data models and database logic for application data such as:



```text

Leads

Appointments

```



This separates conversational AI behavior from persistent business data.



\---



\# ⚙️ Local Development



\## 1. Clone the repository



```bash

git clone https://github.com/daps-hub/overcy-voice-agent.git

cd overcy-voice-agent

```



\## 2. Create a Python virtual environment



Windows:



```powershell

python -m venv .venv

.\\.venv\\Scripts\\Activate.ps1

```



\## 3. Install backend dependencies



```powershell

pip install -r backend/tools/requirements.txt

```



\## 4. Configure environment variables



Create a local `.env` file for required credentials.



Example:



```text

OPENAI\_API\_KEY=your\_openai\_api\_key

TWILIO\_ACCOUNT\_SID=your\_twilio\_account\_sid

TWILIO\_AUTH\_TOKEN=your\_twilio\_auth\_token

```



Never commit the real `.env` file or API credentials to GitHub.



\## 5. Start the backend



Run the FastAPI/Uvicorn application using the command appropriate to the project's module configuration.



For example:



```powershell

uvicorn backend.main:app --reload

```



The backend will normally be available at:



```text

http://127.0.0.1:8000

```



FastAPI documentation:



```text

http://127.0.0.1:8000/docs

```



\## 6. Start the frontend



Open another terminal:



```powershell

cd frontend

npm install

npm run dev

```



\## 7. Expose the backend for Twilio



For local testing, expose port `8000` using an HTTPS tunnel.



Example:



```powershell

ngrok http 8000

```



Configure the Twilio voice webhook to point to:



```text

https://YOUR-PUBLIC-HOST/api/twilio/voice

```



\---



\# 🔐 Security



Sensitive credentials are intentionally excluded from source control.



The `.gitignore` excludes files and directories such as:



```text

.env

.env.\*

.venv/

venv/

\_\_pycache\_\_/

\*.pyc

\*.db

node\_modules/

frontend/.next/

\*.log

```



API keys, authentication tokens, and production secrets should be supplied through environment variables or a production secrets-management service.



\---



\# ✅ V1 Validation



The V1 call workflow has been tested end-to-end with a live telephone call.



Validated behavior includes:



```text

Incoming phone call

&#x20;       ↓

Twilio webhook

&#x20;       ↓

Twilio Media Stream

&#x20;       ↓

FastAPI WebSocket

&#x20;       ↓

OpenAI Realtime connection

&#x20;       ↓

Two-way voice conversation

&#x20;       ↓

Lead capture

&#x20;       ↓

Appointment request

&#x20;       ↓

Date validation

&#x20;       ↓

Appointment creation

&#x20;       ↓

Voice confirmation

```



The agent also successfully handles invalid scheduling requests by rejecting past dates and requesting a future appointment date.



\---



\# 🗺️ Roadmap



Potential post-V1 enhancements include:



\- AWS production deployment

\- Docker containerization

\- CI/CD with GitHub Actions

\- Production database deployment

\- Authentication and authorization

\- Multi-tenant business accounts

\- Business-specific agent configuration

\- Calendar integrations

\- CRM integrations

\- Call analytics

\- Conversation transcripts

\- Call history dashboard

\- Monitoring and observability

\- Automated AI evaluation

\- Retry and failure recovery

\- Human-agent escalation

\- SMS follow-up

\- Appointment reminders

\- Production secrets management



\---



\# 📌 Project Status



\*\*Version:\*\* V1.0



\*\*Status:\*\* Functional end-to-end prototype



Core V1 workflow:



\*\*Phone Call → Twilio → FastAPI → OpenAI Realtime → Tool Calling → Lead Capture → Appointment Scheduling\*\*



\---



\## Author



\*\*Dapo Hammed\*\*



Software Engineer / AI Engineer

