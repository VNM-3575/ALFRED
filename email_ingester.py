from config.llm_config import get_llm
import os
import sys
import imaplib
import email
from email.header import decode_header
import psycopg2
from langchain_core.messages import HumanMessage

# Add project root to the system path so we can import ALFRED's config modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def ingest_and_categorize_emails(limit=10):
    print("📧 =========================================")
    print("📧 ALFRED: Email Ingestion & Categorization")
    print("📧 =========================================\n")

    imap_server = os.getenv("IMAP_SERVER", "imap.gmail.com")
    imap_port = int(os.getenv("IMAP_PORT", 993))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    db_url = os.getenv("DATABASE_URL")

    if not all([username, password, db_url]):
        print("❌ Missing required environment variables (SMTP_USERNAME, SMTP_PASSWORD, or DATABASE_URL).")
        return

    try:
        print("  -> Connecting to PostgreSQL...")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        print(f"  -> Connecting to IMAP server ({imap_server})...")
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        mail.login(username, password)
        mail.select("inbox")

        # Search only for UNSEEN (unread) emails
        status, messages = mail.search(None, "UNSEEN")
        if status != "OK":
            print("  ❌ Failed to search emails.")
            return

        email_ids = messages[0].split()
        if not email_ids:
            print("  📭 No unread emails found.")
            return

        email_ids = email_ids[-limit:]
        llm = get_llm(temperature=0.1)

        for e_id in reversed(email_ids):
            res, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    # Decode subject
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(
                            encoding if encoding else "utf-8", errors="ignore")

                    # Decode sender
                    sender, encoding = decode_header(msg.get("From"))[0]
                    if isinstance(sender, bytes):
                        sender = sender.decode(
                            encoding if encoding else "utf-8", errors="ignore")

                    # Extract body
                    body = "No plain text body found."
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition")):
                            body = part.get_payload(
                                decode=True).decode(errors="ignore")
                            break

                    print(f"\nProcessing Email from: {sender}")
                    print(f"Subject: {subject}")

                    # LLM Categorization
                    prompt = f"Analyze the following email and assign it a single-word category from this list: [Invoice, Newsletter, Urgent, Alert, Meeting, Inquiry, Spam, General]\n\nEmail Subject: {subject}\nEmail Body: {body[:2000]}\n\nRespond with ONLY the single-word category."
                    response = llm.invoke([HumanMessage(content=prompt)])
                    category = response.content.strip().replace('"', '').replace("'", "")
                    print(f"  -> Categorized as: {category}")

                    # Insert into PostgreSQL
                    cursor.execute(
                        "INSERT INTO categorized_emails (sender, subject, body, category) VALUES (%s, %s, %s, %s)",
                        (sender, subject, body, category)
                    )
                    print("  ✅ Saved to PostgreSQL.")

        conn.commit()
        cursor.close()
        conn.close()
        mail.logout()
        print("\n🎉 Email ingestion and categorization complete!")

    except Exception as e:
        print(f"\n❌ Error during email ingestion: {str(e)}")


if __name__ == "__main__":
    ingest_and_categorize_emails()
