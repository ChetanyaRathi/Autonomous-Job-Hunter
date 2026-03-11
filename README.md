# 🚀 Autonomous Job Hunter

An AI-powered job search tool that finds entry-level software engineering jobs with visa sponsorship in the USA. Search on demand, get Gemini AI analysis, and receive email notifications — all from a beautiful local dashboard.

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.1-black?logo=flask)
![Gemini](https://img.shields.io/badge/Google_Gemini-AI-orange?logo=google)

---

## ✨ Features

- **🔍 Search on Demand** — Type any role (e.g. "ML Engineer") and get real-time results from Google via Serper API
- **🤖 AI Analysis** — Google Gemini parses every job description, extracting skills, experience level, visa status, and tech stack
- **⭐ Smart Scoring** — Jobs are scored based on skill match, experience level, location, visa sponsorship, and title keywords
- **📧 Email Digest** — Automatically sends a formatted HTML email with all matched jobs and apply links
- **📂 Run History** — Browse previous searches and compare results across runs
- **🎯 Entry-Level Filters** — Aggressively filters out senior roles, junk aggregator results, and non-USA locations

## 🏗️ Architecture

```
├── app.py              # Flask web server + API routes
├── scraper.py          # Serper API integration + Google search
├── analyzer.py         # Google Gemini job description parser
├── matcher.py          # Scoring engine + SQLite database
├── notifier.py         # Email notification system
├── main.py             # CLI pipeline runner
├── config.py           # User profile + API key config
├── templates/
│   └── index.html      # Search dashboard UI
├── requirements.txt    # Python dependencies
├── run_dashboard.sh    # Quick start script
└── .env                # API keys (not tracked by git)
```

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/ChetanyaRathi/Autonomous-Job-Hunter.git
cd Autonomous-Job-Hunter
```

### 2. Install dependencies

```bash
pip3 install -r requirements.txt
```

### 3. Set up API keys

Create a `.env` file in the project root:

```env
SERPER_API_KEY=your_serper_api_key
GEMINI_API_KEY=your_gemini_api_key
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password
```

> **Note:** For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833), not your regular password.

### 4. Run the dashboard

```bash
python3 app.py
```

Open **http://localhost:8080** in your browser.

### 5. Search for jobs

1. Type a role like "Software Engineer" in the search bar
2. Click a suggestion pill or type your own query
3. Select a time filter
4. Hit **🔍 Search Jobs**
5. Watch as the pipeline scrapes, analyzes, and scores results in real-time

## 🔧 API Keys

| Service | Purpose | Get it at |
|---------|---------|-----------|
| **Serper** | Google search results | [serper.dev](https://serper.dev) |
| **Gemini** | AI job description parsing | [aistudio.google.com](https://aistudio.google.com/apikey) |
| **Gmail SMTP** | Email notifications | [Google App Passwords](https://myaccount.google.com/apppasswords) |

## 👤 User Profile

The default profile in `config.py` is configured for:

- **Role:** Software Engineer
- **Experience:** Entry Level
- **Skills:** Python, React, Node.js, Machine Learning, AWS
- **Location:** USA
- **Visa Sponsorship:** Required
- **Remote:** Yes

Edit `config.py` to customize the profile for your own job search.

## 📡 API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Dashboard UI |
| `/api/search` | POST | Start a new search pipeline |
| `/api/search/status` | GET | Poll search progress |
| `/api/jobs` | GET | Get jobs (supports `?run_id=` and `?posted_within=`) |
| `/api/runs` | GET | List all previous search runs |
| `/api/stats` | GET | Job statistics |

## ⚙️ CLI Mode

Run the full pipeline from the terminal (uses hardcoded queries in `scraper.py`):

```bash
python3 main.py
```

## 📝 License

MIT
