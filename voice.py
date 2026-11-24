
import re
import wave
import time
import msvcrt
import winsound
import tempfile
from pathlib import Path
from piper import PiperVoice
import io
import wave
from threading import Lock

MODEL_PATH = Path(__file__).resolve().parent / "en_US-ryan-medium.onnx"

voice = PiperVoice.load(str(MODEL_PATH))

def clean_for_speech(text):
    text = re.sub(r"(?m)^[ \t]*[-*+][ \t]+", "", text)
    text = text.replace("*", "")
    text = text.replace("\n", ". ")
    return text

def speak(text):
    text = clean_for_speech(text)

    if not text.strip():
        return

    with tempfile.TemporaryDirectory() as folder:
        audio_path = Path(folder) / "response.wav"

        # Generate the voice recording
        with wave.open(str(audio_path), "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)

        # Calculate audio duration
        with wave.open(str(audio_path), "rb") as wav_file:
            duration = (
                wav_file.getnframes()
                / wav_file.getframerate()
            )

        print("Atlas speaking... Press S to stop.")

        # Start playback without blocking Python
        winsound.PlaySound(
            str(audio_path),
            winsound.SND_FILENAME | winsound.SND_ASYNC
        )

        try:
            end_time = time.monotonic() + duration

            while time.monotonic() < end_time:
                if msvcrt.kbhit():
                    key = msvcrt.getwch().lower()

                    if key == "s":
                        print("Atlas: Speech stopped.")
                        break

                time.sleep(0.05)

        finally:
            # Stop playback before deleting the audio
            winsound.PlaySound(None, 0)

if __name__ == "__main__":
    speak(
        "Hello! I am Atlas, your personal AI assistant. "
        "I can answer questions, explain programming, "
        "and help you with many different tasks."
    )
synthesis_lock = Lock()


def generate_audio(text):

    text = clean_for_speech(text)

    buffer = io.BytesIO()

    with synthesis_lock:
        with wave.open(buffer, "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)

    return buffer.getvalue()