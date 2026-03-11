import smtplib
import sqlite3
from email.message import EmailMessage
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone

from config import (
    SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_RECEIVER
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_posted_text(company: str, title: str) -> str:
    """Look up the timestamp from jobs.db and return a human-readable time-ago string."""
    try:
        conn = sqlite3.connect("jobs.db")
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp FROM jobs WHERE company = ? AND title = ? ORDER BY id DESC LIMIT 1", (company, title))
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            job_time = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            diff = now - job_time
            hours = int(diff.total_seconds() / 3600)
            if hours < 1:
                return "Just now"
            elif hours < 24:
                return f"{hours} hours ago"
            else:
                return job_time.strftime("%b %d, %Y")
    except Exception:
        pass
    return "Recent"

def format_job_html(job: Dict[str, Any], index: int) -> str:
    """Formats a single job into an HTML row/block."""
    title = job.get('title', 'Unknown Title')
    company = job.get('company', 'Unknown Company')
    location = job.get('location', 'Unknown Location')
    score = job.get('score', 0)
    apply_link = job.get('apply_link', 'No link provided')
    experience = job.get('experience_level', 'Entry Level')
    
    posted_at = get_posted_text(company, title)
    
    analysis = job.get('analysis', {})
    visa_status = analysis.get('visa_sponsorship', 'Unknown')
    
    return f"""
    <div style="border-bottom: 1px solid #ddd; padding: 15px 0;">
        <h3 style="margin-bottom: 5px; color: #333;">#{index} - {title} @ <strong style="color: #000;">{company}</strong></h3>
        <p style="margin: 2px 0;"><strong>📍 Location:</strong> {location}</p>
        <p style="margin: 2px 0;"><strong>🎓 Experience:</strong> {experience}</p>
        <p style="margin: 2px 0;"><strong>🌎 Visa:</strong> {visa_status}</p>
        <p style="margin: 2px 0;"><strong>⭐ Score:</strong> {score}/30</p>
        <p style="margin: 2px 0;"><strong>📅 Posted:</strong> {posted_at}</p>
        <p style="margin-top: 15px;">
            <a href="{apply_link}" style="background-color: #28a745; color: white; padding: 10px 15px; text-decoration: none; border-radius: 4px; font-weight: bold; font-family: sans-serif;">APPLY NOW</a>
        </p>
    </div>
    """

def send_email(subject: str, html_body: str):
    """Sends an HTML email via SMTP."""
    target_email = "rathi.chetanya@gmail.com"
    
    if not all([SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD]):
        logging.error("❌ SMTP configuration is incomplete. Skipping email notification.")
        return

    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = SMTP_USERNAME
        msg['To'] = target_email
        msg.set_content("Please enable HTML viewing to see the job matches.")
        msg.add_alternative(html_body, subtype='html')

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
            logging.info(f"✅ Email notification sent successfully to {target_email}.")
    except Exception as e:
        logging.error(f"❌ Failed to send email: {e}")

def notify(jobs: List[Dict[str, Any]]):
    """Generates the daily HTML digest and triggers email notification."""
    if not jobs:
        logging.info("No new jobs to notify about.")
        return

    logging.info(f"Preparing to notify about {len(jobs)} jobs...")
    
    today_str = datetime.now().strftime("%B %d, %Y")
    subject = f"🚀 [{len(jobs)}] Fresh Jobs Found – Apply Now | {today_str}"
    
    header = f"<h2 style='color: #333; font-family: sans-serif;'>🚀 Autonomous Job Hunter</h2><p style='font-family: sans-serif; font-size: 16px;'><strong>{len(jobs)} jobs found matching your profile</strong></p><hr style='border: 1px solid #eee;'>"
    
    jobs_html = "".join([format_job_html(j, idx+1) for idx, j in enumerate(jobs)])
    
    full_html = f"""
    <html>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #444; max-width: 650px; margin: 0 auto; line-height: 1.5;">
            {header}
            {jobs_html}
            <p style="margin-top: 30px; color: #888; font-size: 12px; text-align: center;">Automated by your Autonomous Job Hunter Bot 🤖</p>
        </body>
    </html>
    """
    
    send_email(subject, full_html)
