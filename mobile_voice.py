import io
import av
import numpy as np

from threading import Lock
from faster_whisper import WhisperModel

model = None
model_lock = Lock()


def transcribe_audio(audio_bytes):

    global model

    # Decode phone audio into a 16 kHz mono waveform
    samples = []
    total_samples = 0

    with av.open(io.BytesIO(audio_bytes)) as container:

        resampler = av.AudioResampler(
            format="s16",
            layout="mono",
            rate=16000
        )

        def collect(frames):

            nonlocal total_samples

            for frame in frames:
                data = frame.to_ndarray().flatten()

                total_samples += data.size

                if total_samples > 16000 * 35:
                    raise ValueError("Recording is too long.")

                samples.append(data)

        for frame in container.decode(audio=0):
            collect(resampler.resample(frame))

        collect(resampler.resample(None))

    if not samples:
        return ""

    audio = np.concatenate(samples)
    audio = audio.astype(np.float32) / 32768.0

    with model_lock:

        if model is None:

            print("Loading Atlas mobile speech recognition...")

            model = WhisperModel(
                "base.en",
                device="cpu",
                compute_type="int8"
            )

        segments, _ = model.transcribe(
            audio,
            language="en",
            beam_size=1,
            vad_filter=True
        )

        return " ".join(
            segment.text.strip()
            for segment in segments
        ).strip()