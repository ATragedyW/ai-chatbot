import os
import urllib.request


def notify():

    topic = os.getenv("ATLAS_NTFY_TOPIC")

    if not topic:
        print("Notification topic is not configured.")
        return False

    request = urllib.request.Request(
        f"https://ntfy.sh/{topic}",
        data=b"Atlas has an update for you.",
        headers={
            "Title": "Atlas",
            "Priority": "4",
            "Tags": "robot"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=10
        ) as response:

            print("Atlas notification sent.")
            return True

    except Exception as error:
        print("Notification error:", error)
        return False


if __name__ == "__main__":
    notify()