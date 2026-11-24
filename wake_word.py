from microphone import listen

def wait_for_wake_word():
    print("Atlas is on standby. Say 'Hey Atlas'.")

    while True:
        try:
            text = listen(silent=True).lower().strip()

            if "hey atlas" in text:
                return True

        except Exception:
            continue