import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import Settings, settings

logger = logging.getLogger(__name__)


class EmailNotificationService:
    def __init__(self, config: Settings = settings) -> None:
        self._config = config

    def send_task_assignment_email(
        self,
        *,
        recipient_email: str,
        recipient_name: str,
        task_id: int,
        task_title: str,
    ) -> None:
        if not self._config.smtp_enabled:
            logger.info(
                "task_assignment_email skipped reason=smtp_disabled "
                "task_id=%s recipient=%s",
                task_id,
                recipient_email,
            )
            return

        message = EmailMessage()
        safe_title = task_title.replace("\r", " ").replace("\n", " ")
        message["Subject"] = f"[TaskHub] Task mới được giao: {safe_title}"
        message["From"] = str(self._config.smtp_from_email)
        message["To"] = recipient_email
        message.set_content(
            f"Xin chào {recipient_name},\n\n"
            f"Bạn đã được giao task #{task_id}: {task_title}\n"
        )

        try:
            with smtplib.SMTP(
                self._config.smtp_host,
                self._config.smtp_port,
                timeout=self._config.smtp_timeout_seconds,
            ) as smtp:
                if self._config.smtp_use_tls:
                    smtp.starttls(context=ssl.create_default_context())
                if (
                    self._config.smtp_username is not None
                    and self._config.smtp_password is not None
                ):
                    smtp.login(
                        self._config.smtp_username,
                        self._config.smtp_password.get_secret_value(),
                    )
                smtp.send_message(message)
        except Exception:
            logger.exception(
                "task_assignment_email failed task_id=%s recipient=%s",
                task_id,
                recipient_email,
            )
            return

        logger.info(
            "task_assignment_email sent task_id=%s recipient=%s",
            task_id,
            recipient_email,
        )
