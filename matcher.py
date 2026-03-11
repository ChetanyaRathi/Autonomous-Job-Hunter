import sqlite3
import logging
from typing import List, Dict, Any
from config import USER_PROFILE, SCORING_WEIGHTS, MIN_SCORE_THRESHOLD

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_NAME = "jobs.db"

def init_db():
    """Initializes the SQLite database with the jobs table to track duplicates."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            title TEXT,
            location TEXT,
            apply_link TEXT,
            score INTEGER,
            visa TEXT,
            pipeline_run_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(company, title, location)
        )
    ''')
    # Auto-migrate older schemas
    for col, default in [("visa", "'Unknown'"), ("pipeline_run_id", "'unknown'")]:
        try:
            cursor.execute(f"ALTER TABLE jobs ADD COLUMN {col} TEXT DEFAULT {default}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()

def job_exists(company: str, title: str, location: str) -> bool:
    """Checks if a job already exists in the database based on company, title, and location."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id FROM jobs WHERE company = ? AND title = ? AND location = ?
    ''', (company, title, location))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def save_job(job: Dict[str, Any], run_id: str = "unknown"):
    """Saves a matched job to the database."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO jobs (company, title, location, apply_link, score, visa, pipeline_run_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            job['company'], job['title'], job['location'], job['apply_link'],
            job['score'],
            job.get('analysis', {}).get('visa_sponsorship', 'Unknown'),
            run_id
        ))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Job already exists
    except Exception as e:
        logging.error(f"Error saving job to DB: {e}")
    finally:
        conn.close()

def score_job(job: Dict[str, Any], analysis: Dict[str, Any]) -> int:
    """
    Scores the job using base SCORING_WEIGHTS plus explicit boosts.
    """
    score = 0
    
    # 1. Skills Match
    user_skills = set(s.lower() for s in USER_PROFILE["skills"])
    job_skills = set(s.lower() for s in analysis.get("required_skills", []))
    job_stack = set(s.lower() for s in analysis.get("tech_stack", []))
    combined_job_tech = job_skills.union(job_stack)
    
    if combined_job_tech and user_skills:
        match_ratio = len(user_skills.intersection(combined_job_tech)) / len(user_skills)
        score += int(match_ratio * SCORING_WEIGHTS["skills"])

    # 2. Experience Match
    job_exp = analysis.get("experience_level", "").lower()
    user_exp = USER_PROFILE["experience_level"].lower()
    if user_exp in job_exp or "entry" in job_exp or "junior" in job_exp:
        score += SCORING_WEIGHTS["experience"]
    elif "unknown" in job_exp:
        score += int(SCORING_WEIGHTS["experience"] / 2)

    # 3. Location Match 
    job_loc_analysis = analysis.get("location", "").lower()
    job_loc = job.get("location", "").lower()
    user_loc = USER_PROFILE["location"].lower()
    
    is_remote_job = "remote" in job_loc_analysis or "remote" in job_loc
    
    if user_loc in job_loc_analysis or user_loc in job_loc:
        score += SCORING_WEIGHTS["location"]
    elif USER_PROFILE["remote"] and is_remote_job:
        score += SCORING_WEIGHTS["location"]
    elif "unknown" in job_loc_analysis and "unknown" in job_loc:
        score += int(SCORING_WEIGHTS["location"] / 2)

    # 4. Visa Sponsorship Match
    visa_status = analysis.get("visa_sponsorship", "Unknown")
    if USER_PROFILE["visa_sponsorship_required"]:
        if visa_status == "Likely":
            score += SCORING_WEIGHTS["visa"]
        elif visa_status == "Unknown":
            score += int(SCORING_WEIGHTS["visa"] / 2)
    else:
        score += SCORING_WEIGHTS["visa"]

    # === EXPLICIT BOOSTS ===
    title_lower = job.get("title", "").lower()
    
    # +8 for entry-level title keywords
    entry_keywords = ["new grad", "entry level", "junior", "intern", "0-1 years", "recent graduate", "university"]
    if any(kw in title_lower for kw in entry_keywords):
        score += 8

    # -10 for senior title keywords
    senior_keywords = ["senior", "staff", "lead", "principal"]
    if any(kw in title_lower for kw in senior_keywords):
        score -= 10

    # +5 if visa is Likely
    if visa_status == "Likely":
        score += 5
    
    # +3 if remote
    if is_remote_job:
        score += 3

    return max(score, 0)

def _is_senior_job(job: Dict[str, Any]) -> bool:
    """Returns True if the job should be filtered out as too senior."""
    analysis = job.get('analysis', {})
    exp_level = analysis.get("experience_level", "").lower()
    
    if "senior" in exp_level or "mid" in exp_level:
        return True
    
    desc = job.get("description", "").lower()
    senior_desc_phrases = [
        "4+ years", "5+ years", "6+ years", "7+ years",
        "4 years of experience", "5 years of experience",
        "minimum 3 years", "at least 3 years", "at least 4 years"
    ]
    if any(phrase in desc for phrase in senior_desc_phrases):
        return True
    
    return False

def filter_and_match(jobs: List[Dict[str, Any]], run_id: str = "unknown") -> List[Dict[str, Any]]:
    """
    Takes analyzed jobs, applies the scoring logic, filters out duplicates and senior jobs,
    and returns jobs meeting the threshold.
    """
    init_db()
    passed_jobs = []

    for job in jobs:
        if job_exists(job['company'], job['title'], job['location']):
            continue

        # Filter out senior-level jobs
        if _is_senior_job(job):
            continue

        job_score = score_job(job, job['analysis'])
        job['score'] = job_score

        if job_score >= MIN_SCORE_THRESHOLD:
            save_job(job, run_id)
            passed_jobs.append(job)
            
    passed_jobs.sort(key=lambda x: x['score'], reverse=True)
    
    if not passed_jobs:
        for job in jobs:
            if 'score' not in job:
                job['score'] = 0
        jobs.sort(key=lambda x: x.get('score', 0), reverse=True)
        return jobs
        
    return passed_jobs
