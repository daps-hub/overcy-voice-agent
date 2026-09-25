from datetime import datetime
from backend.database import get_connection


def create_appointment(
    lead_id: int,
    appointment_date: str,
    appointment_time: str
):
    # ---------------------------------------------------------
    # Guardrail: prevent appointments from being created
    # for dates in the past.
    # Expected date format: YYYY-MM-DD
    # ---------------------------------------------------------
    try:
        requested_date = datetime.strptime(
            appointment_date,
            "%Y-%m-%d"
        ).date()
    except ValueError:
        return {
            "success": False,
            "duplicate": False,
            "lead_id": lead_id,
            "date": appointment_date,
            "time": appointment_time,
            "error": "invalid_date",
            "message": (
                "The appointment date is invalid. "
                "Please provide the date in YYYY-MM-DD format."
            )
        }

    today = datetime.now().date()

    if requested_date < today:
        return {
            "success": False,
            "duplicate": False,
            "lead_id": lead_id,
            "date": appointment_date,
            "time": appointment_time,
            "error": "past_date",
            "message": (
                f"The requested appointment date {appointment_date} "
                "is in the past. Please choose a future date."
            )
        }

    # ---------------------------------------------------------
    # Database connection
    # ---------------------------------------------------------
    connection = get_connection()
    cursor = connection.cursor()

    # Check whether this exact appointment already exists
    cursor.execute(
        """
        SELECT id
        FROM appointments
        WHERE lead_id = ?
          AND appointment_date = ?
          AND appointment_time = ?
          AND status = 'scheduled'
        """,
        (
            lead_id,
            appointment_date,
            appointment_time
        )
    )

    existing_appointment = cursor.fetchone()

    if existing_appointment:
        connection.close()

        return {
            "success": False,
            "duplicate": True,
            "appointment_id": existing_appointment["id"],
            "lead_id": lead_id,
            "date": appointment_date,
            "time": appointment_time,
            "message": "This appointment is already scheduled."
        }

    # No duplicate found — create appointment
    cursor.execute(
        """
        INSERT INTO appointments (
            lead_id,
            appointment_date,
            appointment_time
        )
        VALUES (?, ?, ?)
        """,
        (
            lead_id,
            appointment_date,
            appointment_time
        )
    )

    connection.commit()

    appointment_id = cursor.lastrowid

    connection.close()

    return {
        "success": True,
        "duplicate": False,
        "appointment_id": appointment_id,
        "lead_id": lead_id,
        "date": appointment_date,
        "time": appointment_time
    }