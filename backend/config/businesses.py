BUSINESSES = {
    "tanimo": {
        "business_id": "tanimo",
        "name": "Tanimo Software Solutions",

        # We'll replace this with your actual Twilio number later.
        "phone_number": None,

        "greeting": (
            "Hello, thank you for calling "
            "Tanimo Software Solutions. "
            "How can I help you today?"
        ),

        "knowledge_file": "business.txt",

        "timezone": "America/Los_Angeles",

        "active": True,
    },

    # Demo second customer/business.
    "bright_smile_dental": {
        "business_id": "bright_smile_dental",
        "name": "Bright Smile Dental",

        # Later this business can have its own Twilio number.
        "phone_number": None,

        "greeting": (
            "Hello, thank you for calling "
            "Bright Smile Dental. "
            "How can I help you today?"
        ),

        "knowledge_file": "bright_smile_dental.txt",

        "timezone": "America/Los_Angeles",

        "active": True,
    },
}


def get_business(business_id: str):
    return BUSINESSES.get(business_id)


def get_business_by_phone(phone_number: str):
    for business in BUSINESSES.values():
        if business.get("phone_number") == phone_number:
            return business

    return None