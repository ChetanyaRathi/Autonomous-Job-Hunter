import os
import json
import logging
import google.generativeai as genai
from typing import Dict, Any

from config import GEMINI_API_KEY

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")
else:
    model = None
    logging.warning("GEMINI_API_KEY not found. Analyzer will not work properly.")

def analyze_job_description(description: str) -> Dict[str, Any]:
    """
    Uses Google Gemini API to parse the job description and extract structured information.
    Instructs the model to output strict JSON only.
    """
    if not model:
        raise ValueError("GenerativeModel is not initialized because GEMINI_API_KEY is missing.")

    prompt = f"""
    You are a professional technical recruiter and job analyst. Read the following job description and extract key information.
    Your response MUST be valid JSON ONLY with no markdown formatting, no code blocks, and no preamble.
    Do not wrap the JSON in ```json ... ``` blocks. Return purely the JSON text.

    Required JSON keys:
    - "required_skills": list of strings (e.g., ["Python", "JavaScript"])
    - "experience_level": string — Look for keywords like "new grad", "new graduate", "entry level", 
      "entry-level", "0-2 years", "0-1 years", "junior", "intern", "internship", "university hire", 
      "recent graduate", "associate", "early career". If ANY of these are found, return "Entry Level".
      If the job requires MORE than 2 years of experience (e.g., "3+ years", "4 years", "5+ years",
      "mid level", "senior", "staff", "lead"), set experience_level to "Senior" so it can be filtered out.
      If absolutely NONE of these keywords exist, default to "Entry Level" (do NOT return "Unknown").
    - "visa_sponsorship": string, MUST be one of: "Likely", "Unknown", or "No Sponsorship".
      Look for "visa sponsorship", "H1B", "OPT", "we sponsor", "sponsorship available" → "Likely".
      Look for "no sponsorship", "must be authorized", "no visa" → "No Sponsorship".
      If nothing found → "Unknown".
    - "location": string (the parsed location from the text, or "Unknown")
    - "tech_stack": list of strings (all major technologies mentioned)

    Job Description:
    {description}
    """

    try:
        response = model.generate_content(prompt)
        # Clean up any potential markdown fences in case the model ignores the instruction
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        
        parsed_json = json.loads(raw_text.strip())
        
        # Force default experience_level to Entry Level if Unknown or missing
        if parsed_json.get("experience_level", "Unknown") == "Unknown":
            parsed_json["experience_level"] = "Entry Level"
        
        return parsed_json
    except Exception as e:
        logging.error(f"Error during Gemini parsing: {e}")
        # Return a safe fallback so the pipeline doesn't crash completely
        return {
            "required_skills": [],
            "experience_level": "Entry Level",
            "visa_sponsorship": "Unknown",
            "location": "Unknown",
            "tech_stack": []
        }

if __name__ == "__main__":
    # Test block
    sample_jd = "We are looking for an Entry Level Software Engineer skilled in Python and React. We do not provide visa sponsorship."
    res = analyze_job_description(sample_jd)
    print(json.dumps(res, indent=2))
