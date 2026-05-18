"""Database backup via sqlite3 dump, emailed as attachment."""
import os
import smtplib
import sqlite3
from datetime import datetime
from email.message import EmailMessage


def create_backup(database_url):
    """Dump the SQLite database and return the SQL bytes."""
    db_path = database_url.replace('sqlite:///', '')
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.path.dirname(__file__), 'instance', db_path)

    lines = []
    with sqlite3.connect(db_path) as con:
        for line in con.iterdump():
            lines.append(line)
    return '\n'.join(lines).encode('utf-8')


def send_backup_email(sql_bytes):
    """Email the backup as a .sql attachment."""
    smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_pass = os.environ.get('SMTP_PASS', '')
    backup_email = os.environ.get('BACKUP_EMAIL', '')

    if not all([smtp_user, smtp_pass, backup_email]):
        raise RuntimeError(
            "Missing SMTP config. Set SMTP_USER, SMTP_PASS, and BACKUP_EMAIL env vars."
        )

    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
    filename = f"parts_inventory_backup_{timestamp}.sql"

    msg = EmailMessage()
    msg['Subject'] = f'Parts Inventory Backup — {timestamp}'
    msg['From'] = smtp_user
    msg['To'] = backup_email
    msg.set_content(
        f'Automated backup of the parts inventory database.\n'
        f'Generated: {timestamp}\n'
        f'Size: {len(sql_bytes) / 1024:.1f} KB'
    )
    msg.add_attachment(sql_bytes, maintype='application', subtype='sql', filename=filename)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)

    return filename
