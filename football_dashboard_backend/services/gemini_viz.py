# services/gemini_viz.py
import os
import json
from google import genai
from dotenv import load_dotenv
from google.genai import types
import re
import pprint
load_dotenv()
API_KEY = os.getenv("GEMINI_2.5_API_KEY")

client = genai.Client(api_key=API_KEY)

def generate_code(spec: dict) -> str:
    prompt = f"""
You are a Python developer using Plotly Express.
Generate code that creates a chart from this spec.

Spec:
{json.dumps(spec)}

The DataFrame is available as `df`.
"""
    response = client.models.generate_content(
        model='gemini-2.5-pro-exp-03-25',
        config=types.GenerateContentConfig(temperature=0),
        contents=prompt
    )
    return response.text.strip()
