import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from backend.tools.leads import create_lead
from backend.tools.appointments import create_appointment
from backend.tools.booking import create_lead_and_appointment


# Load environment variables
load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)
conversation_sessions = {}

SYSTEM_PROMPT = """
You are a helpful AI voice assistant for a business.

Your responsibilities include:
- answering customer questions
- identifying potential customers
- collecting lead information
- creating leads
- scheduling appointments

Rules:

1. Never invent customer information.

2. Remember information the customer provided earlier
   in the current conversation.

3. If a customer provides their name and expresses
   interest in a product or service, you may use the
   create_lead tool.

4. Before creating an appointment, you MUST confirm
   the appointment date and time with the customer.

5. If the customer has requested an appointment but
   has NOT explicitly confirmed the date and time,
   DO NOT call create_appointment or
   create_lead_and_appointment.

6. Instead, ask:
   "Just to confirm, you'd like your appointment for
   [date] at [time]. Is that correct?"

7. Only after the customer explicitly confirms with
   words such as "yes", "correct", "that's right",
   or an equivalent confirmation may you create the
   appointment.

8. When the customer confirms, use information from
   the conversation history. Do not ask them to repeat
   their name, interest, date, or time if you already
   have it.

9. If the customer is new and has provided their name,
   interest, appointment date, and appointment time,
   use create_lead_and_appointment AFTER confirmation.

10. If an existing customer provides a lead ID and
    confirms an appointment, use create_appointment.

11. Convert appointment dates to YYYY-MM-DD format.

12. Use the appropriate tool instead of claiming an
    action was completed without actually performing it.

13. If a date or time is ambiguous, ask the customer
    to clarify it before calling any appointment tool.

14. Never claim an appointment was scheduled when a tool
    returns success=false. Explain the tool error and ask
    the customer for a valid future date or time.
"""


tools = [

    # -------------------------------------------------
    # TOOL 1: CREATE LEAD
    # -------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "create_lead",
            "description": "Create a new customer lead in the CRM database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Customer's name"
                    },
                    "phone": {
                        "type": "string",
                        "description": "Customer's phone number"
                    },
                    "email": {
                        "type": "string",
                        "description": "Customer's email address"
                    },
                    "interest": {
                        "type": "string",
                        "description": "Product or service the customer is interested in"
                    }
                },
                "required": [
                    "name",
                    "interest"
                ]
            }
        }
    },

    # -------------------------------------------------
    # TOOL 2: CREATE APPOINTMENT
    # -------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "create_appointment",
            "description": "Schedule an appointment for an existing customer lead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_id": {
                        "type": "integer",
                        "description": "Database ID of the existing customer lead"
                    },
                    "appointment_date": {
                        "type": "string",
                        "description": "Appointment date in YYYY-MM-DD format"
                    },
                    "appointment_time": {
                        "type": "string",
                        "description": "Appointment time such as 2:00 PM"
                    }
                },
                "required": [
                    "lead_id",
                    "appointment_date",
                    "appointment_time"
                ]
            }
        }
    },

    # -------------------------------------------------
    # TOOL 3: CREATE LEAD AND APPOINTMENT
    # -------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "create_lead_and_appointment",
            "description": (
                "Create a new customer lead and schedule an "
                "appointment for that customer in one operation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Customer's name"
                    },
                    "phone": {
                        "type": "string",
                        "description": "Customer's phone number"
                    },
                    "email": {
                        "type": "string",
                        "description": "Customer's email address"
                    },
                    "interest": {
                        "type": "string",
                        "description": "Product or service the customer is interested in"
                    },
                    "appointment_date": {
                        "type": "string",
                        "description": "Appointment date in YYYY-MM-DD format"
                    },
                    "appointment_time": {
                        "type": "string",
                        "description": "Appointment time such as 3:30 PM"
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
    }
]


def run_agent(
    user_message: str,
    session_id: str = "default"
):
    if session_id not in conversation_sessions:
        conversation_sessions[session_id] = []

    conversation_history = conversation_sessions[session_id]

    conversation_history.append(
        {
            "role": "user",
            "content": user_message
        }
    )

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        *conversation_history
    ]
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )

    message = response.choices[0].message

    # If GPT does not need a tool
    if not message.tool_calls:
        return {
            "response": message.content,
            "tool_called": None
        }

    # Get the first tool selected by GPT
    tool_call = message.tool_calls[0]

    tool_name = tool_call.function.name

    arguments = json.loads(
        tool_call.function.arguments
    )

    # -------------------------------------------------
    # HANDLE CREATE LEAD
    # -------------------------------------------------

    if tool_name == "create_lead":

        result = create_lead(
            name=arguments["name"],
            phone=arguments.get("phone"),
            email=arguments.get("email"),
            interest=arguments["interest"]
        )

        return {
            "response": (
                f"Thanks {arguments['name']}. "
                "I've saved your information."
            ),
            "tool_called": "create_lead",
            "tool_result": result
        }

    # -------------------------------------------------
    # HANDLE CREATE APPOINTMENT
    # -------------------------------------------------

    if tool_name == "create_appointment":

        result = create_appointment(
            lead_id=arguments["lead_id"],
            appointment_date=arguments["appointment_date"],
            appointment_time=arguments["appointment_time"]
        )

        if not result.get("success"):
            response_text = result.get(
                "message",
                "I wasn't able to schedule that appointment."
            )
        else:
            response_text = (
                "Your appointment has been scheduled for "
                f"{arguments['appointment_date']} "
                f"at {arguments['appointment_time']}."
            )

        return {
            "response": response_text,
            "tool_called": "create_appointment",
            "tool_result": result
        }

    # -------------------------------------------------
    # HANDLE CREATE LEAD + APPOINTMENT
    # -------------------------------------------------

    if tool_name == "create_lead_and_appointment":
     result = create_lead_and_appointment(
        name=arguments["name"],
        phone=arguments.get("phone"),
        email=arguments.get("email"),
        interest=arguments["interest"],
        appointment_date=arguments["appointment_date"],
        appointment_time=arguments["appointment_time"]
    )

    # Never report a successful booking when the tool rejected it.
    if not result.get("success"):
        response_text = result.get(
            "message",
            "I wasn't able to schedule that appointment. "
            "Please choose another date and time."
        )
    else:
        lead_duplicate = result["lead"].get("duplicate", False)
        appointment_duplicate = result["appointment"].get("duplicate", False)

        if appointment_duplicate:
            response_text = (
                f"{arguments['name']}, you already have an "
                f"appointment scheduled for "
                f"{arguments['appointment_date']} "
                f"at {arguments['appointment_time']}."
            )
        elif lead_duplicate:
            response_text = (
                f"Welcome back {arguments['name']}. "
                "I found your existing customer record and "
                f"scheduled your appointment for "
                f"{arguments['appointment_date']} "
                f"at {arguments['appointment_time']}."
            )
        else:
            response_text = (
                f"Thanks {arguments['name']}. "
                "I've saved your information and scheduled "
                f"your appointment for "
                f"{arguments['appointment_date']} "
                f"at {arguments['appointment_time']}."
            )

    conversation_history.append(
        {
            "role": "assistant",
            "content": response_text
        }
    )

    return {
        "response": response_text,
        "tool_called": "create_lead_and_appointment",
        "tool_result": result
    }