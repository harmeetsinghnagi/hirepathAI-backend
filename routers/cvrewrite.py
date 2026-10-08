# cvrewrite.py
# This file handles the CV Rewrite feature
# It receives original CV data, JD data and skill gap data
# Uses Groq AI to rewrite the CV to better match the job
# Adds missing skills naturally into the CV content
# Supports user own Groq key via X-Groq-Key header

from fastapi import APIRouter, HTTPException, Request
from utils.groq_client import call_groq
import json
import re

router = APIRouter(
    prefix="/cvrewrite",
    tags=["CV Rewrite"]
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

@router.post("/generate")
async def rewrite_cv(request: Request):
    """
    Receives original CV data JD data and skill gap data
    Rewrites the CV to better match the job description
    Naturally incorporates missing skills into the content
    Supports user own Groq key via X-Groq-Key header

    How to call from React:
    POST http://localhost:8000/cvrewrite/generate
    Content-Type: application/json
    X-Groq-Key: gsk_xxx (optional)
    Body: JSON with cv_data jd_data and skill_gap_data
    """

    try:
        # Read raw body
        body_bytes = await request.body()
        body_str = body_bytes.decode('utf-8', errors='replace')
        body_str = clean_text(body_str)
        data = json.loads(body_str)

        cv_data = data.get('cv_data')
        jd_data = data.get('jd_data')
        skill_gap_data = data.get('skill_gap_data')

        if not cv_data:
            raise HTTPException(status_code=400, detail="CV data is required")
        if not jd_data:
            raise HTTPException(status_code=400, detail="JD data is required")
        if not skill_gap_data:
            raise HTTPException(status_code=400, detail="Skill gap data is required")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading request: {str(e)}")

    # Clean all data
    cv_str = clean_text(json.dumps(cv_data, indent=2))
    jd_str = clean_text(json.dumps(jd_data, indent=2))
    gap_str = clean_text(json.dumps(skill_gap_data, indent=2))

    # Get key information
    candidate_name = cv_data.get('full_name', '')
    job_title = jd_data.get('job_title', '')
    missing_skills = [s.get('skill', '') for s in skill_gap_data.get('missing_skills', [])]
    matched_skills = [s.get('skill', '') for s in skill_gap_data.get('matched_skills', [])]

    # Build prompt
    prompt = f"""
You are a professional CV writer specialising in New Zealand job applications.
Rewrite the candidate CV to better match the job description.

IMPORTANT RULES:
1. Do NOT invent fake experience or qualifications
2. Naturally incorporate missing skills where candidate has related experience
3. Rephrase existing experience to highlight relevance to this specific job
4. Add missing skills to skills section if candidate could reasonably have them
5. Keep all dates company names and job titles accurate
6. Write in professional New Zealand English
7. Make the summary specifically target this role

Original CV Data:
{cv_str}

Target Job:
{jd_str}

Skill Gap Analysis:
{gap_str}

Missing skills to incorporate naturally: {', '.join(missing_skills)}
Matched skills to highlight strongly: {', '.join(matched_skills)}

Return ONLY this JSON structure with no extra text:
{{
    "full_name": "{candidate_name}",
    "email": "{cv_data.get('email', '')}",
    "phone": "{cv_data.get('phone', '')}",
    "location": "{cv_data.get('location', '')}",
    "target_role": "{job_title}",
    "professional_summary": "A strong 3-4 sentence summary specifically written for this role",
    "skills": {{
        "technical": ["skill1", "skill2", "skill3"],
        "soft": ["skill1", "skill2"]
    }},
    "experience": [
        {{
            "job_title": "exact job title",
            "company": "exact company name",
            "duration": "exact dates",
            "responsibilities": [
                "responsibility rewritten to highlight relevance to target job"
            ],
            "achievements": [
                "quantified achievement if available"
            ]
        }}
    ],
    "education": [
        {{
            "degree": "exact degree name",
            "institution": "exact institution",
            "year": "exact year",
            "relevant_courses": []
        }}
    ],
    "certifications": ["cert1", "cert2"],
    "improvements_made": [
        "Description of what was changed and why"
    ]
}}

Return ONLY the JSON. No explanation. No markdown. No code blocks.
"""

    try:
        # Get user own Groq key from request header if provided
        user_groq_key = request.headers.get('X-Groq-Key')

        ai_response = call_groq(
            prompt=prompt,
            system_message="You are a professional CV writer. You only return valid JSON. Never invent fake experience. Only enhance and rephrase real experience.",
            user_groq_key=user_groq_key
        )

        # Clean AI response
        cleaned_response = ai_response.strip()
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response.split("```")[1]
            if cleaned_response.startswith("json"):
                cleaned_response = cleaned_response[4:]
            cleaned_response = cleaned_response.strip()

        rewritten_cv = json.loads(cleaned_response)

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"AI returned invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI rewrite error: {str(e)}")

    return {
        "success": True,
        "message": "CV rewritten successfully",
        "data": rewritten_cv
    }