import os
import smtplib
from email.message import EmailMessage


def format_digest(picks: list[dict], failures: list[str]) -> str:
    lines = []
    for i, pick in enumerate(picks, 1):
        authors = ", ".join(pick["authors"][:4]) + (" et al." if len(pick["authors"]) > 4 else "")
        lines.append(f"{i}. {pick['title']}")
        if authors:
            lines.append(f"   {authors} - {pick['source']}")
        lines.append(f"   Why: {pick['note']}")
        lines.append(f"   {pick['url']}")
        lines.append("")
    if failures:
        lines.append("Source issues:")
        lines.extend(f"  - {f}" for f in failures)
    return "\n".join(lines) or "No new items today."


def send_email(subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = os.environ["SMTP_FROM"]
    message["To"] = os.environ["NOTIFY_EMAIL"]
    message["Subject"] = subject
    message.set_content(body)
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
        server.send_message(message)
