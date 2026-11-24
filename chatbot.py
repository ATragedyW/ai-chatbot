from ollama import chat
import json
from pathlib import Path

MEMORY_FILE = Path(__file__).with_name("memory.json")

SYSTEM_PROMPT = {
    "role": "system",
    "content": """
    You are Atlas, a friendly AI assistant.
    You are professional, intelligent, and helpful.
    You explain programming concepts clearly.
    """
}

# Load previous conversations
def load_memory():
    if MEMORY_FILE.exists():
        with open(MEMORY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    return []


# Save conversations
def save_memory(history):
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(history, file, indent=4)


history = load_memory()

print("Atlas is online!")
print("Type 'exit' to quit.\n")

while True:
    user_input = input("You: ")

    if user_input.lower() == "exit":
        print("Atlas: Goodbye!")
        break

    history.append({
        "role": "user",
        "content": user_input
    })

    response = chat(
        model="llama3.2:1b",
        messages=[SYSTEM_PROMPT] + history
    )

    ai_response = response.message.content

    print("Atlas:", ai_response)

    history.append({
        "role": "assistant",
        "content": ai_response
    })

    save_memory(history)