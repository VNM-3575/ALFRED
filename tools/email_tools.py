import os
import imaplib
import email
import smtplib
from email.message import EmailMessage
from email.header import decode_header
from langchain_core.tools import tool


@tool
def read_incoming_emails(limit: int = 5, unread_only: bool = True) -> str:
    """
    Reads the most recent incoming emails from the configured email inbox via IMAP.
    Returns a formatted string containing the sender, subject, and body of the emails.
    """
    imap_server = os.getenv("IMAP_SERVER", "imap.gmail.com")
    imap_port = int(os.getenv("IMAP_PORT", 993))
    # Reusing the existing SMTP credentials for IMAP login
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")

    if not username or not password:
        return "Error: Email credentials (SMTP_USERNAME / SMTP_PASSWORD) are not configured."

    try:
        # Connect to the server
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        mail.login(username, password)
        mail.select("inbox")

        # Search for emails
        status, messages = mail.search(
            None, "UNSEEN" if unread_only else "ALL")
        if status != "OK":
            return "Failed to search emails."

        email_ids = messages[0].split()
        if not email_ids:
            return "No matching emails found in the inbox."

        # Get the most recent 'limit' emails
        email_ids = email_ids[-limit:]

        extracted_emails = []
        for e_id in reversed(email_ids):
            res, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    # Decode subject and sender
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(
                            encoding if encoding else "utf-8", errors="ignore")

                    sender, encoding = decode_header(msg.get("From"))[0]
                    if isinstance(sender, bytes):
                        sender = sender.decode(
                            encoding if encoding else "utf-8", errors="ignore")

                    # Extract the body text
                    body = "No plain text body found."
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition")):
                            body = part.get_payload(
                                decode=True).decode(errors="ignore")
                            break

                    extracted_emails.append(
                        f"From: {sender}\nSubject: {subject}\nBody:\n{body[:1000]}...\n")

        mail.logout()
        return "📬 Incoming Emails:\n\n" + "\n---\n".join(extracted_emails)

    except Exception as e:
        return f"Error reading emails: {str(e)}"


@tool
def send_email(to_email: str, subject: str, body: str) -> str:
    """
    Sends an email or replies to a specific address using the configured SMTP server.
    Use this to automatically reply to incoming emails.
    """
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USERNAME")
    smtp_pass = os.getenv("SMTP_PASSWORD")

    if not all([smtp_server, smtp_user, smtp_pass]):
        return "Error: SMTP credentials (SMTP_USERNAME / SMTP_PASSWORD) are not fully configured."

    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = smtp_user
        msg['To'] = to_email

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        return f"Successfully sent email to {to_email} with subject '{subject}'."
    except Exception as e:
        return f"Failed to send email: {str(e)}"
