import time
from threading import Lock
from notifications import notify

last_notification = None
notification_cooldown = 60
action_lock = Lock()


def send_notification():

    global last_notification

    with action_lock:

        now = time.monotonic()

        if (
            last_notification is not None
            and now - last_notification < notification_cooldown
        ):
            return "I sent a notification recently."

        if notify():

            last_notification = time.monotonic()

            return "Notification sent successfully."

        return "I was unable to send the notification."


ACTIONS = {
    "send_notification": send_notification
}


def execute_action(action):

    if action not in ACTIONS:
        return "Unauthorized action."

    print("Atlas executing action:", action)

    return ACTIONS[action]()