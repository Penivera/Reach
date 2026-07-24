# notifications.py
from firebase_admin import messaging

def send_job_notification(user_token: str, job_title: str, job_location: str, job_id: str):
    
    notification = messaging.Notification(
        title="New Job Nearby!",
        body=f"A new job '{job_title}' was posted near you in {job_location}"
    )

    webpush = messaging.WebpushConfig(
        notification=messaging.WebpushNotification(
            title="New Job Nearby!",
            body=f"A new job '{job_title}' was posted near you",
            icon="/icon.png"
        )
    )

    message = messaging.Message(
        notification=notification,
        webpush=webpush,
        token=user_token,
        data={"job_id": job_id, "type": "new_job"}
    )

    try:
        response = messaging.send(message)
        print("Notification sent successfully:", response)
        return True
    except Exception as e:
        print("Error sending notification:", e)
        return False
    
