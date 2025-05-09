# gemini_unified.py
import os
import re
import json
from google import genai
from dotenv import load_dotenv
from google.genai import types
import plotly.io as pio
import pandas as pd
import plotly.express as px
from httpx import RemoteProtocolError
from google.genai.errors import ClientError
import time

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
Generate only the Python code (no markdown fences, no explanations) that creats a chart from the given spec. 
- The code must define a figure named `fig`.
- The DataFrame is available as `df`.

Spec:
{spec_json}
"""

def _safe_generate(model, config, contents, max_retries=3):
    """Call client.models.generate_content with retries on transient errors."""
    delay = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            return client.models.generate_content(
                model=model,
                config=config,
                contents=contents
            )
        except (RemoteProtocolError, ClientError) as e:
            # Only retry on transport disconnects or rate‑limit retries
            retriable = isinstance(e, RemoteProtocolError) or (isinstance(e, ClientError) and e.status_code in (429, 503))
            if attempt < max_retries and retriable:
                time.sleep(delay)
                delay *= 2
                continue
            # Otherwise, re‑raise
            raise

def _strip_fences(text: str) -> str:
    """
    Remove leading/trailing Markdown code fences (```…```) from a block of text.
    """
    raw = text
    # If it starts with a fence, strip the first and last fence lines
    if raw.startswith("```"):
        lines = raw.splitlines()
        # drop opening fence
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        # drop closing fence
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines)
    return raw


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

"""
def get_data_and_chart_spec(question: str) -> tuple:
    prompt = DATA_VIZ_TMPL.format(question=question)
    config = types.GenerateContentConfig(temperature=0.2)

    response = client.models.generate_content(
        model='gemini-2.5-pro-exp-03-25',
        config=config,
        contents=prompt
    )
    raw = response.text.strip().strip("```json").strip("```").strip()
    parsed = json.loads(raw)
    data, spec = _validate_data_and_spec(parsed)
    return data, spec
"""

#+++++++++++++++++++++++++++++++++++++
def get_data_and_chart_spec(question: str) -> tuple[list[dict], dict]:
    prompt = DATA_VIZ_TMPL.format(question=question)
    config = types.GenerateContentConfig(temperature=0.2)

    # === wrap prompt in a list! ===
    response = _safe_generate(
        model="gemini-2.5-pro-exp-03-25",
        config=config,
        contents=[prompt],
    )

    # === guard against None.text ===
    raw = response.text
    if not raw:
        raise RuntimeError(
            "Empty response from Gemini – check your API key, quota, or contents format"
        )

    # strip fences and parse JSON
    raw = raw.strip().strip("```json").strip("```").strip()
    parsed = json.loads(raw)

    data, spec = _validate_data_and_spec(parsed)
    return data, spec
#+++++++++++++++++++++++++++++++++++++

"""
def generate_code(spec: dict) -> str:
    prompt = CODE_TMPL.format(spec_json=json.dumps(spec))
    response = client.models.generate_content(
        model='gemini-2.5-pro-exp-03-25',
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
"""
#++++++++++++++++++++++++++++++++++++
def generate_code(spec: dict) -> str:
    prompt = CODE_TMPL.format(spec_json=json.dumps(spec))
    config = types.GenerateContentConfig(temperature=0)
    response = _safe_generate(
        model="gemini-2.5-pro-preview-03-25",
        config=config,
        contents=[prompt],
    )

    raw = response.text
    if not raw:
        raise RuntimeError("Empty code response from Gemini")

    # strip Markdown fences…
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()

    if "fig" not in raw:
        raise ValueError("Generated code didn’t define `fig`")

    return raw

#++++++++++++++++++++++++++++++++++++


def execute_plotly_code(data, code: str) -> str:
    raw_code = _strip_fences(code.strip())

    # universal palette fallback
    raw_code = re.sub(
        r'px\.colors\.qualitative\.[A-Za-z0-9_]+',
        'px.colors.qualitative.Plotly',
        raw_code
    )

    df = pd.DataFrame(data)
    local_vars = {'df': df, 'px': px}

    try:
        exec(raw_code, {}, local_vars)

    except TypeError as e:
        err = str(e)

        # 1) marker_size fallback (from before)
        if "marker_size" in err:
            fixed = re.sub(
                r'marker_size\s*=\s*([^,\)\s]+)',
                r'marker=dict(size=\1)',
                raw_code
            )
            exec(fixed, {}, local_vars)
        
        # 2) xbins fallback
        elif "xbins" in err:
            # strip out any xbins={...}
            stripped = re.sub(
                r',?\s*xbins\s*=\s*\{[^}]*\}',
                '',
                raw_code
            )
            exec(stripped, {}, local_vars)

        else:
            # re‑raise anything else
            raise
    except ValueError as e:
        msg = str(e)
        if "borderpad" in msg:
            cleaned = re.sub(
                r',?\s*borderpad\s*=\s*[^,)\s]+',
                '',
                raw_code
            )
            exec(cleaned,{}, local_vars)
        else:
            raise

    if 'fig' not in local_vars:
        raise RuntimeError("Generated code must define a `fig` named variable.")

    return pio.to_json(local_vars['fig'])


