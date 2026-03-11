import logging
from datetime import datetime
from scraper import scrape_all_jobs
from analyzer import analyze_job_description
from matcher import filter_and_match
from notifier import notify

# Disable default logging to terminal so our custom prints look clean
logging.getLogger().setLevel(logging.CRITICAL)

"""
CRON JOB SETUP INSTRUCTIONS

To run this pipeline every 6 hours automatically on a Unix/Linux/macOS system, you can set up a cron job.

1. Open your terminal.
2. Type: crontab -e
3. Add the following line to the file (replace with your absolute paths):

0 */6 * * * cd "/Users/chetanya/VS code/Autonomous-job-hunting" && /absolute/path/to/your/python main.py >> cron.log 2>&1

This tells cron to run `main.py` at minute 0 past every 6th hour, save output to cron.log, and append errors.
"""

def print_job_to_terminal(job: dict, index: int):
    """Prints a job neatly to the terminal."""
    company = job.get("company", "Unknown")
    role = job.get("title", "Unknown")
    location = job.get("location", "Unknown")
    score = job.get("score", 0)
    apply_link = job.get("apply_link", "")
    posted = job.get("posted_at", "Unknown")
    
    analysis = job.get('analysis', {})
    visa = analysis.get("visa_sponsorship", "Unknown")

    print(f"  #{index}")
    print(f"  Company   : {company}")
    print(f"  Role      : {role}")
    print(f"  Location  : {location}")
    print(f"  Posted    : {posted}")
    print(f"  Visa      : {visa}")
    print(f"  Score     : {score}/30")
    print(f"  ✅ APPLY  : {apply_link}")
    print("-" * 40)

def main():
    # Generate a unique run ID for this pipeline execution
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f">>> Starting Autonomous Job Hunter Pipeline (Run: {run_id}) <<<")

    # Step 1: Scrape Jobs
    raw_jobs = scrape_all_jobs()
    if not raw_jobs:
        print("No jobs found during scraping. Pipeline finished.")
        return

    # Step 2: Analyze Jobs with Gemini
    analyzed_jobs = []
    print(f"Analyzing {len(raw_jobs)} jobs with Google Gemini...")
    for num, job in enumerate(raw_jobs, 1):
        analysis = analyze_job_description(job['description'])
        job['analysis'] = analysis
        analyzed_jobs.append(job)

    # Step 3: Match, Score, and Deduplicate (pass run_id)
    matched_jobs = filter_and_match(analyzed_jobs, run_id)
    
    print(f"\nHere are ALL the jobs evaluated in this run:\n" + "="*40)
    
    for idx, job in enumerate(matched_jobs, 1):
        print_job_to_terminal(job, idx)

    # Step 4: Notify User
    if matched_jobs:
        print("Sending email digest...")
        notify(matched_jobs)
        print(f"\n✅ Done! {len(matched_jobs)} jobs found.\n   Email sent to rathi.chetanya@gmail.com")
    else:
        print(f"\n✅ Done! 0 jobs found today.")

if __name__ == "__main__":
    main()
