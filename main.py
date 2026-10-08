# main.py
# This is the main file of our FastAPI backend
# It creates the FastAPI app and connects all the routers
# The middleware here cleans all incoming requests before they reach our endpoints
# Run this file with: uvicorn main:app --reload

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import json
import re

# Import our routers
# Each router handles a different feature of HirePathAI
from routers import resume
from routers import jd
from routers import skillgap
from routers import coverletter
from routers import cvrewrite

# Load secret keys from .env file
load_dotenv()

# Create the FastAPI app
app = FastAPI(
    title="HirePathAI Backend",
    description="AI powered job application assistant API",
    version="1.0.0"
)

# ── CORS SETTINGS ─────────────────────────────────────────────────────────────
# This allows our React frontend to talk to this backend
# Without this the browser blocks all requests from React to FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://hirepathai.netlify.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── MIDDLEWARE TO CLEAN SPECIAL CHARACTERS ────────────────────────────────────
# This runs on every single request before it reaches our endpoints
# It fixes real newlines inside JSON strings which break JSON parsing
# It also removes other control characters that cause errors
@app.middleware("http")
async def clean_request_body(request: Request, call_next):
    """
    Cleans incoming request body before JSON parsing
    Main problem it fixes:
    - Real newlines inside JSON string values break parsing
    - Control characters like tab carriage return etc cause errors
    - Smart quotes and special unicode characters

    This runs automatically on every POST and PUT request
    """

    if request.method in ["POST", "PUT"]:
        try:
            # Read the raw body bytes from the request
            body_bytes = await request.body()

            if body_bytes:
                # Decode bytes to string
                # errors=replace means bad bytes become ? instead of crashing
                body_str = body_bytes.decode('utf-8', errors='replace')

                # Fix smart quotes and special unicode characters
                # These come from copy pasting from Word or websites
                body_str = body_str.replace('\u2018', "'")   # Left single quote
                body_str = body_str.replace('\u2019', "'")   # Right single quote you'll
                body_str = body_str.replace('\u201c', '"')   # Left double quote
                body_str = body_str.replace('\u201d', '"')   # Right double quote
                body_str = body_str.replace('\u2013', '-')   # En dash
                body_str = body_str.replace('\u2014', '-')   # Em dash
                body_str = body_str.replace('\u2026', '...')  # Ellipsis
                body_str = body_str.replace('\u00a0', ' ')   # Non breaking space

                # Fix the main problem — real newlines inside JSON strings
                # JSON does not allow actual newline characters inside string values
                # We must replace them with the escaped version \n
                # We do this by going through the string character by character
                # and tracking whether we are inside a JSON string or not
                result = []
                inside_string = False
                i = 0

                while i < len(body_str):
                    char = body_str[i]

                    # Check if this quote starts or ends a JSON string
                    # Make sure it is not an escaped quote like \"
                    if char == '"' and (i == 0 or body_str[i-1] != '\\'):
                        inside_string = not inside_string
                        result.append(char)

                    elif inside_string:
                        # We are inside a JSON string value
                        # Replace problematic characters with safe versions
                        if char == '\n':
                            # Real newline — replace with escaped newline
                            result.append('\\n')
                        elif char == '\r':
                            # Carriage return — replace with escaped version
                            result.append('\\r')
                        elif char == '\t':
                            # Tab — replace with escaped version
                            result.append('\\t')
                        elif char == '\\' and i + 1 < len(body_str):
                            # Backslash — keep it and the next character together
                            result.append(char)
                            result.append(body_str[i + 1])
                            i += 1
                        elif ord(char) < 32:
                            # Any other control character — replace with space
                            result.append(' ')
                        else:
                            # Normal character — keep as is
                            result.append(char)

                    else:
                        # We are outside a JSON string
                        # Keep everything as is
                        result.append(char)

                    i += 1

                # Join all characters back into a string
                cleaned_str = ''.join(result)

                # Convert back to bytes
                cleaned_bytes = cleaned_str.encode('utf-8')

                # Create a new receive function with the cleaned body
                # This replaces the original request body with our cleaned version
                async def receive():
                    return {
                        "type": "http.request",
                        "body": cleaned_bytes,
                        "more_body": False
                    }

                # Replace the request with our cleaned version
                request = Request(request.scope, receive)

        except Exception as e:
            # If anything goes wrong just pass the original request
            # We never want middleware to crash the whole server
            print(f"Middleware cleaning error: {e}")
            pass

    # Pass the request to the actual endpoint
    response = await call_next(request)
    return response

# ── CONNECT ROUTERS ───────────────────────────────────────────────────────────
# This connects our routers to the main app
# All resume endpoints will be at /resume/...
# All job description endpoints will be at /jd/...
app.include_router(resume.router)
app.include_router(jd.router)
app.include_router(skillgap.router)
app.include_router(coverletter.router)
app.include_router(cvrewrite.router)


# ── HOME ENDPOINT ─────────────────────────────────────────────────────────────
# Visit http://localhost:8000 to check if backend is running
@app.get("/")
def home():
    return {
        "message": "HirePathAI Backend is running",
        "status": "ok",
        "version": "1.0.0"
    }

# ── HEALTH CHECK ──────────────────────────────────────────────────────────────
# Visit http://localhost:8000/health to check if API is healthy
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "message": "All systems working"
    }