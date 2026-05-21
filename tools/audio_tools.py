import os
from openai import OpenAI
from langchain_core.tools import tool


@tool
def transcribe_audio(file_path: str) -> str:
    """
    Transcribes an MP3 or other audio file to text using OpenAI's Whisper model.
    Useful for converting spoken audio, podcasts, or voice notes into readable text.
    """
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        if not os.path.exists(file_path):
            return f"Error: Audio file not found at {file_path}"

        with open(file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return f"Transcription successful:\n\n{transcription.text}"
    except Exception as e:
        return f"Failed to transcribe audio: {str(e)}"
