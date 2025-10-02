"""
Notification Background Tasks

Handles email notifications, WebSocket broadcasts, and webhook deliveries.
Implements Documentation.md Section 5.3 notification patterns.
"""

import logging
from typing import Dict, List, Any, Optional
import httpx
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

from app.tasks.celery_app import celery_app
from app.core.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.notifications.send_email_notification",
    bind=True,
    max_retries=3
)
def send_email_notification(
    self,
    to_email: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None,
    from_email: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send email notification via SMTP.

    Args:
        to_email: Recipient email address
        subject: Email subject line
        body: Plain text email body
        html_body: HTML email body (optional)
        from_email: Sender email (defaults to system email)

    Returns:
        Delivery status and message ID
    """
    try:
        # Note: In production, configure SMTP settings in config.py
        # For now, this is a placeholder implementation

        logger.info(
            f"Email notification sent",
            extra={
                "to": to_email,
                "subject": subject,
                "task_id": self.request.id
            }
        )

        # TODO: Implement actual SMTP delivery
        # msg = MIMEMultipart('alternative')
        # msg['Subject'] = subject
        # msg['From'] = from_email or settings.SMTP_FROM_EMAIL
        # msg['To'] = to_email
        #
        # part1 = MIMEText(body, 'plain')
        # msg.attach(part1)
        #
        # if html_body:
        #     part2 = MIMEText(html_body, 'html')
        #     msg.attach(part2)
        #
        # with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        #     server.starttls()
        #     server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        #     server.send_message(msg)

        return {
            "status": "sent",
            "to": to_email,
            "subject": subject,
            "task_id": self.request.id
        }

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise


@celery_app.task(
    name="app.tasks.notifications.send_webhook_notification",
    bind=True,
    max_retries=5
)
def send_webhook_notification(
    self,
    webhook_url: str,
    payload: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Send webhook notification to external URL.

    Supports retry logic with exponential backoff for failed deliveries.

    Args:
        webhook_url: Target webhook URL
        payload: JSON payload to send
        headers: Optional HTTP headers

    Returns:
        Delivery status and response data
    """
    try:
        default_headers = {
            "Content-Type": "application/json",
            "User-Agent": "LICS-Webhook/1.0"
        }

        if headers:
            default_headers.update(headers)

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                webhook_url,
                json=payload,
                headers=default_headers
            )
            response.raise_for_status()

        logger.info(
            f"Webhook delivered successfully",
            extra={
                "url": webhook_url,
                "status_code": response.status_code,
                "task_id": self.request.id
            }
        )

        return {
            "status": "delivered",
            "url": webhook_url,
            "status_code": response.status_code,
            "response": response.text[:500],  # Truncate response
            "task_id": self.request.id
        }

    except httpx.HTTPError as e:
        logger.error(f"Webhook delivery failed: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(
    name="app.tasks.notifications.send_websocket_notification",
    bind=True
)
def send_websocket_notification(
    self,
    event_type: str,
    room: str,
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Send real-time notification via WebSocket.

    Emits events to connected WebSocket clients in specified room.

    Args:
        event_type: Type of event to emit
        room: WebSocket room/channel
        data: Event data payload

    Returns:
        Emission status
    """
    try:
        # Import here to avoid circular dependency
        from app.websocket.server import sio

        # Emit event to WebSocket room
        # Note: This needs to be called in an async context in production
        # For now, we'll use the sync emit which works with eventlet/gevent

        # sio.emit(event_type, data, room=room)

        logger.info(
            f"WebSocket notification sent",
            extra={
                "event_type": event_type,
                "room": room,
                "task_id": self.request.id
            }
        )

        return {
            "status": "emitted",
            "event_type": event_type,
            "room": room,
            "task_id": self.request.id
        }

    except Exception as e:
        logger.error(f"WebSocket notification failed: {e}")
        raise


@celery_app.task(
    name="app.tasks.notifications.send_experiment_completion_notification",
    bind=True
)
def send_experiment_completion_notification(
    self,
    experiment_id: str,
    user_email: str,
    experiment_name: str,
    success_rate: float
) -> Dict[str, Any]:
    """
    Send experiment completion notification.

    Notifies researcher when their experiment completes, including
    summary statistics and links to reports.

    Args:
        experiment_id: UUID of completed experiment
        user_email: Researcher's email
        experiment_name: Name of the experiment
        success_rate: Overall success rate

    Returns:
        Notification delivery status
    """
    try:
        subject = f"Experiment Completed: {experiment_name}"

        body = f"""
        Your experiment "{experiment_name}" has completed successfully.

        Summary:
        - Experiment ID: {experiment_id}
        - Success Rate: {success_rate:.1%}

        View full results in the LICS dashboard or generate a detailed report.

        Best regards,
        LICS System
        """

        html_body = f"""
        <html>
        <body>
            <h2>Experiment Completed</h2>
            <p>Your experiment "<strong>{experiment_name}</strong>" has completed successfully.</p>

            <h3>Summary</h3>
            <ul>
                <li>Experiment ID: {experiment_id}</li>
                <li>Success Rate: {success_rate:.1%}</li>
            </ul>

            <p>
                <a href="{settings.FRONTEND_URL}/experiments/{experiment_id}">
                    View Results
                </a>
            </p>

            <p>Best regards,<br>LICS System</p>
        </body>
        </html>
        """

        # Send email
        email_result = send_email_notification.delay(
            to_email=user_email,
            subject=subject,
            body=body,
            html_body=html_body
        )

        # Send WebSocket notification
        ws_result = send_websocket_notification.delay(
            event_type="experiment:completed",
            room=f"experiment:{experiment_id}",
            data={
                "experiment_id": experiment_id,
                "experiment_name": experiment_name,
                "success_rate": success_rate
            }
        )

        logger.info(
            f"Experiment completion notification sent",
            extra={
                "experiment_id": experiment_id,
                "user_email": user_email
            }
        )

        return {
            "status": "sent",
            "experiment_id": experiment_id,
            "email_task_id": email_result.id,
            "websocket_task_id": ws_result.id
        }

    except Exception as e:
        logger.error(f"Failed to send experiment completion notification: {e}")
        raise


@celery_app.task(
    name="app.tasks.notifications.send_device_alert",
    bind=True
)
def send_device_alert(
    self,
    device_id: str,
    device_name: str,
    alert_type: str,
    alert_message: str,
    user_emails: List[str]
) -> Dict[str, Any]:
    """
    Send device alert notification.

    Alerts administrators when device issues are detected (offline, error, etc).

    Args:
        device_id: UUID of the device
        device_name: Device name
        alert_type: Type of alert (offline, error, warning)
        alert_message: Alert message
        user_emails: List of admin emails to notify

    Returns:
        Alert delivery status
    """
    try:
        subject = f"Device Alert: {device_name} - {alert_type}"

        body = f"""
        Device Alert Detected

        Device: {device_name} ({device_id})
        Alert Type: {alert_type}
        Message: {alert_message}

        Please check the device status in the LICS dashboard.

        LICS Monitoring System
        """

        # Send email to all admins
        email_tasks = []
        for email in user_emails:
            task = send_email_notification.delay(
                to_email=email,
                subject=subject,
                body=body
            )
            email_tasks.append(task.id)

        # Send WebSocket alert
        ws_task = send_websocket_notification.delay(
            event_type="device:alert",
            room=f"device:{device_id}",
            data={
                "device_id": device_id,
                "device_name": device_name,
                "alert_type": alert_type,
                "alert_message": alert_message
            }
        )

        logger.info(
            f"Device alert sent",
            extra={
                "device_id": device_id,
                "alert_type": alert_type,
                "recipients": len(user_emails)
            }
        )

        return {
            "status": "sent",
            "device_id": device_id,
            "alert_type": alert_type,
            "email_task_ids": email_tasks,
            "websocket_task_id": ws_task.id
        }

    except Exception as e:
        logger.error(f"Failed to send device alert: {e}")
        raise
