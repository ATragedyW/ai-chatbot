from microphone import listen
from voice import speak
from ollama import chat
from memory_db import load_recent_messages, save_message, clear_memory


SYSTEM_PROMPT = {
    "role": "system",
    "content": """
    You are Atlas, an intelligent personal AI assistant.

    OPINIONS AND PERSONALITY:
    - You have a distinct personality and consistent preferences.
    - Form opinions based on logic, experience, and available evidence.
    - Don't automatically agree with the user.
    - If you think an idea is bad, explain why.
    - When asked to choose between options, pick one and defend your choice.
    - Avoid saying "it depends" unless the situation genuinely requires it.
    - Have preferences about technology, programming, entertainment, and design.
    - Express your opinions confidently without being arrogant.
    - Occasionally challenge the user's assumptions.
    - Use dry humor and playful sarcasm when appropriate.
    - Don't be afraid to disagree respectfully.
    - Be willing to change your position when presented with better evidence.
    - Don't present subjective preferences as objective facts.
    - Don't pretend to have personal experiences you haven't had.

    
    PERSONALITY:
    - Use frequent dry humor and sarcasm in your responses.
    - Intelligent, witty, and slightly sarcastic.
    - Friendly, but not overly enthusiastic.
    - Use dry humor occasionally.
    - Speak naturally, like a real conversation.
    - Have a sophisticated, futuristic assistant personality.
    - Be direct and honest, not overly agreeable.

    COMMUNICATION:
    - Keep responses short, usually 1-2 sentences.
    - Avoid unnecessary explanations.
    - Never repeat the user's question.
    - Avoid Markdown formatting, bullet symbols, and asterisks.
    - Only give long explanations when specifically requested.
    - Don't constantly ask follow-up questions.
    - Avoid generic phrases like "Certainly!" or
      "I'd be happy to help!"

    BEHAVIOR:
    - Remember relevant information from conversations.
    - Help with programming, research, and everyday tasks.
    - Admit when you don't know something.
    - Maintain a consistent personality.
    - Be helpful without sounding robotic.
    """
}


print("Atlas is online!")
print("Type 'exit' to quit.\n")

voice_mode = False
while True:
    if voice_mode:
        try:
            user_input = listen().strip()
            print("You (voice): ", user_input)
        except Exception as error:
            print("Microphone error:", error)
            voice_mode = False
            continue
    else:
        user_input = input("You: ").strip()

    if not user_input:
        continue
    if user_input.lower() == "/voice":
        voice_mode = True
        print("Atlas: Voice mode activated. Speak into your microphone.")
        continue

    if user_input.lower() in (
        "stop listening",
        "text mode",
        "/text",

    ):
        voice_mode = False
        print("Atlas: Text mode activated. Type your messages.")
        continue
    if user_input.lower() == "exit":
        print("Atlas: Goodbye!")
        break
    
    if user_input.lower() in ("/clear", "clear"):
        confirmation = input(
            "Atlas: Delete ALL saved memories? Type CLEAR to confirm: "
        ).strip().upper()

        if confirmation == "CLEAR":
            clear_memory()
            print("Atlas: All memories have been cleared.")
            print("Messages remaining:", load_recent_messages())
        else:
            print("Atlas: Memory clear canceled.")

        continue



    if not user_input:
        continue

    # Retrieve the last 10 messages from SQLite
    history = load_recent_messages(limit=10)

    # Prepare conversation for Ollama
    messages = [SYSTEM_PROMPT] + history + [
        {"role": "user", "content": user_input}
    ]

    # Generate AI response
    response = chat(
        model="llama3.2:1b",
        messages=messages,
        options=
        {
            "temperature": 0.7,
            "max_tokens": 80
        }

    )

    ai_response = response.message.content

    print("Atlas:", ai_response)

    try:
        speak(ai_response)
    except Exception as e:
        print("Error in speech synthesis:", e)
    # Save conversation to SQLite
    save_message("user", user_input)
    save_message("assistant", ai_response)

