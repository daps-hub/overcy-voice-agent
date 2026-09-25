# Overcy AI Voice Agent
## Functional Requirements Specification

**Version:** 1.0  
**Project:** Overcy AI Voice Agent  
**Status:** V1 Completed

---

## 1. Purpose

This document defines the functional requirements for Overcy AI Voice Agent V1.

Overcy provides real-time AI conversations through web and telephone interfaces and supports lead capture and appointment scheduling through AI tool calling.

---

## 2. Core Functional Requirements

### FR-001 — Receive Incoming Phone Calls

The system shall receive incoming telephone calls through Twilio Programmable Voice.

**Acceptance Criteria**
- A caller can dial the configured Twilio number.
- Twilio sends a request to the Overcy voice webhook.
- The backend responds successfully.

---

### FR-002 — Establish Twilio Media Stream

The system shall establish a WebSocket connection for real-time telephone audio.

**Endpoint**

`/ws/twilio-media`

**Acceptance Criteria**
- Twilio can establish the WebSocket connection.
- The backend receives the Twilio stream start event.
- Audio events can be processed during the call.

---

### FR-003 — Connect to OpenAI Realtime

The backend shall establish a real-time connection to OpenAI for AI voice processing.

**Acceptance Criteria**
- The OpenAI Realtime WebSocket connects successfully.
- The realtime session is configured.
- Caller audio can be passed to the AI service.
- AI responses can be returned to the caller.

---

### FR-004 — Real-Time Conversation

The caller shall be able to have a two-way voice conversation with the AI agent.

**Acceptance Criteria**
- Caller speech is received.
- The AI processes caller speech.
- The AI generates an appropriate response.
- The caller hears the response through the telephone call.

---

### FR-005 — Lead Capture

The AI agent shall be able to capture customer information during a conversation.

**Acceptance Criteria**
- The agent can request customer information.
- The backend can create a lead record.
- The lead receives an identifier.
- The lead is persisted in the database.

---

### FR-006 — Appointment Information Collection

The AI agent shall collect the information required to schedule an appointment.

Information may include:

- Customer name
- Appointment date
- Appointment time

---

### FR-007 — Appointment Date Validation

The backend shall validate the requested appointment date.

**Acceptance Criteria**
- Future dates can proceed to scheduling.
- Past dates are rejected.
- The tool returns a clear validation error.
- The AI asks the caller for another date.

---

### FR-008 — Appointment Creation

The system shall create an appointment after successful validation.

**Acceptance Criteria**
- A valid lead is associated with the appointment.
- Appointment date is stored.
- Appointment time is stored.
- An appointment identifier is generated.
- A success result is returned to the AI.

---

### FR-009 — Tool Calling

The AI shall be able to invoke backend business functions during an active conversation.

Supported V1 operations include:

- Lead capture
- Appointment scheduling
- Appointment validation

---

### FR-010 — Tool Result Handling

The backend shall return structured tool results to the AI agent.

The result shall indicate whether the operation succeeded or failed.

The AI shall use this result to communicate the outcome to the caller.

---

### FR-011 — Database Persistence

The application shall persist business records generated during conversations.

V1 data includes:

- Leads
- Appointments

---

### FR-012 — Web Interface

The system shall provide a Next.js/React web interface for interacting with the application.

---

### FR-013 — Voice Webhook

The backend shall expose a Twilio voice webhook.

**Endpoint**

`POST /api/twilio/voice`

The endpoint shall return the instructions necessary for Twilio to connect the call to the application's media stream.

---

### FR-014 — Conversation Error Recovery

The AI agent shall attempt to recover when caller information is incomplete, invalid, or misunderstood.

Examples include:

- Missing appointment time
- Missing appointment date
- Invalid date
- Incorrectly interpreted caller information

The agent should request clarification instead of silently creating invalid business data.

---

## 3. External Integrations

### Twilio

Used for:

- Telephone number
- Incoming calls
- Voice webhooks
- Media streaming

### OpenAI Realtime

Used for:

- Speech processing
- Conversational reasoning
- Voice response generation
- Tool/function calling

---

## 4. Application Components

### Frontend

Technology:

- Next.js
- React
- TypeScript

Responsibilities:

- User interface
- Web-based interaction
- Presentation of application functionality

### Backend

Technology:

- Python
- FastAPI
- WebSockets

Responsibilities:

- API endpoints
- Twilio webhook handling
- Media-stream handling
- OpenAI Realtime integration
- Business tool execution
- Validation
- Database operations

### Data Layer

Responsibilities:

- Lead persistence
- Appointment persistence
- Business record retrieval

---

## 5. V1 End-to-End Validation

The following scenario has been successfully demonstrated:

1. Caller dials the Twilio number.
2. Twilio invokes `/api/twilio/voice`.
3. Twilio establishes `/ws/twilio-media`.
4. Backend establishes the OpenAI Realtime connection.
5. AI greets the caller.
6. Caller requests an appointment.
7. AI gathers appointment information.
8. Backend receives the AI tool call.
9. Backend validates the requested date.
10. A past date is rejected.
11. AI asks the caller for a future date.
12. Caller provides a valid date.
13. Backend creates the lead.
14. Backend creates the appointment.
15. AI confirms successful scheduling to the caller.

---

## 6. Future Functional Requirements

Future versions may support:

- Appointment rescheduling
- Appointment cancellation
- SMS confirmation
- Email confirmation
- Calendar integration
- CRM synchronization
- Multiple business locations
- Authentication
- Role-based authorization
- Administrative dashboard
- Conversation analytics
- Call history
- Monitoring and alerting
- Production cloud deployment

---

## 7. V1 Completion Criteria

Overcy V1 satisfies its core functional requirements when a caller can complete the following workflow:

`Phone Call → Twilio → FastAPI → OpenAI Realtime → AI Conversation → Tool Call → Lead/Appointment → Database → Voice Confirmation`