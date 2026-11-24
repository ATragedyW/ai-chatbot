import secrets
import os
import hmac
from threading import Lock
from fastapi.responses import FileResponse
from pathlib import Path
from fastapi import Request
from starlette.concurrency import run_in_threadpool
from mobile_voice import transcribe_audio
from fastapi.responses import Response
from voice import generate_audio

import uvicorn

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field

from cognition import think
from atlas_config import SYSTEM_PROMPT, MEMORY_LIMIT

app = FastAPI(title="Atlas Mobile API")

ACCESS_KEY = os.getenv("ATLAS_ACCESS_KEY")

if not ACCESS_KEY:
    raise RuntimeError("Atlas access key is not configured.")

history = []
cognitive_lock = Lock()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    voice_auto: bool = False


@app.get("/")
def home():
    return FileResponse(
        Path(__file__).resolve().parent / "mobile.html"
    )
@app.get("/health")
def health():

    return{
        "name": "Atlas",
        "statu": "online",
        "version" : "1.0"
    }

@app.post("/chat")
def chat(
    request: ChatRequest,
    authorization: str = Header(default="")
):

    expected = f"Bearer {ACCESS_KEY}"

    if not hmac.compare_digest(
        authorization.encode(), expected.encode()
    ):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )

    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Empty message"
        )

    with cognitive_lock:

        messages = [
            SYSTEM_PROMPT,
            *history[-MEMORY_LIMIT:],
            {
                "role": "user",
                "content": message
            }
        ]

        try:
            reply, state = think(
                messages,
                allow_forgetting=not request.voice_auto
            )

        except Exception as error:
            print("Atlas server error:", error)

            raise HTTPException(
                status_code=500,
                detail="Atlas processing error"
            )

        history.append({
            "role": "user",
            "content": message
        })

        history.append({
            "role": "assistant",
            "content": reply
        })

        history[:] = history[-MEMORY_LIMIT:]

        return {
            "reply": reply,
            "state": state
        }

@app.post("/transcribe")
async def transcribe(
    request: Request,
    authorization: str = Header(default="")
):

    expected = f"Bearer {ACCESS_KEY}"

    if not hmac.compare_digest(
        authorization.encode(),
        expected.encode()
    ):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )

    audio = bytearray()

    async for chunk in request.stream():

        if len(audio) + len(chunk) > 5_000_000:
            raise HTTPException(
                status_code=413,
                detail="Recording too large"
            )

        audio.extend(chunk)

    if not audio:
        raise HTTPException(
            status_code=400,
            detail="Empty recording"
        )

    try:

        text = await run_in_threadpool(
            transcribe_audio,
            bytes(audio)
        )

        return {"text": text}

    except Exception as error:

        print("Mobile transcription error:", error)

        raise HTTPException(
            status_code=400,
            detail="Unable to process recording"
        )
class VoiceRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


@app.post("/speak")
def generate_voice(
    request: VoiceRequest,
    authorization: str = Header(default="")
):

    expected = f"Bearer {ACCESS_KEY}"

    if not hmac.compare_digest(
        authorization.encode(),
        expected.encode()
    ):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )

    try:

        audio = generate_audio(request.text)

        return Response(
            content=audio,
            media_type="audio/wav",
            headers={"Cache-Control": "no-store"}
        )

    except Exception as error:

        print("Voice generation error:", error)

        raise HTTPException(
            status_code=500,
            detail="Voice generation failed"
        )
if __name__ == "__main__":

    print("\nATLAS MOBILE SERVER")
    print("----------------------------")
    print("Access key:", ACCESS_KEY)
    print("----------------------------\n")

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000
    )