import sqlite3
from datetime import datetime
from backend.database import get_connection
from difflib import SequenceMatcher

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

def cancel_appointment(
    customer_name: str,
    appointment_date: str
):
    connection = get_connection()
    cursor = connection.cursor()

    # Find scheduled appointments on the requested date first.
    # Then fuzzy-match the spoken customer name because voice
    # transcription may slightly misspell names.
    cursor.execute(
        """
        SELECT
            appointments.id,
            appointments.appointment_date,
            appointments.appointment_time,
            leads.name
        FROM appointments
        JOIN leads
            ON appointments.lead_id = leads.id
        WHERE appointments.appointment_date = ?
        AND appointments.status = 'scheduled'
        ORDER BY appointments.appointment_time ASC
        """,
        (appointment_date,)
    )

    candidates = cursor.fetchall()

    appointment = None
    best_score = 0.0

    spoken_name = customer_name.strip().lower()

    for candidate in candidates:
        database_name = candidate["name"].strip().lower()

        score = SequenceMatcher(
            None,
            spoken_name,
            database_name,
        ).ratio()

        if score > best_score:
            best_score = score
            appointment = candidate

    # Require a strong match so we do not accidentally
    # cancel another customer's appointment.
    if best_score < 0.80:
        appointment = None

    if not appointment:
        connection.close()

        return {
            "success": False,
            "error": "appointment_not_found",
            "message": (
                f"No scheduled appointment was found for "
                f"{customer_name} on {appointment_date}."
            )
        }

    appointment_id = appointment["id"]
    appointment_time = appointment["appointment_time"]
    matched_name = appointment["name"]

    cursor.execute(
        """
        UPDATE appointments
        SET status = 'cancelled'
        WHERE id = ?
        AND status = 'scheduled'
        """,
        (appointment_id,)
    )

    connection.commit()
    connection.close()

    return {
        "success": True,
        "appointment_id": appointment_id,
        "name": matched_name,
        "appointment_date": appointment_date,
        "appointment_time": appointment_time,
        "status": "cancelled",
        "message": (
            f"The appointment for {matched_name} on "
            f"{appointment_date} at {appointment_time} "
            f"has been cancelled."
        )
    }
def reschedule_appointment(
    customer_name: str,
    current_appointment_date: str,
    new_appointment_date: str,
    new_appointment_time: str,
):
    # Validate the new date.
    try:
        requested_date = datetime.strptime(
            new_appointment_date,
            "%Y-%m-%d",
        ).date()
    except ValueError:
        return {
            "success": False,
            "error": "invalid_date",
            "message": "The new appointment date is invalid.",
        }

    if requested_date < datetime.now().date():
        return {
            "success": False,
            "error": "past_date",
            "message": "The new appointment date cannot be in the past.",
        }

    # Normalize the new time.
    raw_time = new_appointment_time.strip().upper()
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
                time_format,
            ).strftime("%H:%M")
            break
        except ValueError:
            continue

    if normalized_time is None:
        return {
            "success": False,
            "error": "invalid_time",
            "message": "The new appointment time is invalid.",
        }

    connection = get_connection()
    cursor = connection.cursor()

    # Find the customer's current scheduled appointment.
    cursor.execute(
        """
        SELECT
            appointments.id,
            appointments.appointment_date,
            appointments.appointment_time,
            leads.name
        FROM appointments
        JOIN leads
            ON appointments.lead_id = leads.id
        WHERE LOWER(leads.name) = LOWER(?)
        AND appointments.appointment_date = ?
        AND appointments.status = 'scheduled'
        ORDER BY appointments.appointment_time ASC
        LIMIT 1
        """,
        (
            customer_name.strip(),
            current_appointment_date,
        ),
    )

    appointment = cursor.fetchone()

    if not appointment:
        connection.close()

        return {
            "success": False,
            "error": "appointment_not_found",
            "message": (
                f"No scheduled appointment was found for "
                f"{customer_name} on {current_appointment_date}."
            ),
        }

    appointment_id = appointment["id"]
    old_time = appointment["appointment_time"]

    # Make sure the new slot is available.
    cursor.execute(
        """
        SELECT id
        FROM appointments
        WHERE appointment_date = ?
        AND appointment_time = ?
        AND status = 'scheduled'
        AND id != ?
        LIMIT 1
        """,
        (
            new_appointment_date,
            normalized_time,
            appointment_id,
        ),
    )

    existing = cursor.fetchone()

    if existing:
        connection.close()

        return {
            "success": False,
            "error": "slot_unavailable",
            "message": (
                f"The {normalized_time} appointment on "
                f"{new_appointment_date} is already booked."
            ),
        }

    # Move the existing appointment.
    cursor.execute(
        """
        UPDATE appointments
        SET appointment_date = ?,
            appointment_time = ?
        WHERE id = ?
        AND status = 'scheduled'
        """,
        (
            new_appointment_date,
            normalized_time,
            appointment_id,
        ),
    )

    connection.commit()
    connection.close()

    return {
        "success": True,
        "appointment_id": appointment_id,
        "name": customer_name,
        "old_appointment_date": current_appointment_date,
        "old_appointment_time": old_time,
        "new_appointment_date": new_appointment_date,
        "new_appointment_time": normalized_time,
        "status": "scheduled",
        "message": (
            f"The appointment for {customer_name} was rescheduled "
            f"from {current_appointment_date} at {old_time} "
            f"to {new_appointment_date} at {normalized_time}."
        ),
    }