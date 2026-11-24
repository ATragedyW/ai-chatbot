import re
from microphone import listen

def wait_for_wake_word():
    print("Atlas is on standby...")

    while True:
        try:
            text = listen(silent=True)

            if not text:
                continue

            print("Detected speech:", text)

            text = re.sub(r"[^\w\s]", "", text.lower())
            text = " ".join(text.split())

            if "hey atlas" in text:
                print("Wake word detected!")
                return True

        except Exception as error:
            print("Wake word error:", error)