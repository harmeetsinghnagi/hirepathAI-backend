# coverletter.py
# This file handles the Cover Letter Generator feature
# It receives CV data, JD data and skill gap data from React
# Uses Groq AI to write a professional NZ style cover letter
# Supports user own Groq key via X-Groq-Key header

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from utils.groq_client import call_groq
import json
import re

router = APIRouter(
    prefix="/coverletter",
    tags=["Cover Letter"]
)

class CoverLetterRequest(BaseModel):
    cv_data: dict
    jd_data: dict
    skill_gap_data: dict
    tone: str = "professional"

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
async def generate_cover_letter(request: Request):
    """
    Receives CV data JD data and skill gap data from React
    Generates a professional NZ style cover letter using Groq AI
    Supports user own Groq key via X-Groq-Key header

    How to call from React:
    POST http://localhost:8000/coverletter/generate
    Content-Type: application/json
    X-Groq-Key: gsk_xxx (optional)
    Body: JSON with cv_data jd_data skill_gap_data and tone
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
        tone = data.get('tone', 'professional')

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

    # Get key details
    candidate_name = cv_data.get('full_name', '')
    candidate_email = cv_data.get('email', '')
    candidate_phone = cv_data.get('phone', '')
    candidate_location = cv_data.get('location', 'Auckland, New Zealand')
    job_title = jd_data.get('job_title', 'the position')
    company_name = jd_data.get('company', 'your organisation')
    highlights = skill_gap_data.get('cover_letter_highlights', [])
    highlights_str = '\n'.join([f'- {h}' for h in highlights]) if highlights else ''

    # Build prompt
    prompt = f"""
You are an expert career coach specialising in New Zealand job applications.
Write a professional cover letter in New Zealand style for the following candidate.

Candidate Information:
{cv_str}

Job Details:
{jd_str}

Skill Gap Analysis:
{gap_str}

Key points to highlight:
{highlights_str}

Cover letter tone: {tone}

New Zealand cover letter guidelines:
- Strong opening showing genuine interest in the role and company
- Maximum 4 paragraphs — concise and focused
- Clear professional language — not too formal not too casual
- Focus on what you can contribute not just what you want
- Mention specific skills matching the job requirements
- Address gaps positively — show willingness to learn
- End with confident call to action
- Use New Zealand English — organise not organize colour not color
- Genuine and human — not robotic or generic

Write the complete cover letter. Start directly with candidate details.
Format exactly like this:

{candidate_name}
{candidate_location}
{candidate_email}
{candidate_phone}

[Today's date]

Hiring Manager
{company_name}

Dear Hiring Manager,

[Opening paragraph]

[Second paragraph]

[Third paragraph]

[Closing paragraph]

Yours sincerely,

{candidate_name}

Write the complete letter with real content. Do not use placeholder text in square brackets.
"""

    try:
        # Get user own Groq key from request header if provided
        user_groq_key = request.headers.get('X-Groq-Key')

        ai_response = call_groq(
            prompt=prompt,
            system_message="You are an expert NZ career coach. Write genuine professional cover letters. Never use placeholder text. Always write real content.",
            user_groq_key=user_groq_key
        )

        cover_letter = ai_response.strip()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation error: {str(e)}")

    return {
        "success": True,
        "message": "Cover letter generated successfully",
        "data": {
            "cover_letter": cover_letter,
            "candidate_name": candidate_name,
            "job_title": job_title,
            "company": company_name,
            "tone": tone,
            "word_count": len(cover_letter.split())
        }
    }