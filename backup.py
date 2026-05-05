"""Database backup via pg_dump, emailed as attachment."""
import os
import smtplib
import subprocess
from datetime import datetime
from email.message import EmailMessage


def create_backup(database_url):
    """Run pg_dump and return the SQL bytes."""
    result = subprocess.run(
        ['pg_dump', database_url, '--no-owner', '--no-acl'],
        capture_output=True, timeout=120
    )
    if result.returncode != 0:
        raise RuntimeError(f"pg_dump failed: {result.stderr.decode()}")
    return result.stdout


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
