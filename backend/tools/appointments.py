import sqlite3
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


    # Normalize appointment time to 24-hour HH:MM format.
    # Examples:
    # 1 PM      -> 13:00
    # 1:00 PM   -> 13:00
    # 1 p.m.    -> 13:00
    # 14:00     -> 14:00
    # ---------------------------------------------------------
    raw_time = appointment_time.strip().upper()
    raw_time = raw_time.replace(".", "")

    supported_formats = (
        "%H:%M",
        "%I %p",
        "%I:%M %p",
    )

    normalized_time = None

    for time_format in supported_formats:
        try:
            normalized_time = datetime.strptime(
                raw_time,
                time_format
            ).strftime("%H:%M")
            break
        except ValueError:
            continue

    if normalized_time is None:
        return {
            "success": False,
            "duplicate": False,
            "lead_id": lead_id,
            "date": appointment_date,
            "time": appointment_time,
            "error": "invalid_time",
            "message": (
                "The appointment time is invalid. "
                "Please provide a valid time."
            )
        }

    appointment_time = normalized_time
    connection = get_connection()
    cursor = connection.cursor()

    # Check whether this exact appointment already exists
    # Check whether this time slot is already booked
    cursor.execute(
        """
        SELECT id, lead_id
        FROM appointments
        WHERE appointment_date = ?
        AND appointment_time = ?
        AND status = 'scheduled'
        LIMIT 1
        """,
        (
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
            "error": "slot_unavailable",
            "message": (
                f"The {appointment_time} appointment on "
                f"{appointment_date} is already booked. "
                "Please choose another date or time."
            )
        }

    # No duplicate found — create appointment
    try:
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

    except sqlite3.IntegrityError:
        connection.rollback()
        connection.close()

        return {
            "success": False,
            "duplicate": True,
            "lead_id": lead_id,
            "date": appointment_date,
            "time": appointment_time,
            "error": "slot_unavailable",
            "message": (
                f"The {appointment_time} appointment on "
                f"{appointment_date} is already booked. "
                "Please choose another date or time."
            )
        }

    connection.close()

    return {
        "success": True,
        "duplicate": False,
        "appointment_id": appointment_id,
        "lead_id": lead_id,
        "date": appointment_date,
        "time": appointment_time
    }
