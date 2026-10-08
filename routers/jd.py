# jd.py
# This file handles all Job Description related API endpoints
# It receives job description text from React frontend
# Sends it to Groq AI for analysis
# Returns structured data about the job requirements
# Supports user own Groq key via X-Groq-Key header

from fastapi import APIRouter, HTTPException, Request
from utils.groq_client import call_groq
import json
import re
from pydantic import BaseModel

class JDRequest(BaseModel):
    job_description: str

router = APIRouter(
    prefix="/jd",
    tags=["Job Description"]
)

def clean_text(text: str) -> str:
    """Cleans special characters from text"""
    text = text.replace('\u2018', "'")
    text = text.replace('\u2019', "'")
    text = text.replace('\u201c', '"')
    text = text.replace('\u201d', '"')
    text = text.replace('\u2013', '-')
    text = text.replace('\u2014', '-')
    text = text.replace('\u2026', '...')
    text = text.replace('\u00a0', ' ')
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text

@router.post("/analyse")
async def analyse_job_description(request: Request):
    """
    Receives job description from React as plain text
    Sends to Groq AI and returns structured data
    Supports user own Groq key via X-Groq-Key header

    How to call from React:
    POST http://localhost:8000/jd/analyse
    Content-Type: text/plain
    X-Groq-Key: gsk_xxx (optional)
    Body: job description text
    """

    try:
        # Read raw body
        body_bytes = await request.body()
        body_str = body_bytes.decode('utf-8', errors='replace')

        # Try JSON first then fall back to plain text
        job_description = None
        try:
            data = json.loads(body_str)
            if isinstance(data, dict):
                job_description = data.get('job_description', '')
            elif isinstance(data, str):
                job_description = data
        except json.JSONDecodeError:
            job_description = body_str

        if not job_description:
            raise HTTPException(status_code=400, detail="No job description provided")

        # Clean the text
        job_description = clean_text(job_description.strip())

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading request: {str(e)}")

    # Validate length
    if len(job_description) < 50:
        raise HTTPException(
            status_code=400,
            detail="Job description is too short. Please paste the full job description."
        )

    if len(job_description) > 15000:
        raise HTTPException(
            status_code=400,
            detail="Job description is too long. Maximum 15000 characters allowed."
        )

    # Build prompt
    prompt = f"""
You are a job description analyser. Extract information from the following job description and return it as valid JSON only.

Job Description:
{job_description}

Extract and return ONLY this JSON structure with no extra text before or after:
{{
    "job_title": "the job title or empty string if not found",
    "company": "company name or empty string if not found",
    "location": "job location or empty string if not found",
    "job_type": "full time, part time, contract or empty string",
    "required_skills": ["skill1", "skill2", "skill3"],
    "nice_to_have_skills": ["skill1", "skill2"],
    "responsibilities": ["responsibility1", "responsibility2", "responsibility3"],
    "required_experience": "years of experience required or empty string",
    "required_education": "education requirements or empty string",
    "salary": "salary range if mentioned or empty string",
    "summary": "brief 2-3 sentence summary of what this role is about"
}}

Return ONLY the JSON. No explanation. No markdown. No code blocks.
"""

    try:
        # Get user own Groq key from request header if provided
        user_groq_key = request.headers.get('X-Groq-Key')

        ai_response = call_groq(
            prompt=prompt,
            system_message="You are a job description analyser. You only return valid JSON. Never add any text outside the JSON.",
            user_groq_key=user_groq_key
        )

        # Clean AI response
        cleaned_response = ai_response.strip()
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response.split("```")[1]
            if cleaned_response.startswith("json"):
                cleaned_response = cleaned_response[4:]
            cleaned_response = cleaned_response.strip()

        analysed_data = json.loads(cleaned_response)

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"AI returned invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis error: {str(e)}")

    return {
        "success": True,
        "message": "Job description analysed successfully",
        "data": analysed_data
    }