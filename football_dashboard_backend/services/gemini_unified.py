# gemini_unified.py
import os
import json
from google import genai
from dotenv import load_dotenv
from google.genai import types
import plotly.io as pio
import pandas as pd
import plotly.express as px

load_dotenv()
API_KEY = os.getenv("GEMINI_2.5_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_2.5_API_KEY missing in environment")

client = genai.Client(api_key=API_KEY)

# Unified prompt to return both data and chart spec
DATA_VIZ_TMPL = """
You are a football data expert and charting specialist.

Your task is to:
1. Answer the question with data (as rows of JSON).
2. Propose a suitable Vega-Lite chart spec for visualizing that data.

Instructions:
- Return a single JSON object with two keys:
  • "data": an array of records
  • "spec": a Vega-Lite v5 spec for visualizing it
- The data must directly answer the question.
- Use simple column names (e.g., year, goals, player_name).

Question:
{question}

JSON:
"""

CODE_TMPL = """
You are a Python developer using Plotly Express.
Generate only the Python code (no markdown fences, no explanations) that creats a chart from the given spec. The code must define a Plotly Express figure object named fig.
The DataFrame is available as `df`.
Use color palletes that are compatible with the plotly version installed 6.0.1.
Spec:
{spec_json}
"""

def _validate_data_and_spec(parsed: dict):
    # Must be a JSON object with both keys
    if not isinstance(parsed, dict):
        raise ValueError("LLM output is not a JSON object")
    if "data" not in parsed or "spec" not in parsed:
        raise ValueError("LLM output must contain 'data' and 'spec'")

    data, spec = parsed["data"], parsed["spec"]

    # Data must be a list of dicts
    if not isinstance(data, list):
        raise ValueError("'data' must be a list of records")
    if any(not isinstance(rec, dict) for rec in data):
        raise ValueError("Every item in 'data' must be a dict")

    # Spec only needs to be a dict (we trust LLM to provide a valid Vega‑Lite spec)
    if not isinstance(spec, dict):
        raise ValueError("'spec' must be a JSON object")

    return data, spec


def get_data_and_chart_spec(question: str) -> tuple:
    prompt = DATA_VIZ_TMPL.format(question=question)
    config = types.GenerateContentConfig(temperature=0.2)

    response = client.models.generate_content(
        model='gemini-2.5-pro-preview-03-25',
        config=config,
        contents=prompt
    )
    raw = response.text.strip().strip("```json").strip("```").strip()
    parsed = json.loads(raw)
    data, spec = _validate_data_and_spec(parsed)
    return data, spec

def generate_code(spec: dict) -> str:
    prompt = CODE_TMPL.format(spec_json=json.dumps(spec))
    response = client.models.generate_content(
        model='gemini-2.5-pro-preview-03-25',
        config=types.GenerateContentConfig(temperature=0),
        contents=prompt
    )
    raw = response.text.strip()

    # Strip Markdown fences if present
    if raw.startswith("```"):
        lines = raw.splitlines()
        # drop the first ```... line
        if lines[0].startswith("```"):
            lines = lines[1:]
        # drop the last ``` line if it's a fence
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()

    # Quick sanity check
    if "fig" not in raw:
        raise ValueError("Plotly code didn’t define a `fig` variable")
    return raw
#    return response.text.strip()

def execute_plotly_code(data, code: str):
    df = pd.DataFrame(data)
    local_vars = {'df': df, 'px': px}
    
    # Execute the generated Plotly code safely
    exec(code, {}, local_vars)
    
    # Expect the generated code defines a figure named 'fig'
    if 'fig' not in local_vars:
        raise RuntimeError("Generated code must define a Plotly figure as 'fig'.")

    fig = local_vars['fig']

    # Return Plotly JSON figure
    return pio.to_json(fig)
