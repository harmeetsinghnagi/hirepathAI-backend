# skillgap.py
# This file handles the Skill Gap Analysis feature
# It receives parsed CV data and analysed JD data
# Compares them using Groq AI
# Returns match percentage, matched skills and missing skills
# Supports user own Groq key via X-Groq-Key header

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from utils.groq_client import call_groq
import json
import re

router = APIRouter(
    prefix="/skillgap",
    tags=["Skill Gap Analysis"]
)

class SkillGapRequest(BaseModel):
    cv_data: dict
    jd_data: dict

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
async def analyse_skill_gap(request: Request):
    """
    Receives CV data and JD data from React
    Compares them using Groq AI
    Returns match percentage, matched skills, missing skills and recommendations
    Supports user own Groq key via X-Groq-Key header

    How to call from React:
    POST http://localhost:8000/skillgap/analyse
    Content-Type: application/json
    X-Groq-Key: gsk_xxx (optional)
    Body: JSON with cv_data and jd_data
    """

    try:
        # Read raw body and parse
        body_bytes = await request.body()
        body_str = body_bytes.decode('utf-8', errors='replace')
        body_str = clean_text(body_str)
        data = json.loads(body_str)

        cv_data = data.get('cv_data')
        jd_data = data.get('jd_data')

        if not cv_data:
            raise HTTPException(status_code=400, detail="CV data is required")
        if not jd_data:
            raise HTTPException(status_code=400, detail="JD data is required")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading request: {str(e)}")

    # Clean data before sending to AI
    cv_str = clean_text(json.dumps(cv_data, indent=2))
    jd_str = clean_text(json.dumps(jd_data, indent=2))

    # Build prompt
    prompt = f"""
You are a career advisor and skill gap analyser. Compare the candidate CV with the job description requirements and return a detailed analysis as valid JSON only.

Candidate CV Data:
{cv_str}

Job Description Requirements:
{jd_str}

Analyse and return ONLY this JSON structure with no extra text:
{{
    "match_percentage": 75,
    "match_level": "Good Match",
    "summary": "2-3 sentence summary of how well the candidate matches this role",
    "matched_skills": [
        {{
            "skill": "skill name",
            "note": "brief note about how candidate demonstrates this skill"
        }}
    ],
    "missing_skills": [
        {{
            "skill": "skill name",
            "importance": "required or nice to have",
            "note": "brief advice on how to address this gap"
        }}
    ],
    "extra_skills": ["skill1", "skill2"],
    "experience_match": {{
        "required": "what the job requires",
        "candidate_has": "what the candidate has",
        "matches": true
    }},
    "education_match": {{
        "required": "what the job requires",
        "candidate_has": "what the candidate has",
        "matches": true
    }},
    "recommendations": [
        "recommendation 1 to improve application",
        "recommendation 2",
        "recommendation 3"
    ],
    "cover_letter_highlights": [
        "key point to mention in cover letter 1",
        "key point to mention in cover letter 2",
        "key point to mention in cover letter 3"
    ]
}}

Rules for match_percentage:
- 90 to 100: Excellent Match
- 70 to 89: Good Match
- 50 to 69: Fair Match
- Below 50: Low Match

Return ONLY the JSON. No explanation. No markdown. No code blocks.
"""

    try:
        # Get user own Groq key from request header if provided
        user_groq_key = request.headers.get('X-Groq-Key')

        ai_response = call_groq(
            prompt=prompt,
            system_message="You are a skill gap analyser. You only return valid JSON. Be accurate and helpful in your analysis.",
            user_groq_key=user_groq_key
        )

        # Clean AI response
        cleaned_response = ai_response.strip()
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response.split("```")[1]
            if cleaned_response.startswith("json"):
                cleaned_response = cleaned_response[4:]
            cleaned_response = cleaned_response.strip()

        analysis = json.loads(cleaned_response)

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"AI returned invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis error: {str(e)}")

    return {
        "success": True,
        "message": "Skill gap analysis completed",
        "data": analysis
    }