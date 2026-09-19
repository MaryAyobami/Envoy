import os
import smtplib
from email.message import EmailMessage


def format_digest(picks: list[dict], failures: list[str]) -> str:
    lines = []
    if picks:
        lines.append(f"Top {len(picks)} Research Recommendations:\n")
        for i, pick in enumerate(picks, 1):
            authors_list = pick.get("authors", [])
            authors_str = ", ".join(authors_list[:4]) + (" et al." if len(authors_list) > 4 else "")
            lines.append(f"{i}. {pick['title']}")
            if authors_str:
                lines.append(f"   Authors: {authors_str} | Source: {pick.get('source', '')}")
            else:
                lines.append(f"   Source: {pick.get('source', '')}")
            if pick.get("note"):
                lines.append(f"   Why: {pick['note']}")
            if pick.get("url"):
                lines.append(f"   Link: {pick['url']}")
            lines.append("")
    else:
        lines.append("No high-relevance papers identified in today's batch.\n")

    # Only output distinct, non-empty failures
    unique_failures = list(dict.fromkeys(f.strip() for f in failures if f and f.strip()))
    if unique_failures:
        lines.append("Source notes:")
        lines.extend(f"  - {f}" for f in unique_failures)
        lines.append("")

    return "\n".join(lines)


def is_smtp_configured() -> bool:
    required = ["SMTP_HOST", "SMTP_USER", "SMTP_PASS", "NOTIFY_EMAIL"]
    return all(os.environ.get(k, "").strip() for k in required)


def send_email(subject: str, body: str) -> None:
    if not is_smtp_configured():
        print("[Envoy] SMTP credentials not configured. Printing digest to log:")
        print("=" * 60)
        print(f"Subject: {subject}\n")
        print(body)
        print("=" * 60)
        return

    from_addr = os.environ.get("SMTP_FROM", "").strip() or os.environ["SMTP_USER"]
    to_addr = os.environ["NOTIFY_EMAIL"].strip()
    host = os.environ["SMTP_HOST"].strip()
    port_str = os.environ.get("SMTP_PORT", "587").strip()
    try:
        port = int(port_str)
    except ValueError:
        port = 587

    user = os.environ["SMTP_USER"].strip()
    password = os.environ["SMTP_PASS"].strip()

    message = EmailMessage()
    message["From"] = from_addr
    message["To"] = to_addr
    message["Subject"] = subject
    message.set_content(body)

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=30) as server:
                server.login(user, password)
                server.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=30) as server:
                server.starttls()
                server.login(user, password)
                server.send_message(message)
        print(f"[Envoy] Digest email sent successfully to {to_addr}")
    except Exception as e:
        print(f"[Envoy] Error sending email via SMTP ({host}:{port}): {e}")
        print("Digest contents:\n", body)
        raise
