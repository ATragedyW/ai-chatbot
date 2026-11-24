
from atlas_config import MODEL, MEMORY_LIMIT, SYSTEM_PROMPT
import re
import time

from wake_word import wait_for_wake_word
from microphone import listen
from voice import speak
from ollama import chat
from memory_db import load_recent_messages, save_message, clear_memory


# ==========================================
# ATLAS CONFIGURATION
# ==========================================


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def normalize_command(text):
    text = text.lower().strip()
    text = text.replace("’", "'")
    text = re.sub(r"[^\w\s/']", " ", text)
    return " ".join(text.split())


def atlas_speak(text):
    print("Atlas:", text)

    try:
        speak(text)
    except Exception as error:
        print("Speech synthesis error:", error)


def generate_response(user_input):

    history = load_recent_messages(limit=MEMORY_LIMIT)

    messages = [SYSTEM_PROMPT] + history + [
        {"role": "user", "content": user_input}
    ]

    start_time = time.perf_counter()

    response = chat(
        model=MODEL,
        messages=messages,
        options={
            "temperature": 0.9,
            "num_predict": 80,
            "top_p": 0.95,
            "repeat_penalty": 1.1
        }
    )

    elapsed = time.perf_counter() - start_time

    print(f"Response generated in {elapsed:.2f}s")

    return response.message.content.strip()


# ==========================================
# MAIN APPLICATION
# ==========================================

def main():

    print("Atlas is online!")
    print("Say 'Hey Atlas' to begin.")
    print("Press Ctrl+C to quit.\n")

    voice_mode = True
    conversation_active = True

    while True:

        # ==================================
        # USER INPUT
        # ==================================

        if voice_mode:
            try:
                if not conversation_active:

                    wait_for_wake_word()

                    conversation_active = True
                    atlas_speak("Yes?")

                user_input = listen().strip()

                if not user_input:
                    continue

                print("You (voice):", user_input)

            except Exception as error:
                print("Microphone error:", error)
                time.sleep(1)
                continue

        else:
            user_input = input("You: ").strip()

        if not user_input:
            continue

        command = normalize_command(user_input)


        # ==================================
        # STANDBY COMMANDS
        # ==================================

        if command in (
            "go to sleep",
            "goodbye atlas",
            "standby",
            "that's all",
            "thats all",
            "atlas go to sleep",
            "go to sleep atlas"
        ):
            conversation_active = False
            voice_mode = True

            atlas_speak("Finally, some peace and quiet.")
            continue


        # ==================================
        # TEXT MODE
        # ==================================

        if command in (
            "stop listening",
            "text mode",
            "/text"
        ):
            voice_mode = False
            conversation_active = False

            print("Atlas: Text mode activated.")
            continue


        # ==================================
        # VOICE MODE
        # ==================================

        if command in (
            "/voice",
            "voice mode",
            "start listening"
        ):
            voice_mode = True
            conversation_active = False

            print("Atlas: Voice mode activated.")
            continue


        # ==================================
        # SHUTDOWN
        # ==================================

        if command in (
            "exit",
            "quit",
            "shutdown atlas",
            "shut down atlas",
            "atlas shut down"
        ):
            atlas_speak("Goodbye. Try not to break anything.")
            break


        # ==================================
        # MEMORY MANAGEMENT
        # ==================================

        if command in (
            "/clear",
            "clear",
            "clear memory"
        ):
            confirmation = input(
                "Delete ALL saved memories? "
                "Type CLEAR to confirm: "
            ).strip().upper()

            if confirmation == "CLEAR":
                clear_memory()
                atlas_speak("Memory cleared.")
            else:
                print("Atlas: Memory clear canceled.")

            continue


        # ==================================
        # AI RESPONSE
        # ==================================

        try:
            print("Atlas is thinking...")

            ai_response = generate_response(user_input)

            if not ai_response:
                print("Atlas returned an empty response.")
                continue

        except Exception as error:
            print("Ollama error:", error)
            continue


        # ==================================
        # SAVE CONVERSATION
        # ==================================

        try:
            save_message("user", user_input)
            save_message("assistant", ai_response)

        except Exception as error:
            print("Memory error:", error)


        # ==================================
        # SPEAK RESPONSE
        # ==================================

        atlas_speak(ai_response)


# ==========================================
# PROGRAM ENTRY POINT
# ==========================================

if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        print("\nAtlas: Shutting down.")
