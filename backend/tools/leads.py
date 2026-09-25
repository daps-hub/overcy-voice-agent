from backend.database import get_connection


def create_lead(
    name: str,
    phone: str = None,
    email: str = None,
    interest: str = None
):
    connection = get_connection()
    cursor = connection.cursor()

    # Try to identify an existing customer.
    #
    # Email is preferred because it is more reliable
    # than matching only by name.
    if email:
        cursor.execute(
            """
            SELECT id, name, phone, email, interest
            FROM leads
            WHERE LOWER(email) = LOWER(?)
            LIMIT 1
            """,
            (email,)
        )

        existing_lead = cursor.fetchone()

        if existing_lead:
            connection.close()

            return {
                "success": True,
                "duplicate": True,
                "lead_id": existing_lead["id"],
                "name": existing_lead["name"],
                "message": "Existing lead found."
            }

    # If there is no email, use phone when available.
    if phone:
        cursor.execute(
            """
            SELECT id, name, phone, email, interest
            FROM leads
            WHERE phone = ?
            LIMIT 1
            """,
            (phone,)
        )

        existing_lead = cursor.fetchone()

        if existing_lead:
            connection.close()

            return {
                "success": True,
                "duplicate": True,
                "lead_id": existing_lead["id"],
                "name": existing_lead["name"],
                "message": "Existing lead found."
            }

    # No existing customer found.
    cursor.execute(
        """
        INSERT INTO leads (
            name,
            phone,
            email,
            interest
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            name,
            phone,
            email,
            interest
        )
    )

    connection.commit()

    lead_id = cursor.lastrowid

    connection.close()

    return {
        "success": True,
        "duplicate": False,
        "lead_id": lead_id,
        "name": name
    }