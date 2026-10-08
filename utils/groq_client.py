# groq_client.py
# This file connects to Groq API
# If user provides their own Groq key we use that
# Otherwise we use the default key from .env file

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def call_groq(prompt: str, system_message: str = None, user_groq_key: str = None) -> str:
    """
    Sends a prompt to Groq AI and returns the response
    user_groq_key — if provided we use this instead of default key
    """

    # Use user own key if provided otherwise use default
    api_key = user_groq_key if user_groq_key else os.getenv("GROQ_API_KEY")

    # Create Groq client
    client = Groq(api_key=api_key)

    # Models to try in order
    models_to_try = [
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
    ]

    # Build messages
    messages = []

    if system_message:
        messages.append({
            "role": "system",
            "content": system_message
        })

    messages.append({
        "role": "user",
        "content": prompt
    })

    # Try each model until one works
    last_error = None

    for model in models_to_try:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=4000,
                temperature=0.3,
            )
            print(f"Successfully used model: {model}")
            return response.choices[0].message.content

        except Exception as e:
            print(f"Model {model} failed: {str(e)}")
            last_error = e
            continue

    raise Exception(f"All models failed. Last error: {str(last_error)}")