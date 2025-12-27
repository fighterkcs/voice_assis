import requests
import os
import tempfile
import uuid
import streamlit as st

voice_id = "gO8Kb3hHPEPElVxVHDwT"

def speak(text, output=None):
    if output is None:
        temp_dir = tempfile.gettempdir()
        unique_id = str(uuid.uuid4())
        output = os.path.join(temp_dir, f"krishna_{unique_id}.mp3")
    if os.path.exists(output):
        base, ext = os.path.splitext(output)
        unique_id = str(uuid.uuid4())
        output = f"{base}_{unique_id}{ext}"
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": st.secrets["ELEVEN_API_KEY"],
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.85
        }
    }
    r = requests.post(url, json=data, headers=headers)
    r.raise_for_status()
    with open(output, "wb") as f:
        f.write(r.content)
    if not os.path.exists(output) or os.path.getsize(output) == 0:
        raise RuntimeError("Failed to generate audio file")
    return output
