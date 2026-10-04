from pathlib import Path
import re


KNOWLEDGE_DIR = (
    Path(__file__).resolve().parent.parent
    / "knowledge"
)


def search_business_knowledge(
    query: str,
    knowledge_file: str = "business.txt",
) -> dict:
    """
    Search the selected business knowledge file for information
    relevant to the caller's question.
    """

    knowledge_file_path = (
        KNOWLEDGE_DIR / knowledge_file
    )

    if not knowledge_file_path.exists():
        return {
            "success": False,
            "error": "knowledge_file_not_found",
            "message": "The business knowledge file could not be found.",
        }

    knowledge = knowledge_file_path.read_text(
        encoding="utf-8"
    ).strip()

    if not knowledge:
        return {
            "success": False,
            "error": "knowledge_empty",
            "message": "The business knowledge base is empty.",
        }

    query_lower = query.lower()

    # Direct retrieval for common business-information questions.
    keyword_map = {
        "hours": [
            "business hours",
            "hours",
            "open",
            "opening",
            "closing",
            "close",
        ],
        "services": [
            "services",
            "service",
            "provide",
            "offer",
            "do you do",
        ],
        "pricing": [
            "pricing",
            "price",
            "prices",
            "cost",
            "costs",
            "how much",
        ],
        "cancellation": [
            "cancel",
            "cancellation",
        ],
        "appointment": [
            "appointment",
            "appointments",
            "booking",
            "book",
            "reschedule",
        ],
    }

    target_heading = None

    for category, keywords in keyword_map.items():
        if any(keyword in query_lower for keyword in keywords):
            if category == "hours":
                target_heading = "BUSINESS HOURS"
            elif category == "services":
                target_heading = "SERVICES"
            elif category == "pricing":
                target_heading = "PRICING"
            elif category == "cancellation":
                target_heading = "CANCELLATION POLICY"
            elif category == "appointment":
                target_heading = "APPOINTMENT POLICY"

            break

    # If we know the section, return the heading plus its content.
    if target_heading:
        pattern = (
            rf"{re.escape(target_heading)}\s*\n+"
            rf"(.*?)(?=\n[A-Z][A-Z /&-]*\n|\Z)"
        )

        match = re.search(
            pattern,
            knowledge,
            flags=re.DOTALL,
        )

        if match:
            content = (
                target_heading
                + "\n"
                + match.group(1).strip()
            )

            return {
                "success": True,
                "found": True,
                "query": query,
                "content": content,
            }

    # Fallback keyword retrieval.
    sections = re.split(
        r"\n\s*\n",
        knowledge,
    )

    query_words = {
        word.lower()
        for word in re.findall(r"\b\w+\b", query)
        if len(word) > 2
    }

    scored_sections = []

    for section in sections:
        section_words = {
            word.lower()
            for word in re.findall(r"\b\w+\b", section)
        }

        score = len(
            query_words.intersection(section_words)
        )

        if score > 0:
            scored_sections.append(
                (score, section.strip())
            )

    scored_sections.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    if not scored_sections:
        return {
            "success": True,
            "found": False,
            "query": query,
            "message": (
                "No relevant information was found "
                "in the business knowledge base."
            ),
        }

    matches = [
        section
        for _, section in scored_sections[:3]
    ]

    return {
        "success": True,
        "found": True,
        "query": query,
        "content": "\n\n".join(matches),
    }