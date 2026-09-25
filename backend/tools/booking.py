from backend.tools.leads import create_lead
from backend.tools.appointments import create_appointment


def create_lead_and_appointment(
    name: str,
    appointment_date: str,
    appointment_time: str,
    phone: str = None,
    email: str = None,
    interest: str = None
):
    # Step 1: Create or retrieve the customer lead
    lead = create_lead(
        name=name,
        phone=phone,
        email=email,
        interest=interest
    )

    # Make sure lead creation succeeded
    if not lead.get("lead_id"):
        return {
            "success": False,
            "error": "lead_creation_failed",
            "lead": lead,
            "appointment": None,
            "message": "Unable to create the customer lead."
        }

    # Step 2: Attempt to create the appointment
    appointment = create_appointment(
        lead_id=lead["lead_id"],
        appointment_date=appointment_date,
        appointment_time=appointment_time
    )

    # Step 3: Propagate appointment failure
    if not appointment.get("success"):
        return {
            "success": False,
            "error": appointment.get(
                "error",
                "appointment_creation_failed"
            ),
            "lead": lead,
            "appointment": appointment,
            "message": appointment.get(
                "message",
                "Unable to schedule the appointment."
            )
        }

    # Step 4: Everything succeeded
    return {
        "success": True,
        "lead": lead,
        "appointment": appointment,
        "message": "Lead captured and appointment scheduled successfully."
    }