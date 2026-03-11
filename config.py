import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

# User Profile Profile
USER_PROFILE = {
    "name": "Chetanya Rathi",
    "role": "Software Engineer",
    "skills": ["Python", "React", "Node.js", "Machine Learning", "AWS"],
    "experience_level": "Entry Level",
    "location": "USA",
    "visa_sponsorship_required": True,
    "job_type": ["Full-time", "Internship"],
    "remote": True
}

# Job Sources to try to scrape from (e.g., via SerpAPI Google Jobs)
JOB_SOURCES = [
    "LinkedIn",
    "Indeed",
    "Wellfound",
    "Greenhouse"
]

# Scoring Weights (Total = 30 points max)
# You can adjust these to change the matching algorithm's priorities
SCORING_WEIGHTS = {
    "skills": 10,       # Up to 10 points for matching skills
    "experience": 8,    # Up to 8 points for experience match
    "location": 6,      # Up to 6 points for location match
    "visa": 6           # Up to 6 points for sponsorship
}

MIN_SCORE_THRESHOLD = 5
