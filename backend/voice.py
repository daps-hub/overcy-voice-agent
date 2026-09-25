import os
import tempfile

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "audio.webm"
):
    suffix = os.path.splitext(filename)[1]

    if not suffix:
        suffix = ".webm"

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        with open(temp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="gpt-4o-transcribe",
                file=audio_file
            )

        return transcript.text

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def synthesize_speech(text: str):
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".mp3"
        ) as temp_file:
            temp_path = temp_file.name

        with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text
        ) as response:
            response.stream_to_file(temp_path)

        with open(temp_path, "rb") as audio_file:
            audio_bytes = audio_file.read()

        return audio_bytes

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)