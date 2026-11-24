
import time
from collections import deque
from math import gcd

import numpy as np
import sounddevice as sd
from scipy.signal import resample_poly
from faster_whisper import WhisperModel


# ==========================================
# MICROPHONE CONFIGURATION
# ==========================================

MICROPHONE_DEVICE = 3

MODEL_SIZE = "base.en"
DEVICE = "cpu"
COMPUTE_TYPE = "int8"

SILENCE_THRESHOLD = 0.008
SILENCE_DURATION = 0.4
MAX_RECORDING_TIME = 20
LISTEN_TIMEOUT = 10
TARGET_SAMPLE_RATE = 16000
BLOCK_DURATION = 0.03

DEBUG = False


# ==========================================
# LOAD WHISPER MODEL
# ==========================================

print("Loading speech recognition model...")

model = WhisperModel(
    MODEL_SIZE,
    device=DEVICE,
    compute_type=COMPUTE_TYPE
)

print("Speech recognition ready.")
print(f"Processing device: {DEVICE}")


# ==========================================
# LISTEN FUNCTION
# ==========================================

def listen(silent=False):

    device_info = sd.query_devices(
        MICROPHONE_DEVICE,
        kind="input"
    )

    sample_rate = int(device_info["default_samplerate"])
    block_size = int(sample_rate * BLOCK_DURATION)

    frames = []
    pre_buffer = deque(maxlen=8)

    speech_detected = False
    silence_time = 0
    speech_start = None

    if not silent:
        print("Listening... Speak into your microphone.")

    with sd.InputStream(
        device=MICROPHONE_DEVICE,
        samplerate=sample_rate,
        blocksize=block_size,
        dtype="float32",
        channels=1
    ) as stream:

        start_time = time.monotonic()

        while True:

            data, overflowed = stream.read(block_size)

            volume = np.sqrt(np.mean(data ** 2))
            now = time.monotonic()

            if DEBUG:
                print(
                    f"Volume: {volume:.5f}",
                    end="\r",
                    flush=True
                )

            # Wait for speech to begin
            if not speech_detected:

                pre_buffer.append(data.copy())

                if volume > SILENCE_THRESHOLD:

                    speech_detected = True
                    speech_start = now

                    frames.extend(pre_buffer)

                    if not silent or DEBUG:
                        print("\nSpeech detected.")

                elif now - start_time >= LISTEN_TIMEOUT:
                    return ""

                continue

            # Record speech
            frames.append(data.copy())

            if volume > SILENCE_THRESHOLD:
                silence_time = 0
            else:
                silence_time += len(data) / sample_rate

            # Stop after silence
            if silence_time >= SILENCE_DURATION:
                break

            # Maximum recording duration
            if now - speech_start >= MAX_RECORDING_TIME:
                break

    if not frames:
        return ""


    # ======================================
    # PREPARE AUDIO
    # ======================================

    audio = np.concatenate(frames, axis=0).flatten()

    # Resample microphone audio to 16000 Hz
    if sample_rate != TARGET_SAMPLE_RATE:

        divisor = gcd(sample_rate, TARGET_SAMPLE_RATE)

        audio = resample_poly(
            audio,
            TARGET_SAMPLE_RATE // divisor,
            sample_rate // divisor
        )

    # Preserve normalized float32 audio
    audio = np.clip(
        audio,
        -1.0,
        1.0
    ).astype(np.float32)


    # ======================================
    # TRANSCRIBE SPEECH
    # ======================================

    if not silent or DEBUG:
        print("Processing speech...")

    processing_start = time.perf_counter()

    segments, _ = model.transcribe(
        audio,
        language="en",
        beam_size=1,
        best_of=1,
        temperature=0.0,
        vad_filter=True,
        condition_on_previous_text=False,
        without_timestamps=True
    )

    text = " ".join(
        segment.text.strip()
        for segment in segments
    ).strip()

    elapsed = time.perf_counter() - processing_start

    if not silent or DEBUG:
        print(f"Speech processed in {elapsed:.2f} seconds.")

    if DEBUG:
        print("Recognized:", repr(text))

    return text


# ==========================================
# STANDALONE MICROPHONE TEST
# ==========================================

if __name__ == "__main__":

    try:

        while True:

            recognized_text = listen()

            if recognized_text:
                print("You said:", recognized_text)

    except KeyboardInterrupt:
        print("\nMicrophone stopped.")
