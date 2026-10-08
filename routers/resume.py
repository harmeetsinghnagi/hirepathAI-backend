# resume.py
# This file handles all resume related API endpoints
# It receives CV files from React frontend
# Extracts text from them
# Sends text to Groq AI for parsing
# Returns structured resume data back to React

from fastapi import APIRouter, UploadFile, File, HTTPException
from utils.file_parser import extract_text
from utils.groq_client import call_groq
import json

# APIRouter is like a mini FastAPI app
# We use it to group related endpoints together
# All resume endpoints will start with /resume
router = APIRouter(
    prefix="/resume",
    tags=["Resume"]
)

@router.post("/parse")
async def parse_resume(file: UploadFile = File(...)):
    """
    This endpoint receives a CV file from React
    Extracts the text from it
    Sends it to Groq AI to parse into structured data
    Returns name, email, skills, experience, education etc
    
    How to call from React:
    POST http://localhost:8000/resume/parse
    Body: form-data with file field
    """

    # Step 1 — Check file type is PDF or DOCX only
    # file.filename gives us the original file name like "harmeet_cv.pdf"
    filename = file.filename.lower()

    if not (filename.endswith(".pdf") or filename.endswith(".docx")):
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are allowed"
        )

    # Step 2 — Read the file bytes
    # await file.read() reads the entire file into memory as bytes
    file_bytes = await file.read()

    # Check file is not empty
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=400,
            detail="File is empty"
        )

    # Check file size is not more than 5MB
    max_size = 5 * 1024 * 1024  # 5MB in bytes
    if len(file_bytes) > max_size:
        raise HTTPException(
            status_code=400,
            detail="File size must be less than 5MB"
        )

    # Step 3 — Extract text from the file
    # Figure out if it is PDF or DOCX from the file name
    file_type = "pdf" if filename.endswith(".pdf") else "docx"

    try:
        # Call our file parser to extract the text
        cv_text = extract_text(file_bytes, file_type)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading file: {str(e)}"
        )

    # Check we actually got some text
    if not cv_text or len(cv_text.strip()) < 50:
        raise HTTPException(
            status_code=400,
            detail="Could not extract enough text from the file. Make sure the CV is not a scanned image."
        )

    # Step 4 — Send text to Groq AI for parsing
    # We write a very specific prompt that tells AI exactly what to extract
    # and exactly how to format the response
    prompt = f"""
You are a professional CV parser. Extract information from the following CV text and return it as valid JSON only.

CV Text:
{cv_text}

Extract and return ONLY this JSON structure with no extra text before or after:
{{
    "full_name": "person's full name or empty string if not found",
    "email": "email address or empty string if not found",
    "phone": "phone number or empty string if not found",
    "location": "city and country or empty string if not found",
    "summary": "professional summary or objective in 2-3 sentences or empty string",
    "skills": ["skill1", "skill2", "skill3"],
    "experience": [
        {{
            "job_title": "job title",
            "company": "company name",
            "duration": "start date to end date",
            "description": "brief description of role"
        }}
    ],
    "education": [
        {{
            "degree": "degree name",
            "institution": "university or college name",
            "year": "graduation year or period"
        }}
    ],
    "certifications": ["certification1", "certification2"]
}}

Return ONLY the JSON. No explanation. No markdown. No code blocks.
"""

    try:
        # Call Groq AI with our prompt
        ai_response = call_groq(
            prompt=prompt,
            system_message="You are a CV parser. You only return valid JSON. Never add any text outside the JSON."
        )

        # Clean the response — remove any markdown formatting if AI added it
        # Sometimes AI wraps JSON in ```json ... ``` even when told not to
        cleaned_response = ai_response.strip()
        if cleaned_response.startswith("```"):
            # Remove markdown code block
            cleaned_response = cleaned_response.split("```")[1]
            if cleaned_response.startswith("json"):
                cleaned_response = cleaned_response[4:]
            cleaned_response = cleaned_response.strip()

        # Parse the JSON string into a Python dictionary
        parsed_data = json.loads(cleaned_response)

    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI returned invalid JSON: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI parsing error: {str(e)}"
        )

    # Step 5 — Return the parsed data to React
    return {
        "success": True,
        "message": "CV parsed successfully",
        "data": parsed_data,
        "raw_text_length": len(cv_text)
    }