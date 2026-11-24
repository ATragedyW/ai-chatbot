import json
import os
from pathlib import Path

STATE_DIR = Path(
    os.getenv("LOCALAPPDATA", str(Path.home()))
) / "Atlas"

STATE_FILE = STATE_DIR / "mental_state.json"

MODES = (
    "normal",
    "focus",
    "serious",
    "sarcastic"
)

MOODS = (
    "calm",
    "curious",
    "amused",
    "concerned",
    "confident"
)

VOICE_STATES = ("on", "off")

DEFAULT_STATE = {
    "mode": "normal",
    "mood": "calm",
    "voice": "on"
}


def load_state():

    state = DEFAULT_STATE.copy()

    if STATE_FILE.exists():
        try:
            saved = json.loads(
                STATE_FILE.read_text(encoding="utf-8")
            )

            if saved.get("mode") in MODES:
                state["mode"] = saved["mode"]

            if saved.get("mood") in MOODS:
                state["mood"] = saved["mood"]

            if saved.get("voice") in VOICE_STATES:
                state["voice"] = saved["voice"]

        except (OSError, ValueError, AttributeError) as error:
            print("State loading error:", error)

    return state


def save_state(state):

    STATE_DIR.mkdir(parents=True, exist_ok=True)

    temporary_file = STATE_FILE.with_suffix(".tmp")

    temporary_file.write_text(
        json.dumps(state, indent=4),
        encoding="utf-8"
    )

    temporary_file.replace(STATE_FILE)
    # Initialize Atlas's internal state on first launch
if not STATE_FILE.exists():
    save_state(DEFAULT_STATE)
    print("Atlas mental state initialized.")