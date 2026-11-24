
import json
import queue
from pathlib import Path

import sounddevice as sd
from vosk import Model, KaldiRecognizer

MODEL_PATH = Path(__file__).resolve().parent / "vosk-model-small-en-us-0.15"

model = Model(str(MODEL_PATH))
audio_queue = queue.Queue()

def audio_callback(indata, frames, time, status):
    if status:
        print(status)
    audio_queue.put(bytes(indata))

def listen(silent = False):

    while not audio_queue.empty():
        audio_queue.get_nowait()
        
    device_info = sd.query_devices(kind="input")
    sample_rate = int(device_info["default_samplerate"])

    recognizer = KaldiRecognizer(model, sample_rate)
    if not silent:
        print("Listening... Speak into your microphone.")

    with sd.RawInputStream(
        samplerate=sample_rate,
        blocksize=8000,
        dtype="int16",
        channels=1,
        callback=audio_callback
    ):
        while True:
            data = audio_queue.get()

            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").strip()

                if text:
                    return text

if __name__ == "__main__":
    try:
        recognized_text = listen()
        print("You said:", recognized_text)
    except KeyboardInterrupt:
        print("\nMicrophone stopped.")
