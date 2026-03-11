import os
import json
import requests
import logging
from typing import List, Dict, Any
from config import SERPER_API_KEY, USER_PROFILE

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Queries designed to target real company career pages via Google Serper
SEARCH_QUERIES = [
    '"software engineer" "entry level" "visa sponsorship" "apply" -site:indeed.com -site:ziprecruiter.com -site:linkedin.com -site:glassdoor.com -site:simplyhired.com -site:monster.com -site:dice.com -site:wellfound.com -site:jooble.org -site:careerbuilder.com -site:reddit.com -site:youtube.com -site:instagram.com -site:facebook.com -site:migratemate.co -site:jobright.ai',

    '"software engineer" "new grad" "we sponsor" OR "sponsorship provided" OR "H1B" OR "OPT" "apply" -site:indeed.com -site:ziprecruiter.com -site:linkedin.com -site:glassdoor.com -site:simplyhired.com',

    '"backend engineer" "entry level" "visa sponsorship" "careers" -site:indeed.com -site:ziprecruiter.com -site:linkedin.com -site:glassdoor.com -site:simplyhired.com',

    '"software engineer intern" "2026" "visa sponsorship" OR "we sponsor" "apply now" -site:indeed.com -site:ziprecruiter.com -site:linkedin.com -site:glassdoor.com',

    '"machine learning engineer" "entry level" "visa sponsorship" "careers" -site:indeed.com -site:ziprecruiter.com -site:linkedin.com',

    '"full stack engineer" "entry level" "H1B sponsorship" OR "visa sponsorship" "apply" -site:indeed.com -site:ziprecruiter.com -site:linkedin.com',

    '"python developer" "entry level" "visa sponsorship" "careers" -site:indeed.com -site:ziprecruiter.com -site:linkedin.com',

    'site:greenhouse.io "software engineer" "visa"',
    'site:greenhouse.io "software engineer" "entry level"',
    'site:greenhouse.io "software engineer" "intern" "2026"',
    'site:greenhouse.io "machine learning engineer"',
    'site:greenhouse.io "backend engineer" "entry level"',
    'site:lever.co "software engineer" "visa sponsorship"',
    'site:lever.co "software engineer" "entry level"',
    'site:lever.co "backend engineer" "entry level"',
    'site:lever.co "machine learning" "entry level"',
    'site:jobs.ashbyhq.com "software engineer" "entry level"',
    'site:jobs.ashbyhq.com "software engineer" "visa"',
    'site:careers.google.com "software engineer" "entry level"',
    'site:amazon.jobs "software engineer" "entry level"',
    'site:careers.microsoft.com "software engineer" "entry level"',
    'site:metacareers.com "software engineer"',
    'site:jobs.apple.com "software engineer" "entry level"',
    'site:stripe.com/jobs "engineer"',
    'site:grammarly.com/jobs "engineer" "entry level"',
]

def fetch_jobs_from_serper(query: str) -> List[Dict[str, Any]]:
    """
    Uses Serper /search endpoint and extracts jobs from the 'jobs' widget
    OR falls back to parsing 'organic' results.
    """
    if not SERPER_API_KEY:
        logging.warning("SERPER_API_KEY is missing.")
        return []

    url = "https://google.serper.dev/search"  # correct endpoint
    payload = json.dumps({
        "q": query,
        "gl": "us",
        "hl": "en",
        "num": 10,
        "type": "search"
    })
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        data = response.json()

        jobs = []

        # Priority 1: Google Jobs widget (best structured data)
        if "jobs" in data:
            logging.info(f"  → Jobs widget found: {len(data['jobs'])} jobs for '{query}'")
            jobs = data["jobs"]

        # Priority 2: Parse organic results for job postings
        elif "organic" in data:
            logging.info(f"  → No jobs widget, parsing {len(data['organic'])} organic results")
            for item in data["organic"]:
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                link = item.get("link", "")
                # Only keep results that look like actual job postings
                if any(kw in title.lower() for kw in ["engineer", "developer", "intern", "scientist"]):
                    jobs.append({
                        "title": title,
                        "companyName": extract_company_from_title(title),
                        "location": "USA",
                        "description": snippet,
                        "applyLink": link,
                    })

        return jobs

    except Exception as e:
        logging.error(f"Error fetching from Serper: {e}")
        return []

def extract_company_from_title(title: str) -> str:
    """Try to extract company name from organic result title like 'SWE at Stripe | Stripe Careers'"""
    separators = [" at ", " | ", " - ", " — "]
    for sep in separators:
        if sep in title:
            parts = title.split(sep)
            if len(parts) > 1:
                return parts[-1].strip().split(" ")[0]
    return "Unknown"

