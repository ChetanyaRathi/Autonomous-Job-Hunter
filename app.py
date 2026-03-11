import os
import json
import sqlite3
import subprocess
import threading
from datetime import datetime
from flask import Flask, render_template, jsonify, request, Response
from scraper import search_custom_query
from analyzer import analyze_job_description
from matcher import filter_and_match, init_db
from notifier import notify

app = Flask(__name__)

DB_NAME = "jobs.db"
RUNNING = False
OUTPUT_LINES = []
SEARCH_STATUS = {"stage": "idle", "message": "", "jobs": []}

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = dict_factory
    return conn

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/jobs")
def api_jobs():
    try:
        run_id = request.args.get('run_id', 'latest')
        posted_within = request.args.get('posted_within', 'all')
        
        conn = get_db_connection()
        
        if run_id == 'latest':
            row = conn.execute("SELECT pipeline_run_id FROM jobs ORDER BY timestamp DESC LIMIT 1").fetchone()
            if row:
                run_id = row['pipeline_run_id']
            else:
                conn.close()
                return jsonify({"jobs": [], "run_id": "none"})
        
        conditions = []
        if run_id != 'ALL':
            conditions.append(f"pipeline_run_id = '{run_id}'")
            
        if posted_within == '1h':
            conditions.append("timestamp >= datetime('now', '-1 hour')")
        elif posted_within == '24h':
            conditions.append("timestamp >= datetime('now', '-24 hours')")
        elif posted_within == '7d':
            conditions.append("timestamp >= datetime('now', '-7 days')")
        elif posted_within == '30d':
            conditions.append("timestamp >= datetime('now', '-30 days')")
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        query = f"SELECT * FROM jobs {where_clause} ORDER BY score DESC, timestamp DESC"
        jobs = conn.execute(query).fetchall()
        conn.close()
        
        filtered = []
        bad_companies = [c.lower() for c in ["Greenhouse", "Lever", "Indeed", 
          "ZipRecruiter", "LinkedIn", "Glassdoor", "SimplyHired",
          "Unknown", "Migrate", "Globe", "Reddit", "YouTube",
          "Instagram", "Facebook", "Summer", "Jobs", "Find",
          "Built", "Job", "ID", "Entry", "Feb", "March", "Space",
          "Ground", "Intern", "Jooble", "Jobright"]]
          
        bad_titles = [t.lower() for t in ["jobs in United States", 
          "Jobs, Employment", "NOW HIRING", "Hiring Now",
          "visa sponsorship jobs -", "How to Immigrate"]]
        
        for j in jobs:
            company = str(j.get('company', '')).strip().lower()
            title = str(j.get('title', '')).strip().lower()
            if company in bad_companies:
                continue
            skip = False
            for bt in bad_titles:
                if bt in title:
                    skip = True
                    break
            if skip:
                continue
            j['visa'] = j.get('visa') or 'Unknown'
            filtered.append(j)
            
        return jsonify({"jobs": filtered, "run_id": run_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stats")
def api_stats():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM jobs")
        total_jobs = cursor.fetchone()[0]
        try:
            cursor.execute("SELECT COUNT(*) FROM jobs WHERE visa = 'Likely'")
            visa_likely = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            visa_likely = 0
        cursor.execute("SELECT AVG(score) FROM jobs")
        avg = cursor.fetchone()[0]
        avg_score = round(avg, 1) if avg else 0
        cursor.execute("SELECT MAX(timestamp) FROM jobs")
        last_run = cursor.fetchone()[0] or "Never"
        conn.close()
        return jsonify({
            "total_jobs": total_jobs, "visa_likely": visa_likely,
            "avg_score": avg_score, "last_run": last_run
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/runs")
def api_runs():
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pipeline_run_id, COUNT(*) as job_count, MAX(timestamp) as run_time
            FROM jobs
            WHERE pipeline_run_id IS NOT NULL AND pipeline_run_id != 'unknown'
            GROUP BY pipeline_run_id
            ORDER BY run_time DESC
        """)
        runs = [{"run_id": r["pipeline_run_id"], "job_count": r["job_count"], "run_time": r["run_time"]} for r in cursor.fetchall()]
        conn.close()
        return jsonify(runs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/search", methods=["POST"])
def api_search():
    global SEARCH_STATUS
    data = request.get_json()
    query = data.get("query", "software engineer entry level")
    time_filter = data.get("time_filter", "24h")
    send_email = data.get("send_email", True)
    
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    SEARCH_STATUS = {"stage": "searching", "message": f"🔍 Searching for '{query}'...", "jobs": [], "run_id": run_id}
    
    def run_search():
        global SEARCH_STATUS
        try:
            # Step 1: Scrape
            SEARCH_STATUS["stage"] = "searching"
            SEARCH_STATUS["message"] = f"🔍 Searching Google for '{query}'..."
            raw_jobs = search_custom_query(query)
            
            if not raw_jobs:
                SEARCH_STATUS = {"stage": "done", "message": "❌ No jobs found for this query.", "jobs": [], "run_id": run_id}
                return
            
            SEARCH_STATUS["message"] = f"🤖 Analyzing {len(raw_jobs)} jobs with Gemini AI..."
            SEARCH_STATUS["stage"] = "analyzing"
            
            # Step 2: Analyze
            analyzed = []
            for i, job in enumerate(raw_jobs):
                try:
                    analysis = analyze_job_description(job['description'])
                    job['analysis'] = analysis
                    analyzed.append(job)
                    SEARCH_STATUS["message"] = f"🤖 Analyzing job {i+1}/{len(raw_jobs)} with Gemini..."
                except Exception as e:
                    job['analysis'] = {"required_skills": [], "experience_level": "Entry Level", "visa_sponsorship": "Unknown", "location": "Unknown", "tech_stack": []}
                    analyzed.append(job)
            
            # Step 3: Match & Score
            SEARCH_STATUS["message"] = "⭐ Scoring and matching jobs..."
            SEARCH_STATUS["stage"] = "matching"
            matched = filter_and_match(analyzed, run_id)
            
            # Step 4: Email
            if send_email and matched:
                SEARCH_STATUS["message"] = "📧 Sending email digest..."
                try:
                    notify(matched)
                except Exception:
                    pass
            
            SEARCH_STATUS = {
                "stage": "done",
                "message": f"✅ Found {len(matched)} matching jobs!",
                "jobs": matched,
                "run_id": run_id
            }
        except Exception as e:
            SEARCH_STATUS = {"stage": "error", "message": f"❌ Error: {str(e)}", "jobs": [], "run_id": run_id}
    
    thread = threading.Thread(target=run_search)
    thread.start()
    
    return jsonify({"status": "started", "run_id": run_id})

@app.route("/api/search/status")
def api_search_status():
    return jsonify(SEARCH_STATUS)

# Legacy: run full pipeline
def run_pipeline():
    global RUNNING, OUTPUT_LINES
    RUNNING = True
    OUTPUT_LINES = []
    process = subprocess.Popen(
        ["python3", "main.py"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1, universal_newlines=True
    )
    for line in iter(process.stdout.readline, ''):
        OUTPUT_LINES.append(line)
        if len(OUTPUT_LINES) > 500:
            OUTPUT_LINES.pop(0)
    process.stdout.close()
    process.wait()
    RUNNING = False

@app.route("/api/run")
def api_run():
    global RUNNING
    if not RUNNING:
        thread = threading.Thread(target=run_pipeline)
        thread.start()
        return jsonify({"status": "started"})
    else:
        return jsonify({"status": "already_running"}), 400

@app.route("/api/output")
def api_output():
    return jsonify({"running": RUNNING, "output": "".join(OUTPUT_LINES)})

if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=8080, debug=True)