def scrape_all_jobs() -> List[Dict[str, Any]]:
    """
    Runs all queries and returns parsed individual job listings.
    """
    logging.info("Starting job scraping process...")
    all_jobs = []
    seen = set()

    for query in SEARCH_QUERIES:
        logging.info(f"Searching: '{query}'")
        raw_jobs = fetch_jobs_from_serper(query)

        for job in raw_jobs:
            title    = str(job.get("title") or "").strip()
            company  = str(job.get("companyName") or job.get("company") or "Unknown").strip()
            location = str(job.get("location") or "USA").strip()
            desc     = str(job.get("description") or job.get("snippet") or "").strip()
            link     = str(job.get("applyLink") or job.get("link") or "").strip()

            if not title:
                continue

            key = f"{title.lower()}|{company.lower()}"
            if key in seen:
                continue
            seen.add(key)

            # Filter: skip non-USA locations
            bad_locations = ["canada", "uk", "australia", "europe", "germany", "france"]
            if any(bl in location.lower() for bl in bad_locations):
                continue

            # Filter: skip senior/non-entry titles and junk titles
            bad_title_words = ["senior", "staff", "principal", "lead", "manager", 
                               "director", "vp", "head of", "preparing for", 
                               "best it", "how to", "guide", "sr.", " iii", " iv"]
            if any(bt in title.lower() for bt in bad_title_words):
                continue

            # Filter: skip junk companies
            bad_companies = ["prosple", "built", "platform", "lever", "greenhouse", 
                             "jobs", "indeed", "ziprecruiter"]
            if company.lower() in bad_companies:
                continue

            all_jobs.append({
                "title": title,
                "company": company,
                "location": location,
                "description": desc,
                "apply_link": link,
                "posted_at": "Recent",
                "experience_level": "Unknown",
                "source": "serper_search"
            })

    logging.info(f"Total jobs scraped: {len(all_jobs)}")
    return all_jobs

if __name__ == "__main__":
    jobs = scrape_all_jobs()
    for j in jobs[:5]:
        print(f"\n{j['company']} — {j['title']}")
        print(f"  Location : {j['location']}")
        print(f"  Apply    : {j['apply_link']}")


def search_custom_query(user_query: str) -> List[Dict[str, Any]]:
    """
    Takes a raw user query (e.g. 'ML Engineer entry level') and searches
    Google via Serper, returning filtered job listings.
    """
    logging.info(f"Custom search: '{user_query}'")
    all_jobs = []
    seen = set()

    # Build multiple query variants from the user query
    queries = [
        f'{user_query} "visa sponsorship" "entry level" "apply"',
        f'{user_query} "new grad" OR "0-2 years" "apply"',
        f'site:greenhouse.io {user_query}',
        f'site:lever.co {user_query}',
        f'{user_query} "careers" "apply now"',
    ]

    for query in queries:
        raw_jobs = fetch_jobs_from_serper(query)
        for job in raw_jobs:
            title    = str(job.get("title") or "").strip()
            company  = str(job.get("companyName") or job.get("company") or "Unknown").strip()
            location = str(job.get("location") or "USA").strip()
            desc     = str(job.get("description") or job.get("snippet") or "").strip()
            link     = str(job.get("applyLink") or job.get("link") or "").strip()

            if not title:
                continue

            key = f"{title.lower()}|{company.lower()}"
            if key in seen:
                continue
            seen.add(key)

            # Location filter
            bad_locations = ["canada", "uk", "australia", "europe", "germany", "france"]
            if any(bl in location.lower() for bl in bad_locations):
                continue

            # Title filter
            bad_title_words = ["senior", "staff", "principal", "lead", "manager",
                               "director", "vp", "head of", "preparing for",
                               "best it", "how to", "guide", "sr.", " iii", " iv"]
            if any(bt in title.lower() for bt in bad_title_words):
                continue

            # Company filter
            bad_companies = ["prosple", "built", "platform", "lever", "greenhouse",
                             "jobs", "indeed", "ziprecruiter"]
            if company.lower() in bad_companies:
                continue

            all_jobs.append({
                "title": title,
                "company": company,
                "location": location,
                "description": desc,
                "apply_link": link,
                "posted_at": "Recent",
                "experience_level": "Unknown",
                "source": "custom_search"
            })

    logging.info(f"Custom search found {len(all_jobs)} jobs")
    return all_jobs